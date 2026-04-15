from __future__ import annotations

import json
import uuid

import pytest

from claude_code_gui.domain.session import SessionRecord
from claude_code_gui.storage import sessions_store

pytestmark = pytest.mark.integration


@pytest.fixture
def sessions_path(tmp_path, monkeypatch: pytest.MonkeyPatch):
    target = tmp_path / "sessions.json"
    monkeypatch.setattr(sessions_store, "SESSIONS_PATH", target)
    monkeypatch.setattr(sessions_store, "ensure_config_dir", lambda: tmp_path)
    return target


def test_session_payloads_from_raw_supports_list_and_object_schema() -> None:
    assert sessions_store._session_payloads_from_raw([{"id": "a"}, "ignored"]) == [{"id": "a"}]
    assert sessions_store._session_payloads_from_raw({"sessions": [{"id": "b"}, 1]}) == [{"id": "b"}]

    with pytest.raises(ValueError):
        sessions_store._session_payloads_from_raw({"unexpected": []})


def test_normalize_payload_for_legacy_schema_preserves_existing_provider() -> None:
    payload = {"id": "session-1", "provider": "codex"}
    migrated = sessions_store._normalize_payload_for_legacy_schema(payload)

    assert migrated is payload
    assert migrated["provider"] == "codex"

    legacy_payload = {"id": "legacy-session"}
    legacy_migrated = sessions_store._normalize_payload_for_legacy_schema(legacy_payload)
    assert legacy_migrated["provider"] == "claude"
    assert "provider" not in legacy_payload


def test_load_sessions_returns_empty_when_file_missing(sessions_path) -> None:
    assert not sessions_path.exists()
    assert sessions_store.load_sessions() == []


def test_load_sessions_rewrites_duplicate_ids(sessions_path, monkeypatch: pytest.MonkeyPatch) -> None:
    sessions_path.write_text(
        json.dumps(
            [
                {"id": "dup", "title": "First", "project_path": "/tmp"},
                {"id": "dup", "title": "Second", "project_path": "/tmp"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sessions_store.uuid,
        "uuid4",
        lambda: uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )

    loaded = sessions_store.load_sessions()

    assert len(loaded) == 2
    assert loaded[0].id == "dup"
    assert loaded[1].id == "11111111-1111-1111-1111-111111111111"


def test_load_sessions_skips_payloads_when_from_dict_raises(
    sessions_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions_path.write_text(
        json.dumps([{"id": "good"}, {"id": "bad"}, {"id": "good-2"}]),
        encoding="utf-8",
    )

    real_from_dict = SessionRecord.from_dict

    def fake_from_dict(payload: dict):
        if payload.get("id") == "bad":
            raise ValueError("bad payload")
        return real_from_dict(payload)

    monkeypatch.setattr(sessions_store.SessionRecord, "from_dict", staticmethod(fake_from_dict))

    loaded = sessions_store.load_sessions()

    assert [session.id for session in loaded] == ["good", "good-2"]


def test_atomic_write_with_empty_payload_writes_empty_json(sessions_path) -> None:
    sessions_store._atomic_write(sessions_path, "")
    assert json.loads(sessions_path.read_text(encoding="utf-8")) == []

