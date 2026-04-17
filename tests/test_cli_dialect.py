from __future__ import annotations

import json

import pytest

from claude_code_gui.domain.cli_dialect import ClaudeDialect, CliRunConfig, CodexDialect, GeminiDialect

pytestmark = pytest.mark.unit


@pytest.fixture
def run_config() -> CliRunConfig:
    return CliRunConfig(
        binary_path="/usr/bin/cli",
        cwd="/tmp/work",
        model="sonnet",
        permission_mode="plan",
        reasoning_level="high",
        output_format="stream-json",
        supports_model_flag=True,
        supports_permission_flag=True,
        supports_output_format_flag=True,
        supports_include_partial_messages=True,
        stream_json_requires_verbose=True,
        supports_reasoning_flag=True,
    )


def test_claude_build_argv_with_all_supported_flags(run_config: CliRunConfig) -> None:
    dialect = ClaudeDialect()

    argv = dialect.build_argv("hello", run_config)

    assert argv == [
        "/usr/bin/cli",
        "-p",
        "hello",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--model",
        "sonnet",
        "--permission-mode",
        "plan",
        "--effort",
        "high",
    ]


def test_claude_build_argv_with_ask_permission_mode(run_config: CliRunConfig) -> None:
    run_config.permission_mode = "ask"
    dialect = ClaudeDialect()

    argv = dialect.build_argv("hello", run_config)

    assert "--permission-mode" in argv
    assert "ask" in argv


def test_claude_build_argv_omits_reasoning_flag_when_disabled(run_config: CliRunConfig) -> None:
    run_config.supports_reasoning_flag = False
    dialect = ClaudeDialect()

    argv = dialect.build_argv("hello", run_config)

    assert "--effort" not in argv


def test_claude_build_resume_argv_appends_resume(run_config: CliRunConfig) -> None:
    dialect = ClaudeDialect()

    argv = dialect.build_resume_argv("sess-1", "resume me", run_config)

    assert argv[-2:] == ["--resume", "sess-1"]


def test_claude_parse_line_for_assistant_text_and_tool() -> None:
    dialect = ClaudeDialect()
    line = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "hello"},
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "Bash",
                        "input": {"command": "pwd"},
                    },
                ]
            },
        }
    )

    events = dialect.parse_line(line)

    assert [event.text for event in events if event.text] == ["hello"]
    tools = [event.tool for event in events if event.tool]
    assert len(tools) == 1
    assert tools[0]["name"] == "Bash"
    assert tools[0]["toolUseId"] == "tool-1"
    assert tools[0]["command"] == "pwd"


def test_claude_parse_line_merges_tool_result_with_prior_tool_use() -> None:
    dialect = ClaudeDialect()
    dialect.parse_line(
        json.dumps(
            {
                "type": "tool_use",
                "id": "tool-2",
                "name": "Bash",
                "input": {"command": "ls"},
            }
        )
    )

    events = dialect.parse_line(
        json.dumps(
            {
                "type": "tool_result",
                "tool_use_id": "tool-2",
                "content": "file-a\nfile-b",
            }
        )
    )

    assert len(events) == 1
    assert events[0].tool is not None
    assert events[0].tool["name"] == "Bash"
    assert events[0].tool["output"] == "file-a\nfile-b"


def test_claude_parse_line_result_emits_session_usage_and_text() -> None:
    dialect = ClaudeDialect()

    events = dialect.parse_line(
        json.dumps(
            {
                "type": "result",
                "conversation_id": "conv-123",
                "usage": {"input_tokens": 10, "output_tokens": 4},
                "total_cost_usd": 0.12,
                "result": "final answer",
            }
        )
    )

    assert any(event.session_id == "conv-123" for event in events)
    usage = [event.usage for event in events if event.usage]
    assert usage == [{"input_tokens": 10, "output_tokens": 4, "total_cost_usd": 0.12}]
    assert [event.text for event in events if event.text] == ["final answer"]


def test_claude_parse_line_error_paths() -> None:
    dialect = ClaudeDialect()

    explicit_error = dialect.parse_line(json.dumps({"type": "error", "message": "boom"}))
    assert [event.error for event in explicit_error if event.error] == ["boom"]

    system_warning = dialect.parse_line(
        json.dumps({"type": "system", "subtype": "warning", "message": "careful"})
    )
    assert [event.error for event in system_warning if event.error] == ["careful"]


def test_claude_parse_line_stream_event_delta() -> None:
    dialect = ClaudeDialect()

    events = dialect.parse_line(
        json.dumps(
            {
                "type": "stream_event",
                "event": {"type": "content_block_delta", "delta": {"text": "chunk"}},
            }
        )
    )

    assert [event.text for event in events if event.text] == ["chunk"]


def test_codex_build_argv_permission_mode_mapping() -> None:
    dialect = CodexDialect()
    config = CliRunConfig(
        binary_path="/usr/bin/codex",
        cwd="/tmp/work",
        model="gpt-5",
        permission_mode="bypassPermissions",
    )

    argv = dialect.build_argv("run", config)

    assert argv[:2] == ["/usr/bin/codex", "exec"]
    assert "--dangerously-bypass-approvals-and-sandbox" in argv


def test_codex_build_argv_adds_reasoning_effort_config_when_enabled() -> None:
    dialect = CodexDialect()
    config = CliRunConfig(
        binary_path="/usr/bin/codex",
        cwd="/tmp/work",
        model="gpt-5",
        permission_mode="ask",
        reasoning_level="high",
        supports_reasoning_flag=True,
    )

    argv = dialect.build_argv("run", config)

    assert "-c" in argv
    assert "model_reasoning_effort=high" in argv


def test_codex_build_argv_with_ask_permission_mode() -> None:
    dialect = CodexDialect()
    config = CliRunConfig(
        binary_path="/usr/bin/codex",
        cwd="/tmp/work",
        model="gpt-5",
        permission_mode="ask",
    )

    argv = dialect.build_argv("run", config)

    assert "--permission-mode" not in argv
    assert "--full-auto" not in argv
    assert "--dangerously-bypass-approvals-and-sandbox" not in argv


def test_codex_build_argv_with_plan_permission_uses_sandbox_flag() -> None:
    dialect = CodexDialect()
    config = CliRunConfig(
        binary_path="/usr/bin/codex",
        cwd="/tmp/work",
        model="gpt-5",
        permission_mode="plan",
    )

    argv = dialect.build_argv("run", config)

    assert "--sandbox" in argv
    assert "read-only" in argv


def test_codex_parse_line_all_primary_event_types() -> None:
    dialect = CodexDialect()

    thread_events = dialect.parse_line(json.dumps({"type": "thread.started", "thread_id": "thread-1"}))
    assert [event.session_id for event in thread_events if event.session_id] == ["thread-1"]

    message_events = dialect.parse_line(
        json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "hello from codex"},
            }
        )
    )
    assert [event.text for event in message_events if event.text] == ["hello from codex"]

    command_events = dialect.parse_line(
        json.dumps(
            {
                "type": "item.started",
                "item": {
                    "type": "command_execution",
                    "id": "cmd-1",
                    "command": "pytest -q",
                    "aggregated_output": "running",
                    "status": "running",
                    "exit_code": None,
                },
            }
        )
    )
    assert command_events[0].tool is not None
    assert command_events[0].tool["phase"] == "started"
    assert command_events[0].tool["command"] == "pytest -q"

    turn_events = dialect.parse_line(
        json.dumps(
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 7, "cached_input_tokens": 2, "output_tokens": 3},
            }
        )
    )
    assert turn_events[0].usage == {
        "input_tokens": 7,
        "cached_input_tokens": 2,
        "output_tokens": 3,
    }


def test_codex_parse_line_file_change_item() -> None:
    dialect = CodexDialect()

    events = dialect.parse_line(
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "chg-1",
                    "type": "file_change",
                    "status": "completed",
                    "changes": [
                        {"path": "/tmp/work/src/app.py", "kind": "update"},
                    ],
                },
            }
        )
    )

    assert len(events) == 1
    assert events[0].tool is not None
    assert events[0].tool["type"] == "file_change"
    assert events[0].tool["phase"] == "completed"
    assert events[0].tool["id"] == "chg-1"
    assert events[0].tool["changes"] == [
        {"path": "/tmp/work/src/app.py", "kind": "update"},
    ]


def test_codex_parse_line_error_fallback_message() -> None:
    dialect = CodexDialect()

    events = dialect.parse_line(json.dumps({"type": "fatal"}))

    assert [event.error for event in events if event.error] == ["Codex returned an error event."]


def test_gemini_build_argv_maps_permission_and_reasoning() -> None:
    dialect = GeminiDialect()
    config = CliRunConfig(
        binary_path="/usr/bin/gemini",
        cwd="/tmp/work",
        model="auto",
        permission_mode="bypassPermissions",
        reasoning_level="high",
        output_format="stream-json",
        supports_model_flag=True,
        supports_permission_flag=True,
        supports_output_format_flag=True,
        supports_reasoning_flag=True,
    )

    argv = dialect.build_argv("run", config)

    assert argv[:3] == ["/usr/bin/gemini", "--output-format", "stream-json"]
    assert "--model" in argv
    assert "pro" in argv
    assert "--approval-mode" in argv
    assert "yolo" in argv
    assert argv[-2:] == ["-p", "run"]


@pytest.mark.parametrize(
    ("reasoning_level", "expected_model"),
    [("low", "flash-lite"), ("medium", "flash"), ("high", "pro"), ("xhigh", "pro")],
)
def test_gemini_build_argv_maps_auto_model_alias_per_reasoning(
    reasoning_level: str,
    expected_model: str,
) -> None:
    dialect = GeminiDialect()
    config = CliRunConfig(
        binary_path="/usr/bin/gemini",
        cwd="/tmp/work",
        model="auto",
        permission_mode="ask",
        reasoning_level=reasoning_level,
        output_format="stream-json",
        supports_model_flag=True,
        supports_permission_flag=True,
        supports_output_format_flag=True,
        supports_reasoning_flag=True,
    )

    argv = dialect.build_argv("run", config)

    assert "--model" in argv
    assert expected_model in argv


def test_gemini_build_argv_keeps_auto_model_when_reasoning_disabled() -> None:
    dialect = GeminiDialect()
    config = CliRunConfig(
        binary_path="/usr/bin/gemini",
        cwd="/tmp/work",
        model="auto",
        permission_mode="ask",
        reasoning_level="high",
        output_format="stream-json",
        supports_model_flag=True,
        supports_permission_flag=True,
        supports_output_format_flag=True,
        supports_reasoning_flag=False,
    )

    argv = dialect.build_argv("run", config)

    assert "--model" in argv
    assert "auto" in argv
    assert "pro" not in argv


def test_gemini_parse_line_init_and_assistant_message() -> None:
    dialect = GeminiDialect()
    init_events = dialect.parse_line(
        json.dumps(
            {
                "type": "init",
                "session_id": "sess-1",
                "model": "flash",
            }
        )
    )
    assert [event.session_id for event in init_events if event.session_id] == ["sess-1"]

    message_events = dialect.parse_line(
        json.dumps(
            {
                "type": "message",
                "role": "assistant",
                "content": "Hello from Gemini",
            }
        )
    )
    assert [event.text for event in message_events if event.text] == ["Hello from Gemini"]


def test_gemini_parse_line_tool_call_extracts_edit_diff_from_nested_json_args() -> None:
    dialect = GeminiDialect()
    events = dialect.parse_line(
        json.dumps(
            {
                "type": "tool_call",
                "toolCall": {
                    "id": "tool-1",
                    "name": "edit",
                    "arguments": '{"path":"src/app.py","old_string":"old","new_string":"new"}',
                },
            }
        )
    )

    assert len(events) == 1
    assert events[0].tool is not None
    assert events[0].tool["name"] == "edit"
    assert events[0].tool["toolUseId"] == "tool-1"
    assert events[0].tool["path"] == "src/app.py"
    assert events[0].tool["old"] == "old"
    assert events[0].tool["new"] == "new"


def test_gemini_parse_line_message_content_extracts_tool_payload_and_output_merge() -> None:
    dialect = GeminiDialect()
    message_events = dialect.parse_line(
        json.dumps(
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_call",
                        "id": "tool-2",
                        "name": "write",
                        "args": {
                            "path": "src/new.py",
                            "content": "print('ok')",
                        },
                    },
                    {"type": "text", "text": "done"},
                ],
            }
        )
    )

    assert [event.text for event in message_events if event.text] == ["done"]
    tool_events = [event.tool for event in message_events if event.tool]
    assert len(tool_events) == 1
    assert tool_events[0]["name"] == "write"
    assert tool_events[0]["toolUseId"] == "tool-2"
    assert tool_events[0]["path"] == "src/new.py"
    assert tool_events[0]["new"] == "print('ok')"

    output_events = dialect.parse_line(
        json.dumps(
            {
                "type": "tool_output",
                "toolUseId": "tool-2",
                "output": "wrote file",
            }
        )
    )

    assert len(output_events) == 1
    assert output_events[0].tool is not None
    assert output_events[0].tool["name"] == "write"
    assert output_events[0].tool["toolUseId"] == "tool-2"
    assert output_events[0].tool["path"] == "src/new.py"
    assert output_events[0].tool["output"] == "wrote file"
