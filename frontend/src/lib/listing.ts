import type { ListingChannelType, ListingStatus, PetPolicy } from '../types';

export const PET_POLICY_LABELS: Record<PetPolicy, string> = {
  no_pets: 'No pets',
  cats_ok: 'Cats OK',
  dogs_ok: 'Dogs OK',
  cats_and_dogs_ok: 'Cats & dogs OK',
  case_by_case: 'Pets considered case by case',
};

export const CHANNEL_LABELS: Record<ListingChannelType, string> = {
  zillow_rental_manager: 'Zillow Rental Manager',
  facebook_marketplace: 'Facebook Marketplace',
  craigslist: 'Craigslist',
  apartments_com: 'Apartments.com',
  realtor_com: 'Realtor.com',
  hotpads: 'HotPads',
  mls: 'MLS',
  yard_sign: 'Yard sign',
  other: 'Other',
};

export const LISTING_STATUS_LABELS: Record<ListingStatus, string> = {
  draft: 'Draft',
  listed: 'Listed',
  closed: 'Closed',
};

export const listingStatusVariant = (s: ListingStatus) =>
  s === 'listed' ? 'green' : s === 'draft' ? 'yellow' : 'gray';

// US zones offered in the property form (stored as IANA names).
export const TIME_ZONES = [
  { value: 'America/Phoenix', label: 'Arizona (no daylight saving)' },
  { value: 'America/Los_Angeles', label: 'Pacific' },
  { value: 'America/Denver', label: 'Mountain' },
  { value: 'America/Chicago', label: 'Central' },
  { value: 'America/Detroit', label: 'Eastern (Michigan)' },
  { value: 'America/New_York', label: 'Eastern' },
  { value: 'America/Anchorage', label: 'Alaska' },
  { value: 'Pacific/Honolulu', label: 'Hawaii' },
];

/** Parse a YYYY-MM-DD date as a calendar date (no time-zone shift). */
export function formatCalendarDate(value?: string | null): string {
  if (!value) return '—';
  const [y, m, d] = value.split('-').map(Number);
  if (!y || !m || !d) return value;
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
