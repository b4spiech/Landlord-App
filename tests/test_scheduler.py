"""Automatic door-code sends, post-tour feedback, photo-ID deletion, and the feedback form."""

import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models import (
    AccessCode, Listing, ListingPhoto, NotificationLog, Property, TourFeedback, TourIdPhoto, TourRequest,
)
from app.seed import seed
from app.services import email_service, scheduler, sms_service
from app.services.access_codes import reserve_for_tour

ADMIN = {"host": "dev-app.example.com"}
PUBLIC = {"host": "tours.example.com"}
NOW = datetime(2026, 12, 5, 17, 0, tzinfo=timezone.utc)  # 10:00 AM in Arizona


def _clear():
    with Session(engine) as s:
        for m in (TourFeedback, AccessCode, NotificationLog, TourIdPhoto, TourRequest, ListingPhoto, Listing):
            s.exec(delete(m))
        s.commit()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    monkeypatch.setattr(settings, "LANDLORD_NOTIFY_EMAIL", "owner@example.com")
    monkeypatch.setattr(settings, "LANDLORD_SMS_NUMBER", "616-555-0199")
    monkeypatch.setattr(settings, "PUBLIC_SITE_URL", "https://tours.example.com")
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
    with TestClient(app) as c:
        seed()
        _clear()
        with Session(engine) as s:
            pid = s.exec(select(Property)).first().id
            listing = Listing(property_id=pid, status="listed", monthly_rent=1850, available_date=date(2026, 12, 1))
            s.add(listing)
            s.commit()
            lid = listing.id
        yield c, pid, lid, outbox
        _clear()


def _tour(pid, lid, start, status="approved", codes=("482913",), consent=True, **extra):
    with Session(engine) as s:
        for code in codes:
            s.add(AccessCode(property_id=pid, code=code))
        req = TourRequest(
            listing_id=lid, property_id=pid, status=status, first_name="Pat", last_name="Renter",
            email="pat@example.com", phone="+16165550142", tour_start=start, tour_end=start + timedelta(minutes=30),
            time_zone="America/Phoenix", sms_consent=consent, id_photo_delete_after=start + timedelta(days=30), **extra,
        )
        s.add(req)
        s.flush()
        s.add(TourIdPhoto(tour_request_id=req.id, content=b"img", content_type="image/png"))
        if status == "approved":
            reserve_for_tour(s, req)
        s.commit()
        return req.id


def _req(rid):
    with Session(engine) as s:
        return s.get(TourRequest, rid)


def run(now):
    return asyncio.run(scheduler.run_due_jobs(now))


# --- Door codes ----------------------------------------------------------------

def test_code_sent_30_minutes_before_and_only_once(env):
    c, pid, lid, outbox = env
    rid = _tour(pid, lid, NOW + timedelta(minutes=45))
    assert run(NOW)["codes_sent"] == 0  # 45 min out: too early
    assert outbox == []
    later = NOW + timedelta(minutes=16)  # now 29 min before
    assert run(later)["codes_sent"] == 1
    assert _req(rid).code_sent_at is not None
    email = next(m for m in outbox if m[0] == "email")
    assert email[1] == "pat@example.com" and "482913" in email[3] and "take off your shoes" in email[3]
    assert any(m[0] == "sms" and "482913" in m[3] for m in outbox)
    outbox.clear()
    assert run(later + timedelta(minutes=1))["codes_sent"] == 0 and outbox == []


def test_late_approval_gets_code_right_away(env):
    c, pid, lid, outbox = env
    rid = _tour(pid, lid, NOW + timedelta(minutes=10))
    run(NOW)
    assert _req(rid).code_sent_at is not None


def test_pending_and_declined_tours_get_nothing(env):
    c, pid, lid, outbox = env
    _tour(pid, lid, NOW + timedelta(minutes=20), status="pending")
    _tour(pid, lid, NOW + timedelta(minutes=20), status="declined", codes=())
    run(NOW)
    assert outbox == []


def test_no_code_alerts_landlord_once_then_recovers(env):
    c, pid, lid, outbox = env
    rid = _tour(pid, lid, NOW + timedelta(minutes=20))
    with Session(engine) as s:  # the held code went missing
        s.exec(delete(AccessCode))
        s.commit()
    run(NOW)
    alerts = [m for m in outbox if m[1] in ("owner@example.com", "+16165550199")]
    assert len(alerts) == 2 and "ACTION NEEDED" in alerts[0][2] and "no door codes" in alerts[0][3]
    outbox.clear()
    run(NOW + timedelta(minutes=2))  # within retry wait: nothing
    assert outbox == [] and _req(rid).code_send_attempts == 1
    c.post(f"/api/v1/properties/{pid}/access-codes", json={"codes": "777888"}, headers=ADMIN)
    run(NOW + timedelta(minutes=6))
    assert _req(rid).code_sent_at is not None
    assert any("777888" in (m[3] or "") for m in outbox) and not any("ACTION" in (m[2] or "") for m in outbox)


def test_delivery_failure_retries_three_times_then_alerts(env, monkeypatch):
    c, pid, lid, outbox = env
    rid = _tour(pid, lid, NOW + timedelta(minutes=29), consent=False)

    async def broken_email(to, *a, **k):
        if to[0] == "pat@example.com":
            raise RuntimeError("mailbox unavailable")
        outbox.append(("email", to[0], a[0], k.get("text_body")))

    monkeypatch.setattr(email_service, "send_email", broken_email)
    for minutes in (0, 5, 10):
        run(NOW + timedelta(minutes=minutes))
    assert _req(rid).code_send_attempts == 3 and _req(rid).code_sent_at is None
    alerts = [m for m in outbox if "ACTION NEEDED" in (m[2] or "") or "ACTION NEEDED" in (m[3] or "")]
    assert len(alerts) == 2  # landlord email + text, once
    run(NOW + timedelta(minutes=15))
    assert _req(rid).code_send_attempts == 3  # gives up


# --- After the tour ------------------------------------------------------------

def test_completed_and_feedback_requested_an_hour_after(env):
    c, pid, lid, outbox = env
    start = NOW - timedelta(minutes=80)  # ended 50 min ago
    rid = _tour(pid, lid, start, code_sent_at=start - timedelta(minutes=30))
    assert run(NOW)["tours_completed"] == 0
    assert run(NOW + timedelta(minutes=10))["tours_completed"] == 1
    req = _req(rid)
    assert req.status == "completed" and req.completed_at and req.feedback_token and req.feedback_requested_at
    email = next(m for m in outbox if m[0] == "email")
    assert email[2].startswith("How was your tour") and f"https://tours.example.com/feedback/{req.feedback_token}" in email[3]
    outbox.clear()
    run(NOW + timedelta(minutes=20))
    assert outbox == []


def test_no_feedback_without_code_or_for_old_tours(env):
    c, pid, lid, outbox = env
    no_code = _tour(pid, lid, NOW - timedelta(hours=3))
    old = _tour(pid, lid, NOW - timedelta(days=5), codes=(), code_sent_at=NOW - timedelta(days=5))
    run(NOW)
    assert _req(no_code).status == "completed" and _req(old).status == "completed"
    assert not any(m[0] == "email" and m[1] == "pat@example.com" for m in outbox)


def test_id_photos_deleted_after_retention(env):
    c, pid, lid, outbox = env
    expired = _tour(pid, lid, NOW - timedelta(days=31), status="declined", codes=())
    kept = _tour(pid, lid, NOW - timedelta(days=10), status="declined", codes=())
    assert run(NOW)["id_photos_deleted"] == 1
    r = c.get(f"/api/v1/tour-requests/{expired}", headers=ADMIN).json()
    assert r["has_id_photo"] is False and r["id_photo_deleted_at"]
    assert c.get(f"/api/v1/tour-requests/{expired}/id-photo", headers=ADMIN).status_code == 404
    assert c.get(f"/api/v1/tour-requests/{kept}", headers=ADMIN).json()["has_id_photo"] is True


# --- Feedback form -------------------------------------------------------------

def test_feedback_form(env):
    c, pid, lid, outbox = env
    rid = _tour(pid, lid, NOW - timedelta(hours=2), code_sent_at=NOW - timedelta(hours=3))
    run(NOW)
    token = _req(rid).feedback_token
    outbox.clear()

    info = c.get(f"/api/v1/public/feedback/{token}", headers=PUBLIC).json()
    assert info["first_name"] == "Pat" and info["submitted"] is False and "Camino" in info["home"]
    assert c.post(f"/api/v1/public/feedback/{token}", json={"rating": 9, "interested": "yes"}, headers=PUBLIC).status_code == 422
    r = c.post(f"/api/v1/public/feedback/{token}", headers=PUBLIC,
               json={"rating": 4, "interested": "maybe", "liked": "Great views", "concerns": " "})
    assert r.status_code == 201
    assert c.post(f"/api/v1/public/feedback/{token}", json={"rating": 5, "interested": "yes"}, headers=PUBLIC).status_code == 409
    assert c.get(f"/api/v1/public/feedback/{token}", headers=PUBLIC).json()["submitted"] is True
    assert c.get("/api/v1/public/feedback/not-a-token", headers=PUBLIC).status_code == 404

    landlord = next(m for m in outbox if m[1] == "owner@example.com")
    assert "4/5" in landlord[2] and "Great views" in landlord[3]
    detail = c.get(f"/api/v1/tour-requests/{rid}", headers=ADMIN).json()
    assert detail["feedback"]["rating"] == 4 and detail["feedback"]["concerns"] is None
    assert "feedback_token" not in detail
