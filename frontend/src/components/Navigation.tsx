import { NavLink } from 'react-router-dom';

const links = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/properties', label: 'Properties' },
  { to: '/leases', label: 'Leases' },
  { to: '/lease-breaks', label: 'Lease Breaks' },
  { to: '/approvals', label: 'Approvals' },
];

export const Navigation = () => (
  <nav className="bg-white shadow sticky top-0 z-10">
    <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between flex-wrap gap-2">
      <NavLink to="/" className="text-xl font-bold text-blue-600">
        APEX Property Management
      </NavLink>
      <div className="flex gap-1 sm:gap-2 flex-wrap">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) =>
              `px-3 py-2 text-sm font-medium rounded transition-colors ${
                isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'
              }`
            }
          >
            {l.label}
          </NavLink>
        ))}
      </div>
    </div>
  </nav>
);
