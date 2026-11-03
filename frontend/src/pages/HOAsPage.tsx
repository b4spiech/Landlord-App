import { useState } from 'react';
import { Link } from 'react-router-dom';
import { hoaAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Button, Card, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { HOAForm } from '../components/HOAForm';
import { formatCurrency } from '../lib/format';

export const HOAsPage = () => {
  const { data, loading, error, reload } = useAsync(() => hoaAPI.list());
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div>
      <PageHeader
        title="HOAs"
        subtitle="Homeowners / condo associations"
        action={<Button onClick={() => setModalOpen(true)}>+ Add HOA</Button>}
      />

      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState title="No HOAs yet" hint="Add an HOA to track contacts, dues, and CC&Rs." />
      )}

      {data && data.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((h) => (
            <Card key={h.id} className="p-5">
              <Link to={`/hoas/${h.id}`} className="font-semibold text-gray-900 hover:text-blue-600">
                {h.name}
              </Link>
              <dl className="text-sm text-gray-500 mt-2 space-y-1">
                {h.contact_name && <dd>Contact: {h.contact_name}</dd>}
                {h.contact_phone && <dd>{h.contact_phone}</dd>}
                {h.dues_amount != null && (
                  <dd>
                    Dues: {formatCurrency(h.dues_amount)}
                    {h.dues_frequency ? ` / ${h.dues_frequency}` : ''}
                  </dd>
                )}
              </dl>
              <Link
                to={`/hoas/${h.id}`}
                className="inline-block mt-4 text-sm font-medium text-blue-600 hover:underline"
              >
                View & documents →
              </Link>
            </Card>
          ))}
        </div>
      )}

      <Modal open={modalOpen} title="Add HOA" onClose={() => setModalOpen(false)}>
        <HOAForm
          onSaved={() => {
            setModalOpen(false);
            reload();
          }}
          onCancel={() => setModalOpen(false)}
        />
      </Modal>
    </div>
  );
};
