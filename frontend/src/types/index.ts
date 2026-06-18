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

export type UnitStatus = 'vacant' | 'occupied' | 'maintenance' | 'unavailable';

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
  year_built?: number | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  square_feet?: number | null;
  hoa_name?: string | null;
  notes?: string | null;
}

export interface Unit extends Timestamped {
  property_id: string;
  unit_number: string;
  status: UnitStatus;
  bedrooms?: number | null;
  bathrooms?: number | null;
  square_feet?: number | null;
  market_rent?: number | null;
  notes?: string | null;
}

export interface Tenant extends Timestamped {
  first_name: string;
  last_name: string;
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
  unit_id: string;
  property_id: string;
  status: LeaseStatus;
  start_date: string;
  end_date: string;
  monthly_rent: number;
  security_deposit: number;
  late_fee: number;
  rent_due_day: number;
  grace_period_days: number;
  docusign_envelope_id?: string | null;
  signed_date?: string | null;
  notes?: string | null;
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
  calculation_context: Record<string, unknown>;
}

export interface LeaseBreakOption extends Timestamped {
  lease_break_request_id: string;
  option_type: 'buyout' | 'relet' | 'sublet' | 'mutual_termination' | 'forfeit_deposit';
  label: string;
  description?: string | null;
  total_cost_to_tenant: number;
  months_charged?: number | null;
  line_items: Array<Record<string, unknown>>;
  is_compliant: boolean;
  compliance_note?: string | null;
  is_selected: boolean;
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
