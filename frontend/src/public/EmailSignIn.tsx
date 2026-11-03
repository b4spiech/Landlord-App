import { useState } from 'react';
import { publicApi } from './publicApi';

const input = 'w-full rounded border border-gray-300 px-3 py-2 text-sm';

/** Two steps: enter email -> enter the 6-digit code we emailed. Calls onSignedIn(email). */
export const EmailSignIn = ({ onSignedIn }: { onSignedIn: (email: string) => void }) => {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const send = async () => {
    setError('');
    setInfo('');
    setBusy(true);
    try {
      await publicApi.startSignIn(email);
      setStep('code');
      setCode('');
      setInfo(
        `We emailed a 6-digit code to ${email.trim()}. Check your spam folder if you don't see it.`,
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    setError('');
    setBusy(true);
    try {
      const res = await publicApi.verifySignIn(email, code);
      onSignedIn(res.email);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-6 rounded-lg border p-5">
      <h2 className="font-semibold text-gray-900">First, verify your email</h2>
      <p className="mt-1 text-sm text-gray-600">
        We'll send your tour updates to this address. You'll only need to do this once on this
        device.
      </p>

      {step === 'email' ? (
        <form
          className="mt-4 flex flex-col gap-3 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <label htmlFor="signin-email" className="sr-only">
            Email
          </label>
          <input
            id="signin-email"
            type="email"
            autoComplete="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={input}
          />
          <button
            type="submit"
            disabled={busy}
            className="shrink-0 rounded bg-blue-700 px-5 py-2 text-white font-medium hover:bg-blue-800 disabled:opacity-60"
          >
            {busy ? 'Sending…' : 'Send code'}
          </button>
        </form>
      ) : (
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            verify();
          }}
        >
          {info && <p className="text-sm text-gray-700">{info}</p>}
          <div className="flex flex-col gap-3 sm:flex-row">
            <label htmlFor="signin-code" className="sr-only">
              6-digit code
            </label>
            <input
              id="signin-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              placeholder="123456"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              className={`${input} font-mono tracking-widest sm:max-w-[10rem]`}
              autoFocus
            />
            <button
              type="submit"
              disabled={busy || code.length !== 6}
              className="shrink-0 rounded bg-blue-700 px-5 py-2 text-white font-medium hover:bg-blue-800 disabled:opacity-60"
            >
              {busy ? 'Checking…' : 'Verify'}
            </button>
          </div>
          <p className="text-xs text-gray-500">
            <button type="button" onClick={send} disabled={busy} className="underline">
              Send a new code
            </button>{' '}
            ·{' '}
            <button
              type="button"
              onClick={() => {
                setStep('email');
                setError('');
                setInfo('');
              }}
              className="underline"
            >
              Use a different email
            </button>
          </p>
        </form>
      )}

      {error && (
        <div
          role="alert"
          className="mt-3 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {error}
        </div>
      )}
    </div>
  );
};
