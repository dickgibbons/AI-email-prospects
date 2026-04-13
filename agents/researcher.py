"""ResearchAgent — reads company background from Drive and calls Claude for prospect research."""

from __future__ import annotations

import json
import logging
import re

import anthropic
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import settings, prompts

log = logging.getLogger(__name__)


def _get_drive_service():
    creds = Credentials.from_service_account_file(
        settings.SERVICE_ACCOUNT_FILE, scopes=settings.SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_child_folder(drive, parent_id: str, name: str) -> str | None:
    q = (
        f"'{parent_id}' in parents "
        f"and name = '{name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    resp = drive.files().list(q=q, fields="files(id, name)", pageSize=1).execute()
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def _find_company_folder(drive, company: str, target_vs_existing: str) -> str | None:
    """Walk EPAM > EPAM Client Outreach > Client|Target Prospect > Messages > [Company]."""
    cfg = settings.DRIVE_PATH_TEMPLATE
    root_id = settings.DRIVE_ROOT_FOLDER_ID
    if not root_id:
        return None

    outreach_id = _find_child_folder(drive, root_id, cfg["outreach_folder"])
    if not outreach_id:
        return None

    branch_name = (
        cfg["existing_branch"]
        if (target_vs_existing or "").lower().startswith("exist")
        else cfg["target_branch"]
    )
    branch_id = _find_child_folder(drive, outreach_id, branch_name)
    if not branch_id:
        return None

    messages_id = _find_child_folder(drive, branch_id, cfg["messages_folder"])
    if not messages_id:
        return None

    return _find_child_folder(drive, messages_id, company)


def _read_company_background(drive, company_folder_id: str) -> str:
    """Find and read a 'Company background' doc in the company folder."""
    q = (
        f"'{company_folder_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.document' "
        f"and name contains 'background' "
        f"and trashed = false"
    )
    resp = drive.files().list(q=q, fields="files(id, name)", pageSize=1).execute()
    files = resp.get("files", [])
    if not files:
        return ""

    doc_id = files[0]["id"]
    content = (
        drive.files()
        .export(fileId=doc_id, mimeType="text/plain")
        .execute()
    )
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    return content[:4000]


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def fetch_company_background(prospect: dict) -> str:
    """Return company background text from Drive, or empty string."""
    try:
        drive = _get_drive_service()
        folder_id = _find_company_folder(
            drive, prospect.get("company", ""), prospect.get("targetVsExisting", "Target")
        )
        if not folder_id:
            return ""
        return _read_company_background(drive, folder_id)
    except Exception:
        log.warning("Could not read company background for %s", prospect.get("company"), exc_info=True)
        return ""


def research_prospect(prospect: dict) -> dict:
    """Call Claude to produce research summary, subject fragment, and opening line."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    background = fetch_company_background(prospect)
    prospect_with_bg = {**prospect, "companyBackground": background}

    user_prompt = prompts.build_research_user_prompt(prospect_with_bg)

    response = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=prompts.RESEARCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text if response.content else ""
    result = _parse_json_response(text)

    if not result.get("researchSummary"):
        log.warning("Research returned no summary for %s", prospect.get("name"))
        result["researchSummary"] = text[:500]

    log.info("Research complete for %s at %s", prospect.get("name"), prospect.get("company"))
    return result
