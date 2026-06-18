import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Property
from app.routers.crud import apply_updates, get_or_404
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(payload: PropertyCreate, session: Session = Depends(get_session)):
    obj = Property(**payload.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.get("", response_model=list[PropertyRead])
def list_properties(
    owner_id: Optional[uuid.UUID] = None,
    management_company_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    statement = select(Property)
    if owner_id is not None:
        statement = statement.where(Property.owner_id == owner_id)
    if management_company_id is not None:
        statement = statement.where(Property.management_company_id == management_company_id)
    return session.exec(statement.offset(skip).limit(limit)).all()


@router.get("/{property_id}", response_model=PropertyRead)
def get_property(property_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, Property, property_id, "Property")


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    session: Session = Depends(get_session),
):
    obj = get_or_404(session, Property, property_id, "Property")
    apply_updates(obj, payload.model_dump(exclude_unset=True))
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj
