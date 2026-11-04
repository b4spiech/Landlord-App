"""Door codes per property: one-time tour codes, tenant codes and landlord codes."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime, Index, text
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import AccessCodeKind, AccessCodeStatus


class AccessCode(TimestampMixin, table=True):
    __tablename__ = "access_code"
    __table_args__ = (
        # The same code can't be live twice for one property (across all kinds).
        Index(
            "uq_access_code_active",
            "property_id",
            "code",
            unique=True,
            postgresql_where=text("status IN ('available', 'reserved', 'assigned', 'active')"),
        ),
    )

    property_id: uuid.UUID = Field(foreign_key="property.id", index=True)
    code: str = Field(max_length=32)
    kind: str = Field(default=AccessCodeKind.one_time.value, max_length=20, index=True,
                      sa_column_kwargs={"server_default": "one_time"})
    status: str = Field(default=AccessCodeStatus.available.value, max_length=20, index=True)
    note: Optional[str] = Field(default=None, max_length=200)
    # Last day the lock accepts this code (optional). Codes expiring before a
    # tour are never reserved for it.
    expires_on: Optional[date] = Field(default=None)

    tour_request_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tour_request.id", index=True)
    reserved_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    issued_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # Tenant codes: who it's assigned to.
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenant.id", index=True)
    assigned_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
