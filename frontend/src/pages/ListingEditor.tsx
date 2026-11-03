import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getErrorMessage, listingAPI, propertyAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type {
  Listing,
  ListingChannelEntry,
  ListingChannelType,
  ListingCloseReason,
  ListingFields,
  ListingPhoto,
  PetPolicy,
  Property,
} from '../types';
import { Button, Card, ErrorState, PageHeader, Spinner } from '../components/ui';
import { Field, NumberInput, Select, Textarea, TextInput } from '../components/FormFields';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import { useToast } from '../components/Toast';
import {
  CHANNEL_LABELS,
  LISTING_STATUS_LABELS,
  PET_POLICY_LABELS,
  formatCalendarDate,
  listingStatusVariant,
} from '../lib/listing';

const petOptions = Object.entries(PET_POLICY_LABELS).map(([value, label]) => ({ value, label }));
const channelOptions = Object.entries(CHANNEL_LABELS).map(([value, label]) => ({ value, label }));
const today = () => new Date().toISOString().slice(0, 10);

interface FormState {
  headline: string;
  description: string;
  monthly_rent: number | '';
  security_deposit: number | '';
  available_date: string;
  lease_term_months: number | '';
  pet_policy: string;
  utilities_included: string;
  internal_notes: string;
  channels: ListingChannelEntry[];
}

const toForm = (l: Listing): FormState => ({
  headline: l.headline ?? '',
  description: l.description ?? '',
  monthly_rent: l.monthly_rent ?? '',
  security_deposit: l.security_deposit ?? '',
  available_date: l.available_date ?? '',
  lease_term_months: l.lease_term_months ?? '',
  pet_policy: l.pet_policy ?? '',
  utilities_included: l.utilities_included ?? '',
  internal_notes: l.internal_notes ?? '',
  channels: l.channels,
});

const toBody = (f: FormState): ListingFields => ({
  headline: f.headline.trim() || null,
  description: f.description.trim() || null,
  monthly_rent: f.monthly_rent === '' ? null : f.monthly_rent,
  security_deposit: f.security_deposit === '' ? null : f.security_deposit,
  available_date: f.available_date || null,
  lease_term_months: f.lease_term_months === '' ? null : f.lease_term_months,
  pet_policy: (f.pet_policy || null) as PetPolicy | null,
  utilities_included: f.utilities_included.trim() || null,
  internal_notes: f.internal_notes.trim() || null,
  channels: f.channels.map((c) => ({
    channel: c.channel,
    url: c.url?.trim() || null,
    listed_on: c.listed_on || null,
  })),
});

export const ListingEditor = () => {
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync(async () => {
    const listing = await listingAPI.get(id!);
    const [property, photos] = await Promise.all([
      propertyAPI.get(listing.property_id),
      listingAPI.photos(id!),
    ]);
    return { listing, property, photos };
  }, [id]);

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;
  // Remount the form whenever the saved listing changes so its state resets.
  return <ListingEditorForm key={data.listing.updated_at} {...data} reload={reload} />;
};

const ListingEditorForm = ({
  listing,
  property,
  photos: initialPhotos,
  reload,
}: {
  listing: Listing;
  property: Property;
  photos: ListingPhoto[];
  reload: () => void;
}) => {
  const toast = useToast();
  const [form, setForm] = useState<FormState>(() => toForm(listing));
  const [photos, setPhotos] = useState<ListingPhoto[]>(initialPhotos);
  const [saving, setSaving] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const isOpen = listing.status !== 'closed';
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const run = async (action: () => Promise<unknown>, success: string) => {
    setSaving(true);
    try {
      await action();
      toast.success(success);
      reload();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const save = () => run(() => listingAPI.update(listing.id, toBody(form)), 'Listing saved');
  const publish = () =>
    run(async () => {
      await listingAPI.update(listing.id, toBody(form));
      await listingAPI.publish(listing.id);
    }, 'Listing is live on the tour site');
  const unpublish = () => run(() => listingAPI.unpublish(listing.id), 'Taken off the tour site');
  const close = (reason: ListingCloseReason) => {
    setCloseOpen(false);
    run(() => listingAPI.close(listing.id, reason), reason === 'rented' ? 'Marked as rented' : 'Listing withdrawn');
  };

  const updateChannel = (i: number, patch: Partial<ListingChannelEntry>) =>
    set('channels', form.channels.map((c, j) => (j === i ? { ...c, ...patch } : c)));

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    try {
      await listingAPI.uploadPhotos(listing.id, Array.from(files));
      setPhotos(await listingAPI.photos(listing.id));
      toast.success(`${files.length} photo${files.length > 1 ? 's' : ''} added`);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      if (fileInput.current) fileInput.current.value = '';
    }
  };

  const move = async (index: number, delta: number) => {
    const next = [...photos];
    const [p] = next.splice(index, 1);
    next.splice(index + delta, 0, p);
    setPhotos(next);
    try {
      setPhotos(await listingAPI.reorderPhotos(listing.id, next.map((x) => x.id)));
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const removePhoto = async (photoId: string) => {
    try {
      await listingAPI.deletePhoto(listing.id, photoId);
      setPhotos((ps) => ps.filter((p) => p.id !== photoId));
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <div>
      <Link to={`/properties/${property.id}`} className="text-sm text-blue-600 hover:underline">
        &larr; {property.name}
      </Link>
      <PageHeader
        title="Listing"
        subtitle={`${property.address_line1}${property.address_line2 ? ', ' + property.address_line2 : ''}, ${property.city}, ${property.state}`}
        action={
          <StatusBadge
            status={
              listing.status === 'closed' && listing.close_reason
                ? `Closed — ${listing.close_reason}`
                : LISTING_STATUS_LABELS[listing.status]
            }
            variant={listingStatusVariant(listing.status)}
          />
        }
      />

      {listing.public_url && (
        <Card className="p-4 mb-6 flex flex-wrap items-center gap-3 justify-between bg-green-50 border-green-200">
          <div className="text-sm">
            <p className="font-medium text-green-900">Live on the tour site</p>
            <a href={listing.public_url} target="_blank" rel="noreferrer" className="text-green-800 underline break-all">
              {listing.public_url}
            </a>
          </div>
          <Button
            variant="secondary"
            onClick={() => navigator.clipboard.writeText(listing.public_url!).then(() => toast.success('Link copied'))}
          >
            Copy link
          </Button>
        </Card>
      )}

      {!isOpen && (
        <Card className="p-4 mb-6 text-sm text-gray-700">
          This listing was closed on {formatCalendarDate(listing.closed_at?.slice(0, 10))}. To list the
          property again, use “List this property” on the property page.
        </Card>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
      >
        <fieldset disabled={!isOpen || saving} className="grid lg:grid-cols-3 gap-6 items-start">
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-5 space-y-4">
              <h2 className="font-semibold text-gray-900">Details shown to renters</h2>
              <Field label="Headline">
                <TextInput
                  value={form.headline}
                  onChange={(v) => set('headline', v)}
                  placeholder="Bright 2 bd condo near Catalina Foothills (leave blank to auto-generate)"
                />
              </Field>
              <div className="grid sm:grid-cols-3 gap-4">
                <Field label="Monthly rent" required>
                  <NumberInput value={form.monthly_rent} onChange={(v) => set('monthly_rent', v)} min={0} step={25} />
                </Field>
                <Field label="Security deposit">
                  <NumberInput value={form.security_deposit} onChange={(v) => set('security_deposit', v)} min={0} step={25} />
                </Field>
                <Field label="Available" required>
                  <input
                    type="date"
                    value={form.available_date}
                    onChange={(e) => set('available_date', e.target.value)}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                  />
                </Field>
                <Field label="Minimum lease (months)">
                  <NumberInput value={form.lease_term_months} onChange={(v) => set('lease_term_months', v)} min={1} />
                </Field>
                <Field label="Pets">
                  <Select value={form.pet_policy} onChange={(v) => set('pet_policy', v)} options={petOptions} placeholder="Not specified" />
                </Field>
                <Field label="Utilities included">
                  <TextInput value={form.utilities_included} onChange={(v) => set('utilities_included', v)} placeholder="Water, trash" />
                </Field>
              </div>
              <Field label="Description">
                <Textarea value={form.description} onChange={(v) => set('description', v)} rows={6} />
              </Field>
            </Card>

            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900">Photos ({photos.length})</h2>
                {isOpen && (
                  <>
                    <input
                      ref={fileInput}
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      multiple
                      className="hidden"
                      onChange={(e) => upload(e.target.files)}
                    />
                    <Button variant="secondary" onClick={() => fileInput.current?.click()}>
                      + Add photos
                    </Button>
                  </>
                )}
              </div>
              {photos.length === 0 && (
                <p className="text-sm text-gray-500">No photos yet. The first photo is the cover image.</p>
              )}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {photos.map((p, i) => (
                  <div key={p.id} className="relative group rounded overflow-hidden border">
                    <img src={listingAPI.photoUrl(listing.id, p.id)} alt="" className="aspect-[4/3] w-full object-cover" />
                    {i === 0 && (
                      <span className="absolute top-1 left-1 rounded bg-blue-600 px-2 py-0.5 text-xs text-white">Cover</span>
                    )}
                    {isOpen && (
                      <div className="absolute bottom-0 inset-x-0 flex justify-between bg-black/50 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="flex gap-2">
                          <button type="button" disabled={i === 0} onClick={() => move(i, -1)} className="disabled:opacity-30">
                            ◀
                          </button>
                          <button type="button" disabled={i === photos.length - 1} onClick={() => move(i, 1)} className="disabled:opacity-30">
                            ▶
                          </button>
                        </span>
                        <button type="button" onClick={() => removePhoto(p.id)}>
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="p-5 space-y-3">
              <h2 className="font-semibold text-gray-900">Where it's listed</h2>
              {form.channels.length === 0 && (
                <p className="text-sm text-gray-500">Track where you've advertised this home.</p>
              )}
              {form.channels.map((c, i) => (
                <div key={i} className="space-y-2 rounded border p-3">
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <Select
                        value={c.channel}
                        onChange={(v) => updateChannel(i, { channel: v as ListingChannelType })}
                        options={channelOptions}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => set('channels', form.channels.filter((_, j) => j !== i))}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                  <TextInput value={c.url ?? ''} onChange={(v) => updateChannel(i, { url: v })} placeholder="Listing URL" />
                  <input
                    type="date"
                    value={c.listed_on ?? ''}
                    onChange={(e) => updateChannel(i, { listed_on: e.target.value })}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                  />
                  {c.url && /^https?:\/\//.test(c.url) && (
                    <a href={c.url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline">
                      Open listing ↗
                    </a>
                  )}
                </div>
              ))}
              {isOpen && (
                <Button
                  variant="secondary"
                  onClick={() =>
                    set('channels', [
                      ...form.channels,
                      { channel: form.channels.length ? 'other' : 'zillow_rental_manager', url: '', listed_on: today() },
                    ])
                  }
                >
                  + Add where it's listed
                </Button>
              )}
            </Card>

            <Card className="p-5 space-y-3">
              <h2 className="font-semibold text-gray-900">Private notes</h2>
              <Textarea value={form.internal_notes} onChange={(v) => set('internal_notes', v)} rows={3} />
              <p className="text-xs text-gray-500">Only visible to you.</p>
            </Card>

            {isOpen && (
              <Card className="p-5 space-y-3">
                <Button type="submit" className="w-full" disabled={saving}>
                  Save
                </Button>
                {listing.status === 'draft' ? (
                  <Button className="w-full bg-green-600 hover:bg-green-700" onClick={publish} disabled={saving}>
                    Save & publish to tour site
                  </Button>
                ) : (
                  <Button variant="secondary" className="w-full" onClick={unpublish} disabled={saving}>
                    Take off tour site (keep as draft)
                  </Button>
                )}
                <Button variant="secondary" className="w-full" onClick={() => setCloseOpen(true)} disabled={saving}>
                  Close listing…
                </Button>
              </Card>
            )}
          </div>
        </fieldset>
      </form>

      <Modal open={closeOpen} title="Close listing" onClose={() => setCloseOpen(false)}>
        <p className="text-sm text-gray-600 mb-4">
          Closing removes it from the tour site and ends this listing. Don't forget to take it down on
          Zillow and anywhere else it's posted.
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" onClick={() => close('withdrawn')}>
            Withdraw
          </Button>
          <Button onClick={() => close('rented')}>Mark as rented</Button>
        </div>
      </Modal>
    </div>
  );
};
