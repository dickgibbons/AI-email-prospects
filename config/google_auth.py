"""Load Google credentials: OAuth user token if present, else service account."""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

from config import settings

log = logging.getLogger(__name__)


def get_credentials():
    """Prefer OAuth user credentials (Drive/Docs/Sheets use your storage)."""
    token_path = Path(settings.OAUTH_TOKEN_FILE)
    if token_path.exists():
        creds = UserCredentials.from_authorized_user_file(
            str(token_path), settings.SCOPES
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        log.debug("Using OAuth user credentials from %s", token_path)
        return creds

    return ServiceAccountCredentials.from_service_account_file(
        settings.SERVICE_ACCOUNT_FILE, scopes=settings.SCOPES
    )
