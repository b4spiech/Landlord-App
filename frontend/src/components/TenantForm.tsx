import { useState } from 'react';
import { getErrorMessage, tenantAPI } from '../services/api';
import type { Tenant } from '../types';
import { Field, TextInput } from './FormFields';
import { Button } from './ui';
import { useToast } from './Toast';

interface Props {
  existing?: Tenant;
  onSaved: (t: Tenant) => void;
  onCancel: () => void;
}

export const TenantForm: React.FC<Props> = ({ existing, onSaved, onCancel }) => {
  const toast = useToast();
  const [firstName, setFirstName] = useState(existing?.first_name ?? '');
  const [lastName, setLastName] = useState(existing?.last_name ?? '');
  const [email, setEmail] = useState(existing?.email ?? '');
  const [phone, setPhone] = useState(existing?.phone ?? '');
  const [emName, setEmName] = useState(existing?.emergency_contact_name ?? '');
  const [emPhone, setEmPhone] = useState(existing?.emergency_contact_phone ?? '');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!firstName.trim()) e.firstName = 'First name is required';
    if (!lastName.trim()) e.lastName = 'Last name is required';
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Enter a valid email';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    const body = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      email: email.trim() || null,
      phone: phone.trim() || null,
      emergency_contact_name: emName.trim() || null,
      emergency_contact_phone: emPhone.trim() || null,
    };
    try {
      const t = existing
        ? await tenantAPI.update(existing.id, body)
        : await tenantAPI.create(body);
      toast.success(existing ? 'Tenant updated' : 'Tenant created');
      onSaved(t);
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
        <Field label="First name" required error={errors.firstName}>
          <TextInput value={firstName} onChange={setFirstName} />
        </Field>
        <Field label="Last name" required error={errors.lastName}>
          <TextInput value={lastName} onChange={setLastName} />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Email" error={errors.email}>
          <TextInput type="email" value={email} onChange={setEmail} />
        </Field>
        <Field label="Phone">
          <TextInput value={phone} onChange={setPhone} />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Emergency contact">
          <TextInput value={emName} onChange={setEmName} />
        </Field>
        <Field label="Emergency phone">
          <TextInput value={emPhone} onChange={setEmPhone} />
        </Field>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : existing ? 'Save changes' : 'Create tenant'}
        </Button>
      </div>
    </form>
  );
};
