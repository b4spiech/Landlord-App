import { useEffect, useState } from 'react';
import { getErrorMessage, leaseImportAPI, propertyAPI, unitAPI } from '../services/api';
import type { CreateLeaseResult, ParsedLease, ParsedLeaseData, ParsedTenant, Property, Unit } from '../types';
import { Button, Card } from './ui';
import { Field, NumberInput, Select, Textarea, TextInput } from './FormFields';
import { StatusBadge } from './StatusBadge';
import { useToast } from './Toast';

type Variant = 'green' | 'yellow' | 'red' | 'gray';
const confidenceVariant: Record<string, Variant> = { high: 'green', medium: 'yellow', low: 'red' };

// Tri-state yes/no/unknown for nullable booleans.
const BoolSelect = ({ value, onChange }: { value?: boolean | null; onChange: (v: boolean | null) => void }) => (
  <Select
    value={value == null ? '' : value ? 'yes' : 'no'}
    onChange={(v) => onChange(v === '' ? null : v === 'yes')}
    options={[
      { value: '', label: '—' },
      { value: 'yes', label: 'Yes' },
      { value: 'no', label: 'No' },
    ]}
  />
);

const numOrEmpty = (n?: number | null): number | '' => (n == null ? '' : n);

interface Props {
  initial: ParsedLeaseData;
  documentId?: string | null;
  onCreated: (r: CreateLeaseResult) => void;
  onCancel: () => void;
}

export const LeaseReviewEditor: React.FC<Props> = ({ initial, documentId, onCreated, onCancel }) => {
  const toast = useToast();
  const [tenants, setTenants] = useState<ParsedTenant[]>(
    initial.tenants.length ? initial.tenants : [{}],
  );
  const [lease, setLease] = useState<ParsedLease>(initial.lease ?? {});

  const [properties, setProperties] = useState<Property[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [propertyId, setPropertyId] = useState('');
  const [unitId, setUnitId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    propertyAPI.list().then(setProperties).catch((e) => toast.error(getErrorMessage(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!propertyId) {
      setUnits([]);
      setUnitId('');
      return;
    }
    unitAPI.list({ property_id: propertyId }).then((u) => {
      setUnits(u);
      setUnitId(u[0]?.id ?? '');
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propertyId]);

  const setLeaseField = <K extends keyof ParsedLease>(k: K, v: ParsedLease[K]) =>
    setLease((p) => ({ ...p, [k]: v }));
  const setTenantField = (i: number, k: keyof ParsedTenant, v: string | number | null) =>
    setTenants((prev) => prev.map((t, idx) => (idx === i ? { ...t, [k]: v } : t)));

  const submit = async () => {
    if (!propertyId) return toast.error('Select a property');
    if (!unitId) return toast.error('Select a unit');
    if (!lease.start_date || !lease.end_date) return toast.error('Start and end dates are required');
    setSubmitting(true);
    const body = {
      parsed: { tenants, lease, confidence: initial.confidence, notes: initial.notes ?? null },
      property_id: propertyId,
      unit_id: unitId,
      document_id: documentId ?? null,
    };
    try {
      const result = documentId
        ? await leaseImportAPI.createFromParsed(body)
        : await leaseImportAPI.createManual(body);
      onCreated(result);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const txt = (label: string, k: keyof ParsedLease) => (
    <Field label={label}>
      <TextInput value={(lease[k] as string) ?? ''} onChange={(v) => setLeaseField(k, (v || null) as never)} />
    </Field>
  );
  const num = (label: string, k: keyof ParsedLease) => (
    <Field label={label}>
      <NumberInput
        value={numOrEmpty(lease[k] as number | null)}
        onChange={(v) => setLeaseField(k, (v === '' ? null : v) as never)}
      />
    </Field>
  );
  const bool = (label: string, k: keyof ParsedLease) => (
    <Field label={label}>
      <BoolSelect value={lease[k] as boolean | null} onChange={(v) => setLeaseField(k, v as never)} />
    </Field>
  );

  return (
    <div className="space-y-6">
      {documentId && (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-600">Extraction confidence:</span>
          <StatusBadge
            status={initial.confidence}
            variant={confidenceVariant[initial.confidence] ?? 'gray'}
          />
        </div>
      )}
      {initial.notes && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded p-3 text-sm">
          <strong>Notes from parser:</strong> {initial.notes}
        </div>
      )}

      {/* Link to property/unit */}
      <Card className="p-5">
        <h3 className="font-semibold text-gray-900 mb-3">Property &amp; Unit</h3>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Property" required>
            <Select
              value={propertyId}
              onChange={setPropertyId}
              options={properties.map((p) => ({ value: p.id, label: p.name }))}
              placeholder="Select property…"
            />
          </Field>
          <Field label="Unit" required>
            <Select
              value={unitId}
              onChange={setUnitId}
              options={units.map((u) => ({ value: u.id, label: `Unit ${u.unit_number}` }))}
              placeholder={propertyId ? 'Select unit…' : 'Choose a property first'}
            />
          </Field>
        </div>
        {lease.property_address && (
          <p className="text-xs text-gray-500 mt-2">Parsed address: {lease.property_address}{lease.unit_number ? `, Unit ${lease.unit_number}` : ''}</p>
        )}
      </Card>

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        {/* Tenants */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900">Tenants</h3>
            <button
              type="button"
              onClick={() => setTenants((p) => [...p, {}])}
              className="text-sm text-blue-600 hover:underline"
            >
              + Add tenant
            </button>
          </div>
          <div className="space-y-5">
            {tenants.map((t, i) => (
              <div key={i} className="border border-gray-200 rounded p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500">
                    Tenant {i + 1}{i === 0 ? ' (primary)' : ''}
                  </span>
                  {tenants.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setTenants((p) => p.filter((_, idx) => idx !== i))}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="First name">
                    <TextInput value={t.first_name ?? ''} onChange={(v) => setTenantField(i, 'first_name', v)} />
                  </Field>
                  <Field label="Last name">
                    <TextInput value={t.last_name ?? ''} onChange={(v) => setTenantField(i, 'last_name', v)} />
                  </Field>
                  <Field label="Email">
                    <TextInput value={t.email ?? ''} onChange={(v) => setTenantField(i, 'email', v)} />
                  </Field>
                  <Field label="Phone">
                    <TextInput value={t.phone ?? ''} onChange={(v) => setTenantField(i, 'phone', v)} />
                  </Field>
                  <Field label="Employer">
                    <TextInput value={t.employer_name ?? ''} onChange={(v) => setTenantField(i, 'employer_name', v)} />
                  </Field>
                  <Field label="Job title">
                    <TextInput value={t.job_title ?? ''} onChange={(v) => setTenantField(i, 'job_title', v)} />
                  </Field>
                  <Field label="Annual income">
                    <NumberInput
                      value={numOrEmpty(t.annual_income)}
                      onChange={(v) => setTenantField(i, 'annual_income', v === '' ? null : v)}
                    />
                  </Field>
                  <Field label="Emergency contact">
                    <TextInput value={t.emergency_contact_name ?? ''} onChange={(v) => setTenantField(i, 'emergency_contact_name', v)} />
                  </Field>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Lease terms */}
        <Card className="p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Lease Terms</h3>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Start date" required>
              <TextInput type="date" value={lease.start_date ?? ''} onChange={(v) => setLeaseField('start_date', v || null)} />
            </Field>
            <Field label="End date" required>
              <TextInput type="date" value={lease.end_date ?? ''} onChange={(v) => setLeaseField('end_date', v || null)} />
            </Field>
            {num('Monthly rent', 'monthly_rent')}
            {num('Security deposit', 'security_deposit')}
            {num('Late fee', 'late_fee')}
            {num('Rent due day', 'rent_due_day')}
            {txt('Lease type', 'lease_type')}
            {txt('Payment frequency', 'payment_frequency')}
            {num('Occupancy limit', 'occupancy_limit')}
            {txt('Quiet hours', 'quiet_hours')}
            {bool('Pets allowed', 'pets_allowed')}
            {num('Pet deposit', 'pet_deposit')}
            {bool('Parking included', 'parking_included')}
            {num('Parking spaces', 'parking_spaces')}
            {bool('No smoking', 'no_smoking')}
            {bool('Trash included', 'trash_service_included')}
            {txt('Utilities included', 'utilities_included')}
            {txt('Lawn maintenance', 'lawn_maintenance_responsibility')}
            {bool('Early termination allowed', 'early_termination_allowed')}
            {num('Early term. penalty', 'early_termination_penalty')}
          </div>
          <div className="mt-3">
            <Field label="Special conditions">
              <Textarea value={lease.special_conditions ?? ''} onChange={(v) => setLeaseField('special_conditions', v || null)} />
            </Field>
          </div>
        </Card>
      </div>

      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={submit} disabled={submitting}>
          {submitting ? 'Creating…' : 'Confirm & Create Lease'}
        </Button>
      </div>
    </div>
  );
};
