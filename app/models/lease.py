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

    # Lease terms (often parsed from the document)
    lease_type: Optional[str] = Field(default=None, max_length=40, description="fixed-term | month-to-month")
    renewal_terms: Optional[str] = Field(default=None)
    payment_frequency: str = Field(default="monthly", max_length=20)
    returned_check_fee: Optional[float] = Field(default=None)

    # Deposit detail
    deposit_held_location: Optional[str] = Field(default=None, max_length=200)
    deposit_interest_rate: Optional[float] = Field(default=None)

    # Utilities
    utilities_included: Optional[str] = Field(default=None, description="e.g. water, trash")
    utilities_tenant_responsibility: Optional[str] = Field(default=None)

    # Occupancy & pets
    occupancy_limit: Optional[int] = Field(default=None)
    pets_allowed: Optional[bool] = Field(default=None)
    pet_restrictions: Optional[str] = Field(default=None)
    pet_deposit: Optional[float] = Field(default=None)
    pet_monthly_fee: Optional[float] = Field(default=None)

    # Parking
    parking_included: Optional[bool] = Field(default=None)
    parking_spaces: Optional[int] = Field(default=None)
    parking_additional_fee: Optional[float] = Field(default=None)

    # House rules
    no_smoking: Optional[bool] = Field(default=None)
    no_waterbeds: Optional[bool] = Field(default=None)
    quiet_hours: Optional[str] = Field(default=None, max_length=100)

    # Maintenance
    lawn_maintenance_responsibility: Optional[str] = Field(default=None, max_length=40)
    trash_service_included: Optional[bool] = Field(default=None)

    # Early termination
    early_termination_allowed: Optional[bool] = Field(default=None)
    early_termination_penalty: Optional[float] = Field(default=None)
    early_termination_notice_days: Optional[int] = Field(default=None)

    special_conditions: Optional[str] = Field(default=None)

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
