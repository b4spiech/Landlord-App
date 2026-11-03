import { useState } from 'react';
import { Link } from 'react-router-dom';
import { accessCodeAPI, getErrorMessage, tourRequestAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import type { TourRequest } from '../types';
import { Button, Card } from './ui';
import { useToast } from './Toast';
import { TOURS_CHANGED } from '../lib/tours';

const fmtDateTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

/** Approve / decline a pending request; send the code or cancel an approved one. */
export const TourDecisionPanel = ({
  request: r,
  onChanged,
}: {
  request: TourRequest;
  onChanged: () => void;
}) => {
  const toast = useToast();
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const { data: codes } = useAsync(
    () => (r.status === 'pending' ? accessCodeAPI.list(r.property_id) : Promise.resolve(null)),
    [r.property_id, r.status],
  );

  const run = async (action: () => Promise<unknown>, success: string, confirm?: string) => {
    if (confirm && !window.confirm(confirm)) return;
    setBusy(true);
    try {
      await action();
      toast.success(success);
      setNote('');
      window.dispatchEvent(new Event(TOURS_CHANGED));
      onChanged();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const tourPassed = new Date(r.tour_start) <= new Date();
  const noteBox = (placeholder: string) => (
    <textarea
      value={note}
      onChange={(e) => setNote(e.target.value)}
      rows={2}
      maxLength={500}
      placeholder={placeholder}
      className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
    />
  );

  if (r.status === 'pending') {
    const noCodes = codes && codes.available === 0;
    return (
      <Card className="p-5 mb-6 space-y-3 border-yellow-200 bg-yellow-50">
        <h2 className="font-semibold text-gray-900">Review this request</h2>
        <p className="text-sm text-gray-700">
          <strong>Approve</strong> holds a door code and tells them the one-time code arrives 30
          minutes before the tour. <strong>Decline</strong> sends a short, polite no and frees the
          time slot.
          {r.sms_consent
            ? ' They will get an email and a text.'
            : ' They will get an email (no texts — they did not opt in).'}
        </p>
        {codes && (
          <p className={`text-sm ${noCodes ? 'text-red-700 font-medium' : 'text-gray-600'}`}>
            {noCodes ? (
              <>
                No door codes left for this property.{' '}
                <Link to={`/properties/${r.property_id}`} className="underline">
                  Add codes
                </Link>{' '}
                before approving.
              </>
            ) : (
              `${codes.available} door code${codes.available === 1 ? '' : 's'} available.`
            )}
          </p>
        )}
        {noteBox(
          'Optional note to include in the message (e.g. parking instructions, or a reason for declining)',
        )}
        <div className="flex flex-wrap gap-3">
          <Button
            className="bg-green-600 hover:bg-green-700"
            disabled={busy || !!noCodes || tourPassed}
            onClick={() =>
              run(
                () => tourRequestAPI.approve(r.id, note || undefined),
                'Approved — visitor notified',
              )
            }
          >
            Approve
          </Button>
          <Button
            variant="danger"
            disabled={busy}
            onClick={() =>
              run(
                () => tourRequestAPI.decline(r.id, note || undefined),
                'Declined — visitor notified',
                `Decline ${r.first_name}'s tour request? They'll be notified.`,
              )
            }
          >
            Decline
          </Button>
        </div>
        {tourPassed && (
          <p className="text-xs text-gray-500">
            This tour time has passed, so it can't be approved.
          </p>
        )}
      </Card>
    );
  }

  if (r.status === 'approved') {
    const sent = r.access_code_status === 'issued';
    return (
      <Card className="p-5 mb-6 space-y-3 border-green-200 bg-green-50">
        <h2 className="font-semibold text-gray-900">Approved</h2>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
          <span>
            Door code:{' '}
            <span className="font-mono text-base font-semibold tracking-wider">
              {r.access_code ?? '—'}
            </span>
          </span>
          <span className="text-gray-700">
            {r.code_sent_at
              ? `Sent ${fmtDateTime(r.code_sent_at)}`
              : sent
                ? 'Code issued but not delivered — check Messages below, then resend.'
                : 'Not sent yet — it goes out 30 minutes before the tour.'}
          </span>
        </div>
        <p className="text-xs text-gray-600">
          Until automatic sending is switched on, use <strong>Send code now</strong> about 30
          minutes before the tour. The message includes the code and the visit rules (shoes off,
          lights off, lock the door).
        </p>
        {noteBox('Optional note if you cancel')}
        <div className="flex flex-wrap gap-3">
          <Button
            disabled={busy}
            onClick={() =>
              run(
                () => tourRequestAPI.sendCode(r.id),
                sent ? 'Code re-sent' : 'Code sent',
                sent
                  ? `Resend code ${r.access_code} to ${r.first_name}?`
                  : `Send door code ${r.access_code ?? ''} to ${r.first_name} now? It can only be used once.`,
              )
            }
          >
            {sent ? 'Resend code' : 'Send code now'}
          </Button>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() =>
              run(
                () => tourRequestAPI.cancel(r.id, note || undefined),
                'Tour cancelled — visitor notified',
                `Cancel ${r.first_name}'s tour? They'll be notified${sent ? '' : ' and the held code goes back to the pool'}.`,
              )
            }
          >
            Cancel tour
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4 mb-6 text-sm text-gray-700">
      {r.status === 'declined' ? 'Declined' : r.status === 'cancelled' ? 'Cancelled' : 'Completed'}{' '}
      {fmtDateTime(r.decided_at)}
      {r.decision_note ? ` · Note: “${r.decision_note}”` : ''}
    </Card>
  );
};
