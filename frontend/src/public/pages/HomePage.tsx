import { Link } from 'react-router-dom';
import { COMPANY } from '../company';

export const HomePage = () => (
  <div className="space-y-8">
    <section>
      <h1 className="text-3xl font-bold text-gray-900">Available homes</h1>
      <p className="mt-2 text-gray-600">
        Tour one of our rentals on your schedule. Request a time, and once it's approved you'll
        get a one-time door code just before your tour.
      </p>
    </section>

    {/* Listings arrive in a later phase; until then show an honest empty state. */}
    <section className="rounded-lg border border-dashed p-8 text-center">
      <p className="font-medium text-gray-900">No homes are open for tours right now.</p>
      <p className="mt-1 text-sm text-gray-600">
        Check back soon, or email{' '}
        <a href={`mailto:${COMPANY.email}`} className="text-blue-700 hover:underline">
          {COMPANY.email}
        </a>
        .
      </p>
    </section>

    <section>
      <h2 className="text-lg font-semibold text-gray-900">How self-guided tours work</h2>
      <ol className="mt-3 space-y-2 text-gray-700 list-decimal list-inside">
        <li>Pick a home and a time (any day, 8:00 am – 8:00 pm, local time).</li>
        <li>Share your contact details and a photo of your ID.</li>
        <li>We review your request and let you know by email or text.</li>
        <li>30 minutes before your tour, you receive a one-time access code.</li>
      </ol>
      <Link
        to="/tour"
        className="inline-block mt-5 rounded bg-blue-700 px-5 py-2.5 text-white font-medium hover:bg-blue-800"
      >
        Request a tour
      </Link>
    </section>
  </div>
);
