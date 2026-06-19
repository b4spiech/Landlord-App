import uuid
from typing import Optional

from pydantic import BaseModel

from app.models.enums import PropertyType
from app.schemas.common import TimestampedRead


class PropertyBase(BaseModel):
    name: str
    property_type: PropertyType = PropertyType.condo
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    owner_id: uuid.UUID
    management_company_id: Optional[uuid.UUID] = None
    jurisdiction_id: uuid.UUID
    hoa_id: Optional[uuid.UUID] = None
    year_built: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    hoa_name: Optional[str] = None
    notes: Optional[str] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    property_type: Optional[PropertyType] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    owner_id: Optional[uuid.UUID] = None
    management_company_id: Optional[uuid.UUID] = None
    jurisdiction_id: Optional[uuid.UUID] = None
    hoa_id: Optional[uuid.UUID] = None
    year_built: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    hoa_name: Optional[str] = None
    notes: Optional[str] = None


class PropertyRead(PropertyBase, TimestampedRead):
    pass
