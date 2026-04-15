from __future__ import annotations

import json

import pytest

from claude_code_gui.core.model_permissions import normalize_permission_value
from claude_code_gui.domain.session import SessionRecord
from claude_code_gui.storage import sessions_store

pytestmark = pytest.mark.integration


@pytest.fixture
def sessions_path(tmp_path, monkeypatch):
    target = tmp_path / "sessions.json"
    monkeypatch.setattr(sessions_store, "SESSIONS_PATH", target)
    monkeypatch.setattr(sessions_store, "ensure_config_dir", lambda: tmp_path)
    return target


def test_load_sessions_reads_provider_field_from_list_format(sessions_path) -> None:
    sessions_path.write_text(
        json.dumps(
            [
                {
                    "id": "a",
                    "title": "One",
                    "project_path": "/tmp",
                    "model": "sonnet",
                    "permission_mode": "auto",
                    "status": "active",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "last_used_at": "2026-01-01T00:00:00+00:00",
                    "provider": "codex",
                }
            ]
        ),
        encoding="utf-8",
    )

    loaded = sessions_store.load_sessions()

    assert len(loaded) == 1
    assert loaded[0].id == "a"
    assert loaded[0].provider == "codex"


def test_load_sessions_migrates_legacy_payload_without_provider(sessions_path) -> None:
    sessions_path.write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "id": "legacy",
                        "title": "Legacy",
                        "project_path": "/tmp",
                        "model": "default",
                        "mode": "ask",
                        "status": "ended",
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    loaded = sessions_store.load_sessions()

    assert len(loaded) == 1
    assert loaded[0].provider == "claude"
    assert loaded[0].model == "sonnet"
    assert loaded[0].permission_mode == normalize_permission_value("ask", provider="claude")


def test_save_sessions_persists_provider_field(sessions_path) -> None:
    sessions_store.save_sessions(
        [
            SessionRecord(
                id="s-1",
                title="Saved",
                project_path="/tmp",
                model="gpt-5",
                permission_mode="plan",
                status="active",
                created_at="2026-01-01T00:00:00+00:00",
                last_used_at="2026-01-01T00:00:00+00:00",
                provider="codex",
            )
        ]
    )

    raw = json.loads(sessions_path.read_text(encoding="utf-8"))

    assert isinstance(raw, list)
    assert raw[0]["provider"] == "codex"
    assert raw[0]["permission_mode"] == "plan"
