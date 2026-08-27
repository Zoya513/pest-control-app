"""Custom SMTP email sender with fallback to Emergent Resend."""
import os
import logging
import aiosmtplib
from email.message import EmailMessage
from typing import Optional, List
from html import escape

logger = logging.getLogger(__name__)

DEFAULT_SR_SUBJECT = "Service Report {report_number} - {client_name}"
DEFAULT_SR_BODY = """Dear {client_name},

Please find attached our Service Report {report_number} dated {period}.

Should you require any further clarification, please feel free to reach out.

Best regards,
{company_name}"""

DEFAULT_MR_SUBJECT = "Monthly Report {period} - {client_name}"
DEFAULT_MR_BODY = """Dear {client_name},

Attached is the Monthly Service Report for {period}, covering all pest control activities carried out at your premises.

The report includes:
- Client information
- Service work realization
- Employee attendance
- Pest findings historical chart
- Full Service Report attachments

Please contact us for any clarification.

Best regards,
{company_name}"""


def render_template(tpl: str, **ctx) -> str:
    """Safe placeholder replacement that ignores unknown fields."""
    try:
        return tpl.format(**{k: (v if v is not None else "") for k, v in ctx.items()})
    except (KeyError, IndexError):
        # Manually replace known placeholders, leave others literal
        out = tpl
        for k, v in ctx.items():
            out = out.replace("{" + k + "}", str(v if v is not None else ""))
        return out


def body_to_html(body: str, signature: str = "") -> str:
    """Convert plain-text body (from admin template) to safe HTML template."""
    safe = escape(body).replace("\n", "<br/>")
    sig = escape(signature).replace("\n", "<br/>")
    return f"""
<table role="presentation" width="100%" style="background:#f6f7fb;padding:24px 0">
  <tr><td align="center">
    <table role="presentation" width="600" style="background:#fff;border-radius:8px;font-family:Arial,sans-serif">
      <tr><td style="padding:24px;color:#222;line-height:1.55">{safe}
      {'<br/><br/><div style="border-top:1px solid #eee;padding-top:12px;color:#555;font-size:13px">' + sig + '</div>' if signature else ''}
      </td></tr>
    </table>
  </td></tr>
</table>
"""


async def send_via_smtp(
    *, host: str, port: int, username: str, password: str, use_tls: bool,
    from_addr: str, from_name: str, to: str, subject: str, html: str,
    attachments: List[dict] = None, reply_to: Optional[str] = None,
) -> str:
    msg = EmailMessage()
    msg["From"] = f'"{from_name}" <{from_addr}>' if from_name else from_addr
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content("This email requires an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    for a in attachments or []:
        msg.add_attachment(a["content"], maintype="application", subtype="pdf", filename=a["filename"])
    # Determine TLS/StartTLS
    if port == 465:
        await aiosmtplib.send(msg, hostname=host, port=port, username=username,
                              password=password, use_tls=True, timeout=45)
    else:
        await aiosmtplib.send(msg, hostname=host, port=port, username=username,
                              password=password, start_tls=use_tls, timeout=45)
    return f"smtp:{host}"
