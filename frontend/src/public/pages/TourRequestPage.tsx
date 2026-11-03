import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { publicApi } from '../publicApi';
import { useLoad } from '../useLoad';
import { money } from '../listingFormat';
import { COMPANY, SMS_CONSENT_TEXT } from '../company';
import { EmailSignIn } from '../EmailSignIn';

// Tours: 30 minutes, start 8:00 am–7:30 pm in the home's local time, at least
// 2 hours ahead and up to 60 days out. The server enforces all of this; the
// form just guides people to valid choices.

const TZ_NAMES: Record<string, string> = {
  'America/Phoenix': 'Arizona time',
  'America/Detroit': 'Eastern time',
  'America/New_York': 'Eastern time',
  'America/Chicago': 'Central time',
  'America/Denver': 'Mountain time',
  'America/Los_Angeles': 'Pacific time',
};

const timeLabel = (hhmm: string) => {
  const [h, m] = hhmm.split(':').map(Number);
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`;
};

const isoDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const input =
  'w-full rounded border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-500';

const Label = ({ children, htmlFor }: { children: ReactNode; htmlFor: string }) => (
  <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 mb-1">
    {children}
  </label>
);

export const TourRequestPage = () => {
  const [params] = useSearchParams();
  const { data: listings } = useLoad(publicApi.listings, 'listings');
  const preselected = params.get('home') ?? '';
  const [home, setHome] = useState<string | null>(null);
  const selectedHome =
    home ??
    (listings?.some((l) => l.id === preselected)
      ? preselected
      : listings?.length === 1
        ? listings[0].id
        : '');
  const listing = listings?.find((l) => l.id === selectedHome);

  const [day, setDay] = useState('');
  const [time, setTime] = useState('');
  const slotKey = selectedHome && day ? `${selectedHome}|${day}` : '';
  const { data: availability, loading: slotsLoading } = useLoad(
    () => (slotKey ? publicApi.availability(selectedHome, day) : Promise.resolve(null)),
    slotKey || 'none',
  );
  const openSlots = availability?.slots.filter((s) => s.available) ?? [];
  const tzName = listing ? (TZ_NAMES[listing.time_zone] ?? 'local time') : "the home's local time";

  // Visitors must verify their email before requesting a tour; that address
  // is where every tour message goes.
  const { data: me, loading: meLoading } = useLoad(publicApi.me, 'me');
  const [signedInAs, setSignedInAs] = useState<string | null | undefined>(undefined);
  const visitorEmail = signedInAs === undefined ? me?.email : signedInAs;

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState<string | null>(null);

  const today = new Date();
  const maxDay = new Date(today.getTime() + 60 * 24 * 3600 * 1000);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    if (!selectedHome) return setError('Please choose a home.');
    if (!day || !time) return setError('Please choose a date and an available start time.');
    const form = new FormData(e.currentTarget);
    form.set('listing_id', selectedHome);
    form.set('tour_date', day);
    form.set('tour_time', time);
    form.set('sms_consent', form.get('sms_consent') ? 'true' : 'false');
    setSubmitting(true);
    try {
      const res = await publicApi.submitTourRequest(form);
      setDone(res.when ?? `${day} ${timeLabel(time)}`);
      window.scrollTo(0, 0);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="py-8">
        <h1 className="text-3xl font-bold text-gray-900">Request received</h1>
        <p className="mt-4 text-gray-700">
          Thanks! We received your request to tour{' '}
          <strong>
            {listing?.address_line1}
            {listing?.address_line2 ? `, ${listing.address_line2}` : ''}
          </strong>{' '}
          on <strong>{done}</strong>.
        </p>
        <p className="mt-3 text-gray-700">
          We'll review it and let you know soon. If it's approved, your one-time access code will be
          sent 30 minutes before your tour. A confirmation is on its way to your email.
        </p>
        <Link to="/" className="mt-8 inline-block font-medium text-blue-700 hover:underline">
          &larr; Back to available homes
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">Request a tour</h1>
      <p className="mt-2 text-gray-600">
        Tours are self-guided, last up to 30 minutes, and can start any day between 8:00 am and 7:30
        pm in the home's local time.
      </p>

      {listing && (
        <div className="mt-6 flex gap-4 rounded-lg border bg-gray-50 p-3">
          {listing.photo_urls[0] && (
            <img
              src={listing.photo_urls[0]}
              alt=""
              className="h-20 w-28 shrink-0 rounded object-cover"
            />
          )}
          <div className="min-w-0 text-sm">
            <p className="font-semibold text-gray-900">{listing.headline}</p>
            <p className="text-gray-600">
              {listing.address_line1}
              {listing.address_line2 ? `, ${listing.address_line2}` : ''}, {listing.city},{' '}
              {listing.state}
            </p>
            <p className="text-gray-900">
              {money(listing.monthly_rent)}/mo ·{' '}
              <Link to={`/homes/${listing.id}`} className="text-blue-700 hover:underline">
                View details
              </Link>
            </p>
          </div>
        </div>
      )}

      {meLoading && signedInAs === undefined ? (
        <p className="mt-6 text-sm text-gray-500">Loading…</p>
      ) : !visitorEmail ? (
        <>
          <EmailSignIn onSignedIn={(email) => setSignedInAs(email)} />
          {/* Shown before sign-in too, so the SMS opt-in wording is publicly visible
              (carrier / Twilio toll-free verification reviews this page). */}
          <div className="mt-4 rounded-lg bg-gray-50 p-4 text-xs text-gray-600">
            <p className="font-medium text-gray-700">Text message updates (optional)</p>
            <p className="mt-1">
              After verifying your email you can choose to get texts by checking a box that reads: “
              {SMS_CONSENT_TEXT}” See our{' '}
              <Link to="/sms-terms" className="underline">
                SMS Terms
              </Link>{' '}
              and{' '}
              <Link to="/privacy" className="underline">
                Privacy Policy
              </Link>
              .
            </p>
          </div>
        </>
      ) : (
        <form className="mt-6 space-y-5" onSubmit={onSubmit}>
          <div>
            <Label htmlFor="property">{listing ? 'Touring' : 'Home'}</Label>
            <select
              id="property"
              className={input}
              value={selectedHome}
              onChange={(e) => {
                setHome(e.target.value);
                setTime('');
              }}
              required
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
              <input
                id="first"
                name="first_name"
                className={input}
                autoComplete="given-name"
                required
                maxLength={100}
              />
            </div>
            <div>
              <Label htmlFor="last">Last name</Label>
              <input
                id="last"
                name="last_name"
                className={input}
                autoComplete="family-name"
                required
                maxLength={100}
              />
            </div>
            <div>
              <Label htmlFor="email">Email (verified)</Label>
              <input
                id="email"
                type="email"
                className={input}
                value={visitorEmail ?? ''}
                readOnly
                disabled
              />
              <button
                type="button"
                onClick={async () => {
                  await publicApi.signOut().catch(() => undefined);
                  setSignedInAs(null);
                }}
                className="mt-1 text-xs text-gray-500 underline"
              >
                Not you? Use a different email
              </button>
            </div>
            <div>
              <Label htmlFor="phone">Mobile phone</Label>
              <input
                id="phone"
                name="phone"
                type="tel"
                className={input}
                autoComplete="tel"
                placeholder="(555) 555-5555"
                required
              />
            </div>
            <div>
              <Label htmlFor="date">Tour date</Label>
              <input
                id="date"
                type="date"
                className={input}
                value={day}
                min={isoDay(today)}
                max={isoDay(maxDay)}
                onChange={(e) => {
                  setDay(e.target.value);
                  setTime('');
                }}
                disabled={!selectedHome}
                required
              />
            </div>
            <div>
              <Label htmlFor="time">Start time ({tzName})</Label>
              <select
                id="time"
                className={input}
                value={time}
                onChange={(e) => setTime(e.target.value)}
                disabled={!day || slotsLoading}
                required
              >
                <option value="" disabled>
                  {!day
                    ? 'Pick a date first'
                    : slotsLoading
                      ? 'Loading times…'
                      : openSlots.length
                        ? 'Select a time'
                        : 'No times left this day'}
                </option>
                {openSlots.map((s) => (
                  <option key={s.time} value={s.time}>
                    {timeLabel(s.time)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <Label htmlFor="photo-id">Photo of your government-issued ID</Label>
            <input
              id="photo-id"
              name="id_photo"
              type="file"
              accept="image/*"
              className="block text-sm"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Used only to verify your identity for this tour. Deleted automatically 30 days after
              your tour.
            </p>
          </div>

          {/* Honeypot: hidden from people, filled in by bots. */}
          <div aria-hidden="true" className="absolute -left-[9999px] h-0 overflow-hidden">
            <label htmlFor="website">Website</label>
            <input id="website" name="website" tabIndex={-1} autoComplete="off" />
          </div>

          <label className="flex items-start gap-3 text-sm text-gray-700">
            {/* Unchecked by default and optional, as carrier rules require. */}
            <input id="sms-consent" name="sms_consent" type="checkbox" className="mt-1" />
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
            disabled={submitting}
            className="rounded bg-blue-700 px-5 py-2.5 text-white font-medium hover:bg-blue-800 disabled:opacity-60"
          >
            {submitting ? 'Sending…' : 'Submit tour request'}
          </button>
          <p className="text-xs text-gray-500">
            Questions? Email{' '}
            <a href={`mailto:${COMPANY.email}`} className="underline">
              {COMPANY.email}
            </a>
            .
          </p>
        </form>
      )}
    </div>
  );
};
