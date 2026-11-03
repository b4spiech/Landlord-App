"""Customer-facing (unauthenticated) API — the ONLY API reachable on public hosts.

Everything here must be safe for anonymous internet traffic: return only data
meant for prospects, never landlord/tenant records.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["public"])

COMPANY = {
    "name": "APEX Element Group LLC",
    "contact_email": "tours@apexelementgrp.com",
}


@router.get("/site")
def site_info():
    """Company details shown in the public site header/footer and legal pages."""
    return COMPANY
