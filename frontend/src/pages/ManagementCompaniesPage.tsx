import { useState } from 'react';
import { managementCompanyAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { ManagementCompany } from '../types';
import { Button, Card, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { ManagementCompanyForm } from '../components/ManagementCompanyForm';

export const ManagementCompaniesPage = () => {
  const { data, loading, error, reload } = useAsync(() => managementCompanyAPI.list());
  const [editing, setEditing] = useState<ManagementCompany | null>(null);
  const [open, setOpen] = useState(false);

  const openCreate = () => {
    setEditing(null);
    setOpen(true);
  };
  const openEdit = (c: ManagementCompany) => {
    setEditing(c);
    setOpen(true);
  };
  const saved = () => {
    setOpen(false);
    reload();
  };

  return (
    <div>
      <PageHeader
        title="Management Companies"
        subtitle="Entities that manage your properties"
        action={<Button onClick={openCreate}>+ Add Company</Button>}
      />
      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && <EmptyState title="No management companies yet" />}
      {data && data.length > 0 && (
        <Card>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left">
              <tr>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Legal name</th>
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{c.name}</td>
                  <td className="px-5 py-3 text-gray-600">{c.legal_name ?? '—'}</td>
                  <td className="px-5 py-3 text-gray-600">{c.email ?? '—'}</td>
                  <td className="px-5 py-3 text-right">
                    <button onClick={() => openEdit(c)} className="text-blue-600 hover:underline">
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <Modal
        open={open}
        title={editing ? 'Edit Management Company' : 'Add Management Company'}
        onClose={() => setOpen(false)}
      >
        <ManagementCompanyForm
          existing={editing ?? undefined}
          onSaved={saved}
          onCancel={() => setOpen(false)}
        />
      </Modal>
    </div>
  );
};
