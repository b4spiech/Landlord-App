import { useState } from 'react';
import { tenantAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { Tenant } from '../types';
import { Button, Card, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { TenantForm } from '../components/TenantForm';

export const TenantsPage = () => {
  const { data, loading, error, reload } = useAsync(() => tenantAPI.list());
  const [editing, setEditing] = useState<Tenant | null>(null);
  const [open, setOpen] = useState(false);

  const openCreate = () => {
    setEditing(null);
    setOpen(true);
  };
  const openEdit = (t: Tenant) => {
    setEditing(t);
    setOpen(true);
  };
  const saved = () => {
    setOpen(false);
    reload();
  };

  return (
    <div>
      <PageHeader
        title="Tenants"
        subtitle="People who sign leases"
        action={<Button onClick={openCreate}>+ Add Tenant</Button>}
      />
      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && <EmptyState title="No tenants yet" />}
      {data && data.length > 0 && (
        <Card>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left">
              <tr>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">Phone</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">
                    {t.first_name} {t.last_name}
                  </td>
                  <td className="px-5 py-3 text-gray-600">{t.email ?? '—'}</td>
                  <td className="px-5 py-3 text-gray-600">{t.phone ?? '—'}</td>
                  <td className="px-5 py-3 text-right">
                    <button onClick={() => openEdit(t)} className="text-blue-600 hover:underline">
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <Modal open={open} title={editing ? 'Edit Tenant' : 'Add Tenant'} onClose={() => setOpen(false)}>
        <TenantForm existing={editing ?? undefined} onSaved={saved} onCancel={() => setOpen(false)} />
      </Modal>
    </div>
  );
};
