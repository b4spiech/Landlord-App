"""DocuSign e-signature routing via the eSignature REST API (JWT auth).

Server-to-server JWT grant: needs an integration key, the impersonated user's
GUID, an RSA private key, and one-time admin consent for the
``signature impersonation`` scopes. Degrades gracefully (raises
``DocuSignError``) when not configured so the UI can show a clear message.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from app.config import settings


class DocuSignError(Exception):
    """Raised when DocuSign is unconfigured or an API/auth call fails."""


@dataclass
class EnvelopeSigner:
    name: str
    email: str
    anchor_string: str  # text in the PDF to place the signature line at


def _integration_key() -> str:
    return settings.DOCUSIGN_INTEGRATION_KEY or settings.DOCUSIGN_API_KEY


def is_configured() -> bool:
    return bool(
        _integration_key()
        and settings.DOCUSIGN_USER_ID
        and settings.DOCUSIGN_ACCOUNT_ID
        and settings.DOCUSIGN_PRIVATE_KEY
    )


def _authenticated_client():
    if not is_configured():
        raise DocuSignError(
            "DocuSign is not configured. Set DOCUSIGN_INTEGRATION_KEY, "
            "DOCUSIGN_USER_ID, DOCUSIGN_ACCOUNT_ID, and DOCUSIGN_PRIVATE_KEY."
        )
    try:
        from docusign_esign import ApiClient
    except ImportError as exc:  # pragma: no cover
        raise DocuSignError("docusign-esign SDK is not installed.") from exc

    client = ApiClient()
    client.set_base_path(settings.DOCUSIGN_BASE_URL)
    client.set_oauth_host_name(settings.DOCUSIGN_OAUTH_HOST)
    try:
        token = client.request_jwt_user_token(
            client_id=_integration_key(),
            user_id=settings.DOCUSIGN_USER_ID,
            oauth_host_name=settings.DOCUSIGN_OAUTH_HOST,
            private_key_bytes=settings.DOCUSIGN_PRIVATE_KEY.encode("utf-8"),
            expires_in=3600,
            scopes=["signature", "impersonation"],
        )
    except Exception as exc:  # docusign raises ApiException; surface a clean error
        # A 'consent_required' here means the integration needs one-time admin
        # consent at the DocuSign account for the impersonation scopes.
        raise DocuSignError(f"DocuSign authentication failed: {exc}") from exc

    client.set_default_header("Authorization", f"Bearer {token.access_token}")
    return client


def create_envelope_from_pdf(
    pdf_bytes: bytes,
    file_name: str,
    subject: str,
    signers: list[EnvelopeSigner],
) -> str:
    """Send a single-PDF envelope for signature; returns the envelope id."""
    if not signers:
        raise DocuSignError("At least one signer is required.")

    from docusign_esign import (
        Document,
        EnvelopeDefinition,
        EnvelopesApi,
        Recipients,
        SignHere,
        Signer,
        Tabs,
    )

    client = _authenticated_client()

    document = Document(
        document_base64=base64.b64encode(pdf_bytes).decode("utf-8"),
        name=file_name,
        file_extension="pdf",
        document_id="1",
    )

    ds_signers = []
    for i, s in enumerate(signers, start=1):
        sign_here = SignHere(
            anchor_string=s.anchor_string,
            anchor_units="pixels",
            anchor_x_offset="120",
            anchor_y_offset="-8",
        )
        ds_signers.append(
            Signer(
                email=s.email,
                name=s.name,
                recipient_id=str(i),
                routing_order="1",
                tabs=Tabs(sign_here_tabs=[sign_here]),
            )
        )

    definition = EnvelopeDefinition(
        email_subject=subject,
        documents=[document],
        recipients=Recipients(signers=ds_signers),
        status="sent",
    )

    try:
        result = EnvelopesApi(client).create_envelope(
            settings.DOCUSIGN_ACCOUNT_ID, envelope_definition=definition
        )
    except Exception as exc:
        raise DocuSignError(f"DocuSign envelope creation failed: {exc}") from exc

    return result.envelope_id


def get_envelope_status(envelope_id: str) -> str:
    client = _authenticated_client()
    from docusign_esign import EnvelopesApi

    try:
        env = EnvelopesApi(client).get_envelope(settings.DOCUSIGN_ACCOUNT_ID, envelope_id)
    except Exception as exc:
        raise DocuSignError(f"DocuSign status lookup failed: {exc}") from exc
    return env.status
