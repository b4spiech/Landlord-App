import { useState } from 'react';
import { getErrorMessage, managementCompanyAPI } from '../services/api';
import type { ManagementCompany } from '../types';
import { Field, TextInput } from './FormFields';
import { Button } from './ui';
import { useToast } from './Toast';

interface Props {
  existing?: ManagementCompany;
  onSaved: (c: ManagementCompany) => void;
  onCancel: () => void;
}

export const ManagementCompanyForm: React.FC<Props> = ({ existing, onSaved, onCancel }) => {
  const toast = useToast();
  const [name, setName] = useState(existing?.name ?? '');
  const [legalName, setLegalName] = useState(existing?.legal_name ?? '');
  const [email, setEmail] = useState(existing?.email ?? '');
  const [phone, setPhone] = useState(existing?.phone ?? '');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = 'Name is required';
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Enter a valid email';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    const body = {
      name: name.trim(),
      legal_name: legalName.trim() || null,
      email: email.trim() || null,
      phone: phone.trim() || null,
    };
    try {
      const company = existing
        ? await managementCompanyAPI.update(existing.id, body)
        : await managementCompanyAPI.create(body);
      toast.success(existing ? 'Management company updated' : 'Management company created');
      onSaved(company);
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
      <Field label="Name" required error={errors.name}>
        <TextInput value={name} onChange={setName} placeholder="APEX Element Group LLC" />
      </Field>
      <Field label="Legal name">
        <TextInput value={legalName} onChange={setLegalName} />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Email" error={errors.email}>
          <TextInput type="email" value={email} onChange={setEmail} />
        </Field>
        <Field label="Phone">
          <TextInput value={phone} onChange={setPhone} />
        </Field>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : existing ? 'Save changes' : 'Create company'}
        </Button>
      </div>
    </form>
  );
};
