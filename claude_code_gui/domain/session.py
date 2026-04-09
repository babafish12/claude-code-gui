"""Session domain object and serialization."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_code_gui.core.model_permissions import (
    normalize_model_value,
    normalize_permission_value,
    normalize_session_status,
)
from claude_code_gui.core.paths import normalize_folder
from claude_code_gui.core.time_utils import current_timestamp


@dataclass
class SessionRecord:
    id: str
    title: str
    project_path: str
    model: str
    permission_mode: str
    status: str
    created_at: str
    last_used_at: str
    conversation_id: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    reasoning_level: str = "medium"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionRecord":
        model = normalize_model_value(payload.get("model"))
        permission_mode = normalize_permission_value(
            payload.get("permission_mode") or payload.get("mode")
        )
        status = normalize_session_status(payload.get("status"))

        created_at = str(payload.get("created_at") or current_timestamp())
        last_used_at = str(payload.get("last_used_at") or payload.get("updated_at") or created_at)

        folder_value = str(
            payload.get("project_path")
            or payload.get("working_dir")
            or payload.get("cwd")
            or str(Path.home())
        )
        try:
            project_path = normalize_folder(folder_value)
        except OSError:
            project_path = str(Path.home())

        title = str(payload.get("title") or "Untitled Session").strip() or "Untitled Session"

        conversation_id = payload.get("conversation_id")
        if not isinstance(conversation_id, str) or not conversation_id.strip():
            conversation_id = None

        history = payload.get("history")
        if not isinstance(history, list):
            history = []

        reasoning_level = str(payload.get("reasoning_level") or "medium")

        return cls(
            id=str(payload.get("id") or uuid.uuid4()),
            title=title,
            project_path=project_path,
            model=model,
            permission_mode=permission_mode,
            status=status,
            created_at=created_at,
            last_used_at=last_used_at,
            conversation_id=conversation_id,
            history=history,
            reasoning_level=reasoning_level,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "project_path": self.project_path,
            "model": self.model,
            "permission_mode": self.permission_mode,
            "status": self.status,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "conversation_id": self.conversation_id,
            "history": self.history[-200:],
            "reasoning_level": self.reasoning_level,
        }
