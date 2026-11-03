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
  submitTourRequest: (form: FormData) =>
    fetch(`${BASE}/tour-requests`, { method: 'POST', body: form }).then((r) =>
      parse<{ ok: boolean; when?: string }>(r),
    ),
};
