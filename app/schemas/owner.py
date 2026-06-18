from typing import Optional

from pydantic import BaseModel

from app.schemas.common import TimestampedRead


class OwnerBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    is_entity: bool = False
    tax_id: Optional[str] = None
    notes: Optional[str] = None


class OwnerCreate(OwnerBase):
    pass


class OwnerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    is_entity: Optional[bool] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None


class OwnerRead(OwnerBase, TimestampedRead):
    pass
