import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import TimestampedRead


class InitiateLeaseBreakRequest(BaseModel):
    lease_id: str
    desired_move_out_date: str  # YYYY-MM-DD
    reason: Optional[str] = None


class CalculateOptionsRequest(BaseModel):
    move_out_date: str  # YYYY-MM-DD
    last_months_rent_held: Optional[float] = None  # defaults to monthly rent
    buyout_multiple: Optional[float] = None  # joint buyout multiple, default 3.0


class SelectOptionRequest(BaseModel):
    option_id: str
    tenant_id: Optional[str] = None


class GenerateAgreementRequest(BaseModel):
    option_id: str


class RouteForSignatureRequest(BaseModel):
    document_id: Optional[str] = None  # defaults to the most recent generated agreement


class RouteForSignatureResult(BaseModel):
    envelope_id: str
    status: str = "sent"


class LeaseBreakOptionRead(TimestampedRead):
    lease_break_request_id: uuid.UUID
    option_number: int
    option_type: str
    label: str
    description: Optional[str] = None
    terms: Optional[str] = None
    is_selected: bool
    is_compliant: bool
    compliance_note: Optional[str] = None

    buyout_multiple: Optional[float] = None
    monthly_rent_amount: Optional[float] = None
    last_months_rent_held: Optional[float] = None
    current_month_rent: Optional[float] = None
    buyout_amount_gross: Optional[float] = None
    last_month_credit: Optional[float] = None
    cash_due_at_signing: Optional[float] = None
    total_cash_collected: Optional[float] = None
    security_deposit_held: Optional[float] = None
    move_out_date: Optional[str] = None
    final_rent_due_date: Optional[str] = None


class LeaseBreakDocumentRead(TimestampedRead):
    lease_break_request_id: uuid.UUID
    document_type: str
    status: str
    file_name: str
    file_type: Optional[str] = None
    has_file: bool = False


class LeaseBreakRequestRead(TimestampedRead):
    lease_id: uuid.UUID
    status: str
    requested_date: date
    desired_move_out_date: date
    reason: Optional[str] = None
    selected_option_id: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None


class LeaseBreakDetail(BaseModel):
    request: LeaseBreakRequestRead
    options: list[LeaseBreakOptionRead] = []
    documents: list[LeaseBreakDocumentRead] = []
