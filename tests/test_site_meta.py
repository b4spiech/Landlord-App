"""The server tells the browser which site to render, based on PUBLIC_HOSTS."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def c(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", False)
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", "dev-tours.example.com")
    with TestClient(app) as client:
        yield client


def test_public_host_gets_public_site(c):
    r = c.get("/tour", headers={"host": "dev-tours.example.com"})
    assert r.status_code == 200 and '<meta name="apex-site" content="public" />' in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_other_hosts_get_landlord_app(c):
    r = c.get("/properties", headers={"host": "dev-app.example.com"})
    assert '<meta name="apex-site" content="landlord" />' in r.text


def test_real_files_still_served(c):
    assert c.get("/favicon.svg", headers={"host": "dev-tours.example.com"}).status_code == 200
