import { useState } from 'react';
import { ownerAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { Owner } from '../types';
import { Button, Card, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { OwnerForm } from '../components/OwnerForm';

export const OwnersPage = () => {
  const { data, loading, error, reload } = useAsync(() => ownerAPI.list());
  const [editing, setEditing] = useState<Owner | null>(null);
  const [open, setOpen] = useState(false);

  const openCreate = () => {
    setEditing(null);
    setOpen(true);
  };
  const openEdit = (o: Owner) => {
    setEditing(o);
    setOpen(true);
  };
  const saved = () => {
    setOpen(false);
    reload();
  };

  return (
    <div>
      <PageHeader
        title="Owners"
        subtitle="People and entities that hold title"
        action={<Button onClick={openCreate}>+ Add Owner</Button>}
      />
      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && <EmptyState title="No owners yet" />}
      {data && data.length > 0 && (
        <Card>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left">
              <tr>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">Location</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((o) => (
                <tr key={o.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{o.name}</td>
                  <td className="px-5 py-3 text-gray-600">{o.is_entity ? 'Entity' : 'Individual'}</td>
                  <td className="px-5 py-3 text-gray-600">{o.email ?? '—'}</td>
                  <td className="px-5 py-3 text-gray-600">
                    {[o.city, o.state].filter(Boolean).join(', ') || '—'}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button onClick={() => openEdit(o)} className="text-blue-600 hover:underline">
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <Modal open={open} title={editing ? 'Edit Owner' : 'Add Owner'} onClose={() => setOpen(false)}>
        <OwnerForm existing={editing ?? undefined} onSaved={saved} onCancel={() => setOpen(false)} />
      </Modal>
    </div>
  );
};
