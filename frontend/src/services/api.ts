import axios from 'axios';
import type { AxiosResponse } from 'axios';
import type {
  CreateLeaseResult,
  EmailApproval,
  HOA,
  HOADocument,
  Jurisdiction,
  Lease,
  LeaseBreakOption,
  LeaseBreakRequest,
  LeaseDetail,
  LeaseDocument,
  ManagementCompany,
  Owner,
  ParseDocumentResult,
  ParsedLeaseData,
  Property,
  Tenant,
  Unit,
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

export const unitAPI = {
  list: (params?: { property_id?: string }) => data<Unit[]>(api.get('/units', { params })),
  get: (id: string) => data<Unit>(api.get(`/units/${id}`)),
  create: (body: Partial<Unit>) => data<Unit>(api.post('/units', body)),
  update: (id: string, body: Partial<Unit>) => data<Unit>(api.patch(`/units/${id}`, body)),
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
  list: (params?: { property_id?: string; unit_id?: string; status_filter?: string }) =>
    data<Lease[]>(api.get('/leases', { params })),
  get: (id: string) => data<LeaseDetail>(api.get(`/leases/${id}`)),
  create: (body: LeaseCreateInput) => data<LeaseDetail>(api.post('/leases', body)),
  update: (id: string, body: Partial<Lease>) =>
    data<LeaseDetail>(api.patch(`/leases/${id}`, body)),
};

export interface CreateFromParsedBody {
  parsed: ParsedLeaseData;
  property_id: string;
  unit_id: string;
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

// ---------------------------------------------------------------------------
// Planned endpoints (backend Milestones 5-6) — will 404 until implemented.
// ---------------------------------------------------------------------------

export const leaseBreakAPI = {
  initiate: (body: { lease_id: string; desired_move_out_date: string; reason?: string }) =>
    data<LeaseBreakRequest>(api.post('/lease-breaks/initiate', body)),
  get: (requestId: string) => data<LeaseBreakRequest>(api.get(`/lease-breaks/${requestId}`)),
  presentOptions: (requestId: string, body: unknown) =>
    data<{ options: LeaseBreakOption[] }>(
      api.post(`/lease-breaks/${requestId}/present-options`, body),
    ),
  selectOption: (requestId: string, body: { option_id: string }) =>
    data<LeaseBreakRequest>(api.post(`/lease-breaks/${requestId}/select-option`, body)),
  getDocuments: (requestId: string) =>
    data<unknown[]>(api.get(`/lease-breaks/${requestId}/documents`)),
  approveEmail: (requestId: string, body?: unknown) =>
    data<EmailApproval>(api.post(`/lease-breaks/${requestId}/approve-email`, body)),
  routeForSignature: (requestId: string, body?: unknown) =>
    data<{ envelope_id: string }>(api.post(`/lease-breaks/${requestId}/route-for-signature`, body)),
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
