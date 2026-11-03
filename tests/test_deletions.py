"""Deleting records: previews, blockers, cascades and unlinking."""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models import (
    HOA, AccessCode, HOADocument, Lease, LeaseTenant, Listing, ListingPhoto, ManagementCompany, NotificationLog,
    Owner, Payment, Property, PropertyPhoto, Tenant, TourFeedback, TourIdPhoto, TourRequest,
)
from app.seed import seed

ADMIN = {"host": "dev-app.example.com"}
PUBLIC = {"host": "tours.example.com"}


@pytest.fixture
def c(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    with TestClient(app) as client:
        seed()
        yield client
        # Remove anything a test left behind so other test files see only seed data.
        with Session(engine) as s:
            leftover = s.exec(select(Property).where(Property.name == "Delete Me Condo")).all()
            from app.models import EmailApproval, LeaseBreakDocument, LeaseBreakOption, LeaseBreakRequest
            for p in leftover:
                for lease in s.exec(select(Lease).where(Lease.property_id == p.id)).all():
                    for req in s.exec(select(LeaseBreakRequest).where(LeaseBreakRequest.lease_id == lease.id)).all():
                        req.selected_option_id = None
                        s.add(req)
                        s.flush()
                        for model in (EmailApproval, LeaseBreakDocument, LeaseBreakOption):
                            for row in s.exec(select(model).where(model.lease_break_request_id == req.id)).all():
                                s.delete(row)
                        s.flush()
                        s.delete(req)
                    s.flush()
                    for model in (LeaseTenant, Payment):
                        for row in s.exec(select(model).where(model.lease_id == lease.id)).all():
                            s.delete(row)
                    s.delete(lease)
                s.delete(p)
            for name, model in (("Temp Owner", Owner), ("Temp Mgmt", ManagementCompany), ("Test HOA", HOA)):
                for row in s.exec(select(model).where(model.name == name)).all():
                    s.delete(row)
            for t in s.exec(select(Tenant).where(Tenant.last_name == "Ant")).all():
                s.delete(t)
            s.commit()


def _base():
    with Session(engine) as s:
        p = s.exec(select(Property)).first()
        return p.owner_id, p.jurisdiction_id


def _property(name="Delete Me Condo", **kw):
    owner_id, jur_id = _base()
    with Session(engine) as s:
        p = Property(name=name, address_line1="1 Test St", city="Tucson", state="AZ", postal_code="85718",
                     owner_id=kw.pop("owner_id", owner_id), jurisdiction_id=jur_id, **kw)
        s.add(p)
        s.commit()
        return p.id


def _exists(model, obj_id) -> bool:
    with Session(engine) as s:
        return s.get(model, obj_id) is not None


def _preview(c, kind, obj_id):
    r = c.get(f"/api/v1/{kind}/{obj_id}/delete-preview", headers=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()


def test_property_with_listing_tours_and_codes_is_fully_removed(c):
    pid = _property()
    start = datetime(2026, 12, 5, 17, tzinfo=timezone.utc)
    with Session(engine) as s:
        s.add(PropertyPhoto(property_id=pid, content=b"p"))
        listing = Listing(property_id=pid, status="listed", monthly_rent=1, available_date=date(2026, 12, 1))
        s.add(listing)
        s.flush()
        s.add(ListingPhoto(listing_id=listing.id, content=b"l"))
        req = TourRequest(listing_id=listing.id, property_id=pid, first_name="A", last_name="B", email="a@b.co",
                          phone="+16165550142", tour_start=start, tour_end=start + timedelta(minutes=30),
                          time_zone="America/Phoenix", id_photo_delete_after=start + timedelta(days=30))
        s.add(req)
        s.flush()
        s.add_all([TourIdPhoto(tour_request_id=req.id, content=b"i"),
                   TourFeedback(tour_request_id=req.id, rating=5, interested="yes"),
                   NotificationLog(tour_request_id=req.id, channel="email", audience="visitor", kind="x",
                                   recipient="a@b.co", status="sent"),
                   AccessCode(property_id=pid, code="1234", status="issued", tour_request_id=req.id),
                   AccessCode(property_id=pid, code="5678")])
        s.commit()
        req_id = req.id

    plan = _preview(c, "properties", pid)
    assert plan["can_delete"] and plan["name"] == "Delete Me Condo"
    text = " ".join(plan["also_deletes"])
    assert "its photo" in text and "1 listing and 1 listing photo" in text and "2 door codes" in text
    assert "1 tour request" in text

    assert c.delete(f"/api/v1/properties/{pid}", headers=ADMIN).status_code == 204
    assert not _exists(Property, pid) and not _exists(TourRequest, req_id)
    with Session(engine) as s:
        assert s.exec(select(AccessCode).where(AccessCode.property_id == pid)).all() == []
        assert s.exec(select(TourFeedback).where(TourFeedback.tour_request_id == req_id)).all() == []


def test_property_with_lease_is_blocked(c):
    pid = _property()
    with Session(engine) as s:
        s.add(Lease(property_id=pid, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), monthly_rent=1))
        s.commit()
    plan = _preview(c, "properties", pid)
    assert not plan["can_delete"] and "1 lease" in plan["blockers"][0]
    r = c.delete(f"/api/v1/properties/{pid}", headers=ADMIN)
    assert r.status_code == 409 and "1 lease" in r.json()["detail"]
    assert _exists(Property, pid)


def test_hoa_delete_unlinks_properties_and_removes_documents(c):
    with Session(engine) as s:
        hoa = HOA(name="Test HOA")
        s.add(hoa)
        s.flush()
        s.add(HOADocument(hoa_id=hoa.id, name="CC&Rs"))
        s.commit()
        hoa_id = hoa.id
    pid = _property(hoa_id=hoa_id)
    plan = _preview(c, "hoas", hoa_id)
    assert plan["can_delete"] and plan["also_deletes"] == ["1 HOA document"]
    assert "Delete Me Condo" in plan["unlinks"][0]
    assert c.delete(f"/api/v1/hoas/{hoa_id}", headers=ADMIN).status_code == 204
    assert not _exists(HOA, hoa_id)
    with Session(engine) as s:
        assert s.get(Property, pid).hoa_id is None
        s.delete(s.get(Property, pid))
        s.commit()


def test_owner_with_properties_is_blocked_then_deletable(c):
    with Session(engine) as s:
        owner = Owner(name="Temp Owner")
        s.add(owner)
        s.commit()
        oid = owner.id
    pid = _property(owner_id=oid)
    assert not _preview(c, "owners", oid)["can_delete"]
    assert c.delete(f"/api/v1/owners/{oid}", headers=ADMIN).status_code == 409
    c.delete(f"/api/v1/properties/{pid}", headers=ADMIN)
    assert c.delete(f"/api/v1/owners/{oid}", headers=ADMIN).status_code == 204


def test_management_company_unlinks(c):
    with Session(engine) as s:
        mc = ManagementCompany(name="Temp Mgmt")
        s.add(mc)
        s.commit()
        mid = mc.id
    pid = _property(management_company_id=mid)
    assert "Delete Me Condo" in _preview(c, "management-companies", mid)["unlinks"][0]
    assert c.delete(f"/api/v1/management-companies/{mid}", headers=ADMIN).status_code == 204
    with Session(engine) as s:
        assert s.get(Property, pid).management_company_id is None
    c.delete(f"/api/v1/properties/{pid}", headers=ADMIN)


def test_tenant_and_lease_rules(c):
    pid = _property()
    with Session(engine) as s:
        t = Tenant(first_name="Ten", last_name="Ant")
        lease = Lease(property_id=pid, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), monthly_rent=1)
        s.add_all([t, lease])
        s.flush()
        s.add(LeaseTenant(lease_id=lease.id, tenant_id=t.id, is_primary=True))
        s.add(Payment(lease_id=lease.id, amount=100))
        s.commit()
        tid, lid = t.id, lease.id

    assert "1 lease" in _preview(c, "tenants", tid)["blockers"][0]
    lease_plan = _preview(c, "leases", lid)
    assert not lease_plan["can_delete"] and "1 payment" in lease_plan["blockers"][0]
    assert "1 tenant will be removed" in lease_plan["unlinks"][0]

    with Session(engine) as s:
        for pay in s.exec(select(Payment).where(Payment.lease_id == lid)).all():
            s.delete(pay)
        s.commit()
    assert c.delete(f"/api/v1/leases/{lid}", headers=ADMIN).status_code == 204
    assert _exists(Tenant, tid)  # tenant record kept
    assert c.delete(f"/api/v1/tenants/{tid}", headers=ADMIN).status_code == 204
    assert c.delete(f"/api/v1/properties/{pid}", headers=ADMIN).status_code == 204


def test_missing_record_and_public_host(c):
    assert c.get(f"/api/v1/properties/{uuid.uuid4()}/delete-preview", headers=ADMIN).status_code == 404
    pid = _property()
    assert c.delete(f"/api/v1/properties/{pid}", headers=PUBLIC).status_code == 404
    assert _exists(Property, pid)
    c.delete(f"/api/v1/properties/{pid}", headers=ADMIN)


def _lease_with_break(signed=False):
    from app.models import EmailApproval, LeaseBreakDocument, LeaseBreakOption, LeaseBreakRequest

    pid = _property()
    with Session(engine) as s:
        lease = Lease(property_id=pid, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), monthly_rent=1)
        s.add(lease)
        s.flush()
        req = LeaseBreakRequest(lease_id=lease.id, requested_date=date(2026, 6, 1), desired_move_out_date=date(2026, 7, 31))
        s.add(req)
        s.flush()
        opt = LeaseBreakOption(lease_break_request_id=req.id, option_type="buyout", label="3x buyout", line_items=[],
                               cash_due_at_signing=4500)
        s.add(opt)
        s.flush()
        req.selected_option_id = opt.id
        s.add_all([req,
                   LeaseBreakDocument(lease_break_request_id=req.id, document_type="termination_agreement",
                                      file_name="a.pdf", status="signed" if signed else "generated"),
                   EmailApproval(lease_break_request_id=req.id, to_emails=[], cc_emails=[], subject="s",
                                 body_html="b", attachments=[])])
        s.commit()
        return pid, lease.id, req.id


def test_lease_breaks_list_and_lease_delete_cascades(c):
    from app.models import LeaseBreakOption, LeaseBreakRequest

    pid, lid, rid = _lease_with_break()
    rows = c.get("/api/v1/lease-breaks", params={"lease_id": lid}, headers=ADMIN).json()
    assert len(rows) == 1 and rows[0]["property_name"] == "Delete Me Condo"
    assert rows[0]["selected_option_label"] == "3x buyout" and rows[0]["cash_due_at_signing"] == 4500
    assert rows[0]["has_signed_agreement"] is False

    plan = _preview(c, "leases", lid)
    assert plan["can_delete"] and "1 lease-break request" in " ".join(plan["also_deletes"])
    assert c.delete(f"/api/v1/leases/{lid}", headers=ADMIN).status_code == 204
    assert not _exists(LeaseBreakRequest, rid)
    with Session(engine) as s:
        assert s.exec(select(LeaseBreakOption).where(LeaseBreakOption.lease_break_request_id == rid)).all() == []
    assert c.delete(f"/api/v1/properties/{pid}", headers=ADMIN).status_code == 204


def test_delete_single_lease_break(c):
    from app.models import LeaseBreakRequest

    pid, lid, rid = _lease_with_break()
    plan = _preview(c, "lease-breaks", rid)
    assert plan["can_delete"] and plan["also_deletes"] == ["1 buyout option", "1 generated agreement", "1 email draft"]
    assert c.delete(f"/api/v1/lease-breaks/{rid}", headers=ADMIN).status_code == 204
    assert not _exists(LeaseBreakRequest, rid) and _exists(Lease, lid)
    c.delete(f"/api/v1/leases/{lid}", headers=ADMIN)
    c.delete(f"/api/v1/properties/{pid}", headers=ADMIN)


def test_signed_lease_break_blocks_deletes(c):
    pid, lid, rid = _lease_with_break(signed=True)
    assert c.get("/api/v1/lease-breaks", params={"lease_id": lid}, headers=ADMIN).json()[0]["has_signed_agreement"]
    assert "signed" in _preview(c, "lease-breaks", rid)["blockers"][0]
    assert c.delete(f"/api/v1/lease-breaks/{rid}", headers=ADMIN).status_code == 409
    assert "signed lease-break agreement" in _preview(c, "leases", lid)["blockers"][0]
    assert c.delete(f"/api/v1/leases/{lid}", headers=ADMIN).status_code == 409
