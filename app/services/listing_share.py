"""Send a listing link to someone who asked about it (e.g. by phone)."""

from __future__ import annotations

import html
import logging
import uuid

from sqlmodel import Session

from app.models import Listing, NotificationLog, Property
from app.services import email_service, sms_service

log = logging.getLogger(__name__)
COMPANY = "APEX Element Group"
KIND = "listing_share"


def _record(session: Session, listing_id: uuid.UUID, channel: str, recipient: str, status: str, detail=None) -> dict:
    session.add(NotificationLog(listing_id=listing_id, channel=channel, audience="prospect", kind=KIND,
                                recipient=recipient, status=status, detail=(detail or "")[:2000] or None))
    session.commit()
    return {"channel": channel, "recipient": recipient, "status": status, "detail": detail}


async def share_listing(session: Session, listing: Listing, prop: Property, *, listing_url: str, tour_url: str,
                        name: str | None, email: str | None, phone: str | None, note: str | None) -> list[dict]:
    """Email and/or text the listing link. Returns one result per channel attempted."""
    greeting = f"Hi {name}," if name else "Hi,"
    where = f"{prop.address_line1}{', ' + prop.address_line2 if prop.address_line2 else ''}, {prop.city}"
    headline = listing.headline or where
    results = []

    if email:
        e = html.escape
        rent = f"${listing.monthly_rent:,.0f}/mo" if listing.monthly_rent else ""
        paragraphs = [
            f"Thanks for your interest in {where}. Here are the details and photos:",
        ]
        text = "\n\n".join([
            greeting, *paragraphs, f"{headline}{' — ' + rent if rent else ''}\n{listing_url}",
            *( [f"Note from us: {note}"] if note else [] ),
            f"Want to see it? Book a self-guided tour here:\n{tour_url}",
            f"— {COMPANY}",
        ]) + "\n"
        body = (
            "<div style='font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:15px;color:#111;line-height:1.5'>"
            f"<p>{e(greeting)}</p><p>{e(paragraphs[0])}</p>"
            f"<p><a href='{e(listing_url)}' style='font-weight:600'>{e(headline)}</a>{' — ' + e(rent) if rent else ''}</p>"
            + (f"<p>Note from us: {e(note)}</p>" if note else "")
            + "<p>Want to see it? Book a self-guided tour:</p>"
            f"<p><a href='{e(tour_url)}' style='background:#1d4ed8;color:#fff;padding:10px 18px;border-radius:6px;"
            "text-decoration:none;display:inline-block'>Request a tour</a></p>"
            f"<p>— {COMPANY}</p></div>"
        )
        if not email_service.is_configured():
            results.append(_record(session, listing.id, "email", email, "skipped", "email not configured"))
        else:
            try:
                await email_service.send_email([email], f"The home you asked about: {headline}", body, text_body=text)
                results.append(_record(session, listing.id, "email", email, "sent"))
            except Exception as exc:  # noqa: BLE001
                log.exception("Listing share email to %s failed", email)
                results.append(_record(session, listing.id, "email", email, "failed", str(exc)))

    if phone:
        body = (f"{COMPANY}: Here's the home you asked about, {where}: {listing_url} "
                "You can book a self-guided tour from that page. Reply STOP to opt out.")
        if not sms_service.is_configured():
            results.append(_record(session, listing.id, "sms", phone, "skipped", "SMS not configured"))
        else:
            try:
                sid = await sms_service.send_sms(phone, body)
                results.append(_record(session, listing.id, "sms", phone, "sent", sid))
            except Exception as exc:  # noqa: BLE001
                log.exception("Listing share SMS to %s failed", phone)
                results.append(_record(session, listing.id, "sms", phone, "failed", str(exc)))
    return results
