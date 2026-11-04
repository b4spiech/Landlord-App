"""Email notifications (SMTP via aiosmtplib).

Building the email body is always available (used for the in-app preview).
Actually sending requires SMTP configuration and degrades gracefully with a
clear error otherwise — so nothing is sent unless explicitly approved AND the
server is configured.
"""

from __future__ import annotations

import html
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from app.config import settings


class EmailError(Exception):
    """Raised when email is unconfigured or sending fails."""


def is_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD and settings.SMTP_FROM)


def _money(v: float | None) -> str:
    return f"${(v or 0):,.2f}"


def build_lease_break_email(option, prop, owner, tenants) -> tuple[str, str, list[str]]:
    """Return (subject, html_body, to_emails) for a lease-break notification."""
    to_emails = [t.email for t in tenants if t.email]
    names = " & ".join(f"{t.preferred_name or t.first_name} {t.last_name}" for t in tenants) or "there"
    prop_name = prop.name if prop else "your unit"
    subject = f"Early lease termination — {prop_name}"

    if option is not None and option.option_type == "buyout":
        terms = f"""
          <p style="margin:16px 0;padding:12px 16px;border-left:4px solid #2563eb;background:#f8fafc">
            <strong>Option:</strong> {option.label}<br/>
            Buyout amount: {_money(option.buyout_amount_gross)}<br/>
            Less last month's rent credit: -{_money(option.last_month_credit)}<br/>
            <strong style="font-size:16px">Cash due at signing: {_money(option.cash_due_at_signing)}</strong>
          </p>
          <p><strong>Timeline:</strong><br/>
            • {option.final_rent_due_date or ''}: standard rent {_money(option.current_month_rent)}<br/>
            • At signing: {_money(option.cash_due_at_signing)} buyout<br/>
            • Move-out: {option.move_out_date}<br/>
            • Security deposit refunded after the move-out inspection (less any documented damage)
          </p>
        """
    else:
        terms = f"<p>Option: {option.label if option else '—'}</p>"

    html = f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px;color:#111">
  <p>Hi {names},</p>
  <p>Thank you for requesting early lease termination at <strong>{prop_name}</strong>.
     We've agreed to the following:</p>
  {terms}
  <p>Please review the attached buyout agreement. If you agree, sign and return it
     (or complete the e-signature request).</p>
  <p>Sincerely,<br/>{owner.name if owner else 'Your landlord'}</p>
</div>"""
    return subject, html, to_emails


def branded_html(body_html: str) -> str:
    """Put the APEX letterhead (logo, or the name if no logo URL) above an email body."""
    if settings.EMAIL_LOGO_URL:
        header = (
            f'<img src="{html.escape(settings.EMAIL_LOGO_URL)}" alt="APEX Element Group" width="180" '
            'style="display:block;width:180px;max-width:60%;height:auto;border:0">'
        )
    else:
        header = ('<div style="font-family:Montserrat,Arial,sans-serif;font-weight:700;font-size:20px;'
                  'color:#0B2545">APEX Element Group</div>')
    return (
        '<div style="max-width:600px;margin:0 auto">'
        f'<div style="padding:16px 0 12px;border-bottom:2px solid #2B7BE4;margin-bottom:16px">{header}</div>'
        f"{body_html}</div>"
    )


async def send_email(
    to_emails: list[str],
    subject: str,
    html_body: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
    text_body: str | None = None,
) -> None:
    if not is_configured():
        raise EmailError(
            "Email is not configured on the server. Set SMTP_HOST, SMTP_USER, "
            "SMTP_PASSWORD, and SMTP_FROM to enable sending."
        )
    if not to_emails:
        raise EmailError("No recipient email addresses.")

    try:
        import aiosmtplib
    except ImportError as exc:  # pragma: no cover
        raise EmailError("aiosmtplib is not installed.") from exc

    msg = EmailMessage()
    sender_domain = settings.SMTP_FROM.rpartition("@")[2] or None
    # Standard headers spam filters expect: a display name, Date and Message-ID
    # (the SMTP library doesn't add the last two on its own).
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM)) if settings.SMTP_FROM_NAME else settings.SMTP_FROM
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=False, usegmt=True)
    msg["Message-ID"] = make_msgid(domain=sender_domain)
    msg["Reply-To"] = settings.SMTP_REPLY_TO or settings.SMTP_FROM
    msg.set_content(text_body or "This message requires an HTML-capable email client.")
    msg.add_alternative(branded_html(html_body), subtype="html")
    for name, content, mime in attachments or []:
        maintype, _, subtype = mime.partition("/")
        msg.add_attachment(content, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=name)

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            # Port 465 (e.g. Cloudflare Email Service) uses implicit TLS;
            # 587 (e.g. Gmail) upgrades via STARTTLS.
            use_tls=settings.SMTP_PORT == 465,
            start_tls=settings.SMTP_PORT != 465,
        )
    except Exception as exc:
        raise EmailError(f"Email sending failed: {exc}") from exc
