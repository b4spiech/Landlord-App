import { useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { publicApi } from '../publicApi';
import { useLoad } from '../useLoad';
import { money } from '../listingFormat';
import { COMPANY, SMS_CONSENT_TEXT } from '../company';

// The form and SMS opt-in wording are final (Twilio's toll-free verification
// reviews this page). Submitting is wired to the tour-request API in a later
// phase; until then it explains that online booking opens soon.

// 30-minute tours starting 8:00 am through 7:30 pm (home's local time).
const START_TIMES = Array.from({ length: 24 }, (_, i) => {
  const minutes = 8 * 60 + i * 30;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const label = `${((h + 11) % 12) + 1}:${m === 0 ? '00' : '30'} ${h < 12 ? 'am' : 'pm'}`;
  return { value: `${String(h).padStart(2, '0')}:${m === 0 ? '00' : '30'}`, label };
});

const input =
  'w-full rounded border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-500';

const Label = ({ children, htmlFor }: { children: ReactNode; htmlFor: string }) => (
  <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 mb-1">
    {children}
  </label>
);

export const TourRequestPage = () => {
  const [submitted, setSubmitted] = useState(false);
  const [params] = useSearchParams();
  const { data: listings } = useLoad(publicApi.listings, 'listings');
  const preselected = params.get('home') ?? '';
  const [home, setHome] = useState<string | null>(null);
  const selectedHome = home ?? (listings?.some((l) => l.id === preselected) ? preselected : '');

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">Request a tour</h1>
      <p className="mt-2 text-gray-600">
        Tours are self-guided, last up to 30 minutes, and can start any day between 8:00 am and 7:30
        pm in the home's local time.
      </p>

      <form
        className="mt-6 space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(true);
        }}
      >
        <div className="space-y-5">
          <div>
            <Label htmlFor="property">Home</Label>
            <select
              id="property"
              className={input}
              value={selectedHome}
              onChange={(e) => setHome(e.target.value)}
            >
              <option value="" disabled>
                Select a home
              </option>
              {listings?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.address_line1}
                  {l.address_line2 ? `, ${l.address_line2}` : ''}, {l.city} —{' '}
                  {money(l.monthly_rent)}/mo
                </option>
              ))}
              {listings && listings.length === 0 && (
                <option value="none" disabled>
                  No homes are open for tours right now
                </option>
              )}
            </select>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="first">First name</Label>
              <input id="first" className={input} autoComplete="given-name" />
            </div>
            <div>
              <Label htmlFor="last">Last name</Label>
              <input id="last" className={input} autoComplete="family-name" />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <input id="email" type="email" className={input} autoComplete="email" />
            </div>
            <div>
              <Label htmlFor="phone">Mobile phone</Label>
              <input id="phone" type="tel" className={input} autoComplete="tel" />
            </div>
            <div>
              <Label htmlFor="date">Tour date</Label>
              <input id="date" type="date" className={input} />
            </div>
            <div>
              <Label htmlFor="time">Start time (home's local time)</Label>
              <select id="time" className={input} defaultValue="">
                <option value="" disabled>
                  Select a time
                </option>
                {START_TIMES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <Label htmlFor="photo-id">Photo of your government-issued ID</Label>
            <input id="photo-id" type="file" accept="image/*" className="block text-sm" />
            <p className="mt-1 text-xs text-gray-500">
              Used only to verify your identity for this tour. Deleted automatically 30 days after
              your tour.
            </p>
          </div>

          <label className="flex items-start gap-3 text-sm text-gray-700">
            {/* Unchecked by default and optional, as carrier rules require. */}
            <input id="sms-consent" type="checkbox" className="mt-1" />
            <span>
              {SMS_CONSENT_TEXT} See our{' '}
              <Link to="/sms-terms" className="text-blue-700 hover:underline">
                SMS Terms
              </Link>{' '}
              and{' '}
              <Link to="/privacy" className="text-blue-700 hover:underline">
                Privacy Policy
              </Link>
              .
            </span>
          </label>

          <button
            type="submit"
            className="rounded bg-blue-700 px-5 py-2.5 text-white font-medium hover:bg-blue-800"
          >
            Submit tour request
          </button>

          {submitted && (
            <div
              role="status"
              className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            >
              Online tour booking opens soon. To schedule a tour now, email{' '}
              <a href={`mailto:${COMPANY.email}`} className="font-medium underline">
                {COMPANY.email}
              </a>
              .
            </div>
          )}
        </div>
      </form>
    </div>
  );
};
