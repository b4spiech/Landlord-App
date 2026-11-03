import { titleCase } from '../lib/format';

type Variant = 'green' | 'blue' | 'yellow' | 'red' | 'gray';

interface StatusBadgeProps {
  status: string;
  variant?: Variant;
}

const colorMap: Record<Variant, string> = {
  green: 'bg-green-100 text-green-800',
  blue: 'bg-blue-100 text-blue-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red: 'bg-red-100 text-red-800',
  gray: 'bg-gray-100 text-gray-700',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, variant = 'blue' }) => (
  <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${colorMap[variant]}`}>
    {titleCase(status)}
  </span>
);
