import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import HOA, HOADocument, Property
from app.routers.crud import apply_updates, get_or_404
from app.schemas.hoa import HOACreate, HOADocumentRead, HOARead, HOAUpdate

router = APIRouter(prefix="/hoas", tags=["hoas"])

MAX_DOC_BYTES = 20 * 1024 * 1024  # 20 MB per document


def _doc_to_read(doc: HOADocument) -> HOADocumentRead:
    return HOADocumentRead(
        id=doc.id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        hoa_id=doc.hoa_id,
        name=doc.name,
        doc_type=doc.doc_type,
        filename=doc.filename,
        content_type=doc.content_type,
        file_size=doc.file_size,
        external_url=doc.external_url,
        uploaded_at=doc.uploaded_at,
        has_file=doc.content is not None,
    )


@router.post("", response_model=HOARead, status_code=status.HTTP_201_CREATED)
def create_hoa(payload: HOACreate, session: Session = Depends(get_session)):
    hoa = HOA(**payload.model_dump())
    session.add(hoa)
    session.commit()
    session.refresh(hoa)
    return hoa


@router.get("", response_model=list[HOARead])
def list_hoas(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    return session.exec(select(HOA).offset(skip).limit(limit)).all()


@router.get("/{hoa_id}", response_model=HOARead)
def get_hoa(hoa_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, HOA, hoa_id, "HOA")


@router.patch("/{hoa_id}", response_model=HOARead)
def update_hoa(hoa_id: uuid.UUID, payload: HOAUpdate, session: Session = Depends(get_session)):
    hoa = get_or_404(session, HOA, hoa_id, "HOA")
    apply_updates(hoa, payload.model_dump(exclude_unset=True))
    session.add(hoa)
    session.commit()
    session.refresh(hoa)
    return hoa


@router.delete("/{hoa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hoa(hoa_id: uuid.UUID, session: Session = Depends(get_session)):
    hoa = get_or_404(session, HOA, hoa_id, "HOA")
    linked = session.exec(select(Property).where(Property.hoa_id == hoa_id)).first()
    if linked is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="HOA is linked to one or more properties; unlink them first.",
        )
    # Remove its documents, then the HOA.
    for doc in session.exec(select(HOADocument).where(HOADocument.hoa_id == hoa_id)).all():
        session.delete(doc)
    session.delete(hoa)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Documents -------------------------------------------------------------


@router.get("/{hoa_id}/documents", response_model=list[HOADocumentRead])
def list_documents(hoa_id: uuid.UUID, session: Session = Depends(get_session)):
    get_or_404(session, HOA, hoa_id, "HOA")
    docs = session.exec(
        select(HOADocument).where(HOADocument.hoa_id == hoa_id)
    ).all()
    return [_doc_to_read(d) for d in docs]


@router.post(
    "/{hoa_id}/documents",
    response_model=HOADocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_document(
    hoa_id: uuid.UUID,
    name: str = Form(...),
    doc_type: str = Form("other"),
    external_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
):
    get_or_404(session, HOA, hoa_id, "HOA")

    if file is None and not external_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either a file upload or an external_url.",
        )

    doc = HOADocument(hoa_id=hoa_id, name=name, doc_type=doc_type, external_url=external_url or None)

    if file is not None:
        content = await file.read()
        if len(content) > MAX_DOC_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {MAX_DOC_BYTES // (1024 * 1024)} MB limit.",
            )
        doc.content = content
        doc.filename = file.filename
        doc.content_type = file.content_type or "application/octet-stream"
        doc.file_size = len(content)

    session.add(doc)
    session.commit()
    session.refresh(doc)
    return _doc_to_read(doc)


@router.get("/{hoa_id}/documents/{doc_id}/download")
def download_document(
    hoa_id: uuid.UUID, doc_id: uuid.UUID, session: Session = Depends(get_session)
):
    doc = session.get(HOADocument, doc_id)
    if doc is None or doc.hoa_id != hoa_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.content is None:
        if doc.external_url:
            return RedirectResponse(url=doc.external_url)
        raise HTTPException(status_code=404, detail="Document has no file")
    filename = doc.filename or f"{doc.name}"
    return Response(
        content=doc.content,
        media_type=doc.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{hoa_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    hoa_id: uuid.UUID, doc_id: uuid.UUID, session: Session = Depends(get_session)
):
    doc = session.get(HOADocument, doc_id)
    if doc is None or doc.hoa_id != hoa_id:
        raise HTTPException(status_code=404, detail="Document not found")
    session.delete(doc)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
