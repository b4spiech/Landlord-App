"""Request gatekeeping for the two faces of the app.

One FastAPI service answers on two kinds of hostnames:

* **Public hosts** (``settings.PUBLIC_HOSTS``, e.g. tours.apexelementgrp.com):
  the customer tour site. Only the SPA, static assets, ``/health`` and
  ``/api/v1/public/*`` are reachable. Every landlord API and the API docs
  answer 404, so a public visitor can never reach landlord data.

* **Every other host** (dev-app.apexelementgrp.com, the raw *.up.railway.app
  URL, localhost): the landlord app. When ``CLOUDFLARE_ACCESS_ENABLED`` is on,
  landlord APIs require a valid Cloudflare Access JWT, so going around
  Cloudflare to the Railway URL no longer works.

The Host header can be spoofed when hitting Railway directly, but that only
ever moves a request into a *more* restricted mode: public mode exposes only
public endpoints, and landlord mode demands an Access JWT.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.config import settings

log = logging.getLogger(__name__)

PUBLIC_API_PREFIX = "/api/v1/public"
# Server-to-server callbacks that authenticate themselves (HMAC), so they
# don't carry an Access JWT.
SELF_AUTHENTICATED_PATHS = ("/api/v1/lease-breaks/webhook/docusign",)
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


def _host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0].strip().lower()


def is_public_host(request: Request) -> bool:
    return _host(request) in settings.public_hosts_list


def _is_landlord_api(path: str) -> bool:
    if path.startswith(PUBLIC_API_PREFIX + "/") or path == PUBLIC_API_PREFIX:
        return False
    return path.startswith("/api/") or path in DOCS_PATHS or path.startswith("/docs/")


def _not_found() -> JSONResponse:
    return JSONResponse({"detail": "Not Found"}, status_code=404)


@lru_cache(maxsize=1)
def _jwks_client(team_domain: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"https://{team_domain}/cdn-cgi/access/certs", cache_keys=True, lifespan=3600)


def _verify_access_jwt(token: str) -> dict:
    """Validate a Cloudflare Access JWT (signature, audience, issuer, expiry)."""
    team = settings.CF_ACCESS_TEAM_DOMAIN.strip()
    signing_key = _jwks_client(team).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.CF_ACCESS_AUD.strip(),
        issuer=f"https://{team}",
    )


async def gatekeeper(request: Request, call_next):
    path = request.url.path

    if is_public_host(request):
        if _is_landlord_api(path):
            return _not_found()
        return await call_next(request)

    if (
        settings.CLOUDFLARE_ACCESS_ENABLED
        and _is_landlord_api(path)
        and path not in SELF_AUTHENTICATED_PATHS
        and request.method != "OPTIONS"
    ):
        if not (settings.CF_ACCESS_TEAM_DOMAIN and settings.CF_ACCESS_AUD):
            # Fail closed: protection was requested but can't be checked.
            log.error("CLOUDFLARE_ACCESS_ENABLED is on but CF_ACCESS_TEAM_DOMAIN/CF_ACCESS_AUD are missing")
            return JSONResponse({"detail": "Server authentication is misconfigured."}, status_code=503)

        token = request.headers.get("cf-access-jwt-assertion") or request.cookies.get("CF_Authorization")
        if not token:
            return JSONResponse({"detail": "Authentication required."}, status_code=401)
        try:
            claims = await run_in_threadpool(_verify_access_jwt, token)
        except jwt.PyJWKClientError:
            log.exception("Could not fetch Cloudflare Access signing keys")
            return JSONResponse({"detail": "Authentication service unavailable."}, status_code=503)
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "Invalid or expired login. Refresh the page."}, status_code=401)

        allowed = settings.access_allowed_emails_list
        email = str(claims.get("email", "")).lower()
        if allowed and email not in allowed:
            return JSONResponse({"detail": "Not authorized."}, status_code=403)
        request.state.user_email = email

    return await call_next(request)
