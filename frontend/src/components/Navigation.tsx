import { useEffect, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';

const primaryLinks = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/properties', label: 'Properties' },
];

// Everything editable lives under the Menu dropdown.
const menuLinks = [
  { to: '/leases', label: 'Leases' },
  { to: '/owners', label: 'Owners' },
  { to: '/management-companies', label: 'Management Companies' },
  { to: '/tenants', label: 'Tenants' },
  { to: '/hoas', label: 'HOAs' },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 text-sm font-medium rounded transition-colors ${
    isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'
  }`;

export const Navigation = () => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close the dropdown on any outside click.
  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [menuOpen]);

  return (
    <nav className="bg-white shadow sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between flex-wrap gap-2">
        <NavLink to="/" className="text-xl font-bold text-blue-600">
          APEX Property Management
        </NavLink>
        <div className="flex items-center gap-1 sm:gap-2">
          {primaryLinks.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={linkClass}>
              {l.label}
            </NavLink>
          ))}

          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className={`px-3 py-2 text-sm font-medium rounded transition-colors flex items-center gap-1 ${
                menuOpen ? 'bg-gray-100 text-gray-900' : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              Menu
              <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-1 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-30">
                <p className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-400">
                  Records
                </p>
                {menuLinks.map((l) => (
                  <NavLink
                    key={l.to}
                    to={l.to}
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) =>
                      `block px-4 py-2 text-sm ${
                        isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'
                      }`
                    }
                  >
                    {l.label}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};
