"""Listing lifecycle (landlord) and what the public site can see."""

import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models import Listing, ListingPhoto, Property
from app.seed import seed

ADMIN = {"host": "dev-app.example.com"}
PUBLIC = {"host": "tours.example.com"}
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _clear_listings():
    with Session(engine) as s:
        s.exec(delete(ListingPhoto))
        s.exec(delete(Listing))
        s.commit()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    with TestClient(app) as c:
        seed()
        _clear_listings()
        yield c
        _clear_listings()


@pytest.fixture
def property_id(client):
    with Session(engine) as s:
        return str(s.exec(select(Property)).first().id)


def _create(client, property_id, **fields):
    body = {"property_id": property_id, **fields}
    return client.post("/api/v1/listings", json=body, headers=ADMIN)


def test_draft_is_not_public(client, property_id):
    r = _create(client, property_id, monthly_rent=1850, available_date="2026-12-01")
    assert r.status_code == 201
    listing = r.json()
    assert listing["status"] == "draft"
    assert listing["public_url"] is None
    assert client.get("/api/v1/public/listings", headers=PUBLIC).json() == []
    assert client.get(f"/api/v1/public/listings/{listing['id']}", headers=PUBLIC).status_code == 404


def test_publish_requires_rent_and_date(client, property_id):
    listing = _create(client, property_id).json()
    r = client.post(f"/api/v1/listings/{listing['id']}/publish", headers=ADMIN)
    assert r.status_code == 422
    assert "monthly rent" in r.json()["detail"] and "available date" in r.json()["detail"]
    assert _create(client, property_id, publish=True).status_code == 409  # still has the open draft


def test_published_listing_is_public_without_private_fields(client, property_id):
    r = _create(
        client, property_id, publish=True, monthly_rent=1850, security_deposit=1850,
        available_date="2026-12-01", pet_policy="cats_ok", internal_notes="owner wants 12mo min",
        channels=[{"channel": "zillow_rental_manager", "url": "zillow.com/x", "listed_on": "2026-11-03"}],
    )
    assert r.status_code == 201, r.text
    listing = r.json()
    assert listing["status"] == "listed"
    assert listing["listed_at"]
    assert listing["public_url"].endswith(f"/homes/{listing['id']}")
    assert listing["channels"][0]["url"] == "https://zillow.com/x"

    public = client.get("/api/v1/public/listings", headers=PUBLIC).json()
    assert [p["id"] for p in public] == [listing["id"]]
    detail = client.get(f"/api/v1/public/listings/{listing['id']}", headers=PUBLIC).json()
    assert detail["monthly_rent"] == 1850
    assert detail["time_zone"] == "America/Phoenix"
    assert detail["headline"]  # default headline generated
    for private in ("internal_notes", "channels", "owner_id", "property_id", "status"):
        assert private not in detail


def test_one_open_listing_per_property(client, property_id):
    assert _create(client, property_id).status_code == 201
    assert _create(client, property_id).status_code == 409


def test_unpublish_and_close(client, property_id):
    listing = _create(client, property_id, publish=True, monthly_rent=1800, available_date="2026-12-01").json()
    lid = listing["id"]
    assert client.post(f"/api/v1/listings/{lid}/unpublish", headers=ADMIN).json()["status"] == "draft"
    assert client.get("/api/v1/public/listings", headers=PUBLIC).json() == []

    closed = client.post(f"/api/v1/listings/{lid}/close", json={"reason": "rented"}, headers=ADMIN).json()
    assert closed["status"] == "closed" and closed["close_reason"] == "rented" and closed["closed_at"]
    assert client.patch(f"/api/v1/listings/{lid}", json={"monthly_rent": 1}, headers=ADMIN).status_code == 409
    # A closed listing frees the property for a new one.
    assert _create(client, property_id).status_code == 201


def test_live_listing_cannot_drop_required_fields(client, property_id):
    lid = _create(client, property_id, publish=True, monthly_rent=1800, available_date="2026-12-01").json()["id"]
    r = client.patch(f"/api/v1/listings/{lid}", json={"monthly_rent": None}, headers=ADMIN)
    assert r.status_code == 422


def test_photos_upload_order_and_public_visibility(client, property_id):
    lid = _create(client, property_id, monthly_rent=1800, available_date="2026-12-01").json()["id"]
    files = [("files", (f"p{i}.png", io.BytesIO(PNG), "image/png")) for i in range(3)]
    photos = client.post(f"/api/v1/listings/{lid}/photos", files=files, headers=ADMIN).json()
    ids = [p["id"] for p in photos]
    assert [p["sort_order"] for p in photos] == [0, 1, 2]

    new_order = [ids[2], ids[0], ids[1]]
    r = client.put(f"/api/v1/listings/{lid}/photos/order", json={"photo_ids": new_order}, headers=ADMIN)
    assert [p["id"] for p in r.json()] == new_order

    # Draft: photo hidden publicly.
    assert client.get(f"/api/v1/public/listings/{lid}/photos/{ids[0]}", headers=PUBLIC).status_code == 404
    client.post(f"/api/v1/listings/{lid}/publish", headers=ADMIN)
    r = client.get(f"/api/v1/public/listings/{lid}/photos/{ids[0]}", headers=PUBLIC)
    assert r.status_code == 200 and r.content == PNG
    urls = client.get(f"/api/v1/public/listings/{lid}", headers=PUBLIC).json()["photo_urls"]
    assert urls == [f"/api/v1/public/listings/{lid}/photos/{pid}" for pid in new_order]

    bad = [("files", ("x.txt", io.BytesIO(b"hi"), "text/plain"))]
    assert client.post(f"/api/v1/listings/{lid}/photos", files=bad, headers=ADMIN).status_code == 422


def test_landlord_listing_api_hidden_on_public_host(client, property_id):
    assert client.get("/api/v1/listings", headers=PUBLIC).status_code == 404


def test_property_time_zone_validation(client, property_id):
    r = client.patch(f"/api/v1/properties/{property_id}", json={"time_zone": "Mars/Olympus"}, headers=ADMIN)
    assert r.status_code == 422
    r = client.patch(f"/api/v1/properties/{property_id}", json={"time_zone": "America/Phoenix"}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["time_zone"] == "America/Phoenix"


def test_property_photo_is_cover_when_listing_has_no_photos(client, property_id):
    client.delete(f"/api/v1/properties/{property_id}/photo", headers=ADMIN)  # start with no property photo
    lid = _create(client, property_id, publish=True, monthly_rent=1800, available_date="2026-12-01").json()["id"]
    assert client.get(f"/api/v1/public/listings/{lid}", headers=PUBLIC).json()["photo_urls"] == []

    files = {"file": ("house.png", io.BytesIO(PNG), "image/png")}
    assert client.post(f"/api/v1/properties/{property_id}/photo", files=files, headers=ADMIN).status_code == 201
    try:
        urls = client.get(f"/api/v1/public/listings/{lid}", headers=PUBLIC).json()["photo_urls"]
        assert len(urls) == 1 and "/property-photo?v=" in urls[0]
        r = client.get(urls[0], headers=PUBLIC)
        assert r.status_code == 200 and r.content == PNG

        # Hidden again once the listing is no longer live.
        client.post(f"/api/v1/listings/{lid}/unpublish", headers=ADMIN)
        assert client.get(f"/api/v1/public/listings/{lid}/property-photo", headers=PUBLIC).status_code == 404
    finally:
        client.delete(f"/api/v1/properties/{property_id}/photo", headers=ADMIN)
