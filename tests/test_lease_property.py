"""A lease is always linked to exactly one existing property, and can be moved."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models import Lease, Property
from app.seed import seed

H = {"host": "dev-app.example.com"}


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    with TestClient(app) as c:
        seed()
        with Session(engine) as s:
            first = s.exec(select(Property)).first()
            second = Property(
                name="Test Second Property", address_line1="1 Test St", city="Tucson", state="AZ",
                postal_code="85718", owner_id=first.owner_id, jurisdiction_id=first.jurisdiction_id,
            )
            s.add(second)
            s.commit()
            ids = (str(first.id), str(second.id))
        body = {"property_id": ids[0], "start_date": "2026-01-01", "end_date": "2026-12-31", "monthly_rent": 1500}
        lease = c.post("/api/v1/leases", json=body, headers=H).json()
        yield c, ids, lease["id"]
        with Session(engine) as s:
            s.exec(delete(Lease).where(Lease.id == uuid.UUID(lease["id"])))
            s.exec(delete(Property).where(Property.id == uuid.UUID(ids[1])))
            s.commit()


def test_move_lease_to_another_property(ctx):
    c, (first, second), lease_id = ctx
    r = c.patch(f"/api/v1/leases/{lease_id}", json={"property_id": second}, headers=H)
    assert r.status_code == 200 and r.json()["property_id"] == second
    assert [l["id"] for l in c.get("/api/v1/leases", params={"property_id": second}, headers=H).json()] == [lease_id]


def test_cannot_unlink_or_link_to_missing_property(ctx):
    c, _, lease_id = ctx
    assert c.patch(f"/api/v1/leases/{lease_id}", json={"property_id": None}, headers=H).status_code == 422
    r = c.patch(f"/api/v1/leases/{lease_id}", json={"property_id": str(uuid.uuid4())}, headers=H)
    assert r.status_code == 404


def test_create_requires_existing_property(ctx):
    c, _, _ = ctx
    body = {"property_id": str(uuid.uuid4()), "start_date": "2026-01-01", "end_date": "2026-12-31", "monthly_rent": 1}
    assert c.post("/api/v1/leases", json=body, headers=H).status_code == 404
