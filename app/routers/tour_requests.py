"""Landlord review of tour requests: view, approve, decline, cancel, and send the door code."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.database import get_session
from app.models import AccessCode, NotificationLog, Property, TourIdPhoto, TourRequest
from app.models.enums import TourRequestStatus
from app.routers.crud import get_or_404
from app.services import tour_notifications
from app.services.access_codes import code_for_tour, release_for_tour, reserve_for_tour
from app.services.tour_scheduling import fmt_for_landlord

router = APIRouter(prefix="/tour-requests", tags=["tour-requests"])


class TourRequestRead(BaseModel):
    id: uuid.UUID
    created_at: datetime
    listing_id: uuid.UUID
    property_id: uuid.UUID
    property_name: str
    property_address: str
    status: str
    first_name: str
    last_name: str
    email: str
    phone: str
    tour_start: datetime
    tour_end: datetime
    time_zone: str
    when_display: str  # property-local time (+ landlord time if different)
    sms_consent: bool
    sms_consent_at: Optional[datetime] = None
    sms_consent_text: Optional[str] = None
    submitted_ip: Optional[str] = None
    has_id_photo: bool
    id_photo_delete_after: datetime
    decided_at: Optional[datetime] = None
    decision_note: Optional[str] = None
    access_code: Optional[str] = None
    access_code_status: Optional[str] = None  # reserved | issued
    code_sent_at: Optional[datetime] = None


class DecisionIn(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


class NotificationRead(BaseModel):
    created_at: datetime
    channel: str
    audience: str
    kind: str
    recipient: str
    status: str
    detail: Optional[str] = None


def _read(session: Session, req: TourRequest, prop: Property) -> TourRequestRead:
    has_photo = session.exec(
        select(TourIdPhoto.id).where(TourIdPhoto.tour_request_id == req.id)
    ).first() is not None
    code: Optional[AccessCode] = code_for_tour(session, req)
    unit = f", {prop.address_line2}" if prop.address_line2 else ""
    return TourRequestRead(
        **req.model_dump(exclude={"updated_at", "user_agent", "id_photo_deleted_at"}),
        property_name=prop.name,
        property_address=f"{prop.address_line1}{unit}, {prop.city}, {prop.state}",
        when_display=fmt_for_landlord(req.tour_start, req.time_zone),
        has_id_photo=has_photo,
        access_code=code.code if code else None,
        access_code_status=code.status if code else None,
    )


@router.get("", response_model=list[TourRequestRead])
def list_tour_requests(
    status_filter: Optional[TourRequestStatus] = None,
    property_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    stmt = select(TourRequest, Property).join(Property, Property.id == TourRequest.property_id)
    if status_filter:
        stmt = stmt.where(TourRequest.status == status_filter.value)
    if property_id:
        stmt = stmt.where(TourRequest.property_id == property_id)
    stmt = stmt.order_by(TourRequest.tour_start.desc())
    return [_read(session, r, p) for r, p in session.exec(stmt).all()]


@router.get("/{request_id}", response_model=TourRequestRead)
def get_tour_request(request_id: uuid.UUID, session: Session = Depends(get_session)):
    req = get_or_404(session, TourRequest, request_id, "Tour request")
    return _read(session, req, session.get(Property, req.property_id))


@router.get("/{request_id}/notifications", response_model=list[NotificationRead])
def get_notifications(request_id: uuid.UUID, session: Session = Depends(get_session)):
    get_or_404(session, TourRequest, request_id, "Tour request")
    return session.exec(
        select(NotificationLog)
        .where(NotificationLog.tour_request_id == request_id)
        .order_by(NotificationLog.created_at)
    ).all()


@router.get("/{request_id}/id-photo")
def get_id_photo(request_id: uuid.UUID, session: Session = Depends(get_session)):
    photo = session.exec(select(TourIdPhoto).where(TourIdPhoto.tour_request_id == request_id)).first()
    if photo is None:
        raise HTTPException(status_code=404, detail="No ID photo (it may have been deleted after 30 days).")
    # Sensitive: never cache.
    return Response(content=photo.content, media_type=photo.content_type or "image/jpeg",
                    headers={"Cache-Control": "no-store"})


# --- Decisions ------------------------------------------------------------------


def _load(session: Session, request_id: uuid.UUID, allowed: tuple[str, ...], action: str) -> TourRequest:
    # Row lock: two clicks on Approve can't both reserve a code.
    req = session.exec(select(TourRequest).where(TourRequest.id == request_id).with_for_update()).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Tour request not found")
    if req.status not in allowed:
        raise HTTPException(status_code=409, detail=f"Can't {action} a tour that is {req.status}.")
    return req


def _decide(session: Session, req: TourRequest, status: TourRequestStatus, note: Optional[str]) -> None:
    req.status = status.value
    req.decided_at = datetime.now(timezone.utc)
    req.decision_note = (note or "").strip() or None
    session.add(req)


@router.post("/{request_id}/approve", response_model=TourRequestRead)
def approve(request_id: uuid.UUID, payload: DecisionIn, background: BackgroundTasks,
            session: Session = Depends(get_session)):
    """Approve: hold a door code for this tour and tell the visitor."""
    req = _load(session, request_id, ("pending",), "approve")
    if req.tour_start.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="This tour time has already passed.")
    if reserve_for_tour(session, req) is None:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="No door codes are available for this property on the tour date. Add codes on the "
                   "property page, then approve.",
        )
    _decide(session, req, TourRequestStatus.approved, payload.note)
    session.commit()
    background.add_task(tour_notifications.notify_tour_approved, req.id)
    return _read(session, req, session.get(Property, req.property_id))


@router.post("/{request_id}/decline", response_model=TourRequestRead)
def decline(request_id: uuid.UUID, payload: DecisionIn, background: BackgroundTasks,
            session: Session = Depends(get_session)):
    """Decline a pending request; the time slot opens up again."""
    req = _load(session, request_id, ("pending",), "decline")
    _decide(session, req, TourRequestStatus.declined, payload.note)
    session.commit()
    background.add_task(tour_notifications.notify_tour_declined, req.id)
    return _read(session, req, session.get(Property, req.property_id))


@router.post("/{request_id}/cancel", response_model=TourRequestRead)
def cancel(request_id: uuid.UUID, payload: DecisionIn, background: BackgroundTasks,
           session: Session = Depends(get_session)):
    """Cancel an approved tour: release its unsent code and tell the visitor."""
    req = _load(session, request_id, ("approved",), "cancel")
    release_for_tour(session, req)
    _decide(session, req, TourRequestStatus.cancelled, payload.note)
    session.commit()
    background.add_task(tour_notifications.notify_tour_cancelled, req.id)
    return _read(session, req, session.get(Property, req.property_id))


@router.post("/{request_id}/send-code", response_model=TourRequestRead)
async def send_code(request_id: uuid.UUID, session: Session = Depends(get_session)):
    """Send (or resend) the door code now. The same code is reused on resend."""
    req = get_or_404(session, TourRequest, request_id, "Tour request")
    if req.status != "approved":
        raise HTTPException(status_code=409, detail=f"Can't send a code for a tour that is {req.status}.")
    # Don't hold this session's transaction open: send_access_code updates the
    # same row in its own session (holding a lock here would deadlock).
    session.rollback()
    try:
        await tour_notifications.send_access_code(req.id)
    except tour_notifications.NoCodeAvailable:
        raise HTTPException(status_code=409, detail="No door codes are available for this property.")
    session.expire_all()
    req = session.get(TourRequest, request_id)
    return _read(session, req, session.get(Property, req.property_id))
