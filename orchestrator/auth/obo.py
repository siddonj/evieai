"""Teams SSO On-Behalf-Of (OBO) token exchange.

Feature-flagged behind ENABLE_TEAMS_SSO=true.
When enabled, exchanges a Teams-obtained access token for a Microsoft Graph token
using MSAL acquire_token_on_behalf_of, so the orchestrator can access the user's
own OneDrive, Outlook, and other Graph-backed services.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import msal


logger = logging.getLogger("orchestrator.auth.obo")

ENABLED = os.getenv("ENABLE_TEAMS_SSO", "false").lower() in ("1", "true", "yes")


@dataclass
class TeamsOBOExchange:
    """Holds credentials for the OBO token exchange."""

    tenant_id: str
    client_id: str
    client_secret: str | None = None

    @classmethod
    def from_env(cls) -> "TeamsOBOExchange":
        return cls(
            tenant_id=os.getenv("AZURE_TENANT_ID", ""),
            client_id=os.getenv("AZURE_CLIENT_ID", os.getenv("TEAMS_CLIENT_ID", "")),
            client_secret=os.getenv("AZURE_CLIENT_SECRET", os.getenv("TEAMS_CLIENT_SECRET")),
        )

    @property
    def configured(self) -> bool:
        return bool(self.tenant_id and self.client_id)

    def acquire_graph_token(self, user_assertion: str, scopes: list[str] | None = None) -> str | None:
        """Exchange a Teams user assertion for a Microsoft Graph access token.

        Args:
            user_assertion: The access token obtained from Teams SSO.
            scopes: Graph API scopes. Defaults to Mail.Read, Files.Read, User.Read.

        Returns:
            The Graph API access token, or None if exchange fails.
        """
        if not self.configured:
            logger.warning("OBO exchange not configured — skipping")
            return None

        if not user_assertion:
            logger.warning("OBO exchange called with empty user assertion")
            return None

        scopes = scopes or [
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/Files.Read",
            "https://graph.microsoft.com/User.Read",
        ]

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        client_credential = self.client_secret or {
            "client_certificate": None,
        }

        app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=client_credential,
            authority=authority,
        )

        result = app.acquire_token_on_behalf_of(
            user_assertion=user_assertion,
            scopes=scopes,
        )

        if "error" in result:
            logger.error(
                "OBO exchange failed: %s — %s",
                result.get("error"),
                result.get("error_description", ""),
            )
            return None

        token = result.get("access_token")
        if not token:
            logger.error("OBO exchange returned no access_token")
            return None

        logger.info("OBO exchange succeeded for scopes: %s", scopes)
        return token


_exchange: TeamsOBOExchange | None = None


def get_obo_exchange() -> TeamsOBOExchange | None:
    """Get or create the OBO exchange instance, respecting the feature flag."""
    global _exchange
    if not ENABLED:
        return None
    if _exchange is None:
        _exchange = TeamsOBOExchange.from_env()
    return _exchange
