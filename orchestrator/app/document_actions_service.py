from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import httpx

try:
    from app.actions_store import ActionsStore
    from app.blob import DOCUMENT_ARTIFACT_ROOT, upload_report, write_local_document_artifact
    from app.document_actions_store import DocumentActionsStore
except ImportError:
    from orchestrator.app.actions_store import ActionsStore
    from orchestrator.app.blob import DOCUMENT_ARTIFACT_ROOT, upload_report, write_local_document_artifact
    from orchestrator.app.document_actions_store import DocumentActionsStore


class DocumentActionsService:
    def __init__(
        self,
        store: DocumentActionsStore,
        artifact_root: Path | str | None = None,
        actions_store: ActionsStore | None = None,
    ) -> None:
        self.store = store
        self.artifact_root = Path(artifact_root or os.getenv("DOCUMENT_ARTIFACT_ROOT", DOCUMENT_ARTIFACT_ROOT))
        self.actions_store = actions_store
        self.document_export_base_url = self._resolve_document_export_base_url()

    def create_draft(
        self,
        *,
        user_id: str,
        work_packet_id: str,
        document_type: str,
        title: str,
        source_summary: str,
    ) -> dict[str, Any]:
        draft_markdown = f"# {title}\n\n## Summary\n\n{source_summary}\n"
        return self.store.create_draft(
            user_id=user_id,
            work_packet_id=work_packet_id,
            document_type=document_type,
            title=title,
            draft_markdown=draft_markdown,
        )

    def approve(
        self,
        *,
        document_action_id: int,
        approved_by: str,
        destination_type: str,
        destination_ref: str,
        output_formats: list[str],
    ) -> dict[str, Any]:
        return self.store.mark_approved(
            document_action_id=document_action_id,
            approved_by=approved_by,
            destination_type=destination_type,
            destination_ref=destination_ref,
            output_formats=output_formats,
        )

    def finalize(self, *, document_action_id: int) -> dict[str, Any]:
        record = self.store.get(document_action_id)
        destination = {
            "type": record["destination_type"],
            "ref": record["destination_ref"],
        }

        if record["status"] == "executed":
            return {
                "status": "executed",
                "document_action": record,
                "artifacts": record["artifacts"],
                "destination": destination,
                "announcement": record["announcement"],
            }

        if record["status"] != "approved":
            return {
                "status": "blocked",
                "reason": "approval_required",
                "document_action_id": document_action_id,
            }
        artifacts = [
            self._write_artifact(record=record, output_format=output_format)
            for output_format in record["output_formats"]
        ]
        announcement = self._create_announcement_action(
            record=record,
            artifacts=artifacts,
            destination=destination,
        )
        executed = self.store.mark_executed(
            document_action_id=document_action_id,
            artifacts=artifacts,
            announcement=announcement,
        )
        return {
            "status": "executed",
            "document_action": executed,
            "artifacts": executed["artifacts"],
            "destination": destination,
            "announcement": executed["announcement"],
        }

    def delete(self, *, document_action_id: int) -> None:
        record = self.store.get(document_action_id)

        if self.actions_store is not None:
            for action_id in self._collect_action_ids(record):
                self.actions_store.delete_action_request(action_id)

        artifact_dir = self.artifact_root / str(document_action_id)
        if artifact_dir.is_dir():
            shutil.rmtree(artifact_dir, ignore_errors=True)

        self.store.delete(document_action_id)

    @staticmethod
    def _collect_action_ids(record: dict[str, Any]) -> list[str]:
        action_ids: list[str] = []
        for key in ("announcement", "export_package"):
            value = record.get(key)
            if isinstance(value, dict):
                action_id = value.get("action_id") or (
                    value.get("announcement") or {}
                ).get("action_id")
                if isinstance(action_id, str) and action_id:
                    action_ids.append(action_id)
        return action_ids

    def export_package(self, *, document_action_id: int) -> dict[str, Any]:
        record = self.store.get(document_action_id)
        export_package = record.get("export_package")

        if record["status"] != "executed":
            return {
                "status": "blocked",
                "reason": "finalization_required",
                "document_action_id": document_action_id,
            }

        if isinstance(export_package, dict) and export_package.get("status") == "completed":
            return {
                "status": "completed",
                "document_action": record,
                "artifacts": list(export_package.get("artifacts") or []),
                "export_action": export_package,
            }

        artifacts = [
            self._write_export_artifact(record=record, output_format=output_format)
            for output_format in ("pdf", "docx", "xlsx")
        ]
        export_action = self._create_export_action(record=record, artifacts=artifacts)
        persisted = self.store.mark_export_package(
            document_action_id=document_action_id,
            export_package=export_action | {"artifacts": artifacts},
        )
        return {
            "status": "completed",
            "document_action": persisted,
            "artifacts": persisted["export_package"]["artifacts"],
            "export_action": persisted["export_package"],
        }

    def _write_artifact(
        self,
        *,
        record: dict[str, Any],
        output_format: str,
    ) -> dict[str, Any]:
        file_name = f"{record['title'].replace(' ', '_').lower()}.{output_format}"
        content, content_type = self._render_artifact_content(record=record, output_format=output_format)
        artifact_path = write_local_document_artifact(
            artifact_root=self.artifact_root,
            document_action_id=int(record["id"]),
            file_name=file_name,
            content=content,
        )
        artifact = {
            "format": output_format,
            "file_name": file_name,
            "storage_ref": str(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
        }
        blob_url = upload_report(
            name=f"document_artifacts/{record['id']}/{file_name}",
            content=content,
            content_type=content_type,
        )
        if blob_url:
            artifact["blob_url"] = blob_url
        return artifact

    def _write_export_artifact(
        self,
        *,
        record: dict[str, Any],
        output_format: str,
    ) -> dict[str, Any]:
        file_stem = record["title"].replace(" ", "_").lower()
        file_name = f"{file_stem}_export.{output_format}"
        content, content_type = self._render_artifact_content(record=record, output_format=output_format)
        artifact_path = write_local_document_artifact(
            artifact_root=self.artifact_root,
            document_action_id=int(record["id"]),
            file_name=file_name,
            content=content,
        )
        artifact = {
            "format": output_format,
            "file_name": file_name,
            "storage_ref": str(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
        }
        blob_url = upload_report(
            name=f"document_artifacts/{record['id']}/{file_name}",
            content=content,
            content_type=content_type,
        )
        if blob_url:
            artifact["blob_url"] = blob_url
        return artifact

    def _resolve_document_export_base_url(self) -> str:
        export_url = os.getenv("DOCUMENT_EXPORT_URL", os.getenv("MCP_DOC_URL", "http://localhost:8006/mcp")).strip()
        if export_url.endswith("/mcp"):
            return export_url[:-4]
        return export_url.rstrip("/")

    def _artifact_export_payload(self, *, record: dict[str, Any], output_format: str) -> dict[str, Any]:
        markdown = str(record.get("draft_markdown") or f"# {record['title']}\n")
        # The export template already renders the document title; drop a leading
        # H1 that repeats it and let the markdown's own headings structure the body.
        lines = markdown.lstrip().splitlines()
        if lines and lines[0].startswith("# ") and lines[0][2:].strip() == str(record["title"]).strip():
            markdown = "\n".join(lines[1:]).lstrip("\n")
        return {
            "type": "report",
            "format": output_format,
            "title": record["title"],
            "data": {
                "sections": [
                    {
                        "heading": "",
                        "content": markdown,
                        "key_metrics": [],
                    }
                ],
                "action_items": [],
                "tags": [str(record.get("document_type") or "document_workflow")],
            },
        }

    def _artifact_content_type(self, output_format: str) -> str:
        return {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }.get(output_format, "application/octet-stream")

    def _render_artifact_content(
        self,
        *,
        record: dict[str, Any],
        output_format: str,
    ) -> tuple[bytes, str]:
        export_url = f"{self.document_export_base_url}/export"
        export_payload = self._artifact_export_payload(record=record, output_format=output_format)
        try:
            with httpx.Client(timeout=90.0, follow_redirects=False) as client:
                resp = client.post(export_url, json=export_payload)
                # Azure Container Apps ingress returns 301 HTTP→HTTPS; re-POST to location.
                if resp.status_code in (301, 302, 307, 308) and "location" in resp.headers:
                    resp = client.post(resp.headers["location"], json=export_payload)
            if resp.status_code < 400 and resp.content:
                return resp.content, resp.headers.get("content-type", self._artifact_content_type(output_format))
        except Exception:
            pass

        if output_format in ("pdf", "docx", "xlsx"):
            raise RuntimeError(
                f"The document generation service is not available right now, so your {output_format.upper()} "
                f"could not be created. Please try again in a moment or contact support if the issue persists."
            )

        destination_line = f"Destination: {record.get('destination_type') or 'local'} / {record.get('destination_ref') or 'n/a'}"
        format_line = f"Format: {output_format}"
        content = "\n".join(
            [
                record["draft_markdown"].rstrip(),
                "",
                destination_line,
                format_line,
            ]
        )
        return content.encode("utf-8"), "text/plain; charset=utf-8"

    def _create_announcement_action(
        self,
        *,
        record: dict[str, Any],
        artifacts: list[dict[str, Any]],
        destination: dict[str, Any],
    ) -> dict[str, Any]:
        if self.actions_store is None:
            return {
                "status": "created",
                "type": "document_finalized",
                "channel": "internal_queue",
            }

        payload = {
            "document_action_id": record["id"],
            "title": record["title"],
            "document_type": record["document_type"],
            "destination": destination,
            "artifacts": artifacts,
            "message": f"{record['title']} finalized with {len(artifacts)} artifact(s).",
        }
        created = self.actions_store.create_action_request(
            action_id=str(uuid.uuid4()),
            source_id="document_workflow",
            entity_type="announcement",
            payload=payload,
            idempotency_key=f"document-announcement:{record['id']}",
            risk_level="low",
            policy_version="document-workflow-v1",
            policy_decision={
                "allow": True,
                "risk_level": "low",
                "requires_approval": False,
                "reason": "Internal document workflow announcement",
                "policy_version": "document-workflow-v1",
            },
            requires_approval=False,
            requested_by=record.get("approved_by"),
        )
        action_id = created["action_id"]
        completed = self.actions_store.update_action_result(
            action_id=action_id,
            status="completed",
            result={
                "delivered": True,
                "channel": "internal_queue",
                "message": payload["message"],
                "artifact_count": len(artifacts),
            },
            approved_by=record.get("approved_by"),
        )
        return {
            "status": (completed or {}).get("status", created["status"]),
            "type": "document_finalized",
            "channel": "internal_queue",
            "action_id": action_id,
            "result": (completed or {}).get("result"),
        }

    def _create_export_action(
        self,
        *,
        record: dict[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if self.actions_store is None:
            return {
                "status": "completed",
                "type": "export_package",
                "channel": "internal_queue",
                "action_id": None,
                "result": {
                    "delivered": True,
                    "channel": "internal_queue",
                    "artifact_count": len(artifacts),
                },
            }

        payload = {
            "document_action_id": record["id"],
            "title": record["title"],
            "document_type": record["document_type"],
            "artifacts": artifacts,
            "message": f"{record['title']} export package generated with {len(artifacts)} artifact(s).",
        }
        created = self.actions_store.create_action_request(
            action_id=str(uuid.uuid4()),
            source_id="document_workflow",
            entity_type="export_package",
            payload=payload,
            idempotency_key=f"document-export-package:{record['id']}",
            risk_level="low",
            policy_version="document-workflow-v1",
            policy_decision={
                "allow": True,
                "risk_level": "low",
                "requires_approval": False,
                "reason": "Internal document workflow export package",
                "policy_version": "document-workflow-v1",
            },
            requires_approval=False,
            requested_by=record.get("approved_by"),
        )
        action_id = created["action_id"]
        completed = self.actions_store.update_action_result(
            action_id=action_id,
            status="completed",
            result={
                "delivered": True,
                "channel": "internal_queue",
                "message": payload["message"],
                "artifact_count": len(artifacts),
            },
            approved_by=record.get("approved_by"),
        )
        return {
            "status": (completed or {}).get("status", created["status"]),
            "type": "export_package",
            "channel": "internal_queue",
            "action_id": action_id,
            "result": (completed or {}).get("result"),
        }
