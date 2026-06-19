import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    Lease,
    LeaseBreakDocument,
    LeaseBreakOption,
    LeaseBreakRequest,
    LeaseTenant,
    Owner,
    Property,
    Tenant,
)
from app.models.enums import DocumentType, LeaseBreakStatus
from app.routers.crud import get_or_404
from app.schemas.lease_break import (
    CalculateOptionsRequest,
    GenerateAgreementRequest,
    InitiateLeaseBreakRequest,
    LeaseBreakDetail,
    LeaseBreakDocumentRead,
    LeaseBreakOptionRead,
    LeaseBreakRequestRead,
    SelectOptionRequest,
)
from app.services.lease_break_calculator import LeaseBreakCalculator
from app.services.lease_break_documents import build_buyout_agreement_pdf

router = APIRouter(prefix="/lease-breaks", tags=["lease-breaks"])


def _tenants_for_lease(session: Session, lease_id: uuid.UUID) -> list[Tenant]:
    """Tenants on the lease, primary first."""
    links = session.exec(
        select(LeaseTenant)
        .where(LeaseTenant.lease_id == lease_id)
        .order_by(LeaseTenant.is_primary.desc())
    ).all()
    tenants: list[Tenant] = []
    for link in links:
        t = session.get(Tenant, link.tenant_id)
        if t is not None:
            tenants.append(t)
    return tenants


def _doc_read(doc: LeaseBreakDocument) -> LeaseBreakDocumentRead:
    return LeaseBreakDocumentRead(
        id=doc.id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        lease_break_request_id=doc.lease_break_request_id,
        document_type=doc.document_type,
        status=doc.status,
        file_name=doc.file_name,
        file_type=doc.file_type,
        has_file=doc.content is not None,
    )


@router.post("/initiate", response_model=LeaseBreakRequestRead, status_code=status.HTTP_201_CREATED)
def initiate(body: InitiateLeaseBreakRequest, session: Session = Depends(get_session)):
    lease = get_or_404(session, Lease, uuid.UUID(body.lease_id), "Lease")
    try:
        move_out = date.fromisoformat(body.desired_move_out_date[:10])
    except ValueError:
        raise HTTPException(status_code=422, detail="desired_move_out_date must be YYYY-MM-DD")

    req = LeaseBreakRequest(
        lease_id=lease.id,
        status=LeaseBreakStatus.initiated.value,
        requested_date=date.today(),
        desired_move_out_date=move_out,
        reason=body.reason,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


@router.post("/{request_id}/calculate-options", response_model=list[LeaseBreakOptionRead])
def calculate_options(
    request_id: uuid.UUID,
    body: CalculateOptionsRequest,
    session: Session = Depends(get_session),
):
    req = get_or_404(session, LeaseBreakRequest, request_id, "Lease break request")
    lease = get_or_404(session, Lease, req.lease_id, "Lease")
    tenants = _tenants_for_lease(session, lease.id)
    tenant_names = [f"{t.first_name} {t.last_name}" for t in tenants]
    n = max(1, len(tenants))

    rent = lease.monthly_rent
    deposit = lease.security_deposit or 0.0
    last_month_held = body.last_months_rent_held if body.last_months_rent_held is not None else rent
    joint_multiple = body.buyout_multiple or 3.0
    final_rent_due_date = f"{body.move_out_date[:7]}-01"

    # Recompute: clear any prior options for this request.
    for existing in session.exec(
        select(LeaseBreakOption).where(LeaseBreakOption.lease_break_request_id == request_id)
    ).all():
        session.delete(existing)
    session.flush()

    calc = LeaseBreakCalculator()
    options: list[LeaseBreakOption] = []

    # Option 1 — joint buyout (all tenants).
    c1 = calc.calculate_buyout_option(rent, last_month_held, deposit, joint_multiple, body.move_out_date)
    options.append(
        LeaseBreakOption(
            lease_break_request_id=request_id,
            option_number=1,
            option_type="buyout",
            label=calc.generate_option_title(1, "buyout", tenant_names),
            description=f"All {n} tenant(s) execute a clean break at {joint_multiple:g}× monthly rent.",
            total_cost_to_tenant=c1.cash_due_at_signing,
            buyout_multiple=joint_multiple,
            monthly_rent_amount=rent,
            last_months_rent_held=last_month_held,
            current_month_rent=c1.current_month_rent,
            buyout_amount_gross=c1.buyout_amount_gross,
            last_month_credit=c1.last_month_credit,
            cash_due_at_signing=c1.cash_due_at_signing,
            total_cash_collected=c1.total_cash_collected,
            security_deposit_held=deposit,
            move_out_date=body.move_out_date,
            final_rent_due_date=final_rent_due_date,
            terms=(
                f"Tenant(s) pay {c1.cash_due_at_signing:,.2f} at signing "
                f"(gross buyout {c1.buyout_amount_gross:,.2f} less {c1.last_month_credit:,.2f} credit)."
            ),
        )
    )

    next_num = 2
    # Option 2 — individual buyout (only when there are co-tenants).
    if len(tenants) > 1:
        c2 = calc.calculate_buyout_option(rent, last_month_held / n, deposit / n, 2.0, body.move_out_date)
        primary = tenant_names[0]
        options.append(
            LeaseBreakOption(
                lease_break_request_id=request_id,
                option_number=2,
                option_type="buyout",
                label=f"Option 2: {primary} Buyout Only",
                description=f"{primary} buys out at 2× rent; the remaining tenant(s) stay on the lease.",
                total_cost_to_tenant=c2.cash_due_at_signing,
                buyout_multiple=2.0,
                monthly_rent_amount=rent,
                last_months_rent_held=last_month_held / n,
                current_month_rent=c2.current_month_rent,
                buyout_amount_gross=c2.buyout_amount_gross,
                last_month_credit=c2.last_month_credit,
                cash_due_at_signing=c2.cash_due_at_signing,
                total_cash_collected=c2.total_cash_collected,
                security_deposit_held=deposit / n,
                move_out_date=body.move_out_date,
                final_rent_due_date=final_rent_due_date,
                terms=f"{primary} pays {c2.cash_due_at_signing:,.2f}; remaining tenant(s) remain liable.",
            )
        )
        next_num = 3

    # Final option — stay on hook (remain liable).
    options.append(
        LeaseBreakOption(
            lease_break_request_id=request_id,
            option_number=next_num,
            option_type="stay_on_hook",
            label=f"Option {next_num}: No Buyout (Remain Liable)",
            description="Tenant(s) remain fully liable for rent until the unit is re-rented or the lease ends.",
            total_cost_to_tenant=0.0,
            monthly_rent_amount=rent,
            security_deposit_held=deposit,
            move_out_date=body.move_out_date,
            terms="Liability continues until re-rented (landlord's duty to mitigate applies). Highest risk for tenant.",
        )
    )

    for o in options:
        session.add(o)

    req.calculation_context = {
        "monthly_rent": rent,
        "last_months_rent_held": last_month_held,
        "security_deposit": deposit,
        "joint_multiple": joint_multiple,
        "move_out_date": body.move_out_date,
        "tenant_count": len(tenants),
    }
    req.status = LeaseBreakStatus.options_presented.value
    session.add(req)
    session.commit()
    for o in options:
        session.refresh(o)
    return options


@router.get("/{request_id}", response_model=LeaseBreakDetail)
def get_request(request_id: uuid.UUID, session: Session = Depends(get_session)):
    req = get_or_404(session, LeaseBreakRequest, request_id, "Lease break request")
    options = session.exec(
        select(LeaseBreakOption)
        .where(LeaseBreakOption.lease_break_request_id == request_id)
        .order_by(LeaseBreakOption.option_number)
    ).all()
    docs = session.exec(
        select(LeaseBreakDocument).where(LeaseBreakDocument.lease_break_request_id == request_id)
    ).all()
    return LeaseBreakDetail(
        request=LeaseBreakRequestRead.model_validate(req),
        options=[LeaseBreakOptionRead.model_validate(o) for o in options],
        documents=[_doc_read(d) for d in docs],
    )


@router.post("/{request_id}/select-option", response_model=LeaseBreakOptionRead)
def select_option(
    request_id: uuid.UUID,
    body: SelectOptionRequest,
    session: Session = Depends(get_session),
):
    req = get_or_404(session, LeaseBreakRequest, request_id, "Lease break request")
    chosen = session.get(LeaseBreakOption, uuid.UUID(body.option_id))
    if chosen is None or chosen.lease_break_request_id != request_id:
        raise HTTPException(status_code=404, detail="Option not found")

    for o in session.exec(
        select(LeaseBreakOption).where(LeaseBreakOption.lease_break_request_id == request_id)
    ).all():
        o.is_selected = o.id == chosen.id
        session.add(o)

    chosen.selected_at = datetime.now()
    chosen.selected_by_tenant = uuid.UUID(body.tenant_id) if body.tenant_id else None
    req.selected_option_id = chosen.id
    req.status = LeaseBreakStatus.option_selected.value
    session.add(chosen)
    session.add(req)
    session.commit()
    session.refresh(chosen)
    return chosen


@router.post("/{request_id}/generate-agreement", response_model=LeaseBreakDocumentRead)
def generate_agreement(
    request_id: uuid.UUID,
    body: GenerateAgreementRequest,
    session: Session = Depends(get_session),
):
    req = get_or_404(session, LeaseBreakRequest, request_id, "Lease break request")
    option = session.get(LeaseBreakOption, uuid.UUID(body.option_id))
    if option is None or option.lease_break_request_id != request_id:
        raise HTTPException(status_code=404, detail="Option not found")
    if option.option_type != "buyout":
        raise HTTPException(status_code=422, detail="Agreements are generated for buyout options only.")

    lease = get_or_404(session, Lease, req.lease_id, "Lease")
    prop = session.get(Property, lease.property_id)
    owner = session.get(Owner, prop.owner_id) if prop else None
    tenants = _tenants_for_lease(session, lease.id)

    pdf = build_buyout_agreement_pdf(option, lease, prop, owner, tenants)
    fname = f"buyout-agreement-{req.id}.pdf"

    doc = LeaseBreakDocument(
        lease_break_request_id=request_id,
        document_type=DocumentType.buyout_addendum.value,
        file_name=fname,
        file_type="application/pdf",
        content=pdf,
    )
    session.add(doc)
    req.status = LeaseBreakStatus.documents_generated.value
    session.add(req)
    session.commit()
    session.refresh(doc)
    return _doc_read(doc)


@router.get("/{request_id}/documents", response_model=list[LeaseBreakDocumentRead])
def list_documents(request_id: uuid.UUID, session: Session = Depends(get_session)):
    get_or_404(session, LeaseBreakRequest, request_id, "Lease break request")
    docs = session.exec(
        select(LeaseBreakDocument).where(LeaseBreakDocument.lease_break_request_id == request_id)
    ).all()
    return [_doc_read(d) for d in docs]


@router.get("/{request_id}/documents/{document_id}/download")
def download_document(
    request_id: uuid.UUID, document_id: uuid.UUID, session: Session = Depends(get_session)
):
    doc = session.get(LeaseBreakDocument, document_id)
    if doc is None or doc.lease_break_request_id != request_id or doc.content is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(
        content=doc.content,
        media_type=doc.file_type or "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'},
    )
