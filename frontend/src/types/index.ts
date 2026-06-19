// Types aligned to the FastAPI backend (app/models + app/schemas).
// Enum string unions mirror app/models/enums.py.

export interface Timestamped {
  id: string;
  created_at: string;
  updated_at: string;
}

export type PropertyType =
  | 'condo'
  | 'single_family'
  | 'multi_family'
  | 'townhouse'
  | 'apartment'
  | 'commercial';


export type LeaseStatus =
  | 'draft'
  | 'active'
  | 'pending_signature'
  | 'expired'
  | 'terminated'
  | 'broken';

export type PaymentType = 'rent' | 'deposit' | 'late_fee' | 'buyout' | 'other';
export type PaymentStatus = 'pending' | 'paid' | 'partial' | 'overdue' | 'refunded';

export interface Owner extends Timestamped {
  name: string;
  email?: string | null;
  phone?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  is_entity: boolean;
  tax_id?: string | null;
  notes?: string | null;
}

export interface ManagementCompany extends Timestamped {
  name: string;
  legal_name?: string | null;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  tax_id?: string | null;
  notes?: string | null;
}

export interface Jurisdiction extends Timestamped {
  state_code: string;
  state_name: string;
  name: string;
  early_termination_rules: Record<string, unknown>;
  statute_reference?: string | null;
}

export interface Property extends Timestamped {
  name: string;
  property_type: PropertyType;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  owner_id: string;
  management_company_id?: string | null;
  jurisdiction_id: string;
  hoa_id?: string | null;
  year_built?: number | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  square_feet?: number | null;
  hoa_name?: string | null;
  notes?: string | null;
}

export interface Tenant extends Timestamped {
  first_name: string;
  last_name: string;
  preferred_name?: string | null;
  email?: string | null;
  phone?: string | null;
  date_of_birth?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  notes?: string | null;
}

export interface HOA extends Timestamped {
  name: string;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  website?: string | null;
  management_company_name?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  dues_amount?: number | null;
  dues_frequency?: string | null;
  notes?: string | null;
}

export interface HOADocument extends Timestamped {
  hoa_id: string;
  name: string;
  doc_type: string;
  filename?: string | null;
  content_type?: string | null;
  file_size?: number | null;
  external_url?: string | null;
  uploaded_at: string;
  has_file: boolean;
}

// --- AI lease document import ---------------------------------------------

export interface ParsedTenant {
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  date_of_birth?: string | null;
  drivers_license?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  emergency_contact_relationship?: string | null;
  employer_name?: string | null;
  employer_phone?: string | null;
  job_title?: string | null;
  annual_income?: number | null;
  reference_name?: string | null;
  reference_phone?: string | null;
  reference_relationship?: string | null;
}

export interface ParsedLease {
  property_address?: string | null;
  unit_number?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  monthly_rent?: number | null;
  security_deposit?: number | null;
  late_fee?: number | null;
  late_fee_grace_days?: number | null;
  rent_due_day?: number | null;
  payment_frequency?: string | null;
  returned_check_fee?: number | null;
  lease_type?: string | null;
  renewal_terms?: string | null;
  deposit_held_location?: string | null;
  deposit_interest_rate?: number | null;
  utilities_included?: string | null;
  utilities_tenant_responsibility?: string | null;
  occupancy_limit?: number | null;
  pets_allowed?: boolean | null;
  pet_restrictions?: string | null;
  pet_deposit?: number | null;
  pet_monthly_fee?: number | null;
  parking_included?: boolean | null;
  parking_spaces?: number | null;
  parking_additional_fee?: number | null;
  no_smoking?: boolean | null;
  no_waterbeds?: boolean | null;
  quiet_hours?: string | null;
  lawn_maintenance_responsibility?: string | null;
  trash_service_included?: boolean | null;
  early_termination_allowed?: boolean | null;
  early_termination_penalty?: number | null;
  early_termination_notice_days?: number | null;
  special_conditions?: string | null;
}

export interface ParsedLeaseData {
  tenants: ParsedTenant[];
  lease: ParsedLease;
  confidence: 'high' | 'medium' | 'low' | string;
  notes?: string | null;
}

export interface ParseDocumentResult {
  document_id: string;
  parsed: ParsedLeaseData;
}

export interface CreateLeaseResult {
  lease_id: string;
  tenants_created: number;
  document_id?: string | null;
  message: string;
}

export interface Payment extends Timestamped {
  lease_id: string;
  payment_type: PaymentType;
  status: PaymentStatus;
  amount: number;
  amount_paid: number;
  due_date?: string | null;
  paid_date?: string | null;
  method?: string | null;
  reference?: string | null;
  notes?: string | null;
}

export interface Lease extends Timestamped {
  property_id: string;
  status: LeaseStatus;
  start_date: string;
  end_date: string;
  monthly_rent: number;
  security_deposit: number;
  late_fee: number;
  rent_due_day: number;
  grace_period_days: number;
  // Extended terms (document import)
  lease_type?: string | null;
  renewal_terms?: string | null;
  payment_frequency?: string | null;
  returned_check_fee?: number | null;
  deposit_held_location?: string | null;
  deposit_interest_rate?: number | null;
  utilities_included?: string | null;
  utilities_tenant_responsibility?: string | null;
  occupancy_limit?: number | null;
  pets_allowed?: boolean | null;
  pet_restrictions?: string | null;
  pet_deposit?: number | null;
  pet_monthly_fee?: number | null;
  parking_included?: boolean | null;
  parking_spaces?: number | null;
  parking_additional_fee?: number | null;
  no_smoking?: boolean | null;
  no_waterbeds?: boolean | null;
  quiet_hours?: string | null;
  lawn_maintenance_responsibility?: string | null;
  trash_service_included?: boolean | null;
  early_termination_allowed?: boolean | null;
  early_termination_penalty?: number | null;
  early_termination_notice_days?: number | null;
  special_conditions?: string | null;
  docusign_envelope_id?: string | null;
  signed_date?: string | null;
  notes?: string | null;
}

export interface LeaseDocument extends Timestamped {
  lease_id?: string | null;
  document_type: string;
  file_name: string;
  file_type?: string | null;
  file_size?: number | null;
  extraction_confidence?: string | null;
  extraction_notes?: string | null;
  uploaded_at: string;
  has_file: boolean;
}

// GET /leases/{id} returns the lease plus nested tenants + payments.
export interface LeaseDetail extends Lease {
  tenants: Tenant[];
  payments: Payment[];
}

// Sent on POST /leases (nested join rows).
export interface LeaseTenantInput {
  tenant_id: string;
  is_primary: boolean;
  is_guarantor: boolean;
}

// ---------------------------------------------------------------------------
// Lease-break workflow + email approvals.
// NOTE: these backend endpoints are not implemented yet (backend Milestones
// 5-6). The shapes below are the planned contract the UI is built against.
// ---------------------------------------------------------------------------

export type LeaseBreakStatus =
  | 'initiated'
  | 'options_presented'
  | 'option_selected'
  | 'documents_generated'
  | 'email_pending_approval'
  | 'email_approved'
  | 'email_sent'
  | 'out_for_signature'
  | 'signed'
  | 'completed'
  | 'cancelled';

export interface LeaseBreakRequest extends Timestamped {
  lease_id: string;
  status: LeaseBreakStatus;
  requested_date: string;
  desired_move_out_date: string;
  reason?: string | null;
  selected_option_id?: string | null;
  completed_at?: string | null;
}

export interface LeaseBreakOption extends Timestamped {
  lease_break_request_id: string;
  option_number: number;
  option_type: string;
  label: string;
  description?: string | null;
  terms?: string | null;
  is_selected: boolean;
  buyout_multiple?: number | null;
  monthly_rent_amount?: number | null;
  last_months_rent_held?: number | null;
  current_month_rent?: number | null;
  buyout_amount_gross?: number | null;
  last_month_credit?: number | null;
  cash_due_at_signing?: number | null;
  total_cash_collected?: number | null;
  security_deposit_held?: number | null;
  move_out_date?: string | null;
  final_rent_due_date?: string | null;
}

export interface LeaseBreakDocumentMeta extends Timestamped {
  lease_break_request_id: string;
  document_type: string;
  status: string;
  file_name: string;
  file_type?: string | null;
  has_file: boolean;
}

export interface LeaseBreakDetail {
  request: LeaseBreakRequest;
  options: LeaseBreakOption[];
  documents: LeaseBreakDocumentMeta[];
}

export type EmailApprovalStatus = 'draft' | 'approved' | 'sent' | 'failed' | 'rejected';

export interface EmailApproval extends Timestamped {
  lease_break_request_id?: string | null;
  status: EmailApprovalStatus;
  to_emails: string[];
  cc_emails: string[];
  subject: string;
  body_html: string;
  attachments: Array<Record<string, unknown>>;
  approved_by?: string | null;
}
