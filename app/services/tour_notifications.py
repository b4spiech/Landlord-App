"""Messages sent when a tour request is submitted. Every attempt is recorded in
notification_log; failures never break the request itself."""

from __future__ import annotations

import html
import logging
import uuid

from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.models import NotificationLog, Property, TourRequest
from app.services import email_service, sms_service
from app.services.sms_service import format_us_phone
from app.services.tour_scheduling import fmt_for_landlord, fmt_local

log = logging.getLogger(__name__)
COMPANY = "APEX Element Group"


def _address(prop: Property) -> str:
    unit = f" {prop.address_line2}" if prop.address_line2 else ""
    return f"{prop.address_line1}{unit}, {prop.city}"


def _record(session: Session, req_id, channel, audience, kind, recipient, status, detail=None):
    session.add(NotificationLog(
        tour_request_id=req_id, channel=channel, audience=audience, kind=kind,
        recipient=recipient or "-", status=status, detail=(detail or "")[:2000] or None,
    ))
    session.commit()


async def _email(session, req_id, audience, kind, to, subject, html_body, text_body):
    if not to:
        return _record(session, req_id, "email", audience, kind, to, "skipped", "no recipient configured")
    if not email_service.is_configured():
        return _record(session, req_id, "email", audience, kind, to, "skipped", "email not configured")
    try:
        await email_service.send_email([to], subject, html_body, text_body=text_body)
        _record(session, req_id, "email", audience, kind, to, "sent")
    except Exception as exc:  # noqa: BLE001 - log any provider failure
        log.exception("Email %s to %s failed", kind, to)
        _record(session, req_id, "email", audience, kind, to, "failed", str(exc))


async def _sms(session, req_id, audience, kind, to, body):
    if not to:
        return _record(session, req_id, "sms", audience, kind, to, "skipped", "no recipient configured")
    if not sms_service.is_configured():
        return _record(session, req_id, "sms", audience, kind, to, "skipped", "SMS not configured")
    try:
        sid = await sms_service.send_sms(to, body)
        _record(session, req_id, "sms", audience, kind, to, "sent", sid)
    except Exception as exc:  # noqa: BLE001
        log.exception("SMS %s to %s failed", kind, to)
        _record(session, req_id, "sms", audience, kind, to, "failed", str(exc))


def _wrap(body_html: str) -> str:
    return f'<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:15px;color:#111;line-height:1.5">{body_html}</div>'


async def notify_tour_request_submitted(request_id: uuid.UUID) -> None:
    """Tell the landlord a request needs review, and confirm receipt to the visitor."""
    with Session(engine) as session:
        req = session.get(TourRequest, request_id)
        prop = session.get(Property, req.property_id)
        name = f"{req.first_name} {req.last_name}"
        when_landlord = fmt_for_landlord(req.tour_start, req.time_zone)
        when_visitor = fmt_local(req.tour_start, req.time_zone)
        where = _address(prop)
        review_url = f"{settings.LANDLORD_APP_URL.rstrip('/')}/tour-requests/{req.id}"
        e = html.escape

        # --- Landlord -------------------------------------------------------
        text = (
            f"New tour request — please review.\n\n"
            f"Home: {where}\nWhen: {when_landlord}\nName: {name}\n"
            f"Phone: {format_us_phone(req.phone)}\nEmail: {req.email}\n"
            f"Texts OK: {'yes' if req.sms_consent else 'no'}\n\nReview: {review_url}\n"
        )
        body = _wrap(
            f"<p><strong>New tour request</strong> — please review and approve or decline.</p>"
            f"<table style='border-collapse:collapse'>"
            f"<tr><td style='padding:2px 12px 2px 0;color:#666'>Home</td><td>{e(where)}</td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0;color:#666'>When</td><td><strong>{e(when_landlord)}</strong></td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0;color:#666'>Name</td><td>{e(name)}</td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0;color:#666'>Phone</td><td>{e(format_us_phone(req.phone))}</td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0;color:#666'>Email</td><td>{e(req.email)}</td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0;color:#666'>Texts OK</td><td>{'Yes' if req.sms_consent else 'No'}</td></tr>"
            f"</table>"
            f"<p style='margin-top:20px'><a href='{e(review_url)}' style='background:#2563eb;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none'>Review request &amp; photo ID</a></p>"
        )
        await _email(session, req.id, "landlord", "tour_request_received", settings.landlord_notify_email,
                     f"Tour request: {where} — {when_landlord}", body, text)
        await _sms(session, req.id, "landlord", "tour_request_received",
                   sms_service.normalize_us_phone(settings.LANDLORD_SMS_NUMBER),
                   f"New tour request: {name}, {where}, {when_landlord}. Review: {review_url}")

        # --- Visitor ----------------------------------------------------------
        text = (
            f"Hi {req.first_name},\n\nThanks for requesting a tour of {where} on {when_visitor}.\n"
            f"We'll review your request and let you know soon. If approved, your one-time access "
            f"code will be sent 30 minutes before your tour.\n\n— {COMPANY}\n"
        )
        body = _wrap(
            f"<p>Hi {e(req.first_name)},</p>"
            f"<p>Thanks for requesting a tour of <strong>{e(where)}</strong> on <strong>{e(when_visitor)}</strong>.</p>"
            f"<p>We'll review your request and let you know soon. If approved, your one-time access code "
            f"will be sent 30 minutes before your tour.</p><p>— {COMPANY}</p>"
        )
        await _email(session, req.id, "visitor", "tour_request_received", req.email,
                     "We received your tour request", body, text)
        if req.sms_consent:
            await _sms(session, req.id, "visitor", "tour_request_received", req.phone,
                       f"{COMPANY}: We received your tour request for {where} on {when_visitor}. "
                       f"We'll let you know once it's reviewed. Reply STOP to opt out.")
