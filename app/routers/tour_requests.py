"""Landlord review of tour requests (read-only in Phase 3; decisions come in Phase 4)."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models import NotificationLog, Property, TourIdPhoto, TourRequest
from app.models.enums import TourRequestStatus
from app.routers.crud import get_or_404
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
    unit = f", {prop.address_line2}" if prop.address_line2 else ""
    return TourRequestRead(
        **req.model_dump(exclude={"updated_at", "user_agent", "id_photo_deleted_at"}),
        property_name=prop.name,
        property_address=f"{prop.address_line1}{unit}, {prop.city}, {prop.state}",
        when_display=fmt_for_landlord(req.tour_start, req.time_zone),
        has_id_photo=has_photo,
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
