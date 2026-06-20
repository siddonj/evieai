from __future__ import annotations

from typing import Any

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

    def finalize(self, *, document_action_id: int) -> dict[str, Any]:
        record = self.store.get(document_action_id)
        if record["status"] != "approved":
            return {
                "status": "blocked",
                "reason": "approval_required",
                "document_action_id": document_action_id,
            }
        return {"status": "ready", "document_action_id": document_action_id}
