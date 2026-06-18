import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Unit
from app.routers.crud import apply_updates, get_or_404
from app.schemas.unit import UnitCreate, UnitRead, UnitUpdate

router = APIRouter(prefix="/units", tags=["units"])


@router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(payload: UnitCreate, session: Session = Depends(get_session)):
    obj = Unit(**payload.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.get("", response_model=list[UnitRead])
def list_units(
    property_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    statement = select(Unit)
    if property_id is not None:
        statement = statement.where(Unit.property_id == property_id)
    return session.exec(statement.offset(skip).limit(limit)).all()


@router.get("/{unit_id}", response_model=UnitRead)
def get_unit(unit_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, Unit, unit_id, "Unit")


@router.patch("/{unit_id}", response_model=UnitRead)
def update_unit(
    unit_id: uuid.UUID,
    payload: UnitUpdate,
    session: Session = Depends(get_session),
):
    obj = get_or_404(session, Unit, unit_id, "Unit")
    apply_updates(obj, payload.model_dump(exclude_unset=True))
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj
