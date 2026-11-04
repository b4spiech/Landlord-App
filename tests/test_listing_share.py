"""Sharing a listing link by email/text with someone who asked about it."""

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
from app.services import email_service, sms_service

ADMIN = {"host": "dev-app.example.com"}
PUBLIC = {"host": "tours.example.com"}


def _clear():
    with Session(engine) as s:
        for m in (TourFeedback, AccessCode, NotificationLog, TourIdPhoto, TourRequest, ListingPhoto, Listing):
            s.exec(delete(m))
        s.commit()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    monkeypatch.setattr(settings, "PUBLIC_SITE_URL", "https://tours.example.com")
    sent = []

    async def fake_email(to, subject, html, attachments=None, text_body=None):
        sent.append(("email", to[0], subject, text_body, html))

    async def fake_sms(to, body):
        sent.append(("sms", to, None, body, None))
        return "SM9"

    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_email", fake_email)
    monkeypatch.setattr(sms_service, "is_configured", lambda: True)
    monkeypatch.setattr(sms_service, "send_sms", fake_sms)
    with TestClient(app) as c:
        seed()
        _clear()
        with Session(engine) as s:
            pid = str(s.exec(select(Property)).first().id)
        lid = c.post("/api/v1/listings", headers=ADMIN, json={
            "property_id": pid, "publish": True, "monthly_rent": 1850, "available_date": "2026-12-01",
            "headline": "Bright condo"}).json()["id"]
        yield c, lid, sent
        _clear()


def _share(c, lid, **body):
    return c.post(f"/api/v1/listings/{lid}/share", json=body, headers=ADMIN)


def test_email_share(env):
    c, lid, sent = env
    r = _share(c, lid, name="Sam", email=" Sam@Example.com ", note="Call me with questions.")
    assert r.status_code == 200 and r.json() == [
        {"channel": "email", "recipient": "sam@example.com", "status": "sent", "detail": None}]
    _, to, subject, text, html = sent[0]
    assert to == "sam@example.com" and "Bright condo" in subject
    assert f"https://tours.example.com/homes/{lid}" in text and f"https://tours.example.com/tour?home={lid}" in text
    assert "Hi Sam," in text and "Call me with questions." in text and "Request a tour" in html


def test_text_and_both_channels(env):
    c, lid, sent = env
    r = _share(c, lid, phone="(616) 555-0142")
    assert r.status_code == 200 and r.json()[0]["channel"] == "sms"
    r = _share(c, lid, email="a@b.co", phone="6165550142").json()
    assert [(x["channel"], x["status"]) for x in r] == [("email", "sent"), ("sms", "sent")]
    sms = next(m for m in sent if m[0] == "sms")
    assert sms[1] == "+16165550142" and f"/homes/{lid}" in sms[3] and "STOP" in sms[3]


def test_sms_failure_is_reported_email_still_sent(env, monkeypatch):
    c, lid, sent = env

    async def broken(to, body):
        raise RuntimeError("Twilio error 400: unverified number")

    monkeypatch.setattr(sms_service, "send_sms", broken)
    r = _share(c, lid, email="a@b.co", phone="6165550142").json()
    assert r[0]["status"] == "sent" and r[1]["status"] == "failed" and "unverified" in r[1]["detail"]


def test_validation_and_history(env):
    c, lid, sent = env
    assert _share(c, lid).status_code == 422
    assert _share(c, lid, email="nope").status_code == 422
    assert _share(c, lid, phone="123").status_code == 422
    _share(c, lid, email="one@example.com")
    _share(c, lid, email="two@example.com")
    history = c.get(f"/api/v1/listings/{lid}/shares", headers=ADMIN).json()
    assert [h["recipient"] for h in history] == ["two@example.com", "one@example.com"]
    c.post(f"/api/v1/listings/{lid}/unpublish", headers=ADMIN)
    assert _share(c, lid, email="x@example.com").status_code == 409
    assert c.post(f"/api/v1/listings/{lid}/share", json={"email": "a@b.co"}, headers=PUBLIC).status_code == 404
