from __future__ import annotations

from typing import Any

try:
    from app.blob import build_document_artifact_ref
    from app.document_actions_store import DocumentActionsStore
except ImportError:
    from orchestrator.app.blob import build_document_artifact_ref
    from orchestrator.app.document_actions_store import DocumentActionsStore


class DocumentActionsService:
    def __init__(self, store: DocumentActionsStore) -> None:
        self.store = store

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
            {
                "format": output_format,
                "file_name": f"{record['title'].replace(' ', '_').lower()}.{output_format}",
                "storage_ref": build_document_artifact_ref(
                    destination_type=str(record["destination_type"] or "artifact"),
                    destination_ref=str(record["destination_ref"] or ""),
                    file_name=f"{record['title'].replace(' ', '_').lower()}.{output_format}",
                ),
            }
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
