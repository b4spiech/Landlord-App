"""Generate lease-break PDFs (buyout agreement, move-out statement).

Uses reportlab (pure Python — no system deps), so it builds reliably on
Railway. The spec's WeasyPrint approach needs cairo/pango native libs that
aren't in the deploy image.
"""

from __future__ import annotations

import io
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _money(v: float | None) -> str:
    return f"${(v or 0):,.2f}"


def _month_name(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%B")
    except ValueError:
        return ""


def _address(obj) -> str:
    parts = [
        getattr(obj, "address_line1", None),
        getattr(obj, "address_line2", None),
        ", ".join(p for p in [getattr(obj, "city", None), getattr(obj, "state", None)] if p),
        getattr(obj, "postal_code", None),
    ]
    return ", ".join(p for p in parts if p)


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("DocTitle", parent=ss["Title"], fontSize=16, spaceAfter=12))
    ss.add(ParagraphStyle("H", parent=ss["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle("Small", parent=ss["BodyText"], fontSize=9, textColor=colors.grey))
    return ss


def build_buyout_agreement_pdf(option, lease, prop, owner, tenants) -> bytes:
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        title="Early Lease Termination & Buyout Agreement",
    )
    tenant_names = ", ".join(f"{t.first_name} {t.last_name}" for t in tenants)
    move_month = _month_name(option.move_out_date)
    total_from_tenant = (option.current_month_rent or 0) + (option.cash_due_at_signing or 0)

    el = []
    el.append(Paragraph("Early Lease Termination &amp; Buyout Agreement", ss["DocTitle"]))
    el.append(Paragraph(f"Executed on {date.today():%B %d, %Y}", ss["Small"]))
    el.append(Spacer(1, 10))

    parties = [
        ["Landlord:", owner.name if owner else "—", "Property:", prop.name if prop else "—"],
        ["", _address(owner) if owner else "", "", _address(prop) if prop else ""],
        ["Tenant(s):", tenant_names or "—", "Move-out date:", option.move_out_date or "—"],
    ]
    pt = Table(parties, colWidths=[1.1 * inch, 2.5 * inch, 1.2 * inch, 2.0 * inch])
    pt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(pt)
    el.append(Spacer(1, 8))
    el.append(HRFlowable(width="100%", color=colors.lightgrey))

    el.append(Paragraph("1. Early Termination Buyout", ss["H"]))
    rows = [
        ["Monthly rent", _money(option.monthly_rent_amount)],
        [f"Buyout multiple", f"{option.buyout_multiple:g}×" if option.buyout_multiple else "—"],
        ["Buyout amount (gross)", _money(option.buyout_amount_gross)],
        ["Less: last month's rent credit", f"-{_money(option.last_month_credit)}"],
        ["Cash due from tenant at signing", _money(option.cash_due_at_signing)],
    ]
    bt = Table(rows, colWidths=[4.0 * inch, 2.0 * inch])
    bt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(bt)

    el.append(Paragraph("2. Payment Schedule", ss["H"]))
    sched = [
        [f"{move_month} 1 (standard rent)", _money(option.current_month_rent)],
        ["Upon signing (buyout, net of credit)", _money(option.cash_due_at_signing)],
        ["Total paid by tenant", _money(total_from_tenant)],
        ["Total received by landlord", _money(option.total_cash_collected)],
    ]
    st = Table(sched, colWidths=[4.0 * inch, 2.0 * inch])
    st.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(st)

    el.append(Paragraph("3. Security Deposit", ss["H"]))
    el.append(Paragraph(
        f"Security deposit held: <b>{_money(option.security_deposit_held)}</b>. "
        "This deposit is not forfeited. It is refunded per the lease and state law, "
        "less documented damage and any lease violations, following a move-out inspection. "
        "An itemized move-out statement will accompany any deductions.",
        ss["BodyText"],
    ))

    el.append(Paragraph("4. Move-out &amp; Termination", ss["H"]))
    el.append(Paragraph(
        f"Tenant(s) shall vacate and surrender the property by {option.move_out_date} (11:59 PM), "
        "return all keys/access devices, and provide a forwarding address. Upon payment of all "
        "amounts due and move-out, the lease is fully terminated with no further rent obligation.",
        ss["BodyText"],
    ))

    el.append(Spacer(1, 24))
    sigs = [["Landlord: ____________________", "Date: ___________"]]
    for t in tenants:
        sigs.append([f"Tenant ({t.first_name} {t.last_name}): ____________________", "Date: ___________"])
    sg = Table(sigs, colWidths=[4.2 * inch, 1.8 * inch])
    sg.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 14)]))
    el.append(sg)

    doc.build(el)
    return buf.getvalue()


def build_moveout_statement_pdf(option, lease, prop, tenants, deductions=None) -> bytes:
    ss = _styles()
    deductions = deductions or []
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Move-out Statement")
    tenant_names = ", ".join(f"{t.first_name} {t.last_name}" for t in tenants)
    held = option.security_deposit_held or 0
    total_ded = sum(float(d.get("amount", 0)) for d in deductions)
    refund = round(held - total_ded, 2)

    el = []
    el.append(Paragraph("Move-out Statement &amp; Security Deposit Accounting", ss["DocTitle"]))
    el.append(Paragraph(f"Property: {prop.name if prop else '—'}", ss["BodyText"]))
    el.append(Paragraph(f"Tenant(s): {tenant_names or '—'}", ss["BodyText"]))
    el.append(Paragraph(f"Move-out date: {option.move_out_date or '—'}", ss["BodyText"]))
    el.append(Spacer(1, 8))
    el.append(Paragraph("Security Deposit Refund", ss["H"]))

    rows = [["Security deposit held", _money(held)]]
    for d in deductions:
        rows.append([d.get("description", "Deduction"), f"-{_money(d.get('amount'))}"])
    rows.append(["Refund due to tenant(s)", _money(refund)])
    t = Table(rows, colWidths=[4.2 * inch, 1.8 * inch])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t)
    el.append(Spacer(1, 6))
    el.append(Paragraph(
        "Refund is issued per the lease and applicable state law following the move-out inspection.",
        ss["Small"],
    ))
    el.append(Spacer(1, 24))
    el.append(Paragraph("Landlord: ____________________   Date: ___________", ss["BodyText"]))

    doc.build(el)
    return buf.getvalue()
