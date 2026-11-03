import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { publicApi } from '../publicApi';
import { useLoad } from '../useLoad';
import { COMPANY } from '../company';

type Interest = 'yes' | 'maybe' | 'no';

const INTEREST: { value: Interest; label: string }[] = [
  { value: 'yes', label: "Yes, I'd like to apply" },
  { value: 'maybe', label: 'Maybe' },
  { value: 'no', label: 'No, not for me' },
];

/** Private post-tour feedback form (link sent about an hour after the tour). */
export const FeedbackPage = () => {
  const { token = '' } = useParams<{ token: string }>();
  const {
    data: info,
    error: loadError,
    loading,
  } = useLoad(() => publicApi.feedbackInfo(token), token);
  const [rating, setRating] = useState(0);
  const [interested, setInterested] = useState<Interest | ''>('');
  const [liked, setLiked] = useState('');
  const [concerns, setConcerns] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>;
  if (loadError || !info)
    return (
      <div className="py-16 text-center">
        <h1 className="text-2xl font-semibold">This feedback link isn't valid</h1>
        <p className="mt-2 text-gray-600">
          Questions? Email{' '}
          <a href={`mailto:${COMPANY.email}`} className="text-blue-700 underline">
            {COMPANY.email}
          </a>
          .
        </p>
      </div>
    );

  if (done || info.submitted)
    return (
      <div className="py-12">
        <h1 className="text-3xl font-bold text-gray-900">Thank you!</h1>
        <p className="mt-3 text-gray-700">
          {done ? 'Your feedback was sent.' : 'We already have your feedback.'} We appreciate you
          taking the time.
        </p>
        <p className="mt-3 text-gray-700">
          Interested in applying? Email{' '}
          <a href={`mailto:${COMPANY.email}`} className="text-blue-700 underline">
            {COMPANY.email}
          </a>
          .
        </p>
        <Link to="/" className="mt-8 inline-block font-medium text-blue-700 hover:underline">
          &larr; See available homes
        </Link>
      </div>
    );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!rating) return setError('Please choose a rating.');
    if (!interested) return setError('Please tell us if you are interested in applying.');
    setSending(true);
    try {
      await publicApi.submitFeedback(token, { rating, interested, liked, concerns });
      setDone(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">How was your tour?</h1>
      <p className="mt-2 text-gray-600">
        Hi {info.first_name} — thanks for touring <strong>{info.home}</strong> on {info.when}. This
        takes under a minute.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-6">
        <fieldset>
          <legend className="text-sm font-medium text-gray-700 mb-2">
            Overall, how did you like the home?
          </legend>
          <div className="flex gap-2" role="radiogroup">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={rating === n}
                aria-label={`${n} star${n > 1 ? 's' : ''}`}
                onClick={() => setRating(n)}
                className={`h-11 w-11 rounded-full border text-lg font-semibold ${
                  n <= rating
                    ? 'border-amber-400 bg-amber-100 text-amber-700'
                    : 'border-gray-300 text-gray-400'
                }`}
              >
                ★
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-sm font-medium text-gray-700 mb-2">
            Are you interested in applying?
          </legend>
          <div className="flex flex-wrap gap-2">
            {INTEREST.map((o) => (
              <label
                key={o.value}
                className={`cursor-pointer rounded border px-4 py-2 text-sm ${
                  interested === o.value
                    ? 'border-blue-700 bg-blue-50 text-blue-800'
                    : 'border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="interested"
                  value={o.value}
                  checked={interested === o.value}
                  onChange={() => setInterested(o.value)}
                  className="sr-only"
                />
                {o.label}
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <label htmlFor="liked" className="block text-sm font-medium text-gray-700 mb-1">
            What did you like? (optional)
          </label>
          <textarea
            id="liked"
            value={liked}
            onChange={(e) => setLiked(e.target.value)}
            rows={3}
            maxLength={2000}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor="concerns" className="block text-sm font-medium text-gray-700 mb-1">
            Any concerns or questions? (optional)
          </label>
          <textarea
            id="concerns"
            value={concerns}
            onChange={(e) => setConcerns(e.target.value)}
            rows={3}
            maxLength={2000}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        {error && (
          <div
            role="alert"
            className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
          >
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={sending}
          className="rounded bg-blue-700 px-5 py-2.5 text-white font-medium hover:bg-blue-800 disabled:opacity-60"
        >
          {sending ? 'Sending…' : 'Send feedback'}
        </button>
      </form>
    </div>
  );
};
