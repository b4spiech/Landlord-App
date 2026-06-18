import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field
from sqlmodel.sql.sqltypes import GUID

from app.models.base import TimestampMixin
from app.models.enums import (
    DocumentStatus,
    DocumentType,
    LeaseBreakOptionType,
    LeaseBreakStatus,
)


class LeaseBreakRequest(TimestampMixin, table=True):
    """A tenant's request to break a lease early, with full workflow state."""

    __tablename__ = "lease_break_request"

    lease_id: uuid.UUID = Field(foreign_key="lease.id", index=True)

    status: str = Field(default=LeaseBreakStatus.initiated.value, max_length=40, index=True)

    requested_date: date = Field(description="Date the tenant requested to break")
    desired_move_out_date: date = Field()
    reason: Optional[str] = Field(default=None)

    # Set when an option is chosen. ``use_alter`` breaks the circular FK
    # dependency with ``lease_break_option`` (which references this table).
    selected_option_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            GUID(),
            ForeignKey(
                "lease_break_option.id",
                use_alter=True,
                name="fk_lease_break_request_selected_option",
            ),
            nullable=True,
        ),
    )

    # Snapshot of the figures used to compute options (rent, months remaining, etc.)
    calculation_context: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )

    docusign_envelope_id: Optional[str] = Field(default=None, max_length=100)
    completed_at: Optional[datetime] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class LeaseBreakOption(TimestampMixin, table=True):
    """A presented option for resolving a lease break (e.g. buyout, re-let)."""

    __tablename__ = "lease_break_option"

    lease_break_request_id: uuid.UUID = Field(
        foreign_key="lease_break_request.id", index=True
    )

    option_type: str = Field(max_length=40)
    label: str = Field(max_length=200)
    description: Optional[str] = Field(default=None)

    total_cost_to_tenant: float = Field(default=0.0)
    months_charged: Optional[float] = Field(default=None)

    # Breakdown of charges/credits (deposit forfeit, buyout fee, reletting fee...)
    line_items: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    # Result of jurisdiction validation for this option
    is_compliant: bool = Field(default=True)
    compliance_note: Optional[str] = Field(default=None)

    is_selected: bool = Field(default=False)


class LeaseBreakDocument(TimestampMixin, table=True):
    """A generated document tied to a lease break (termination agreement, etc.)."""

    __tablename__ = "lease_break_document"

    lease_break_request_id: uuid.UUID = Field(
        foreign_key="lease_break_request.id", index=True
    )
    template_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="lease_template.id"
    )

    document_type: str = Field(max_length=40)
    status: str = Field(default=DocumentStatus.generated.value, max_length=30)

    file_name: str = Field(max_length=255)
    file_path: Optional[str] = Field(default=None, max_length=500)
    rendered_html: Optional[str] = Field(default=None)

    docusign_envelope_id: Optional[str] = Field(default=None, max_length=100)
    signed_at: Optional[datetime] = Field(default=None)
