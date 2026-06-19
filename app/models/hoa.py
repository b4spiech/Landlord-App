import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, LargeBinary
from sqlmodel import Field

from app.models.base import TimestampMixin


class HOA(TimestampMixin, table=True):
    """A homeowners' / condo association. One HOA may cover many properties."""

    __tablename__ = "hoa"

    name: str = Field(index=True, max_length=200)

    # Primary contact
    contact_name: Optional[str] = Field(default=None, max_length=200)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    website: Optional[str] = Field(default=None, max_length=255)

    # Management company running the HOA (often different from the property mgr)
    management_company_name: Optional[str] = Field(default=None, max_length=200)

    # Mailing address
    address_line1: Optional[str] = Field(default=None, max_length=200)
    address_line2: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=2)
    postal_code: Optional[str] = Field(default=None, max_length=20)

    # Dues
    dues_amount: Optional[float] = Field(default=None)
    dues_frequency: Optional[str] = Field(
        default=None, max_length=20, description="monthly | quarterly | annual"
    )

    notes: Optional[str] = Field(default=None)


class HOADocument(TimestampMixin, table=True):
    """A document belonging to an HOA (CC&Rs, bylaws, etc.).

    Stores either the file bytes directly in the database (``content``) or an
    external link (``external_url``). ``content`` is deliberately excluded from
    list responses to keep them light.
    """

    __tablename__ = "hoa_document"

    hoa_id: uuid.UUID = Field(foreign_key="hoa.id", index=True)

    name: str = Field(max_length=255)
    doc_type: str = Field(
        default="other",
        max_length=40,
        description="ccr | bylaws | rules | budget | meeting_minutes | insurance | other",
    )

    # File storage (when uploaded)
    filename: Optional[str] = Field(default=None, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=120)
    file_size: Optional[int] = Field(default=None)
    content: Optional[bytes] = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )

    # Alternative: link to an externally-hosted document
    external_url: Optional[str] = Field(default=None, max_length=600)

    uploaded_at: datetime = Field(default_factory=lambda: datetime.now())
