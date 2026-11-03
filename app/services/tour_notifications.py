"""Messages sent when a tour request is submitted. Every attempt is recorded in
notification_log; failures never break the request itself."""

from __future__ import annotations

import html
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.models import NotificationLog, Property, TourRequest
from app.services import email_service, sms_service
from app.services.sms_service import format_us_phone
from app.services.tour_scheduling import fmt_for_landlord, fmt_local, fmt_time

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
    return status


async def _email(session, req_id, audience, kind, to, subject, html_body, text_body):
    if not to:
        return _record(session, req_id, "email", audience, kind, to, "skipped", "no recipient configured")
    if not email_service.is_configured():
        return _record(session, req_id, "email", audience, kind, to, "skipped", "email not configured")
    try:
        await email_service.send_email([to], subject, html_body, text_body=text_body)
        return _record(session, req_id, "email", audience, kind, to, "sent")
    except Exception as exc:  # noqa: BLE001 - log any provider failure
        log.exception("Email %s to %s failed", kind, to)
        return _record(session, req_id, "email", audience, kind, to, "failed", str(exc))


async def _sms(session, req_id, audience, kind, to, body):
    if not to:
        return _record(session, req_id, "sms", audience, kind, to, "skipped", "no recipient configured")
    if not sms_service.is_configured():
        return _record(session, req_id, "sms", audience, kind, to, "skipped", "SMS not configured")
    try:
        sid = await sms_service.send_sms(to, body)
        return _record(session, req_id, "sms", audience, kind, to, "sent", sid)
    except Exception as exc:  # noqa: BLE001
        log.exception("SMS %s to %s failed", kind, to)
        return _record(session, req_id, "sms", audience, kind, to, "failed", str(exc))


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


# --- Decisions and the door code ---------------------------------------------

STOP = " Reply STOP to opt out."
VISIT_RULES = [
    "Please take off your shoes when you go inside.",
    "Turn off all the lights before you leave.",
    "Make sure the door is locked behind you when you go.",
]


async def _to_visitor(session: Session, req: TourRequest, kind: str, subject: str,
                      paragraphs: list[str], sms: str, bullets: list[str] | None = None,
                      highlight: str | None = None) -> bool:
    """Email the visitor (always) and text them (only with consent).

    Layout: greeting, first paragraph, optional highlighted code, optional
    bullet list, remaining paragraphs. Returns True if any channel succeeded.
    """
    e = html.escape
    first, rest = paragraphs[0], paragraphs[1:]
    text_parts = [f"Hi {req.first_name},", first]
    html_parts = [f"<p>Hi {e(req.first_name)},</p>", f"<p>{e(first)}</p>"]
    if highlight:
        text_parts.append(f"    {highlight}")
        html_parts.append(
            "<p style='font-size:28px;font-weight:700;letter-spacing:4px;font-family:monospace;"
            f"background:#f1f5f9;padding:12px 16px;border-radius:8px;display:inline-block'>{e(highlight)}</p>"
        )
    if rest and bullets:
        # The paragraph that introduces the bullets comes right before them.
        text_parts.append(rest[0])
        html_parts.append(f"<p>{e(rest[0])}</p>")
        rest = rest[1:]
    if bullets:
        text_parts.append("\n".join(f"- {b}" for b in bullets))
        html_parts.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in bullets) + "</ul>")
    text_parts += rest + [f"— {COMPANY}"]
    html_parts += [f"<p>{e(p)}</p>" for p in rest] + [f"<p>— {COMPANY}</p>"]

    statuses = [await _email(session, req.id, "visitor", kind, req.email, subject,
                             _wrap("".join(html_parts)), "\n\n".join(text_parts) + "\n")]
    if req.sms_consent:
        statuses.append(await _sms(session, req.id, "visitor", kind, req.phone, f"{COMPANY}: {sms}{STOP}"))
    return "sent" in statuses


def _note(req: TourRequest) -> list[str]:
    return [f"Note from us: {req.decision_note}"] if req.decision_note else []


async def notify_tour_approved(request_id: uuid.UUID) -> None:
    with Session(engine) as session:
        req = session.get(TourRequest, request_id)
        where = _address(session.get(Property, req.property_id))
        when = fmt_local(req.tour_start, req.time_zone)
        code_at = fmt_time(req.tour_start - timedelta(minutes=30), req.time_zone)
        await _to_visitor(
            session, req, "tour_approved", "Your tour is approved",
            [
                f"Good news! Your tour of {where} on {when} is approved.",
                f"Your one-time access code will be sent 30 minutes before your tour (around {code_at}). "
                "The code works only once, so please arrive on time.",
                *_note(req),
            ],
            f"Your tour of {where} on {when} is approved! Your one-time access code will be sent 30 "
            f"minutes before your tour. It works only once, so please be on time.",
        )


async def notify_tour_declined(request_id: uuid.UUID) -> None:
    with Session(engine) as session:
        req = session.get(TourRequest, request_id)
        where = _address(session.get(Property, req.property_id))
        when = fmt_local(req.tour_start, req.time_zone)
        await _to_visitor(
            session, req, "tour_declined", "About your tour request",
            [
                f"Thanks for your interest in {where}. Unfortunately, we can't approve your tour "
                f"request for {when}.",
                *_note(req),
                "Thank you for understanding.",
            ],
            f"Thanks for your interest in {where}. Unfortunately, we can't approve your tour request "
            f"for {when}.",
        )


async def notify_tour_cancelled(request_id: uuid.UUID) -> None:
    with Session(engine) as session:
        req = session.get(TourRequest, request_id)
        where = _address(session.get(Property, req.property_id))
        when = fmt_local(req.tour_start, req.time_zone)
        await _to_visitor(
            session, req, "tour_cancelled", "Your tour has been cancelled",
            [
                f"Your tour of {where} on {when} has been cancelled."
                + (" Please don't use the access code we sent." if req.code_sent_at
                   else " No access code will be sent."),
                *_note(req),
                "Sorry for the inconvenience.",
            ],
            f"Your tour of {where} on {when} has been cancelled.",
        )


class NoCodeAvailable(Exception):
    pass


async def send_access_code(request_id: uuid.UUID) -> str:
    """Issue this tour's door code (idempotent) and send it with the visit instructions.

    Returns the code. Raises NoCodeAvailable if the property has no usable code.
    Used by the landlord's 'Send code now' button and by the scheduler.
    """
    from app.services.access_codes import issue_for_tour  # local import avoids a cycle

    with Session(engine) as session:
        req = session.get(TourRequest, request_id)
        code = issue_for_tour(session, req)
        if code is None:
            raise NoCodeAvailable("No door codes are available for this property.")
        session.commit()
        where = _address(session.get(Property, req.property_id))
        start = fmt_time(req.tour_start, req.time_zone)
        sent = await _to_visitor(
            session, req, "access_code", f"Your one-time access code for {where}",
            [
                f"Here is your one-time access code for your {start} tour of {where}:",
                "This code works only once. Before you go:",
                "Enjoy the tour!",
            ],
            f"Your one-time access code for {where} ({start} tour): {code.code}. It works once. "
            f"Please remove your shoes inside, turn off all lights when leaving, and lock the door behind you.",
            bullets=VISIT_RULES,
            highlight=code.code,
        )
        if sent:
            req.code_sent_at = datetime.now(timezone.utc)
            session.add(req)
            session.commit()
        return code.code
