"""IO for session list serialization and persistence."""

from __future__ import annotations

import json
import uuid
from typing import Any

from claude_code_gui.domain.session import SessionRecord
from claude_code_gui.storage.config_paths import SESSIONS_PATH, ensure_config_dir


def _session_payloads_from_raw(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    if isinstance(raw, dict):
        sessions = raw.get("sessions")
        if isinstance(sessions, list):
            return [item for item in sessions if isinstance(item, dict)]

    raise ValueError("Unsupported sessions.json format")


def load_sessions() -> list[SessionRecord]:
    ensure_config_dir()
    if not SESSIONS_PATH.is_file():
        return []

    raw = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
    payloads = _session_payloads_from_raw(raw)

    loaded: list[SessionRecord] = []
    seen_ids: set[str] = set()

    for item in payloads:
        session = SessionRecord.from_dict(item)
        if session.id in seen_ids:
            session.id = str(uuid.uuid4())
        seen_ids.add(session.id)
        loaded.append(session)

    return loaded


def save_sessions(sessions: list[SessionRecord]) -> None:
    ensure_config_dir()
    payload = [session.to_dict() for session in sessions]
    SESSIONS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
