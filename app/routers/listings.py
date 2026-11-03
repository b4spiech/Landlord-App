"""Landlord-side listing management: list a property, edit details, photos, close."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import Listing, ListingPhoto, Property
from app.models.base import utcnow
from app.models.enums import ListingStatus
from app.models.listing import OPEN_LISTING_STATUSES
from app.routers.crud import get_or_404
from app.schemas.listing import (
    ListingClose,
    ListingCreate,
    ListingPhotoRead,
    ListingRead,
    ListingUpdate,
    PhotoOrder,
)

router = APIRouter(prefix="/listings", tags=["listings"])

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTOS = 30
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


def photo_ids(session: Session, listing_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.exec(
            select(ListingPhoto.id)
            .where(ListingPhoto.listing_id == listing_id)
            .order_by(ListingPhoto.sort_order, ListingPhoto.created_at)
        ).all()
    )


def public_listing_url(listing_id: uuid.UUID) -> str:
    return f"{settings.PUBLIC_SITE_URL.rstrip('/')}/homes/{listing_id}"


def to_read(session: Session, listing: Listing) -> ListingRead:
    out = ListingRead.model_validate(listing)
    out.photo_ids = photo_ids(session, listing.id)
    out.public_url = public_listing_url(listing.id) if listing.status == ListingStatus.listed.value else None
    return out


def _apply_fields(listing: Listing, payload) -> None:
    data = payload.model_dump(exclude_unset=True, exclude={"property_id", "publish"}, mode="json")
    for key, value in data.items():
        if key == "channels" and value is None:
            value = []
        setattr(listing, key, value)
    # model_dump(mode="json") turns dates into strings; restore real dates.
    if "available_date" in data:
        listing.available_date = payload.available_date


def _publish_problems(listing: Listing) -> list[str]:
    problems = []
    if not listing.monthly_rent:
        problems.append("monthly rent")
    if not listing.available_date:
        problems.append("available date")
    return problems


def _publish(listing: Listing) -> None:
    problems = _publish_problems(listing)
    if problems:
        raise HTTPException(status_code=422, detail=f"Add the {' and '.join(problems)} before publishing.")
    listing.status = ListingStatus.listed.value
    listing.listed_at = listing.listed_at or utcnow()


def _get_open(session: Session, listing_id: uuid.UUID) -> Listing:
    listing = get_or_404(session, Listing, listing_id, "Listing")
    if listing.status not in OPEN_LISTING_STATUSES:
        raise HTTPException(status_code=409, detail="This listing is closed. Start a new listing instead.")
    return listing


@router.get("", response_model=list[ListingRead])
def list_listings(
    property_id: Optional[uuid.UUID] = None,
    status_filter: Optional[ListingStatus] = None,
    open_only: bool = False,
    session: Session = Depends(get_session),
):
    stmt = select(Listing)
    if property_id:
        stmt = stmt.where(Listing.property_id == property_id)
    if status_filter:
        stmt = stmt.where(Listing.status == status_filter.value)
    if open_only:
        stmt = stmt.where(Listing.status.in_(OPEN_LISTING_STATUSES))
    stmt = stmt.order_by(Listing.created_at.desc())
    return [to_read(session, l) for l in session.exec(stmt).all()]


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, session: Session = Depends(get_session)):
    get_or_404(session, Property, payload.property_id, "Property")
    existing = session.exec(
        select(Listing).where(
            Listing.property_id == payload.property_id, Listing.status.in_(OPEN_LISTING_STATUSES)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This property already has an open listing.")

    listing = Listing(property_id=payload.property_id)
    _apply_fields(listing, payload)
    if payload.publish:
        _publish(listing)
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return to_read(session, listing)


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: uuid.UUID, session: Session = Depends(get_session)):
    return to_read(session, get_or_404(session, Listing, listing_id, "Listing"))


@router.patch("/{listing_id}", response_model=ListingRead)
def update_listing(listing_id: uuid.UUID, payload: ListingUpdate, session: Session = Depends(get_session)):
    listing = _get_open(session, listing_id)
    _apply_fields(listing, payload)
    if listing.status == ListingStatus.listed.value:
        _publish(listing)  # re-validate: a live listing must keep rent + date
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return to_read(session, listing)


@router.post("/{listing_id}/publish", response_model=ListingRead)
def publish_listing(listing_id: uuid.UUID, session: Session = Depends(get_session)):
    listing = _get_open(session, listing_id)
    _publish(listing)
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return to_read(session, listing)


@router.post("/{listing_id}/unpublish", response_model=ListingRead)
def unpublish_listing(listing_id: uuid.UUID, session: Session = Depends(get_session)):
    """Take it off the public site but keep it as a draft."""
    listing = _get_open(session, listing_id)
    listing.status = ListingStatus.draft.value
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return to_read(session, listing)


@router.post("/{listing_id}/close", response_model=ListingRead)
def close_listing(listing_id: uuid.UUID, payload: ListingClose, session: Session = Depends(get_session)):
    listing = _get_open(session, listing_id)
    listing.status = ListingStatus.closed.value
    listing.close_reason = payload.reason.value
    listing.closed_at = utcnow()
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return to_read(session, listing)


# --- Photos -------------------------------------------------------------------


@router.get("/{listing_id}/photos", response_model=list[ListingPhotoRead])
def list_photos(listing_id: uuid.UUID, session: Session = Depends(get_session)):
    get_or_404(session, Listing, listing_id, "Listing")
    return session.exec(
        select(ListingPhoto)
        .where(ListingPhoto.listing_id == listing_id)
        .order_by(ListingPhoto.sort_order, ListingPhoto.created_at)
    ).all()


@router.post("/{listing_id}/photos", response_model=list[ListingPhotoRead], status_code=status.HTTP_201_CREATED)
async def upload_photos(
    listing_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
):
    _get_open(session, listing_id)
    count = session.exec(select(func.count()).select_from(ListingPhoto).where(ListingPhoto.listing_id == listing_id)).one()
    if count + len(files) > MAX_PHOTOS:
        raise HTTPException(status_code=422, detail=f"A listing can have at most {MAX_PHOTOS} photos.")

    max_order = session.exec(
        select(func.max(ListingPhoto.sort_order)).where(ListingPhoto.listing_id == listing_id)
    ).one()
    next_order = (max_order if max_order is not None else -1) + 1

    created = []
    for f in files:
        if f.content_type not in ALLOWED_PHOTO_TYPES:
            raise HTTPException(status_code=422, detail=f"{f.filename}: upload JPG, PNG, or WEBP images.")
        content = await f.read()
        if not content:
            raise HTTPException(status_code=422, detail=f"{f.filename} is empty.")
        if len(content) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail=f"{f.filename} exceeds the 10 MB limit.")
        photo = ListingPhoto(
            listing_id=listing_id,
            sort_order=next_order,
            filename=f.filename,
            content_type=f.content_type,
            file_size=len(content),
            content=content,
        )
        next_order += 1
        session.add(photo)
        created.append(photo)
    session.commit()
    for p in created:
        session.refresh(p)
    return created


@router.put("/{listing_id}/photos/order", response_model=list[ListingPhotoRead])
def reorder_photos(listing_id: uuid.UUID, payload: PhotoOrder, session: Session = Depends(get_session)):
    get_or_404(session, Listing, listing_id, "Listing")
    photos = {
        p.id: p for p in session.exec(select(ListingPhoto).where(ListingPhoto.listing_id == listing_id)).all()
    }
    if set(payload.photo_ids) != set(photos):
        raise HTTPException(status_code=422, detail="Photo list doesn't match this listing's photos.")
    for i, pid in enumerate(payload.photo_ids):
        photos[pid].sort_order = i
        session.add(photos[pid])
    session.commit()
    return list_photos(listing_id, session)


@router.get("/{listing_id}/photos/{photo_id}")
def get_photo(listing_id: uuid.UUID, photo_id: uuid.UUID, session: Session = Depends(get_session)):
    photo = session.get(ListingPhoto, photo_id)
    if photo is None or photo.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="Photo not found")
    return Response(content=photo.content, media_type=photo.content_type or "image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400"})


@router.delete("/{listing_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(listing_id: uuid.UUID, photo_id: uuid.UUID, session: Session = Depends(get_session)):
    photo = session.get(ListingPhoto, photo_id)
    if photo is None or photo.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="Photo not found")
    session.delete(photo)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
