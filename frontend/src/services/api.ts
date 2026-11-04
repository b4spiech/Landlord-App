import axios from 'axios';
import type { AxiosResponse } from 'axios';
import type {
  AccessCode,
  AccessCodeKind,
  AccessCodeList,
  ManagedCodes,
  CreateLeaseResult,
  EmailApproval,
  HOA,
  HOADocument,
  Jurisdiction,
  Lease,
  LeaseBreakDetail,
  LeaseBreakDocumentMeta,
  LeaseBreakOption,
  LeaseBreakRequest,
  LeaseDetail,
  LeaseDocument,
  Listing,
  ListingCloseReason,
  ListingFields,
  ListingPhoto,
  ManagementCompany,
  NotificationEntry,
  TourRequest,
  TourRequestStatus,
  Owner,
  ParseDocumentResult,
  ParsedLeaseData,
  Property,
  Tenant,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach a Cloudflare Access token if one was stored (no-op otherwise).
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cf_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Pull a human-readable message out of an Axios error for toasts.
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    return err.message;
  }
  return err instanceof Error ? err.message : 'Unexpected error';
}

const data = <T>(p: Promise<AxiosResponse<T>>): Promise<T> => p.then((r) => r.data);

export const ownerAPI = {
  list: () => data<Owner[]>(api.get('/owners')),
  get: (id: string) => data<Owner>(api.get(`/owners/${id}`)),
  create: (body: Partial<Owner>) => data<Owner>(api.post('/owners', body)),
  update: (id: string, body: Partial<Owner>) => data<Owner>(api.patch(`/owners/${id}`, body)),
};

export const managementCompanyAPI = {
  list: () => data<ManagementCompany[]>(api.get('/management-companies')),
  get: (id: string) => data<ManagementCompany>(api.get(`/management-companies/${id}`)),
  create: (body: Partial<ManagementCompany>) =>
    data<ManagementCompany>(api.post('/management-companies', body)),
  update: (id: string, body: Partial<ManagementCompany>) =>
    data<ManagementCompany>(api.patch(`/management-companies/${id}`, body)),
};

export const propertyAPI = {
  list: (params?: { owner_id?: string; management_company_id?: string }) =>
    data<Property[]>(api.get('/properties', { params })),
  get: (id: string) => data<Property>(api.get(`/properties/${id}`)),
  create: (body: Partial<Property>) => data<Property>(api.post('/properties', body)),
  update: (id: string, body: Partial<Property>) =>
    data<Property>(api.patch(`/properties/${id}`, body)),
};

export const propertyPhotoAPI = {
  photoUrl: (propertyId: string) => `${API_URL}/properties/${propertyId}/photo`,
  upload: (propertyId: string, form: FormData) =>
    data<{ ok: boolean }>(
      api.post(`/properties/${propertyId}/photo`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    ),
  remove: (propertyId: string) => api.delete(`/properties/${propertyId}/photo`),
};

export const listingAPI = {
  list: (params?: { property_id?: string; status_filter?: string; open_only?: boolean }) =>
    data<Listing[]>(api.get('/listings', { params })),
  get: (id: string) => data<Listing>(api.get(`/listings/${id}`)),
  create: (body: ListingFields & { property_id: string; publish?: boolean }) =>
    data<Listing>(api.post('/listings', body)),
  update: (id: string, body: ListingFields) => data<Listing>(api.patch(`/listings/${id}`, body)),
  publish: (id: string) => data<Listing>(api.post(`/listings/${id}/publish`)),
  unpublish: (id: string) => data<Listing>(api.post(`/listings/${id}/unpublish`)),
  close: (id: string, reason: ListingCloseReason) =>
    data<Listing>(api.post(`/listings/${id}/close`, { reason })),
  photos: (id: string) => data<ListingPhoto[]>(api.get(`/listings/${id}/photos`)),
  photoUrl: (id: string, photoId: string) => `${API_URL}/listings/${id}/photos/${photoId}`,
  uploadPhotos: (id: string, files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    return data<ListingPhoto[]>(
      api.post(`/listings/${id}/photos`, form, { headers: { 'Content-Type': 'multipart/form-data' } }),
    );
  },
  reorderPhotos: (id: string, photoIds: string[]) =>
    data<ListingPhoto[]>(api.put(`/listings/${id}/photos/order`, { photo_ids: photoIds })),
  deletePhoto: (id: string, photoId: string) => api.delete(`/listings/${id}/photos/${photoId}`),
};

export const accessCodeAPI = {
  list: (propertyId: string, history = false) =>
    data<AccessCodeList>(api.get(`/properties/${propertyId}/access-codes`, { params: { history } })),
  managed: (propertyId: string) => data<ManagedCodes>(api.get(`/properties/${propertyId}/access-codes/managed`)),
  assign: (codeId: string, tenantId: string) =>
    data<AccessCode>(api.post(`/access-codes/${codeId}/assign`, { tenant_id: tenantId })),
  unassign: (codeId: string) => data<AccessCode>(api.post(`/access-codes/${codeId}/unassign`)),
  add: (
    propertyId: string,
    body: { codes: string; kind?: AccessCodeKind; expires_on?: string | null; note?: string | null },
  ) =>
    data<{ added: number; duplicates: string[]; invalid: string[] }>(
      api.post(`/properties/${propertyId}/access-codes`, body),
    ),
  remove: (codeId: string) => api.delete(`/access-codes/${codeId}`),
};

export type DeletableKind =
  | 'properties'
  | 'hoas'
  | 'owners'
  | 'management-companies'
  | 'tenants'
  | 'leases'
  | 'lease-breaks';

export interface DeletePreview {
  kind: string;
  name: string;
  can_delete: boolean;
  blockers: string[];
  also_deletes: string[];
  unlinks: string[];
}

export const deleteAPI = {
  preview: (kind: DeletableKind, id: string) => data<DeletePreview>(api.get(`/${kind}/${id}/delete-preview`)),
  remove: (kind: DeletableKind, id: string) => api.delete(`/${kind}/${id}`),
};

export const tourRequestAPI = {
  list: (params?: { status_filter?: TourRequestStatus; property_id?: string }) =>
    data<TourRequest[]>(api.get('/tour-requests', { params })),
  get: (id: string) => data<TourRequest>(api.get(`/tour-requests/${id}`)),
  notifications: (id: string) => data<NotificationEntry[]>(api.get(`/tour-requests/${id}/notifications`)),
  idPhotoUrl: (id: string) => `${API_URL}/tour-requests/${id}/id-photo`,
  approve: (id: string, note?: string) => data<TourRequest>(api.post(`/tour-requests/${id}/approve`, { note })),
  decline: (id: string, note?: string) => data<TourRequest>(api.post(`/tour-requests/${id}/decline`, { note })),
  cancel: (id: string, note?: string) => data<TourRequest>(api.post(`/tour-requests/${id}/cancel`, { note })),
  sendCode: (id: string) => data<TourRequest>(api.post(`/tour-requests/${id}/send-code`)),
};

export const tenantAPI = {
  list: () => data<Tenant[]>(api.get('/tenants')),
  get: (id: string) => data<Tenant>(api.get(`/tenants/${id}`)),
  create: (body: Partial<Tenant>) => data<Tenant>(api.post('/tenants', body)),
  update: (id: string, body: Partial<Tenant>) => data<Tenant>(api.patch(`/tenants/${id}`, body)),
};

export interface LeaseCreateInput extends Partial<Lease> {
  lease_tenants?: Array<{ tenant_id: string; is_primary: boolean; is_guarantor: boolean }>;
}

export const leaseAPI = {
  list: (params?: { property_id?: string; status_filter?: string }) =>
    data<Lease[]>(api.get('/leases', { params })),
  get: (id: string) => data<LeaseDetail>(api.get(`/leases/${id}`)),
  create: (body: LeaseCreateInput) => data<LeaseDetail>(api.post('/leases', body)),
  update: (id: string, body: Partial<Lease>) =>
    data<LeaseDetail>(api.patch(`/leases/${id}`, body)),
};

export interface CreateFromParsedBody {
  parsed: ParsedLeaseData;
  property_id: string;
  management_company_id?: string | null;
  jurisdiction_id?: string | null;
  document_id?: string | null;
}

export const leaseImportAPI = {
  parseDocument: (fileForm: FormData) =>
    data<ParseDocumentResult>(
      api.post('/leases/parse-document', fileForm, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000, // parsing can take up to ~2 min
      }),
    ),
  createFromParsed: (body: CreateFromParsedBody) =>
    data<CreateLeaseResult>(api.post('/leases/create-from-parsed', body)),
  createManual: (body: CreateFromParsedBody) =>
    data<CreateLeaseResult>(api.post('/leases/create-manual', body)),
};

export const leaseDocumentAPI = {
  list: (leaseId: string) => data<LeaseDocument[]>(api.get(`/leases/${leaseId}/documents`)),
  downloadUrl: (leaseId: string, docId: string) =>
    `${API_URL}/leases/${leaseId}/documents/${docId}/download`,
};

export const jurisdictionAPI = {
  list: () => data<Jurisdiction[]>(api.get('/jurisdictions')),
};

export const hoaAPI = {
  list: () => data<HOA[]>(api.get('/hoas')),
  get: (id: string) => data<HOA>(api.get(`/hoas/${id}`)),
  create: (body: Partial<HOA>) => data<HOA>(api.post('/hoas', body)),
  update: (id: string, body: Partial<HOA>) => data<HOA>(api.patch(`/hoas/${id}`, body)),
  remove: (id: string) => api.delete(`/hoas/${id}`),
};

export const hoaDocumentAPI = {
  list: (hoaId: string) => data<HOADocument[]>(api.get(`/hoas/${hoaId}/documents`)),
  upload: (hoaId: string, form: FormData) =>
    data<HOADocument>(
      api.post(`/hoas/${hoaId}/documents`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    ),
  // Absolute path so a regular <a href> / window.open downloads through the
  // same origin the SPA is served from.
  downloadUrl: (hoaId: string, docId: string) =>
    `${API_URL}/hoas/${hoaId}/documents/${docId}/download`,
  remove: (hoaId: string, docId: string) => api.delete(`/hoas/${hoaId}/documents/${docId}`),
};

export interface LeaseBreakSummary {
  id: string;
  created_at: string;
  lease_id: string;
  property_id: string;
  property_name: string;
  tenant_names: string;
  status: string;
  requested_date: string;
  desired_move_out_date: string;
  selected_option_label?: string | null;
  cash_due_at_signing?: number | null;
  has_signed_agreement: boolean;
}

export const leaseBreakAPI = {
  list: (params?: { lease_id?: string }) => data<LeaseBreakSummary[]>(api.get('/lease-breaks', { params })),
  initiate: (body: { lease_id: string; desired_move_out_date: string; reason?: string }) =>
    data<LeaseBreakRequest>(api.post('/lease-breaks/initiate', body)),
  get: (requestId: string) => data<LeaseBreakDetail>(api.get(`/lease-breaks/${requestId}`)),
  calculateOptions: (
    requestId: string,
    body: { move_out_date: string; last_months_rent_held?: number; buyout_multiple?: number },
  ) => data<LeaseBreakOption[]>(api.post(`/lease-breaks/${requestId}/calculate-options`, body)),
  selectOption: (requestId: string, body: { option_id: string; tenant_id?: string }) =>
    data<LeaseBreakOption>(api.post(`/lease-breaks/${requestId}/select-option`, body)),
  generateAgreement: (requestId: string, body: { option_id: string }) =>
    data<LeaseBreakDocumentMeta>(api.post(`/lease-breaks/${requestId}/generate-agreement`, body)),
  documentDownloadUrl: (requestId: string, docId: string) =>
    `${API_URL}/lease-breaks/${requestId}/documents/${docId}/download`,
  routeForSignature: (requestId: string, body: { document_id?: string }) =>
    data<{ envelope_id: string; status: string }>(
      api.post(`/lease-breaks/${requestId}/route-for-signature`, body),
    ),
  emailPreview: (requestId: string, optionId: string) =>
    data<{ subject: string; body_html: string; to_emails: string[]; configured: boolean }>(
      api.get(`/lease-breaks/${requestId}/email-preview`, { params: { option_id: optionId } }),
    ),
  sendEmail: (requestId: string, body: { option_id: string; attach_document_id?: string }) =>
    data<{ sent: boolean; to_emails: string[] }>(
      api.post(`/lease-breaks/${requestId}/send-email`, body),
    ),
};

export const emailApprovalAPI = {
  list: () => data<EmailApproval[]>(api.get('/email-approvals')),
  get: (id: string) => data<EmailApproval>(api.get(`/email-approvals/${id}`)),
  approve: (id: string, body?: unknown) =>
    data<EmailApproval>(api.post(`/email-approvals/${id}/approve`, body)),
  reject: (id: string, reason: string) =>
    data<EmailApproval>(api.post(`/email-approvals/${id}/reject`, { reason })),
};

export default api;
