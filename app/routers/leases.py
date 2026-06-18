import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Lease, LeaseTenant, Payment, Tenant
from app.routers.crud import apply_updates, get_or_404
from app.schemas.lease import (
    LeaseCreate,
    LeaseDetailRead,
    LeaseRead,
    LeaseUpdate,
)

router = APIRouter(prefix="/leases", tags=["leases"])


def _build_detail(session: Session, lease: Lease) -> LeaseDetailRead:
    tenant_ids = session.exec(
        select(LeaseTenant.tenant_id).where(LeaseTenant.lease_id == lease.id)
    ).all()
    tenants = []
    if tenant_ids:
        tenants = session.exec(select(Tenant).where(Tenant.id.in_(tenant_ids))).all()
    payments = session.exec(select(Payment).where(Payment.lease_id == lease.id)).all()

    detail = LeaseDetailRead.model_validate(lease)
    detail.tenants = [t for t in tenants]
    detail.payments = [p for p in payments]
    return detail


@router.post("", response_model=LeaseDetailRead, status_code=status.HTTP_201_CREATED)
def create_lease(payload: LeaseCreate, session: Session = Depends(get_session)):
    data = payload.model_dump(exclude={"lease_tenants"})
    lease = Lease(**data)
    session.add(lease)
    session.flush()  # assign lease.id

    for lt in payload.lease_tenants:
        session.add(LeaseTenant(lease_id=lease.id, **lt.model_dump()))

    session.commit()
    session.refresh(lease)
    return _build_detail(session, lease)


@router.get("", response_model=list[LeaseRead])
def list_leases(
    property_id: Optional[uuid.UUID] = None,
    unit_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    statement = select(Lease)
    if property_id is not None:
        statement = statement.where(Lease.property_id == property_id)
    if unit_id is not None:
        statement = statement.where(Lease.unit_id == unit_id)
    if status_filter is not None:
        statement = statement.where(Lease.status == status_filter)
    return session.exec(statement.offset(skip).limit(limit)).all()


@router.get("/{lease_id}", response_model=LeaseDetailRead)
def get_lease(lease_id: uuid.UUID, session: Session = Depends(get_session)):
    lease = get_or_404(session, Lease, lease_id, "Lease")
    return _build_detail(session, lease)


@router.patch("/{lease_id}", response_model=LeaseDetailRead)
def update_lease(
    lease_id: uuid.UUID,
    payload: LeaseUpdate,
    session: Session = Depends(get_session),
):
    lease = get_or_404(session, Lease, lease_id, "Lease")
    apply_updates(lease, payload.model_dump(exclude_unset=True))
    session.add(lease)
    session.commit()
    session.refresh(lease)
    return _build_detail(session, lease)
