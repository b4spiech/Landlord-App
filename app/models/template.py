import uuid
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import TemplateType


class LeaseTemplate(TimestampMixin, table=True):
    """A versioned Jinja2 document template.

    The combination of (template_type, version) is unique. `body` holds the
    Jinja2 source; `context_schema` documents the variables the template
    expects so the UI/services can supply a correct render context.
    """

    __tablename__ = "lease_template"

    name: str = Field(index=True, max_length=200)
    template_type: str = Field(index=True, max_length=50)
    version: int = Field(default=1)
    is_active: bool = Field(default=True)

    subject: Optional[str] = Field(
        default=None, max_length=300, description="For email templates"
    )
    body: str = Field(description="Jinja2 source (HTML or plaintext)")
    jurisdiction_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="jurisdiction.id", index=True
    )

    context_schema: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    notes: Optional[str] = Field(default=None)
