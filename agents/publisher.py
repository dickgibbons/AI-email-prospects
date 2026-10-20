"""PublisherAgent — resolves/creates Drive folders, creates a Google Doc, and updates the Sheet row."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from googleapiclient.discovery import build

from config import settings
from config.google_auth import get_credentials

log = logging.getLogger(__name__)

_folder_cache: dict[str, str] = {}

# Shared drives (Team Drives) require these flags; harmless for My Drive.
_DRIVE_KW = {"supportsAllDrives": True, "includeItemsFromAllDrives": True}


def _get_services():
    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    return drive, sheets, docs


def _find_child(drive, parent_id: str, name: str, mime: str = "application/vnd.google-apps.folder") -> str | None:
    q = (
        f"'{parent_id}' in parents "
        f"and name = '{name}' "
        f"and mimeType = '{mime}' "
        f"and trashed = false"
    )
    resp = (
        drive.files()
        .list(q=q, fields="files(id)", pageSize=1, **_DRIVE_KW)
        .execute()
    )
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def _create_folder(drive, parent_id: str, name: str) -> str:
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = drive.files().create(
        body=metadata, fields="id", supportsAllDrives=True
    ).execute()
    return folder["id"]


def _find_or_create(drive, parent_id: str, name: str) -> str:
    existing = _find_child(drive, parent_id, name)
    if existing:
        return existing
    log.info("Creating folder: %s", name)
    return _create_folder(drive, parent_id, name)


def _resolve_prospect_folder(drive, prospect: dict) -> str:
    """Walk or create: EPAM > EPAM Client Outreach > Client|Target > Messages > [Company] > Dick Gibbons."""
    company = prospect.get("company", "Unknown")
    target_vs = prospect.get("targetVsExisting", "Target")
    branch_name = (
        settings.DRIVE_PATH_TEMPLATE["existing_branch"]
        if (target_vs or "").lower().startswith("exist")
        else settings.DRIVE_PATH_TEMPLATE["target_branch"]
    )

    cache_key = f"{branch_name}:{company}"
    if cache_key in _folder_cache:
        return _folder_cache[cache_key]

    cfg = settings.DRIVE_PATH_TEMPLATE
    root_id = settings.DRIVE_ROOT_FOLDER_ID
    if not root_id:
        raise ValueError(
            "DRIVE_ROOT_FOLDER_ID is not set. Set it in .env to the Google Drive "
            "folder ID for your EPAM root folder (share that folder with the service account)."
        )

    outreach_id = _find_or_create(drive, root_id, cfg["outreach_folder"])
    branch_id = _find_or_create(drive, outreach_id, branch_name)
    messages_id = _find_or_create(drive, branch_id, cfg["messages_folder"])
    company_id = _find_or_create(drive, messages_id, company)
    sender_id = _find_or_create(drive, company_id, cfg["sender_name"])

    _folder_cache[cache_key] = sender_id
    return sender_id


def _create_google_doc(drive, docs_svc, folder_id: str, title: str, subject: str, body: str) -> str:
    """Create a Google Doc with the email content. Returns the Doc's webViewLink."""
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
        "parents": [folder_id],
    }
    doc_file = drive.files().create(
        body=file_metadata, fields="id, webViewLink", supportsAllDrives=True
    ).execute()
    doc_id = doc_file["id"]
    web_link = doc_file.get("webViewLink", "")

    content = f"Subject: {subject}\n\n{body}"
    requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
    docs_svc.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

    return web_link


def _compute_next_touch_due(touch_number: int) -> str:
    cadence = settings.CADENCE
    idx = min(touch_number - 1, len(cadence) - 1)
    days = cadence[idx] if idx >= 0 else cadence[-1]
    return (date.today() + timedelta(days=days)).isoformat()


def _update_sheet_row(sheets_svc, row_index: int, prospect: dict, doc_link: str):
    touch_number = prospect.get("lastTouchSent", 0) + 1
    next_due = _compute_next_touch_due(touch_number)
    max_touches = prospect.get("maxTouches", 5)

    new_status = "Done" if touch_number >= max_touches else "In sequence"

    values = {
        "Status": new_status,
        "Last Touch Sent": str(touch_number),
        "Next Touch Due": next_due,
        "Doc Link": doc_link,
        "Last Processed": date.today().isoformat(),
    }

    all_rows = (
        sheets_svc.spreadsheets()
        .values()
        .get(spreadsheetId=settings.SPREADSHEET_ID, range=f"{settings.SHEET_NAME}!1:1")
        .execute()
    )
    headers = all_rows.get("values", [[]])[0]

    batch_data = []
    for col_name, val in values.items():
        if col_name in headers:
            col_idx = headers.index(col_name)
            col_letter = chr(ord("A") + col_idx) if col_idx < 26 else f"A{chr(ord('A') + col_idx - 26)}"
            cell = f"{settings.SHEET_NAME}!{col_letter}{row_index}"
            batch_data.append({"range": cell, "values": [[val]]})

    if batch_data:
        sheets_svc.spreadsheets().values().batchUpdate(
            spreadsheetId=settings.SPREADSHEET_ID,
            body={"valueInputOption": "USER_ENTERED", "data": batch_data},
        ).execute()


def publish(prospect: dict, email: dict) -> str:
    """Create Drive doc and update sheet. Returns the Doc webViewLink."""
    drive, sheets_svc, docs_svc = _get_services()

    folder_id = _resolve_prospect_folder(drive, prospect)

    touch_number = prospect.get("lastTouchSent", 0) + 1
    doc_title = f"{prospect.get('name', 'Unknown')} – Touch {touch_number}"
    subject = email.get("subject", "")
    body = email.get("body", "")

    doc_link = _create_google_doc(drive, docs_svc, folder_id, doc_title, subject, body)
    log.info("Created doc: %s -> %s", doc_title, doc_link)

    _update_sheet_row(sheets_svc, prospect["rowIndex"], prospect, doc_link)
    log.info("Updated sheet row %d for %s", prospect["rowIndex"], prospect.get("name"))

    return doc_link
