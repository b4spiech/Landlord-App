import { Link, useParams } from 'react-router-dom';
import { tourRequestAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Card, ErrorState, PageHeader, Spinner } from '../components/ui';
import { StatusBadge } from '../components/StatusBadge';
import { formatPhone, tourStatusVariant } from '../lib/tours';
import { TourDecisionPanel } from '../components/TourDecisionPanel';
import { titleCase } from '../lib/format';

const fmtDateTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

export const TourRequestDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync(async () => {
    const [request, notifications] = await Promise.all([
      tourRequestAPI.get(id!),
      tourRequestAPI.notifications(id!),
    ]);
    return { request, notifications };
  }, [id]);

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;
  const { request: r, notifications } = data;

  const rows: [string, React.ReactNode][] = [
    ['When', <strong key="w">{r.when_display}</strong>],
    ['Home', <Link key="h" to={`/properties/${r.property_id}`} className="text-blue-600 hover:underline">{r.property_name}</Link>],
    ['Address', r.property_address],
    ['Phone', <a key="p" href={`tel:${r.phone}`} className="text-blue-600 hover:underline">{formatPhone(r.phone)}</a>],
    ['Email', <a key="e" href={`mailto:${r.email}`} className="text-blue-600 hover:underline">{r.email}</a>],
    ['Texts OK', r.sms_consent ? `Yes (agreed ${fmtDateTime(r.sms_consent_at)})` : 'No — email only'],
    ['Submitted', fmtDateTime(r.created_at)],
  ];

  return (
    <div>
      <Link to="/tour-requests" className="text-sm text-blue-600 hover:underline">
        &larr; Tour Requests
      </Link>
      <PageHeader
        title={`${r.first_name} ${r.last_name}`}
        subtitle={`Tour request · ${r.property_name}`}
        action={<StatusBadge status={r.status} variant={tourStatusVariant(r.status)} />}
      />

      <TourDecisionPanel request={r} onChanged={reload} />

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <div className="space-y-6">
          <Card className="p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Request</h2>
            <dl className="text-sm space-y-2">
              {rows.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="text-gray-500">{k}</dt>
                  <dd className="text-right">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card>
            <div className="px-5 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Messages</h2>
            </div>
            <ul className="divide-y divide-gray-100 text-sm">
              {notifications.length === 0 && <li className="px-5 py-4 text-gray-500">None yet.</li>}
              {notifications.map((n, i) => (
                <li key={i} className="px-5 py-3 flex items-start justify-between gap-4">
                  <div>
                    <p className="text-gray-900">
                      {n.channel === 'sms' ? 'Text' : 'Email'} to {n.audience} · {titleCase(n.kind)}
                    </p>
                    <p className="text-xs text-gray-500">
                      {n.recipient} · {fmtDateTime(n.created_at)}
                      {n.status !== 'sent' && n.detail ? ` · ${n.detail}` : ''}
                    </p>
                  </div>
                  <StatusBadge
                    status={n.status}
                    variant={n.status === 'sent' ? 'green' : n.status === 'failed' ? 'red' : 'gray'}
                  />
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <Card className="p-5">
          <h2 className="font-semibold text-gray-900 mb-3">Photo ID</h2>
          {r.has_id_photo ? (
            <a href={tourRequestAPI.idPhotoUrl(r.id)} target="_blank" rel="noreferrer">
              <img
                src={tourRequestAPI.idPhotoUrl(r.id)}
                alt={`Photo ID for ${r.first_name} ${r.last_name}`}
                className="w-full rounded border object-contain max-h-[480px] bg-gray-50"
              />
            </a>
          ) : (
            <p className="text-sm text-gray-500">The photo ID has been deleted.</p>
          )}
          <p className="mt-2 text-xs text-gray-500">
            Deleted automatically after {fmtDateTime(r.id_photo_delete_after)}.
          </p>
        </Card>
      </div>
    </div>
  );
};
