import { useEffect, useMemo, useState } from 'react';
import { getErrorMessage, leaseBreakAPI } from '../services/api';
import type { Lease, LeaseBreakDocumentMeta, LeaseBreakOption } from '../types';
import { ProgressBar } from './ProgressBar';
import { Button, Card } from './ui';
import { Field, NumberInput, Textarea, TextInput, Select } from './FormFields';
import { useToast } from './Toast';
import { formatCurrency } from '../lib/format';

const STEPS = ['Initiate', 'Options', 'Documents', 'Approvals'];

interface EmailPreview {
  subject: string;
  body_html: string;
  to_emails: string[];
  configured: boolean;
}

export const LeaseBreakWorkflow: React.FC<{ leases: Lease[]; initialLeaseId?: string }> = ({
  leases,
  initialLeaseId = '',
}) => {
  const toast = useToast();
  const [step, setStep] = useState(0);

  const [leaseId, setLeaseId] = useState(initialLeaseId);
  const [moveOutDate, setMoveOutDate] = useState('');
  const [reason, setReason] = useState('');
  const [lastMonthHeld, setLastMonthHeld] = useState<number | ''>('');
  const [buyoutMultiple, setBuyoutMultiple] = useState<number | ''>(3);

  const [requestId, setRequestId] = useState('');
  const [options, setOptions] = useState<LeaseBreakOption[]>([]);
  const [selected, setSelected] = useState<LeaseBreakOption | null>(null);
  const [doc, setDoc] = useState<LeaseBreakDocumentMeta | null>(null);
  const [envelopeId, setEnvelopeId] = useState('');
  const [emailPreview, setEmailPreview] = useState<EmailPreview | null>(null);
  const [emailSentTo, setEmailSentTo] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);

  const lease = useMemo(() => leases.find((l) => l.id === leaseId), [leaseId, leases]);
  const leaseOptions = leases.map((l) => ({
    value: l.id,
    label: `${formatCurrency(l.monthly_rent)}/mo · ${l.start_date} → ${l.end_date}`,
  }));
  const isBuyout = selected?.option_type === 'buyout';

  // Load the email preview when entering Approvals (read-only — sends nothing).
  useEffect(() => {
    if (step === 3 && selected && !emailPreview) {
      leaseBreakAPI
        .emailPreview(requestId, selected.id)
        .then(setEmailPreview)
        .catch((e) => toast.error(getErrorMessage(e)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, selected]);

  const initiate = async () => {
    if (!leaseId) return toast.error('Select a lease');
    if (!moveOutDate) return toast.error('Enter a desired move-out date');
    setBusy(true);
    try {
      const req = await leaseBreakAPI.initiate({
        lease_id: leaseId,
        desired_move_out_date: moveOutDate,
        reason: reason || undefined,
      });
      const opts = await leaseBreakAPI.calculateOptions(req.id, {
        move_out_date: moveOutDate,
        last_months_rent_held: lastMonthHeld === '' ? undefined : lastMonthHeld,
        buyout_multiple: buyoutMultiple === '' ? undefined : buyoutMultiple,
      });
      setRequestId(req.id);
      setOptions(opts);
      setStep(1);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const choose = async (o: LeaseBreakOption) => {
    setBusy(true);
    try {
      await leaseBreakAPI.selectOption(requestId, { option_id: o.id });
      setSelected(o);
      setDoc(null);
      setEnvelopeId('');
      setEmailPreview(null);
      setEmailSentTo(null);
      setStep(2);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const d = await leaseBreakAPI.generateAgreement(requestId, { option_id: selected.id });
      setDoc(d);
      toast.success('Agreement generated — preview below');
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const sendEmail = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const res = await leaseBreakAPI.sendEmail(requestId, {
        option_id: selected.id,
        attach_document_id: doc?.id,
      });
      setEmailSentTo(res.to_emails);
      toast.success(`Email sent to ${res.to_emails.join(', ')}`);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const routeForSignature = async () => {
    if (!doc) return toast.error('Generate the agreement first');
    setBusy(true);
    try {
      const res = await leaseBreakAPI.routeForSignature(requestId, { document_id: doc.id });
      setEnvelopeId(res.envelope_id);
      toast.success('Routed for signature via DocuSign');
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const nav = (back?: number, skipTo?: number) => (
    <div className="flex justify-between pt-2">
      {back !== undefined ? (
        <Button variant="secondary" onClick={() => setStep(back)}>
          Back
        </Button>
      ) : (
        <span />
      )}
      {skipTo !== undefined && (
        <Button variant="secondary" onClick={() => setStep(skipTo)}>
          Skip →
        </Button>
      )}
    </div>
  );

  return (
    <div>
      <ProgressBar steps={STEPS} currentStep={step} />

      {/* Step 0 — Initiate */}
      {step === 0 && (
        <Card className="p-5 space-y-4 max-w-2xl">
          <h2 className="font-semibold text-gray-900">Initiate Lease Break</h2>
          <Field label="Lease" required>
            <Select value={leaseId} onChange={setLeaseId} options={leaseOptions} placeholder="Select a lease…" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Desired move-out date" required>
              <TextInput type="date" value={moveOutDate} onChange={setMoveOutDate} />
            </Field>
            <Field label="Buyout multiple (joint)">
              <NumberInput value={buyoutMultiple} onChange={setBuyoutMultiple} min={0} step={0.5} />
            </Field>
          </div>
          <Field label="Last month's rent held (credit)">
            <NumberInput
              value={lastMonthHeld}
              onChange={setLastMonthHeld}
              min={0}
              placeholder={lease ? `Defaults to rent: ${formatCurrency(lease.monthly_rent)}` : 'Defaults to monthly rent'}
            />
          </Field>
          <Field label="Reason">
            <Textarea value={reason} onChange={setReason} />
          </Field>
          <div className="flex justify-end">
            <Button onClick={initiate} disabled={busy}>
              {busy ? 'Calculating…' : 'Calculate Options'}
            </Button>
          </div>
        </Card>
      )}

      {/* Step 1 — Options */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="font-semibold text-gray-900">Lease Break Options</h2>
          <div className="grid gap-4">
            {options.map((o) => (
              <Card key={o.id} className={`p-5 ${selected?.id === o.id ? 'ring-2 ring-blue-500' : ''}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-gray-900">{o.label}</p>
                    {o.description && <p className="text-sm text-gray-500 mt-1">{o.description}</p>}
                  </div>
                  <Button onClick={() => choose(o)} disabled={busy}>
                    {selected?.id === o.id ? 'Selected' : 'Select'}
                  </Button>
                </div>
                {o.option_type === 'buyout' ? (
                  <div className="mt-4 grid sm:grid-cols-3 gap-y-2 gap-x-6 text-sm bg-blue-50 rounded p-4">
                    <Stat label="Monthly rent" value={formatCurrency(o.monthly_rent_amount)} />
                    <Stat label="Buyout multiple" value={`${o.buyout_multiple ?? '—'}×`} />
                    <Stat label="Buyout (gross)" value={formatCurrency(o.buyout_amount_gross)} />
                    <Stat label="Last month credit" value={`-${formatCurrency(o.last_month_credit)}`} accent="green" />
                    <Stat label="Cash due at signing" value={formatCurrency(o.cash_due_at_signing)} accent="bold" />
                    <Stat label="Security deposit" value={formatCurrency(o.security_deposit_held)} />
                  </div>
                ) : (
                  <div className="mt-4 text-sm bg-yellow-50 rounded p-4 text-yellow-800">{o.terms}</div>
                )}
              </Card>
            ))}
          </div>
          {nav(0, selected ? 2 : undefined)}
        </div>
      )}

      {/* Step 2 — Documents (preview before anything is sent) */}
      {step === 2 && (
        <div className="space-y-4 max-w-3xl">
          <h2 className="font-semibold text-gray-900">Documents</h2>
          {!selected ? (
            <Card className="p-5 text-sm text-gray-500">Select an option first to generate documents.</Card>
          ) : !isBuyout ? (
            <Card className="p-5 text-sm text-gray-600">
              No buyout agreement is generated for “{selected.label}”. You can continue.
            </Card>
          ) : (
            <Card className="p-5">
              <p className="text-sm text-gray-600 mb-3">
                Generate the buyout agreement and review it here before anything is emailed or routed
                for signature. Generating does not send anything.
              </p>
              <Button onClick={generate} disabled={busy}>
                {busy ? 'Generating…' : doc ? 'Regenerate agreement' : 'Generate agreement (PDF)'}
              </Button>
              {doc && (
                <div className="mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">{doc.file_name}</span>
                    <a
                      href={leaseBreakAPI.documentDownloadUrl(requestId, doc.id)}
                      className="text-sm text-blue-600 hover:underline"
                    >
                      Download
                    </a>
                  </div>
                  <iframe
                    title="Agreement preview"
                    src={`${leaseBreakAPI.documentDownloadUrl(requestId, doc.id)}?inline=true`}
                    className="w-full h-[32rem] border border-gray-200 rounded"
                  />
                </div>
              )}
            </Card>
          )}
          {nav(1, 3)}
        </div>
      )}

      {/* Step 3 — Approvals (explicit send / route only) */}
      {step === 3 && (
        <div className="space-y-5 max-w-3xl">
          <h2 className="font-semibold text-gray-900">Approvals</h2>
          <div className="bg-gray-50 border border-gray-200 rounded px-4 py-3 text-sm text-gray-600">
            Nothing is sent or routed until you click an <strong>Approve</strong> button below. You can
            skip either action.
          </div>

          {/* Email */}
          <Card className="overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Notification email</h3>
              {emailSentTo && <span className="text-sm text-green-700">Sent ✓</span>}
            </div>
            {!selected ? (
              <p className="px-5 py-6 text-sm text-gray-500">Select an option to preview the email.</p>
            ) : !emailPreview ? (
              <p className="px-5 py-6 text-sm text-gray-500">Loading preview…</p>
            ) : (
              <>
                <div className="px-5 py-3 text-sm border-b border-gray-100">
                  <div><span className="text-gray-500">To:</span> {emailPreview.to_emails.join(', ') || '— (no tenant emails on file)'}</div>
                  <div><span className="text-gray-500">Subject:</span> {emailPreview.subject}</div>
                </div>
                <div
                  className="px-5 py-4 text-sm text-gray-800"
                  dangerouslySetInnerHTML={{ __html: emailPreview.body_html }}
                />
                <div className="px-5 py-4 border-t border-gray-100 flex items-center gap-3">
                  <Button onClick={sendEmail} disabled={busy || !!emailSentTo}>
                    {emailSentTo ? 'Email sent' : busy ? 'Sending…' : 'Approve & Send Email'}
                  </Button>
                  {!emailPreview.configured && (
                    <span className="text-xs text-gray-500">Email isn't configured on the server yet.</span>
                  )}
                </div>
              </>
            )}
          </Card>

          {/* DocuSign */}
          <Card className="p-5">
            <h3 className="font-semibold text-gray-900 mb-2">E-signature (DocuSign)</h3>
            {!doc ? (
              <p className="text-sm text-gray-500">
                Generate the agreement on the Documents step to enable signature routing.
              </p>
            ) : (
              <div className="flex items-center gap-3">
                <Button onClick={routeForSignature} disabled={busy || !!envelopeId}>
                  {envelopeId ? 'Routed' : busy ? 'Routing…' : 'Approve & Route for Signature'}
                </Button>
                {envelopeId && (
                  <span className="text-sm text-green-700">Sent · envelope {envelopeId.slice(0, 8)}…</span>
                )}
              </div>
            )}
            <p className="text-xs text-gray-500 mt-2">
              Routes the agreement to the landlord and each tenant. Requires DocuSign configured and an
              email on each signer.
            </p>
          </Card>

          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(2)}>
              Back
            </Button>
            <span className="text-sm text-gray-500 self-center">
              Done — close this when finished. No further action is taken automatically.
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

const Stat = ({ label, value, accent }: { label: string; value: string; accent?: 'green' | 'bold' }) => (
  <div>
    <p className="text-gray-500">{label}</p>
    <p
      className={
        accent === 'green'
          ? 'font-semibold text-green-600'
          : accent === 'bold'
            ? 'font-bold text-gray-900 text-base'
            : 'font-semibold text-gray-900'
      }
    >
      {value}
    </p>
  </div>
);
