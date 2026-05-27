from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
import msal


@dataclass
class GraphClient:
    tenant_id: str
    client_id: str
    client_secret: str
    user_upn: str

    @classmethod
    def from_env(cls) -> "GraphClient":
        return cls(
            tenant_id=os.getenv("AZURE_TENANT_ID", ""),
            client_id=os.getenv("AZURE_CLIENT_ID", ""),
            client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
            user_upn=os.getenv("AZURE_USER_ID", ""),
        )

    @property
    def configured(self) -> bool:
        return all([self.tenant_id, self.client_id, self.client_secret, self.user_upn])

    async def get_access_token(self) -> str:
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=authority,
        )

        # Cache-first token retrieval, then fallback to client credentials.
        result = app.acquire_token_silent(scopes=["https://graph.microsoft.com/.default"], account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

        token = result.get("access_token") if isinstance(result, dict) else None
        if not token:
            error = result.get("error") if isinstance(result, dict) else "unknown_error"
            desc = result.get("error_description") if isinstance(result, dict) else "No description"
            raise RuntimeError(f"Failed to acquire Graph token: {error} - {desc}")
        return token

    async def get(self, path: str) -> dict[str, Any]:
        if not self.configured:
            return {
                "configured": False,
                "path": path,
                "message": "Graph client is not configured; returning mock data.",
            }

        token = await self.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        # URL-encode the UPN in the path (# must become %23 to avoid being treated as a fragment)
        encoded_path = path.replace(self.user_upn, quote(self.user_upn, safe="@"))
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://graph.microsoft.com/v1.0{encoded_path}", headers=headers)
            response.raise_for_status()
            return response.json()
