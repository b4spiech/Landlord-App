import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PET_POLICY_LABELS } from '../../lib/listing';
import { publicApi } from '../publicApi';
import { useLoad } from '../useLoad';
import { address, availability, money, specs } from '../listingFormat';

const TZ_NAMES: Record<string, string> = {
  'America/Phoenix': 'Arizona time',
  'America/Detroit': 'Eastern time',
  'America/New_York': 'Eastern time',
  'America/Chicago': 'Central time',
  'America/Denver': 'Mountain time',
  'America/Los_Angeles': 'Pacific time',
};

export const ListingPage = () => {
  const { id } = useParams<{ id: string }>();
  const { data: listing, error, loading } = useLoad(() => publicApi.listing(id!), id!);
  const [active, setActive] = useState(0);

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>;
  if (error || !listing)
    return (
      <div className="py-16 text-center">
        <h1 className="text-2xl font-semibold">This home isn't available</h1>
        <p className="mt-2 text-gray-600">It may have been rented. See what's open now.</p>
        <Link to="/" className="mt-6 inline-block font-medium text-blue-700 hover:underline">
          &larr; Available homes
        </Link>
      </div>
    );

  const photos = listing.photo_ids;
  const facts: [string, string | null | undefined][] = [
    ['Rent', `${money(listing.monthly_rent)}/mo`],
    ['Security deposit', listing.security_deposit != null ? money(listing.security_deposit) : null],
    ['Available', availability(listing.available_date)?.replace('Available ', '')],
    ['Minimum lease', listing.lease_term_months ? `${listing.lease_term_months} months` : null],
    ['Pets', listing.pet_policy ? PET_POLICY_LABELS[listing.pet_policy] : null],
    ['Utilities included', listing.utilities_included],
  ];

  return (
    <div className="space-y-6">
      <Link to="/" className="text-sm text-blue-700 hover:underline">
        &larr; All homes
      </Link>

      {photos.length > 0 && (
        <div>
          <img
            src={publicApi.photoUrl(listing.id, photos[active])}
            alt={`${listing.headline} photo ${active + 1}`}
            className="aspect-[4/3] w-full rounded-lg object-cover bg-gray-100"
          />
          {photos.length > 1 && (
            <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
              {photos.map((pid, i) => (
                <button key={pid} onClick={() => setActive(i)} className="shrink-0">
                  <img
                    src={publicApi.photoUrl(listing.id, pid)}
                    alt={`Photo ${i + 1}`}
                    loading="lazy"
                    className={`h-16 w-24 rounded object-cover ${i === active ? 'ring-2 ring-blue-700' : 'opacity-70 hover:opacity-100'}`}
                  />
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{listing.headline}</h1>
          <p className="mt-1 text-gray-600">{address(listing)}</p>
          <p className="mt-1 text-gray-700">{specs(listing)}</p>
        </div>
        <p className="text-3xl font-bold text-gray-900">
          {money(listing.monthly_rent)}
          <span className="text-base font-normal text-gray-500">/mo</span>
        </p>
      </div>

      <Link
        to={`/tour?home=${listing.id}`}
        className="inline-block rounded bg-blue-700 px-6 py-3 text-white font-medium hover:bg-blue-800"
      >
        Request a tour
      </Link>
      <p className="text-sm text-gray-500">
        Self-guided tours, any day 8:00 am – 8:00 pm {TZ_NAMES[listing.time_zone] ?? 'local time'}.
      </p>

      <dl className="grid gap-x-8 gap-y-3 rounded-lg border p-5 sm:grid-cols-2">
        {facts
          .filter(([, v]) => v)
          .map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 text-sm">
              <dt className="text-gray-500">{k}</dt>
              <dd className="text-right font-medium text-gray-900">{v}</dd>
            </div>
          ))}
      </dl>

      {listing.description && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900">About this home</h2>
          <p className="mt-2 whitespace-pre-line text-gray-700 leading-relaxed">{listing.description}</p>
        </section>
      )}
    </div>
  );
};
