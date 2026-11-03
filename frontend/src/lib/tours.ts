import type { TourRequestStatus } from '../types';

export const tourStatusVariant = (s: TourRequestStatus) =>
  s === 'pending' ? 'yellow' : s === 'approved' ? 'green' : s === 'declined' ? 'red' : 'gray';

export const formatPhone = (e164: string) => {
  const d = e164.replace(/\D/g, '').slice(-10);
  return d.length === 10 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}` : e164;
};
