"""IO for session list serialization and persistence."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from typing import Any
from pathlib import Path

from claude_code_gui.domain.session import SessionRecord
from claude_code_gui.storage.config_paths import SESSIONS_PATH, ensure_config_dir

logger = logging.getLogger(__name__)


def _session_payloads_from_raw(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    if isinstance(raw, dict):
        sessions = raw.get("sessions")
        if isinstance(sessions, list):
            return [item for item in sessions if isinstance(item, dict)]

    raise ValueError("Unsupported sessions.json format")


def _normalize_payload_for_legacy_schema(payload: dict[str, Any]) -> dict[str, Any]:
    if "provider" in payload:
        return payload
    migrated = dict(payload)
    migrated["provider"] = "claude"
    return migrated


def load_sessions() -> list[SessionRecord]:
    ensure_config_dir()
    if not SESSIONS_PATH.is_file():
        return []

    try:
        raw = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        payloads = _session_payloads_from_raw(raw)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return []

    loaded: list[SessionRecord] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(payloads):
        try:
            normalized_payload = _normalize_payload_for_legacy_schema(item)
            session = SessionRecord.from_dict(normalized_payload)
        except (TypeError, ValueError, KeyError, OSError) as error:
            logger.warning("Skipping invalid session payload at index=%s: %s", index, error)
            continue
        if session.id in seen_ids:
            session.id = str(uuid.uuid4())
        seen_ids.add(session.id)
        loaded.append(session)

    return loaded


def _atomic_write(path: Path, payload: str) -> None:
    if not payload:
        payload = "[]"
    temp_file: str | None = None
    try:
        fd, temp_file = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if temp_file is None:
            raise RuntimeError("Failed to allocate temporary file for sessions write")
        os.replace(temp_file, path)
        _fsync_parent_dir(path)
    finally:
        if temp_file is not None and os.path.exists(temp_file):
            Path(temp_file).unlink()


def _fsync_parent_dir(path: Path) -> None:
    parent = path.parent
    if not parent.exists():
        return
    try:
        dir_fd = os.open(str(parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        return
    finally:
        os.close(dir_fd)


def save_sessions(sessions: list[SessionRecord]) -> None:
    ensure_config_dir()
    payload = [session.to_dict() for session in sessions]
    _atomic_write(SESSIONS_PATH, json.dumps(payload, indent=2))
