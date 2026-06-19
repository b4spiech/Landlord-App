import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlmodel import Session, select

from app.database import get_session
from app.models import Property, PropertyPhoto
from app.routers.crud import apply_updates, get_or_404
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


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


# --- Property photo --------------------------------------------------------


@router.post("/{property_id}/photo", status_code=status.HTTP_201_CREATED)
async def upload_property_photo(
    property_id: uuid.UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    get_or_404(session, Property, property_id, "Property")
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(status_code=422, detail="Upload a JPG, PNG, WEBP, or GIF image.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Photo exceeds the 10 MB limit.")

    # One photo per property: replace any existing.
    for existing in session.exec(
        select(PropertyPhoto).where(PropertyPhoto.property_id == property_id)
    ).all():
        session.delete(existing)

    photo = PropertyPhoto(
        property_id=property_id,
        filename=file.filename,
        content_type=file.content_type,
        file_size=len(content),
        content=content,
    )
    session.add(photo)
    session.commit()
    return {"ok": True, "file_size": len(content)}


@router.get("/{property_id}/photo")
def get_property_photo(property_id: uuid.UUID, session: Session = Depends(get_session)):
    photo = session.exec(
        select(PropertyPhoto)
        .where(PropertyPhoto.property_id == property_id)
        .order_by(PropertyPhoto.created_at.desc())
    ).first()
    if photo is None:
        raise HTTPException(status_code=404, detail="No photo")
    return Response(
        content=photo.content,
        media_type=photo.content_type or "image/jpeg",
        headers={"Cache-Control": "no-cache"},
    )


@router.delete("/{property_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_photo(property_id: uuid.UUID, session: Session = Depends(get_session)):
    photos = session.exec(
        select(PropertyPhoto).where(PropertyPhoto.property_id == property_id)
    ).all()
    for p in photos:
        session.delete(p)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
