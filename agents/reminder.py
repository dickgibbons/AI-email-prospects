"""ReminderAgent — queries the Sheet for today's follow-ups and sends a Gmail digest."""

from __future__ import annotations

import logging
import smtplib
from datetime import date
from email.mime.text import MIMEText

from agents.selector import read_all_rows
from config import settings

log = logging.getLogger(__name__)


def _build_reminder_body(due_rows: list[dict]) -> str:
    if not due_rows:
        return "No follow-ups due today."

    lines = [f"Follow-ups due today ({date.today().isoformat()}):\n"]
    for r in due_rows:
        name = r.get("name", "")
        company = r.get("company", "")
        touch = r.get("lastTouchSent", "?")
        doc_link = r.get("docLink", "")
        line = f"  - {name} | {company} | Touch {touch}"
        if doc_link:
            line += f" | {doc_link}"
        lines.append(line)

    lines.append(f"\nTotal: {len(due_rows)} prospect(s).")
    return "\n".join(lines)


def get_due_today(all_rows: list[dict] | None = None) -> list[dict]:
    if all_rows is None:
        all_rows = read_all_rows()

    today = date.today().isoformat()
    return [
        r
        for r in all_rows
        if r.get("status") in ("In sequence",)
        and r.get("nextTouchDue", "") == today
    ]


def send_reminder(due_rows: list[dict] | None = None):
    """Send reminder email via Gmail SMTP."""
    if due_rows is None:
        due_rows = get_due_today()

    body_text = _build_reminder_body(due_rows)

    msg = MIMEText(body_text, "plain")
    msg["Subject"] = f"EPAM Outreach – Follow up today ({date.today().isoformat()})"
    msg["From"] = settings.GMAIL_ADDRESS
    msg["To"] = settings.REMINDER_TO

    if not settings.GMAIL_APP_PASSWORD:
        log.warning("GMAIL_APP_PASSWORD not set; skipping email send. Body:\n%s", body_text)
        return

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

    log.info("Reminder sent to %s (%d prospects due)", settings.REMINDER_TO, len(due_rows))
