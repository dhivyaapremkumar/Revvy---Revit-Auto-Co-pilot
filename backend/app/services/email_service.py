"""Email notification service.

Provides one function per notification type used elsewhere in the product
(welcome email on registration, password reset, compliance report summary
after a Design Generation request is confirmed/applied). All are triggered
internally by other services/routers in Phase 2 — there are no public
endpoints for this module (see PRPs/revvy-prp.md Module 7).

Provider: plain SMTP via env vars (`SMTP_HOST`, `SMTP_PORT`,
`SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`), which works with any
SMTP-compatible provider (SendGrid, Mailgun, SES SMTP endpoint, Gmail App
Passwords, etc.) without pulling in a provider-specific SDK. No secrets
are hardcoded — everything comes from `app.config.settings`.

TODO(Phase 2): swap in a dedicated provider SDK (e.g. SendGrid) via
`EMAIL_SERVICE_API_KEY` if/when one is chosen; keep this module's public
function signatures stable so callers don't need to change.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    settings = get_settings()
    return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)


def _send_sync(*, to: str, subject: str, html_body: str, text_body: str | None = None) -> None:
    """Blocking SMTP send, run off the event loop by `_send`."""
    settings = get_settings()

    if not _is_configured():
        # Development fallback: log instead of raising, so the rest of the
        # app (registration, password reset, compliance flows) keeps
        # working end-to-end even without SMTP credentials configured.
        logger.warning(
            "Email not sent (SMTP not configured): to=%s subject=%r. "
            "Set SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD env vars to enable delivery.",
            to,
            subject,
        )
        return

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM_ADDRESS
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body or "This email requires an HTML-capable client to view.")
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
        logger.info("Email sent: to=%s subject=%r", to, subject)
    except smtplib.SMTPException:
        logger.exception("Failed to send email to=%s subject=%r", to, subject)
        raise


async def _send(*, to: str, subject: str, html_body: str, text_body: str | None = None) -> None:
    """Send an email without blocking the event loop."""
    await asyncio.to_thread(_send_sync, to=to, subject=subject, html_body=html_body, text_body=text_body)


async def send_welcome_email(*, to: str, full_name: str | None = None) -> None:
    """Send the post-registration welcome email."""
    name = full_name or "there"
    subject = "Welcome to REVVY"
    html_body = (
        f"<p>Hi {name},</p>"
        "<p>Welcome to REVVY, your AI copilot for Revit and Tamil Nadu building code compliance.</p>"
        "<p>You can now sign in and start chatting, searching TNCDBR, or generating compliant designs.</p>"
    )
    await _send(to=to, subject=subject, html_body=html_body)


async def send_password_reset_email(*, to: str, reset_token: str, reset_url: str) -> None:
    """Send a password reset email containing a reset link.

    `reset_url` should already include `reset_token` as a query/path
    parameter, e.g. f"{settings.FRONTEND_URL}/reset-password?token={reset_token}".
    """
    subject = "Reset your REVVY password"
    html_body = (
        "<p>We received a request to reset your REVVY password.</p>"
        f'<p><a href="{reset_url}">Click here to reset your password</a>.</p>'
        "<p>If you didn't request this, you can safely ignore this email.</p>"
    )
    logger.debug("Password reset requested (token issued, not logged in full): to=%s", to)
    await _send(to=to, subject=subject, html_body=html_body)


async def send_compliance_report_email(
    *,
    to: str,
    revit_project_name: str,
    compliance_status: str,
    summary: str,
) -> None:
    """Send a compliance-report summary after a Design Generation request.

    Triggered by the Design Generation module once a request's
    `compliance_status` (pending | passed | failed | overridden) is
    finalized, so the user has a record outside the live Revit session.
    """
    subject = f"REVVY compliance report: {revit_project_name} ({compliance_status})"
    html_body = (
        f"<p>Compliance check for project <strong>{revit_project_name}</strong> "
        f"completed with status: <strong>{compliance_status}</strong>.</p>"
        f"<p>{summary}</p>"
    )
    await _send(to=to, subject=subject, html_body=html_body)
