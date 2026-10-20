#!/usr/bin/env python3
"""One-time setup: sign in with your Google account and save oauth_token.json.

Why: Service accounts cannot own Google Docs in personal Drive (0 quota → 403).
     OAuth runs as you, so new Docs use your storage.

Prerequisites:
  1. Google Cloud Console → APIs & Services → Credentials → Create OAuth client ID
     → Application type: **Desktop app** → Download JSON.
  2. Save it as:  config/oauth_client_secret.json
  3. On the OAuth consent screen, add your Gmail as a test user (if app is in Testing).

Then run (from project root, with venv activated):

  python tools/setup_oauth.py

A browser opens; sign in with the same Google account that owns EPAM Drive + the Sheet.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from google_auth_oauthlib.flow import InstalledAppFlow

from config import settings

SCOPES = settings.SCOPES


def main():
    secret = Path(settings.OAUTH_CLIENT_SECRET_FILE)
    if not secret.exists():
        print(f"Missing OAuth client file: {secret}")
        print("Download Desktop OAuth client JSON from Google Cloud Console and save it there.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    out = Path(settings.OAUTH_TOKEN_FILE)
    out.write_text(creds.to_json())
    print(f"Saved: {out}")
    print("Keep this file private. Add oauth_token.json to .gitignore on shared repos.")


if __name__ == "__main__":
    main()
