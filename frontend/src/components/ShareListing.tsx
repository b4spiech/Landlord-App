import { useState } from 'react';
import { getErrorMessage, listingAPI, type ShareResult } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Button } from './ui';
import { Modal } from './Modal';
import { Field, TextInput } from './FormFields';
import { StatusBadge } from './StatusBadge';

const fmtDateTime = (iso?: string) =>
  iso ? new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '';

const statusVariant = (s: ShareResult['status']) =>
  s === 'sent' ? 'green' : s === 'failed' ? 'red' : 'gray';

/** "Share link" button: email and/or text a live listing to someone who asked about it. */
export const ShareListingButton = ({
  listingId,
  className = '',
}: {
  listingId: string;
  className?: string;
}) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="secondary" className={className} onClick={() => setOpen(true)}>
        Share link
      </Button>
      {open && <ShareDialog listingId={listingId} onClose={() => setOpen(false)} />}
    </>
  );
};

const ShareDialog = ({ listingId, onClose }: { listingId: string; onClose: () => void }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState<ShareResult[] | null>(null);
  const { data: history, reload } = useAsync(() => listingAPI.shares(listingId), [listingId]);

  const send = async () => {
    setError('');
    setBusy(true);
    try {
      setResults(
        await listingAPI.share(listingId, {
          name: name || undefined,
          email: email || undefined,
          phone: phone || undefined,
          note: note || undefined,
        }),
      );
      reload();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open title="Share this listing" onClose={onClose}>
      {results ? (
        <div className="space-y-4">
          <ul className="space-y-2 text-sm">
            {results.map((r) => (
              <li key={r.channel} className="flex items-start justify-between gap-3">
                <span>
                  {r.channel === 'email' ? 'Email' : 'Text'} to {r.recipient}
                  {r.status !== 'sent' && r.detail && (
                    <span className="block text-xs text-gray-500">
                      {r.channel === 'sms'
                        ? 'Texts will work once Twilio approves your number. '
                        : ''}
                      {r.detail}
                    </span>
                  )}
                </span>
                <StatusBadge status={r.status} variant={statusVariant(r.status)} />
              </li>
            ))}
          </ul>
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setResults(null);
                setName('');
                setEmail('');
                setPhone('');
                setNote('');
              }}
            >
              Share with someone else
            </Button>
            <Button onClick={onClose}>Done</Button>
          </div>
        </div>
      ) : (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <p className="text-sm text-gray-600">
            Sends the home's page (details and photos) with a <strong>Request a tour</strong>{' '}
            button.
          </p>
          <Field label="Their name (optional)">
            <TextInput value={name} onChange={setName} placeholder="Sam" />
          </Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Email">
              <TextInput
                value={email}
                onChange={setEmail}
                type="email"
                placeholder="sam@example.com"
              />
            </Field>
            <Field label="Mobile">
              <TextInput
                value={phone}
                onChange={setPhone}
                type="tel"
                placeholder="(555) 555-5555"
              />
            </Field>
          </div>
          {phone.trim() && (
            <p className="-mt-2 text-xs text-gray-500">
              Only text people who asked for the link. The text includes “Reply STOP to opt out.”
            </p>
          )}
          <Field label="Personal note (optional, email only)">
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              maxLength={500}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </Field>
          {error && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy || (!email.trim() && !phone.trim())}>
              {busy ? 'Sending…' : 'Send link'}
            </Button>
          </div>
        </form>
      )}

      {history && history.length > 0 && (
        <div className="mt-6 border-t pt-4">
          <h3 className="text-sm font-semibold text-gray-900">Shared before</h3>
          <ul className="mt-2 max-h-40 overflow-y-auto space-y-1 text-xs text-gray-600">
            {history.map((h, i) => (
              <li key={i} className="flex justify-between gap-3">
                <span>
                  {h.channel === 'email' ? 'Email' : 'Text'} · {h.recipient} ·{' '}
                  {fmtDateTime(h.created_at)}
                </span>
                <span
                  className={
                    h.status === 'sent'
                      ? 'text-green-700'
                      : h.status === 'failed'
                        ? 'text-red-700'
                        : ''
                  }
                >
                  {h.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  );
};
