import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.models.enums import LeaseStatus, PaymentStatus, PaymentType
from app.schemas.common import ORMModel, TimestampedRead
from app.schemas.tenant import TenantRead


class LeaseTenantCreate(BaseModel):
    tenant_id: uuid.UUID
    is_primary: bool = False
    is_guarantor: bool = False


class LeaseTenantRead(TimestampedRead):
    lease_id: uuid.UUID
    tenant_id: uuid.UUID
    is_primary: bool
    is_guarantor: bool


class PaymentRead(TimestampedRead):
    lease_id: uuid.UUID
    payment_type: PaymentType
    status: PaymentStatus
    amount: float
    amount_paid: float
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    method: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class LeaseBase(BaseModel):
    unit_id: uuid.UUID
    property_id: uuid.UUID
    status: LeaseStatus = LeaseStatus.draft
    start_date: date
    end_date: date
    monthly_rent: float
    security_deposit: float = 0.0
    late_fee: float = 0.0
    rent_due_day: int = 1
    grace_period_days: int = 5
    notes: Optional[str] = None


class LeaseCreate(LeaseBase):
    lease_tenants: list[LeaseTenantCreate] = []


class LeaseUpdate(BaseModel):
    unit_id: Optional[uuid.UUID] = None
    property_id: Optional[uuid.UUID] = None
    status: Optional[LeaseStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    late_fee: Optional[float] = None
    rent_due_day: Optional[int] = None
    grace_period_days: Optional[int] = None
    signed_date: Optional[date] = None
    docusign_envelope_id: Optional[str] = None
    notes: Optional[str] = None


class LeaseRead(LeaseBase, TimestampedRead):
    docusign_envelope_id: Optional[str] = None
    signed_date: Optional[date] = None


class LeaseTenantWithTenant(ORMModel):
    is_primary: bool
    is_guarantor: bool
    tenant: TenantRead


class LeaseDetailRead(LeaseRead):
    tenants: list[TenantRead] = []
    payments: list[PaymentRead] = []
