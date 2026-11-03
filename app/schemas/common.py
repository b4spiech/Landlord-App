import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for read schemas that hydrate from SQLAlchemy/SQLModel objects."""

    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
