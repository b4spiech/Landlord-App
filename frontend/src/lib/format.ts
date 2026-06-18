import type { LeaseStatus, PropertyType, UnitStatus } from '../types';

export function formatCurrency(value?: number | null): string {
  if (value == null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDate(value?: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function titleCase(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function propertyTypeLabel(t: PropertyType): string {
  return titleCase(t);
}

type Variant = 'green' | 'blue' | 'yellow' | 'red' | 'gray';

export function leaseStatusVariant(status: LeaseStatus): Variant {
  switch (status) {
    case 'active':
      return 'green';
    case 'pending_signature':
      return 'yellow';
    case 'draft':
      return 'blue';
    case 'terminated':
    case 'broken':
      return 'red';
    case 'expired':
      return 'gray';
    default:
      return 'gray';
  }
}

export function unitStatusVariant(status: UnitStatus): Variant {
  switch (status) {
    case 'occupied':
      return 'green';
    case 'vacant':
      return 'blue';
    case 'maintenance':
      return 'yellow';
    default:
      return 'gray';
  }
}
