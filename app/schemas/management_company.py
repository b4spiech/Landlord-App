from typing import Optional

from pydantic import BaseModel

from app.schemas.common import TimestampedRead


class ManagementCompanyBase(BaseModel):
    name: str
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None


class ManagementCompanyCreate(ManagementCompanyBase):
    pass


class ManagementCompanyUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None


class ManagementCompanyRead(ManagementCompanyBase, TimestampedRead):
    pass
