"""Rental listings: when a property is on the market, and the details shown to prospects."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, Index, LargeBinary, text
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import ListingStatus

# A property can have many listings over the years, but at most one that is
# still open (draft or listed).
OPEN_LISTING_STATUSES = (ListingStatus.draft.value, ListingStatus.listed.value)


class Listing(TimestampMixin, table=True):
    __tablename__ = "listing"
    __table_args__ = (
        Index(
            "uq_listing_open_per_property",
            "property_id",
            unique=True,
            postgresql_where=text("status IN ('draft', 'listed')"),
        ),
    )

    property_id: uuid.UUID = Field(foreign_key="property.id", index=True)
    status: str = Field(default=ListingStatus.draft.value, max_length=20, index=True)
    close_reason: Optional[str] = Field(default=None, max_length=20)

    # --- Shown publicly -------------------------------------------------
    headline: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None)
    monthly_rent: Optional[float] = Field(default=None)
    security_deposit: Optional[float] = Field(default=None)
    available_date: Optional[date] = Field(default=None)
    lease_term_months: Optional[int] = Field(default=None)
    pet_policy: Optional[str] = Field(default=None, max_length=30)
    utilities_included: Optional[str] = Field(default=None, max_length=300)

    # --- Landlord only ----------------------------------------------------
    # Where it's advertised: [{"channel": "zillow_rental_manager", "url": "...", "listed_on": "2026-11-03"}]
    channels: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]"))
    internal_notes: Optional[str] = Field(default=None)

    listed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    closed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))


class ListingPhoto(TimestampMixin, table=True):
    """A listing photo (bytes in Postgres; the deploy disk is ephemeral)."""

    __tablename__ = "listing_photo"

    listing_id: uuid.UUID = Field(foreign_key="listing.id", index=True)
    sort_order: int = Field(default=0)
    filename: Optional[str] = Field(default=None, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=120)
    file_size: Optional[int] = Field(default=None)
    content: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
