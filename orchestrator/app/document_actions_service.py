from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

try:
    from app.blob import DOCUMENT_ARTIFACT_ROOT, upload_report, write_local_document_artifact
    from app.actions_store import ActionsStore
    from app.document_actions_store import DocumentActionsStore
except ImportError:
    from orchestrator.app.blob import DOCUMENT_ARTIFACT_ROOT, upload_report, write_local_document_artifact
    from orchestrator.app.actions_store import ActionsStore
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

    def _write_artifact(
        self,
        *,
        record: dict[str, Any],
        output_format: str,
    ) -> dict[str, Any]:
        file_name = f"{record['title'].replace(' ', '_').lower()}.{output_format}"
        content = self._render_artifact_content(record=record, output_format=output_format)
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
            content_type="text/plain",
        )
        if blob_url:
            artifact["blob_url"] = blob_url
        return artifact

    def _render_artifact_content(
        self,
        *,
        record: dict[str, Any],
        output_format: str,
    ) -> bytes:
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
        return content.encode("utf-8")

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
