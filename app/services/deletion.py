"""What deleting a record would do — and doing it.

Each `plan_*` function inspects a record and returns a DeletePlan: what blocks
the delete (financial or legal history we never remove silently), what will be
deleted along with it, and what will just be unlinked. The landlord app shows
the plan in a confirmation dialog; `apply()` re-checks and performs it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable

from fastapi import HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlmodel import Session, func, select

from app.models.enums import DocumentStatus, LeaseBreakStatus
from app.models import (
    HOA,
    AccessCode,
    EmailApproval,
    Expense,
    HOADocument,
    Lease,
    LeaseBreakDocument,
    LeaseBreakOption,
    LeaseBreakRequest,
    LeaseDocument,
    LeaseTenant,
    Listing,
    ListingPhoto,
    ManagementCompany,
    NotificationLog,
    Owner,
    Payment,
    Property,
    PropertyPhoto,
    Tenant,
    TourFeedback,
    TourIdPhoto,
    TourRequest,
)


@dataclass
class DeletePlan:
    kind: str
    name: str
    blockers: list[str] = field(default_factory=list)
    also_deletes: list[str] = field(default_factory=list)
    unlinks: list[str] = field(default_factory=list)
    _steps: list[Callable[[], None]] = field(default_factory=list, repr=False)

    @property
    def can_delete(self) -> bool:
        return not self.blockers

    def summary(self) -> dict:
        return {"kind": self.kind, "name": self.name, "can_delete": self.can_delete, "blockers": self.blockers,
                "also_deletes": self.also_deletes, "unlinks": self.unlinks}


def _count(session: Session, model, *where) -> int:
    return session.exec(select(func.count()).select_from(model).where(*where)).one()


def _n(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _get(session: Session, model, obj_id: uuid.UUID, label: str):
    obj = session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def apply(session: Session, plan: DeletePlan) -> None:
    if not plan.can_delete:
        raise HTTPException(status_code=409, detail="Can't delete: " + "; ".join(plan.blockers))
    for step in plan._steps:
        step()
    session.commit()


# --- Per record type ----------------------------------------------------------


def plan_property(session: Session, property_id: uuid.UUID) -> DeletePlan:
    prop = _get(session, Property, property_id, "Property")
    plan = DeletePlan("property", prop.name)
    if n := _count(session, Lease, Lease.property_id == property_id):
        plan.blockers.append(f"it has {_n(n, 'lease')} (delete or move them to another property first)")
    if n := _count(session, Expense, Expense.property_id == property_id):
        plan.blockers.append(f"it has {_n(n, 'expense')} recorded")

    listing_ids = list(session.exec(select(Listing.id).where(Listing.property_id == property_id)).all())
    tour_ids = list(session.exec(select(TourRequest.id).where(TourRequest.property_id == property_id)).all())
    if _count(session, PropertyPhoto, PropertyPhoto.property_id == property_id):
        plan.also_deletes.append("its photo")
    if listing_ids:
        photos = _count(session, ListingPhoto, ListingPhoto.listing_id.in_(listing_ids))
        plan.also_deletes.append(_n(len(listing_ids), "listing") + (f" and {_n(photos, 'listing photo')}" if photos else ""))
    if n := _count(session, AccessCode, AccessCode.property_id == property_id):
        plan.also_deletes.append(_n(n, "door code"))
    if tour_ids:
        plan.also_deletes.append(_n(len(tour_ids), "tour request") + " (with their photo IDs, feedback and message history)")

    def run():
        if tour_ids:
            for model in (TourFeedback, TourIdPhoto, NotificationLog):
                session.exec(sa_delete(model).where(model.tour_request_id.in_(tour_ids)))
        session.exec(sa_delete(AccessCode).where(AccessCode.property_id == property_id))
        if tour_ids:
            session.exec(sa_delete(TourRequest).where(TourRequest.id.in_(tour_ids)))
        if listing_ids:
            session.exec(sa_delete(ListingPhoto).where(ListingPhoto.listing_id.in_(listing_ids)))
            session.exec(sa_delete(Listing).where(Listing.id.in_(listing_ids)))
        session.exec(sa_delete(PropertyPhoto).where(PropertyPhoto.property_id == property_id))
        session.delete(prop)

    plan._steps.append(run)
    return plan


def plan_hoa(session: Session, hoa_id: uuid.UUID) -> DeletePlan:
    hoa = _get(session, HOA, hoa_id, "HOA")
    plan = DeletePlan("hoa", hoa.name)
    if n := _count(session, HOADocument, HOADocument.hoa_id == hoa_id):
        plan.also_deletes.append(_n(n, "HOA document"))
    names = list(session.exec(select(Property.name).where(Property.hoa_id == hoa_id)).all())
    if names:
        plan.unlinks.append(f"{_n(len(names), 'property')} will no longer have an HOA: {', '.join(names)}")

    def run():
        session.exec(sa_update(Property).where(Property.hoa_id == hoa_id).values(hoa_id=None))
        session.exec(sa_delete(HOADocument).where(HOADocument.hoa_id == hoa_id))
        session.delete(hoa)

    plan._steps.append(run)
    return plan


def plan_owner(session: Session, owner_id: uuid.UUID) -> DeletePlan:
    owner = _get(session, Owner, owner_id, "Owner")
    plan = DeletePlan("owner", owner.name)
    if n := _count(session, Property, Property.owner_id == owner_id):
        plan.blockers.append(f"they own {_n(n, 'property')} (assign a different owner first)")
    plan._steps.append(lambda: session.delete(owner))
    return plan


def plan_management_company(session: Session, company_id: uuid.UUID) -> DeletePlan:
    company = _get(session, ManagementCompany, company_id, "Management company")
    plan = DeletePlan("management_company", company.name)
    names = list(session.exec(select(Property.name).where(Property.management_company_id == company_id)).all())
    if names:
        plan.unlinks.append(f"{_n(len(names), 'property')} will no longer have a management company: {', '.join(names)}")

    def run():
        session.exec(sa_update(Property).where(Property.management_company_id == company_id)
                     .values(management_company_id=None))
        session.delete(company)

    plan._steps.append(run)
    return plan


def plan_tenant(session: Session, tenant_id: uuid.UUID) -> DeletePlan:
    tenant = _get(session, Tenant, tenant_id, "Tenant")
    plan = DeletePlan("tenant", f"{tenant.first_name} {tenant.last_name}")
    if n := _count(session, LeaseTenant, LeaseTenant.tenant_id == tenant_id):
        plan.blockers.append(f"they are on {_n(n, 'lease')} (remove them from the lease or delete it first)")
    if n := _count(session, AccessCode, AccessCode.tenant_id == tenant_id):
        plan.unlinks.append(f"{_n(n, 'door code')} assigned to them will go back to the property's tenant-code pool")

    def run():
        session.exec(sa_update(AccessCode).where(AccessCode.tenant_id == tenant_id)
                     .values(tenant_id=None, assigned_at=None, status="available"))
        session.delete(tenant)

    plan._steps.append(run)
    return plan


def plan_lease(session: Session, lease_id: uuid.UUID) -> DeletePlan:
    lease = _get(session, Lease, lease_id, "Lease")
    prop = session.get(Property, lease.property_id)
    plan = DeletePlan("lease", f"{prop.name if prop else 'Lease'} · {lease.start_date} → {lease.end_date}")
    if n := _count(session, Payment, Payment.lease_id == lease_id):
        plan.blockers.append(f"it has {_n(n, 'payment')} recorded")
    breaks = list(session.exec(select(LeaseBreakRequest).where(LeaseBreakRequest.lease_id == lease_id)).all())
    signed = [b for b in breaks if lease_break_is_signed(session, b)]
    if signed:
        plan.blockers.append(f"it has {_n(len(signed), 'signed lease-break agreement')} (legal record)")
    elif breaks:
        plan.also_deletes.append(_n(len(breaks), "lease-break request") + " (with their options, agreements and email drafts)")
    if n := _count(session, LeaseTenant, LeaseTenant.lease_id == lease_id):
        plan.unlinks.append(f"{_n(n, 'tenant')} will be removed from this lease (the tenant records stay)")
    if n := _count(session, LeaseDocument, LeaseDocument.lease_id == lease_id):
        plan.also_deletes.append(_n(n, "uploaded lease document"))

    def run():
        for b in breaks:
            _delete_lease_break_rows(session, b)
        session.exec(sa_delete(LeaseTenant).where(LeaseTenant.lease_id == lease_id))
        session.exec(sa_delete(LeaseDocument).where(LeaseDocument.lease_id == lease_id))
        session.delete(lease)

    plan._steps.append(run)
    return plan


def lease_break_is_signed(session: Session, req: LeaseBreakRequest) -> bool:
    """A signed/completed termination agreement is a legal record we never delete."""
    if req.status in (LeaseBreakStatus.signed.value, LeaseBreakStatus.completed.value):
        return True
    return _count(session, LeaseBreakDocument, LeaseBreakDocument.lease_break_request_id == req.id,
                  LeaseBreakDocument.status == DocumentStatus.signed.value) > 0


def _delete_lease_break_rows(session: Session, req: LeaseBreakRequest) -> None:
    # selected_option_id points at an option; clear it before deleting options.
    req.selected_option_id = None
    session.add(req)
    session.flush()
    for model in (EmailApproval, LeaseBreakDocument, LeaseBreakOption):
        session.exec(sa_delete(model).where(model.lease_break_request_id == req.id))
    # Delete immediately (not at commit) so it's gone before its lease is deleted.
    session.exec(sa_delete(LeaseBreakRequest).where(LeaseBreakRequest.id == req.id))
    session.expunge(req)


def plan_lease_break(session: Session, request_id: uuid.UUID) -> DeletePlan:
    req = _get(session, LeaseBreakRequest, request_id, "Lease break request")
    lease = session.get(Lease, req.lease_id)
    prop = session.get(Property, lease.property_id) if lease else None
    plan = DeletePlan("lease_break", f"{prop.name if prop else 'Lease'} · move-out {req.desired_move_out_date}")
    if lease_break_is_signed(session, req):
        plan.blockers.append("its termination agreement has been signed (legal record)")
    if n := _count(session, LeaseBreakOption, LeaseBreakOption.lease_break_request_id == request_id):
        plan.also_deletes.append(_n(n, "buyout option"))
    if n := _count(session, LeaseBreakDocument, LeaseBreakDocument.lease_break_request_id == request_id):
        plan.also_deletes.append(_n(n, "generated agreement"))
    if n := _count(session, EmailApproval, EmailApproval.lease_break_request_id == request_id):
        plan.also_deletes.append(_n(n, "email draft"))
    plan._steps.append(lambda: _delete_lease_break_rows(session, req))
    return plan


PLANNERS = {
    "properties": plan_property,
    "hoas": plan_hoa,
    "owners": plan_owner,
    "management-companies": plan_management_company,
    "tenants": plan_tenant,
    "leases": plan_lease,
    "lease-breaks": plan_lease_break,
}
