import { useState } from 'react';
import { Link } from 'react-router-dom';
import { propertyAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { Property } from '../types';
import { Button, Card, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Modal } from '../components/Modal';
import { PropertyForm } from '../components/PropertyForm';
import { propertyTypeLabel } from '../lib/format';

export const PropertiesPage = () => {
  const { data, loading, error, reload } = useAsync(() => propertyAPI.list());
  const [editing, setEditing] = useState<Property | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };
  const openEdit = (p: Property) => {
    setEditing(p);
    setModalOpen(true);
  };
  const handleSaved = () => {
    setModalOpen(false);
    reload();
  };

  return (
    <div>
      <PageHeader
        title="Properties"
        subtitle="Manage your rental properties"
        action={<Button onClick={openCreate}>+ Add Property</Button>}
      />

      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title="No properties yet" hint="Click “Add Property” to create your first one." />
      )}

      {data && data.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((p) => (
            <Card key={p.id} className="p-5 flex flex-col">
              <div className="flex items-start justify-between">
                <Link to={`/properties/${p.id}`} className="font-semibold text-gray-900 hover:text-blue-600">
                  {p.name}
                </Link>
                <span className="text-xs text-gray-400">{propertyTypeLabel(p.property_type)}</span>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {p.address_line1}
                {p.address_line2 ? `, ${p.address_line2}` : ''}
                <br />
                {p.city}, {p.state} {p.postal_code}
              </p>
              <div className="mt-4 pt-4 border-t border-gray-100 flex gap-3">
                <Link
                  to={`/properties/${p.id}`}
                  className="text-sm font-medium text-blue-600 hover:underline"
                >
                  View
                </Link>
                <button
                  onClick={() => openEdit(p)}
                  className="text-sm font-medium text-gray-600 hover:underline"
                >
                  Edit
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={modalOpen}
        title={editing ? 'Edit Property' : 'Add Property'}
        onClose={() => setModalOpen(false)}
      >
        <PropertyForm
          existing={editing ?? undefined}
          onSaved={handleSaved}
          onCancel={() => setModalOpen(false)}
        />
      </Modal>
    </div>
  );
};
