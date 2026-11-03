"""Customer-facing (unauthenticated) API — the ONLY API reachable on public hosts.

Everything here must be safe for anonymous internet traffic: return only data
meant for prospects, never landlord/tenant records. Only listings with status
``listed`` are visible.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.database import get_session
from app.models import Listing, ListingPhoto, Property
from app.models.enums import ListingStatus
from app.routers.listings import photo_ids
from app.schemas.listing import PublicListing
from app.services.timezones import property_time_zone

router = APIRouter(prefix="/public", tags=["public"])

COMPANY = {
    "name": "APEX Element Group LLC",
    "contact_email": "tours@apexelementgrp.com",
}


@router.get("/site")
def site_info():
    """Company details shown in the public site header/footer and legal pages."""
    return COMPANY


def _default_headline(prop: Property) -> str:
    parts = []
    if prop.bedrooms is not None:
        parts.append(f"{prop.bedrooms} bd")
    if prop.bathrooms is not None:
        parts.append(f"{prop.bathrooms:g} ba")
    kind = prop.property_type.replace("_", " ").title()
    lead = " / ".join(parts)
    return f"{lead} {kind} in {prop.city}".strip()


def _to_public(session: Session, listing: Listing, prop: Property) -> PublicListing:
    return PublicListing(
        id=listing.id,
        headline=listing.headline or _default_headline(prop),
        description=listing.description,
        property_type=prop.property_type,
        address_line1=prop.address_line1,
        address_line2=prop.address_line2,
        city=prop.city,
        state=prop.state,
        postal_code=prop.postal_code,
        bedrooms=prop.bedrooms,
        bathrooms=prop.bathrooms,
        square_feet=prop.square_feet,
        monthly_rent=listing.monthly_rent,
        security_deposit=listing.security_deposit,
        available_date=listing.available_date,
        lease_term_months=listing.lease_term_months,
        pet_policy=listing.pet_policy,
        utilities_included=listing.utilities_included,
        time_zone=property_time_zone(prop),
        photo_ids=photo_ids(session, listing.id),
    )


def _get_live(session: Session, listing_id: uuid.UUID) -> tuple[Listing, Property]:
    listing = session.get(Listing, listing_id)
    if listing is None or listing.status != ListingStatus.listed.value:
        raise HTTPException(status_code=404, detail="This home isn't available.")
    return listing, session.get(Property, listing.property_id)


@router.get("/listings", response_model=list[PublicListing])
def public_listings(session: Session = Depends(get_session)):
    rows = session.exec(
        select(Listing, Property)
        .join(Property, Property.id == Listing.property_id)
        .where(Listing.status == ListingStatus.listed.value)
        .order_by(Listing.listed_at.desc())
    ).all()
    return [_to_public(session, l, p) for l, p in rows]


@router.get("/listings/{listing_id}", response_model=PublicListing)
def public_listing(listing_id: uuid.UUID, session: Session = Depends(get_session)):
    listing, prop = _get_live(session, listing_id)
    return _to_public(session, listing, prop)


@router.get("/listings/{listing_id}/photos/{photo_id}")
def public_listing_photo(listing_id: uuid.UUID, photo_id: uuid.UUID, session: Session = Depends(get_session)):
    _get_live(session, listing_id)
    photo = session.get(ListingPhoto, photo_id)
    if photo is None or photo.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Photo bytes never change for a given id, so let browsers/Cloudflare cache.
    return Response(content=photo.content, media_type=photo.content_type or "image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})
