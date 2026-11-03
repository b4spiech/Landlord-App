"""Lease document parsing via Claude Sonnet 4.6 vision/PDF.

Sends an uploaded lease (PDF or image) to the Anthropic API and extracts
tenant info + comprehensive lease terms as structured JSON.
"""

from __future__ import annotations

import base64
import json

from app.config import settings
from app.schemas.lease_import import ParsedLeaseData

IMAGE_MEDIA_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}


class LeaseParserError(Exception):
    """Raised when parsing cannot be performed or fails."""


EXTRACTION_PROMPT = """\
You are extracting structured data from a residential lease document for a property
management system. Read the entire document (up to 10 pages) carefully.

Return ONLY a single JSON object (no markdown, no code fences, no commentary) with
exactly this shape:

{
  "tenants": [
    {
      "first_name": str|null, "last_name": str|null, "email": str|null,
      "phone": str|null, "date_of_birth": "YYYY-MM-DD"|null,
      "drivers_license": str|null,
      "emergency_contact_name": str|null, "emergency_contact_phone": str|null,
      "emergency_contact_relationship": str|null,
      "employer_name": str|null, "employer_phone": str|null, "job_title": str|null,
      "annual_income": number|null,
      "reference_name": str|null, "reference_phone": str|null,
      "reference_relationship": str|null
    }
  ],
  "lease": {
    "property_address": str|null, "unit_number": str|null,
    "start_date": "YYYY-MM-DD"|null, "end_date": "YYYY-MM-DD"|null,
    "monthly_rent": number|null, "security_deposit": number|null,
    "late_fee": number|null, "late_fee_grace_days": int|null,
    "rent_due_day": int|null, "payment_frequency": str|null,
    "returned_check_fee": number|null,
    "lease_type": "fixed-term"|"month-to-month"|null, "renewal_terms": str|null,
    "deposit_held_location": str|null, "deposit_interest_rate": number|null,
    "utilities_included": str|null, "utilities_tenant_responsibility": str|null,
    "occupancy_limit": int|null,
    "pets_allowed": bool|null, "pet_restrictions": str|null,
    "pet_deposit": number|null, "pet_monthly_fee": number|null,
    "parking_included": bool|null, "parking_spaces": int|null,
    "parking_additional_fee": number|null,
    "no_smoking": bool|null, "no_waterbeds": bool|null, "quiet_hours": str|null,
    "lawn_maintenance_responsibility": "landlord"|"tenant"|null,
    "trash_service_included": bool|null,
    "early_termination_allowed": bool|null, "early_termination_penalty": number|null,
    "early_termination_notice_days": int|null,
    "special_conditions": str|null
  },
  "confidence": "high"|"medium"|"low",
  "notes": str|null
}

Rules:
- Use null for anything not present in the document. Do NOT guess or invent values.
- Money values are plain numbers (1450, not "$1,450.00").
- List every tenant/co-signer found, primary tenant first.
- Do NOT extract Social Security numbers.
- Set "confidence" to your overall confidence in the extraction, and use "notes"
  to flag anything ambiguous, unreadable, or that needs human review.
"""


def _build_document_block(content: bytes, content_type: str) -> dict:
    ct = (content_type or "").lower()
    b64 = base64.standard_b64encode(content).decode("utf-8")
    if ct == "application/pdf":
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
        }
    if ct in IMAGE_MEDIA_TYPES:
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": IMAGE_MEDIA_TYPES[ct], "data": b64},
        }
    raise LeaseParserError(
        f"Unsupported file type '{content_type}'. Upload a PDF, JPG, or PNG."
    )


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of the model response (tolerates stray fences/prose)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # strip ```json ... ``` fences
        cleaned = cleaned.split("```", 2)[1] if "```" in cleaned else cleaned
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise LeaseParserError("Model did not return JSON.")
    return json.loads(cleaned[start : end + 1])


def parse_lease_document(content: bytes, content_type: str, filename: str) -> ParsedLeaseData:
    if not settings.ANTHROPIC_API_KEY:
        raise LeaseParserError(
            "Document parsing is not configured (ANTHROPIC_API_KEY is not set). "
            "You can enter the lease details manually instead."
        )

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise LeaseParserError("anthropic SDK is not installed.") from exc

    document_block = _build_document_block(content, content_type)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": [document_block, {"type": "text", "text": EXTRACTION_PROMPT}],
                }
            ],
        )
    except anthropic.APIStatusError as exc:
        raise LeaseParserError(f"Document parsing failed: {exc.message}") from exc
    except anthropic.APIError as exc:
        raise LeaseParserError(f"Document parsing failed: {exc}") from exc

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise LeaseParserError("The parser returned an empty response.")

    try:
        data = _extract_json(text)
        return ParsedLeaseData.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LeaseParserError(f"Could not parse the extracted data: {exc}") from exc
