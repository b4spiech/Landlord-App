from typing import Optional

from pydantic import BaseModel


class ParsedTenant(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    drivers_license: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    employer_name: Optional[str] = None
    employer_phone: Optional[str] = None
    job_title: Optional[str] = None
    annual_income: Optional[float] = None
    reference_name: Optional[str] = None
    reference_phone: Optional[str] = None
    reference_relationship: Optional[str] = None


class ParsedLease(BaseModel):
    property_address: Optional[str] = None
    unit_number: Optional[str] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    late_fee: Optional[float] = None
    late_fee_grace_days: Optional[int] = None
    rent_due_day: Optional[int] = None
    payment_frequency: Optional[str] = None
    returned_check_fee: Optional[float] = None
    lease_type: Optional[str] = None
    renewal_terms: Optional[str] = None
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


class ParsedLeaseData(BaseModel):
    tenants: list[ParsedTenant] = []
    lease: ParsedLease = ParsedLease()
    confidence: str = "low"  # high | medium | low
    notes: Optional[str] = None


# --- create-from-parsed / create-manual request bodies ----------------------


class CreateFromParsedRequest(BaseModel):
    parsed: ParsedLeaseData
    property_id: str
    unit_id: str
    management_company_id: Optional[str] = None
    jurisdiction_id: Optional[str] = None
    document_id: Optional[str] = None  # links the already-uploaded document


class CreateResult(BaseModel):
    lease_id: str
    tenants_created: int
    document_id: Optional[str] = None
    message: str
