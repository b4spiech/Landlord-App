"""One-time email codes and visitor sessions for the public tour form."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, func, select

from app.models.visitor_auth import EmailVerification, VisitorSession

CODE_TTL = timedelta(minutes=10)
CODE_MAX_ATTEMPTS = 5
CODES_PER_EMAIL_WINDOW = (3, timedelta(minutes=10))  # max codes per email per window
SESSION_TTL = timedelta(days=30)
COOKIE_NAME = "apex_tour_session"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class VerifyError(Exception):
    pass


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_email(raw: str) -> str | None:
    email = (raw or "").strip().lower()
    return email if EMAIL_RE.match(email) and len(email) <= 254 else None


def too_many_codes(session: Session, email: str, now: datetime) -> bool:
    limit, window = CODES_PER_EMAIL_WINDOW
    recent = session.exec(
        select(func.count()).select_from(EmailVerification).where(
            EmailVerification.email == email, EmailVerification.created_at >= now - window
        )
    ).one()
    return recent >= limit


def create_code(session: Session, email: str, ip: str | None, now: datetime | None = None) -> str:
    """Create a fresh code (older unused codes for this email stop working). Caller commits."""
    now = now or datetime.now(timezone.utc)
    for old in session.exec(
        select(EmailVerification).where(EmailVerification.email == email, EmailVerification.consumed_at.is_(None))
    ).all():
        old.consumed_at = now
        session.add(old)
    code = f"{secrets.randbelow(1_000_000):06d}"
    session.add(EmailVerification(email=email, code_hash=_hash(f"{email}:{code}"),
                                  expires_at=now + CODE_TTL, ip=(ip or "")[:64] or None))
    return code


def verify_code(session: Session, email: str, code: str, now: datetime | None = None) -> None:
    """Raise VerifyError unless `code` is the current, unexpired code for `email`. Caller commits."""
    now = now or datetime.now(timezone.utc)
    row = session.exec(
        select(EmailVerification)
        .where(EmailVerification.email == email, EmailVerification.consumed_at.is_(None))
        .order_by(EmailVerification.created_at.desc())
        .with_for_update()
    ).first()
    if row is None or row.expires_at <= now:
        raise VerifyError("That code has expired. Please request a new one.")
    if row.attempts >= CODE_MAX_ATTEMPTS:
        raise VerifyError("Too many wrong tries. Please request a new code.")
    row.attempts += 1
    session.add(row)
    if not hmac.compare_digest(row.code_hash, _hash(f"{email}:{(code or '').strip()}")):
        session.commit()  # keep the attempt count even though we raise
        left = CODE_MAX_ATTEMPTS - row.attempts
        raise VerifyError(f"That code isn't right. {left} tr{'y' if left == 1 else 'ies'} left."
                          if left else "Too many wrong tries. Please request a new code.")
    row.consumed_at = now


def create_session(session: Session, email: str, now: datetime | None = None) -> str:
    """Return a new session token (store it only in the visitor's cookie). Caller commits."""
    now = now or datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    session.add(VisitorSession(token_hash=_hash(token), email=email, expires_at=now + SESSION_TTL))
    return token


def session_email(session: Session, token: str | None, now: datetime | None = None) -> str | None:
    if not token:
        return None
    now = now or datetime.now(timezone.utc)
    row = session.exec(select(VisitorSession).where(VisitorSession.token_hash == _hash(token))).first()
    return row.email if row and row.expires_at > now else None


def end_session(session: Session, token: str | None) -> None:
    if token:
        row = session.exec(select(VisitorSession).where(VisitorSession.token_hash == _hash(token))).first()
        if row:
            session.delete(row)
