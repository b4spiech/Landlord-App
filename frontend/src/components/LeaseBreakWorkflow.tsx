import { useMemo, useState } from 'react';
import { getErrorMessage, leaseBreakAPI } from '../services/api';
import type { Lease, LeaseBreakDocumentMeta, LeaseBreakOption } from '../types';
import { ProgressBar } from './ProgressBar';
import { Button, Card } from './ui';
import { Field, NumberInput, Textarea, TextInput, Select } from './FormFields';
import { useToast } from './Toast';
import { formatCurrency } from '../lib/format';

const STEPS = ['Initiate', 'Options', 'Agreement'];

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
  const [busy, setBusy] = useState(false);

  const lease = useMemo(() => leases.find((l) => l.id === leaseId), [leaseId, leases]);
  const leaseOptions = leases.map((l) => ({
    value: l.id,
    label: `${formatCurrency(l.monthly_rent)}/mo · ${l.start_date} → ${l.end_date}`,
  }));

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
      setStep(2);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const sendForSignature = async () => {
    if (!doc) return;
    setBusy(true);
    try {
      const res = await leaseBreakAPI.routeForSignature(requestId, { document_id: doc.id });
      setEnvelopeId(res.envelope_id);
      toast.success('Sent for signature via DocuSign');
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
      setEnvelopeId('');
      toast.success('Buyout agreement generated');
      window.open(leaseBreakAPI.documentDownloadUrl(requestId, d.id), '_blank');
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

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
              <Card key={o.id} className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-gray-900">{o.label}</p>
                    {o.description && <p className="text-sm text-gray-500 mt-1">{o.description}</p>}
                  </div>
                  <Button onClick={() => choose(o)} disabled={busy}>
                    Select
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
                    <div className="sm:col-span-3 text-xs text-gray-600 bg-white rounded p-3 mt-1">
                      {o.move_out_date && (
                        <>
                          {o.final_rent_due_date}: tenant pays {formatCurrency(o.current_month_rent)} (standard rent) ·
                          at signing: {formatCurrency(o.cash_due_at_signing)} · landlord receives{' '}
                          {formatCurrency(o.total_cash_collected)} total. Security deposit is separate and refunded
                          after move-out inspection.
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 text-sm bg-yellow-50 rounded p-4 text-yellow-800">
                    {o.terms}
                  </div>
                )}
              </Card>
            ))}
          </div>
          <Button variant="secondary" onClick={() => setStep(0)}>
            Back
          </Button>
        </div>
      )}

      {/* Step 2 — Agreement */}
      {step === 2 && selected && (
        <div className="space-y-4 max-w-2xl">
          <h2 className="font-semibold text-gray-900">Agreement</h2>
          <Card className="p-5">
            <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
              <strong>Selected:</strong> {selected.label}
            </div>

            {selected.option_type === 'buyout' && (
              <div className="mt-4 text-sm space-y-1">
                <Row label="Buyout (gross)" value={formatCurrency(selected.buyout_amount_gross)} />
                <Row label="Less last month's credit" value={`-${formatCurrency(selected.last_month_credit)}`} />
                <Row label="Cash due at signing" value={formatCurrency(selected.cash_due_at_signing)} bold />
                <Row label="Landlord receives (total)" value={formatCurrency(selected.total_cash_collected)} />
              </div>
            )}

            <div className="mt-5 bg-gray-50 border rounded p-4 text-sm text-gray-700">
              <p className="font-medium mb-2">Email preview</p>
              <p>Hi {lease ? '' : ''}there,</p>
              <p className="mt-2">
                Thank you for requesting early lease termination. We've agreed to:{' '}
                <strong>{selected.label}</strong>.
              </p>
              {selected.option_type === 'buyout' && (
                <p className="mt-2">
                  Buyout {formatCurrency(selected.buyout_amount_gross)} less last month's rent credit{' '}
                  {formatCurrency(selected.last_month_credit)} ={' '}
                  <strong>{formatCurrency(selected.cash_due_at_signing)} due at signing</strong>. Move-out:{' '}
                  {selected.move_out_date}. Security deposit refunded after inspection.
                </p>
              )}
              <p className="mt-2">Please review and sign the attached agreement.</p>
            </div>

            <div className="mt-5 flex justify-between gap-3">
              <Button variant="secondary" onClick={() => setStep(1)}>
                Back
              </Button>
              {selected.option_type === 'buyout' ? (
                <Button onClick={generate} disabled={busy}>
                  {busy ? 'Generating…' : doc ? 'Re-download Agreement (PDF)' : 'Generate & Download Agreement (PDF)'}
                </Button>
              ) : (
                <span className="text-sm text-gray-500 self-center">
                  No buyout agreement for this option.
                </span>
              )}
            </div>
            {doc && (
              <div className="mt-4 border-t pt-4">
                <p className="text-sm">
                  Generated:{' '}
                  <a
                    href={leaseBreakAPI.documentDownloadUrl(requestId, doc.id)}
                    className="text-blue-600 hover:underline"
                  >
                    {doc.file_name}
                  </a>
                </p>
                <div className="mt-3 flex items-center gap-3">
                  <Button onClick={sendForSignature} disabled={busy}>
                    {busy ? 'Sending…' : 'Send for Signature (DocuSign)'}
                  </Button>
                  {envelopeId && (
                    <span className="text-sm text-green-700">
                      Sent · envelope {envelopeId.slice(0, 8)}…
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Routes the agreement to the landlord and each tenant for e-signature. Requires
                  DocuSign credentials configured on the server and an email on each signer.
                </p>
              </div>
            )}
          </Card>
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

const Row = ({ label, value, bold }: { label: string; value: string; bold?: boolean }) => (
  <div className={`flex justify-between ${bold ? 'border-t pt-1 font-bold text-gray-900' : 'text-gray-600'}`}>
    <span>{label}</span>
    <span>{value}</span>
  </div>
);
