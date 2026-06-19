import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlmodel import Session, func, select

from app.database import get_session
from app.models import Lease, LeaseDocument, LeaseTenant, Payment, Tenant
from app.routers.crud import apply_updates, get_or_404
from app.schemas.lease import (
    LeaseCreate,
    LeaseDocumentRead,
    LeaseDetailRead,
    LeaseRead,
    LeaseUpdate,
)
from app.schemas.lease_import import (
    CreateFromParsedRequest,
    CreateResult,
    ParsedLeaseData,
)
from app.services.lease_parser import LeaseParserError, parse_lease_document

router = APIRouter(prefix="/leases", tags=["leases"])

MAX_UPLOAD_BYTES = 32 * 1024 * 1024  # 32 MB


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
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    statement = select(Lease)
    if property_id is not None:
        statement = statement.where(Lease.property_id == property_id)
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


# ---------------------------------------------------------------------------
# AI document import
# ---------------------------------------------------------------------------


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


# Lease columns that map 1:1 from ParsedLease (excludes address/dates handled separately).
_PARSED_LEASE_FIELDS = (
    "monthly_rent", "security_deposit", "late_fee", "rent_due_day", "payment_frequency",
    "returned_check_fee", "lease_type", "renewal_terms", "deposit_held_location",
    "deposit_interest_rate", "utilities_included", "utilities_tenant_responsibility",
    "occupancy_limit", "pets_allowed", "pet_restrictions", "pet_deposit", "pet_monthly_fee",
    "parking_included", "parking_spaces", "parking_additional_fee", "no_smoking",
    "no_waterbeds", "quiet_hours", "lawn_maintenance_responsibility", "trash_service_included",
    "early_termination_allowed", "early_termination_penalty", "early_termination_notice_days",
    "special_conditions",
)


def _get_or_create_tenant(session: Session, t) -> Optional[Tenant]:
    first = (t.first_name or "").strip()
    last = (t.last_name or "").strip()
    if not first and not last:
        return None  # nothing to identify this tenant by
    existing = session.exec(
        select(Tenant)
        .where(func.lower(Tenant.first_name) == first.lower())
        .where(func.lower(Tenant.last_name) == last.lower())
    ).first()
    if existing is not None:
        return existing
    tenant = Tenant(
        first_name=first or "Unknown",
        last_name=last or "Unknown",
        email=t.email,
        phone=t.phone,
        date_of_birth=t.date_of_birth,
        drivers_license=t.drivers_license,
        emergency_contact_name=t.emergency_contact_name,
        emergency_contact_phone=t.emergency_contact_phone,
        emergency_contact_relationship=t.emergency_contact_relationship,
        employer_name=t.employer_name,
        employer_phone=t.employer_phone,
        job_title=t.job_title,
        annual_income=t.annual_income,
        reference_name=t.reference_name,
        reference_phone=t.reference_phone,
        reference_relationship=t.reference_relationship,
    )
    session.add(tenant)
    session.flush()
    return tenant


def _create_from_parsed(session: Session, req: CreateFromParsedRequest) -> CreateResult:
    parsed = req.parsed
    start = _parse_date(parsed.lease.start_date)
    end = _parse_date(parsed.lease.end_date)
    if start is None or end is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lease start and end dates are required (use YYYY-MM-DD).",
        )

    lease_kwargs = {
        "property_id": uuid.UUID(req.property_id),
        "start_date": start,
        "end_date": end,
        "monthly_rent": parsed.lease.monthly_rent or 0.0,
    }
    for field in _PARSED_LEASE_FIELDS:
        value = getattr(parsed.lease, field, None)
        if value is not None:
            lease_kwargs[field] = value

    lease = Lease(**lease_kwargs)
    session.add(lease)
    session.flush()

    tenants_created = 0
    for pt in parsed.tenants:
        tenant = _get_or_create_tenant(session, pt)
        if tenant is None:
            continue
        session.add(
            LeaseTenant(
                lease_id=lease.id,
                tenant_id=tenant.id,
                is_primary=(tenants_created == 0),
            )
        )
        tenants_created += 1

    document_id = None
    if req.document_id:
        doc = session.get(LeaseDocument, uuid.UUID(req.document_id))
        if doc is not None:
            doc.lease_id = lease.id
            session.add(doc)
            document_id = str(doc.id)

    session.commit()
    return CreateResult(
        lease_id=str(lease.id),
        tenants_created=tenants_created,
        document_id=document_id,
        message="Lease created.",
    )


@router.post("/parse-document")
async def parse_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 32 MB limit.")

    try:
        parsed = parse_lease_document(content, file.content_type or "", file.filename or "")
    except LeaseParserError as exc:
        # 422 → the UI shows the message and offers manual entry.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    doc = LeaseDocument(
        document_type="original_lease",
        file_name=file.filename or "lease",
        file_type=file.content_type,
        file_size=len(content),
        content=content,
        extracted_data=parsed.model_dump(),
        extraction_confidence=parsed.confidence,
        extraction_notes=parsed.notes,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return {"document_id": str(doc.id), "parsed": parsed.model_dump()}


@router.post("/create-from-parsed", response_model=CreateResult)
def create_from_parsed(req: CreateFromParsedRequest, session: Session = Depends(get_session)):
    return _create_from_parsed(session, req)


@router.post("/create-manual", response_model=CreateResult)
def create_manual(req: CreateFromParsedRequest, session: Session = Depends(get_session)):
    # Same as create-from-parsed but without a stored document.
    req.document_id = None
    return _create_from_parsed(session, req)


def _doc_to_read(doc: LeaseDocument) -> LeaseDocumentRead:
    return LeaseDocumentRead(
        id=doc.id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        lease_id=doc.lease_id,
        document_type=doc.document_type,
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        extraction_confidence=doc.extraction_confidence,
        extraction_notes=doc.extraction_notes,
        uploaded_at=doc.uploaded_at,
        has_file=doc.content is not None,
    )


@router.get("/{lease_id}/documents", response_model=list[LeaseDocumentRead])
def list_lease_documents(lease_id: uuid.UUID, session: Session = Depends(get_session)):
    get_or_404(session, Lease, lease_id, "Lease")
    docs = session.exec(select(LeaseDocument).where(LeaseDocument.lease_id == lease_id)).all()
    return [_doc_to_read(d) for d in docs]


@router.get("/{lease_id}/documents/{document_id}/download")
def download_lease_document(
    lease_id: uuid.UUID, document_id: uuid.UUID, session: Session = Depends(get_session)
):
    doc = session.get(LeaseDocument, document_id)
    if doc is None or doc.lease_id != lease_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.content is None:
        raise HTTPException(status_code=404, detail="Document has no file")
    return Response(
        content=doc.content,
        media_type=doc.file_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'},
    )
