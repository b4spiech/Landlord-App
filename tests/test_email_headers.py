"""Outgoing emails carry the headers spam filters expect."""

import asyncio
from email.utils import parseaddr

import aiosmtplib

from app.config import settings
from app.services import email_service


def test_headers(monkeypatch):
    sent = {}

    async def fake_send(msg, **kwargs):
        sent["msg"] = msg

    monkeypatch.setattr(aiosmtplib, "send", fake_send)
    for k, v in {"SMTP_HOST": "smtp.example.com", "SMTP_USER": "u", "SMTP_PASSWORD": "p",
                 "SMTP_FROM": "tours@apexelementgrp.com", "SMTP_FROM_NAME": "APEX Element Group",
                 "SMTP_REPLY_TO": ""}.items():
        monkeypatch.setattr(settings, k, v)
    asyncio.run(email_service.send_email(["pat@example.com"], "Hi", "<p>Hi</p>", text_body="Hi"))
    msg = sent["msg"]
    assert parseaddr(msg["From"]) == ("APEX Element Group", "tours@apexelementgrp.com")
    assert msg["Date"] and msg["Message-ID"].endswith("@apexelementgrp.com>")
    assert msg["Reply-To"] == "tours@apexelementgrp.com"
    assert msg.get_body(("plain",)).get_content().strip() == "Hi"
