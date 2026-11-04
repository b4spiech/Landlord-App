"""Landlord management of each property's door codes.

Three kinds live in one table:
* one_time — single-use tour codes: available -> reserved -> issued (never reused)
* tenant   — pre-programmed codes: available (in the pool) <-> assigned to a tenant
* landlord — the landlord's own codes: active
"""

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import case
from sqlmodel import Session, select

from app.database import get_session
from app.models import AccessCode, Lease, LeaseTenant, Property, Tenant, TourRequest
from app.models.enums import LIVE_CODE_STATUSES, AccessCodeKind, AccessCodeStatus
from app.routers.crud import get_or_404
from app.services.access_codes import LOW_STOCK, assign_to_tenant, counts, parse_codes, unassign

router = APIRouter(tags=["access-codes"])

ONE_TIME_ACTIVE = (AccessCodeStatus.available.value, AccessCodeStatus.reserved.value)
CURRENT_LEASE_STATUSES = ("active", "draft", "pending_signature")


class AccessCodeRead(BaseModel):
    id: uuid.UUID
    created_at: datetime
    code: str
    kind: str
    status: str
    note: Optional[str] = None
    expires_on: Optional[date] = None
    tour_request_id: Optional[uuid.UUID] = None
    tour_visitor: Optional[str] = None
    reserved_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None
    tenant_id: Optional[uuid.UUID] = None
    tenant_name: Optional[str] = None
    assigned_at: Optional[datetime] = None


class AccessCodeList(BaseModel):
    """One-time tour codes (with stock counts)."""

    available: int
    reserved: int
    issued: int
    low_stock: bool
    low_stock_threshold: int
    codes: list[AccessCodeRead]


class TenantOption(BaseModel):
    id: uuid.UUID
    name: str
    on_current_lease: bool


class ManagedCodes(BaseModel):
    """Tenant and landlord codes, plus who tenant codes can be assigned to."""

    tenant_codes: list[AccessCodeRead]
    landlord_codes: list[AccessCodeRead]
    tenants: list[TenantOption]


class AccessCodeAdd(BaseModel):
    codes: str = Field(..., description="Pasted codes separated by new lines, commas or spaces")
    kind: AccessCodeKind = AccessCodeKind.one_time
    expires_on: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=200)


class AccessCodeAddResult(BaseModel):
    added: int
    duplicates: list[str]
    invalid: list[str]


class AssignIn(BaseModel):
    tenant_id: uuid.UUID


def _read(code: AccessCode, tour: Optional[TourRequest] = None, tenant: Optional[Tenant] = None) -> AccessCodeRead:
    return AccessCodeRead(
        **code.model_dump(include=set(AccessCodeRead.model_fields) - {"tour_visitor", "tenant_name"}),
        tour_visitor=f"{tour.first_name} {tour.last_name}" if tour else None,
        tenant_name=f"{tenant.first_name} {tenant.last_name}" if tenant else None,
    )


@router.get("/properties/{property_id}/access-codes", response_model=AccessCodeList)
def list_codes(property_id: uuid.UUID, history: bool = False, session: Session = Depends(get_session)):
    """One-time tour codes: active ones (available + reserved); ?history=true adds sent codes."""
    get_or_404(session, Property, property_id, "Property")
    stmt = (
        select(AccessCode, TourRequest)
        .outerjoin(TourRequest, TourRequest.id == AccessCode.tour_request_id)
        .where(AccessCode.property_id == property_id, AccessCode.kind == AccessCodeKind.one_time.value)
    )
    if not history:
        stmt = stmt.where(AccessCode.status.in_(ONE_TIME_ACTIVE))
    order = case({"reserved": 0, "available": 1, "issued": 2}, value=AccessCode.status)
    stmt = stmt.order_by(order, AccessCode.issued_at.desc(), AccessCode.created_at)
    codes = [_read(c, tour=t) for c, t in session.exec(stmt).all()]
    n = counts(session, property_id)
    return AccessCodeList(
        available=n["available"], reserved=n["reserved"], issued=n["issued"],
        low_stock=n["available"] < LOW_STOCK, low_stock_threshold=LOW_STOCK, codes=codes,
    )


@router.get("/properties/{property_id}/access-codes/managed", response_model=ManagedCodes)
def managed_codes(property_id: uuid.UUID, session: Session = Depends(get_session)):
    """Tenant and landlord codes for the property, and the tenants to offer when assigning."""
    get_or_404(session, Property, property_id, "Property")
    rows = session.exec(
        select(AccessCode, Tenant)
        .outerjoin(Tenant, Tenant.id == AccessCode.tenant_id)
        .where(
            AccessCode.property_id == property_id,
            AccessCode.kind.in_((AccessCodeKind.tenant.value, AccessCodeKind.landlord.value)),
        )
        .order_by(AccessCode.created_at)
    ).all()
    tenant_codes = [_read(c, tenant=t) for c, t in rows if c.kind == AccessCodeKind.tenant.value]
    landlord_codes = [_read(c) for c, _ in rows if c.kind == AccessCodeKind.landlord.value]

    current = set(session.exec(
        select(LeaseTenant.tenant_id)
        .join(Lease, Lease.id == LeaseTenant.lease_id)
        .where(Lease.property_id == property_id, Lease.status.in_(CURRENT_LEASE_STATUSES))
    ).all())
    tenants = sorted(
        (TenantOption(id=t.id, name=f"{t.first_name} {t.last_name}", on_current_lease=t.id in current)
         for t in session.exec(select(Tenant)).all()),
        key=lambda t: (not t.on_current_lease, t.name.lower()),
    )
    return ManagedCodes(tenant_codes=tenant_codes, landlord_codes=landlord_codes, tenants=tenants)


@router.post("/properties/{property_id}/access-codes", response_model=AccessCodeAddResult,
             status_code=status.HTTP_201_CREATED)
def add_codes(property_id: uuid.UUID, payload: AccessCodeAdd, session: Session = Depends(get_session)):
    get_or_404(session, Property, property_id, "Property")
    valid, invalid = parse_codes(payload.codes)
    if not valid:
        raise HTTPException(
            status_code=422,
            detail="No valid codes found. Codes are 3–20 characters: digits, letters, * or #.",
        )
    # A code can't be live twice on the same property, whatever its kind.
    live = set(session.exec(
        select(AccessCode.code).where(AccessCode.property_id == property_id, AccessCode.status.in_(LIVE_CODE_STATUSES))
    ).all())
    duplicates = [c for c in valid if c in live]
    new = [c for c in valid if c not in live]
    note = (payload.note or "").strip() or None
    status_for_kind = (AccessCodeStatus.active if payload.kind == AccessCodeKind.landlord
                       else AccessCodeStatus.available).value
    for code in new:
        session.add(AccessCode(property_id=property_id, code=code, kind=payload.kind.value, status=status_for_kind,
                               expires_on=payload.expires_on, note=note))
    session.commit()
    return AccessCodeAddResult(added=len(new), duplicates=duplicates, invalid=invalid)


def _tenant_code(session: Session, code_id: uuid.UUID) -> AccessCode:
    code = get_or_404(session, AccessCode, code_id, "Access code")
    if code.kind != AccessCodeKind.tenant.value:
        raise HTTPException(status_code=409, detail="Only tenant codes can be assigned to tenants.")
    return code


@router.post("/access-codes/{code_id}/assign", response_model=AccessCodeRead)
def assign(code_id: uuid.UUID, payload: AssignIn, session: Session = Depends(get_session)):
    code = _tenant_code(session, code_id)
    tenant = get_or_404(session, Tenant, payload.tenant_id, "Tenant")
    assign_to_tenant(session, code, tenant)
    session.commit()
    session.refresh(code)
    return _read(code, tenant=tenant)


@router.post("/access-codes/{code_id}/unassign", response_model=AccessCodeRead)
def unassign_code(code_id: uuid.UUID, session: Session = Depends(get_session)):
    code = _tenant_code(session, code_id)
    unassign(session, code)
    session.commit()
    session.refresh(code)
    return _read(code)


@router.delete("/access-codes/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_code(code_id: uuid.UUID, session: Session = Depends(get_session)):
    """Remove a code that's no longer valid on the lock.

    Tour codes: only unused ones (held/sent codes are kept as a record).
    Tenant codes: unassign first. Landlord codes: always.
    """
    code = get_or_404(session, AccessCode, code_id, "Access code")
    if code.kind == AccessCodeKind.one_time.value and code.status != AccessCodeStatus.available.value:
        raise HTTPException(
            status_code=409,
            detail="Only available codes can be removed. This one is held for or was sent to a visitor.",
        )
    if code.kind == AccessCodeKind.tenant.value and code.status == AccessCodeStatus.assigned.value:
        raise HTTPException(status_code=409, detail="Unassign this code from the tenant before removing it.")
    session.delete(code)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
