from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from claude_code_gui.app.constants import (
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_ENDED,
)
from claude_code_gui.gi_runtime import Gdk

from claude_code_gui.ui import window as window_module
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
        self.stop_calls = 0

    def is_running(self) -> bool:
        return self._running

    def stop(self) -> None:
        self.stop_calls += 1
        self._running = False


class _FakeNotebookPage:
    def __init__(self, tab_id: str) -> None:
        self._tab_id = tab_id


class _FakeNotebook:
    def __init__(self, pages: list[_FakeNotebookPage], *, current_page: int = 0) -> None:
        self.pages = list(pages)
        self.current_page = current_page

    def page_num(self, page: _FakeNotebookPage) -> int:
        try:
            return self.pages.index(page)
        except ValueError:
            return -1

    def get_n_pages(self) -> int:
        return len(self.pages)

    def get_nth_page(self, page_num: int) -> _FakeNotebookPage | None:
        if 0 <= page_num < len(self.pages):
            return self.pages[page_num]
        return None

    def remove_page(self, page_num: int) -> None:
        self.pages.pop(page_num)
        if not self.pages:
            self.current_page = -1
        elif self.current_page >= len(self.pages):
            self.current_page = len(self.pages) - 1

    def set_current_page(self, page_num: int) -> None:
        self.current_page = page_num

    def get_current_page(self) -> int:
        return self.current_page


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


def _build_cross_provider_agent_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    active_provider_id: str,
) -> tuple[ClaudeCodeWindow, list[str | None]]:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    monkeypatch.setattr(window_module.GLib, "timeout_add", lambda *_args, **_kwargs: 1)

    window._pane_context_id = None
    window._pane_id_counter = 1
    window._agent_counter = 0
    window._max_panes = 4
    window._active_provider_id = active_provider_id
    window._project_folder = str(tmp_path)
    window._provider_binaries = {
        "claude": "/usr/bin/claude",
        "codex": "/usr/bin/codex",
    }
    window._sessions = []
    window._pane_registry = {
        "pane-1": SimpleNamespace(
            _is_agent=False,
            _agent_name=None,
            _agent_status="",
            _agent_status_label=None,
            _title_label=None,
            _session_label=None,
            _active_session_id=None,
            _provider_id_override=None,
        )
    }
    window._active_pane_id = "pane-1"
    window._ordered_pane_ids = lambda: list(window._pane_registry.keys())
    window._primary_pane_id = lambda: "pane-1"
    window._set_active_pane = lambda pane_id, grab_focus=False: setattr(window, "_active_pane_id", pane_id)
    window._update_pane_header = lambda _pane_id: None
    window._sync_pane_mode_to_webviews = lambda pane_id=None: None
    window._focus_chat_input_in_pane = lambda _pane_id: None
    window._refresh_session_list = lambda: None
    window._save_sessions_safe = lambda _context: True
    window._refresh_connection_state = lambda: None
    window._reset_conversation_state = lambda *_args, **_kwargs: None
    window._set_connection_state = lambda *_args, **_kwargs: None
    window._set_status_message = lambda *_args, **_kwargs: None
    window._add_system_message = lambda *_args, **_kwargs: None

    split_provider_calls: list[str | None] = []

    def _fake_split_active_pane(_orientation: Any, *, provider_id: str | None = None) -> str:
        split_provider_calls.append(provider_id)
        new_pane_id = window._new_pane_id()
        window._pane_registry[new_pane_id] = SimpleNamespace(
            _is_agent=False,
            _agent_name=None,
            _agent_status="",
            _agent_status_label=None,
            _title_label=None,
            _session_label=None,
            _active_session_id=None,
            _provider_id_override=None,
        )
        with window._pane_context(new_pane_id):
            window._start_new_session(window._project_folder, provider_id=provider_id)
        return new_pane_id

    window._split_active_pane = _fake_split_active_pane
    return window, split_provider_calls


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
    window._send_prompt_to_pane = lambda target_pane_id, prompt, keep_focus_on=None, kind="user": (
        sent_payload.update(
            {
                "target": target_pane_id,
                "prompt": prompt,
                "keep_focus_on": keep_focus_on,
                "kind": kind,
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
    assert sent_payload["kind"] == "agent_prompt"
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


@pytest.mark.parametrize(
    ("active_provider_id", "requested_provider_id"),
    [("claude", "codex"), ("codex", "claude")],
)
def test_agent_provider_spawn_creates_session_for_requested_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    active_provider_id: str,
    requested_provider_id: str,
) -> None:
    window, split_provider_calls = _build_cross_provider_agent_window(
        tmp_path,
        monkeypatch,
        active_provider_id=active_provider_id,
    )

    handled = window._handle_agent_command("pane-1", f"/agent {requested_provider_id}")

    assert handled is True
    assert split_provider_calls == [requested_provider_id]
    new_pane = window._pane_by_id("pane-2")
    assert new_pane is not None
    assert new_pane._provider_id_override == requested_provider_id
    created_session = window._find_session(new_pane._active_session_id)
    assert created_session is not None
    assert created_session.provider == requested_provider_id


def test_send_prompt_to_pane_passes_message_kind_to_webview() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    calls: list[tuple[str, str, dict[str, object]]] = []
    window._pane_registry = {"pane-2": SimpleNamespace()}
    window._call_js_in_pane = lambda pane_id, function_name, payload: calls.append((pane_id, function_name, payload)) or True

    sent = window._send_prompt_to_pane("pane-2", " delegated task ", kind="agent_prompt")

    assert sent is True
    assert calls == [
        (
            "pane-2",
            "hostSendMessage",
            {
                "text": "delegated task",
                "attachments": [],
                "kind": "agent_prompt",
            },
        )
    ]


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
    window._active_tab_id = None
    window._active_provider_id = "claude"
    window._binary_path = "/usr/bin/claude"
    window._session_search_query = ""
    window._session_filter = "all"
    window._save_sessions_safe = lambda _context: True
    window._refresh_session_list = lambda: None
    window._refresh_connection_state = lambda: None
    window._apply_session_to_controls = lambda _session, add_to_recent: None
    window._render_active_session_view = lambda: None
    window._sync_active_tab_state = lambda: None
    window._set_tab_provider_id = lambda _tab_id, _provider_id: None
    window._set_active_provider_context = (
        lambda _provider_id, *, session=None, persist_preference=False: True
    )
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


def test_pane_effective_provider_prefers_session_provider_over_global() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    pane = SimpleNamespace(
        _provider_id_override=None,
        _active_session_id="session-1",
    )
    window._pane_registry = {"pane-1": pane}
    window._tab_controllers = {}
    window._active_provider_id = "gemini"
    session = SimpleNamespace(provider="claude")
    window._find_session = lambda session_id: session if session_id == "session-1" else None

    assert window._pane_effective_provider_id("pane-1") == "claude"


def test_sync_window_chrome_for_active_pane_uses_active_session_provider() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    session = SimpleNamespace(provider="gemini", project_path="/tmp/project")
    pane = SimpleNamespace(_active_session_id="session-1")
    provider_calls: list[tuple[str, object]] = []
    project_paths: list[str] = []

    window._active_pane_id = "pane-1"
    window._pane_registry = {"pane-1": pane}
    window._find_session = lambda session_id: session if session_id == "session-1" else None
    window._pane_effective_provider_id = lambda pane_id: "gemini" if pane_id == "pane-1" else "claude"
    window._set_active_provider_context = (
        lambda provider_id, *, session=None, persist_preference=False: provider_calls.append((provider_id, session))
    )
    window._set_project_path_entry_text = lambda path_value: project_paths.append(path_value)
    window._update_project_folder_labels = lambda: None
    window._update_status_model_and_permission = lambda: None
    window._refresh_connection_state = lambda: None
    window._refresh_session_list = lambda: None
    window._update_all_pane_headers = lambda: None

    window._sync_window_chrome_for_active_pane()

    assert provider_calls == [("gemini", session)]
    assert project_paths == ["/tmp/project"]


def test_switch_to_session_rebinds_provider_context_for_target_session() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    session1 = SimpleNamespace(
        id="s1",
        provider="claude",
        status=SESSION_STATUS_ACTIVE,
        last_used_at="2026-01-01T10:00:00+00:00",
        project_path="/tmp/project",
        history=[],
        conversation_id=None,
        title="chat 1",
        model="sonnet",
        permission_mode="auto",
        reasoning_level="medium",
    )
    session2 = SimpleNamespace(
        id="s2",
        provider="gemini",
        status=SESSION_STATUS_ENDED,
        last_used_at="2026-01-01T09:00:00+00:00",
        project_path="/tmp/project",
        history=[],
        conversation_id=None,
        title="chat 2",
        model="pro",
        permission_mode="auto",
        reasoning_level="medium",
    )
    pane = SimpleNamespace(
        _active_session_id="s1",
        _active_request_token=None,
        _active_request_session_id=None,
        _claude_process=_SwitchFakeProcess(running=False),
    )
    provider_calls: list[tuple[str, object]] = []
    tab_provider_calls: list[tuple[str | None, str]] = []

    window._pane_context_id = "pane-1"
    window._active_pane_id = "pane-1"
    window._pane_registry = {"pane-1": pane}
    window._active_tab_id = "tab-1"
    window._active_provider_id = "claude"
    window._provider_unavailability_reason = lambda *_args, **_kwargs: None
    window._pane_effective_provider_id = lambda _pane_id: "claude"
    window._save_sessions_safe = lambda _context: True
    window._refresh_session_list = lambda: None
    window._refresh_connection_state = lambda: None
    window._apply_session_to_controls = lambda _session, add_to_recent: None
    window._render_active_session_view = lambda: None
    window._sync_active_tab_state = lambda: None
    window._set_status_message = lambda *_args, **_kwargs: None
    window._set_connection_state = lambda *_args, **_kwargs: None
    window._binary_path = "/usr/bin/gemini"
    window._set_tab_provider_id = lambda tab_id, provider_id: tab_provider_calls.append((tab_id, provider_id))
    window._set_active_provider_context = (
        lambda provider_id, *, session=None, persist_preference=False: provider_calls.append((provider_id, session))
    )
    window._sessions = [session1, session2]
    window._find_session = lambda sid: session1 if sid == "s1" else (session2 if sid == "s2" else None)
    window._get_active_session = lambda: window._find_session(window._active_session_id)

    window._switch_to_session("s2")

    assert window._active_session_id == "s2"
    assert provider_calls == [("gemini", session2)]
    assert tab_provider_calls == [("tab-1", "gemini")]


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
            {"role": "agent_prompt", "content": "p1"},
            {"role": "assistant", "content": "a1"},
            {"role": "system", "content": "s1"},
        ]
    )

    assert calls == [
        ("addUserMessage", "u1"),
        ("addAgentPromptMessage", "p1"),
        ("addAssistantMessage", "a1"),
        ("addSystemMessage", "s1"),
    ]


def test_render_active_session_view_preserves_agent_prompt_role_in_history_payload() -> None:
    window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
    js_calls: list[tuple[str, object]] = []
    session = SimpleNamespace(
        id="s1",
        history=[
            {"role": "agent_prompt", "content": "delegated"},
            {"role": "assistant", "content": "done"},
        ],
    )
    window._get_active_session = lambda: session
    window._is_request_bound_to_session = lambda _session_id: False
    window._call_js = lambda function_name, payload: js_calls.append((function_name, payload))
    window._set_typing = lambda _value: None
    window._update_context_indicator = lambda: None
    window._active_assistant_message = ""
    window._has_messages = False
    window._context_char_count = 0

    window._render_active_session_view()

    assert js_calls[0] == (
        "resetMessageHistory",
        [
            {"role": "agent_prompt", "content": "delegated"},
            {"role": "assistant", "content": "done"},
        ],
    )
    assert window._has_messages is True


class TestSessionTabs:
    def test_provider_button_same_provider_only_focuses_current_tab(self) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        focused: list[str] = []
        opened_tabs: list[str] = []
        switched_tabs: list[str] = []

        window._active_pane_id = "pane-1"
        window._pane_effective_provider_id = lambda _pane_id: "claude"
        window._focus_chat_input_in_pane = lambda pane_id: focused.append(pane_id)
        window._active_tab_has_chat_activity = lambda: True
        window._open_provider_tab = lambda provider_id: opened_tabs.append(provider_id)
        window._switch_active_tab_provider = lambda provider_id: switched_tabs.append(provider_id)

        window._on_provider_button_clicked(None, "claude")

        assert focused == ["pane-1"]
        assert opened_tabs == []
        assert switched_tabs == []

    def test_provider_button_with_active_chat_opens_new_tab(self) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        opened_tabs: list[str] = []
        switched_tabs: list[str] = []

        window._active_pane_id = "pane-1"
        window._pane_effective_provider_id = lambda _pane_id: "claude"
        window._active_tab_has_chat_activity = lambda: True
        window._open_provider_tab = lambda provider_id: opened_tabs.append(provider_id)
        window._switch_active_tab_provider = lambda provider_id: switched_tabs.append(provider_id)

        window._on_provider_button_clicked(None, "gemini")

        assert opened_tabs == ["gemini"]
        assert switched_tabs == []

    def test_provider_button_with_split_tab_chat_in_sibling_pane_opens_new_tab(self) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        opened_tabs: list[str] = []
        switched_tabs: list[str] = []

        window._active_pane_id = "pane-1"
        window._active_tab_id = "tab-1"
        window._active_provider_id = "claude"
        window._tab_controllers = {
            "tab-1": SimpleNamespace(
                tab_id="tab-1",
                _pane_tree_root_widget=object(),
                _active_pane_id="pane-1",
            )
        }
        window._pane_registry = {
            "pane-1": SimpleNamespace(
                _claude_process=_SwitchFakeProcess(running=False),
                _active_session_id=None,
                _active_request_session_id=None,
                _active_assistant_message="",
                _has_messages=False,
                _conversation_id=None,
            ),
            "pane-2": SimpleNamespace(
                _claude_process=_SwitchFakeProcess(running=False),
                _active_session_id="session-2",
                _active_request_session_id=None,
                _active_assistant_message="",
                _has_messages=False,
                _conversation_id=None,
            ),
        }
        window._session_runtime_tracker = set()
        window._pane_ids_in_widget = lambda _widget: ["pane-1", "pane-2"]
        session = SimpleNamespace(
            id="session-2",
            status=SESSION_STATUS_ACTIVE,
            history=[{"role": "user", "content": "hello"}],
            conversation_id="conv-2",
        )
        window._find_session = lambda sid: session if sid == "session-2" else None
        window._pane_effective_provider_id = lambda _pane_id: "claude"
        window._open_provider_tab = lambda provider_id: opened_tabs.append(provider_id)
        window._switch_active_tab_provider = lambda provider_id: switched_tabs.append(provider_id)

        window._on_provider_button_clicked(None, "gemini")

        assert window._active_tab_has_chat_activity() is True
        assert opened_tabs == ["gemini"]
        assert switched_tabs == []

    def test_provider_button_without_active_chat_reuses_current_tab(self) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        opened_tabs: list[str] = []
        switched_tabs: list[str] = []

        window._active_pane_id = "pane-1"
        window._pane_effective_provider_id = lambda _pane_id: "claude"
        window._active_tab_has_chat_activity = lambda: False
        window._open_provider_tab = lambda provider_id: opened_tabs.append(provider_id)
        window._switch_active_tab_provider = lambda provider_id: switched_tabs.append(provider_id)

        window._on_provider_button_clicked(None, "gemini")

        assert opened_tabs == []
        assert switched_tabs == ["gemini"]

    def test_new_chat_busy_opens_new_tab(self, tmp_path: Path) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        opened_tabs: list[str] = []
        started_sessions: list[str] = []
        window._project_folder = str(tmp_path)
        window._pane_context_id = None
        window._active_pane_id = "pane-1"
        window._pane_registry = {
            "pane-1": SimpleNamespace(
                _claude_process=_SwitchFakeProcess(running=True),
                _active_session_id="session-1",
            )
        }
        window._set_status_message = lambda *_args, **_kwargs: None
        window._prompt_for_project_folder = lambda: None
        window._open_new_session_tab = lambda folder: opened_tabs.append(folder)
        window._start_new_session = lambda folder: started_sessions.append(folder)
        window._session_runtime_tracker = set()

        window._on_new_session_clicked(None)

        assert opened_tabs == [str(tmp_path)]
        assert started_sessions == []

    def test_new_chat_never_run_reuses_tab(self, tmp_path: Path) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        opened_tabs: list[str] = []
        started_sessions: list[str] = []
        window._project_folder = str(tmp_path)
        window._pane_context_id = None
        window._active_pane_id = "pane-1"
        window._pane_registry = {
            "pane-1": SimpleNamespace(
                _claude_process=_SwitchFakeProcess(running=False),
                _active_session_id="session-1",
            )
        }
        window._set_status_message = lambda *_args, **_kwargs: None
        window._prompt_for_project_folder = lambda: None
        window._open_new_session_tab = lambda folder: opened_tabs.append(folder)
        window._start_new_session = lambda folder: started_sessions.append(folder)
        window._session_runtime_tracker = set()

        window._on_new_session_clicked(None)

        assert opened_tabs == []
        assert started_sessions == [str(tmp_path)]

    def test_new_chat_previously_run_opens_new_tab(self, tmp_path: Path) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        opened_tabs: list[str] = []
        started_sessions: list[str] = []
        window._project_folder = str(tmp_path)
        window._pane_context_id = None
        window._active_pane_id = "pane-1"
        window._pane_registry = {
            "pane-1": SimpleNamespace(
                _claude_process=_SwitchFakeProcess(running=False),
                _active_session_id="session-1",
            )
        }
        window._set_status_message = lambda *_args, **_kwargs: None
        window._prompt_for_project_folder = lambda: None
        window._open_new_session_tab = lambda folder: opened_tabs.append(folder)
        window._start_new_session = lambda folder: started_sessions.append(folder)
        window._session_runtime_tracker = {"session-1"}

        window._on_new_session_clicked(None)

        assert opened_tabs == [str(tmp_path)]
        assert started_sessions == []

    def test_close_active_tab_falls_to_neighbor(self) -> None:
        window = ClaudeCodeWindow.__new__(ClaudeCodeWindow)
        page_1 = _FakeNotebookPage("tab-1")
        page_2 = _FakeNotebookPage("tab-2")
        notebook = _FakeNotebook([page_1, page_2], current_page=0)
        pane_1_process = _SwitchFakeProcess(running=False)
        pane_2_process = _SwitchFakeProcess(running=True)
        session_1 = SimpleNamespace(
            id="session-1",
            status=SESSION_STATUS_ACTIVE,
            last_used_at="2026-01-01T10:00:00+00:00",
        )
        session_2 = SimpleNamespace(
            id="session-2",
            status=SESSION_STATUS_ACTIVE,
            last_used_at="2026-01-01T09:00:00+00:00",
        )
        activated_tabs: list[str] = []
        created_tabs: list[str] = []
        saved_contexts: list[str] = []
        refresh_calls = 0

        window._tab_notebook = notebook
        window._tab_controllers = {
            "tab-1": SimpleNamespace(
                tab_id="tab-1",
                _page=page_1,
                _workspace_host=None,
                _pane_tree_root_widget=SimpleNamespace(_pane_id="pane-1"),
                _active_pane_id="pane-1",
                session_id="session-1",
                _title_label=None,
                _label_box=None,
                _close_button=None,
            ),
            "tab-2": SimpleNamespace(
                tab_id="tab-2",
                _page=page_2,
                _workspace_host=None,
                _pane_tree_root_widget=SimpleNamespace(_pane_id="pane-2"),
                _active_pane_id="pane-2",
                session_id="session-2",
                _title_label=None,
                _label_box=None,
                _close_button=None,
            ),
        }
        window._active_tab_id = "tab-1"
        window._active_pane_id = "pane-1"
        window._workspace_host = None
        window._workspace_container = SimpleNamespace(_pane_id="pane-1")
        window._pane_registry = {
            "pane-1": SimpleNamespace(
                _claude_process=pane_1_process,
                _request_temp_files={},
                _active_session_id="session-1",
                _active_request_session_id=None,
            ),
            "pane-2": SimpleNamespace(
                _claude_process=pane_2_process,
                _request_temp_files={},
                _active_session_id="session-2",
                _active_request_session_id=None,
            ),
        }
        window._sessions = [session_1, session_2]
        window._find_session = lambda sid: session_1 if sid == "session-1" else (session_2 if sid == "session-2" else None)
        window._set_active_tab = lambda tab_id, grab_focus=False: (
            activated_tabs.append(tab_id),
            setattr(window, "_active_tab_id", tab_id),
        )

        def _record_refresh() -> None:
            nonlocal refresh_calls
            refresh_calls += 1

        window._refresh_session_list = _record_refresh
        window._save_sessions_safe = lambda context: saved_contexts.append(context) or True
        window._update_pane_close_buttons = lambda: None
        window._update_all_pane_headers = lambda: None

        def _create_workspace_tab(*, make_active: bool = False) -> str:
            created_tabs.append("tab-3")
            page_3 = _FakeNotebookPage("tab-3")
            notebook.pages.append(page_3)
            window._tab_controllers["tab-3"] = SimpleNamespace(
                tab_id="tab-3",
                _page=page_3,
                _workspace_host=None,
                _pane_tree_root_widget=SimpleNamespace(_pane_id="pane-3"),
                _active_pane_id="pane-3",
                _title_label=None,
                _label_box=None,
                _close_button=None,
            )
            window._pane_registry["pane-3"] = SimpleNamespace(
                _claude_process=_SwitchFakeProcess(running=False),
                _request_temp_files={},
            )
            if make_active:
                notebook.set_current_page(notebook.page_num(page_3))
                window._active_tab_id = "tab-3"
            return "tab-3"

        window._create_workspace_tab = _create_workspace_tab

        window._close_workspace_tab("tab-1")

        assert activated_tabs == ["tab-2"]
        assert pane_1_process.stop_calls == 1
        assert session_1.status == SESSION_STATUS_ARCHIVED
        assert session_2.status == SESSION_STATUS_ACTIVE
        assert "tab-1" not in window._tab_controllers
        assert notebook.get_n_pages() == 1

        window._close_workspace_tab("tab-2")

        assert pane_2_process.stop_calls == 1
        assert session_2.status == SESSION_STATUS_ARCHIVED
        assert created_tabs == ["tab-3"]
        assert notebook.get_n_pages() == 1
        assert set(window._tab_controllers) == {"tab-3"}
        assert refresh_calls == 2
        assert saved_contexts == ["Could not save sessions", "Could not save sessions"]
