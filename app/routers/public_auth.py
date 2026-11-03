"""Email sign-in for the public tour form: send a code, verify it, get a session cookie."""

from __future__ import annotations

import html
import logging
import time as _time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.database import get_session
from app.services import email_service
from app.services import visitor_auth as va

log = logging.getLogger(__name__)
router = APIRouter(prefix="/public/auth", tags=["public"])

# Per-IP limit on code requests (single instance): 10 per hour.
IP_LIMIT, IP_WINDOW = 10, 3600
_recent: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    return (
        request.headers.get("cf-connecting-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )


def _ip_limited(ip: str) -> bool:
    now = _time.monotonic()
    q = _recent[ip]
    while q and now - q[0] > IP_WINDOW:
        q.popleft()
    if len(q) >= IP_LIMIT:
        return True
    q.append(now)
    return False


def _is_https(request: Request) -> bool:
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def current_visitor_email(request: Request, session: Session = Depends(get_session)) -> str | None:
    return va.session_email(session, request.cookies.get(va.COOKIE_NAME))


class StartIn(BaseModel):
    email: str = Field(..., max_length=254)


class VerifyIn(BaseModel):
    email: str = Field(..., max_length=254)
    code: str = Field(..., max_length=10)


@router.post("/start")
async def start(payload: StartIn, request: Request, session: Session = Depends(get_session)):
    """Email a 6-digit sign-in code."""
    email = va.normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")
    if _ip_limited(client_ip(request)) or va.too_many_codes(session, email, datetime.now(timezone.utc)):
        raise HTTPException(status_code=429, detail="Too many codes requested. Please wait a few minutes.")
    if not email_service.is_configured():
        raise HTTPException(status_code=503, detail="Email sign-in isn't available right now. Please email us.")
    code = va.create_code(session, email, client_ip(request))
    session.commit()
    text = (f"Your APEX Element Group sign-in code is {code}\n\nIt expires in 10 minutes. "
            "If you didn't request it, you can ignore this email.\n")
    body = (
        "<div style='font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:15px;color:#111'>"
        "<p>Your sign-in code for requesting a tour:</p>"
        f"<p style='font-size:30px;font-weight:700;letter-spacing:6px;font-family:monospace'>{html.escape(code)}</p>"
        "<p>It expires in 10 minutes. If you didn't request it, you can ignore this email.</p>"
        "<p>— APEX Element Group</p></div>"
    )
    try:
        await email_service.send_email([email], f"Your sign-in code: {code}", body, text_body=text)
    except Exception:  # noqa: BLE001
        log.exception("Sign-in code email to %s failed", email)
        raise HTTPException(status_code=502, detail="We couldn't send the code. Please check the address and try again.")
    return {"ok": True}


@router.post("/verify")
def verify(payload: VerifyIn, request: Request, response: Response, session: Session = Depends(get_session)):
    """Check the code; on success set the session cookie (30 days)."""
    email = va.normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")
    try:
        va.verify_code(session, email, payload.code)
    except va.VerifyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    token = va.create_session(session, email)
    session.commit()
    response.set_cookie(
        va.COOKIE_NAME, token, max_age=int(va.SESSION_TTL.total_seconds()), httponly=True,
        secure=_is_https(request), samesite="lax", path="/",
    )
    return {"email": email}


@router.get("/me")
def me(email: str | None = Depends(current_visitor_email)):
    if not email:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"email": email}


@router.post("/logout")
def logout(request: Request, response: Response, session: Session = Depends(get_session)):
    va.end_session(session, request.cookies.get(va.COOKIE_NAME))
    session.commit()
    response.delete_cookie(va.COOKIE_NAME, path="/")
    return {"ok": True}
