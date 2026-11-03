import { Link } from 'react-router-dom';
import { COMPANY } from '../company';
import { HomeCard } from '../HomeCard';
import { publicApi } from '../publicApi';
import { useLoad } from '../useLoad';

// Company homepage (apexelementgrp.com) and tour-site landing page. Keep the
// copy factual: carriers (Twilio verification) check that this site matches
// the business name and describes what it actually does.
export const HomePage = () => {
  const { data: listings, error, loading } = useLoad(publicApi.listings, 'listings');

  return (
    <div className="space-y-12">
      <section className="pt-4">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
          Residential rentals
        </p>
        <h1 className="mt-2 text-4xl font-bold text-gray-900">{COMPANY.legalName}</h1>
        <p className="mt-4 text-lg text-gray-600">
          We own and manage residential rental homes, including properties in Tucson, Arizona. We
          offer well-kept homes, straightforward leases, and self-guided tours on your schedule.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to="/tour"
            className="rounded bg-blue-700 px-5 py-2.5 text-white font-medium hover:bg-blue-800"
          >
            Request a tour
          </Link>
          <a
            href={`mailto:${COMPANY.email}`}
            className="rounded border border-gray-300 px-5 py-2.5 font-medium text-gray-800 hover:bg-gray-50"
          >
            Contact us
          </a>
        </div>
      </section>

      <section id="homes">
        <h2 className="text-2xl font-semibold text-gray-900">Available homes</h2>
        {loading && <p className="mt-4 text-sm text-gray-500">Loading homes…</p>}
        {error && (
          <p className="mt-4 text-sm text-red-600">Couldn't load homes. Please refresh the page.</p>
        )}
        {listings && listings.length > 0 && (
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            {listings.map((l) => (
              <HomeCard key={l.id} listing={l} />
            ))}
          </div>
        )}
        {listings && listings.length === 0 && (
          <div className="mt-4 rounded-lg border border-dashed p-8 text-center">
            <p className="font-medium text-gray-900">No homes are open for tours right now.</p>
            <p className="mt-1 text-sm text-gray-600">
              Check back soon, or email{' '}
              <a href={`mailto:${COMPANY.email}`} className="text-blue-700 hover:underline">
                {COMPANY.email}
              </a>
              .
            </p>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-2xl font-semibold text-gray-900">How self-guided tours work</h2>
        <ol className="mt-4 grid gap-4 sm:grid-cols-2">
          {[
            ['Pick a home and a time', "Any day, 8:00 am – 8:00 pm in the home's local time."],
            ['Share your details', 'Your name, contact info, and a photo of your ID.'],
            ['Get approved', 'We review your request and let you know by email or text.'],
            ['Tour on your own', 'A one-time door code arrives 30 minutes before your tour.'],
          ].map(([title, body], i) => (
            <li key={title} className="rounded-lg border p-4">
              <p className="text-sm font-semibold text-blue-700">Step {i + 1}</p>
              <p className="mt-1 font-medium text-gray-900">{title}</p>
              <p className="mt-1 text-sm text-gray-600">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-lg bg-gray-50 p-6">
        <h2 className="text-xl font-semibold text-gray-900">Contact</h2>
        <p className="mt-2 text-gray-700">
          Questions about a home or a tour? Email{' '}
          <a href={`mailto:${COMPANY.email}`} className="text-blue-700 hover:underline">
            {COMPANY.email}
          </a>
          .
        </p>
      </section>
    </div>
  );
};
