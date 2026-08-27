"""Emergent-managed email helper (Resend under the hood).

Only server-side templates. Never accepts caller HTML.
"""
import os
import re
import ipaddress
import logging
import base64
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "PestOps Pro")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = (
    "reply with your password", "reply with the code", "send your password", "cvv",
    "send us your password", "enter your password below", "confirm your card number",
    "your full card number", "seed phrase", "recovery phrase", "verify your card",
    "social security number", "confirm your bank details"
)
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened/IP/creds URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor {m.group(1)!r} ≠ host {real!r} (G3)")


def render_report_email(*, brand_name: str, brand_address: str, recipient_name: str,
                        client_name: str, period: str, admin_message: str, report_kind: str) -> str:
    """Build server-side HTML template. admin_message is plaintext, escaped."""
    safe_msg = escape(admin_message).replace("\n", "<br/>")
    return f"""
<table role="presentation" width="100%" style="background:#f6f7fb;padding:24px 0">
  <tr><td align="center">
    <table role="presentation" width="600" style="background:#fff;border-radius:8px;font-family:Arial,sans-serif">
      <tr><td style="padding:20px 24px;border-bottom:3px solid #10B981">
        <div style="font-size:14px;color:#666">{escape(brand_name)}</div>
        <div style="font-size:20px;font-weight:700;color:#111">{escape(report_kind)}</div>
        <div style="font-size:12px;color:#666">{escape(brand_address)}</div>
      </td></tr>
      <tr><td style="padding:24px">
        <p style="margin:0 0 12px;color:#111">Dear {escape(recipient_name or client_name)},</p>
        <p style="margin:0 0 12px;color:#333">Please find attached the {escape(report_kind)} for
          <strong>{escape(client_name)}</strong> — period <strong>{escape(period)}</strong>.</p>
        <div style="margin:16px 0;padding:12px;background:#f4f7fa;border-left:3px solid #10B981;color:#333;font-size:14px">
          {safe_msg or "The report is attached to this email."}
        </div>
        <p style="margin:0 0 6px;color:#333">Should you need any clarification, please reply to this email.</p>
        <p style="margin:24px 0 4px;color:#111"><strong>{escape(brand_name)}</strong></p>
      </td></tr>
      <tr><td style="padding:14px 24px;background:#fafafa;color:#888;font-size:12px;border-top:1px solid #eee">
        Sent by {escape(brand_name)}. We never ask for your password or payment details by email.
      </td></tr>
    </table>
  </td></tr>
</table>
"""


async def send_email_with_attachments(*, to: str, subject: str, html: str,
                                      attachments: list = None,
                                      reply_to: str = None) -> str:
    """Send via Emergent proxy. attachments = [{filename, content_bytes}]."""
    if not EMAIL_KEY:
        raise HTTPException(status_code=500, detail="Email not configured (EMERGENT_EMAIL_KEY missing)")
    _assert_safe_email(subject, html)
    payload = {
        "to": [to],
        "subject": subject,
        "html": html,
        "from_name": EMAIL_FROM_NAME,
    }
    if reply_to:
        payload["contact_email"] = reply_to
    if attachments:
        payload["attachments"] = [
            {"filename": a["filename"], "content": base64.b64encode(a["content"]).decode("ascii")}
            for a in attachments
        ]
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json=payload,
            )
        resp.raise_for_status()
        return resp.json().get("id", "")
    except httpx.HTTPStatusError as e:
        logger.error(f"Email failed {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=502, detail=f"Email provider error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Email send error")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
