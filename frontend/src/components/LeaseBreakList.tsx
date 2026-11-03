import { useNavigate } from 'react-router-dom';
import { leaseBreakAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { formatCurrency, formatDate, titleCase } from '../lib/format';
import { Card, EmptyState, ErrorState, Spinner } from './ui';
import { StatusBadge } from './StatusBadge';

/** Table of lease-break requests (all, or for one lease). */
export const LeaseBreakList = ({
  leaseId,
  compact = false,
}: {
  leaseId?: string;
  compact?: boolean;
}) => {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(
    () => leaseBreakAPI.list(leaseId ? { lease_id: leaseId } : undefined),
    [leaseId],
  );

  if (loading) return compact ? null : <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data || data.length === 0)
    return compact ? (
      <p className="px-5 py-4 text-sm text-gray-500">No lease breaks.</p>
    ) : (
      <EmptyState
        title="No lease breaks yet"
        hint="Start one from a lease, or with the button above."
      />
    );

  const table = (
    <table className="w-full text-sm">
      <thead className="bg-gray-50 text-gray-500 text-left">
        <tr>
          {!compact && <th className="px-5 py-3 font-medium">Property</th>}
          {!compact && <th className="px-5 py-3 font-medium">Tenants</th>}
          <th className="px-5 py-3 font-medium">Move-out</th>
          <th className="px-5 py-3 font-medium">Option</th>
          <th className="px-5 py-3 font-medium">Status</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {data.map((r) => (
          <tr
            key={r.id}
            onClick={() => navigate(`/lease-breaks/${r.id}`)}
            className="hover:bg-gray-50 cursor-pointer"
          >
            {!compact && <td className="px-5 py-3 font-medium text-blue-600">{r.property_name}</td>}
            {!compact && <td className="px-5 py-3 text-gray-700">{r.tenant_names}</td>}
            <td className="px-5 py-3 text-gray-700">{formatDate(r.desired_move_out_date)}</td>
            <td className="px-5 py-3 text-gray-700">
              {r.selected_option_label
                ? `${r.selected_option_label}${r.cash_due_at_signing != null ? ` · ${formatCurrency(r.cash_due_at_signing)} due` : ''}`
                : '—'}
            </td>
            <td className="px-5 py-3">
              <StatusBadge
                status={titleCase(r.status)}
                variant={
                  r.has_signed_agreement ? 'green' : r.status === 'cancelled' ? 'gray' : 'blue'
                }
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
  return compact ? table : <Card>{table}</Card>;
};
