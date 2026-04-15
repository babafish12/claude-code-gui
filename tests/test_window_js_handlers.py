from __future__ import annotations

import pytest
from types import SimpleNamespace
from typing import Any

from claude_code_gui.app.constants import (
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_ENDED,
)
from claude_code_gui.gi_runtime import Gdk
from claude_code_gui.ui.window import ClaudeCodeWindow

pytestmark = pytest.mark.unit


class _FakeEntry:
    def __init__(self, text: str, selection: tuple[int, int]):
        self.text = text
        self._selection = selection
        self.delete_calls: list[tuple[int, int]] = []
        self.caret_calls: list[int] = []
        self.region_calls: list[tuple[int, int]] = []

    def get_text(self) -> str:
        return self.text

    def get_selection_bounds(self) -> tuple[int, int]:
        return self._selection

    def delete_text(self, start: int, end: int) -> None:
        self.delete_calls.append((start, end))
        self.text = self.text[:start] + self.text[end:]
        self._selection = (start, start)

    def set_position(self, position: int) -> None:
        self.caret_calls.append(position)

    def select_region(self, start: int, end: int) -> None:
        self.region_calls.append((start, end))


class _FakeJsResult:
    def __init__(self, payload: Any):
        self._payload = payload

    def get_js_value(self) -> Any:
        return self._payload


class _FakeStyleContext:
    def __init__(self) -> None:
        self.classes: set[str] = set()

    def add_class(self, class_name: str) -> None:
        self.classes.add(class_name)

    def remove_class(self, class_name: str) -> None:
        self.classes.discard(class_name)


class _FakeLabel:
    def __init__(self) -> None:
        self.text = ""
        self.visible = False
        self._context = _FakeStyleContext()

    def set_text(self, value: str) -> None:
        self.text = value

    def set_visible(self, value: bool) -> None:
        self.visible = bool(value)

    def get_style_context(self) -> _FakeStyleContext:
        return self._context


class _FakePane:
    def __init__(self, process: _FakeClaudeProcess) -> None:
        self._claude_process = process


class _FakeClaudeProcess:
    def __init__(self) -> None:
        self.responses: list[tuple[str, str, str]] = []

    def send_permission_response(self, *, action: str, comment: str = "", request_id: str = "") -> bool:
        self.responses.append((action, comment, request_id))
        return True


class _SwitchFakeProcess:
    def __init__(self, *, running: bool) -> None:
        self._running = running

    def is_running(self) -> bool:
        return self._running


def _build_permission_window() -> tuple[ClaudeCodeWindow, _FakeClaudeProcess]:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    process = _FakeClaudeProcess()
    pane = _FakePane(process)
    window._pane_context_id = "p1"
    window._pane_registry = {"p1": pane}
    window._active_pane_id = "p1"
    window._active_provider_id = "claude"
    window._activate_existing_pane = lambda _pane_id: True
    window._set_status_message = lambda *args, **kwargs: None
    window._add_system_message = lambda *_args, **_kwargs: None
    window._allowed_tools = set()
    return window, process


def test_extract_action_from_js_result_supports_string_and_json_payloads() -> None:
    assert (
        ClaudeCodeWindow._extract_action_from_js_result(
            _FakeJsResult("open"),
            allowed_actions={"open", "attach"},
        )
        == "open"
    )
    assert (
        ClaudeCodeWindow._extract_action_from_js_result(
            _FakeJsResult('{"action": "attach"}'),
            allowed_actions={"open", "attach"},
        )
        == "attach"
    )
    assert (
        ClaudeCodeWindow._extract_action_from_js_result(
            _FakeJsResult('[{"action":"open"}]'),
            allowed_actions={"open", "attach"},
        )
        == "open"
    )
    assert (
        ClaudeCodeWindow._extract_action_from_js_result(
            _FakeJsResult('{"type":"attach_file"}'),
            allowed_actions={"attach_file"},
        )
        == "attach_file"
    )


def test_extract_action_from_js_result_rejects_unknown_actions() -> None:
    assert (
        ClaudeCodeWindow._extract_action_from_js_result(
            _FakeJsResult('{"action":"denied"}'),
            allowed_actions={"open", "attach"},
        )
        is None
    )
    assert (
        ClaudeCodeWindow._extract_action_from_js_result(
            _FakeJsResult("unsupported"),
            allowed_actions={"open"},
        )
        is None
    )


def test_project_path_key_press_does_not_delete_full_selection_on_backspace_or_delete() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    entry = _FakeEntry("my/path/here", (0, 12))
    window._project_path_entry = entry

    backspace_event = SimpleNamespace(keyval=Gdk.KEY_BackSpace)
    delete_event = SimpleNamespace(keyval=Gdk.KEY_Delete)

    assert window._on_project_path_entry_key_press(entry, backspace_event) is True
    assert entry.text == "my/path/her"
    assert entry.delete_calls == [(11, 12)]
    assert entry._selection == (11, 11)

    entry = _FakeEntry("my/path/here", (0, 12))
    window._project_path_entry = entry
    assert window._on_project_path_entry_key_press(entry, delete_event) is True
    assert entry.text == "y/path/here"
    assert entry.delete_calls == [(0, 1)]
    assert entry._selection == (0, 0)


def test_on_js_permission_response_accepts_aliases_and_yes_no_shortcuts() -> None:
    window, process = _build_permission_window()

    payload_yes = _FakeJsResult('{"action":"y","tool_name":"Write","request_id":"r1","is_denial_card":false}')
    window._on_js_permission_response("p1", None, payload_yes)
    assert process.responses == [("allow", "", "r1")]

    window, process = _build_permission_window()
    payload_no = _FakeJsResult('{"action":"No","tool":"Read","request_id":"r2","is_denial_card":false}')
    window._on_js_permission_response("p1", None, payload_no)
    assert process.responses == [("deny", "", "r2")]

    window, process = _build_permission_window()
    payload_comment_choice = _FakeJsResult(
        '{"tool":"Write","action":"comment","choice":"Please continue with tests","requestId":"r3","isDenialCard":false}'
    )
    window._on_js_permission_response("p1", None, payload_comment_choice)
    assert process.responses == [("comment", "Please continue with tests", "r3")]


def test_on_js_change_folder_uses_default_action_for_undefined_payload() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    calls: list[tuple[str, bool]] = []
    labels: list[str] = []
    window._pane_context_id = None
    window._active_pane_id = "p1"
    window._pane_registry = {"p1": SimpleNamespace(_active_session_id=None)}
    window._activate_existing_pane = lambda _pane_id: True
    window._set_status_message = lambda *_args, **_kwargs: None
    window._choose_project_folder_with_dialog = lambda: "/tmp/project"
    window._set_project_path_entry_text = lambda value: labels.append(value)
    window._set_project_folder = lambda value, restart_session=False: calls.append((value, restart_session))

    window._on_js_change_folder("p1", None, _FakeJsResult("undefined"))

    assert labels == ["/tmp/project"]
    assert calls == [("/tmp/project", False)]


def test_execute_agentctl_from_assistant_ignores_non_primary_pane() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    called: list[tuple[str, str, bool]] = []
    system_messages: list[str] = []

    window._is_primary_pane = lambda _pane_id: False
    window._extract_agentctl_commands = lambda _text: ["/agent new Worker 2"]
    window._handle_agent_command = (
        lambda pane_id, command, allow_non_primary=False: called.append((pane_id, command, allow_non_primary)) or True
    )
    window._add_system_message = lambda message: system_messages.append(message)

    executed = window._execute_agentctl_from_assistant("pane-2", "/agent new Worker 2")

    assert executed == 0
    assert called == []
    assert system_messages == []


def test_agent_send_wraps_worker_prompt_with_handoff_protocol() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    sent_payload: dict[str, str | None] = {}
    statuses: list[str] = []
    system_messages: list[str] = []

    window._is_primary_pane = lambda pane_id: pane_id == "pane-1"
    window._resolve_pane_target = lambda _reference, current_pane_id: "pane-2" if current_pane_id == "pane-1" else None
    window._send_prompt_to_pane = lambda target_pane_id, prompt, keep_focus_on=None: (
        sent_payload.update(
            {
                "target": target_pane_id,
                "prompt": prompt,
                "keep_focus_on": keep_focus_on,
            }
        )
        or True
    )
    window._set_status_message = lambda message, _status: statuses.append(message)
    window._add_system_message = lambda message: system_messages.append(message)
    window._pane_registry = {
        "pane-1": SimpleNamespace(
            _is_agent=False,
            _agent_name=None,
            _agent_status="",
            _agent_status_label=None,
            _title_label=None,
            _session_label=None,
            _active_session_id=None,
        ),
        "pane-2": SimpleNamespace(
            _is_agent=True,
            _agent_name="Worker 1",
            _agent_status="",
            _agent_status_label=None,
            _title_label=None,
            _session_label=None,
            _active_session_id=None,
        ),
    }
    window._pane_by_id = lambda pane_id: window._pane_registry.get(pane_id)
    window._pane_display_name = lambda pane_id: "Worker 1" if pane_id == "pane-2" else "Pane 1"

    handled = window._handle_agent_command(
        "pane-1",
        "/agent send pane-2 Bitte bearbeite vube/test.txt und entferne Zeile 3",
    )

    assert handled is True
    assert sent_payload["target"] == "pane-2"
    assert sent_payload["keep_focus_on"] == "pane-1"
    prompt_text = str(sent_payload["prompt"] or "")
    assert "You are Worker 1, a worker agent." in prompt_text
    assert "Never output or execute /agent, /pane, @agentctl, agentctl commands." in prompt_text
    assert "AGENT_STATUS: DONE or BLOCKED" in prompt_text
    assert "AGENT_SUMMARY:" in prompt_text
    assert "AGENT_FILES:" in prompt_text
    assert "AGENT_NEXT:" in prompt_text
    assert "Delegated task:" in prompt_text
    assert "Bitte bearbeite vube/test.txt und entferne Zeile 3" in prompt_text
    assert statuses and statuses[-1] == "Prompt sent to Worker 1."
    assert system_messages == []


def test_extract_agent_status_marker_parses_done_and_blocked() -> None:
    done_text = "Result:\nAGENT_STATUS: DONE\nAGENT_SUMMARY: ok"
    blocked_text = "- AGENT_STATUS: BLOCKED\nreason"

    assert ClaudeCodeWindow._extract_agent_status_marker(done_text) == "done"
    assert ClaudeCodeWindow._extract_agent_status_marker(blocked_text) == "blocked"
    assert ClaudeCodeWindow._extract_agent_status_marker("no marker") == ""


def test_extract_agent_summary_and_files_markers() -> None:
    text = (
        "AGENT_STATUS: DONE\n"
        "AGENT_SUMMARY: Refactor complete\n"
        "AGENT_FILES: src/app.ts, src/ui.ts\n"
        "AGENT_NEXT: none\n"
    )
    assert ClaudeCodeWindow._extract_agent_summary_marker(text) == "Refactor complete"
    assert ClaudeCodeWindow._extract_agent_files_marker(text) == "src/app.ts, src/ui.ts"


def test_publish_agent_result_to_main_chat_uses_summary_and_files() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    calls: list[tuple[str, str, str]] = []
    window._primary_pane_id = lambda: "pane-1"
    window._pane_display_name = lambda _pane_id: "Worker 1"
    window._call_js_in_pane = (
        lambda pane_id, function_name, payload: calls.append((pane_id, function_name, payload)) or True
    )

    window._publish_agent_result_to_main_chat(
        agent_pane_id="pane-2",
        status="done",
        assistant_text=(
            "AGENT_STATUS: DONE\n"
            "AGENT_SUMMARY: Implemented endpoint\n"
            "AGENT_FILES: api/routes.py\n"
        ),
    )

    assert calls == [
        (
            "pane-1",
            "addSystemMessage",
            "Worker 1 [DONE]: Implemented endpoint | Files: api/routes.py",
        )
    ]


def test_set_pane_agent_status_updates_badge_classes() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    badge = _FakeLabel()
    pane = SimpleNamespace(
        _is_agent=True,
        _agent_status="",
        _agent_status_label=badge,
        _title_label=None,
        _session_label=None,
        _active_session_id=None,
    )
    window._pane_registry = {"pane-2": pane}
    window._pane_by_id = lambda pane_id: window._pane_registry.get(pane_id)
    window._find_session = lambda _session_id: None
    window._truncate_text = lambda text, _limit: text

    window._set_pane_agent_status("pane-2", "blocked")

    assert pane._agent_status == "blocked"
    assert badge.visible is True
    assert badge.text == "BLOCKED"
    assert "pane-agent-status-blocked" in badge.get_style_context().classes


def test_session_status_dot_class_tracks_inactive_active_and_working() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    pane = SimpleNamespace(
        _active_session_id="session-1",
        _active_request_session_id="session-1",
        _claude_process=_SwitchFakeProcess(running=True),
        _is_agent=False,
    )
    window._pane_registry = {"pane-1": pane}

    session = SimpleNamespace(id="session-1", status=SESSION_STATUS_ACTIVE)
    assert window._session_status_dot_class(session) == "session-status-active-working"

    pane._claude_process = _SwitchFakeProcess(running=False)
    assert window._session_status_dot_class(session) == "session-status-active-done"

    pane._active_session_id = "other-session"
    assert window._session_status_dot_class(session) == "session-status-inactive"

    session.status = SESSION_STATUS_ARCHIVED
    assert window._session_status_dot_class(session) == "session-status-archived"


def test_switch_to_session_keeps_running_request_in_background() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    pane = SimpleNamespace(
        _active_session_id="s1",
        _conversation_id="conv-1",
        _active_request_token="req-1",
        _active_request_session_id="s1",
        _active_assistant_message="partial",
        _allowed_tools=set(),
        _permission_request_pending=False,
        _has_messages=True,
        _last_request_failed=False,
        _request_temp_files={},
        _claude_process=_SwitchFakeProcess(running=True),
    )
    window._pane_context_id = "p1"
    window._active_pane_id = "p1"
    window._pane_registry = {"p1": pane}
    window._active_provider_id = "claude"
    window._binary_path = "/usr/bin/claude"
    window._session_search_query = ""
    window._session_filter = "all"
    window._save_sessions_safe = lambda _context: True
    window._refresh_session_list = lambda: None
    window._refresh_connection_state = lambda: None
    window._apply_session_to_controls = lambda _session, add_to_recent: None
    window._render_active_session_view = lambda: None
    window._switch_provider = lambda _provider_id: True
    status_messages: list[str] = []
    window._set_status_message = lambda message, _severity=None: status_messages.append(message)

    session1 = SimpleNamespace(
        id="s1",
        provider="claude",
        status=SESSION_STATUS_ACTIVE,
        last_used_at="2026-01-01T10:00:00+00:00",
        project_path="/tmp/project",
        history=[{"role": "user", "content": "hi"}],
        conversation_id="conv-1",
        title="chat 1",
    )
    session2 = SimpleNamespace(
        id="s2",
        provider="claude",
        status=SESSION_STATUS_ENDED,
        last_used_at="2026-01-01T09:00:00+00:00",
        project_path="/tmp/project",
        history=[],
        conversation_id=None,
        title="chat 2",
    )
    window._sessions = [session1, session2]
    window._find_session = lambda sid: session1 if sid == "s1" else (session2 if sid == "s2" else None)
    window._get_active_session = lambda: window._find_session(window._active_session_id)

    window._switch_to_session("s2")

    assert window._active_session_id == "s2"
    assert session1.status == SESSION_STATUS_ACTIVE
    assert session2.status == SESSION_STATUS_ACTIVE
    assert session1.last_used_at == "2026-01-01T10:00:00+00:00"
    assert session2.last_used_at == "2026-01-01T09:00:00+00:00"
    assert any("continues in background" in message for message in status_messages)


def test_replay_history_uses_static_assistant_message_rendering() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    calls: list[tuple[str, str]] = []
    pane = SimpleNamespace(_has_messages=False)
    window._pane_context_id = "pane-1"
    window._active_pane_id = "pane-1"
    window._pane_registry = {"pane-1": pane}
    window._call_js = lambda function_name, payload: calls.append((function_name, payload))

    window._replay_history(
        [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "system", "content": "s1"},
        ]
    )

    assert calls == [
        ("addUserMessage", "u1"),
        ("addAssistantMessage", "a1"),
        ("addSystemMessage", "s1"),
    ]
