from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from app.blob import DOCUMENT_ARTIFACT_ROOT, write_local_document_artifact
    from app.document_actions_store import DocumentActionsStore
except ImportError:
    from orchestrator.app.blob import DOCUMENT_ARTIFACT_ROOT, write_local_document_artifact
    from orchestrator.app.document_actions_store import DocumentActionsStore


class DocumentActionsService:
    def __init__(
        self,
        store: DocumentActionsStore,
        artifact_root: Path | str | None = None,
    ) -> None:
        self.store = store
        self.artifact_root = Path(artifact_root or os.getenv("DOCUMENT_ARTIFACT_ROOT", DOCUMENT_ARTIFACT_ROOT))

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
        announcement = {
            "status": "created",
            "type": "document_finalized",
            "channel": "internal_queue",
        }
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
        return {
            "format": output_format,
            "file_name": file_name,
            "storage_ref": str(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
        }

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
