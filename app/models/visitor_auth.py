"""Email sign-in for public visitors (required to request a tour).

A visitor proves they own an email address with a one-time 6-digit code; we
then give them a session cookie. Only hashes of codes and session tokens are
stored, so a database leak can't be used to sign in.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field

from app.models.base import TimestampMixin


class EmailVerification(TimestampMixin, table=True):
    __tablename__ = "email_verification"

    email: str = Field(max_length=254, index=True)
    code_hash: str = Field(max_length=64)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    attempts: int = Field(default=0)
    consumed_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    ip: Optional[str] = Field(default=None, max_length=64)


class VisitorSession(TimestampMixin, table=True):
    __tablename__ = "visitor_session"

    token_hash: str = Field(max_length=64, unique=True, index=True)
    email: str = Field(max_length=254, index=True)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
