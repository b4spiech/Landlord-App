import { useState } from 'react';
import { getErrorMessage, leaseAPI } from '../services/api';
import type { Lease, LeaseStatus } from '../types';
import { Field, NumberInput, Select, Textarea, TextInput } from './FormFields';
import { Button } from './ui';
import { useToast } from './Toast';

const STATUSES: { value: LeaseStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'pending_signature', label: 'Pending Signature' },
  { value: 'expired', label: 'Expired' },
  { value: 'terminated', label: 'Terminated' },
  { value: 'broken', label: 'Broken' },
];

const numOrEmpty = (n?: number | null): number | '' => (n == null ? '' : n);

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

interface Props {
  lease: Lease;
  onSaved: () => void;
  onCancel: () => void;
}

export const LeaseEditForm: React.FC<Props> = ({ lease, onSaved, onCancel }) => {
  const toast = useToast();
  const [form, setForm] = useState<Partial<Lease>>({ ...lease });
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = <K extends keyof Lease>(k: K, v: Lease[K] | null) =>
    setForm((p) => ({ ...p, [k]: v }));

  const txt = (label: string, k: keyof Lease) => (
    <Field label={label}>
      <TextInput value={(form[k] as string) ?? ''} onChange={(v) => set(k, (v || null) as never)} />
    </Field>
  );
  const num = (label: string, k: keyof Lease) => (
    <Field label={label}>
      <NumberInput
        value={numOrEmpty(form[k] as number | null)}
        onChange={(v) => set(k, (v === '' ? null : v) as never)}
      />
    </Field>
  );
  const bool = (label: string, k: keyof Lease) => (
    <Field label={label}>
      <BoolSelect value={form[k] as boolean | null} onChange={(v) => set(k, v as never)} />
    </Field>
  );

  const handleSubmit = async () => {
    const e: Record<string, string> = {};
    if (!form.start_date) e.start_date = 'Required';
    if (!form.end_date) e.end_date = 'Required';
    if (form.monthly_rent == null || form.monthly_rent <= 0) e.monthly_rent = 'Enter a rent';
    setErrors(e);
    if (Object.keys(e).length) return;

    setSubmitting(true);
    try {
      await leaseAPI.update(lease.id, form);
      toast.success('Lease updated');
      onSaved();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={(ev) => {
        ev.preventDefault();
        handleSubmit();
      }}
      className="space-y-5"
    >
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Core</h3>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Status">
            <Select
              value={(form.status as string) ?? 'draft'}
              onChange={(v) => set('status', v as LeaseStatus)}
              options={STATUSES}
            />
          </Field>
          <div />
          <Field label="Start date" required error={errors.start_date}>
            <TextInput type="date" value={(form.start_date as string) ?? ''} onChange={(v) => set('start_date', (v || null) as never)} />
          </Field>
          <Field label="End date" required error={errors.end_date}>
            <TextInput type="date" value={(form.end_date as string) ?? ''} onChange={(v) => set('end_date', (v || null) as never)} />
          </Field>
          <Field label="Monthly rent" required error={errors.monthly_rent}>
            <NumberInput value={numOrEmpty(form.monthly_rent)} onChange={(v) => set('monthly_rent', (v === '' ? null : v) as never)} />
          </Field>
          {num('Security deposit', 'security_deposit')}
          {num('Late fee', 'late_fee')}
          {num('Rent due day', 'rent_due_day')}
          {num('Grace period (days)', 'grace_period_days')}
          {txt('Lease type', 'lease_type')}
          {txt('Payment frequency', 'payment_frequency')}
          {num('Returned check fee', 'returned_check_fee')}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Occupancy, pets &amp; parking</h3>
        <div className="grid grid-cols-2 gap-3">
          {num('Occupancy limit', 'occupancy_limit')}
          {bool('Pets allowed', 'pets_allowed')}
          {num('Pet deposit', 'pet_deposit')}
          {num('Pet monthly fee', 'pet_monthly_fee')}
          {txt('Pet restrictions', 'pet_restrictions')}
          {bool('Parking included', 'parking_included')}
          {num('Parking spaces', 'parking_spaces')}
          {num('Parking fee', 'parking_additional_fee')}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Rules, utilities &amp; termination</h3>
        <div className="grid grid-cols-2 gap-3">
          {bool('No smoking', 'no_smoking')}
          {bool('No waterbeds', 'no_waterbeds')}
          {txt('Quiet hours', 'quiet_hours')}
          {txt('Lawn maintenance', 'lawn_maintenance_responsibility')}
          {bool('Trash included', 'trash_service_included')}
          {txt('Utilities included', 'utilities_included')}
          {txt('Utilities (tenant)', 'utilities_tenant_responsibility')}
          {bool('Early termination allowed', 'early_termination_allowed')}
          {num('Early term. penalty', 'early_termination_penalty')}
          {num('Early term. notice (days)', 'early_termination_notice_days')}
        </div>
      </section>

      <Field label="Renewal terms">
        <Textarea value={(form.renewal_terms as string) ?? ''} onChange={(v) => set('renewal_terms', (v || null) as never)} />
      </Field>
      <Field label="Special conditions">
        <Textarea value={(form.special_conditions as string) ?? ''} onChange={(v) => set('special_conditions', (v || null) as never)} />
      </Field>
      <Field label="Notes">
        <Textarea value={(form.notes as string) ?? ''} onChange={(v) => set('notes', (v || null) as never)} />
      </Field>

      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
    </form>
  );
};
