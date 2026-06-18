import { useState } from 'react';
import { Button, Card } from './ui';

export interface DraftEmail {
  subject: string;
  to_emails: string[];
  cc_emails?: string[];
  body_html: string;
}

interface Props {
  email: DraftEmail;
  onApprove: () => void;
  onReject: (reason: string) => void;
  busy?: boolean;
}

/**
 * Human approval gate: renders a draft email for review and requires an
 * explicit Approve (or Reject with reason) before anything is sent.
 */
export const EmailApprovalGate: React.FC<Props> = ({ email, onApprove, onReject, busy }) => {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');

  return (
    <Card className="overflow-hidden">
      <div className="bg-yellow-50 border-b border-yellow-200 px-5 py-3 text-sm text-yellow-800">
        Review this email carefully. Nothing is sent until you approve.
      </div>
      <div className="px-5 py-4 space-y-2 text-sm border-b border-gray-100">
        <div className="flex gap-2">
          <span className="text-gray-500 w-16">To</span>
          <span className="text-gray-900">{email.to_emails.join(', ') || '—'}</span>
        </div>
        {email.cc_emails && email.cc_emails.length > 0 && (
          <div className="flex gap-2">
            <span className="text-gray-500 w-16">Cc</span>
            <span className="text-gray-900">{email.cc_emails.join(', ')}</span>
          </div>
        )}
        <div className="flex gap-2">
          <span className="text-gray-500 w-16">Subject</span>
          <span className="font-medium text-gray-900">{email.subject}</span>
        </div>
      </div>

      <div
        className="px-5 py-4 prose prose-sm max-w-none text-gray-800"
        dangerouslySetInnerHTML={{ __html: email.body_html }}
      />

      <div className="px-5 py-4 border-t border-gray-100">
        {!rejecting ? (
          <div className="flex justify-end gap-3">
            <Button variant="danger" onClick={() => setRejecting(true)} disabled={busy}>
              Reject
            </Button>
            <Button onClick={onApprove} disabled={busy}>
              {busy ? 'Sending…' : 'Approve & Send'}
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason for rejection (optional)…"
              rows={2}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setRejecting(false)}>
                Back
              </Button>
              <Button variant="danger" onClick={() => onReject(reason)} disabled={busy}>
                Confirm Reject
              </Button>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
