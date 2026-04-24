"""IO for session list serialization and persistence."""

from __future__ import annotations

import fcntl
import json
import logging
import os
import tempfile
import uuid
from contextlib import contextmanager
from typing import Any
from pathlib import Path

from claude_code_gui.core.time_utils import parse_timestamp
from claude_code_gui.domain.session import SessionRecord
from claude_code_gui.storage.config_paths import SESSIONS_PATH, ensure_config_dir

logger = logging.getLogger(__name__)


def _lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


@contextmanager
def _store_lock(path: Path, *, exclusive: bool) -> Any:
    lock_path = _lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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


def _read_session_payloads(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _session_payloads_from_raw(raw)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return []


def _session_payload_timestamp(payload: dict[str, Any]) -> float:
    if not isinstance(payload, dict):
        return 0.0
    for key in ("last_used_at", "updated_at", "created_at"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parsed = parse_timestamp(value)
            if parsed > 0:
                return parsed
    return 0.0


def _merge_session_payloads(
    file_payloads: list[dict[str, Any]],
    memory_payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []

    def remember_order(session_id: str) -> None:
        if session_id and session_id not in ordered_ids:
            ordered_ids.append(session_id)

    for payloads, prefer_existing_on_tie in (
        (memory_payloads, True),
        (file_payloads, True),
    ):
        for raw_payload in payloads:
            if not isinstance(raw_payload, dict):
                continue
            payload = _normalize_payload_for_legacy_schema(dict(raw_payload))
            session_id = str(payload.get("id") or "").strip()
            if not session_id:
                continue
            remember_order(session_id)
            current = merged_by_id.get(session_id)
            if current is None:
                merged_by_id[session_id] = payload
                continue
            candidate_timestamp = _session_payload_timestamp(payload)
            current_timestamp = _session_payload_timestamp(current)
            if candidate_timestamp > current_timestamp:
                merged_by_id[session_id] = payload
                continue
            if not prefer_existing_on_tie and candidate_timestamp == current_timestamp:
                merged_by_id[session_id] = payload

    return [merged_by_id[session_id] for session_id in ordered_ids if session_id in merged_by_id]


def load_sessions() -> list[SessionRecord]:
    ensure_config_dir()
    with _store_lock(SESSIONS_PATH, exclusive=False):
        payloads = _read_session_payloads(SESSIONS_PATH)
        if not payloads:
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
    with _store_lock(SESSIONS_PATH, exclusive=True):
        merged_payload = _merge_session_payloads(
            _read_session_payloads(SESSIONS_PATH),
            payload,
        )
        _atomic_write(SESSIONS_PATH, json.dumps(merged_payload, indent=2))
