import { Link, useParams } from 'react-router-dom';
import { hoaAPI, leaseAPI, propertyAPI, unitAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Card, ErrorState, PageHeader, Spinner } from '../components/ui';
import { StatusBadge } from '../components/StatusBadge';
import {
  formatCurrency,
  formatDate,
  leaseStatusVariant,
  propertyTypeLabel,
  unitStatusVariant,
} from '../lib/format';

export const PropertyDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync(async () => {
    const property = await propertyAPI.get(id!);
    const [units, leases] = await Promise.all([
      unitAPI.list({ property_id: id }),
      leaseAPI.list({ property_id: id }),
    ]);
    const hoa = property.hoa_id ? await hoaAPI.get(property.hoa_id) : null;
    return { property, units, leases, hoa };
  }, [id]);

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const { property, units, leases, hoa } = data;

  return (
    <div>
      <Link to="/properties" className="text-sm text-blue-600 hover:underline">
        &larr; Properties
      </Link>
      <PageHeader
        title={property.name}
        subtitle={`${property.address_line1}${property.address_line2 ? ', ' + property.address_line2 : ''}, ${property.city}, ${property.state} ${property.postal_code}`}
      />

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="p-5">
          <h2 className="font-semibold text-gray-900 mb-3">Details</h2>
          <dl className="text-sm space-y-2">
            <div className="flex justify-between">
              <dt className="text-gray-500">Type</dt>
              <dd>{propertyTypeLabel(property.property_type)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Bedrooms</dt>
              <dd>{property.bedrooms ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Bathrooms</dt>
              <dd>{property.bathrooms ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">HOA</dt>
              <dd>
                {hoa ? (
                  <Link to={`/hoas/${hoa.id}`} className="text-blue-600 hover:underline">
                    {hoa.name}
                  </Link>
                ) : (
                  '—'
                )}
              </dd>
            </div>
          </dl>
        </Card>

        <Card className="lg:col-span-2">
          <div className="px-5 py-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">Units ({units.length})</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {units.length === 0 && <p className="px-5 py-6 text-sm text-gray-500">No units.</p>}
            {units.map((u) => (
              <div key={u.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="font-medium text-gray-900">Unit {u.unit_number}</p>
                  <p className="text-sm text-gray-500">
                    {u.bedrooms ?? '—'} bd / {u.bathrooms ?? '—'} ba · {formatCurrency(u.market_rent)} mkt
                  </p>
                </div>
                <StatusBadge status={u.status} variant={unitStatusVariant(u.status)} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      {hoa && (
        <Card className="mt-6">
          <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">HOA — {hoa.name}</h2>
            <Link to={`/hoas/${hoa.id}`} className="text-sm text-blue-600 hover:underline">
              Manage & documents →
            </Link>
          </div>
          <dl className="text-sm px-5 py-4 grid sm:grid-cols-2 gap-x-8 gap-y-2">
            {hoa.contact_name && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Contact</dt>
                <dd>{hoa.contact_name}</dd>
              </div>
            )}
            {hoa.contact_phone && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Phone</dt>
                <dd>{hoa.contact_phone}</dd>
              </div>
            )}
            {hoa.contact_email && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Email</dt>
                <dd>{hoa.contact_email}</dd>
              </div>
            )}
            {hoa.website && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Website</dt>
                <dd>
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
            {hoa.dues_amount != null && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Dues</dt>
                <dd>
                  {formatCurrency(hoa.dues_amount)}
                  {hoa.dues_frequency ? ` / ${hoa.dues_frequency}` : ''}
                </dd>
              </div>
            )}
          </dl>
        </Card>
      )}

      <Card className="mt-6">
        <div className="px-5 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Leases ({leases.length})</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {leases.length === 0 && <p className="px-5 py-6 text-sm text-gray-500">No leases.</p>}
          {leases.map((l) => (
            <div key={l.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="font-medium text-gray-900">{formatCurrency(l.monthly_rent)}/mo</p>
                <p className="text-sm text-gray-500">
                  {formatDate(l.start_date)} → {formatDate(l.end_date)}
                </p>
              </div>
              <StatusBadge status={l.status} variant={leaseStatusVariant(l.status)} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
