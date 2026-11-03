import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Jurisdiction
from app.routers.crud import get_or_404

router = APIRouter(prefix="/jurisdictions", tags=["jurisdictions"])


@router.get("")
def list_jurisdictions(session: Session = Depends(get_session)):
    return session.exec(select(Jurisdiction)).all()


@router.get("/{jurisdiction_id}")
def get_jurisdiction(jurisdiction_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, Jurisdiction, jurisdiction_id, "Jurisdiction")
