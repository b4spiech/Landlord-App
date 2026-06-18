import { useEffect, useState } from 'react';
import {
  getErrorMessage,
  jurisdictionAPI,
  managementCompanyAPI,
  ownerAPI,
  propertyAPI,
} from '../services/api';
import type { ManagementCompany, Owner, Property, PropertyType } from '../types';
import { Field, NumberInput, Select, Textarea, TextInput } from './FormFields';
import { Button } from './ui';
import { Modal } from './Modal';
import { OwnerForm } from './OwnerForm';
import { ManagementCompanyForm } from './ManagementCompanyForm';
import { useToast } from './Toast';

const PROPERTY_TYPES: { value: PropertyType; label: string }[] = [
  { value: 'condo', label: 'Condo' },
  { value: 'single_family', label: 'Single Family' },
  { value: 'multi_family', label: 'Multi Family' },
  { value: 'townhouse', label: 'Townhouse' },
  { value: 'apartment', label: 'Apartment' },
  { value: 'commercial', label: 'Commercial' },
];

interface Props {
  existing?: Property;
  onSaved: (p: Property) => void;
  onCancel: () => void;
}

export const PropertyForm: React.FC<Props> = ({ existing, onSaved, onCancel }) => {
  const toast = useToast();
  const [owners, setOwners] = useState<{ value: string; label: string }[]>([]);
  const [companies, setCompanies] = useState<{ value: string; label: string }[]>([]);
  const [jurisdictions, setJurisdictions] = useState<{ value: string; label: string }[]>([]);

  const [name, setName] = useState(existing?.name ?? '');
  const [propertyType, setPropertyType] = useState<PropertyType>(existing?.property_type ?? 'condo');
  const [address1, setAddress1] = useState(existing?.address_line1 ?? '');
  const [address2, setAddress2] = useState(existing?.address_line2 ?? '');
  const [city, setCity] = useState(existing?.city ?? '');
  const [state, setState] = useState(existing?.state ?? '');
  const [postal, setPostal] = useState(existing?.postal_code ?? '');
  const [ownerId, setOwnerId] = useState(existing?.owner_id ?? '');
  const [companyId, setCompanyId] = useState(existing?.management_company_id ?? '');
  const [jurisdictionId, setJurisdictionId] = useState(existing?.jurisdiction_id ?? '');
  const [hoaName, setHoaName] = useState(existing?.hoa_name ?? '');
  const [bedrooms, setBedrooms] = useState<number | ''>(existing?.bedrooms ?? '');
  const [bathrooms, setBathrooms] = useState<number | ''>(existing?.bathrooms ?? '');
  const [notes, setNotes] = useState(existing?.notes ?? '');

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [ownerModalOpen, setOwnerModalOpen] = useState(false);
  const [companyModalOpen, setCompanyModalOpen] = useState(false);

  const handleOwnerCreated = (o: Owner) => {
    setOwners((prev) => [...prev, { value: o.id, label: o.name }]);
    setOwnerId(o.id);
    setOwnerModalOpen(false);
  };
  const handleCompanyCreated = (c: ManagementCompany) => {
    setCompanies((prev) => [...prev, { value: c.id, label: c.name }]);
    setCompanyId(c.id);
    setCompanyModalOpen(false);
  };

  useEffect(() => {
    Promise.all([ownerAPI.list(), managementCompanyAPI.list(), jurisdictionAPI.list()])
      .then(([o, c, j]) => {
        setOwners(o.map((x) => ({ value: x.id, label: x.name })));
        setCompanies(c.map((x) => ({ value: x.id, label: x.name })));
        setJurisdictions(j.map((x) => ({ value: x.id, label: x.name || x.state_name })));
        // Sensible defaults when creating the first property.
        if (!existing) {
          if (o[0]) setOwnerId(o[0].id);
          if (j[0]) setJurisdictionId(j[0].id);
        }
      })
      .catch((err) => toast.error(getErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = 'Name is required';
    if (!address1.trim()) e.address1 = 'Street address is required';
    if (!city.trim()) e.city = 'City is required';
    if (!/^[A-Za-z]{2}$/.test(state)) e.state = 'Use the 2-letter state code';
    if (!postal.trim()) e.postal = 'ZIP is required';
    if (!ownerId) e.ownerId = 'Select an owner';
    if (!jurisdictionId) e.jurisdictionId = 'Select a jurisdiction';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    const body = {
      name: name.trim(),
      property_type: propertyType,
      address_line1: address1.trim(),
      address_line2: address2.trim() || null,
      city: city.trim(),
      state: state.toUpperCase(),
      postal_code: postal.trim(),
      owner_id: ownerId,
      management_company_id: companyId || null,
      jurisdiction_id: jurisdictionId,
      hoa_name: hoaName.trim() || null,
      bedrooms: bedrooms === '' ? null : bedrooms,
      bathrooms: bathrooms === '' ? null : bathrooms,
      notes: notes.trim() || null,
    };
    try {
      const saved = existing
        ? await propertyAPI.update(existing.id, body)
        : await propertyAPI.create(body);
      toast.success(existing ? 'Property updated' : 'Property created');
      onSaved(saved);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
    <form
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit();
      }}
      className="space-y-4"
    >
      <Field label="Property name" required error={errors.name}>
        <TextInput value={name} onChange={setName} placeholder="Camino Pimeria Alta Unit 60" />
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Type" required>
          <Select
            value={propertyType}
            onChange={(v) => setPropertyType(v as PropertyType)}
            options={PROPERTY_TYPES}
          />
        </Field>
        <Field label="HOA name" error={errors.hoaName}>
          <TextInput value={hoaName} onChange={setHoaName} />
        </Field>
      </div>

      <Field label="Street address" required error={errors.address1}>
        <TextInput value={address1} onChange={setAddress1} placeholder="6255 N Camino Pimeria Alta" />
      </Field>
      <Field label="Address line 2" error={errors.address2}>
        <TextInput value={address2} onChange={setAddress2} placeholder="Unit 60" />
      </Field>

      <div className="grid grid-cols-3 gap-4">
        <Field label="City" required error={errors.city}>
          <TextInput value={city} onChange={setCity} />
        </Field>
        <Field label="State" required error={errors.state}>
          <TextInput value={state} onChange={setState} placeholder="AZ" />
        </Field>
        <Field label="ZIP" required error={errors.postal}>
          <TextInput value={postal} onChange={setPostal} />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Owner" required error={errors.ownerId}>
          <div className="flex gap-2">
            <div className="flex-1">
              <Select value={ownerId} onChange={setOwnerId} options={owners} placeholder="Select owner…" />
            </div>
            <Button variant="secondary" onClick={() => setOwnerModalOpen(true)}>
              + New
            </Button>
          </div>
        </Field>
        <Field label="Management company" error={errors.companyId}>
          <div className="flex gap-2">
            <div className="flex-1">
              <Select
                value={companyId ?? ''}
                onChange={setCompanyId}
                options={companies}
                placeholder="None"
              />
            </div>
            <Button variant="secondary" onClick={() => setCompanyModalOpen(true)}>
              + New
            </Button>
          </div>
        </Field>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Field label="Jurisdiction" required error={errors.jurisdictionId}>
          <Select
            value={jurisdictionId}
            onChange={setJurisdictionId}
            options={jurisdictions}
            placeholder="Select…"
          />
        </Field>
        <Field label="Bedrooms">
          <NumberInput value={bedrooms} onChange={setBedrooms} min={0} />
        </Field>
        <Field label="Bathrooms">
          <NumberInput value={bathrooms} onChange={setBathrooms} min={0} step={0.5} />
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
          {submitting ? 'Saving…' : existing ? 'Save changes' : 'Create property'}
        </Button>
      </div>
    </form>

    <Modal open={ownerModalOpen} title="Add Owner" onClose={() => setOwnerModalOpen(false)}>
      <OwnerForm onSaved={handleOwnerCreated} onCancel={() => setOwnerModalOpen(false)} />
    </Modal>
    <Modal
      open={companyModalOpen}
      title="Add Management Company"
      onClose={() => setCompanyModalOpen(false)}
    >
      <ManagementCompanyForm
        onSaved={handleCompanyCreated}
        onCancel={() => setCompanyModalOpen(false)}
      />
    </Modal>
    </>
  );
};
