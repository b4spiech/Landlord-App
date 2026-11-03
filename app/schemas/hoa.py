import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import TimestampedRead


class HOABase(BaseModel):
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    management_company_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    dues_amount: Optional[float] = None
    dues_frequency: Optional[str] = None
    notes: Optional[str] = None


class HOACreate(HOABase):
    pass


class HOAUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    management_company_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    dues_amount: Optional[float] = None
    dues_frequency: Optional[str] = None
    notes: Optional[str] = None


class HOARead(HOABase, TimestampedRead):
    pass


# Document metadata only (never includes the file bytes).
class HOADocumentRead(TimestampedRead):
    hoa_id: uuid.UUID
    name: str
    doc_type: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    external_url: Optional[str] = None
    uploaded_at: datetime
    has_file: bool = False
