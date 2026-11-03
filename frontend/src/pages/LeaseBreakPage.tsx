import { Link, useParams, useSearchParams } from 'react-router-dom';
import { leaseAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Button, ErrorState, PageHeader, Spinner } from '../components/ui';
import { LeaseBreakWorkflow } from '../components/LeaseBreakWorkflow';
import { LeaseBreakList } from '../components/LeaseBreakList';
import { LeaseBreakDetailView } from '../components/LeaseBreakDetailView';

/**
 * /lease-breaks                -> list of all lease breaks
 * /lease-breaks?new=1          -> start a new one (pick a lease)
 * /lease-breaks?lease=<id>     -> start a new one for that lease
 * /lease-breaks/<requestId>    -> view an existing one (and delete it)
 */
export const LeaseBreakPage = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const [searchParams] = useSearchParams();
  const initialLeaseId = searchParams.get('lease') ?? '';
  const starting = !!initialLeaseId || searchParams.get('new') === '1';

  if (requestId) return <LeaseBreakDetailView requestId={requestId} />;
  if (!starting)
    return (
      <div>
        <PageHeader
          title="Lease Breaks"
          subtitle="Early-termination requests"
          action={
            <Link to="/lease-breaks?new=1">
              <Button>+ Start a lease break</Button>
            </Link>
          }
        />
        <LeaseBreakList />
      </div>
    );
  return <StartLeaseBreak initialLeaseId={initialLeaseId} />;
};

const StartLeaseBreak = ({ initialLeaseId }: { initialLeaseId: string }) => {
  const { data, loading, error, reload } = useAsync(() => leaseAPI.list());
  return (
    <div>
      <Link to="/lease-breaks" className="text-sm text-blue-600 hover:underline">
        &larr; Lease breaks
      </Link>
      <PageHeader title="Start a lease break" subtitle="Guided early-termination workflow" />

      <div className="bg-blue-50 border border-blue-200 text-blue-800 rounded-lg px-4 py-3 text-sm mb-6">
        Generate buyout options with exact cash-due figures, record the tenant's selection, and
        produce a signable buyout agreement PDF.
      </div>

      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && <LeaseBreakWorkflow leases={data} initialLeaseId={initialLeaseId} />}
    </div>
  );
};
