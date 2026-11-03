from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampMixin


class Jurisdiction(TimestampMixin, table=True):
    """A state (or local) legal jurisdiction with rental rules.

    `early_termination_rules` holds a JSON document of state-law constraints
    used by the lease-break workflow (e.g. max buyout multiple, required
    notice days, mitigation duty).
    """

    __tablename__ = "jurisdiction"

    state_code: str = Field(index=True, unique=True, max_length=2, description="e.g. AZ")
    state_name: str = Field(max_length=100)
    name: str = Field(max_length=150, description="Human label, e.g. 'Arizona'")

    # Notice / termination defaults
    notice_days_month_to_month: int = Field(default=30)
    notice_days_lease_termination: int = Field(default=30)
    security_deposit_max_months: Optional[float] = Field(default=None)
    security_deposit_return_days: Optional[int] = Field(default=None)

    # Duty-to-mitigate: landlord must make reasonable efforts to re-rent.
    landlord_must_mitigate: bool = Field(default=True)

    early_termination_rules: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )

    statute_reference: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None)
