"""Async email dispatch service.

Sends emails via aiosmtplib using Jinja2 HTML templates.
"""

import logging
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_template_env = Environment(
    loader=FileSystemLoader("templates/email"),
    autoescape=select_autoescape(["html"]),
)


def _render_template(template_name: str, context: dict[str, Any]) -> str:
    template = _template_env.get_template(template_name)
    return template.render(**context)


async def send_email(
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any] | None = None,
) -> bool:
    """Send an email. Returns True if sent, False if skipped/failed."""
    if not settings.email_enabled:
        logger.info("Email disabled — skipping send to %s: %s", to, subject)
        return False

    html_body = _render_template(template_name, context or {})

    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        message = MIMEText(html_body, "html", "utf-8")
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
            timeout=settings.smtp_timeout_seconds,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s: %s", to, subject)
        return False


async def send_welcome_email(user_email: str, user_name: str, password: str) -> bool:
    return await send_email(
        user_email,
        "Welcome to OFFSITE Studio ERP",
        "welcome.html",
        {
            "user_name": user_name,
            "password": password,
            "login_url": f"{settings.frontend_url.rstrip('/')}/login",
        },
    )


async def send_leave_status_email(
    user_email: str,
    user_name: str,
    leave_type: str,
    from_date: str,
    to_date: str,
    status: str,
    reason: str | None = None,
) -> bool:
    return await send_email(
        user_email,
        f"Leave {status.title()} — {leave_type}",
        "leave_status.html",
        {
            "user_name": user_name,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "status": status,
            "reason": reason,
        },
    )


async def send_invoice_email(
    client_email: str, client_name: str, invoice_number: str, total: str, due_date: str
) -> bool:
    return await send_email(
        client_email,
        f"Invoice {invoice_number} from OFFSITE Studio",
        "invoice_send.html",
        {
            "client_name": client_name,
            "invoice_number": invoice_number,
            "total": total,
            "due_date": due_date,
        },
    )
