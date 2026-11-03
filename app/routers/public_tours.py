"""Public tour booking: slot availability and request submission.

Lives under /api/v1/public so it's reachable on the public hosts. Anonymous, so
it validates everything server-side and is rate limited.
"""

from __future__ import annotations

import time as _time
import uuid
from collections import defaultdict, deque
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session
from app.models import Listing, Property, TourFeedback, TourIdPhoto, TourRequest
from app.models.enums import ACTIVE_TOUR_STATUSES, ListingStatus
from app.routers.public_auth import current_visitor_email
from app.services.sms_service import normalize_us_phone
from app.services.timezones import property_time_zone
from app.services.tour_notifications import notify_landlord_feedback, notify_tour_request_submitted
from app.services.tour_scheduling import (
    ID_PHOTO_RETENTION,
    SLOT_TIMES,
    TOUR_MINUTES,
    check_slot,
    fmt_local,
    local_to_utc,
)

router = APIRouter(prefix="/public", tags=["public"])

# Must match SMS_CONSENT_TEXT in frontend/src/public/company.ts (a test checks this).
SMS_CONSENT_TEXT = (
    "I agree to receive text messages from APEX Element Group LLC about my tour request, "
    "including approval status, my one-time access code, and a follow-up request for feedback. "
    "Message frequency varies (typically 3–5 messages per tour). Message and data rates may apply. "
    "Reply STOP to opt out or HELP for help. Consent is not required to request a tour."
)

MAX_ID_BYTES = 10 * 1024 * 1024
ID_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}

# Simple per-IP limit (single Railway instance): 5 submissions per hour.
RATE_LIMIT, RATE_WINDOW = 5, 3600
_recent: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return (
        request.headers.get("cf-connecting-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )


def _rate_limited(ip: str) -> bool:
    now = _time.monotonic()
    q = _recent[ip]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return True
    q.append(now)
    return False


def _live_listing(session: Session, listing_id: uuid.UUID) -> tuple[Listing, Property]:
    listing = session.get(Listing, listing_id)
    if listing is None or listing.status != ListingStatus.listed.value:
        raise HTTPException(status_code=404, detail="This home isn't available for tours.")
    return listing, session.get(Property, listing.property_id)


def _taken_starts(session: Session, property_id: uuid.UUID, start: datetime, end: datetime) -> set[datetime]:
    rows = session.exec(
        select(TourRequest.tour_start).where(
            TourRequest.property_id == property_id,
            TourRequest.status.in_(ACTIVE_TOUR_STATUSES),
            TourRequest.tour_start >= start,
            TourRequest.tour_start < end,
        )
    ).all()
    return {r.astimezone(timezone.utc) for r in rows}


@router.get("/listings/{listing_id}/availability")
def availability(listing_id: uuid.UUID, day: date, session: Session = Depends(get_session)):
    """Bookable start times for one local day at this home."""
    _, prop = _live_listing(session, listing_id)
    tz = property_time_zone(prop)
    day_start = local_to_utc(day, time(0, 0), tz)
    taken = _taken_starts(session, prop.id, day_start, day_start + timedelta(days=1, hours=1))
    slots = []
    for t in SLOT_TIMES:
        start_utc = local_to_utc(day, t, tz)
        slots.append({
            "time": t.strftime("%H:%M"),
            "available": check_slot(day, t, tz) is None and start_utc not in taken,
        })
    return {"time_zone": tz, "date": day.isoformat(), "slots": slots}


@router.post("/tour-requests", status_code=201)
async def submit_tour_request(
    request: Request,
    background: BackgroundTasks,
    listing_id: uuid.UUID = Form(...),
    first_name: str = Form(..., max_length=100),
    last_name: str = Form(..., max_length=100),
    phone: str = Form(..., max_length=30),
    tour_date: date = Form(...),
    tour_time: str = Form(...),
    sms_consent: bool = Form(False),
    website: str = Form(""),  # honeypot: real people never fill this hidden field
    id_photo: UploadFile = File(...),
    session: Session = Depends(get_session),
    visitor_email: str | None = Depends(current_visitor_email),
):
    # The email comes from the visitor's verified sign-in, never from the form.
    if not visitor_email:
        raise HTTPException(status_code=401, detail="Please verify your email address first.")
    email = visitor_email
    if website.strip():
        # Pretend success so bots don't learn anything.
        return {"ok": True}

    ip = _client_ip(request)
    if _rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later or email us.")

    first_name, last_name = first_name.strip(), last_name.strip()
    if not first_name or not last_name:
        raise HTTPException(status_code=422, detail="Please enter your first and last name.")
    phone_e164 = normalize_us_phone(phone)
    if not phone_e164:
        raise HTTPException(status_code=422, detail="Please enter a valid US mobile number.")
    try:
        start_t = datetime.strptime(tour_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=422, detail="Please choose a start time.")

    listing, prop = _live_listing(session, listing_id)
    tz = property_time_zone(prop)
    problem = check_slot(tour_date, start_t, tz)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    start_utc = local_to_utc(tour_date, start_t, tz)
    if start_utc in _taken_starts(session, prop.id, start_utc, start_utc + timedelta(minutes=1)):
        raise HTTPException(status_code=409, detail="That time was just booked. Please pick another time.")

    if id_photo.content_type not in ID_TYPES:
        raise HTTPException(status_code=422, detail="Upload a photo of your ID (JPG, PNG, WEBP or HEIC).")
    content = await id_photo.read()
    if not content:
        raise HTTPException(status_code=422, detail="The ID photo is empty.")
    if len(content) > MAX_ID_BYTES:
        raise HTTPException(status_code=413, detail="The ID photo must be under 10 MB.")

    now = datetime.now(timezone.utc)
    end_utc = start_utc + timedelta(minutes=TOUR_MINUTES)
    req = TourRequest(
        listing_id=listing.id,
        property_id=prop.id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone_e164,
        tour_start=start_utc,
        tour_end=end_utc,
        time_zone=tz,
        sms_consent=sms_consent,
        sms_consent_text=SMS_CONSENT_TEXT if sms_consent else None,
        sms_consent_at=now if sms_consent else None,
        submitted_ip=ip[:64],
        user_agent=(request.headers.get("user-agent") or "")[:400] or None,
        id_photo_delete_after=end_utc + ID_PHOTO_RETENTION,
    )
    session.add(req)
    session.flush()
    session.add(TourIdPhoto(
        tour_request_id=req.id,
        filename=(id_photo.filename or "")[:255] or None,
        content_type=id_photo.content_type,
        file_size=len(content),
        content=content,
    ))
    try:
        session.commit()
    except IntegrityError:
        # Someone else grabbed this slot between our check and the insert.
        session.rollback()
        raise HTTPException(status_code=409, detail="That time was just booked. Please pick another time.")

    background.add_task(notify_tour_request_submitted, req.id)
    return {"ok": True, "when": fmt_local(start_utc, tz)}


# --- Post-tour feedback (private link sent after the tour) ----------------------


class FeedbackIn(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    interested: Literal["yes", "maybe", "no"]
    liked: Optional[str] = Field(default=None, max_length=2000)
    concerns: Optional[str] = Field(default=None, max_length=2000)


def _by_token(session: Session, token: str) -> TourRequest:
    req = session.exec(select(TourRequest).where(TourRequest.feedback_token == token)).first() if token else None
    if req is None:
        raise HTTPException(status_code=404, detail="This feedback link isn't valid.")
    return req


@router.get("/feedback/{token}")
def feedback_info(token: str, session: Session = Depends(get_session)):
    req = _by_token(session, token)
    prop = session.get(Property, req.property_id)
    unit = f", {prop.address_line2}" if prop.address_line2 else ""
    return {
        "first_name": req.first_name,
        "home": f"{prop.address_line1}{unit}, {prop.city}",
        "when": fmt_local(req.tour_start, req.time_zone),
        "submitted": session.exec(select(TourFeedback.id).where(TourFeedback.tour_request_id == req.id)).first()
        is not None,
    }


@router.post("/feedback/{token}", status_code=201)
def submit_feedback(token: str, payload: FeedbackIn, background: BackgroundTasks,
                    session: Session = Depends(get_session)):
    req = _by_token(session, token)
    clean = lambda v: (v or "").strip() or None  # noqa: E731
    session.add(TourFeedback(tour_request_id=req.id, rating=payload.rating, interested=payload.interested,
                             liked=clean(payload.liked), concerns=clean(payload.concerns)))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Thanks — we already have your feedback.")
    background.add_task(notify_landlord_feedback, req.id)
    return {"ok": True}
