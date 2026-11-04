"""Door-code inventory: parsing pasted codes, and reserving/releasing/issuing
codes for tours. Each step is idempotent so retries (or a restarted scheduler)
never hand out two codes or reuse an issued one."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, nulls_last
from sqlmodel import Session, select

from app.models import AccessCode, Tenant, TourRequest
from app.models.enums import AccessCodeKind, AccessCodeStatus

# Keypad-friendly: digits, letters, * and #, 3-20 characters.
CODE_RE = re.compile(r"^[0-9A-Za-z*#]{3,20}$")
LOW_STOCK = 3  # warn when a property has fewer available codes than this

A, R, I = AccessCodeStatus.available.value, AccessCodeStatus.reserved.value, AccessCodeStatus.issued.value
ONE_TIME = AccessCodeKind.one_time.value


def parse_codes(raw: str) -> tuple[list[str], list[str]]:
    """Split pasted text (newlines, commas, spaces, tabs) into (valid unique codes, invalid tokens)."""
    valid, invalid, seen = [], [], set()
    for token in re.split(r"[\s,;]+", raw or ""):
        token = token.strip()
        if not token:
            continue
        if not CODE_RE.match(token):
            invalid.append(token)
        elif token not in seen:
            seen.add(token)
            valid.append(token)
    return valid, invalid


def counts(session: Session, property_id: uuid.UUID) -> dict[str, int]:
    rows = session.exec(
        select(AccessCode.status, func.count())
        .where(AccessCode.property_id == property_id, AccessCode.kind == ONE_TIME)
        .group_by(AccessCode.status)
    ).all()
    out = {A: 0, R: 0, I: 0}
    out.update({status: n for status, n in rows})
    return out


def code_for_tour(session: Session, req: TourRequest) -> AccessCode | None:
    return session.exec(
        select(AccessCode).where(AccessCode.tour_request_id == req.id, AccessCode.status.in_((R, I)))
    ).first()


def reserve_for_tour(session: Session, req: TourRequest) -> AccessCode | None:
    """Hold an available code for this tour (or return the one already held).

    Picks the code expiring soonest that is still valid on the tour's local
    date, so codes get used before they lapse. Returns None if none are left.
    Caller commits.
    """
    existing = code_for_tour(session, req)
    if existing:
        return existing
    tour_day = req.tour_start.astimezone(ZoneInfo(req.time_zone)).date()
    code = session.exec(
        select(AccessCode)
        .where(
            AccessCode.property_id == req.property_id,
            AccessCode.kind == ONE_TIME,  # never hand out tenant or landlord codes
            AccessCode.status == A,
            (AccessCode.expires_on.is_(None)) | (AccessCode.expires_on >= tour_day),
        )
        .order_by(nulls_last(AccessCode.expires_on.asc()), AccessCode.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    ).first()
    if code is None:
        return None
    code.status = R
    code.tour_request_id = req.id
    code.reserved_at = datetime.now(timezone.utc)
    session.add(code)
    return code


def release_for_tour(session: Session, req: TourRequest) -> None:
    """Return a reserved (never sent) code to the pool, e.g. on decline/cancel. Caller commits."""
    for code in session.exec(
        select(AccessCode).where(AccessCode.tour_request_id == req.id, AccessCode.status == R)
    ).all():
        code.status = A
        code.tour_request_id = None
        code.reserved_at = None
        session.add(code)


def issue_for_tour(session: Session, req: TourRequest) -> AccessCode | None:
    """Mark this tour's code as issued (reserving one first if needed).

    Issued codes are never returned to the pool. Returns None if the property
    has no usable code. Caller commits.
    """
    code = code_for_tour(session, req) or reserve_for_tour(session, req)
    if code is None:
        return None
    if code.status != I:
        code.status = I
        code.issued_at = datetime.now(timezone.utc)
        session.add(code)
    return code


# --- Tenant codes ---------------------------------------------------------------


def assign_to_tenant(session: Session, code: AccessCode, tenant: Tenant) -> None:
    """Give a pre-programmed tenant code to a tenant. Caller commits."""
    code.status = AccessCodeStatus.assigned.value
    code.tenant_id = tenant.id
    code.assigned_at = datetime.now(timezone.utc)
    session.add(code)


def unassign(session: Session, code: AccessCode) -> None:
    """Put a tenant code back in the property's pool. Caller commits."""
    code.status = A
    code.tenant_id = None
    code.assigned_at = None
    session.add(code)
