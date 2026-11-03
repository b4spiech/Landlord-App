// Anonymous API client for the public site. Talks only to /api/v1/public/*.
import type { PublicListing } from '../types';

const BASE = (import.meta.env.VITE_API_URL || '/api/v1') + '/public';

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
    throw new Error(detail || `Something went wrong (${res.status}). Please try again.`);
  }
  return res.json();
}

const get = <T>(path: string) => fetch(BASE + path).then((r) => parse<T>(r));
const post = <T>(path: string, body: unknown) =>
  fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((r) => parse<T>(r));

export interface Slot {
  time: string; // "HH:MM", home's local time
  available: boolean;
}

export const publicApi = {
  listings: () => get<PublicListing[]>('/listings'),
  listing: (id: string) => get<PublicListing>(`/listings/${id}`),
  availability: (listingId: string, day: string) =>
    get<{ time_zone: string; date: string; slots: Slot[] }>(
      `/listings/${listingId}/availability?day=${encodeURIComponent(day)}`,
    ),
  feedbackInfo: (token: string) =>
    get<{ first_name: string; home: string; when: string; submitted: boolean }>(
      `/feedback/${encodeURIComponent(token)}`,
    ),
  submitFeedback: (
    token: string,
    body: { rating: number; interested: 'yes' | 'maybe' | 'no'; liked?: string; concerns?: string },
  ) =>
    fetch(`${BASE}/feedback/${encodeURIComponent(token)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then((r) => parse<{ ok: boolean }>(r)),
  // Email sign-in (required before requesting a tour). Cookies are same-origin.
  me: () =>
    fetch(`${BASE}/auth/me`).then(
      (r) => (r.ok ? r.json() : null) as Promise<{ email: string } | null>,
    ),
  startSignIn: (email: string) => post<{ ok: boolean }>('/auth/start', { email }),
  verifySignIn: (email: string, code: string) =>
    post<{ email: string }>('/auth/verify', { email, code }),
  signOut: () => post<{ ok: boolean }>('/auth/logout', {}),
  submitTourRequest: (form: FormData) =>
    fetch(`${BASE}/tour-requests`, { method: 'POST', body: form }).then((r) =>
      parse<{ ok: boolean; when?: string }>(r),
    ),
};
