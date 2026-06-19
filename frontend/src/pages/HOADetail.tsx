import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { hoaAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Button, Card, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { HOAForm } from '../components/HOAForm';
import { HOADocuments } from '../components/HOADocuments';
import { formatCurrency } from '../lib/format';

export const HOADetail = () => {
  const { id } = useParams<{ id: string }>();
  const { data: hoa, loading, error, reload } = useAsync(() => hoaAPI.get(id!), [id]);
  const [editOpen, setEditOpen] = useState(false);

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!hoa) return null;

  const row = (label: string, value?: string | null) =>
    value ? (
      <div className="flex justify-between gap-4">
        <dt className="text-gray-500">{label}</dt>
        <dd className="text-gray-900 text-right">{value}</dd>
      </div>
    ) : null;

  const address = [hoa.address_line1, hoa.address_line2, [hoa.city, hoa.state].filter(Boolean).join(', '), hoa.postal_code]
    .filter(Boolean)
    .join(', ');

  return (
    <div>
      <Link to="/hoas" className="text-sm text-blue-600 hover:underline">
        &larr; HOAs
      </Link>
      <PageHeader
        title={hoa.name}
        action={
          <Button variant="secondary" onClick={() => setEditOpen(true)}>
            Edit
          </Button>
        }
      />

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <Card className="p-5">
          <h2 className="font-semibold text-gray-900 mb-3">Details</h2>
          <dl className="text-sm space-y-2">
            {row('Contact', hoa.contact_name)}
            {row('Email', hoa.contact_email)}
            {row('Phone', hoa.contact_phone)}
            {row('Management', hoa.management_company_name)}
            {hoa.website && (
              <div className="flex justify-between gap-4">
                <dt className="text-gray-500">Website</dt>
                <dd className="text-right">
                  <a
                    href={hoa.website.startsWith('http') ? hoa.website : `https://${hoa.website}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {hoa.website}
                  </a>
                </dd>
              </div>
            )}
            {hoa.dues_amount != null &&
              row(
                'Dues',
                `${formatCurrency(hoa.dues_amount)}${hoa.dues_frequency ? ` / ${hoa.dues_frequency}` : ''}`,
              )}
            {row('Address', address || null)}
            {row('Notes', hoa.notes)}
          </dl>
        </Card>

        <HOADocuments hoaId={hoa.id} />
      </div>

      <Modal open={editOpen} title="Edit HOA" onClose={() => setEditOpen(false)}>
        <HOAForm
          existing={hoa}
          onSaved={() => {
            setEditOpen(false);
            reload();
          }}
          onCancel={() => setEditOpen(false)}
        />
      </Modal>
    </div>
  );
};
