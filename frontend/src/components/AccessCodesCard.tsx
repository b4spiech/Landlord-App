import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { accessCodeAPI, getErrorMessage } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { formatCalendarDate } from '../lib/listing';
import type { AccessCode, AccessCodeKind } from '../types';
import { Button, Card } from './ui';
import { Modal } from './Modal';
import { Field, TextInput } from './FormFields';
import { StatusBadge } from './StatusBadge';
import { useToast } from './Toast';

const fmtDateTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

const KIND_LABEL: Record<AccessCodeKind, string> = {
  one_time: 'tour codes (one-time)',
  tenant: 'tenant codes',
  landlord: 'landlord codes',
};

const Section = ({
  title,
  hint,
  action,
  children,
}: {
  title: string;
  hint: string;
  action: ReactNode;
  children: ReactNode;
}) => (
  <section className="border-t border-gray-100">
    <div className="px-5 pt-4 pb-2 flex items-start justify-between gap-3">
      <div>
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
        <p className="text-xs text-gray-500">{hint}</p>
      </div>
      {action}
    </div>
    {children}
  </section>
);

const Masked = ({ code, show }: { code: string; show: boolean }) => (
  <span className="font-mono text-base tracking-wider text-gray-900">
    {show ? code : '•'.repeat(Math.max(code.length, 4))}
  </span>
);

/**
 * Property-page card for all door codes: one-time tour codes (sent
 * automatically), pre-programmed tenant codes (assign / unassign), and the
 * landlord's own codes. Collapsed to a one-line summary until clicked.
 */
export const AccessCodesCard = ({ propertyId }: { propertyId: string }) => {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [reveal, setReveal] = useState(false); // tenant + landlord codes are masked by default
  const [adding, setAdding] = useState<AccessCodeKind | null>(null);
  const { data, loading, reload } = useAsync(
    () => accessCodeAPI.list(propertyId, showHistory),
    [propertyId, showHistory],
  );
  const { data: managed, reload: reloadManaged } = useAsync(
    () => accessCodeAPI.managed(propertyId),
    [propertyId],
  );
  const refresh = () => {
    reload();
    reloadManaged();
  };

  const act = async (fn: () => Promise<unknown>, success: string) => {
    try {
      await fn();
      toast.success(success);
      refresh();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const remove = (c: AccessCode, what: string) => {
    if (!window.confirm(`Remove ${what} ${c.code}? Only do this if it's no longer valid on the lock.`))
      return;
    act(() => accessCodeAPI.remove(c.id), `Removed ${c.code}`);
  };

  const active = data?.codes.filter((c) => c.status !== 'issued') ?? [];
  const issued = data?.codes.filter((c) => c.status === 'issued') ?? [];
  const tenantCodes = managed?.tenant_codes ?? [];
  const landlordCodes = managed?.landlord_codes ?? [];
  const assignedCount = tenantCodes.filter((c) => c.status === 'assigned').length;

  const addButton = (kind: AccessCodeKind) => (
    <Button variant="secondary" className="shrink-0 !px-3 !py-1 text-xs" onClick={() => setAdding(kind)}>
      + Add
    </Button>
  );

  return (
    <Card>
      <div className="px-5 py-4 flex items-center justify-between gap-3">
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
            {data && managed && (
              <p className="text-xs text-gray-500 mt-0.5">
                {data.available} tour code{data.available === 1 ? '' : 's'} available ·{' '}
                {tenantCodes.length} tenant ({assignedCount} assigned) · {landlordCodes.length}{' '}
                landlord
              </p>
            )}
          </span>
        </button>
        {open && (tenantCodes.length > 0 || landlordCodes.length > 0) && (
          <button
            onClick={() => setReveal((r) => !r)}
            className="text-xs text-gray-500 hover:text-blue-600 hover:underline"
          >
            {reveal ? 'Hide codes' : 'Show codes'}
          </button>
        )}
      </div>

      {data?.low_stock && (
        <div className="px-5 py-3 text-sm bg-amber-50 text-amber-900 border-t border-amber-100">
          {data.available === 0
            ? "No tour codes left — tours can't be approved until you add more."
            : `Only ${data.available} tour code${data.available === 1 ? '' : 's'} left. Add more from your lock's app.`}
        </div>
      )}

      {open && (
        <>
          {/* --- One-time tour codes --- */}
          <Section
            title="Tour codes (one-time)"
            hint="Each approved tour gets one, sent automatically 30 minutes before. Never reused."
            action={addButton('one_time')}
          >
            {loading && !data && <p className="px-5 pb-3 text-sm text-gray-500">Loading…</p>}
            {data && active.length === 0 && (
              <p className="px-5 pb-3 text-sm text-gray-500">None loaded.</p>
            )}
            <ul className="divide-y divide-gray-100">
              {active.map((c) => (
                <li key={c.id} className="px-5 py-2.5 flex items-center justify-between gap-4 text-sm">
                  <div className="min-w-0">
                    <Masked code={c.code} show />
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
                      variant={c.status === 'reserved' ? 'yellow' : 'green'}
                    />
                    {c.status === 'available' && (
                      <button
                        onClick={() => remove(c, 'tour code')}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            {data && data.issued > 0 && (
              <div className="px-5 py-2 text-sm">
                <button
                  onClick={() => setShowHistory((v) => !v)}
                  className="text-gray-500 hover:text-blue-600 hover:underline"
                >
                  {showHistory ? 'Hide' : 'Show'} {data.issued} sent code{data.issued === 1 ? '' : 's'}
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
            <div className="pb-2" />
          </Section>

          {/* --- Tenant codes --- */}
          <Section
            title="Tenant codes"
            hint="Pre-programmed codes you hand to tenants. Set back to “Not assigned” when they move out to return it to the pool."
            action={addButton('tenant')}
          >
            {managed && tenantCodes.length === 0 && (
              <p className="px-5 pb-3 text-sm text-gray-500">None loaded.</p>
            )}
            <ul className="divide-y divide-gray-100 pb-2">
              {tenantCodes.map((c) => (
                <li
                  key={c.id}
                  className="px-5 py-2.5 flex flex-wrap items-center justify-between gap-3 text-sm"
                >
                  <div className="min-w-0">
                    <Masked code={c.code} show={reveal} />
                    <p className="text-xs text-gray-500">
                      {c.status === 'assigned'
                        ? `Assigned ${fmtDateTime(c.assigned_at)}`
                        : 'In the pool'}
                      {c.note ? ` · ${c.note}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <select
                      aria-label="Assign this code to a tenant"
                      value={c.tenant_id ?? ''}
                      onChange={(e) =>
                        e.target.value
                          ? act(() => accessCodeAPI.assign(c.id, e.target.value), 'Code assigned')
                          : act(() => accessCodeAPI.unassign(c.id), 'Code returned to the pool')
                      }
                      className="rounded border border-gray-300 px-2 py-1 text-sm max-w-[14rem]"
                    >
                      <option value="">Not assigned</option>
                      {managed?.tenants.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                          {t.on_current_lease ? ' (current lease)' : ''}
                        </option>
                      ))}
                    </select>
                    {c.status !== 'assigned' && (
                      <button
                        onClick={() => remove(c, 'tenant code')}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </Section>

          {/* --- Landlord codes --- */}
          <Section
            title="Landlord codes"
            hint="Your own codes, for your reference."
            action={addButton('landlord')}
          >
            {managed && landlordCodes.length === 0 && (
              <p className="px-5 pb-3 text-sm text-gray-500">None saved.</p>
            )}
            <ul className="divide-y divide-gray-100 pb-2">
              {landlordCodes.map((c) => (
                <li key={c.id} className="px-5 py-2.5 flex items-center justify-between gap-4 text-sm">
                  <div className="min-w-0">
                    <Masked code={c.code} show={reveal} />
                    <p className="text-xs text-gray-500">
                      {c.note || `Added ${fmtDateTime(c.created_at)}`}
                    </p>
                  </div>
                  <button
                    onClick={() => remove(c, 'landlord code')}
                    className="text-xs text-red-600 hover:underline"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </Section>
        </>
      )}

      <Modal
        open={adding !== null}
        title={`Add ${adding ? KIND_LABEL[adding] : 'codes'}`}
        onClose={() => setAdding(null)}
      >
        {adding && (
          <AddCodesForm
            propertyId={propertyId}
            kind={adding}
            onDone={() => {
              setAdding(null);
              setOpen(true);
              refresh();
            }}
            onCancel={() => setAdding(null)}
          />
        )}
      </Modal>
    </Card>
  );
};

const AddCodesForm = ({
  propertyId,
  kind,
  onDone,
  onCancel,
}: {
  propertyId: string;
  kind: AccessCodeKind;
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
        kind,
        expires_on: kind === 'one_time' ? expires || null : null,
        note: note || null,
      });
      const extra = [
        r.duplicates.length
          ? `${r.duplicates.length} already on this property (${r.duplicates.join(', ')})`
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
          rows={kind === 'landlord' ? 2 : 6}
          placeholder={'One per line (or separated by commas)\n482913\n705126'}
          className="w-full rounded border border-gray-300 px-3 py-2 font-mono text-sm"
          autoFocus
        />
      </Field>
      <p className="-mt-2 text-xs text-gray-500">3–20 characters each: digits, letters, * or #.</p>
      <div className={`grid gap-4 ${kind === 'one_time' ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {kind === 'one_time' && (
          <Field label="Expires on (optional)">
            <input
              type="date"
              value={expires}
              onChange={(e) => setExpires(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </Field>
        )}
        <Field label={kind === 'landlord' ? 'Label (optional)' : 'Note (optional)'}>
          <TextInput
            value={note}
            onChange={setNote}
            placeholder={kind === 'landlord' ? 'e.g. Owner – front door' : 'e.g. Front door lock'}
          />
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
