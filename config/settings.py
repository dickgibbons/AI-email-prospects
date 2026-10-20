import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Anthropic ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# --- Google Service Account ---
SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    str(PROJECT_ROOT / "config" / "service_account.json"),
)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

# Optional: OAuth token (your Google user). Required for creating Google Docs in
# Drive — service accounts have no personal Drive quota, so Doc creation fails with
# storageQuotaExceeded. Run: python tools/setup_oauth.py (once, on a machine with a browser).
OAUTH_TOKEN_FILE = os.environ.get(
    "GOOGLE_OAUTH_TOKEN_FILE",
    str(PROJECT_ROOT / "config" / "oauth_token.json"),
)
OAUTH_CLIENT_SECRET_FILE = os.environ.get(
    "GOOGLE_OAUTH_CLIENT_SECRET_FILE",
    str(PROJECT_ROOT / "config" / "oauth_client_secret.json"),
)

# --- Google Sheet ---
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
SHEET_NAME = os.environ.get("SHEET_NAME", "Contacts")

# --- Google Drive ---
DRIVE_ROOT_FOLDER_ID = os.environ.get("DRIVE_ROOT_FOLDER_ID", "")

DRIVE_PATH_TEMPLATE = {
    "root_name": "EPAM",
    "outreach_folder": "EPAM Client Outreach",
    "existing_branch": "Client",
    "target_branch": "Target Prospect",
    "messages_folder": "Messages",
    "sender_name": "Dick Gibbons",
}

# --- Email (reminder digest only; prospect emails are never sent by this app) ---
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "dickgibbons@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
REMINDER_TO = os.environ.get("REMINDER_TO", "richard_gibbons@epam.com")
# Set to "0", "false", or "no" to skip the daily digest email entirely.
SEND_REMINDER_EMAIL = os.environ.get("SEND_REMINDER_EMAIL", "true").lower() in (
    "1",
    "true",
    "yes",
)

# --- Selection ---
MAX_PROSPECTS_PER_RUN = 20
MAX_PER_COMPANY = 3

# --- Sequence cadence (days between touches) ---
CADENCE = [3, 4, 5, 5, 5, 5]

# --- Role-based default touch counts ---
ROLE_TOUCH_DEFAULTS = {
    "c_level": 4,   # CIO, CTO, CEO, Chief*, CDO, CRO
    "vp_md": 6,     # VP, MD, Director, Head of
    "default": 5,
}

C_LEVEL_KEYWORDS = ["cio", "cto", "ceo", "cdo", "cro", "cfo", "coo", "chief"]
VP_MD_KEYWORDS = ["vp", "vice president", "md", "managing director", "director", "head of", "svp", "evp"]
