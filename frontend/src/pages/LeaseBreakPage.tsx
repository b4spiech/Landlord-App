import { leaseAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { ErrorState, PageHeader, Spinner } from '../components/ui';
import { LeaseBreakWorkflow } from '../components/LeaseBreakWorkflow';

export const LeaseBreakPage = () => {
  const { data, loading, error, reload } = useAsync(() => leaseAPI.list());

  return (
    <div>
      <PageHeader title="Lease Break" subtitle="Guided early-termination workflow" />

      <div className="bg-blue-50 border border-blue-200 text-blue-800 rounded-lg px-4 py-3 text-sm mb-6">
        <strong>Preview mode.</strong> Options, compliance checks, and the email draft are computed
        in the browser. Persistence, real email delivery, and DocuSign routing arrive with backend
        Milestones 5–6.
      </div>

      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && <LeaseBreakWorkflow leases={data} />}
    </div>
  );
};
