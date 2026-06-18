import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import EmailApprovalStatus


class EmailApproval(TimestampMixin, table=True):
    """A draft email that must be approved by the landlord before sending.

    Acts as the human approval gate in the lease-break workflow: services
    generate a draft, the landlord reviews it in the UI and approves, then the
    email is dispatched.
    """

    __tablename__ = "email_approval"

    lease_break_request_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="lease_break_request.id", index=True
    )

    status: str = Field(default=EmailApprovalStatus.draft.value, max_length=20, index=True)

    to_emails: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    cc_emails: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    subject: str = Field(max_length=300)
    body_html: str = Field()

    # Names of files attached when sent (e.g. generated PDFs)
    attachments: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    approved_by: Optional[str] = Field(default=None, max_length=200)
    approved_at: Optional[datetime] = Field(default=None)
    sent_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
