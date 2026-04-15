from __future__ import annotations

import json

import pytest

from claude_code_gui.domain.claude_types import ClaudeRunConfig
from claude_code_gui.runtime.claude_process import ClaudeProcess

pytestmark = pytest.mark.integration


def _build_process():
    running: list[tuple[str, bool]] = []
    chunks: list[tuple[str, str]] = []
    system_messages: list[tuple[str, str]] = []
    permission_requests: list[tuple[str, dict]] = []
    completed: list[tuple[str, object]] = []

    process = ClaudeProcess(
        on_running_changed=lambda token, value: running.append((token, value)),
        on_assistant_chunk=lambda token, chunk: chunks.append((token, chunk)),
        on_system_message=lambda token, message: system_messages.append((token, message)),
        on_permission_request=lambda token, payload: permission_requests.append((token, payload)),
        on_complete=lambda token, result: completed.append((token, result)),
    )
    return process, running, chunks, system_messages, permission_requests, completed


def _build_codex_config() -> ClaudeRunConfig:
    return ClaudeRunConfig(
        binary_path="/usr/bin/codex",
        message="say hi",
        cwd="/tmp/work",
        model="gpt-5",
        permission_mode="auto",
        conversation_id=None,
        supports_model_flag=True,
        supports_permission_flag=True,
        supports_output_format_flag=False,
        supports_stream_json=True,
        supports_json=True,
        supports_include_partial_messages=False,
        stream_json_requires_verbose=False,
        provider_id="codex",
    )


def test_codex_run_single_attempt_parses_jsonl_and_emits_callbacks(fake_subprocess) -> None:
    fake_subprocess.enqueue(
        lines=[
            json.dumps({"type": "thread.started", "thread_id": "thread-abc"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "Hello from Codex"},
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "id": "cmd-1",
                        "command": "pytest -q",
                        "aggregated_output": "ok",
                        "status": "completed",
                        "exit_code": 0,
                    },
                }
            ),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 11,
                        "cached_input_tokens": 2,
                        "output_tokens": 3,
                    },
                }
            ),
        ],
        returncode=0,
    )

    process, _running, chunks, system_messages, permission_requests, _completed = _build_process()

    result, unsupported_output = process._run_single_attempt(
        request_token="req-1",
        config=_build_codex_config(),
        mode="stream-json",
    )

    assert result.success is True
    assert result.conversation_id == "thread-abc"
    assert result.assistant_text == "Hello from Codex"
    assert result.streamed_assistant is True
    assert result.input_tokens == 11
    assert result.output_tokens == 3
    assert unsupported_output is False

    assert chunks == [("req-1", "Hello from Codex")]
    assert permission_requests == []

    assert len(system_messages) == 1
    _, payload_raw = system_messages[0]
    payload = json.loads(payload_raw)
    assert payload["__tool__"] is True
    assert payload["name"] == "bash"
    assert payload["command"] == "pytest -q"


def test_codex_run_single_attempt_collects_error_events(fake_subprocess) -> None:
    fake_subprocess.enqueue(
        lines=[json.dumps({"type": "error", "message": "codex failed"})],
        returncode=1,
    )

    process, _running, chunks, system_messages, permission_requests, _completed = _build_process()

    result, unsupported_output = process._run_single_attempt(
        request_token="req-2",
        config=_build_codex_config(),
        mode="stream-json",
    )

    assert result.success is False
    assert result.error_message == "codex failed"
    assert result.assistant_text == ""
    assert unsupported_output is False
    assert chunks == []
    assert system_messages == []
    assert permission_requests == []


def test_codex_file_change_events_emit_diff_payload(fake_subprocess, mocker) -> None:
    fake_subprocess.enqueue(
        lines=[
            json.dumps({"type": "thread.started", "thread_id": "thread-xyz"}),
            json.dumps(
                {
                    "type": "item.started",
                    "item": {
                        "id": "chg-1",
                        "type": "file_change",
                        "status": "in_progress",
                        "changes": [{"path": "src/app.py", "kind": "update"}],
                    },
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "id": "chg-1",
                        "type": "file_change",
                        "status": "completed",
                        "changes": [{"path": "src/app.py", "kind": "update"}],
                    },
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "DONE"},
                }
            ),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 4,
                        "cached_input_tokens": 0,
                        "output_tokens": 1,
                    },
                }
            ),
        ],
        returncode=0,
    )

    process, _running, chunks, system_messages, permission_requests, _completed = _build_process()
    mocker.patch.object(
        process,
        "_snapshot_text_for_diff",
        side_effect=["before\n", "after\n"],
    )

    result, unsupported_output = process._run_single_attempt(
        request_token="req-diff",
        config=_build_codex_config(),
        mode="stream-json",
    )

    assert result.success is True
    assert result.assistant_text == "DONE"
    assert chunks == [("req-diff", "DONE")]
    assert unsupported_output is False
    assert permission_requests == []

    assert len(system_messages) == 1
    _, payload_raw = system_messages[0]
    payload = json.loads(payload_raw)
    assert payload["__tool__"] is True
    assert payload["name"] == "Edit"
    assert payload["path"] == "src/app.py"
    assert payload["old"] == "before\n"
    assert payload["new"] == "after\n"


def test_detect_ci_event_ignores_generic_failures_without_ci_signal() -> None:
    process, _running, _chunks, _system_messages, _permission_requests, _completed = _build_process()

    event = process._detect_ci_event(
        command="bash -lc 'echo failed'",
        output="Operation failed while parsing local file",
        pr_event=None,
    )

    assert event is None


def test_detect_ci_event_for_explicit_ci_command() -> None:
    process, _running, _chunks, _system_messages, _permission_requests, _completed = _build_process()

    event = process._detect_ci_event(
        command="gh run view 123",
        output="status: failed",
        pr_event=None,
    )

    assert event is not None
    assert event["status"] == "failing"


def test_detect_ci_event_ignores_generic_pipeline_words_without_ci_signal() -> None:
    process, _running, _chunks, _system_messages, _permission_requests, _completed = _build_process()

    event = process._detect_ci_event(
        command="cat pipeline_notes.txt",
        output="pipeline pending in local planning doc",
        pr_event=None,
    )

    assert event is None
