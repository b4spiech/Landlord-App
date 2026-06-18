import uuid
from datetime import date
from typing import Optional

from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import LeaseStatus


class Lease(TimestampMixin, table=True):
    __tablename__ = "lease"

    unit_id: uuid.UUID = Field(foreign_key="unit.id", index=True)
    property_id: uuid.UUID = Field(foreign_key="property.id", index=True)

    status: str = Field(default=LeaseStatus.draft.value, max_length=30, index=True)

    start_date: date = Field()
    end_date: date = Field()

    monthly_rent: float = Field(description="Base monthly rent in USD")
    security_deposit: float = Field(default=0.0)
    late_fee: float = Field(default=0.0)
    rent_due_day: int = Field(default=1, description="Day of month rent is due")
    grace_period_days: int = Field(default=5)

    # Cached signing state
    docusign_envelope_id: Optional[str] = Field(default=None, max_length=100)
    signed_date: Optional[date] = Field(default=None)

    notes: Optional[str] = Field(default=None)


class LeaseTenant(TimestampMixin, table=True):
    """Join table linking tenants to a lease (a lease may have co-signers)."""

    __tablename__ = "lease_tenant"

    lease_id: uuid.UUID = Field(foreign_key="lease.id", index=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

    is_primary: bool = Field(default=False)
    is_guarantor: bool = Field(default=False)
