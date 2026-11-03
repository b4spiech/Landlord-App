import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ListingChannel, ListingCloseReason, PetPolicy
from app.schemas.common import ORMModel, TimestampedRead


class ListingChannelEntry(BaseModel):
    channel: ListingChannel
    url: Optional[str] = Field(default=None, max_length=1000)
    listed_on: Optional[date] = None

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v):
        if v is None or not v.strip():
            return None
        v = v.strip()
        return v if v.startswith(("http://", "https://")) else f"https://{v}"


class ListingFields(BaseModel):
    headline: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    monthly_rent: Optional[float] = Field(default=None, ge=0)
    security_deposit: Optional[float] = Field(default=None, ge=0)
    available_date: Optional[date] = None
    lease_term_months: Optional[int] = Field(default=None, ge=1, le=60)
    pet_policy: Optional[PetPolicy] = None
    utilities_included: Optional[str] = Field(default=None, max_length=300)
    channels: Optional[list[ListingChannelEntry]] = None
    internal_notes: Optional[str] = None


class ListingCreate(ListingFields):
    property_id: uuid.UUID
    publish: bool = False  # create and immediately make public


class ListingUpdate(ListingFields):
    pass


class ListingClose(BaseModel):
    reason: ListingCloseReason


class ListingRead(TimestampedRead):
    property_id: uuid.UUID
    status: str
    close_reason: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    available_date: Optional[date] = None
    lease_term_months: Optional[int] = None
    pet_policy: Optional[str] = None
    utilities_included: Optional[str] = None
    channels: list[dict] = []
    internal_notes: Optional[str] = None
    listed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    photo_ids: list[uuid.UUID] = []
    public_url: Optional[str] = None


class ListingPhotoRead(ORMModel):
    id: uuid.UUID
    sort_order: int
    filename: Optional[str] = None
    file_size: Optional[int] = None


class PhotoOrder(BaseModel):
    photo_ids: list[uuid.UUID]


# --- Public (anonymous) ------------------------------------------------------
# Only what a prospect should see: no owner, tenant, notes, or channel data.


class PublicListing(BaseModel):
    id: uuid.UUID
    headline: str
    description: Optional[str] = None
    property_type: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    available_date: Optional[date] = None
    lease_term_months: Optional[int] = None
    pet_policy: Optional[str] = None
    utilities_included: Optional[str] = None
    time_zone: str
    # Ready-to-use image URLs, cover first. Falls back to the property's own
    # photo when the listing has no photos of its own.
    photo_urls: list[str] = []
