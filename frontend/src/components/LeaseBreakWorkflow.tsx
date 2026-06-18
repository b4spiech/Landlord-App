import { useMemo, useState } from 'react';
import type { Lease } from '../types';
import { ProgressBar } from './ProgressBar';
import { Button, Card } from './ui';
import { Field, NumberInput, Select, Textarea, TextInput } from './FormFields';
import { EmailApprovalGate } from './EmailApprovalGate';
import type { DraftEmail } from './EmailApprovalGate';
import { useToast } from './Toast';
import { formatCurrency } from '../lib/format';

const STEPS = ['Initiate', 'Present Options', 'Await Selection', 'Email Approval', 'Signatures'];

// Arizona early-termination cap (mirrors seed ARIZONA_RULES.max_buyout_months).
const AZ_MAX_BUYOUT_MONTHS = 3;

interface WorkflowOption {
  id: string;
  option_type: string;
  label: string;
  description: string;
  total_cost_to_tenant: number;
  months_charged?: number;
  is_compliant: boolean;
  compliance_note?: string;
}

function monthsRemaining(endDate: string): number {
  const end = new Date(endDate);
  const now = new Date();
  const months = (end.getFullYear() - now.getFullYear()) * 12 + (end.getMonth() - now.getMonth());
  return Math.max(0, months);
}

export const LeaseBreakWorkflow: React.FC<{ leases: Lease[] }> = ({ leases }) => {
  const toast = useToast();
  const [step, setStep] = useState(0);

  const [leaseId, setLeaseId] = useState('');
  const [moveOutDate, setMoveOutDate] = useState('');
  const [reason, setReason] = useState('');

  const [buyoutMonths, setBuyoutMonths] = useState<number | ''>(2);
  const [options, setOptions] = useState<WorkflowOption[]>([]);
  const [selectedId, setSelectedId] = useState('');

  const lease = useMemo(() => leases.find((l) => l.id === leaseId), [leaseId, leases]);
  const leaseOptions = leases.map((l) => ({
    value: l.id,
    label: `${formatCurrency(l.monthly_rent)}/mo · ${l.start_date} → ${l.end_date}`,
  }));

  const handleInitiate = () => {
    if (!leaseId) return toast.error('Select a lease');
    if (!moveOutDate) return toast.error('Enter a desired move-out date');
    setStep(1);
  };

  const handlePresentOptions = () => {
    if (!lease) return;
    const rent = lease.monthly_rent;
    const months = buyoutMonths === '' ? 0 : buyoutMonths;
    const buyoutTotal = rent * months;
    const compliant = months <= AZ_MAX_BUYOUT_MONTHS;
    const remaining = monthsRemaining(lease.end_date);

    setOptions([
      {
        id: 'buyout',
        option_type: 'buyout',
        label: `Buyout — ${months} months' rent`,
        description: `One-time payment to terminate early (${formatCurrency(rent)} × ${months}).`,
        total_cost_to_tenant: buyoutTotal,
        months_charged: months,
        is_compliant: compliant,
        compliance_note: compliant
          ? `Within Arizona cap of ${AZ_MAX_BUYOUT_MONTHS}× monthly rent.`
          : `Exceeds Arizona cap of ${AZ_MAX_BUYOUT_MONTHS}× monthly rent (${formatCurrency(rent * AZ_MAX_BUYOUT_MONTHS)}).`,
      },
      {
        id: 'forfeit',
        option_type: 'forfeit_deposit',
        label: 'Forfeit security deposit + re-let',
        description: `Tenant forfeits the ${formatCurrency(lease.security_deposit)} deposit; landlord re-rents (duty to mitigate).`,
        total_cost_to_tenant: lease.security_deposit,
        is_compliant: true,
        compliance_note: 'Landlord must make reasonable efforts to re-rent (A.R.S. 33-1370).',
      },
      {
        id: 'mutual',
        option_type: 'mutual_termination',
        label: 'Mutual termination',
        description: `Both parties agree to end the lease; ${remaining} month(s) remained.`,
        total_cost_to_tenant: 0,
        is_compliant: true,
      },
    ]);
    setStep(2);
  };

  const selectedOption = options.find((o) => o.id === selectedId);

  const draftEmail: DraftEmail | null = useMemo(() => {
    if (!selectedOption || !lease) return null;
    return {
      subject: `Lease termination — ${selectedOption.label}`,
      to_emails: ['tenant@example.com'],
      body_html: `
        <p>Dear Tenant,</p>
        <p>Following your request to end your lease early (desired move-out
        <strong>${moveOutDate}</strong>), we are proceeding with:
        <strong>${selectedOption.label}</strong>.</p>
        <p>Total amount due: <strong>${formatCurrency(selectedOption.total_cost_to_tenant)}</strong>.</p>
        <p>${selectedOption.description}</p>
        <p>We will send the termination documents for electronic signature shortly.</p>
        <p>Sincerely,<br/>APEX Element Group LLC</p>`,
    };
  }, [selectedOption, lease, moveOutDate]);

  return (
    <div>
      <ProgressBar steps={STEPS} currentStep={step} />

      {/* Step 0 — Initiate */}
      {step === 0 && (
        <Card className="p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Initiate Lease Break</h2>
          <Field label="Lease" required>
            <Select value={leaseId} onChange={setLeaseId} options={leaseOptions} placeholder="Select a lease…" />
          </Field>
          <Field label="Desired move-out date" required>
            <TextInput type="date" value={moveOutDate} onChange={setMoveOutDate} />
          </Field>
          <Field label="Reason">
            <Textarea value={reason} onChange={setReason} />
          </Field>
          <div className="flex justify-end">
            <Button onClick={handleInitiate}>Continue</Button>
          </div>
        </Card>
      )}

      {/* Step 1 — Present Options */}
      {step === 1 && lease && (
        <Card className="p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Configure Options</h2>
          <p className="text-sm text-gray-500">
            Monthly rent {formatCurrency(lease.monthly_rent)} · {monthsRemaining(lease.end_date)} month(s) remaining.
          </p>
          <Field label="Buyout (months of rent)">
            <NumberInput value={buyoutMonths} onChange={setBuyoutMonths} min={0} step={0.5} />
          </Field>
          {buyoutMonths !== '' && buyoutMonths > AZ_MAX_BUYOUT_MONTHS && (
            <p className="text-sm text-red-600">
              ⚠ Exceeds Arizona cap of {AZ_MAX_BUYOUT_MONTHS}× monthly rent.
            </p>
          )}
          <div className="flex justify-between">
            <Button variant="secondary" onClick={() => setStep(0)}>
              Back
            </Button>
            <Button onClick={handlePresentOptions}>Generate Options</Button>
          </div>
        </Card>
      )}

      {/* Step 2 — Await Selection */}
      {step === 2 && (
        <div className="space-y-4">
          <h2 className="font-semibold text-gray-900">Select an Option</h2>
          <div className="grid gap-3">
            {options.map((o) => (
              <button
                key={o.id}
                onClick={() => setSelectedId(o.id)}
                className={`text-left rounded-lg border p-4 transition-colors ${
                  selectedId === o.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{o.label}</span>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(o.total_cost_to_tenant)}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-1">{o.description}</p>
                {o.compliance_note && (
                  <p className={`text-xs mt-2 ${o.is_compliant ? 'text-green-700' : 'text-red-600'}`}>
                    {o.is_compliant ? '✓' : '⚠'} {o.compliance_note}
                  </p>
                )}
              </button>
            ))}
          </div>
          <div className="flex justify-between">
            <Button variant="secondary" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button
              onClick={() => {
                if (!selectedOption) return toast.error('Select an option');
                if (!selectedOption.is_compliant)
                  return toast.error('Selected option is not compliant with state law');
                setStep(3);
              }}
            >
              Continue
            </Button>
          </div>
        </div>
      )}

      {/* Step 3 — Email Approval */}
      {step === 3 && draftEmail && (
        <div className="space-y-4">
          <h2 className="font-semibold text-gray-900">Approve Notification Email</h2>
          <EmailApprovalGate
            email={draftEmail}
            onApprove={() => {
              toast.success('Email approved (will send once backend email service is live)');
              setStep(4);
            }}
            onReject={() => {
              toast.notify('Email rejected — returned to options');
              setStep(2);
            }}
          />
          <Button variant="secondary" onClick={() => setStep(2)}>
            Back
          </Button>
        </div>
      )}

      {/* Step 4 — Signatures */}
      {step === 4 && (
        <Card className="p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Route for Signature</h2>
          <p className="text-sm text-gray-500">
            Generate the termination documents and send them via DocuSign for e-signature.
          </p>
          <div className="rounded border border-gray-200 divide-y divide-gray-100 text-sm">
            <div className="flex items-center justify-between px-4 py-3">
              <span>Landlord — APEX Element Group LLC</span>
              <span className="text-gray-400">Awaiting backend</span>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <span>Tenant</span>
              <span className="text-gray-400">Awaiting backend</span>
            </div>
          </div>
          <Button
            onClick={() =>
              toast.notify('DocuSign routing requires backend Milestones 5-6 (not yet deployed)')
            }
          >
            Send for Signature
          </Button>
        </Card>
      )}
    </div>
  );
};
