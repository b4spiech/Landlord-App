"""One-time door codes per property (loaded from the lock's app by the landlord)."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime, Index, text
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import AccessCodeStatus


class AccessCode(TimestampMixin, table=True):
    __tablename__ = "access_code"
    __table_args__ = (
        # The same code can't be in the active pool twice for one property.
        Index(
            "uq_access_code_active",
            "property_id",
            "code",
            unique=True,
            postgresql_where=text("status IN ('available', 'reserved')"),
        ),
    )

    property_id: uuid.UUID = Field(foreign_key="property.id", index=True)
    code: str = Field(max_length=32)
    status: str = Field(default=AccessCodeStatus.available.value, max_length=20, index=True)
    note: Optional[str] = Field(default=None, max_length=200)
    # Last day the lock accepts this code (optional). Codes expiring before a
    # tour are never reserved for it.
    expires_on: Optional[date] = Field(default=None)

    tour_request_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tour_request.id", index=True)
    reserved_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    issued_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
