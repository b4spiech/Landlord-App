"""Self-guided tour requests from the public site, and an outbound notification log."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Index, LargeBinary, text
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import TourRequestStatus


class TourRequest(TimestampMixin, table=True):
    __tablename__ = "tour_request"
    __table_args__ = (
        # One active (pending/approved) booking per property per start time.
        Index(
            "uq_tour_slot_active",
            "property_id",
            "tour_start",
            unique=True,
            postgresql_where=text("status IN ('pending', 'approved')"),
        ),
    )

    listing_id: uuid.UUID = Field(foreign_key="listing.id", index=True)
    property_id: uuid.UUID = Field(foreign_key="property.id", index=True)
    status: str = Field(default=TourRequestStatus.pending.value, max_length=20, index=True)

    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str = Field(max_length=254)
    phone: str = Field(max_length=20)  # E.164, e.g. +16165551234

    # When: stored in UTC; time_zone is the property's zone at booking time.
    tour_start: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    tour_end: datetime = Field(sa_type=DateTime(timezone=True))
    time_zone: str = Field(max_length=64)

    # SMS consent record (TCPA / carrier compliance): exactly what they agreed to, and when.
    sms_consent: bool = Field(default=False)
    sms_consent_text: Optional[str] = Field(default=None)
    sms_consent_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    submitted_ip: Optional[str] = Field(default=None, max_length=64)
    user_agent: Optional[str] = Field(default=None, max_length=400)

    # Landlord decision (Phase 4).
    decided_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    decision_note: Optional[str] = Field(default=None)
    # When the door code was last sent (manually or by the scheduler).
    code_sent_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    # Scheduler bookkeeping for automatic code sends (retries + landlord alert).
    code_send_attempts: int = Field(default=0, sa_column_kwargs={"server_default": "0"})
    code_last_attempt_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # After the tour: marked completed, and a private feedback link is sent.
    completed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    feedback_token: Optional[str] = Field(default=None, max_length=64, unique=True, index=True)
    feedback_requested_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # Photo ID retention: deleted after this time (30 days after the tour).
    id_photo_delete_after: datetime = Field(sa_type=DateTime(timezone=True))
    id_photo_deleted_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))


class TourIdPhoto(TimestampMixin, table=True):
    """The visitor's photo ID. Separate table so listing requests never loads image bytes."""

    __tablename__ = "tour_id_photo"

    tour_request_id: uuid.UUID = Field(foreign_key="tour_request.id", index=True, unique=True)
    filename: Optional[str] = Field(default=None, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=120)
    file_size: Optional[int] = Field(default=None)
    content: bytes = Field(sa_column=Column(LargeBinary, nullable=False))


class NotificationLog(TimestampMixin, table=True):
    """Every email/SMS the system tries to send, with the outcome."""

    __tablename__ = "notification_log"

    tour_request_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tour_request.id", index=True)
    # Set for messages about a listing that aren't tied to a tour (e.g. "share link").
    listing_id: Optional[uuid.UUID] = Field(default=None, foreign_key="listing.id", index=True)
    channel: str = Field(max_length=10)  # email | sms
    audience: str = Field(max_length=20)  # landlord | visitor
    kind: str = Field(max_length=50)  # e.g. tour_request_received
    recipient: str = Field(max_length=254)
    status: str = Field(max_length=20)  # sent | failed | skipped
    detail: Optional[str] = Field(default=None)  # provider id or error / skip reason


class TourFeedback(TimestampMixin, table=True):
    """What the visitor thought, submitted through their private feedback link."""

    __tablename__ = "tour_feedback"

    tour_request_id: uuid.UUID = Field(foreign_key="tour_request.id", index=True, unique=True)
    rating: int  # 1-5
    interested: str = Field(max_length=10)  # yes | maybe | no
    liked: Optional[str] = Field(default=None, max_length=2000)
    concerns: Optional[str] = Field(default=None, max_length=2000)
