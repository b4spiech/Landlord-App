"""Email sign-in for the public tour form."""

import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models import EmailVerification, VisitorSession
from app.routers import public_auth
from app.services import email_service, visitor_auth

PUBLIC = {"host": "tours.example.com"}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    sent = []

    async def fake_email(to, subject, html, attachments=None, text_body=None):
        sent.append((to[0], subject, text_body))

    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_email", fake_email)
    public_auth._recent.clear()
    with TestClient(app) as c:
        with Session(engine) as s:
            s.exec(delete(EmailVerification))
            s.exec(delete(VisitorSession))
            s.commit()
        yield c, sent


def _code(sent):
    return re.search(r"\b(\d{6})\b", sent[-1][2]).group(1)


def test_full_sign_in_flow(env):
    c, sent = env
    assert c.get("/api/v1/public/auth/me", headers=PUBLIC).status_code == 401
    assert c.post("/api/v1/public/auth/start", json={"email": " Pat@Example.COM "}, headers=PUBLIC).status_code == 200
    assert sent[-1][0] == "pat@example.com" and "sign-in code" in sent[-1][1]
    r = c.post("/api/v1/public/auth/verify", json={"email": "pat@example.com", "code": _code(sent)}, headers=PUBLIC)
    assert r.status_code == 200 and r.json() == {"email": "pat@example.com"}
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=2592000" in cookie
    assert c.get("/api/v1/public/auth/me", headers=PUBLIC).json() == {"email": "pat@example.com"}
    # Codes are single use.
    assert c.post("/api/v1/public/auth/verify", json={"email": "pat@example.com", "code": _code(sent)},
                  headers=PUBLIC).status_code == 400
    c.post("/api/v1/public/auth/logout", headers=PUBLIC)
    assert c.get("/api/v1/public/auth/me", headers=PUBLIC).status_code == 401


def test_secure_cookie_over_https(env):
    c, sent = env
    c.post("/api/v1/public/auth/start", json={"email": "a@example.com"}, headers=PUBLIC)
    r = c.post("/api/v1/public/auth/verify", json={"email": "a@example.com", "code": _code(sent)},
               headers=PUBLIC | {"x-forwarded-proto": "https"})
    assert "Secure" in r.headers["set-cookie"]


def test_wrong_codes_lock_out_after_five(env):
    c, sent = env
    c.post("/api/v1/public/auth/start", json={"email": "b@example.com"}, headers=PUBLIC)
    good = _code(sent)
    bad = "000000" if good != "000000" else "111111"
    for left in (4, 3, 2, 1):
        r = c.post("/api/v1/public/auth/verify", json={"email": "b@example.com", "code": bad}, headers=PUBLIC)
        assert r.status_code == 400 and f"{left} tr" in r.json()["detail"]
    c.post("/api/v1/public/auth/verify", json={"email": "b@example.com", "code": bad}, headers=PUBLIC)
    r = c.post("/api/v1/public/auth/verify", json={"email": "b@example.com", "code": good}, headers=PUBLIC)
    assert r.status_code == 400 and "new code" in r.json()["detail"]


def test_new_code_replaces_old_and_codes_expire(env):
    c, sent = env
    c.post("/api/v1/public/auth/start", json={"email": "d@example.com"}, headers=PUBLIC)
    first = _code(sent)
    c.post("/api/v1/public/auth/start", json={"email": "d@example.com"}, headers=PUBLIC)
    second = _code(sent)
    if first != second:
        assert c.post("/api/v1/public/auth/verify", json={"email": "d@example.com", "code": first},
                      headers=PUBLIC).status_code == 400
    with Session(engine) as s:
        row = s.exec(select(EmailVerification).where(EmailVerification.consumed_at.is_(None))).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        s.commit()
    r = c.post("/api/v1/public/auth/verify", json={"email": "d@example.com", "code": second}, headers=PUBLIC)
    assert r.status_code == 400 and "expired" in r.json()["detail"]


def test_rate_limits(env):
    c, sent = env
    for _ in range(3):
        assert c.post("/api/v1/public/auth/start", json={"email": "e@example.com"}, headers=PUBLIC).status_code == 200
    assert c.post("/api/v1/public/auth/start", json={"email": "e@example.com"}, headers=PUBLIC).status_code == 429


def test_bad_email_and_unconfigured_email(env, monkeypatch):
    c, sent = env
    assert c.post("/api/v1/public/auth/start", json={"email": "nope"}, headers=PUBLIC).status_code == 422
    monkeypatch.setattr(email_service, "is_configured", lambda: False)
    assert c.post("/api/v1/public/auth/start", json={"email": "f@example.com"}, headers=PUBLIC).status_code == 503


def test_only_hashes_are_stored(env):
    c, sent = env
    c.post("/api/v1/public/auth/start", json={"email": "g@example.com"}, headers=PUBLIC)
    code = _code(sent)
    r = c.post("/api/v1/public/auth/verify", json={"email": "g@example.com", "code": code}, headers=PUBLIC)
    token = r.cookies[visitor_auth.COOKIE_NAME]
    with Session(engine) as s:
        assert code not in s.exec(select(EmailVerification)).one().code_hash
        assert s.exec(select(VisitorSession)).one().token_hash != token


def test_expired_session_is_rejected(env):
    c, sent = env
    with Session(engine) as s:
        token = visitor_auth.create_session(s, "h@example.com", now=datetime.now(timezone.utc) - timedelta(days=31))
        s.commit()
    c.cookies.set(visitor_auth.COOKIE_NAME, token)
    assert c.get("/api/v1/public/auth/me", headers=PUBLIC).status_code == 401
