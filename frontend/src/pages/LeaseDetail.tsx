import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { leaseAPI, leaseDocumentAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { Lease } from '../types';
import { Button, Card, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { LeaseEditForm } from '../components/LeaseEditForm';
import { TenantForm } from '../components/TenantForm';
import { StatusBadge } from '../components/StatusBadge';
import type { Tenant } from '../types';
import { formatCurrency, formatDate, leaseStatusVariant, titleCase } from '../lib/format';

function humanSize(bytes?: number | null): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const yesNo = (v?: boolean | null) => (v == null ? '—' : v ? 'Yes' : 'No');

export const LeaseDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [editOpen, setEditOpen] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const { data, loading, error, reload } = useAsync(async () => {
    const lease = await leaseAPI.get(id!);
    const documents = await leaseDocumentAPI.list(id!);
    return { lease, documents };
  }, [id]);

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const { lease, documents } = data;

  // Curated terms to display (label, value), skipping empties.
  const terms: [string, string | number | null | undefined][] = [
    ['Lease type', lease.lease_type && titleCase(lease.lease_type)],
    ['Payment frequency', lease.payment_frequency && titleCase(lease.payment_frequency)],
    ['Rent due day', lease.rent_due_day],
    ['Late fee', lease.late_fee ? formatCurrency(lease.late_fee) : null],
    ['Grace period (days)', lease.grace_period_days],
    ['Occupancy limit', lease.occupancy_limit],
    ['Pets allowed', lease.pets_allowed == null ? null : yesNo(lease.pets_allowed)],
    ['Pet deposit', lease.pet_deposit ? formatCurrency(lease.pet_deposit) : null],
    ['Parking included', lease.parking_included == null ? null : yesNo(lease.parking_included)],
    ['Parking spaces', lease.parking_spaces],
    ['No smoking', lease.no_smoking == null ? null : yesNo(lease.no_smoking)],
    ['Quiet hours', lease.quiet_hours],
    ['Utilities included', lease.utilities_included],
    ['Lawn maintenance', lease.lawn_maintenance_responsibility && titleCase(lease.lawn_maintenance_responsibility)],
    ['Trash included', lease.trash_service_included == null ? null : yesNo(lease.trash_service_included)],
    [
      'Early termination',
      lease.early_termination_allowed == null
        ? null
        : lease.early_termination_allowed
          ? `Allowed${lease.early_termination_penalty ? ` · ${formatCurrency(lease.early_termination_penalty)}` : ''}`
          : 'Not allowed',
    ],
  ];
  const shownTerms = terms.filter(([, v]) => v !== null && v !== undefined && v !== '');

  const leaseField = (k: keyof Lease) => lease[k];

  return (
    <div>
      <Link to="/leases" className="text-sm text-blue-600 hover:underline">
        &larr; Leases
      </Link>
      <PageHeader
        title={`${formatCurrency(lease.monthly_rent)}/mo lease`}
        subtitle={`${formatDate(lease.start_date)} → ${formatDate(lease.end_date)}`}
        action={
          <div className="flex items-center gap-3">
            <StatusBadge status={lease.status} variant={leaseStatusVariant(lease.status)} />
            <Button variant="secondary" onClick={() => setEditOpen(true)}>
              Edit
            </Button>
          </div>
        }
      />

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <Card className="p-5">
          <h2 className="font-semibold text-gray-900 mb-3">Terms</h2>
          <dl className="text-sm space-y-2">
            <div className="flex justify-between">
              <dt className="text-gray-500">Monthly rent</dt>
              <dd>{formatCurrency(lease.monthly_rent)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Security deposit</dt>
              <dd>{formatCurrency(lease.security_deposit)}</dd>
            </div>
            {shownTerms.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4">
                <dt className="text-gray-500">{label}</dt>
                <dd className="text-right">{value}</dd>
              </div>
            ))}
          </dl>
          {(leaseField('special_conditions') as string) && (
            <div className="mt-4">
              <p className="text-gray-500 text-sm mb-1">Special conditions</p>
              <p className="text-sm text-gray-800 whitespace-pre-wrap">
                {leaseField('special_conditions') as string}
              </p>
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <div className="px-5 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Tenants ({lease.tenants.length})</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {lease.tenants.length === 0 && (
                <p className="px-5 py-6 text-sm text-gray-500">No tenants.</p>
              )}
              {lease.tenants.map((t) => (
                <div key={t.id} className="flex items-start justify-between px-5 py-3">
                  <div>
                    <p className="font-medium text-gray-900">
                      {t.first_name} {t.last_name}
                      {t.preferred_name ? ` (${t.preferred_name})` : ''}
                    </p>
                    <p className="text-sm text-gray-500">
                      {[t.email, t.phone].filter(Boolean).join(' · ') || '—'}
                    </p>
                  </div>
                  <button
                    onClick={() => setEditingTenant(t)}
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    Edit
                  </button>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <div className="px-5 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Documents ({documents.length})</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {documents.length === 0 && (
                <p className="px-5 py-6 text-sm text-gray-500">No documents.</p>
              )}
              {documents.map((d) => (
                <div key={d.id} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <p className="font-medium text-gray-900">{d.file_name}</p>
                    <p className="text-xs text-gray-500">
                      {titleCase(d.document_type)}
                      {d.file_size ? ` · ${humanSize(d.file_size)}` : ''}
                      {d.extraction_confidence ? ` · parsed (${d.extraction_confidence})` : ''}
                    </p>
                  </div>
                  {d.has_file && (
                    <a
                      href={leaseDocumentAPI.downloadUrl(lease.id, d.id)}
                      className="text-sm font-medium text-blue-600 hover:underline"
                    >
                      Download
                    </a>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <Modal open={editOpen} title="Edit Lease" onClose={() => setEditOpen(false)}>
        <LeaseEditForm
          lease={lease}
          onSaved={() => {
            setEditOpen(false);
            reload();
          }}
          onCancel={() => setEditOpen(false)}
        />
      </Modal>

      <Modal
        open={editingTenant !== null}
        title="Edit Tenant"
        onClose={() => setEditingTenant(null)}
      >
        {editingTenant && (
          <TenantForm
            existing={editingTenant}
            onSaved={() => {
              setEditingTenant(null);
              reload();
            }}
            onCancel={() => setEditingTenant(null)}
          />
        )}
      </Modal>
    </div>
  );
};
