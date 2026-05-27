"""Azure Blob Storage helper for report uploads and downloads."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "")
STORAGE_KEY = os.getenv("AZURE_STORAGE_KEY", "")
CONTAINER = "reports"


def _get_client() -> Any | None:
    if not STORAGE_ACCOUNT or not STORAGE_KEY:
        return None
    try:
        from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

        return (BlobServiceClient(
            account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
            credential=STORAGE_KEY,
        ), generate_blob_sas, BlobSasPermissions)
    except ImportError:
        return None


def upload_report(name: str, content: bytes, content_type: str = "text/html") -> str | None:
    """Upload a report to Blob Storage. Returns the download URL or None."""
    client_tuple = _get_client()
    if not client_tuple:
        return None
    client, generate_sas, perms = client_tuple

    try:
        blob_client = client.get_blob_client(container=CONTAINER, blob=name)
        blob_client.upload_blob(content, overwrite=True, content_type=content_type)

        sas = generate_sas(
            account_name=STORAGE_ACCOUNT,
            container_name=CONTAINER,
            blob_name=name,
            permission=perms(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(days=30),
        )
        return f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{CONTAINER}/{name}?{sas}"
    except Exception:
        return None


def download_report(name: str) -> tuple[bytes, str] | None:
    """Download a report from Blob Storage. Returns (content, content_type) or None."""
    client_tuple = _get_client()
    if not client_tuple:
        return None
    client, _, _ = client_tuple

    try:
        blob_client = client.get_blob_client(container=CONTAINER, blob=name)
        props = blob_client.get_blob_properties()
        stream = blob_client.download_blob()
        return stream.readall(), props.content_type or "text/html"
    except Exception:
        return None
