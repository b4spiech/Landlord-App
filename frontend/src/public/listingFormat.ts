import type { PublicListing } from '../types';

export const money = (v?: number | null) =>
  v == null
    ? '—'
    : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v);

export const address = (l: PublicListing) =>
  `${l.address_line1}${l.address_line2 ? ', ' + l.address_line2 : ''}, ${l.city}, ${l.state} ${l.postal_code}`;

export const specs = (l: PublicListing) =>
  [
    l.bedrooms != null && `${l.bedrooms} bd`,
    l.bathrooms != null && `${l.bathrooms} ba`,
    l.square_feet != null && `${l.square_feet.toLocaleString()} sq ft`,
  ]
    .filter(Boolean)
    .join(' · ');

/** "Available now" for past/today dates, else "Available Dec 1, 2026". */
export const availability = (date?: string | null) => {
  if (!date) return null;
  const [y, m, d] = date.split('-').map(Number);
  const when = new Date(y, m - 1, d);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return when <= today
    ? 'Available now'
    : `Available ${when.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
};
