import { useState } from 'react';
import { getErrorMessage, hoaAPI } from '../services/api';
import type { HOA } from '../types';
import { Field, NumberInput, Select, Textarea, TextInput } from './FormFields';
import { Button } from './ui';
import { useToast } from './Toast';

const FREQUENCIES = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'annual', label: 'Annual' },
];

interface Props {
  existing?: HOA;
  onSaved: (h: HOA) => void;
  onCancel: () => void;
}

export const HOAForm: React.FC<Props> = ({ existing, onSaved, onCancel }) => {
  const toast = useToast();
  const [name, setName] = useState(existing?.name ?? '');
  const [contactName, setContactName] = useState(existing?.contact_name ?? '');
  const [contactEmail, setContactEmail] = useState(existing?.contact_email ?? '');
  const [contactPhone, setContactPhone] = useState(existing?.contact_phone ?? '');
  const [website, setWebsite] = useState(existing?.website ?? '');
  const [mgmtName, setMgmtName] = useState(existing?.management_company_name ?? '');
  const [dues, setDues] = useState<number | ''>(existing?.dues_amount ?? '');
  const [duesFreq, setDuesFreq] = useState(existing?.dues_frequency ?? 'monthly');
  const [notes, setNotes] = useState(existing?.notes ?? '');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = 'Name is required';
    if (contactEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactEmail))
      e.contactEmail = 'Enter a valid email';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    const body = {
      name: name.trim(),
      contact_name: contactName.trim() || null,
      contact_email: contactEmail.trim() || null,
      contact_phone: contactPhone.trim() || null,
      website: website.trim() || null,
      management_company_name: mgmtName.trim() || null,
      dues_amount: dues === '' ? null : dues,
      dues_frequency: duesFreq || null,
      notes: notes.trim() || null,
    };
    try {
      const saved = existing ? await hoaAPI.update(existing.id, body) : await hoaAPI.create(body);
      toast.success(existing ? 'HOA updated' : 'HOA created');
      onSaved(saved);
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
      <Field label="HOA name" required error={errors.name}>
        <TextInput value={name} onChange={setName} placeholder="Camino Pimeria Alta Condo Association" />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Contact name">
          <TextInput value={contactName} onChange={setContactName} />
        </Field>
        <Field label="Management company">
          <TextInput value={mgmtName} onChange={setMgmtName} />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Contact email" error={errors.contactEmail}>
          <TextInput type="email" value={contactEmail} onChange={setContactEmail} />
        </Field>
        <Field label="Contact phone">
          <TextInput value={contactPhone} onChange={setContactPhone} />
        </Field>
      </div>
      <Field label="Website">
        <TextInput value={website} onChange={setWebsite} placeholder="https://…" />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Dues amount">
          <NumberInput value={dues} onChange={setDues} min={0} placeholder="350" />
        </Field>
        <Field label="Dues frequency">
          <Select value={duesFreq} onChange={setDuesFreq} options={FREQUENCIES} />
        </Field>
      </div>
      <Field label="Notes">
        <Textarea value={notes} onChange={setNotes} />
      </Field>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : existing ? 'Save changes' : 'Create HOA'}
        </Button>
      </div>
    </form>
  );
};
