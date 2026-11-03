import { Link } from 'react-router-dom';
import type { PublicListing } from '../types';
import { publicApi } from './publicApi';
import { availability, money, specs } from './listingFormat';

export const HomeCard = ({ listing }: { listing: PublicListing }) => (
  <Link
    to={`/homes/${listing.id}`}
    className="group block overflow-hidden rounded-lg border hover:shadow-md transition-shadow"
  >
    <div className="aspect-[4/3] bg-gray-100">
      {listing.photo_ids[0] ? (
        <img
          src={publicApi.photoUrl(listing.id, listing.photo_ids[0])}
          alt={listing.headline}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      ) : (
        <div className="flex h-full items-center justify-center text-sm text-gray-400">Photos coming soon</div>
      )}
    </div>
    <div className="p-4">
      <p className="text-xl font-bold text-gray-900">
        {money(listing.monthly_rent)}
        <span className="text-sm font-normal text-gray-500">/mo</span>
      </p>
      <p className="mt-1 text-sm text-gray-700">{specs(listing)}</p>
      <p className="mt-1 font-medium text-gray-900 group-hover:text-blue-700">{listing.headline}</p>
      <p className="text-sm text-gray-500">
        {listing.city}, {listing.state}
      </p>
      {availability(listing.available_date) && (
        <p className="mt-2 text-xs font-medium text-green-700">{availability(listing.available_date)}</p>
      )}
    </div>
  </Link>
);
