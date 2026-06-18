import uuid
from typing import Optional

from pydantic import BaseModel

from app.models.enums import UnitStatus
from app.schemas.common import TimestampedRead


class UnitBase(BaseModel):
    property_id: uuid.UUID
    unit_number: str
    status: UnitStatus = UnitStatus.vacant
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    market_rent: Optional[float] = None
    notes: Optional[str] = None


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    property_id: Optional[uuid.UUID] = None
    unit_number: Optional[str] = None
    status: Optional[UnitStatus] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    market_rent: Optional[float] = None
    notes: Optional[str] = None


class UnitRead(UnitBase, TimestampedRead):
    pass
