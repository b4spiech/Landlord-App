"""Landlord management of each property's one-time door codes."""

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import case
from sqlmodel import Session, select

from app.database import get_session
from app.models import AccessCode, Property, TourRequest
from app.models.enums import AccessCodeStatus
from app.routers.crud import get_or_404
from app.services.access_codes import LOW_STOCK, counts, parse_codes

router = APIRouter(tags=["access-codes"])

ACTIVE = (AccessCodeStatus.available.value, AccessCodeStatus.reserved.value)


class AccessCodeRead(BaseModel):
    id: uuid.UUID
    created_at: datetime
    code: str
    status: str
    note: Optional[str] = None
    expires_on: Optional[date] = None
    tour_request_id: Optional[uuid.UUID] = None
    tour_visitor: Optional[str] = None
    reserved_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None


class AccessCodeList(BaseModel):
    available: int
    reserved: int
    issued: int
    low_stock: bool
    low_stock_threshold: int
    codes: list[AccessCodeRead]


class AccessCodeAdd(BaseModel):
    codes: str = Field(..., description="Pasted codes separated by new lines, commas or spaces")
    expires_on: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=200)


class AccessCodeAddResult(BaseModel):
    added: int
    duplicates: list[str]
    invalid: list[str]


@router.get("/properties/{property_id}/access-codes", response_model=AccessCodeList)
def list_codes(property_id: uuid.UUID, history: bool = False, session: Session = Depends(get_session)):
    """Active codes (available + reserved); add ?history=true to include issued codes."""
    get_or_404(session, Property, property_id, "Property")
    stmt = select(AccessCode, TourRequest).outerjoin(TourRequest, TourRequest.id == AccessCode.tour_request_id)
    stmt = stmt.where(AccessCode.property_id == property_id)
    if not history:
        stmt = stmt.where(AccessCode.status.in_(ACTIVE))
    order = case({"reserved": 0, "available": 1, "issued": 2}, value=AccessCode.status)
    stmt = stmt.order_by(order, AccessCode.issued_at.desc(), AccessCode.created_at)
    codes = [
        AccessCodeRead(
            **c.model_dump(include=set(AccessCodeRead.model_fields) - {"tour_visitor"}),
            tour_visitor=f"{t.first_name} {t.last_name}" if t else None,
        )
        for c, t in session.exec(stmt).all()
    ]
    n = counts(session, property_id)
    return AccessCodeList(
        available=n["available"], reserved=n["reserved"], issued=n["issued"],
        low_stock=n["available"] < LOW_STOCK, low_stock_threshold=LOW_STOCK, codes=codes,
    )


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
    active = set(session.exec(
        select(AccessCode.code).where(AccessCode.property_id == property_id, AccessCode.status.in_(ACTIVE))
    ).all())
    duplicates = [c for c in valid if c in active]
    new = [c for c in valid if c not in active]
    note = (payload.note or "").strip() or None
    for code in new:
        session.add(AccessCode(property_id=property_id, code=code, expires_on=payload.expires_on, note=note))
    session.commit()
    return AccessCodeAddResult(added=len(new), duplicates=duplicates, invalid=invalid)


@router.delete("/access-codes/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_code(code_id: uuid.UUID, session: Session = Depends(get_session)):
    """Remove an unused code (e.g. typo, or deleted from the lock). Reserved and issued codes are kept."""
    code = get_or_404(session, AccessCode, code_id, "Access code")
    if code.status != AccessCodeStatus.available.value:
        raise HTTPException(
            status_code=409,
            detail="Only available codes can be removed. This one is held for or was sent to a visitor.",
        )
    session.delete(code)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
