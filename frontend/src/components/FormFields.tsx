import type { ReactNode } from 'react';

interface FieldProps {
  label: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}

export const Field = ({ label, error, required, children }: FieldProps) => (
  <label className="block">
    <span className="block text-sm font-medium text-gray-700 mb-1">
      {label}
      {required && <span className="text-red-500"> *</span>}
    </span>
    {children}
    {error && <span className="block text-xs text-red-600 mt-1">{error}</span>}
  </label>
);

const baseInput =
  'w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none';

export const TextInput = ({
  value,
  onChange,
  type = 'text',
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) => (
  <input
    type={type}
    value={value}
    placeholder={placeholder}
    onChange={(e) => onChange(e.target.value)}
    className={baseInput}
  />
);

export const NumberInput = ({
  value,
  onChange,
  placeholder,
  min,
  step,
}: {
  value: number | '' ;
  onChange: (v: number | '') => void;
  placeholder?: string;
  min?: number;
  step?: number;
}) => (
  <input
    type="number"
    value={value}
    min={min}
    step={step}
    placeholder={placeholder}
    onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
    className={baseInput}
  />
);

export const Select = ({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) => (
  <select value={value} onChange={(e) => onChange(e.target.value)} className={baseInput}>
    {placeholder && <option value="">{placeholder}</option>}
    {options.map((o) => (
      <option key={o.value} value={o.value}>
        {o.label}
      </option>
    ))}
  </select>
);

export const Textarea = ({
  value,
  onChange,
  rows = 3,
}: {
  value: string;
  onChange: (v: string) => void;
  rows?: number;
}) => (
  <textarea
    value={value}
    rows={rows}
    onChange={(e) => onChange(e.target.value)}
    className={baseInput}
  />
);
