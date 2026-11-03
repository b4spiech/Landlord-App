"""Public tour booking, landlord review endpoints, notifications and time-zone handling."""

import asyncio
import io
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models import AccessCode, Listing, ListingPhoto, NotificationLog, Property, TourIdPhoto, TourRequest
from app.routers import public_tours
from app.seed import seed
from app.services import email_service, sms_service, tour_notifications
from app.services.tour_scheduling import check_slot, fmt_for_landlord

ADMIN = {"host": "dev-app.example.com"}
PUBLIC = {"host": "tours.example.com"}
AZ = ZoneInfo("America/Phoenix")
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _clear():
    with Session(engine) as s:
        for model in (AccessCode, NotificationLog, TourIdPhoto, TourRequest, ListingPhoto, Listing):
            s.exec(delete(model))
        s.commit()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    notified = []

    async def fake_notify(request_id):
        notified.append(request_id)

    monkeypatch.setattr(public_tours, "notify_tour_request_submitted", fake_notify)
    public_tours._recent.clear()
    with TestClient(app) as c:
        seed()
        _clear()
        with Session(engine) as s:
            pid = str(s.exec(select(Property)).first().id)
        listing = c.post("/api/v1/listings", headers=ADMIN, json={
            "property_id": pid, "publish": True, "monthly_rent": 1850, "available_date": "2026-12-01",
        }).json()
        yield c, listing["id"], pid, notified
        _clear()


def _future_day(days=3) -> date:
    return datetime.now(AZ).date() + timedelta(days=days)


def _form(listing_id, **over):
    data = {
        "listing_id": listing_id, "first_name": "Pat", "last_name": "Renter", "email": "Pat@Example.com",
        "phone": "(616) 555-0142", "tour_date": _future_day().isoformat(), "tour_time": "10:00",
        "sms_consent": "true", "website": "",
    }
    data.update(over)
    return data


def _submit(c, listing_id, file=("id.png", PNG, "image/png"), **over):
    files = {"id_photo": (file[0], io.BytesIO(file[1]), file[2])}
    return c.post("/api/v1/public/tour-requests", data=_form(listing_id, **over), files=files, headers=PUBLIC)


def test_availability_lists_half_hour_slots(env):
    c, lid, _, _ = env
    r = c.get(f"/api/v1/public/listings/{lid}/availability", params={"day": _future_day().isoformat()}, headers=PUBLIC)
    body = r.json()
    assert body["time_zone"] == "America/Phoenix"
    times = [s["time"] for s in body["slots"]]
    assert times[0] == "08:00" and times[-1] == "19:30" and len(times) == 24
    assert all(s["available"] for s in body["slots"])
    past = c.get(f"/api/v1/public/listings/{lid}/availability", params={"day": "2020-01-01"}, headers=PUBLIC).json()
    assert not any(s["available"] for s in past["slots"])


def test_submit_stores_request_in_utc_and_notifies(env):
    c, lid, pid, notified = env
    r = _submit(c, lid)
    assert r.status_code == 201, r.text
    assert "10:00 AM MST" in r.json()["when"]
    with Session(engine) as s:
        req = s.exec(select(TourRequest)).one()
        assert req.status == "pending" and str(req.property_id) == pid
        # 10:00 Arizona (UTC-7, no DST) == 17:00 UTC.
        assert req.tour_start.astimezone(timezone.utc).time() == time(17, 0)
        assert req.tour_end - req.tour_start == timedelta(minutes=30)
        assert req.time_zone == "America/Phoenix"
        assert req.phone == "+16165550142" and req.email == "pat@example.com"
        assert req.sms_consent and req.sms_consent_text == public_tours.SMS_CONSENT_TEXT and req.sms_consent_at
        assert req.id_photo_delete_after == req.tour_end + timedelta(days=30)
        assert s.exec(select(TourIdPhoto)).one().content == PNG
        assert notified == [req.id]


def test_booked_slot_is_unavailable_and_cannot_be_double_booked(env):
    c, lid, _, _ = env
    assert _submit(c, lid).status_code == 201
    slots = c.get(f"/api/v1/public/listings/{lid}/availability",
                  params={"day": _future_day().isoformat()}, headers=PUBLIC).json()["slots"]
    assert {s["time"]: s["available"] for s in slots}["10:00"] is False
    assert _submit(c, lid, email="other@example.com").status_code == 409


@pytest.mark.parametrize("over, status", [
    ({"tour_time": "07:30"}, 422),
    ({"tour_time": "20:00"}, 422),
    ({"tour_time": "10:15"}, 422),
    ({"tour_date": (date.today() + timedelta(days=90)).isoformat()}, 422),
    ({"tour_date": "2020-01-01"}, 422),
    ({"phone": "555-0142"}, 422),
    ({"email": "not-an-email"}, 422),
    ({"first_name": "  "}, 422),
])
def test_validation(env, over, status):
    c, lid, _, _ = env
    assert _submit(c, lid, **over).status_code == status


def test_id_photo_must_be_an_image(env):
    c, lid, _, _ = env
    assert _submit(c, lid, file=("id.pdf", b"%PDF-1.4", "application/pdf")).status_code == 422


def test_unlisted_home_cannot_be_booked(env):
    c, lid, _, _ = env
    c.post(f"/api/v1/listings/{lid}/unpublish", headers=ADMIN)
    assert _submit(c, lid).status_code == 404


def test_honeypot_pretends_success_but_stores_nothing(env):
    c, lid, _, notified = env
    r = _submit(c, lid, website="http://spam")
    assert r.status_code == 201 and r.json() == {"ok": True}  # looks like success to a bot
    with Session(engine) as s:
        assert s.exec(select(TourRequest)).all() == []
    assert notified == []


def test_rate_limit(env, monkeypatch):
    c, lid, _, _ = env
    monkeypatch.setattr(public_tours, "RATE_LIMIT", 2)
    assert _submit(c, lid, tour_time="09:00").status_code == 201
    assert _submit(c, lid, tour_time="09:30").status_code == 201
    assert _submit(c, lid, tour_time="11:00").status_code == 429


def test_landlord_review_endpoints(env):
    c, lid, _, _ = env
    _submit(c, lid)
    rows = c.get("/api/v1/tour-requests", headers=ADMIN).json()
    assert len(rows) == 1
    req = rows[0]
    assert req["property_name"] and req["has_id_photo"] and req["status"] == "pending"
    assert "MST" in req["when_display"] and "your time" in req["when_display"]
    assert "user_agent" not in req
    photo = c.get(f"/api/v1/tour-requests/{req['id']}/id-photo", headers=ADMIN)
    assert photo.content == PNG and photo.headers["cache-control"] == "no-store"
    assert c.get("/api/v1/tour-requests", params={"status_filter": "approved"}, headers=ADMIN).json() == []
    # Never reachable from the public site.
    assert c.get("/api/v1/tour-requests", headers=PUBLIC).status_code == 404
    assert c.get(f"/api/v1/tour-requests/{req['id']}/id-photo", headers=PUBLIC).status_code == 404


def test_notifications_sent_and_logged(env, monkeypatch):
    c, lid, _, _ = env
    _submit(c, lid)
    _submit(c, lid, tour_time="11:00", sms_consent="false", email="nosms@example.com")
    sent = {"email": [], "sms": []}

    async def fake_email(to, subject, html, attachments=None, text_body=None):
        sent["email"].append((to[0], subject))

    async def fake_sms(to, body):
        sent["sms"].append((to, body))
        return "SM123"

    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_email", fake_email)
    monkeypatch.setattr(sms_service, "is_configured", lambda: True)
    monkeypatch.setattr(sms_service, "send_sms", fake_sms)
    monkeypatch.setattr(settings, "LANDLORD_NOTIFY_EMAIL", "")
    monkeypatch.setattr(settings, "CF_ACCESS_ALLOWED_EMAILS", "owner@example.com")
    monkeypatch.setattr(settings, "LANDLORD_SMS_NUMBER", "616-555-0199")

    with Session(engine) as s:
        with_sms, without_sms = sorted(s.exec(select(TourRequest)).all(), key=lambda r: r.tour_start)
    asyncio.run(tour_notifications.notify_tour_request_submitted(with_sms.id))
    asyncio.run(tour_notifications.notify_tour_request_submitted(without_sms.id))

    assert [to for to, _ in sent["email"]] == ["owner@example.com", "pat@example.com",
                                               "owner@example.com", "nosms@example.com"]
    # Landlord texted for both; visitor texted only when they consented.
    assert [to for to, _ in sent["sms"]] == ["+16165550199", "+16165550142", "+16165550199"]
    assert "STOP" in sent["sms"][1][1]
    with Session(engine) as s:
        logs = s.exec(select(NotificationLog).where(NotificationLog.tour_request_id == with_sms.id)).all()
        assert {(l.channel, l.audience, l.status) for l in logs} == {
            ("email", "landlord", "sent"), ("sms", "landlord", "sent"),
            ("email", "visitor", "sent"), ("sms", "visitor", "sent"),
        }
    notes = c.get(f"/api/v1/tour-requests/{with_sms.id}/notifications", headers=ADMIN).json()
    assert len(notes) == 4


def test_unconfigured_channels_are_skipped_not_failed(env, monkeypatch):
    c, lid, _, _ = env
    _submit(c, lid)
    monkeypatch.setattr(email_service, "is_configured", lambda: False)
    monkeypatch.setattr(sms_service, "is_configured", lambda: False)
    with Session(engine) as s:
        rid = s.exec(select(TourRequest)).one().id
    asyncio.run(tour_notifications.notify_tour_request_submitted(rid))
    with Session(engine) as s:
        logs = s.exec(select(NotificationLog)).all()
        assert logs and all(l.status == "skipped" for l in logs)


def test_landlord_time_shows_michigan_offset():
    winter = datetime(2026, 12, 5, 17, 0, tzinfo=timezone.utc)  # 10:00 MST / 12:00 EST
    assert fmt_for_landlord(winter, "America/Phoenix") == "Sat, Dec 5 at 10:00 AM MST (12:00 PM EST your time)"
    summer = datetime(2026, 7, 4, 17, 0, tzinfo=timezone.utc)  # 10:00 MST / 1:00 EDT
    assert fmt_for_landlord(summer, "America/Phoenix") == "Sat, Jul 4 at 10:00 AM MST (1:00 PM EDT your time)"
    assert "your time" not in fmt_for_landlord(winter, "America/Detroit")


def test_minimum_lead_time():
    now = datetime(2026, 12, 5, 16, 0, tzinfo=timezone.utc)  # 9:00 AM in Arizona
    assert check_slot(date(2026, 12, 5), time(10, 0), "America/Phoenix", now)  # only 1 hour away
    assert check_slot(date(2026, 12, 5), time(11, 0), "America/Phoenix", now) is None


def test_sms_consent_text_matches_frontend():
    src = (Path(__file__).parents[1] / "frontend/src/public/company.ts").read_text()
    block = src[src.index("SMS_CONSENT_TEXT ="):]
    block = block[: block.index(";")]
    parts = re.findall(r"[`'](.*?)[`']", block, re.S)
    text = "".join(parts).replace("${COMPANY.legalName}", "APEX Element Group LLC")
    assert text == public_tours.SMS_CONSENT_TEXT
