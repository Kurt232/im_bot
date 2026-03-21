"""OAuth 2.0 token management for Microsoft (Outlook / Office 365).

Uses MSAL device-code flow for initial authorization, then caches
refresh tokens so the bot can run unattended.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import msal

logger = logging.getLogger(__name__)

# Scopes required for IMAP and SMTP access.
SCOPES = [
    "https://outlook.office365.com/IMAP.AccessAsUser.All",
    "https://outlook.office365.com/SMTP.Send",
]


class OAuth2Manager:
    """Acquire and cache OAuth 2.0 access tokens via MSAL."""

    def __init__(
        self,
        client_id: str,
        tenant_id: str = "consumers",
        token_cache_path: str = ".token_cache.json",
    ) -> None:
        self._client_id = client_id
        self._tenant_id = tenant_id
        self._cache_path = Path(token_cache_path)
        self._cache = msal.SerializableTokenCache()

        if self._cache_path.exists():
            self._cache.deserialize(self._cache_path.read_text())

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        self._app = msal.PublicClientApplication(
            client_id,
            authority=authority,
            token_cache=self._cache,
        )

    def _save_cache(self) -> None:
        if self._cache.has_state_changed:
            self._cache_path.write_text(self._cache.serialize())

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing or prompting as needed."""
        # 1. Try silent acquisition (cached refresh token).
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_cache()
                return result["access_token"]

        # 2. No cached token — initiate device-code flow.
        flow = self._app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Device-code flow failed: {json.dumps(flow, indent=2)}")

        # Print instructions for the user.
        print(flow["message"], file=sys.stderr, flush=True)

        result = self._app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "unknown"))
            raise RuntimeError(f"OAuth2 authentication failed: {error}")

        self._save_cache()
        logger.info("OAuth2 token acquired and cached")
        return result["access_token"]
