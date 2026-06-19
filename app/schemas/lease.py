import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import LeaseStatus, PaymentStatus, PaymentType
from app.schemas.common import ORMModel, TimestampedRead
from app.schemas.tenant import TenantRead


class LeaseDocumentRead(TimestampedRead):
    lease_id: Optional[uuid.UUID] = None
    document_type: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    extraction_confidence: Optional[str] = None
    extraction_notes: Optional[str] = None
    uploaded_at: datetime
    has_file: bool = False


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
    # Extended terms (often from document import)
    lease_type: Optional[str] = None
    renewal_terms: Optional[str] = None
    payment_frequency: Optional[str] = None
    returned_check_fee: Optional[float] = None
    deposit_held_location: Optional[str] = None
    deposit_interest_rate: Optional[float] = None
    utilities_included: Optional[str] = None
    utilities_tenant_responsibility: Optional[str] = None
    occupancy_limit: Optional[int] = None
    pets_allowed: Optional[bool] = None
    pet_restrictions: Optional[str] = None
    pet_deposit: Optional[float] = None
    pet_monthly_fee: Optional[float] = None
    parking_included: Optional[bool] = None
    parking_spaces: Optional[int] = None
    parking_additional_fee: Optional[float] = None
    no_smoking: Optional[bool] = None
    no_waterbeds: Optional[bool] = None
    quiet_hours: Optional[str] = None
    lawn_maintenance_responsibility: Optional[str] = None
    trash_service_included: Optional[bool] = None
    early_termination_allowed: Optional[bool] = None
    early_termination_penalty: Optional[float] = None
    early_termination_notice_days: Optional[int] = None
    special_conditions: Optional[str] = None
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
    # Extended terms (editable post-import)
    lease_type: Optional[str] = None
    renewal_terms: Optional[str] = None
    payment_frequency: Optional[str] = None
    returned_check_fee: Optional[float] = None
    deposit_held_location: Optional[str] = None
    deposit_interest_rate: Optional[float] = None
    utilities_included: Optional[str] = None
    utilities_tenant_responsibility: Optional[str] = None
    occupancy_limit: Optional[int] = None
    pets_allowed: Optional[bool] = None
    pet_restrictions: Optional[str] = None
    pet_deposit: Optional[float] = None
    pet_monthly_fee: Optional[float] = None
    parking_included: Optional[bool] = None
    parking_spaces: Optional[int] = None
    parking_additional_fee: Optional[float] = None
    no_smoking: Optional[bool] = None
    no_waterbeds: Optional[bool] = None
    quiet_hours: Optional[str] = None
    lawn_maintenance_responsibility: Optional[str] = None
    trash_service_included: Optional[bool] = None
    early_termination_allowed: Optional[bool] = None
    early_termination_penalty: Optional[float] = None
    early_termination_notice_days: Optional[int] = None
    special_conditions: Optional[str] = None
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
