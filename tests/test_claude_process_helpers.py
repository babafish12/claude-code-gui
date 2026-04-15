from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_code_gui.domain.claude_types import ClaudeRunConfig
from claude_code_gui.domain.cli_dialect import ParsedEvent
from claude_code_gui.runtime.claude_process import ClaudeProcess

pytestmark = pytest.mark.unit


def _build_process():
    permission_requests: list[tuple[str, dict]] = []

    process = ClaudeProcess(
        on_running_changed=lambda *_args: None,
        on_assistant_chunk=lambda *_args: None,
        on_system_message=lambda *_args: None,
        on_permission_request=lambda token, payload: permission_requests.append((token, payload)),
        on_complete=lambda *_args: None,
    )
    return process, permission_requests


def _build_config(*, provider_id: str = "claude", supports_reasoning_flag: bool = True) -> ClaudeRunConfig:
    return ClaudeRunConfig(
        binary_path="/usr/bin/cli",
        message="hello",
        cwd="/tmp/work",
        model="model-a",
        permission_mode="plan",
        conversation_id=None,
        supports_model_flag=False,
        supports_permission_flag=False,
        supports_output_format_flag=True,
        supports_stream_json=True,
        supports_json=True,
        supports_include_partial_messages=True,
        stream_json_requires_verbose=False,
        provider_id=provider_id,
        supports_reasoning_flag=supports_reasoning_flag,
        allowed_tools=["Bash"],
    )


def test_mode_attempts_and_cli_run_config_for_codex_and_claude() -> None:
    codex_attempts = ClaudeProcess._build_mode_attempts(_build_config(provider_id="codex", supports_reasoning_flag=True))
    assert codex_attempts == [("stream-json", True), ("stream-json", False), ("text", False)]

    claude_attempts = ClaudeProcess._build_mode_attempts(_build_config(provider_id="claude", supports_reasoning_flag=True))
    assert claude_attempts == [("stream-json", True), ("json", True), ("text", True)]

    codex_cli = ClaudeProcess._build_cli_run_config(
        _build_config(provider_id="codex", supports_reasoning_flag=True),
        mode="stream-json",
        include_reasoning=False,
    )
    assert codex_cli.supports_model_flag is True
    assert codex_cli.supports_permission_flag is True
    assert codex_cli.supports_output_format_flag is True
    assert codex_cli.supports_reasoning_flag is False
    assert codex_cli.allowed_tools == ["Bash"]


def test_parse_json_and_text_choice_helpers() -> None:
    assert ClaudeProcess._parse_json_line('{"ok":true}') == {"ok": True}
    assert ClaudeProcess._parse_json_line('["not-dict"]') is None
    assert ClaudeProcess._parse_json_line("{bad") is None

    numbered = ClaudeProcess._extract_text_choices("[1] yes [2] no")
    labeled = ClaudeProcess._extract_text_choices("A) keep B) discard")
    assert numbered == ["yes", "no"]
    assert labeled == ["keep", "discard"]


def test_text_permission_request_emission_is_deduplicated() -> None:
    process, permission_requests = _build_process()
    seen: set[str] = set()

    first = process._maybe_emit_text_permission_request(
        request_token="req-1",
        text="Should I proceed with update? [Y/n]",
        seen_signatures=seen,
    )
    second = process._maybe_emit_text_permission_request(
        request_token="req-1",
        text="Should I proceed with update? [Y/n]",
        seen_signatures=seen,
    )

    assert first is True
    assert second is True
    assert len(permission_requests) == 1
    payload = permission_requests[0][1]
    assert payload["choices"] == ["Yes", "No"]
    assert payload["defaultChoice"] == "Yes"


def test_file_change_helpers_and_snapshotting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    process, _permission_requests = _build_process()

    assert process._resolve_file_change_path("src/app.py", cwd="/work") == "/work/src/app.py"
    assert process._display_file_change_path("/work/src/app.py", cwd="/work") == "src/app.py"
    assert process._file_change_tool_name("add") == "Write"
    assert process._file_change_tool_name("delete") == "Delete"
    assert process._file_change_tool_name("update") == "Edit"

    text_file = tmp_path / "notes.txt"
    text_file.write_text("hello", encoding="utf-8")
    binary_file = tmp_path / "bin.dat"
    binary_file.write_bytes(b"\x00bin")

    assert process._snapshot_text_for_diff(str(text_file)) == "hello"
    assert process._snapshot_text_for_diff(str(binary_file)) is None
    assert process._snapshot_text_for_diff(str(tmp_path / "missing.txt")) == ""
    assert process._snapshot_text_for_diff(str(tmp_path)) is None

    monkeypatch.setattr(
        "os.path.relpath",
        lambda _path, _cwd: (_ for _ in ()).throw(ValueError("bad drive")),
    )
    assert process._display_file_change_path("/elsewhere/file.txt", cwd="/work") == "/elsewhere/file.txt"


def test_materialize_codex_file_change_payloads_generates_diff(tmp_path: Path, mocker) -> None:
    process, _permission_requests = _build_process()
    snapshots: dict[str, dict[str, str | None]] = {}
    target = tmp_path / "demo.txt"

    mocked_snapshot = mocker.patch.object(
        process,
        "_snapshot_text_for_diff",
        side_effect=["old content", "new content"],
    )

    started_payload = {
        "id": "chg-1",
        "type": "file_change",
        "status": "in_progress",
        "changes": [{"path": str(target), "kind": "update"}],
    }
    completed_payload = {
        "id": "chg-1",
        "type": "file_change",
        "status": "completed",
        "changes": [{"path": str(target), "kind": "update"}],
    }

    assert process._materialize_codex_file_change_payloads(started_payload, cwd=str(tmp_path), snapshots=snapshots) == []
    diff_payloads = process._materialize_codex_file_change_payloads(
        completed_payload,
        cwd=str(tmp_path),
        snapshots=snapshots,
    )

    assert mocked_snapshot.call_count == 2
    assert len(diff_payloads) == 1
    assert diff_payloads[0]["name"] == "Edit"
    assert diff_payloads[0]["old"] == "old content"
    assert diff_payloads[0]["new"] == "new content"
    assert diff_payloads[0]["path"] == "demo.txt"


def test_tool_payload_normalization_and_text_delta_extraction() -> None:
    process, _permission_requests = _build_process()

    codex_payload = process._normalize_tool_payload(
        parsed_event=ParsedEvent(tool={"command": "ls"}),
        provider_id="codex",
    )
    assert codex_payload is not None
    assert codex_payload["name"] == "bash"
    assert codex_payload["__tool__"] is True

    filtered = process._normalize_tool_payload(
        parsed_event=ParsedEvent(tool={"name": "tool_result", "output": "plain output"}),
        provider_id="claude",
    )
    assert filtered is None

    event = {
        "type": "stream_event",
        "delta": {"text": "a"},
        "content": [{"delta": {"text": "b"}}, {"type": "tool_use", "text": "skip"}],
    }
    assert process._extract_text_deltas(event) == ["a", "b"]


def test_command_metadata_extractors_for_git_pr_and_ci_events() -> None:
    process, _permission_requests = _build_process()

    commit_event = process._detect_git_event(
        command="git commit -m \"feat: add tests\"",
        output="[main abcdef1] feat: add tests\n 2 files changed",
    )
    assert commit_event == {
        "operation": "commit",
        "hash": "abcdef1",
        "message": "feat: add tests",
        "filesChanged": 2,
    }

    push_event = process._detect_git_event(
        command="git push origin HEAD:feature-branch",
        output="2 commits\n abcdef1..fedcba9 -> feature-branch",
    )
    assert push_event == {
        "operation": "push",
        "remote": "origin",
        "branch": "feature-branch",
        "commitCount": 2,
    }

    pr_event = process._detect_pr_event(
        command="gh pr create --title \"Add parser\" --head feature --base main",
        output="Created pull request https://github.com/acme/repo/pull/42\n 3 files changed, 10 insertions(+), 2 deletions(-)",
        git_event=push_event,
    )
    assert pr_event is not None
    assert pr_event["number"] == "42"
    assert pr_event["sourceBranch"] == "feature"
    assert pr_event["targetBranch"] == "main"

    ci_event = process._detect_ci_event(
        command="gh pr checks 42",
        output="workflow: test-suite\nbuild ... failed in 12s\nhttps://github.com/acme/repo/actions/runs/123",
        pr_event=pr_event,
    )
    assert ci_event is not None
    assert ci_event["status"] == "failing"
    assert ci_event["pipeline"] == "test-suite"
    assert ci_event["prUrl"] == pr_event["url"]


def test_permission_helpers_and_tool_result_merge() -> None:
    process, _permission_requests = _build_process()

    assert process._extract_flag_value("gh pr create --title \"My PR\" --base=main", "--title") == "My PR"
    assert process._extract_flag_value("gh pr create --title \"My PR\" --base=main", "--base") == "main"
    assert process._extract_first_match(r"PR #(\d+)", "Open PR #77", group=1) == "77"

    assert process._requires_permission({"requires_permission": True}) is True
    assert process._requires_permission({"type": "assistant", "choices": ["Yes", "No"]}) is True
    assert process._requires_permission({"type": "system"}) is False

    assert process._extract_permission_choices({"choices": {"y": "Yes", "n": "No"}}) == ["Yes", "No"]
    assert process._extract_permission_choices({"choices": [{"label": "Allow"}, {"value": "Deny"}]}) == [
        "Allow",
        "Deny",
    ]

    permission_payload = process._extract_permission_request(
        {"requires_permission": True, "question": "Proceed?", "choices": ["Yes", "No"], "defaultChoice": "Yes"},
        request_token="req-9",
        fallback_tool_data={"name": "bash", "command": "pytest -q"},
    )
    assert permission_payload is not None
    assert permission_payload["proposedAction"] == "Proceed?"
    assert permission_payload["description"] == "Proceed?"
    assert permission_payload["choices"] == ["Yes", "No"]
    assert permission_payload["command"] == "pytest -q"

    entries = process._extract_tool_result_entries(
        {
            "content": [
                {"type": "tool_result", "tool_use_id": "tool-1", "content": "done"},
                {"type": "text", "text": "ignored"},
            ]
        }
    )
    assert entries == [{"toolUseId": "tool-1", "output": "done"}]

    merged = process._merge_tool_result_with_tool_use(
        {"toolUseId": "tool-1", "output": "ok"},
        pending_shell_tools={"tool-1": {"__tool__": True, "name": "bash", "command": "echo 1"}},
    )
    assert merged is not None
    assert merged["output"] == "ok"
    assert merged["name"] == "bash"


def test_extract_assistant_content_and_coerce_text() -> None:
    process, _permission_requests = _build_process()

    texts, tools, permission_requests = process._extract_assistant_content(
        {
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "tool_use", "name": "Bash", "input": {"command": "pwd"}},
            ]
        },
        request_token="req-10",
    )
    assert texts == ["Hello"]
    assert len(tools) == 1
    assert json.loads(tools[0])["name"] == "Bash"
    assert permission_requests == []

    assert process._coerce_text({"text": "hello"}) == "hello"
    assert process._coerce_text(["a", {"value": "b"}]) == "a\nb"
    assert process._clip_text("abcdef", limit=3) == "abc"
