from enum import Enum


class PropertyType(str, Enum):
    condo = "condo"
    single_family = "single_family"
    multi_family = "multi_family"
    townhouse = "townhouse"
    apartment = "apartment"
    commercial = "commercial"


class UnitStatus(str, Enum):
    vacant = "vacant"
    occupied = "occupied"
    maintenance = "maintenance"
    unavailable = "unavailable"


class LeaseStatus(str, Enum):
    draft = "draft"
    active = "active"
    pending_signature = "pending_signature"
    expired = "expired"
    terminated = "terminated"
    broken = "broken"


class PaymentType(str, Enum):
    rent = "rent"
    deposit = "deposit"
    late_fee = "late_fee"
    buyout = "buyout"
    other = "other"


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    partial = "partial"
    overdue = "overdue"
    refunded = "refunded"


class ExpenseCategory(str, Enum):
    maintenance = "maintenance"
    repair = "repair"
    utilities = "utilities"
    insurance = "insurance"
    taxes = "taxes"
    hoa = "hoa"
    management = "management"
    other = "other"


class TemplateType(str, Enum):
    buyout_options_email = "buyout_options_email"
    termination_agreement = "termination_agreement"
    move_out_statement = "move_out_statement"
    lease_agreement = "lease_agreement"
    notice = "notice"


class LeaseBreakStatus(str, Enum):
    """State machine for the lease break workflow."""

    initiated = "initiated"
    options_presented = "options_presented"
    option_selected = "option_selected"
    documents_generated = "documents_generated"
    email_pending_approval = "email_pending_approval"
    email_approved = "email_approved"
    email_sent = "email_sent"
    out_for_signature = "out_for_signature"
    signed = "signed"
    completed = "completed"
    cancelled = "cancelled"


class LeaseBreakOptionType(str, Enum):
    buyout = "buyout"
    relet = "relet"
    sublet = "sublet"
    mutual_termination = "mutual_termination"
    forfeit_deposit = "forfeit_deposit"


class DocumentType(str, Enum):
    termination_agreement = "termination_agreement"
    move_out_statement = "move_out_statement"
    buyout_addendum = "buyout_addendum"
    other = "other"


class DocumentStatus(str, Enum):
    generated = "generated"
    sent_for_signature = "sent_for_signature"
    signed = "signed"
    voided = "voided"


class EmailApprovalStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    sent = "sent"
    failed = "failed"
    rejected = "rejected"


class EnvelopeStatus(str, Enum):
    created = "created"
    sent = "sent"
    delivered = "delivered"
    completed = "completed"
    declined = "declined"
    voided = "voided"
