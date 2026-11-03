"""SMS via Twilio's REST API (no SDK needed)."""

from __future__ import annotations

import re

import httpx

from app.config import settings


class SmsError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER)


def normalize_us_phone(raw: str) -> str | None:
    """Return +1XXXXXXXXXX for a valid US/Canada number, else None."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] in "01" or digits[3] in "01":
        return None
    return f"+1{digits}"


def format_us_phone(e164: str) -> str:
    d = e164[-10:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}"


async def send_sms(to: str, body: str) -> str:
    """Send a text; returns the Twilio message SID."""
    if not is_configured():
        raise SmsError("SMS is not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER).")
    sid = settings.TWILIO_ACCOUNT_SID
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, settings.TWILIO_AUTH_TOKEN),
            data={"To": to, "From": settings.TWILIO_FROM_NUMBER, "Body": body},
        )
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", r.text)
        except ValueError:
            msg = r.text
        raise SmsError(f"Twilio error {r.status_code}: {msg}")
    return r.json().get("sid", "")
