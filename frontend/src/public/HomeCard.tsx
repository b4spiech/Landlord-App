import { Link } from 'react-router-dom';
import type { PublicListing } from '../types';
import { availability, money, specs } from './listingFormat';

/** Homepage card: photo/title open the details page; the button books a tour of this home. */
export const HomeCard = ({ listing }: { listing: PublicListing }) => (
  <div className="flex flex-col overflow-hidden rounded-lg border hover:shadow-md transition-shadow">
    <Link to={`/homes/${listing.id}`} className="group block">
      <div className="aspect-[4/3] bg-gray-100">
        {listing.photo_urls[0] ? (
          <img
            src={listing.photo_urls[0]}
            alt={listing.headline}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-gray-400">
            Photos coming soon
          </div>
        )}
      </div>
      <div className="p-4 pb-2">
        <p className="text-xl font-bold text-gray-900">
          {money(listing.monthly_rent)}
          <span className="text-sm font-normal text-gray-500">/mo</span>
        </p>
        <p className="mt-1 text-sm text-gray-700">{specs(listing)}</p>
        <p className="mt-1 font-medium text-gray-900 group-hover:text-blue-700">{listing.headline}</p>
        <p className="text-sm text-gray-500">
          {listing.address_line1}
          {listing.address_line2 ? `, ${listing.address_line2}` : ''}, {listing.city}, {listing.state}
        </p>
        {availability(listing.available_date) && (
          <p className="mt-2 text-xs font-medium text-green-700">{availability(listing.available_date)}</p>
        )}
      </div>
    </Link>
    <div className="mt-auto flex gap-2 p-4 pt-2">
      <Link
        to={`/tour?home=${listing.id}`}
        className="flex-1 rounded bg-blue-700 px-4 py-2 text-center text-sm font-medium text-white hover:bg-blue-800"
      >
        Request a tour
      </Link>
      <Link
        to={`/homes/${listing.id}`}
        className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
      >
        Details
      </Link>
    </div>
  </div>
);
