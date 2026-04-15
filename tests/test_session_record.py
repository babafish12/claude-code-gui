from __future__ import annotations

from pathlib import Path

import pytest

from claude_code_gui.core.model_permissions import normalize_permission_value
from claude_code_gui.domain.provider import get_provider_config
from claude_code_gui.domain.session import SessionRecord

pytestmark = pytest.mark.unit


def test_from_dict_legacy_payload_defaults_provider_and_mode(tmp_path: Path) -> None:
    payload = {
        "id": "s-1",
        "title": " Legacy ",
        "working_dir": str(tmp_path),
        "model": "default",
        "mode": "ask",
        "status": "invalid-status",
        "history": "not-a-list",
    }

    record = SessionRecord.from_dict(payload)

    assert record.id == "s-1"
    assert record.provider == "claude"
    assert record.model == "sonnet"
    assert record.permission_mode == normalize_permission_value("ask", provider="claude")
    assert record.status == "ended"
    assert record.history == []
    assert record.project_path == str(tmp_path.resolve())


def test_from_dict_falls_back_to_home_when_path_normalization_fails(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("claude_code_gui.domain.session.normalize_folder", side_effect=OSError("boom"))

    record = SessionRecord.from_dict({"cwd": "/definitely/missing"})

    assert record.project_path == str(Path.home())
    assert record.provider == "claude"


def test_from_dict_codex_normalization_and_reasoning_level(tmp_path: Path) -> None:
    payload = {
        "provider": "codex",
        "project_path": str(tmp_path),
        "model": "unknown-model",
        "permission_mode": "plan",
        "reasoning_level": "low",
    }

    record = SessionRecord.from_dict(payload)

    assert record.provider == "codex"
    assert record.model == get_provider_config("codex").model_options[0][1]
    assert record.permission_mode == "plan"
    assert record.reasoning_level == "low"


def test_to_dict_truncates_history_to_last_200() -> None:
    history = [{"role": "assistant", "content": f"line-{index}"} for index in range(250)]
    record = SessionRecord(
        id="s-2",
        title="t",
        project_path="/tmp",
        model="sonnet",
        permission_mode="auto",
        status="active",
        created_at="2026-01-01T00:00:00+00:00",
        last_used_at="2026-01-01T00:00:00+00:00",
        provider="claude",
        history=history,
    )

    serialized = record.to_dict()

    assert len(serialized["history"]) == 200
    assert serialized["history"][0]["content"] == "line-50"
    assert serialized["provider"] == "claude"
