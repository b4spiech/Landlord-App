// Anonymous API client for the public site. Talks only to /api/v1/public/*.
import type { PublicListing } from '../types';

const BASE = (import.meta.env.VITE_API_URL || '/api/v1') + '/public';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const publicApi = {
  listings: () => get<PublicListing[]>('/listings'),
  listing: (id: string) => get<PublicListing>(`/listings/${id}`),
};
