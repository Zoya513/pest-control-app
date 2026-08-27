"""Twilio WhatsApp sender."""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

TWILIO_BASE = "https://api.twilio.com/2010-04-01"


def _norm_wa(number: str) -> str:
    if not number:
        return ""
    n = number.strip()
    if n.startswith("whatsapp:"):
        return n
    if n.startswith("+"):
        return f"whatsapp:{n}"
    # Assume Indonesia default if no country code
    if n.startswith("0"):
        return f"whatsapp:+62{n[1:]}"
    return f"whatsapp:+{n}"


async def send_whatsapp(*, account_sid: str, auth_token: str, from_wa: str,
                        to: str, body: str, media_url: str = None) -> str:
    """Send WhatsApp via Twilio REST API."""
    if not account_sid or not auth_token or not from_wa:
        raise ValueError("Twilio credentials missing")
    to_wa = _norm_wa(to)
    from_wa = _norm_wa(from_wa)
    url = f"{TWILIO_BASE}/Accounts/{account_sid}/Messages.json"
    data = {"From": from_wa, "To": to_wa, "Body": body}
    if media_url:
        data["MediaUrl"] = media_url
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, data=data, auth=(account_sid, auth_token))
    if resp.status_code >= 400:
        logger.error(f"Twilio WA {resp.status_code}: {resp.text[:300]}")
        raise RuntimeError(f"Twilio error: {resp.status_code} {resp.text[:200]}")
    return resp.json().get("sid", "")


DEFAULT_SR_WA = "Halo {client_name}, Service Report {report_number} tanggal {period} telah selesai. Detail lengkap dikirim via email. — {company_name}"

DEFAULT_MR_WA = "Halo {client_name}, Laporan Bulanan periode {period} telah kami kirim ke email Anda. Ringkasan pekerjaan tersedia di dashboard. — {company_name}"
