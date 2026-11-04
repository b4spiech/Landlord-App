import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getErrorMessage, listingAPI } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { formatCurrency } from '../lib/format';
import { CHANNEL_LABELS, LISTING_STATUS_LABELS, formatCalendarDate, listingStatusVariant } from '../lib/listing';
import { Button, Card } from './ui';
import { StatusBadge } from './StatusBadge';
import { useToast } from './Toast';
import { ShareListingButton } from './ShareListing';

/** Property-page summary of the open listing, or a "List this property" action. */
export const ListingCard = ({ propertyId }: { propertyId: string }) => {
  const toast = useToast();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const { data, loading, reload } = useAsync(
    () => listingAPI.list({ property_id: propertyId, open_only: true }),
    [propertyId],
  );
  const listing = data?.[0];

  const startListing = async () => {
    setBusy(true);
    try {
      const created = await listingAPI.create({ property_id: propertyId });
      navigate(`/listings/${created.id}`);
    } catch (err) {
      toast.error(getErrorMessage(err));
      reload();
    } finally {
      setBusy(false);
    }
  };

  const copyLink = async (url: string) => {
    await navigator.clipboard.writeText(url);
    toast.success('Link copied');
  };

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-gray-900">Listing</h2>
        {listing ? (
          <StatusBadge
            status={LISTING_STATUS_LABELS[listing.status]}
            variant={listingStatusVariant(listing.status)}
          />
        ) : (
          !loading && <StatusBadge status="Not listed" variant="gray" />
        )}
      </div>

      {!loading && !listing && (
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-gray-500">
            List this property to show it on the public tour site.
          </p>
          <Button onClick={startListing} disabled={busy}>
            List this property
          </Button>
        </div>
      )}

      {listing && (
        <div className="space-y-3 text-sm">
          <dl className="grid grid-cols-2 gap-y-2">
            <dt className="text-gray-500">Rent</dt>
            <dd className="text-right">
              {listing.monthly_rent ? `${formatCurrency(listing.monthly_rent)}/mo` : '—'}
            </dd>
            <dt className="text-gray-500">Available</dt>
            <dd className="text-right">{formatCalendarDate(listing.available_date)}</dd>
            <dt className="text-gray-500">Listed on</dt>
            <dd className="text-right">
              {listing.channels.length
                ? listing.channels.map((c) => CHANNEL_LABELS[c.channel]).join(', ')
                : '—'}
            </dd>
          </dl>
          {listing.public_url && (
            <div className="flex items-center gap-2 rounded bg-gray-50 px-3 py-2">
              <a
                href={listing.public_url}
                target="_blank"
                rel="noreferrer"
                className="flex-1 truncate text-blue-600 hover:underline"
              >
                {listing.public_url}
              </a>
              <button
                onClick={() => copyLink(listing.public_url!)}
                className="text-xs font-medium text-gray-600 hover:underline"
              >
                Copy link
              </button>
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => navigate(`/listings/${listing.id}`)}>
              Manage listing
            </Button>
            {listing.status === 'listed' && <ShareListingButton listingId={listing.id} />}
          </div>
        </div>
      )}
    </Card>
  );
};
