from typing import Optional

from pydantic import BaseModel

from app.schemas.common import TimestampedRead


class TenantBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    drivers_license: Optional[str] = None
    employer_name: Optional[str] = None
    employer_phone: Optional[str] = None
    job_title: Optional[str] = None
    annual_income: Optional[float] = None
    reference_name: Optional[str] = None
    reference_phone: Optional[str] = None
    reference_relationship: Optional[str] = None
    notes: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    notes: Optional[str] = None


class TenantRead(TenantBase, TimestampedRead):
    pass
