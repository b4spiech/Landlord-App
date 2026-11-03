import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { SMS_CONSENT_TEXT } from '../company';

// Phase 0: the form layout and SMS opt-in wording are final (Twilio's
// toll-free verification reviews this page), but submission is switched on
// in a later phase once listings and the tour-request API exist.
const BOOKING_OPEN = false;

const input =
  'w-full rounded border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-500';

const Label = ({ children, htmlFor }: { children: ReactNode; htmlFor: string }) => (
  <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 mb-1">
    {children}
  </label>
);

export const TourRequestPage = () => (
  <div>
    <h1 className="text-3xl font-bold text-gray-900">Request a tour</h1>
    <p className="mt-2 text-gray-600">
      Tours are self-guided, last up to 30 minutes, and can start any day between 8:00 am and
      7:30 pm in the home's local time.
    </p>

    {!BOOKING_OPEN && (
      <div className="mt-6 rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        Online tour booking opens soon. No homes are open for tours right now.
      </div>
    )}

    <form className="mt-6 space-y-5" onSubmit={(e) => e.preventDefault()}>
      <fieldset disabled={!BOOKING_OPEN} className="space-y-5">
        <div>
          <Label htmlFor="property">Home</Label>
          <select id="property" className={input} defaultValue="">
            <option value="" disabled>
              No homes available
            </option>
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
            {SMS_CONSENT_TEXT}{' '}
            See our{' '}
            <Link to="/sms-terms" className="text-blue-700 hover:underline">SMS Terms</Link> and{' '}
            <Link to="/privacy" className="text-blue-700 hover:underline">Privacy Policy</Link>.
          </span>
        </label>

        <button
          type="submit"
          className="rounded bg-blue-700 px-5 py-2.5 text-white font-medium hover:bg-blue-800 disabled:opacity-50"
        >
          Submit tour request
        </button>
      </fieldset>
    </form>
  </div>
);
