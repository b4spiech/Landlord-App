import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { leaseAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { LeaseStatus } from '../types';
import { Button, Card, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { LeaseForm } from '../components/LeaseForm';
import { StatusBadge } from '../components/StatusBadge';
import { formatCurrency, formatDate, leaseStatusVariant } from '../lib/format';

const FILTERS: { value: '' | LeaseStatus; label: string }[] = [
  { value: '', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'draft', label: 'Draft' },
  { value: 'pending_signature', label: 'Pending' },
  { value: 'expired', label: 'Expired' },
  { value: 'terminated', label: 'Terminated' },
];

export const LeasesPage = () => {
  const { data, loading, error, reload } = useAsync(() => leaseAPI.list());
  const [filter, setFilter] = useState<'' | LeaseStatus>('');
  const [modalOpen, setModalOpen] = useState(false);

  const filtered = useMemo(
    () => (data ?? []).filter((l) => (filter ? l.status === filter : true)),
    [data, filter],
  );

  const handleSaved = () => {
    setModalOpen(false);
    reload();
  };

  return (
    <div>
      <PageHeader
        title="Leases"
        subtitle="All lease agreements"
        action={
          <div className="flex items-center gap-2 flex-wrap">
            <Link to="/lease-breaks">
              <Button variant="secondary">Lease Breaks</Button>
            </Link>
            <Link to="/approvals">
              <Button variant="secondary">Approvals</Button>
            </Link>
            <Button onClick={() => setModalOpen(true)}>+ New Lease</Button>
          </div>
        }
      />

      <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-600 mb-4">
        Lease actions like the <strong>Lease Break</strong> workflow and email{' '}
        <strong>Approvals</strong> live here, alongside your leases.
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded text-sm font-medium ${
              filter === f.value ? 'bg-blue-600 text-white' : 'bg-white border border-gray-300 text-gray-700'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && filtered.length === 0 && (
        <EmptyState title="No leases" hint="Create a lease or change the filter." />
      )}

      {filtered.length > 0 && (
        <Card>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left">
              <tr>
                <th className="px-5 py-3 font-medium">Rent</th>
                <th className="px-5 py-3 font-medium">Term</th>
                <th className="px-5 py-3 font-medium">Deposit</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">
                    {formatCurrency(l.monthly_rent)}/mo
                  </td>
                  <td className="px-5 py-3 text-gray-600">
                    {formatDate(l.start_date)} → {formatDate(l.end_date)}
                  </td>
                  <td className="px-5 py-3 text-gray-600">{formatCurrency(l.security_deposit)}</td>
                  <td className="px-5 py-3">
                    <StatusBadge status={l.status} variant={leaseStatusVariant(l.status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Modal open={modalOpen} title="New Lease" onClose={() => setModalOpen(false)}>
        <LeaseForm onSaved={handleSaved} onCancel={() => setModalOpen(false)} />
      </Modal>
    </div>
  );
};
