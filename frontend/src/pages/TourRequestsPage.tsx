import { useNavigate, useSearchParams } from 'react-router-dom';
import { tourRequestAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { TourRequestStatus } from '../types';
import { Card, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui';
import { StatusBadge } from '../components/StatusBadge';
import { tourStatusVariant } from '../lib/tours';

const FILTERS: { value: '' | TourRequestStatus; label: string }[] = [
  { value: 'pending', label: 'Needs review' },
  { value: 'approved', label: 'Approved' },
  { value: 'declined', label: 'Declined' },
  { value: '', label: 'All' },
];

export const TourRequestsPage = () => {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const filter = (params.get('status') ?? 'pending') as '' | TourRequestStatus;
  const { data, loading, error, reload } = useAsync(
    () => tourRequestAPI.list(filter ? { status_filter: filter } : undefined),
    [filter],
  );

  return (
    <div>
      <PageHeader title="Tour Requests" subtitle="Self-guided tour requests from the public site" />

      <div className="flex gap-2 mb-4 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => setParams({ status: f.value })}
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
      {data && data.length === 0 && (
        <EmptyState
          title={filter === 'pending' ? 'Nothing to review' : 'No tour requests'}
          hint="New requests from the tour site will appear here, and you'll get an email."
        />
      )}

      {data && data.length > 0 && (
        <Card>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left">
              <tr>
                <th className="px-5 py-3 font-medium">When</th>
                <th className="px-5 py-3 font-medium">Visitor</th>
                <th className="px-5 py-3 font-medium">Home</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((r) => (
                <tr key={r.id} onClick={() => navigate(`/tour-requests/${r.id}`)} className="hover:bg-gray-50 cursor-pointer">
                  <td className="px-5 py-3 font-medium text-gray-900">{r.when_display}</td>
                  <td className="px-5 py-3 text-gray-700">
                    {r.first_name} {r.last_name}
                  </td>
                  <td className="px-5 py-3 text-gray-600">{r.property_name}</td>
                  <td className="px-5 py-3">
                    <StatusBadge status={r.status} variant={tourStatusVariant(r.status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
};
