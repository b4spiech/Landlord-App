import { useState } from 'react';
import { Link } from 'react-router-dom';
import { accessCodeAPI, getErrorMessage } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { formatCalendarDate } from '../lib/listing';
import type { AccessCode } from '../types';
import { Button, Card } from './ui';
import { Modal } from './Modal';
import { Field, TextInput } from './FormFields';
import { StatusBadge } from './StatusBadge';
import { useToast } from './Toast';

const fmtDateTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

const statusVariant = (s: AccessCode['status']) =>
  s === 'available' ? 'green' : s === 'reserved' ? 'yellow' : 'gray';

/** Property-page card: the property's pool of one-time door codes. */
export const AccessCodesCard = ({ propertyId }: { propertyId: string }) => {
  const toast = useToast();
  const [open, setOpen] = useState(false); // collapsed by default: rarely needed
  const [showHistory, setShowHistory] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const { data, loading, reload } = useAsync(
    () => accessCodeAPI.list(propertyId, showHistory),
    [propertyId, showHistory],
  );

  const remove = async (c: AccessCode) => {
    if (!window.confirm(`Remove code ${c.code}? Only do this if it's no longer valid on the lock.`))
      return;
    try {
      await accessCodeAPI.remove(c.id);
      toast.success(`Removed ${c.code}`);
      reload();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const active = data?.codes.filter((c) => c.status !== 'issued') ?? [];
  const issued = data?.codes.filter((c) => c.status === 'issued') ?? [];

  return (
    <Card>
      <div
        className={`px-5 py-4 flex items-center justify-between gap-3 ${open ? 'border-b border-gray-200' : ''}`}
      >
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex flex-1 items-start gap-2 text-left"
        >
          <svg
            className={`mt-1 h-4 w-4 shrink-0 text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`}
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M7.21 14.77a.75.75 0 01.02-1.06L11.17 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
              clipRule="evenodd"
            />
          </svg>
          <span>
            <h2 className="font-semibold text-gray-900">Door codes</h2>
            {data && (
              <p className="text-xs text-gray-500 mt-0.5">
                {data.available} available · {data.reserved} held for tours · {data.issued} sent
              </p>
            )}
          </span>
        </button>
        <Button variant="secondary" onClick={() => setAddOpen(true)}>
          + Add codes
        </Button>
      </div>

      {data?.low_stock && (
        <div className="px-5 py-3 text-sm bg-amber-50 text-amber-900 border-b border-amber-100">
          {data.available === 0
            ? "No codes left — tours can't be approved until you add more."
            : `Only ${data.available} code${data.available === 1 ? '' : 's'} left. Add more from your lock's app.`}
        </div>
      )}

      {open && (
        <>
          {loading && !data && <p className="px-5 py-4 text-sm text-gray-500">Loading…</p>}
          {data && active.length === 0 && (
            <p className="px-5 py-4 text-sm text-gray-500">
              No codes loaded. Create one-time codes in your lock's app, then add them here. Each
              approved tour gets one, sent 30 minutes before the tour.
            </p>
          )}

          {active.length > 0 && (
            <ul className="divide-y divide-gray-100">
              {active.map((c) => (
                <li
                  key={c.id}
                  className="px-5 py-3 flex items-center justify-between gap-4 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-mono text-base tracking-wider text-gray-900">{c.code}</p>
                    <p className="text-xs text-gray-500">
                      {c.status === 'reserved' && c.tour_request_id ? (
                        <>
                          Held for{' '}
                          <Link
                            to={`/tour-requests/${c.tour_request_id}`}
                            className="text-blue-600 hover:underline"
                          >
                            {c.tour_visitor}
                          </Link>
                        </>
                      ) : (
                        `Added ${fmtDateTime(c.created_at)}`
                      )}
                      {c.expires_on ? ` · expires ${formatCalendarDate(c.expires_on)}` : ''}
                      {c.note ? ` · ${c.note}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <StatusBadge
                      status={c.status === 'reserved' ? 'Held' : 'Available'}
                      variant={statusVariant(c.status)}
                    />
                    {c.status === 'available' && (
                      <button
                        onClick={() => remove(c)}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {data && data.issued > 0 && (
            <div className="px-5 py-3 border-t border-gray-100 text-sm">
              <button
                onClick={() => setShowHistory((v) => !v)}
                className="text-gray-500 hover:text-blue-600 hover:underline"
              >
                {showHistory ? 'Hide' : 'Show'} {data.issued} sent code
                {data.issued === 1 ? '' : 's'}
              </button>
              {showHistory && (
                <ul className="mt-2 space-y-1">
                  {issued.map((c) => (
                    <li key={c.id} className="flex justify-between gap-4 text-xs text-gray-500">
                      <span className="font-mono text-gray-700">{c.code}</span>
                      <span>
                        Sent {fmtDateTime(c.issued_at)} to{' '}
                        {c.tour_request_id ? (
                          <Link
                            to={`/tour-requests/${c.tour_request_id}`}
                            className="text-blue-600 hover:underline"
                          >
                            {c.tour_visitor}
                          </Link>
                        ) : (
                          '—'
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}

      <Modal open={addOpen} title="Add door codes" onClose={() => setAddOpen(false)}>
        <AddCodesForm
          propertyId={propertyId}
          onDone={() => {
            setAddOpen(false);
            reload();
          }}
          onCancel={() => setAddOpen(false)}
        />
      </Modal>
    </Card>
  );
};

const AddCodesForm = ({
  propertyId,
  onDone,
  onCancel,
}: {
  propertyId: string;
  onDone: () => void;
  onCancel: () => void;
}) => {
  const toast = useToast();
  const [codes, setCodes] = useState('');
  const [expires, setExpires] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      const r = await accessCodeAPI.add(propertyId, {
        codes,
        expires_on: expires || null,
        note: note || null,
      });
      const extra = [
        r.duplicates.length
          ? `${r.duplicates.length} already loaded (${r.duplicates.join(', ')})`
          : '',
        r.invalid.length ? `${r.invalid.length} skipped as invalid (${r.invalid.join(', ')})` : '',
      ].filter(Boolean);
      toast.success(
        `Added ${r.added} code${r.added === 1 ? '' : 's'}${extra.length ? ' — ' + extra.join('; ') : ''}`,
      );
      onDone();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Field label="Codes" required>
        <textarea
          value={codes}
          onChange={(e) => setCodes(e.target.value)}
          rows={6}
          placeholder={'One per line (or separated by commas)\n482913\n705126'}
          className="w-full rounded border border-gray-300 px-3 py-2 font-mono text-sm"
          autoFocus
        />
      </Field>
      <p className="-mt-2 text-xs text-gray-500">3–20 characters each: digits, letters, * or #.</p>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Expires on (optional)">
          <input
            type="date"
            value={expires}
            onChange={(e) => setExpires(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </Field>
        <Field label="Note (optional)">
          <TextInput value={note} onChange={setNote} placeholder="e.g. Front door lock" />
        </Field>
      </div>
      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || !codes.trim()}>
          Add codes
        </Button>
      </div>
    </form>
  );
};
