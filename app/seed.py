"""Idempotent database seed.

Run with::

    python -m app.seed

Creates the Arizona jurisdiction, the owner (Brad Spiech), the management
company (APEX Element Group LLC), the first property + unit, and the three core
Jinja2 templates. Re-running is safe: existing records are detected by a
natural key and skipped.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.database import create_all_tables, engine
from app.models import (
    Jurisdiction,
    LeaseTemplate,
    ManagementCompany,
    Owner,
    Property,
    Unit,
)
from app.models.enums import PropertyType, TemplateType, UnitStatus

# --- Arizona early-termination / rental rules -------------------------------
# References: Arizona Residential Landlord and Tenant Act (A.R.S. Title 33,
# Chapter 10). Security deposit cap A.R.S. 33-1321 (1.5 months). Duty to
# mitigate A.R.S. 33-1370. Early termination for military (SCRA/A.R.S. 33-1318)
# and certain domestic-violence situations is allowed without penalty.
ARIZONA_RULES = {
    "security_deposit_max_months": 1.5,
    "security_deposit_return_days": 14,  # business days
    "notice_days_lease_termination": 30,
    "notice_days_month_to_month": 30,
    "landlord_must_mitigate": True,
    "early_termination": {
        # Cap used by jurisdiction_service.validate_buyout_amount.
        "max_buyout_months": 3,
        "reletting_fee_allowed": True,
        "penalty_free_reasons": [
            "active_military_deployment",  # A.R.S. 33-1318 / SCRA
            "domestic_violence",
            "uninhabitable_premises",
        ],
        "notes": (
            "Arizona has no flat statutory early-termination fee. Landlord must "
            "make reasonable efforts to re-rent (duty to mitigate, A.R.S. 33-1370). "
            "Buyout amounts are negotiated and capped here at 3x monthly rent."
        ),
    },
    "statute_reference": "A.R.S. Title 33, Chapter 10 (Residential Landlord and Tenant Act)",
}


BUYOUT_OPTIONS_EMAIL = """\
<p>Dear {{ tenant_name }},</p>

<p>Thank you for notifying us of your intent to end your lease at
<strong>{{ property_address }}</strong> early. Your current lease runs through
<strong>{{ lease_end_date }}</strong> at a monthly rent of
<strong>${{ "%.2f"|format(monthly_rent) }}</strong>, with
<strong>{{ months_remaining }}</strong> month(s) remaining.</p>

<p>Per Arizona law and the terms of your lease, here are the options available
to resolve the early termination:</p>

<ul>
{% for option in options %}
  <li>
    <strong>{{ option.label }}</strong> &mdash;
    total cost to you: <strong>${{ "%.2f"|format(option.total_cost_to_tenant) }}</strong>.
    {% if option.description %}{{ option.description }}{% endif %}
  </li>
{% endfor %}
</ul>

<p>Please reply to let us know which option you would like to pursue. Once you
confirm, we will prepare the necessary documents for electronic signature.</p>

<p>Sincerely,<br/>
{{ management_company_name }}</p>
"""

TERMINATION_AGREEMENT = """\
<h2>LEASE TERMINATION AGREEMENT</h2>

<p>This Lease Termination Agreement ("Agreement") is entered into on
<strong>{{ agreement_date }}</strong> by and between
<strong>{{ landlord_name }}</strong> ("Landlord") and
<strong>{{ tenant_name }}</strong> ("Tenant").</p>

<p><strong>Premises:</strong> {{ property_address }}{% if unit_number %}, Unit {{ unit_number }}{% endif %}</p>

<p><strong>Original Lease Term:</strong> {{ lease_start_date }} through {{ lease_end_date }}</p>

<p>The parties agree to terminate the above-referenced lease effective
<strong>{{ termination_date }}</strong>, subject to the following terms:</p>

<ol>
  <li>Tenant shall vacate and surrender the Premises on or before {{ move_out_date }}.</li>
  <li>Tenant shall pay an early termination amount of
      <strong>${{ "%.2f"|format(buyout_amount) }}</strong>.</li>
  <li>The security deposit of ${{ "%.2f"|format(security_deposit) }} shall be
      reconciled per the move-out statement and Arizona law (A.R.S. 33-1321).</li>
  <li>Upon satisfaction of these terms, both parties release each other from
      further obligations under the lease, except those that survive termination.</li>
</ol>

<p>Landlord: ______________________________  Date: ____________</p>
<p>Tenant: ________________________________  Date: ____________</p>
"""

MOVE_OUT_STATEMENT = """\
<h2>MOVE-OUT STATEMENT</h2>

<p><strong>Tenant:</strong> {{ tenant_name }}<br/>
<strong>Premises:</strong> {{ property_address }}{% if unit_number %}, Unit {{ unit_number }}{% endif %}<br/>
<strong>Move-out date:</strong> {{ move_out_date }}<br/>
<strong>Statement date:</strong> {{ statement_date }}</p>

<h3>Security Deposit Reconciliation</h3>
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th align="left">Description</th><th align="right">Amount</th></tr>
  <tr><td>Security deposit held</td><td align="right">${{ "%.2f"|format(security_deposit) }}</td></tr>
{% for item in deductions %}
  <tr><td>{{ item.description }}</td><td align="right">-${{ "%.2f"|format(item.amount) }}</td></tr>
{% endfor %}
  <tr><td><strong>Balance {{ "due to tenant" if balance >= 0 else "owed by tenant" }}</strong></td>
      <td align="right"><strong>${{ "%.2f"|format(balance|abs) }}</strong></td></tr>
</table>

<p>This statement is provided in accordance with A.R.S. 33-1321. Any refund due
will be issued within 14 business days of move-out.</p>

<p>{{ management_company_name }}</p>
"""


def _get_or_create(session: Session, model, defaults: dict, **lookup):
    """Return (instance, created). Looks up by **lookup; creates with merged kwargs."""
    statement = select(model)
    for key, value in lookup.items():
        statement = statement.where(getattr(model, key) == value)
    existing = session.exec(statement).first()
    if existing is not None:
        return existing, False
    instance = model(**{**lookup, **defaults})
    session.add(instance)
    session.flush()  # assign PK for downstream FKs
    return instance, True


def seed() -> tuple[int, int]:
    create_all_tables()
    created = 0
    skipped = 0

    with Session(engine) as session:
        # 1. Arizona jurisdiction
        az, made = _get_or_create(
            session,
            Jurisdiction,
            defaults={
                "state_name": "Arizona",
                "name": "Arizona",
                "notice_days_month_to_month": 30,
                "notice_days_lease_termination": 30,
                "security_deposit_max_months": 1.5,
                "security_deposit_return_days": 14,
                "landlord_must_mitigate": True,
                "early_termination_rules": ARIZONA_RULES,
                "statute_reference": ARIZONA_RULES["statute_reference"],
            },
            state_code="AZ",
        )
        created += made
        skipped += not made

        # 2. Owner — Brad Spiech
        owner, made = _get_or_create(
            session,
            Owner,
            defaults={
                "email": "bspiech@gmail.com",
                "address_line1": "8719 Burlingame Ave SW",
                "city": "Byron Center",
                "state": "MI",
                "postal_code": "49315",
                "is_entity": False,
            },
            name="Brad Spiech",
        )
        created += made
        skipped += not made

        # 3. Management company — APEX Element Group LLC
        mgmt, made = _get_or_create(
            session,
            ManagementCompany,
            defaults={
                "legal_name": "APEX Element Group LLC",
                "website": "apexelementgrp.com",
                "state": "MI",
            },
            name="APEX Element Group LLC",
        )
        created += made
        skipped += not made

        # 4. Property — 6255 N Camino Pimeria Alta Unit 60
        prop, made = _get_or_create(
            session,
            Property,
            defaults={
                "name": "Camino Pimeria Alta Unit 60",
                "property_type": PropertyType.condo.value,
                "address_line2": "Unit 60",
                "city": "Tucson",
                "state": "AZ",
                "postal_code": "85718",
                "owner_id": owner.id,
                "management_company_id": mgmt.id,
                "jurisdiction_id": az.id,
            },
            address_line1="6255 N Camino Pimeria Alta",
        )
        created += made
        skipped += not made

        # 5. Unit — Unit 60
        _, made = _get_or_create(
            session,
            Unit,
            defaults={
                "status": UnitStatus.vacant.value,
            },
            property_id=prop.id,
            unit_number="60",
        )
        created += made
        skipped += not made

        # 6. Templates
        templates = [
            {
                "name": "Buyout Options Email",
                "template_type": TemplateType.buyout_options_email.value,
                "subject": "Lease Early-Termination Options for {{ property_address }}",
                "body": BUYOUT_OPTIONS_EMAIL,
                "context_schema": {
                    "tenant_name": "str",
                    "property_address": "str",
                    "lease_end_date": "str",
                    "monthly_rent": "float",
                    "months_remaining": "int",
                    "options": "list[{label,total_cost_to_tenant,description}]",
                    "management_company_name": "str",
                },
            },
            {
                "name": "Lease Termination Agreement",
                "template_type": TemplateType.termination_agreement.value,
                "subject": None,
                "body": TERMINATION_AGREEMENT,
                "context_schema": {
                    "agreement_date": "str",
                    "landlord_name": "str",
                    "tenant_name": "str",
                    "property_address": "str",
                    "unit_number": "str",
                    "lease_start_date": "str",
                    "lease_end_date": "str",
                    "termination_date": "str",
                    "move_out_date": "str",
                    "buyout_amount": "float",
                    "security_deposit": "float",
                },
            },
            {
                "name": "Move-Out Statement",
                "template_type": TemplateType.move_out_statement.value,
                "subject": None,
                "body": MOVE_OUT_STATEMENT,
                "context_schema": {
                    "tenant_name": "str",
                    "property_address": "str",
                    "unit_number": "str",
                    "move_out_date": "str",
                    "statement_date": "str",
                    "security_deposit": "float",
                    "deductions": "list[{description,amount}]",
                    "balance": "float",
                    "management_company_name": "str",
                },
            },
        ]
        for tpl in templates:
            _, made = _get_or_create(
                session,
                LeaseTemplate,
                defaults={
                    "name": tpl["name"],
                    "subject": tpl["subject"],
                    "body": tpl["body"],
                    "context_schema": tpl["context_schema"],
                    "jurisdiction_id": az.id,
                    "is_active": True,
                },
                template_type=tpl["template_type"],
                version=1,
            )
            created += made
            skipped += not made

        session.commit()

    return created, skipped


if __name__ == "__main__":
    n_created, n_skipped = seed()
    print(f"Created {n_created} records, skipped {n_skipped} (already exist).")
