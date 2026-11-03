import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Owner
from app.routers.crud import apply_updates, get_or_404
from app.schemas.owner import OwnerCreate, OwnerRead, OwnerUpdate

router = APIRouter(prefix="/owners", tags=["owners"])


@router.post("", response_model=OwnerRead, status_code=status.HTTP_201_CREATED)
def create_owner(payload: OwnerCreate, session: Session = Depends(get_session)):
    owner = Owner(**payload.model_dump())
    session.add(owner)
    session.commit()
    session.refresh(owner)
    return owner


@router.get("", response_model=list[OwnerRead])
def list_owners(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    return session.exec(select(Owner).offset(skip).limit(limit)).all()


@router.get("/{owner_id}", response_model=OwnerRead)
def get_owner(owner_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, Owner, owner_id, "Owner")


@router.patch("/{owner_id}", response_model=OwnerRead)
def update_owner(
    owner_id: uuid.UUID,
    payload: OwnerUpdate,
    session: Session = Depends(get_session),
):
    owner = get_or_404(session, Owner, owner_id, "Owner")
    apply_updates(owner, payload.model_dump(exclude_unset=True))
    session.add(owner)
    session.commit()
    session.refresh(owner)
    return owner
