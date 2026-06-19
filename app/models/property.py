import uuid
from typing import Optional

from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import PropertyType, UnitStatus


class Property(TimestampMixin, table=True):
    __tablename__ = "property"

    name: str = Field(index=True, max_length=200)
    property_type: str = Field(default=PropertyType.condo.value, max_length=40)

    address_line1: str = Field(max_length=200)
    address_line2: Optional[str] = Field(default=None, max_length=200)
    city: str = Field(max_length=100)
    state: str = Field(max_length=2, index=True)
    postal_code: str = Field(max_length=20)

    # Relationships (foreign keys)
    owner_id: uuid.UUID = Field(foreign_key="owner.id", index=True)
    management_company_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="management_company.id", index=True
    )
    jurisdiction_id: uuid.UUID = Field(foreign_key="jurisdiction.id", index=True)
    hoa_id: Optional[uuid.UUID] = Field(default=None, foreign_key="hoa.id", index=True)

    year_built: Optional[int] = Field(default=None)
    bedrooms: Optional[int] = Field(default=None)
    bathrooms: Optional[float] = Field(default=None)
    square_feet: Optional[int] = Field(default=None)
    hoa_name: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None)


class Unit(TimestampMixin, table=True):
    """A leasable space within a property."""

    __tablename__ = "unit"

    property_id: uuid.UUID = Field(foreign_key="property.id", index=True)
    unit_number: str = Field(max_length=50, description="e.g. '60'")
    status: str = Field(default=UnitStatus.vacant.value, max_length=30)

    bedrooms: Optional[int] = Field(default=None)
    bathrooms: Optional[float] = Field(default=None)
    square_feet: Optional[int] = Field(default=None)
    market_rent: Optional[float] = Field(default=None)
    notes: Optional[str] = Field(default=None)
