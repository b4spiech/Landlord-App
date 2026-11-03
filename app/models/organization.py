from typing import Optional

from sqlmodel import Field

from app.models.base import TimestampMixin


class Owner(TimestampMixin, table=True):
    """A property owner (person or entity that holds title)."""

    __tablename__ = "owner"

    name: str = Field(index=True, max_length=200)
    email: Optional[str] = Field(default=None, max_length=255, index=True)
    phone: Optional[str] = Field(default=None, max_length=30)

    # Mailing address
    address_line1: Optional[str] = Field(default=None, max_length=200)
    address_line2: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=2)
    postal_code: Optional[str] = Field(default=None, max_length=20)

    is_entity: bool = Field(default=False, description="True if an LLC/corp rather than a person")
    tax_id: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None)


class ManagementCompany(TimestampMixin, table=True):
    """The entity managing properties (e.g. APEX Element Group LLC)."""

    __tablename__ = "management_company"

    name: str = Field(index=True, max_length=200)
    legal_name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)
    website: Optional[str] = Field(default=None, max_length=255)

    address_line1: Optional[str] = Field(default=None, max_length=200)
    address_line2: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=2)
    postal_code: Optional[str] = Field(default=None, max_length=20)

    tax_id: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None)
