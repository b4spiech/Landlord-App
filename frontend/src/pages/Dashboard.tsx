import { Link } from 'react-router-dom';
import { leaseAPI, propertyAPI, tenantAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Card, ErrorState, PageHeader, Spinner } from '../components/ui';
import { StatusBadge } from '../components/StatusBadge';
import { formatCurrency, leaseStatusVariant } from '../lib/format';

const StatCard = ({ label, value, to }: { label: string; value: string | number; to?: string }) => {
  const inner = (
    <Card className="p-5 h-full hover:shadow-md transition-shadow">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
    </Card>
  );
  return to ? <Link to={to}>{inner}</Link> : inner;
};

export const Dashboard = () => {
  const { data, loading, error, reload } = useAsync(async () => {
    const [properties, tenants, leases] = await Promise.all([
      propertyAPI.list(),
      tenantAPI.list(),
      leaseAPI.list(),
    ]);
    return { properties, tenants, leases };
  });

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const { properties, tenants, leases } = data;
  const activeLeases = leases.filter((l) => l.status === 'active');
  const monthlyRevenue = activeLeases.reduce((sum, l) => sum + (l.monthly_rent || 0), 0);

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Portfolio overview" />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Properties" value={properties.length} to="/properties" />
        <StatCard label="Active Leases" value={activeLeases.length} to="/leases" />
        <StatCard label="Tenants" value={tenants.length} to="/tenants" />
        <StatCard label="Monthly Revenue" value={formatCurrency(monthlyRevenue)} />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Properties</h2>
            <Link to="/properties" className="text-sm text-blue-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {properties.length === 0 && (
              <p className="px-5 py-6 text-sm text-gray-500">No properties yet.</p>
            )}
            {properties.slice(0, 5).map((p) => (
              <Link
                key={p.id}
                to={`/properties/${p.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-gray-50"
              >
                <div>
                  <p className="font-medium text-gray-900">{p.name}</p>
                  <p className="text-sm text-gray-500">
                    {p.address_line1}, {p.city} {p.state}
                  </p>
                </div>
                <span className="text-sm text-gray-400">{p.property_type.replace('_', ' ')}</span>
              </Link>
            ))}
          </div>
        </Card>

        <Card>
          <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Leases</h2>
            <Link to="/leases" className="text-sm text-blue-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {leases.length === 0 && (
              <p className="px-5 py-6 text-sm text-gray-500">No leases yet.</p>
            )}
            {leases.slice(0, 5).map((l) => (
              <div key={l.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="font-medium text-gray-900">{formatCurrency(l.monthly_rent)}/mo</p>
                  <p className="text-sm text-gray-500">
                    {l.start_date} → {l.end_date}
                  </p>
                </div>
                <StatusBadge status={l.status} variant={leaseStatusVariant(l.status)} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};
