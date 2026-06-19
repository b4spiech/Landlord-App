from typing import Optional

from sqlmodel import Field

from app.models.base import TimestampMixin


class Tenant(TimestampMixin, table=True):
    """A person who signs a lease."""

    __tablename__ = "tenant"

    first_name: str = Field(max_length=100)
    last_name: str = Field(index=True, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255, index=True)
    phone: Optional[str] = Field(default=None, max_length=30)

    date_of_birth: Optional[str] = Field(default=None, max_length=10, description="YYYY-MM-DD")

    # Optional separate mailing address (e.g. forwarding address for move-out)
    address_line1: Optional[str] = Field(default=None, max_length=200)
    address_line2: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=2)
    postal_code: Optional[str] = Field(default=None, max_length=20)

    emergency_contact_name: Optional[str] = Field(default=None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=30)
    emergency_contact_relationship: Optional[str] = Field(default=None, max_length=100)

    # Identification (sensitive — not populated by document parsing)
    drivers_license: Optional[str] = Field(default=None, max_length=50)
    ssn_or_tax_id: Optional[str] = Field(default=None, max_length=50)

    # Employment
    employer_name: Optional[str] = Field(default=None, max_length=200)
    employer_phone: Optional[str] = Field(default=None, max_length=30)
    job_title: Optional[str] = Field(default=None, max_length=150)
    annual_income: Optional[float] = Field(default=None)

    # Reference
    reference_name: Optional[str] = Field(default=None, max_length=200)
    reference_phone: Optional[str] = Field(default=None, max_length=30)
    reference_relationship: Optional[str] = Field(default=None, max_length=100)

    notes: Optional[str] = Field(default=None)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
