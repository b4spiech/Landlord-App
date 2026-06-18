import { useEffect, useMemo, useState } from 'react';
import { getErrorMessage, leaseAPI, propertyAPI, tenantAPI, unitAPI } from '../services/api';
import type { LeaseStatus, Property, Tenant, Unit } from '../types';
import { Field, NumberInput, Select, TextInput } from './FormFields';
import { Button } from './ui';
import { useToast } from './Toast';

const STATUSES: { value: LeaseStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'pending_signature', label: 'Pending Signature' },
  { value: 'expired', label: 'Expired' },
  { value: 'terminated', label: 'Terminated' },
];

interface Props {
  onSaved: () => void;
  onCancel: () => void;
}

export const LeaseForm: React.FC<Props> = ({ onSaved, onCancel }) => {
  const toast = useToast();
  const [properties, setProperties] = useState<Property[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);

  const [propertyId, setPropertyId] = useState('');
  const [unitId, setUnitId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [rent, setRent] = useState<number | ''>('');
  const [deposit, setDeposit] = useState<number | ''>('');
  const [status, setStatus] = useState<LeaseStatus>('draft');
  const [selectedTenants, setSelectedTenants] = useState<string[]>([]);
  const [primaryTenant, setPrimaryTenant] = useState('');

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([propertyAPI.list(), tenantAPI.list()])
      .then(([p, t]) => {
        setProperties(p);
        setTenants(t);
      })
      .catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reload units when the selected property changes.
  useEffect(() => {
    if (!propertyId) {
      setUnits([]);
      setUnitId('');
      return;
    }
    unitAPI
      .list({ property_id: propertyId })
      .then((u) => {
        setUnits(u);
        setUnitId(u[0]?.id ?? '');
      })
      .catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propertyId]);

  const toggleTenant = (id: string) => {
    setSelectedTenants((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      if (next.length && !next.includes(primaryTenant)) setPrimaryTenant(next[0]);
      if (!next.length) setPrimaryTenant('');
      return next;
    });
  };

  const propertyOptions = useMemo(
    () => properties.map((p) => ({ value: p.id, label: p.name })),
    [properties],
  );
  const unitOptions = useMemo(
    () => units.map((u) => ({ value: u.id, label: `Unit ${u.unit_number}` })),
    [units],
  );

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!propertyId) e.propertyId = 'Select a property';
    if (!unitId) e.unitId = 'Select a unit';
    if (!startDate) e.startDate = 'Start date is required';
    if (!endDate) e.endDate = 'End date is required';
    if (startDate && endDate && endDate < startDate) e.endDate = 'End date must be after start date';
    if (rent === '' || rent <= 0) e.rent = 'Enter a monthly rent';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    try {
      await leaseAPI.create({
        property_id: propertyId,
        unit_id: unitId,
        start_date: startDate,
        end_date: endDate,
        monthly_rent: rent === '' ? 0 : rent,
        security_deposit: deposit === '' ? 0 : deposit,
        status,
        lease_tenants: selectedTenants.map((tid) => ({
          tenant_id: tid,
          is_primary: tid === primaryTenant,
          is_guarantor: false,
        })),
      });
      toast.success('Lease created');
      onSaved();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit();
      }}
      className="space-y-4"
    >
      <div className="grid grid-cols-2 gap-4">
        <Field label="Property" required error={errors.propertyId}>
          <Select
            value={propertyId}
            onChange={setPropertyId}
            options={propertyOptions}
            placeholder="Select property…"
          />
        </Field>
        <Field label="Unit" required error={errors.unitId}>
          <Select
            value={unitId}
            onChange={setUnitId}
            options={unitOptions}
            placeholder={propertyId ? 'Select unit…' : 'Choose a property first'}
          />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Start date" required error={errors.startDate}>
          <TextInput type="date" value={startDate} onChange={setStartDate} />
        </Field>
        <Field label="End date" required error={errors.endDate}>
          <TextInput type="date" value={endDate} onChange={setEndDate} />
        </Field>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Field label="Monthly rent" required error={errors.rent}>
          <NumberInput value={rent} onChange={setRent} min={0} placeholder="2400" />
        </Field>
        <Field label="Security deposit">
          <NumberInput value={deposit} onChange={setDeposit} min={0} />
        </Field>
        <Field label="Status">
          <Select value={status} onChange={(v) => setStatus(v as LeaseStatus)} options={STATUSES} />
        </Field>
      </div>

      <Field label="Tenants" error={errors.tenants}>
        {tenants.length === 0 ? (
          <p className="text-sm text-gray-500">No tenants on file yet.</p>
        ) : (
          <div className="space-y-2 max-h-44 overflow-y-auto border border-gray-200 rounded p-3">
            {tenants.map((t) => {
              const checked = selectedTenants.includes(t.id);
              return (
                <div key={t.id} className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={checked} onChange={() => toggleTenant(t.id)} />
                    {t.first_name} {t.last_name}
                  </label>
                  {checked && (
                    <label className="flex items-center gap-1 text-xs text-gray-500">
                      <input
                        type="radio"
                        name="primary"
                        checked={primaryTenant === t.id}
                        onChange={() => setPrimaryTenant(t.id)}
                      />
                      Primary
                    </label>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Field>

      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Create lease'}
        </Button>
      </div>
    </form>
  );
};
