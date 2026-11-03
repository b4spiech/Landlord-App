"""Approve / decline / cancel / send-code, and what the visitor is told."""

import asyncio
import io
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select
from zoneinfo import ZoneInfo

from app.config import settings
from app.database import engine
from app.main import app
from app.models import TourFeedback, AccessCode, Listing, ListingPhoto, NotificationLog, Property, TourIdPhoto, TourRequest
from app.routers import public_tours
from app.seed import seed
from app.services import email_service, sms_service, tour_notifications
from tests.conftest import sign_in

ADMIN = {"host": "dev-app.example.com"}
PUBLIC = {"host": "tours.example.com"}
AZ = ZoneInfo("America/Phoenix")


def _clear():
    with Session(engine) as s:
        for model in (TourFeedback, AccessCode, NotificationLog, TourIdPhoto, TourRequest, ListingPhoto, Listing):
            s.exec(delete(model))
        s.commit()


@pytest.fixture
def env(monkeypatch):
    """App with fake email/SMS that record every message; background tasks run inline."""
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    monkeypatch.setattr(settings, "LANDLORD_SMS_NUMBER", "")
    outbox = []

    async def fake_email(to, subject, html, attachments=None, text_body=None):
        outbox.append(("email", to[0], subject, text_body))

    async def fake_sms(to, body):
        outbox.append(("sms", to, None, body))
        return "SM1"

    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_email", fake_email)
    monkeypatch.setattr(sms_service, "is_configured", lambda: True)
    monkeypatch.setattr(sms_service, "send_sms", fake_sms)
    public_tours._recent.clear()
    with TestClient(app) as c:
        seed()
        _clear()
        with Session(engine) as s:
            pid = str(s.exec(select(Property)).first().id)
        lid = c.post("/api/v1/listings", headers=ADMIN, json={
            "property_id": pid, "publish": True, "monthly_rent": 1850, "available_date": "2026-12-01",
        }).json()["id"]
        yield c, pid, lid, outbox
        _clear()


def _request(c, lid, outbox, tour_time="10:00", consent=True):
    day = (datetime.now(AZ).date() + timedelta(days=3)).isoformat()
    sign_in(c, "pat@example.com")
    r = c.post("/api/v1/public/tour-requests", headers=PUBLIC, files={"id_photo": ("id.png", io.BytesIO(b"img"), "image/png")},
               data={"listing_id": lid, "first_name": "Pat", "last_name": "Renter", "email": "pat@example.com",
                     "phone": "6165550142", "tour_date": day, "tour_time": tour_time,
                     "sms_consent": "true" if consent else "false"})
    assert r.status_code == 201, r.text
    outbox.clear()  # ignore the "request received" messages
    with Session(engine) as s:
        return str(s.exec(select(TourRequest).order_by(TourRequest.created_at.desc())).first().id)


def _codes(c, pid, *codes):
    c.post(f"/api/v1/properties/{pid}/access-codes", json={"codes": " ".join(codes)}, headers=ADMIN)


def _slots(c, lid):
    day = (datetime.now(AZ).date() + timedelta(days=3)).isoformat()
    body = c.get(f"/api/v1/public/listings/{lid}/availability", params={"day": day}, headers=PUBLIC).json()
    return {s["time"]: s["available"] for s in body["slots"]}


def test_approve_requires_a_code(env):
    c, pid, lid, outbox = env
    rid = _request(c, lid, outbox)
    r = c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN)
    assert r.status_code == 409 and "No door codes" in r.json()["detail"]
    assert c.get(f"/api/v1/tour-requests/{rid}", headers=ADMIN).json()["status"] == "pending"
    assert outbox == []


def test_approve_holds_code_and_tells_visitor(env):
    c, pid, lid, outbox = env
    _codes(c, pid, "482913")
    rid = _request(c, lid, outbox)
    r = c.post(f"/api/v1/tour-requests/{rid}/approve", json={"note": "Park in space 60."}, headers=ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved" and body["decided_at"]
    assert body["access_code"] == "482913" and body["access_code_status"] == "reserved"
    assert body["code_sent_at"] is None
    email = next(m for m in outbox if m[0] == "email")
    assert email[1] == "pat@example.com" and email[2] == "Your tour is approved"
    assert "30 minutes before your tour" in email[3] and "works only once" in email[3]
    assert "Park in space 60." in email[3]
    assert "482913" not in email[3]  # the code itself is not sent yet
    sms = next(m for m in outbox if m[0] == "sms")
    assert sms[1] == "+16165550142" and "approved" in sms[3] and "STOP" in sms[3]
    # Can't approve twice.
    assert c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN).status_code == 409


def test_decline_frees_slot_and_texts_only_with_consent(env):
    c, pid, lid, outbox = env
    rid = _request(c, lid, outbox, consent=False)
    assert _slots(c, lid)["10:00"] is False
    r = c.post(f"/api/v1/tour-requests/{rid}/decline", json={"note": "The home was just rented."}, headers=ADMIN)
    assert r.json()["status"] == "declined"
    assert [m[0] for m in outbox] == ["email"]  # no consent -> no text
    assert "can't approve your tour request" in outbox[0][3] and "just rented" in outbox[0][3]
    assert _slots(c, lid)["10:00"] is True
    assert c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN).status_code == 409


def test_send_code_with_instructions_and_resend_uses_same_code(env):
    c, pid, lid, outbox = env
    _codes(c, pid, "705126")
    rid = _request(c, lid, outbox)
    # Not approved yet -> no code.
    assert c.post(f"/api/v1/tour-requests/{rid}/send-code", headers=ADMIN).status_code == 409
    c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN)
    outbox.clear()

    r = c.post(f"/api/v1/tour-requests/{rid}/send-code", headers=ADMIN).json()
    assert r["access_code"] == "705126" and r["access_code_status"] == "issued" and r["code_sent_at"]
    email = next(m for m in outbox if m[0] == "email")
    text = email[3]
    assert "705126" in text and "works only once" in text
    for rule in ("take off your shoes", "Turn off all the lights", "door is locked behind you"):
        assert rule in text
    sms = next(m for m in outbox if m[0] == "sms")
    assert "705126" in sms[3] and "shoes" in sms[3] and "lights" in sms[3] and "lock the door" in sms[3]

    outbox.clear()
    assert c.post(f"/api/v1/tour-requests/{rid}/send-code", headers=ADMIN).json()["access_code"] == "705126"
    assert any("705126" in (m[3] or "") for m in outbox)
    codes = c.get(f"/api/v1/properties/{pid}/access-codes", params={"history": True}, headers=ADMIN).json()
    assert codes["issued"] == 1 and codes["available"] == 0


def test_cancel_releases_unsent_code(env):
    c, pid, lid, outbox = env
    _codes(c, pid, "111222")
    rid = _request(c, lid, outbox)
    c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN)
    outbox.clear()
    r = c.post(f"/api/v1/tour-requests/{rid}/cancel", json={}, headers=ADMIN).json()
    assert r["status"] == "cancelled" and r["access_code"] is None
    assert c.get(f"/api/v1/properties/{pid}/access-codes", headers=ADMIN).json()["available"] == 1
    assert "has been cancelled" in outbox[0][3] and "No access code will be sent" in outbox[0][3]
    assert _slots(c, lid)["10:00"] is True


def test_cancel_after_code_sent_keeps_code_spent(env):
    c, pid, lid, outbox = env
    _codes(c, pid, "333444")
    rid = _request(c, lid, outbox)
    c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN)
    c.post(f"/api/v1/tour-requests/{rid}/send-code", headers=ADMIN)
    outbox.clear()
    c.post(f"/api/v1/tour-requests/{rid}/cancel", json={}, headers=ADMIN)
    assert "don't use the access code" in outbox[0][3]
    codes = c.get(f"/api/v1/properties/{pid}/access-codes", headers=ADMIN).json()
    assert codes["available"] == 0 and codes["issued"] == 1  # a sent code is never reused


def test_failed_send_does_not_mark_code_sent(env, monkeypatch):
    c, pid, lid, outbox = env
    _codes(c, pid, "999000")
    rid = _request(c, lid, outbox, consent=False)
    c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN)

    async def broken_email(*a, **k):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(email_service, "send_email", broken_email)
    r = c.post(f"/api/v1/tour-requests/{rid}/send-code", headers=ADMIN).json()
    assert r["code_sent_at"] is None and r["access_code_status"] == "issued"
    logs = c.get(f"/api/v1/tour-requests/{rid}/notifications", headers=ADMIN).json()
    assert any(l["kind"] == "access_code" and l["status"] == "failed" and "SMTP down" in l["detail"] for l in logs)


def test_decision_endpoints_hidden_on_public_site(env):
    c, pid, lid, outbox = env
    rid = _request(c, lid, outbox)
    for action in ("approve", "decline", "cancel", "send-code"):
        assert c.post(f"/api/v1/tour-requests/{rid}/{action}", json={}, headers=PUBLIC).status_code == 404


def test_send_access_code_raises_when_pool_empty(env):
    c, pid, lid, outbox = env
    _codes(c, pid, "555666")
    rid = _request(c, lid, outbox)
    c.post(f"/api/v1/tour-requests/{rid}/approve", json={}, headers=ADMIN)
    with Session(engine) as s:  # simulate the held code being lost
        s.exec(delete(AccessCode))
        s.commit()
    with pytest.raises(tour_notifications.NoCodeAvailable):
        asyncio.run(tour_notifications.send_access_code(rid))
