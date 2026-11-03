import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Tenant
from app.routers.crud import apply_updates, get_or_404
from app.schemas.tenant import TenantCreate, TenantRead, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate, session: Session = Depends(get_session)):
    obj = Tenant(**payload.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.get("", response_model=list[TenantRead])
def list_tenants(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    return session.exec(select(Tenant).offset(skip).limit(limit)).all()


@router.get("/{tenant_id}", response_model=TenantRead)
def get_tenant(tenant_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, Tenant, tenant_id, "Tenant")


@router.patch("/{tenant_id}", response_model=TenantRead)
def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    session: Session = Depends(get_session),
):
    obj = get_or_404(session, Tenant, tenant_id, "Tenant")
    apply_updates(obj, payload.model_dump(exclude_unset=True))
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj
