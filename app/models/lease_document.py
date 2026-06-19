import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column, LargeBinary
from sqlmodel import Field

from app.models.base import TimestampMixin


class LeaseDocument(TimestampMixin, table=True):
    """An uploaded lease document (original PDF/image) plus extraction metadata.

    The file bytes are stored in ``content`` (Postgres) rather than on disk,
    since the deploy filesystem is ephemeral. ``extracted_data`` keeps the full
    parsed JSON for the audit trail.
    """

    __tablename__ = "lease_document"

    lease_id: Optional[uuid.UUID] = Field(default=None, foreign_key="lease.id", index=True)
    document_type: str = Field(
        default="original_lease",
        max_length=40,
        description="original_lease | amended | addendum | move_out_statement",
    )

    # File storage (in the database)
    file_name: str = Field(max_length=255)
    file_type: Optional[str] = Field(default=None, max_length=120)
    file_size: Optional[int] = Field(default=None)
    content: Optional[bytes] = Field(default=None, sa_column=Column(LargeBinary, nullable=True))

    # Extraction metadata
    extracted_data: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    extraction_confidence: Optional[str] = Field(
        default=None, max_length=20, description="high | medium | low"
    )
    extraction_notes: Optional[str] = Field(default=None)

    uploaded_at: datetime = Field(default_factory=lambda: datetime.now())
