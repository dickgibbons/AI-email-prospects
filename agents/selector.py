"""SelectorAgent — reads the Contacts sheet and returns up to 20 eligible prospects."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from googleapiclient.discovery import build

from config import settings
from config.google_auth import get_credentials

log = logging.getLogger(__name__)

HEADER_MAP = {
    "Name": "name",
    "Title": "title",
    "Company": "company",
    "LinkedIn URL": "linkedInUrl",
    "Linkedin URL": "linkedInUrl",
    "Target vs Existing": "targetVsExisting",
    "Intro Call Topic": "introCallTopic",
    "EPAM Footprint": "epamFootprint",
    "Internal Contact": "internalContact",
    "Notes": "notes",
    "Status": "status",
    "Max Touches": "maxTouches",
    "Last Touch Sent": "lastTouchSent",
    "Next Touch Due": "nextTouchDue",
    "Doc Link": "docLink",
    "Last Processed": "lastProcessed",
}


def _get_sheets_service():
    return build("sheets", "v4", credentials=get_credentials(), cache_discovery=False)


def _max_touches_for_role(title: str) -> int:
    t = (title or "").lower()
    if any(kw in t for kw in settings.C_LEVEL_KEYWORDS):
        return settings.ROLE_TOUCH_DEFAULTS["c_level"]
    if any(kw in t for kw in settings.VP_MD_KEYWORDS):
        return settings.ROLE_TOUCH_DEFAULTS["vp_md"]
    return settings.ROLE_TOUCH_DEFAULTS["default"]


def _parse_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def read_all_rows() -> list[dict]:
    """Return every data row from the Contacts sheet as a list of dicts."""
    svc = _get_sheets_service()
    result = (
        svc.spreadsheets()
        .values()
        .get(
            spreadsheetId=settings.SPREADSHEET_ID,
            range=f"{settings.SHEET_NAME}!A:ZZ",
        )
        .execute()
    )
    rows = result.get("values", [])
    if len(rows) < 2:
        return []

    headers = [h.strip() for h in rows[0]]
    data = []
    for row_idx, row in enumerate(rows[1:], start=2):
        padded = row + [""] * (len(headers) - len(row))
        raw = {headers[i]: padded[i] for i in range(len(headers))}
        mapped = {}
        for sheet_col, key in HEADER_MAP.items():
            mapped[key] = (raw.get(sheet_col) or "").strip()
        mapped["rowIndex"] = row_idx
        data.append(mapped)
    return data


def select_prospects(all_rows: list[dict] | None = None) -> list[dict]:
    """Filter and return up to MAX_PROSPECTS_PER_RUN prospects, max MAX_PER_COMPANY per company."""
    if all_rows is None:
        all_rows = read_all_rows()

    today = date.today().isoformat()
    eligible: list[dict] = []

    for row in all_rows:
        status = row.get("status", "")
        if status not in ("New", "In sequence"):
            continue

        next_due = row.get("nextTouchDue", "")
        if status == "In sequence" and next_due and next_due > today:
            continue

        company = row.get("company", "")
        if not company:
            continue

        last_touch = _parse_int(row.get("lastTouchSent"), 0)
        max_touches_raw = row.get("maxTouches", "")
        max_touches = (
            _parse_int(max_touches_raw)
            if max_touches_raw
            else _max_touches_for_role(row.get("title", ""))
        )

        if last_touch >= max_touches:
            continue

        row["lastTouchSent"] = last_touch
        row["maxTouches"] = max_touches
        row["nextTouchDue"] = next_due or today
        eligible.append(row)

    eligible.sort(key=lambda r: (r.get("nextTouchDue", ""), r.get("company", "")))

    by_company: dict[str, int] = {}
    selected: list[dict] = []
    for item in eligible:
        if len(selected) >= settings.MAX_PROSPECTS_PER_RUN:
            break
        co = item["company"]
        count = by_company.get(co, 0)
        if count >= settings.MAX_PER_COMPANY:
            continue
        by_company[co] = count + 1
        selected.append(item)

    log.info("Selected %d prospect(s) from %d eligible", len(selected), len(eligible))
    return selected
