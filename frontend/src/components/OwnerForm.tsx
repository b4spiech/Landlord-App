import { useState } from 'react';
import { getErrorMessage, ownerAPI } from '../services/api';
import type { Owner } from '../types';
import { Field, TextInput } from './FormFields';
import { Button } from './ui';
import { useToast } from './Toast';

interface Props {
  onSaved: (o: Owner) => void;
  onCancel: () => void;
}

export const OwnerForm: React.FC<Props> = ({ onSaved, onCancel }) => {
  const toast = useToast();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [isEntity, setIsEntity] = useState(false);
  const [address1, setAddress1] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [postal, setPostal] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = 'Name is required';
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Enter a valid email';
    if (state && !/^[A-Za-z]{2}$/.test(state)) e.state = 'Use the 2-letter state code';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    try {
      const owner = await ownerAPI.create({
        name: name.trim(),
        email: email.trim() || null,
        phone: phone.trim() || null,
        is_entity: isEntity,
        address_line1: address1.trim() || null,
        city: city.trim() || null,
        state: state ? state.toUpperCase() : null,
        postal_code: postal.trim() || null,
      });
      toast.success('Owner created');
      onSaved(owner);
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
        <TextInput value={name} onChange={setName} placeholder="Brad Spiech or APEX Element Group LLC" />
      </Field>
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" checked={isEntity} onChange={(e) => setIsEntity(e.target.checked)} />
        This owner is a company / LLC (not an individual)
      </label>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Email" error={errors.email}>
          <TextInput type="email" value={email} onChange={setEmail} />
        </Field>
        <Field label="Phone">
          <TextInput value={phone} onChange={setPhone} />
        </Field>
      </div>
      <Field label="Street address">
        <TextInput value={address1} onChange={setAddress1} />
      </Field>
      <div className="grid grid-cols-3 gap-4">
        <Field label="City">
          <TextInput value={city} onChange={setCity} />
        </Field>
        <Field label="State" error={errors.state}>
          <TextInput value={state} onChange={setState} placeholder="MI" />
        </Field>
        <Field label="ZIP">
          <TextInput value={postal} onChange={setPostal} />
        </Field>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Create owner'}
        </Button>
      </div>
    </form>
  );
};
