"""Host gatekeeping, Cloudflare Access JWT checks, and DocuSign webhook HMAC."""

import base64
import hashlib
import hmac
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import security
from app.config import settings
from app.main import app

TEAM = "team.cloudflareaccess.com"
AUD = "test-aud"
PUBLIC = "tours.example.com"
ADMIN = "dev-app.example.com"
WEBHOOK = "/api/v1/lease-breaks/webhook/docusign"

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeJWKS:
    def get_signing_key_from_jwt(self, token):
        return type("K", (), {"key": _key.public_key()})()


def _token(**overrides):
    claims = {"aud": AUD, "iss": f"https://{TEAM}", "email": "owner@example.com", "exp": int(time.time()) + 300}
    claims.update(overrides)
    return jwt.encode(claims, _key, algorithm="RS256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_HOSTS", PUBLIC)
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCESS_ENABLED", True)
    monkeypatch.setattr(settings, "CF_ACCESS_TEAM_DOMAIN", TEAM)
    monkeypatch.setattr(settings, "CF_ACCESS_AUD", AUD)
    monkeypatch.setattr(settings, "CF_ACCESS_ALLOWED_EMAILS", "")
    monkeypatch.setattr(settings, "DOCUSIGN_WEBHOOK_SECRET", "s3cret")
    monkeypatch.setattr(security, "_jwks_client", lambda team: _FakeJWKS())
    with TestClient(app) as c:
        yield c


# --- public host --------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/v1/properties", "/api/v1/tenants", "/docs", "/openapi.json", WEBHOOK])
def test_public_host_hides_landlord_api(client, path):
    r = client.get(path, headers={"host": PUBLIC, "cf-access-jwt-assertion": _token()})
    assert r.status_code == 404


def test_public_host_serves_public_api_without_login(client):
    r = client.get("/api/v1/public/site", headers={"host": PUBLIC})
    assert r.status_code == 200
    assert r.json()["name"] == "APEX Element Group LLC"


def test_public_host_matches_case_and_port(client):
    r = client.get("/api/v1/properties", headers={"host": "TOURS.example.com:443"})
    assert r.status_code == 404


# --- landlord host ------------------------------------------------------

def test_landlord_api_requires_token(client):
    assert client.get("/api/v1/properties", headers={"host": ADMIN}).status_code == 401


def test_landlord_api_accepts_valid_token(client):
    r = client.get("/api/v1/properties", headers={"host": ADMIN, "cf-access-jwt-assertion": _token()})
    assert r.status_code == 200


def test_landlord_api_accepts_cookie(client):
    client.cookies.set("CF_Authorization", _token())
    assert client.get("/api/v1/properties", headers={"host": ADMIN}).status_code == 200


@pytest.mark.parametrize("bad", [
    {"aud": "other-app"},
    {"iss": "https://evil.cloudflareaccess.com"},
    {"exp": int(time.time()) - 10},
])
def test_landlord_api_rejects_bad_claims(client, bad):
    r = client.get("/api/v1/properties", headers={"host": ADMIN, "cf-access-jwt-assertion": _token(**bad)})
    assert r.status_code == 401


def test_landlord_api_rejects_token_signed_by_other_key(client):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode({"aud": AUD, "iss": f"https://{TEAM}", "exp": int(time.time()) + 300}, other, algorithm="RS256")
    r = client.get("/api/v1/properties", headers={"host": ADMIN, "cf-access-jwt-assertion": forged})
    assert r.status_code == 401


def test_raw_railway_host_is_treated_as_landlord(client):
    assert client.get("/api/v1/properties", headers={"host": "abc.up.railway.app"}).status_code == 401


def test_email_allow_list(client, monkeypatch):
    monkeypatch.setattr(settings, "CF_ACCESS_ALLOWED_EMAILS", "boss@example.com")
    r = client.get("/api/v1/properties", headers={"host": ADMIN, "cf-access-jwt-assertion": _token()})
    assert r.status_code == 403


def test_misconfigured_access_fails_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "CF_ACCESS_AUD", "")
    assert client.get("/api/v1/properties", headers={"host": ADMIN}).status_code == 503


def test_health_is_open(client):
    assert client.get("/health", headers={"host": ADMIN}).status_code == 200
    assert client.get("/health", headers={"host": PUBLIC}).status_code == 200


# --- DocuSign webhook -----------------------------------------------------

def _sig(body: bytes, secret="s3cret"):
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_webhook_rejects_missing_signature(client):
    assert client.post(WEBHOOK, content=b"{}", headers={"host": ADMIN}).status_code == 401


def test_webhook_rejects_wrong_signature(client):
    body = b'{"envelopeId": "x"}'
    r = client.post(WEBHOOK, content=body, headers={"host": ADMIN, "x-docusign-signature-1": _sig(body, "nope")})
    assert r.status_code == 401


def test_webhook_accepts_valid_signature_without_access_token(client):
    body = b'{"envelopeId": "does-not-exist", "status": "completed"}'
    r = client.post(WEBHOOK, content=body, headers={"host": ADMIN, "x-docusign-signature-1": _sig(body)})
    assert r.status_code == 200


def test_webhook_rejects_everything_without_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "DOCUSIGN_WEBHOOK_SECRET", "")
    body = b"{}"
    r = client.post(WEBHOOK, content=body, headers={"host": ADMIN, "x-docusign-signature-1": _sig(body, "")})
    assert r.status_code == 401
