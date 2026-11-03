"""Door-code inventory: loading, listing, removing, and the reserve/release/issue lifecycle."""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.config import settings
from app.database import engine
from app.main import app
from app.models import TourFeedback, AccessCode, Listing, ListingPhoto, NotificationLog, Property, TourIdPhoto, TourRequest
from app.seed import seed
from app.services.access_codes import (
    code_for_tour,
    issue_for_tour,
    parse_codes,
    release_for_tour,
    reserve_for_tour,
)

ADMIN = {"host": "dev-app.example.com"}
PUBLIC = {"host": "tours.example.com"}


def _clear():
    with Session(engine) as s:
        for model in (TourFeedback, AccessCode, NotificationLog, TourIdPhoto, TourRequest, ListingPhoto, Listing):
            s.exec(delete(model))
        s.commit()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC["host"])
    with TestClient(app) as c:
        seed()
        _clear()
        with Session(engine) as s:
            pid = s.exec(select(Property)).first().id
        yield c, pid
        _clear()


def _url(pid):
    return f"/api/v1/properties/{pid}/access-codes"


def _tour(session, pid, start=datetime(2026, 12, 5, 17, 0, tzinfo=timezone.utc)):
    listing = session.exec(select(Listing).where(Listing.property_id == pid)).first()
    if listing is None:
        listing = Listing(property_id=pid, status="listed", monthly_rent=1, available_date=date(2026, 12, 1))
        session.add(listing)
        session.flush()
    req = TourRequest(
        listing_id=listing.id, property_id=pid, first_name="Pat", last_name="Renter", email="p@example.com",
        phone="+16165550142", tour_start=start, tour_end=start + timedelta(minutes=30),
        time_zone="America/Phoenix", id_photo_delete_after=start + timedelta(days=30),
    )
    session.add(req)
    session.commit()
    return req


def test_parse_codes():
    valid, invalid = parse_codes("1234\n5678, 9012  1234\n#4321*\tab; x\n12345678901234567890123")
    assert valid == ["1234", "5678", "9012", "#4321*"]
    assert invalid == ["ab", "x", "12345678901234567890123"]


def test_add_list_and_low_stock(env):
    c, pid = env
    r = c.post(_url(pid), json={"codes": "1111\n2222\nbad!\n2222", "expires_on": "2026-12-31", "note": "Front door"},
               headers=ADMIN)
    assert r.status_code == 201
    assert r.json() == {"added": 2, "duplicates": [], "invalid": ["bad!"]}
    # Re-adding an active code is reported, not duplicated.
    assert c.post(_url(pid), json={"codes": "2222 3333"}, headers=ADMIN).json()["duplicates"] == ["2222"]

    body = c.get(_url(pid), headers=ADMIN).json()
    assert (body["available"], body["reserved"], body["issued"]) == (3, 0, 0)
    assert body["low_stock"] is False and body["low_stock_threshold"] == 3
    first = next(x for x in body["codes"] if x["code"] == "1111")
    assert first["expires_on"] == "2026-12-31" and first["note"] == "Front door"

    c.delete(f"/api/v1/access-codes/{first['id']}", headers=ADMIN)
    assert c.get(_url(pid), headers=ADMIN).json()["low_stock"] is True


def test_nothing_valid_is_rejected(env):
    c, pid = env
    assert c.post(_url(pid), json={"codes": "!! ??"}, headers=ADMIN).status_code == 422


def test_reserve_picks_soonest_valid_and_is_idempotent(env):
    c, pid = env
    c.post(_url(pid), json={"codes": "NOEXP"}, headers=ADMIN)
    c.post(_url(pid), json={"codes": "EXPIRED"}, headers=ADMIN)
    c.post(_url(pid), json={"codes": "SOON", "expires_on": "2026-12-10"}, headers=ADMIN)
    with Session(engine) as s:
        s.exec(select(AccessCode).where(AccessCode.code == "EXPIRED")).one().expires_on = date(2026, 12, 1)
        s.commit()
        req = _tour(s, pid)  # Dec 5 in Arizona
        code = reserve_for_tour(s, req)
        s.commit()
        assert code.code == "SOON" and code.status == "reserved" and code.tour_request_id == req.id
        assert reserve_for_tour(s, req).id == code.id  # same code on retry


def test_release_returns_code_to_pool(env):
    c, pid = env
    c.post(_url(pid), json={"codes": "4444"}, headers=ADMIN)
    with Session(engine) as s:
        req = _tour(s, pid)
        reserve_for_tour(s, req)
        s.commit()
        listed = c.get(_url(pid), headers=ADMIN).json()
        assert listed["reserved"] == 1 and listed["codes"][0]["tour_visitor"] == "Pat Renter"
        # Reserved codes can't be deleted out from under a tour.
        assert c.delete(f"/api/v1/access-codes/{listed['codes'][0]['id']}", headers=ADMIN).status_code == 409
        release_for_tour(s, req)
        s.commit()
        assert code_for_tour(s, req) is None
    assert c.get(_url(pid), headers=ADMIN).json()["available"] == 1


def test_issue_moves_code_to_history_and_never_reuses_it(env):
    c, pid = env
    c.post(_url(pid), json={"codes": "5555 6666"}, headers=ADMIN)
    with Session(engine) as s:
        first, second = _tour(s, pid), _tour(s, pid, datetime(2026, 12, 6, 17, 0, tzinfo=timezone.utc))
        issued = issue_for_tour(s, first)  # reserves then issues in one step
        s.commit()
        assert issued.status == "issued" and issued.issued_at
        assert issue_for_tour(s, first).id == issued.id  # idempotent
        release_for_tour(s, first)  # issued codes are never released
        s.commit()
        other = issue_for_tour(s, second)
        s.commit()
        assert other.code != issued.code
        third = _tour(s, pid, datetime(2026, 12, 7, 17, 0, tzinfo=timezone.utc))
        assert issue_for_tour(s, third) is None  # pool empty

    active = c.get(_url(pid), headers=ADMIN).json()
    assert active["codes"] == [] and active["issued"] == 2 and active["available"] == 0
    history = c.get(_url(pid), params={"history": True}, headers=ADMIN).json()["codes"]
    assert {h["code"] for h in history} == {"5555", "6666"} and all(h["status"] == "issued" for h in history)
    assert c.delete(f"/api/v1/access-codes/{history[0]['id']}", headers=ADMIN).status_code == 409
    # An issued code's digits may be loaded again later (lock regenerated it).
    assert c.post(_url(pid), json={"codes": "5555"}, headers=ADMIN).json()["added"] == 1


def test_codes_never_reachable_from_public_site(env):
    c, pid = env
    assert c.get(_url(pid), headers=PUBLIC).status_code == 404
    assert c.post(_url(pid), json={"codes": "1234"}, headers=PUBLIC).status_code == 404
