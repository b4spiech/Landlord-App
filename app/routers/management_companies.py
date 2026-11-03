import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import ManagementCompany
from app.routers.crud import apply_updates, get_or_404
from app.schemas.management_company import (
    ManagementCompanyCreate,
    ManagementCompanyRead,
    ManagementCompanyUpdate,
)

router = APIRouter(prefix="/management-companies", tags=["management-companies"])


@router.post("", response_model=ManagementCompanyRead, status_code=status.HTTP_201_CREATED)
def create_management_company(
    payload: ManagementCompanyCreate, session: Session = Depends(get_session)
):
    obj = ManagementCompany(**payload.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.get("", response_model=list[ManagementCompanyRead])
def list_management_companies(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_session)
):
    return session.exec(select(ManagementCompany).offset(skip).limit(limit)).all()


@router.get("/{company_id}", response_model=ManagementCompanyRead)
def get_management_company(company_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, ManagementCompany, company_id, "Management company")


@router.patch("/{company_id}", response_model=ManagementCompanyRead)
def update_management_company(
    company_id: uuid.UUID,
    payload: ManagementCompanyUpdate,
    session: Session = Depends(get_session),
):
    obj = get_or_404(session, ManagementCompany, company_id, "Management company")
    apply_updates(obj, payload.model_dump(exclude_unset=True))
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj
