import { Link, useNavigate } from 'react-router-dom';
import { leaseAPI, leaseBreakAPI, propertyAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { formatCurrency, formatDate, titleCase } from '../lib/format';
import { Card, ErrorState, PageHeader, Spinner } from './ui';
import { StatusBadge } from './StatusBadge';
import { DeleteButton } from './ConfirmDelete';

/** Read-only view of an existing lease-break request, with delete. */
export const LeaseBreakDetailView = ({ requestId }: { requestId: string }) => {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(async () => {
    const detail = await leaseBreakAPI.get(requestId);
    const lease = await leaseAPI.get(detail.request.lease_id);
    const property = await propertyAPI.get(lease.property_id);
    return { ...detail, lease, property };
  }, [requestId]);

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;
  const { request: r, options, documents, lease, property } = data;
  const tenants =
    lease.tenants.map((t) => `${t.first_name} ${t.last_name}`).join(', ') || 'No tenants';

  return (
    <div>
      <Link to="/lease-breaks" className="text-sm text-blue-600 hover:underline">
        &larr; Lease breaks
      </Link>
      <PageHeader
        title={`Lease break · ${property.name}`}
        subtitle={`${tenants} · requested ${formatDate(r.requested_date)}`}
        action={
          <div className="flex items-center gap-3">
            <StatusBadge status={titleCase(r.status)} variant="blue" />
            <DeleteButton
              kind="lease-breaks"
              id={r.id}
              onDeleted={() => navigate('/lease-breaks')}
            />
          </div>
        }
      />

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <Card className="p-5">
          <h2 className="font-semibold text-gray-900 mb-3">Request</h2>
          <dl className="text-sm space-y-2">
            {(
              [
                [
                  'Lease',
                  <Link
                    key="l"
                    to={`/leases/${lease.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    {formatCurrency(lease.monthly_rent)}/mo · {formatDate(lease.start_date)} →{' '}
                    {formatDate(lease.end_date)}
                  </Link>,
                ],
                ['Desired move-out', formatDate(r.desired_move_out_date)],
                ['Reason', r.reason || '—'],
                ['Completed', r.completed_at ? formatDate(r.completed_at) : '—'],
              ] as [string, React.ReactNode][]
            ).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4">
                <dt className="text-gray-500">{k}</dt>
                <dd className="text-right">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card>
          <div className="px-5 py-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">Options ({options.length})</h2>
          </div>
          {options.length === 0 && (
            <p className="px-5 py-4 text-sm text-gray-500">No options calculated.</p>
          )}
          <ul className="divide-y divide-gray-100 text-sm">
            {options.map((o) => (
              <li key={o.id} className="px-5 py-3 flex justify-between gap-4">
                <span>
                  {o.label}
                  {o.is_selected && (
                    <span className="ml-2 text-xs font-semibold text-green-700">Selected</span>
                  )}
                </span>
                <span className="text-gray-700">
                  {o.cash_due_at_signing != null
                    ? `${formatCurrency(o.cash_due_at_signing)} due`
                    : ''}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="lg:col-span-2">
          <div className="px-5 py-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">Documents ({documents.length})</h2>
          </div>
          {documents.length === 0 && (
            <p className="px-5 py-4 text-sm text-gray-500">No documents generated.</p>
          )}
          <ul className="divide-y divide-gray-100 text-sm">
            {documents.map((d) => (
              <li key={d.id} className="px-5 py-3 flex justify-between gap-4">
                <span>
                  {titleCase(d.document_type)} ·{' '}
                  <span className="text-gray-500">{d.file_name}</span>
                </span>
                <span className="flex items-center gap-3">
                  <StatusBadge
                    status={titleCase(d.status)}
                    variant={d.status === 'signed' ? 'green' : 'gray'}
                  />
                  {d.has_file && (
                    <a
                      href={leaseBreakAPI.documentDownloadUrl(r.id, d.id)}
                      className="text-blue-600 hover:underline"
                    >
                      Download
                    </a>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
};
