"""Main application window with WebKit2 chat UI and session management."""

from __future__ import annotations

import base64
from contextlib import contextmanager
import copy
import json
import logging
import math
import mimetypes
import os
import re
import shlex
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_code_gui.gi_runtime import Gdk, Gio, GLib, Gtk, Pango, WebKit, GTK4

from claude_code_gui.app.constants import (
    APP_DEFAULT_HEIGHT,
    APP_DEFAULT_WIDTH,
    APP_MIN_HEIGHT,
    APP_MIN_WIDTH,
    APP_NAME,
    ATTACHMENT_MAX_BYTES,
    CONNECTION_CONNECTED,
    CONNECTION_DISCONNECTED,
    CONNECTION_ERROR,
    CONNECTION_STARTING,
    CONTEXT_MAX_TOKENS,
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_ENDED,
    SESSION_STATUS_ERROR,
    SESSION_STATUSES,
    SIDEBAR_COLLAPSED_WIDTH,
    SIDEBAR_OPEN_WIDTH,
    STATUS_ERROR,
    STATUS_INFO,
    STATUS_MUTED,
    STATUS_WARNING,
)
from claude_code_gui.domain.app_settings import (
    get_reasoning_options,
    load_settings,
    save_settings,
)
from claude_code_gui.assets.chat_template import CHAT_WEBVIEW_HTML
from claude_code_gui.assets.gtk_css import build_gtk_css
from claude_code_gui.core.model_permissions import (
    normalize_model_value,
    normalize_permission_value,
)
from claude_code_gui.core.paths import format_path, normalize_folder, shorten_path
from claude_code_gui.core.time_utils import current_timestamp, parse_timestamp
from claude_code_gui.domain.claude_types import ClaudeRunConfig
from claude_code_gui.domain.provider import (
    DEFAULT_PROVIDER_ID,
    PROVIDERS,
    ProviderConfig,
    refresh_provider_registry,
    normalize_provider_id,
)
from claude_code_gui.domain.session import SessionRecord
from claude_code_gui.runtime.claude_process import ClaudeProcess
from claude_code_gui.services.attachment_service import (
    cleanup_temp_paths,
    compose_message_with_attachments,
    decode_data_url,
    materialize_attachments,
    parse_send_payload,
)
from claude_code_gui.services.binary_probe import (
    binary_exists,
    CliCapabilities,
    detect_cli_flag_support,
    find_provider_binary,
    detect_provider_model_options,
    is_codex_authenticated,
)
from claude_code_gui.storage.config_paths import RECENT_FOLDERS_LIMIT
from claude_code_gui.storage.recent_folders_store import (
    load_recent_folders,
    save_recent_folders,
)
from claude_code_gui.storage.sessions_store import load_sessions, save_sessions


logger = logging.getLogger(__name__)

_AGENTCTL_HINT = (
    "You are the main orchestrator for this chat. To delegate work, control panes by emitting "
    "lines starting with '/agent', 'agent', or '@agentctl'. Commands: new <name>, list, focus <target>, "
    "send <target> <prompt>, summarize <target> <source1> <source2>..., close <target>. "
    "Emit commands only when needed."
)
_AGENTCTL_COMMAND_KEYWORDS = {
    "?",
    "add",
    "ask",
    "close",
    "create",
    "focus",
    "go",
    "goto",
    "help",
    "h",
    "kill",
    "list",
    "ls",
    "merge",
    "new",
    "previous",
    "prev",
    "remove",
    "run",
    "send",
    "spawn",
    "summarize",
    "summary",
    "switch",
}

_ICONS_DIR = Path(__file__).resolve().parents[2] / "icons"


def _resolve_icons_dir() -> Path:
    """Resolve the icons directory from likely source layouts."""
    for candidate in (
        Path(__file__).resolve().parent.parent.parent / "icons",
        Path(__file__).resolve().parent.parent / "icons",
        Path(__file__).resolve().parent / "icons",
        _ICONS_DIR,
        Path.cwd() / "icons",
    ):
        if candidate.is_dir():
            return candidate
    return _ICONS_DIR


_ICONS_DIR = _resolve_icons_dir()


class PaneController:
    """Encapsulates one pane's WebView, process and request state."""

    def __init__(self, pane_id: str) -> None:
        self.pane_id = pane_id
        self._container: Gtk.Box | None = None
        self._close_button: Gtk.Button | None = None
        self._title_label: Gtk.Label | None = None
        self._session_label: Gtk.Label | None = None
        self._webview: WebKit.WebView | None = None
        self._webview_user_content_manager: WebKit.UserContentManager | None = None
        self._webview_ready = False
        self._pending_webview_scripts: list[str] = []
        self._chat_shell: Gtk.EventBox | None = None

        self._claude_process: ClaudeProcess | None = None
        self._active_session_id: str | None = None
        self._conversation_id: str | None = None
        self._active_request_token: str | None = None
        self._active_assistant_message = ""
        self._request_temp_files: dict[str, list[str]] = {}
        self._permission_request_pending = False
        self._allowed_tools: set[str] = set()
        self._has_messages = False
        self._last_request_failed = False
        self._is_agent = False
        self._agent_name: str | None = None


class ClaudeCodeWindow(Gtk.Window):
    """Single-window Claude Code shell with WebKit2 chat UI and session context."""

    def __init__(self) -> None:
        super().__init__(title=APP_NAME)
        self._active_provider_id: str = DEFAULT_PROVIDER_ID
        self._provider_binaries: dict[str, str | None] = {
            provider_id: find_provider_binary(list(provider.binary_names))
            for provider_id, provider in PROVIDERS.items()
        }
        self._agentctl_auto_enabled = bool(load_settings().get("agentctl_auto_enabled", True))
        self.set_decorated(True)
        self.set_default_size(APP_DEFAULT_WIDTH, APP_DEFAULT_HEIGHT)
        self.set_size_request(APP_MIN_WIDTH, APP_MIN_HEIGHT)

        self._active_pane_id: str | None = None
        self._pane_registry: dict[str, PaneController] = {}
        self._workspace_container: Gtk.Widget | None = None
        self._workspace_host: Gtk.Box | None = None
        self._pane_context_id: str | None = None
        self._pane_id_counter = 0
        self._agent_counter = 0
        self._max_panes = 4

        self._sidebar_container: Gtk.Box | None = None
        self._sidebar_toggle_button: Gtk.Button | None = None
        self._provider_toggle_button: Gtk.Button | None = None
        self._provider_toggle_button_icon: Gtk.Image | None = None
        self._provider_toggle_button_label: Gtk.Label | None = None
        self._settings_button: Gtk.Button | None = None
        self._sidebar_current_width = float(SIDEBAR_OPEN_WIDTH)
        self._sidebar_expanded = True
        self._sidebar_animation_id: int | None = None
        self._sidebar_toggle_pulse_animation_id: int | None = None
        self._sidebar_expanded_only_widgets: list[Gtk.Widget] = []
        self._css_provider: Gtk.CssProvider | None = None

        self._window_fade_animation_id: int | None = None
        self._window_fade_started = False

        self._status_fade_animation_id: int | None = None
        self._status_fade_widgets: list[Gtk.Widget] = []
        self._chat_reveal_animation_id: int | None = None
        self._chat_reveal_widgets: list[tuple[Gtk.Widget, float]] = []
        self._chat_pulse_animation_id: int | None = None
        self._last_slash_commands_cache = ""

        self._project_path_entry: Gtk.Entry | None = None
        self._project_path_popover: Gtk.Popover | None = None
        self._project_path_suggestion_scroll: Gtk.ScrolledWindow | None = None
        self._project_path_suggestion_list: Gtk.ListBox | None = None
        self._project_path_suggestions: list[str] = []
        self._project_path_selected_index = -1
        self._suppress_project_entry_change = False
        self._session_list_box: Gtk.Box | None = None
        self._session_empty_label: Gtk.Label | None = None
        self._sessions_title_label: Gtk.Label | None = None
        self._session_search_entry: Gtk.Entry | None = None
        self._session_filter_buttons: dict[str, Gtk.Button] = {}
        self._session_filter = "all"
        self._session_search_query = ""
        self._window_has_focus = True
        self._notification_counter = 0

        self._connection_dot: Gtk.Label | None = None
        self._connection_label: Gtk.Label | None = None
        self._context_usage_label: Gtk.Label | None = None
        self._context_progress: Gtk.ProgressBar | None = None
        self._session_limit_label: Gtk.Label | None = None
        self._weekly_limit_label: Gtk.Label | None = None
        self._status_message_label: Gtk.Label | None = None
        self._session_timer_label: Gtk.Label | None = None
        self._last_status_message = ""
        self._context_char_count = 0
        self._session_cost_usd = 0.0
        self._session_tokens = 0
        self._gtk_settings_notify_id: int | None = None

        self._model_options: list[tuple[str, str]] = list(self._active_provider.model_options)
        self._permission_options: list[tuple[str, str, bool]] = list(self._active_provider.permission_options)
        self._selected_model_index = 1 if len(self._model_options) > 1 else 0
        self._selected_permission_index = 0
        self._reasoning_options: list[tuple[str, str, str]] = get_reasoning_options()
        self._selected_reasoning_index = self._reasoning_index_from_value("medium")

        self._project_folder = normalize_folder(os.getcwd())
        self._recent_folders = load_recent_folders(self._project_folder)

        self._binary_path = self._provider_binaries.get(self._active_provider_id)
        self._provider_cli_caps: dict[str, CliCapabilities] = {}
        self._provider_cli_probe_inflight: set[str] = set()
        self._stream_json_requires_verbose = True
        self._provider_model_probe_done: set[str] = set()

        self._session_started_us = GLib.get_monotonic_time()
        self._session_timer_id: int | None = None
        self._sessions: list[SessionRecord] = []

        self._set_dark_theme_preference()
        self._bind_gtk_animation_setting()
        self._install_css()
        self._build_ui()
        self._apply_provider_branding()
        self._load_sessions_into_state()
        self._refresh_session_list()
        self._update_provider_toggle_button()
        GLib.idle_add(self._refresh_session_list_idle)

        self.connect("destroy", self._on_destroy)
        if not self._connect_optional_signal(self, "map-event", self._on_map_event):
            GLib.idle_add(self._on_window_mapped_fallback)
        if not self._connect_optional_signal(self, "focus-in-event", self._on_window_focus_in):
            self.connect("notify::is-active", self._on_window_active_changed)
        self._connect_optional_signal(self, "focus-out-event", self._on_window_focus_out)
        if not self._connect_optional_signal(self, "key-press-event", self._on_window_key_press):
            self._install_window_key_controller()

        if self._active_session_id is None:
            self._set_status_message("No active session. Click + New Chat to start.", STATUS_INFO)
        else:
            self._set_status_message("Session ready. Type a message below.", STATUS_MUTED)

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            self._show_missing_binary_error()
        else:
            self._set_connection_state(CONNECTION_CONNECTED)

        for provider_id, binary_path in self._provider_binaries.items():
            self._detect_provider_models_async(binary_path, provider_id)
            self._detect_cli_flag_support_async(binary_path, provider_id)

        self._start_status_fade_in()
        self._refresh_connection_state()

    @staticmethod
    def _set_dark_theme_preference() -> None:
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)

    @staticmethod
    def _connect_optional_signal(widget: Gtk.Widget, signal_name: str, callback: Any) -> bool:
        try:
            widget.connect(signal_name, callback)
            return True
        except TypeError:
            return False

    def _on_window_mapped_fallback(self) -> bool:
        self._on_map_event(self, None)
        return False

    def _on_window_active_changed(self, _widget: Gtk.Widget, _param: Any) -> None:
        try:
            self._window_has_focus = bool(self.is_active())
        except Exception:
            self._window_has_focus = True

    def _install_window_key_controller(self) -> None:
        if not GTK4:
            return
        controller = Gtk.EventControllerKey.new()
        controller.connect("key-pressed", self._on_window_key_pressed_controller)
        self.add_controller(controller)

    def _on_window_key_pressed_controller(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        return self._handle_window_key_press(keyval, state)

    def _bind_gtk_animation_setting(self) -> None:
        settings = Gtk.Settings.get_default()
        if settings is None:
            return
        self._gtk_settings_notify_id = settings.connect(
            "notify::gtk-enable-animations",
            self._on_gtk_enable_animations_changed,
        )

    def _on_gtk_enable_animations_changed(self, _settings: Gtk.Settings, _param: Any) -> None:
        provider = self._active_provider
        self._swap_css(
            provider.colors,
            provider.accent_rgb,
            provider.accent_soft_rgb,
            reduced_motion=self._reduced_motion_from_gtk(),
        )

    @property
    def _active_provider(self) -> ProviderConfig:
        return PROVIDERS[self._active_provider_id]

    def _provider_display_name(self, provider_id: str | None = None) -> str:
        provider = PROVIDERS[normalize_provider_id(provider_id or self._active_provider_id)]
        return provider.name

    def _provider_cli_label(self, provider_id: str | None = None) -> str:
        return f"{self._provider_display_name(provider_id)} CLI"

    def _provider_button_label(self, provider_id: str | None = None) -> str:
        provider = PROVIDERS[normalize_provider_id(provider_id or self._active_provider_id)]
        if self._provider_icon_path(provider.id) is not None:
            return provider.name
        return provider.name

    def _provider_icon_path(self, provider_id: str | None = None) -> Path | None:
        provider_key = normalize_provider_id(provider_id or self._active_provider_id)
        provider = PROVIDERS[provider_key]
        icon_value = provider.icon.strip()
        icon_value_lower = icon_value.lower()
        has_explicit_path = any(sep in icon_value for sep in ("/", "\\")) or icon_value.startswith(".")
        icon_name = Path(icon_value).name.lower()

        if not has_explicit_path:
            if provider_key == "claude" and (
                icon_value_lower in {
                    "claude",
                    "claude.svg",
                    "claude-color.svg",
                    "claude-text.svg",
                    "read",
                    "✺",
                    "claude (1).svg",
                    "claude-color (1).svg",
                    "claude-text (1).svg",
                }
                or icon_name.startswith("claude-text")
            ):
                icon_value = "claude-color.svg"
            elif provider_key == "codex" and (
                icon_value_lower in {
                    "codex",
                    "codex.svg",
                    "codex-color.svg",
                    "codex-text.svg",
                    "codex-white.svg",
                    "read",
                    "⌘",
                    "codex-text (1).svg",
                    "codex (1).svg",
                }
                or icon_name.startswith("codex-text")
            ):
                icon_value = "codex-white.svg"

        icon_candidates: list[Path] = []
        if icon_value:
            icon_candidates.append(Path(icon_value))

        if provider_key == "claude":
            icon_candidates.extend(
                [
                    Path("claude-color.svg"),
                    Path("claude.svg"),
                    Path("claude-text.svg"),
                    Path("claude.webp"),
                ],
            )
        elif provider_key == "codex":
            icon_candidates.extend(
                [
                    Path("codex-white.svg"),
                    Path("codex-text.svg"),
                    Path("codex-text (1).svg"),
                    Path("codex-color.svg"),
                    Path("codex.svg"),
                    Path("codex.webp"),
                ],
            )
        else:
            icon_candidates.append(_ICONS_DIR / f"{provider_key}.svg")

        seen: set[str] = set()
        unique_candidates: list[Path] = []
        for candidate in icon_candidates:
            candidate_key = candidate.name.lower()
            if candidate_key in seen:
                continue
            seen.add(candidate_key)
            unique_candidates.append(candidate)

        for candidate in unique_candidates:
            if candidate.is_absolute():
                icon_path = candidate
            else:
                explicit_relative_path = Path(__file__).resolve().parent / candidate
                if candidate.parent != Path(".") and explicit_relative_path.exists():
                    icon_path = explicit_relative_path
                elif candidate.exists():
                    icon_path = candidate
                else:
                    icon_path = _ICONS_DIR / candidate.name
            if icon_path.exists() and icon_path.is_file():
                return icon_path

        for suffix in (".svg", ".png", ".webp"):
            candidate = _ICONS_DIR / f"{provider_key}{suffix}"
            if candidate.exists() and candidate.is_file():
                return candidate

        for suffix in (".svg", ".png", ".webp"):
            candidate = _ICONS_DIR / f"{provider_key}-color{suffix}"
            if candidate.exists() and candidate.is_file():
                return candidate

        for candidate in _ICONS_DIR.glob(f"{provider_key}.*"):
            if candidate.is_file() and candidate.suffix.lower() in {".svg", ".png", ".webp"}:
                return candidate
        return None

    def _provider_icon_data_uri(self, provider_id: str | None = None) -> str | None:
        icon_path = self._provider_icon_path(provider_id)
        if icon_path is None:
            return None
        try:
            icon_bytes = icon_path.read_bytes()
        except OSError:
            return None

        mime_type = mimetypes.guess_type(str(icon_path))[0] or ""
        if not mime_type:
            if icon_path.suffix.lower() == ".svg":
                mime_type = "image/svg+xml"
            else:
                mime_type = "application/octet-stream"
        return f"data:{mime_type};base64,{base64.b64encode(icon_bytes).decode('ascii')}"

    def _provider_switch_icon_path(self, provider_id: str | None = None) -> Path | None:
        provider_key = normalize_provider_id(provider_id or self._active_provider_id)
        if provider_key == "claude":
            for name in ("claude-switch.svg", "claude.svg", "claude-color.svg", "claude-text.svg"):
                preferred = _ICONS_DIR / name
                if preferred.exists() and preferred.is_file():
                    return preferred
        if provider_key == "codex":
            for name in ("codex-switch.svg", "codex.svg", "codex-white.svg", "codex-text.svg", "codex-color.svg"):
                preferred = _ICONS_DIR / name
                if preferred.exists() and preferred.is_file():
                    return preferred
        return self._provider_icon_path(provider_key)

    def _provider_window_title(self, provider_id: str | None = None) -> str:
        return f"{self._provider_display_name(provider_id)} Code"

    def _new_pane_id(self) -> str:
        self._pane_id_counter += 1
        return f"pane-{self._pane_id_counter}"

    def _pane_by_id(self, pane_id: str | None) -> PaneController | None:
        if pane_id is None:
            return None
        return self._pane_registry.get(pane_id)

    def _is_active_pane(self, pane_id: str) -> bool:
        return pane_id == self._active_pane_id

    def _state_pane(self) -> PaneController | None:
        if self._pane_context_id is not None:
            pane = self._pane_by_id(self._pane_context_id)
            if pane is not None:
                return pane
        return self._pane_by_id(self._active_pane_id)

    def _state_pane_or_raise(self) -> PaneController:
        pane = self._state_pane()
        if pane is None:
            raise RuntimeError("No active pane is available.")
        return pane

    @contextmanager
    def _pane_context(self, pane_id: str):
        previous = self._pane_context_id
        self._pane_context_id = pane_id
        try:
            yield
        finally:
            self._pane_context_id = previous

    @property
    def _webview(self) -> WebKit.WebView | None:
        pane = self._state_pane()
        return pane._webview if pane is not None else None

    @_webview.setter
    def _webview(self, value: WebKit.WebView | None) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._webview = value

    @property
    def _webview_user_content_manager(self) -> WebKit.UserContentManager | None:
        pane = self._state_pane()
        return pane._webview_user_content_manager if pane is not None else None

    @_webview_user_content_manager.setter
    def _webview_user_content_manager(self, value: WebKit.UserContentManager | None) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._webview_user_content_manager = value

    @property
    def _webview_ready(self) -> bool:
        pane = self._state_pane()
        return bool(pane._webview_ready) if pane is not None else False

    @_webview_ready.setter
    def _webview_ready(self, value: bool) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._webview_ready = bool(value)

    @property
    def _pending_webview_scripts(self) -> list[str]:
        pane = self._state_pane()
        return pane._pending_webview_scripts if pane is not None else []

    @_pending_webview_scripts.setter
    def _pending_webview_scripts(self, value: list[str]) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._pending_webview_scripts = value

    @property
    def _chat_shell(self) -> Gtk.EventBox | None:
        pane = self._state_pane()
        return pane._chat_shell if pane is not None else None

    @_chat_shell.setter
    def _chat_shell(self, value: Gtk.EventBox | None) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._chat_shell = value

    @property
    def _claude_process(self) -> ClaudeProcess:
        pane = self._state_pane_or_raise()
        if pane._claude_process is None:
            raise RuntimeError("Pane process is not initialized.")
        return pane._claude_process

    @_claude_process.setter
    def _claude_process(self, value: ClaudeProcess) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._claude_process = value

    @property
    def _conversation_id(self) -> str | None:
        pane = self._state_pane()
        return pane._conversation_id if pane is not None else None

    @_conversation_id.setter
    def _conversation_id(self, value: str | None) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._conversation_id = value

    @property
    def _active_request_token(self) -> str | None:
        pane = self._state_pane()
        return pane._active_request_token if pane is not None else None

    @_active_request_token.setter
    def _active_request_token(self, value: str | None) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._active_request_token = value

    @property
    def _active_assistant_message(self) -> str:
        pane = self._state_pane()
        return pane._active_assistant_message if pane is not None else ""

    @_active_assistant_message.setter
    def _active_assistant_message(self, value: str) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._active_assistant_message = value

    @property
    def _request_temp_files(self) -> dict[str, list[str]]:
        pane = self._state_pane()
        return pane._request_temp_files if pane is not None else {}

    @_request_temp_files.setter
    def _request_temp_files(self, value: dict[str, list[str]]) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._request_temp_files = value

    @property
    def _permission_request_pending(self) -> bool:
        pane = self._state_pane()
        return bool(pane._permission_request_pending) if pane is not None else False

    @_permission_request_pending.setter
    def _permission_request_pending(self, value: bool) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._permission_request_pending = bool(value)

    @property
    def _allowed_tools(self) -> set[str]:
        pane = self._state_pane()
        return pane._allowed_tools if pane is not None else set()

    @_allowed_tools.setter
    def _allowed_tools(self, value: set[str]) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._allowed_tools = value

    @property
    def _has_messages(self) -> bool:
        pane = self._state_pane()
        return bool(pane._has_messages) if pane is not None else False

    @_has_messages.setter
    def _has_messages(self, value: bool) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._has_messages = bool(value)

    @property
    def _last_request_failed(self) -> bool:
        pane = self._state_pane()
        return bool(pane._last_request_failed) if pane is not None else False

    @_last_request_failed.setter
    def _last_request_failed(self, value: bool) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._last_request_failed = bool(value)

    @property
    def _active_session_id(self) -> str | None:
        pane = self._state_pane()
        return pane._active_session_id if pane is not None else None

    @_active_session_id.setter
    def _active_session_id(self, value: str | None) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._active_session_id = value

    def _install_css(self) -> None:
        provider = self._active_provider
        self._swap_css(
            provider.colors,
            provider.accent_rgb,
            provider.accent_soft_rgb,
            reduced_motion=self._reduced_motion_from_gtk(),
        )

    def _reduced_motion_from_gtk(self) -> bool:
        settings = Gtk.Settings.get_default()
        if settings is None:
            return False
        try:
            return not bool(settings.get_property("gtk-enable-animations"))
        except Exception:
            return False

    def _sync_reduced_motion_to_webviews(self) -> None:
        reduced_motion = self._reduced_motion_from_gtk()
        for pane_id in list(self._pane_registry.keys()):
            self._call_js_in_pane(pane_id, "setReducedMotion", reduced_motion)

    def _swap_css(
        self,
        colors: dict[str, str],
        accent_rgb: tuple[int, int, int],
        accent_soft_rgb: tuple[int, int, int],
        reduced_motion: bool = False,
    ) -> None:
        css = build_gtk_css(
            colors,
            accent_rgb,
            accent_soft_rgb,
            reduced_motion=reduced_motion,
        )
        new_provider = Gtk.CssProvider()
        new_provider.load_from_data(css.encode("utf-8"))

        if GTK4:
            display = Gdk.Display.get_default()
            if display is None:
                return
            Gtk.StyleContext.add_provider_for_display(
                display,
                new_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            if self._css_provider is not None:
                Gtk.StyleContext.remove_provider_for_display(display, self._css_provider)
        else:
            screen = Gdk.Screen.get_default()
            if screen is None:
                return
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                new_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            if self._css_provider is not None:
                Gtk.StyleContext.remove_provider_for_screen(screen, self._css_provider)
        self._css_provider = new_provider
        self._sync_reduced_motion_to_webviews()

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("app-root")
        self.add(root)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        content.get_style_context().add_class("main-content")
        root.pack_start(content, True, True, 0)

        sidebar = self._build_sidebar()
        content.pack_start(sidebar, False, False, 0)

        workspace_panel = self._build_workspace_panel()
        content.pack_start(workspace_panel, True, True, 0)

        status_bar = self._build_status_bar()
        root.pack_end(status_bar, False, False, 0)

        self._update_project_folder_labels()
        self._update_status_model_and_permission()
        self._update_context_indicator()
        self._start_chat_reveal_in()

        self._session_timer_id = GLib.timeout_add_seconds(1, self._update_session_timer)

    def _build_workspace_panel(self) -> Gtk.Box:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.set_hexpand(True)
        panel.set_vexpand(True)

        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrap.get_style_context().add_class("chat-wrap")
        wrap.set_hexpand(True)
        wrap.set_vexpand(True)
        panel.pack_start(wrap, True, True, 0)

        workspace_host = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        workspace_host.set_hexpand(True)
        workspace_host.set_vexpand(True)
        wrap.pack_start(workspace_host, True, True, 0)
        self._workspace_host = workspace_host

        initial_pane_id = self._new_pane_id()
        initial_pane = self._create_pane_controller(initial_pane_id)
        initial_view = self.build_pane_chat_view(initial_pane_id)
        initial_pane._container = initial_view
        initial_view._pane_id = initial_pane_id
        workspace_host.pack_start(initial_view, True, True, 0)
        self._workspace_container = initial_view
        self._active_pane_id = initial_pane_id
        self._update_pane_close_buttons()
        self._update_all_pane_headers()
        self._set_active_pane(initial_pane_id)

        project_path_bar = self._build_project_path_bar()
        wrap.pack_start(project_path_bar, False, False, 8)
        return panel

    def _create_pane_controller(self, pane_id: str) -> PaneController:
        pane = PaneController(pane_id)
        pane._claude_process = ClaudeProcess(
            on_running_changed=lambda request_token, running, pid=pane_id: self._on_process_running_changed(
                pid,
                request_token,
                running,
            ),
            on_assistant_chunk=lambda request_token, chunk, pid=pane_id: self._on_process_assistant_chunk(
                pid,
                request_token,
                chunk,
            ),
            on_system_message=lambda request_token, message, pid=pane_id: self._on_process_system_message(
                pid,
                request_token,
                message,
            ),
            on_permission_request=lambda request_token, payload, pid=pane_id: self._on_process_permission_request(
                pid,
                request_token,
                payload,
            ),
            on_complete=lambda request_token, result, pid=pane_id: self._on_process_complete(
                pid,
                request_token,
                result,
            ),
        )
        self._pane_registry[pane_id] = pane
        return pane

    def build_pane_chat_view(self, pane_id: str) -> Gtk.Box:
        pane = self._pane_registry[pane_id]

        pane_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        pane_box.set_hexpand(True)
        pane_box.set_vexpand(True)
        pane_box.get_style_context().add_class("pane-root")
        pane_box._pane_id = pane_id

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_hexpand(True)
        header.get_style_context().add_class("pane-header")
        if GTK4 and hasattr(Gtk, "GestureClick"):
            header_click = Gtk.GestureClick.new()
            header_click.connect(
                "pressed",
                lambda _gesture, _n_press, _x, _y, pid=pane_id: self._set_active_pane(pid, grab_focus=True),
            )
            header.add_controller(header_click)
        else:
            def _on_header_press(_widget: Gtk.Widget, _event: Gdk.EventButton, pid: str = pane_id) -> bool:
                self._set_active_pane(pid, grab_focus=True)
                return False

            self._connect_optional_signal(
                header,
                "button-press-event",
                _on_header_press,
            )
        pane_box.pack_start(header, False, False, 0)

        title_label = Gtk.Label(label="Pane")
        title_label.set_xalign(0.0)
        title_label.get_style_context().add_class("pane-title")
        header.pack_start(title_label, True, True, 0)
        pane._title_label = title_label

        session_label = Gtk.Label(label="No session")
        session_label.set_xalign(1.0)
        session_label.get_style_context().add_class("pane-session-label")
        header.pack_start(session_label, False, False, 0)
        pane._session_label = session_label

        close_button = Gtk.Button(label="×")
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.get_style_context().add_class("pane-close-button")
        close_button.connect("clicked", lambda _button, pid=pane_id: self._close_pane(pid))
        close_button.set_visible(False)
        header.pack_start(close_button, False, False, 0)
        pane._close_button = close_button

        overlay = Gtk.Overlay()
        overlay.set_hexpand(True)
        overlay.set_vexpand(True)
        pane_box.pack_start(overlay, True, True, 0)

        shell = Gtk.EventBox()
        shell.set_visible_window(True)
        shell.set_hexpand(True)
        shell.set_vexpand(True)
        shell.get_style_context().add_class("chat-shell")
        overlay.add(shell)
        pane._chat_shell = shell
        is_initial_pane = self._workspace_container is None and len(self._pane_registry) <= 1
        if is_initial_pane:
            self._chat_reveal_widgets.append((shell, 60.0))
            shell.set_opacity(0.0)
        else:
            shell.set_opacity(1.0)

        if hasattr(WebKit.WebView, "new_with_user_content_manager"):
            manager = WebKit.UserContentManager()
            webview = WebKit.WebView.new_with_user_content_manager(manager)
        else:
            webview = WebKit.WebView.new()
            manager = webview.get_user_content_manager()

        for handler_name in (
            "sendMessage",
            "changeModel",
            "changePermission",
            "changeReasoning",
            "changeFolder",
            "attachFile",
            "toggleAgentMode",
            "permissionResponse",
            "stopProcess",
            "refreshSlashCommands",
        ):
            manager.register_script_message_handler(handler_name)
        manager.connect(
            "script-message-received::sendMessage",
            lambda manager, result, pid=pane_id: self._on_js_send_message(pid, manager, result),
        )
        manager.connect(
            "script-message-received::changeModel",
            lambda manager, result, pid=pane_id: self._on_js_change_model(pid, manager, result),
        )
        manager.connect(
            "script-message-received::changePermission",
            lambda manager, result, pid=pane_id: self._on_js_change_permission(pid, manager, result),
        )
        manager.connect(
            "script-message-received::changeReasoning",
            lambda manager, result, pid=pane_id: self._on_js_change_reasoning(pid, manager, result),
        )
        manager.connect(
            "script-message-received::changeFolder",
            lambda manager, result, pid=pane_id: self._on_js_change_folder(pid, manager, result),
        )
        manager.connect(
            "script-message-received::attachFile",
            lambda manager, result, pid=pane_id: self._on_js_attach_file(pid, manager, result),
        )
        manager.connect(
            "script-message-received::toggleAgentMode",
            lambda manager, result, pid=pane_id: self._on_js_toggle_agent_mode(pid, manager, result),
        )
        manager.connect(
            "script-message-received::permissionResponse",
            lambda manager, result, pid=pane_id: self._on_js_permission_response(pid, manager, result),
        )
        manager.connect(
            "script-message-received::stopProcess",
            lambda manager, result, pid=pane_id: self._on_js_stop_process(pid, manager, result),
        )
        manager.connect(
            "script-message-received::refreshSlashCommands",
            lambda manager, result, pid=pane_id: self._on_js_refresh_slash_commands(pid, manager, result),
        )
        pane._webview_user_content_manager = manager

        webview.set_hexpand(True)
        webview.set_vexpand(True)
        webview.connect(
            "load-changed",
            lambda webview, load_event, pid=pane_id: self._on_webview_load_changed(pid, webview, load_event),
        )
        self._connect_optional_signal(
            webview,
            "focus-in-event",
            lambda webview, event, pid=pane_id: self._on_webview_focus_in(pid, webview, event),
        )
        self._connect_optional_signal(
            webview,
            "focus-out-event",
            lambda webview, event, pid=pane_id: self._on_webview_focus_out(pid, webview, event),
        )

        settings = webview.get_settings()
        if settings is not None:
            if hasattr(settings, "set_enable_write_console_messages_to_stdout"):
                settings.set_enable_write_console_messages_to_stdout(False)
            if hasattr(settings, "set_enable_developer_extras"):
                settings.set_enable_developer_extras(False)
            if hasattr(settings, "set_enable_javascript"):
                settings.set_enable_javascript(True)

        webview.load_html(CHAT_WEBVIEW_HTML, "")
        shell.add(webview)
        pane._webview = webview

        pane_box.show_all()
        return pane_box

    def _ordered_pane_ids(self) -> list[str]:
        ordered: list[str] = []

        def walk(widget: Gtk.Widget | None) -> None:
            if widget is None:
                return
            if isinstance(widget, Gtk.Paned):
                walk(widget.get_child1())
                walk(widget.get_child2())
                return
            pane_id = getattr(widget, "_pane_id", None)
            if isinstance(pane_id, str) and pane_id in self._pane_registry:
                ordered.append(pane_id)

        walk(self._workspace_container)
        return ordered

    def _first_pane_id_in_widget(self, widget: Gtk.Widget | None) -> str | None:
        if widget is None:
            return None
        pane_id = getattr(widget, "_pane_id", None)
        if isinstance(pane_id, str) and pane_id in self._pane_registry:
            return pane_id
        if isinstance(widget, Gtk.Paned):
            left = self._first_pane_id_in_widget(widget.get_child1())
            if left is not None:
                return left
            return self._first_pane_id_in_widget(widget.get_child2())
        return None

    def _sync_window_chrome_for_active_pane(self) -> None:
        pane = self._pane_by_id(self._active_pane_id)
        if pane is None:
            return
        active_session = self._find_session(pane._active_session_id)
        if active_session is not None and active_session.project_path:
            self._project_folder = normalize_folder(active_session.project_path)
            self._set_project_path_entry_text(self._project_folder)
        self._update_project_folder_labels()
        self._update_status_model_and_permission()
        self._refresh_connection_state()
        self._refresh_session_list()
        self._update_all_pane_headers()

    def _set_active_pane(self, pane_id: str, *, grab_focus: bool = False) -> None:
        if pane_id not in self._pane_registry:
            return
        self._active_pane_id = pane_id
        for current_id, pane in self._pane_registry.items():
            if pane._container is None:
                continue
            context = pane._container.get_style_context()
            if current_id == pane_id:
                context.add_class("pane-active")
            else:
                context.remove_class("pane-active")
        self._sync_window_chrome_for_active_pane()
        if grab_focus:
            pane = self._pane_registry[pane_id]
            if pane._webview is not None:
                pane._webview.grab_focus()

    def _update_pane_header(self, pane_id: str) -> None:
        pane = self._pane_by_id(pane_id)
        if pane is None:
            return
        if pane._title_label is not None:
            if pane._is_agent:
                pane._title_label.set_text(pane._agent_name or f"Agent {pane_id.split('-')[-1]}")
            else:
                pane._title_label.set_text(f"Pane {pane_id.split('-')[-1]}")
        if pane._session_label is not None:
            session = self._find_session(pane._active_session_id)
            if session is None:
                pane._session_label.set_text("No session")
            else:
                pane._session_label.set_text(self._truncate_text(session.title or "Session", 24))

    def _update_all_pane_headers(self) -> None:
        for pane_id in self._pane_registry:
            self._update_pane_header(pane_id)

    def _update_pane_close_buttons(self) -> None:
        can_close_any = len(self._pane_registry) > 1
        primary = self._primary_pane_id()
        for pane_id, pane in self._pane_registry.items():
            if pane._close_button is not None:
                closable = can_close_any and pane_id != primary
                pane._close_button.set_visible(closable)
                pane._close_button.set_sensitive(closable)

    @staticmethod
    def _detach_from_paned(paned: Gtk.Paned, child: Gtk.Widget | None) -> None:
        if child is None:
            return
        if GTK4 and hasattr(paned, "get_start_child"):
            if paned.get_start_child() == child:
                paned.set_start_child(None)
                return
            if paned.get_end_child() == child:
                paned.set_end_child(None)
                return
        if hasattr(paned, "remove"):
            paned.remove(child)

    def _schedule_split_position(
        self,
        split: Gtk.Paned,
        orientation: Gtk.Orientation,
        *,
        min_new_pane: int,
    ) -> None:
        attempts = 0

        def _apply_split_position() -> bool:
            nonlocal attempts
            attempts += 1
            allocation = split.get_allocation()
            span = int(
                getattr(allocation, "width" if orientation == Gtk.Orientation.HORIZONTAL else "height", 0) or 0,
            )
            if span <= 0:
                if attempts < 20:
                    return True
                span = min_new_pane * 2

            position = max(120, span - min_new_pane) if span > min_new_pane else max(1, span // 2)
            try:
                split.set_position(position)
            except Exception:
                pass
            return False

        GLib.timeout_add(30, _apply_split_position)

    def _split_active_pane(self, orientation: Gtk.Orientation) -> str | None:
        if self._active_pane_id is None:
            return None
        if len(self._pane_registry) >= self._max_panes:
            self._add_system_message("Pane limit reached (max 4). Close one pane before splitting again.")
            self._set_status_message("Pane limit reached (4)", STATUS_WARNING)
            return None
        current = self._pane_by_id(self._active_pane_id)
        if current is None or current._container is None:
            return None

        current_allocation = current._container.get_allocation()
        if orientation == Gtk.Orientation.HORIZONTAL:
            span = int(getattr(current_allocation, "width", 0) or 0)
            fallback = 900
            min_new_pane = 340
        else:
            span = int(getattr(current_allocation, "height", 0) or 0)
            fallback = 680
            min_new_pane = 220
        if span <= 0:
            span = fallback
        split_position = max(120, span - min_new_pane) if span > min_new_pane else max(1, span // 2)

        new_pane_id = self._new_pane_id()
        new_pane = self._create_pane_controller(new_pane_id)
        new_view = self.build_pane_chat_view(new_pane_id)
        new_pane._container = new_view
        new_view._pane_id = new_pane_id

        old_parent = current._container.get_parent()
        split = Gtk.Paned(orientation=orientation)
        split.set_wide_handle(True)
        if isinstance(old_parent, Gtk.Paned):
            current_is_first = old_parent.get_child1() == current._container
            self._detach_from_paned(old_parent, current._container)
            split.pack1(current._container, True, False)
            split.pack2(new_view, True, False)
            if current_is_first:
                old_parent.pack1(split, True, False)
            else:
                old_parent.pack2(split, True, False)
        elif isinstance(old_parent, Gtk.Box):
            old_parent.remove(current._container)
            split.pack1(current._container, True, False)
            split.pack2(new_view, True, False)
            old_parent.pack_start(split, True, True, 0)
            self._workspace_container = split
        else:
            split.pack1(current._container, True, False)
            split.pack2(new_view, True, False)
            if self._workspace_host is not None:
                self._workspace_host.pack_start(split, True, True, 0)
                self._workspace_container = split

        with self._pane_context(new_pane_id):
            if os.path.isdir(self._project_folder):
                self._start_new_session(self._project_folder)

        split.show_all()
        try:
            split.set_position(split_position)
        except Exception:
            pass
        self._schedule_split_position(split, orientation, min_new_pane=min_new_pane)
        self._update_pane_close_buttons()
        self._update_all_pane_headers()
        self._set_active_pane(new_pane_id, grab_focus=True)
        return new_pane_id

    def _next_agent_name(self) -> str:
        self._agent_counter += 1
        return f"Agent {self._agent_counter}"

    def _pane_display_name(self, pane_id: str) -> str:
        pane = self._pane_by_id(pane_id)
        if pane is None:
            return pane_id
        if pane._is_agent:
            return pane._agent_name or f"Agent {pane_id.split('-')[-1]}"
        return f"Pane {pane_id.split('-')[-1]}"

    def _primary_pane_id(self) -> str | None:
        ordered = self._ordered_pane_ids() or list(self._pane_registry.keys())
        if not ordered:
            return None

        def pane_rank(pid: str) -> tuple[int, str]:
            match = re.search(r"(\d+)$", pid)
            return (int(match.group(1)) if match else 10**9, pid)

        return min(ordered, key=pane_rank)

    def _is_primary_pane(self, pane_id: str | None) -> bool:
        if not pane_id:
            return False
        primary = self._primary_pane_id()
        return primary is not None and pane_id == primary

    def _last_assistant_message_for_pane(self, pane_id: str) -> str:
        pane = self._pane_by_id(pane_id)
        if pane is None:
            return ""
        session = self._find_session(pane._active_session_id)
        if session is None or not session.history:
            return ""
        for msg in reversed(session.history):
            if str(msg.get("role") or "").strip().lower() == "assistant":
                return str(msg.get("content") or "").strip()
        return ""

    def _send_prompt_to_pane(self, target_pane_id: str, prompt: str, *, keep_focus_on: str | None = None) -> bool:
        text = str(prompt or "").strip()
        if not text:
            return False
        if target_pane_id not in self._pane_registry:
            return False
        self._call_js_in_pane(target_pane_id, "hostSendMessage", text)
        if keep_focus_on and keep_focus_on in self._pane_registry and keep_focus_on != target_pane_id:
            def _restore_focus() -> bool:
                if keep_focus_on in self._pane_registry:
                    self._set_active_pane(keep_focus_on, grab_focus=True)
                return False

            GLib.timeout_add(120, _restore_focus)
        return True

    @staticmethod
    def _extract_agentctl_commands(assistant_text: str) -> list[str]:
        text = str(assistant_text or "")
        commands: list[str] = []
        seen: set[str] = set()

        for block_match in re.finditer(r"```(agentctl|agent)\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL):
            block_body = str(block_match.group(2) or "")
            for raw_line in block_body.splitlines():
                command = ClaudeCodeWindow._normalize_agentctl_line(raw_line, allow_prefixless=True)
                if not command:
                    continue
                line = command
                key = line.casefold()
                if key in seen:
                    continue
                seen.add(key)
                commands.append(line)

        for raw_line in text.splitlines():
            command = ClaudeCodeWindow._normalize_agentctl_line(raw_line)
            if not command:
                continue
            key = command.casefold()
            if key in seen:
                continue
            seen.add(key)
            commands.append(command)
        return commands

    @staticmethod
    def _normalize_agentctl_line(raw_line: str, *, allow_prefixless: bool = False) -> str | None:
        line = str(raw_line or "").strip()
        if not line:
            return None
        line = line.strip(" \t`")
        if not line:
            return None
        line = re.sub(r"^\s*[-*+]\s*", "", line)
        line = re.sub(r"^\s*\d+[.)]\s*", "", line)
        if not line:
            return None

        match = re.match(
            r"^(?P<prefix>@agentctl|/agent|agentctl|agent)\b\s*(?P<body>.*)$",
            line,
            re.IGNORECASE,
        )
        if match:
            prefix = match.group("prefix").lower()
            body = str(match.group("body") or "").strip(" :")
            if prefix == "/agent":
                command = f"/agent {body}".strip()
            else:
                command = f"/agent {body}".strip() if body else "/agent"
        elif allow_prefixless:
            tokens = line.split(maxsplit=1)
            if not tokens:
                return None
            if tokens[0].lower() not in _AGENTCTL_COMMAND_KEYWORDS:
                return None
            command = f"/agent {line}".strip()
        else:
            return None

        command = command.strip()
        if not command:
            return None

        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()

        if not tokens or tokens[0].lower() not in {"/agent", "/pane"}:
            return None
        if len(tokens) == 1:
            return "/agent"
        if tokens[1].lower() not in _AGENTCTL_COMMAND_KEYWORDS:
            return None
        if tokens[1].lower() in {"send", "ask", "run"} and len(tokens) < 3:
            return None
        if tokens[1].lower() in {"summarize", "summary", "merge"} and len(tokens) < 4:
            return None
        return command

    def _execute_agentctl_from_assistant(self, pane_id: str, assistant_text: str) -> int:
        commands = self._extract_agentctl_commands(assistant_text)
        if not commands:
            return 0

        executed = 0
        for command in commands[:12]:
            target_command = command if command.startswith("/agent") else f"/agent {command}"
            if self._handle_agent_command(pane_id, target_command, allow_non_primary=True):
                executed += 1
        if executed:
            self._add_system_message(f"Executed {executed} agent control command(s) from assistant output.")
        return executed

    def _collapse_to_primary_pane(self) -> str | None:
        primary = self._primary_pane_id()
        if primary is None:
            return None
        for pane_id in list(self._pane_registry.keys()):
            if pane_id == primary:
                continue
            self._close_pane(pane_id)
        pane = self._pane_by_id(primary)
        if pane is not None:
            pane._is_agent = False
            pane._agent_name = None
            self._update_pane_header(primary)
        self._set_active_pane(primary, grab_focus=True)
        return primary

    def _resolve_pane_target(self, reference: str | None, *, current_pane_id: str) -> str | None:
        ordered = self._ordered_pane_ids()
        if not ordered:
            ordered = list(self._pane_registry.keys())
        if not ordered:
            return None

        current = current_pane_id if current_pane_id in ordered else (self._active_pane_id or ordered[0])
        ref = str(reference or "").strip().lower()
        if not ref or ref in {"current", "this", "here", "active"}:
            return current

        if ref in {"next", "n"}:
            index = ordered.index(current)
            return ordered[(index + 1) % len(ordered)]
        if ref in {"prev", "previous", "p"}:
            index = ordered.index(current)
            return ordered[(index - 1) % len(ordered)]

        if ref in self._pane_registry:
            return ref

        if ref.isdigit():
            index = int(ref) - 1
            if 0 <= index < len(ordered):
                return ordered[index]
            return None

        pane_match = re.fullmatch(r"pane[-_ ]?(\d+)", ref)
        if pane_match:
            index = int(pane_match.group(1)) - 1
            if 0 <= index < len(ordered):
                return ordered[index]
            return None

        agent_match = re.fullmatch(r"agent[-_ ]?(\d+)", ref)
        if agent_match:
            agents = [pid for pid in ordered if (self._pane_by_id(pid) and self._pane_by_id(pid)._is_agent)]
            index = int(agent_match.group(1)) - 1
            if 0 <= index < len(agents):
                return agents[index]
            return None

        exact_matches = [pid for pid in ordered if self._pane_display_name(pid).lower() == ref]
        if len(exact_matches) == 1:
            return exact_matches[0]

        prefix_matches = [pid for pid in ordered if self._pane_display_name(pid).lower().startswith(ref)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
        return None

    def _handle_agent_command(self, pane_id: str, message: str, *, allow_non_primary: bool = False) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if not (text.startswith("/agent") or text.startswith("/pane")):
            return False
        if (not allow_non_primary) and (not self._is_primary_pane(pane_id)):
            self._add_system_message("Use /agent commands from the main chat pane only.")
            self._set_status_message("Agent control is restricted to the main chat pane.", STATUS_WARNING)
            return True

        try:
            tokens = shlex.split(text)
        except ValueError:
            self._add_system_message("Invalid /agent command syntax.")
            return True

        if not tokens:
            return False
        root = tokens[0].lower()
        if root not in {"/agent", "/pane"}:
            return False

        subcommand = tokens[1].lower() if len(tokens) > 1 else "help"
        if subcommand in {"help", "h", "?"}:
            self._add_system_message(
                "Agent commands:\n"
                "/agent new [name] - create a new agent pane\n"
                "/agent list - list panes and agents\n"
                "/agent focus <target> - focus pane (target: 1, pane-2, next, prev, Agent 1)\n"
                "/agent send <target> <prompt> - send prompt to pane without leaving main chat\n"
                "/agent summarize <target> <source...> - create summary from source agent outputs\n"
                "/agent close [target] - close pane (default: current)\n"
                "/agent help - show this help",
            )
            return True

        if subcommand in {"new", "create", "add", "spawn"}:
            custom_name = " ".join(tokens[2:]).strip() if len(tokens) > 2 else ""
            self._create_agent_pane(name=custom_name or None)
            return True

        if subcommand in {"list", "ls"}:
            ordered = self._ordered_pane_ids() or list(self._pane_registry.keys())
            lines: list[str] = []
            for index, target_pane_id in enumerate(ordered, start=1):
                pane = self._pane_by_id(target_pane_id)
                if pane is None:
                    continue
                session = self._find_session(pane._active_session_id)
                session_text = self._truncate_text(session.title or "No session", 28) if session else "No session"
                marker = "*" if target_pane_id == self._active_pane_id else " "
                role = "agent" if pane._is_agent else "pane"
                lines.append(
                    f"{marker}{index}. {self._pane_display_name(target_pane_id)} [{role}] "
                    f"({target_pane_id}) - {session_text}",
                )
            self._add_system_message("Panes:\n" + ("\n".join(lines) if lines else "No panes available."))
            return True

        if subcommand in {"focus", "switch", "goto", "go"}:
            target_ref = tokens[2] if len(tokens) > 2 else ""
            target_pane_id = self._resolve_pane_target(target_ref, current_pane_id=pane_id)
            if target_pane_id is None:
                self._add_system_message("Unknown pane target. Use /agent list.")
                return True
            self._set_active_pane(target_pane_id, grab_focus=True)
            self._focus_chat_input_in_pane(target_pane_id)
            self._set_status_message(f"Focused {self._pane_display_name(target_pane_id)}.", STATUS_INFO)
            return True

        if subcommand in {"send", "ask", "run"}:
            if len(tokens) < 4:
                self._add_system_message("Usage: /agent send <target> <prompt>")
                return True
            target_ref = tokens[2]
            prompt_text = " ".join(tokens[3:]).strip()
            target_pane_id = self._resolve_pane_target(target_ref, current_pane_id=pane_id)
            if target_pane_id is None:
                self._add_system_message("Unknown pane target. Use /agent list.")
                return True
            if not self._send_prompt_to_pane(target_pane_id, prompt_text, keep_focus_on=pane_id):
                self._add_system_message("Could not dispatch prompt to target pane.")
                return True
            self._set_status_message(f"Prompt sent to {self._pane_display_name(target_pane_id)}.", STATUS_INFO)
            return True

        if subcommand in {"summarize", "summary", "merge"}:
            if len(tokens) < 5:
                self._add_system_message("Usage: /agent summarize <target> <source1> <source2> [sourceN]")
                return True
            target_ref = tokens[2]
            target_pane_id = self._resolve_pane_target(target_ref, current_pane_id=pane_id)
            if target_pane_id is None:
                self._add_system_message("Unknown target pane. Use /agent list.")
                return True

            source_pane_ids: list[str] = []
            for ref in tokens[3:]:
                resolved = self._resolve_pane_target(ref, current_pane_id=pane_id)
                if resolved is None:
                    self._add_system_message(f"Unknown source pane target '{ref}'.")
                    return True
                if resolved == target_pane_id:
                    continue
                if resolved not in source_pane_ids:
                    source_pane_ids.append(resolved)
            if not source_pane_ids:
                self._add_system_message("No valid source panes provided.")
                return True

            source_blocks: list[str] = []
            missing_sources: list[str] = []
            for source_pane_id in source_pane_ids:
                last_output = self._last_assistant_message_for_pane(source_pane_id)
                source_name = self._pane_display_name(source_pane_id)
                if not last_output:
                    missing_sources.append(source_name)
                    continue
                source_blocks.append(f"[{source_name}]\n{last_output}")

            if not source_blocks:
                self._add_system_message("No assistant output available in selected source panes yet.")
                return True

            prompt_lines = [
                "You are a synthesis agent.",
                "Summarize and reconcile the following agent outputs.",
                "Provide: 1) key findings 2) conflicts/uncertainties 3) recommended next actions.",
                "",
                "\n\n".join(source_blocks),
            ]
            if missing_sources:
                prompt_lines.append("")
                prompt_lines.append("Sources without assistant output yet: " + ", ".join(missing_sources))
            summary_prompt = "\n".join(prompt_lines).strip()

            if not self._send_prompt_to_pane(target_pane_id, summary_prompt, keep_focus_on=pane_id):
                self._add_system_message("Could not dispatch summarize prompt.")
                return True
            self._set_status_message(
                f"Summary requested from {self._pane_display_name(target_pane_id)}.",
                STATUS_INFO,
            )
            return True

        if subcommand in {"close", "kill", "remove"}:
            target_ref = tokens[2] if len(tokens) > 2 else "current"
            target_pane_id = self._resolve_pane_target(target_ref, current_pane_id=pane_id)
            if target_pane_id is None:
                self._add_system_message("Unknown pane target. Use /agent list.")
                return True
            if self._is_primary_pane(target_pane_id):
                self._set_status_message("Main pane cannot be closed.", STATUS_WARNING)
                return True
            if len(self._pane_registry) <= 1:
                self._set_status_message("Cannot close the last pane.", STATUS_WARNING)
                return True
            target_label = self._pane_display_name(target_pane_id)
            self._close_pane(target_pane_id)
            self._set_status_message(f"Closed {target_label}.", STATUS_INFO)
            return True

        self._add_system_message("Unknown /agent command. Use /agent help.")
        return True

    def _create_agent_pane(self, *, name: str | None = None) -> str | None:
        try:
            new_pane_id = self._split_active_pane(Gtk.Orientation.HORIZONTAL)
            if new_pane_id is None:
                return None
            pane = self._pane_by_id(new_pane_id)
            if pane is None:
                return None
            pane._is_agent = True
            custom_name = str(name or "").strip()
            pane._agent_name = custom_name or self._next_agent_name()
            self._update_pane_header(new_pane_id)
            with self._pane_context(new_pane_id):
                self._add_system_message(
                    f"{pane._agent_name} ready. Use this pane to chat directly with this agent.",
                )
            self._set_status_message(f"{pane._agent_name} created.", STATUS_INFO)
            self._focus_chat_input_in_pane(new_pane_id)
            return new_pane_id
        except Exception:
            logger.exception("Could not create agent pane.")
            self._set_status_message("Could not create agent pane.", STATUS_ERROR)
            return None

    def _cycle_pane_focus(self, *, forward: bool) -> None:
        ordered = self._ordered_pane_ids()
        if not ordered:
            return
        if self._active_pane_id not in ordered:
            target = ordered[0]
            self._set_active_pane(target, grab_focus=True)
            return
        index = ordered.index(self._active_pane_id)
        if forward:
            target = ordered[(index + 1) % len(ordered)]
        else:
            target = ordered[(index - 1) % len(ordered)]
        self._set_active_pane(target, grab_focus=True)

    def _prune_chat_reveal_widgets(self) -> None:
        live_widgets = {
            pane._chat_shell
            for pane in self._pane_registry.values()
            if pane._chat_shell is not None
        }
        self._chat_reveal_widgets = [
            (widget, delay_ms)
            for widget, delay_ms in self._chat_reveal_widgets
            if widget in live_widgets
        ]

    def _rebuild_workspace_layout(self, pane_order: list[str]) -> None:
        if self._workspace_host is None:
            return

        # Detach current tree in one step to avoid GTK focus warnings when mutating nested paneds.
        self._clear_box(self._workspace_host)

        ordered_ids = [pane_id for pane_id in pane_order if pane_id in self._pane_registry]
        for pane_id in ordered_ids:
            pane = self._pane_registry[pane_id]
            if pane._container is None:
                continue
            parent = pane._container.get_parent()
            if isinstance(parent, Gtk.Paned):
                self._detach_from_paned(parent, pane._container)
            elif isinstance(parent, Gtk.Box):
                try:
                    parent.remove(pane._container)
                except Exception:
                    pass

        root: Gtk.Widget | None = None
        for pane_id in ordered_ids:
            pane = self._pane_registry[pane_id]
            if pane._container is None:
                continue
            if root is None:
                root = pane._container
                continue
            split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            split.set_wide_handle(True)
            split.pack1(root, True, False)
            split.pack2(pane._container, True, False)
            root = split

        if root is None:
            self._workspace_container = None
            return

        self._workspace_host.pack_start(root, True, True, 0)
        self._workspace_container = root
        root.show_all()

    def _close_active_pane(self) -> None:
        if self._active_pane_id is None:
            return
        self._close_pane(self._active_pane_id)

    def _close_pane(self, pane_id: str) -> None:
        if pane_id not in self._pane_registry:
            return
        if self._is_primary_pane(pane_id):
            self._set_status_message("Main pane cannot be closed.", STATUS_WARNING)
            return
        if len(self._pane_registry) <= 1:
            self._set_status_message("Cannot close the last pane.", STATUS_WARNING)
            return

        pane = self._pane_registry[pane_id]
        if pane._container is None:
            return

        with self._pane_context(pane_id):
            if pane._claude_process is not None:
                pane._claude_process.stop()
            for paths in pane._request_temp_files.values():
                cleanup_temp_paths(paths)
            pane._request_temp_files.clear()

        current_order = self._ordered_pane_ids() or list(self._pane_registry.keys())
        desired_active = self._active_pane_id
        if desired_active == pane_id:
            desired_active = None
            if pane_id in current_order:
                index = current_order.index(pane_id)
                for candidate in current_order[index + 1 :] + list(reversed(current_order[:index])):
                    if candidate in self._pane_registry and candidate != pane_id:
                        desired_active = candidate
                        break

        del self._pane_registry[pane_id]
        remaining_order = [candidate for candidate in current_order if candidate in self._pane_registry]
        if not remaining_order:
            remaining_order = list(self._pane_registry.keys())
        self._rebuild_workspace_layout(remaining_order)
        self._prune_chat_reveal_widgets()
        self._update_pane_close_buttons()
        self._update_all_pane_headers()

        if not self._pane_registry:
            self._active_pane_id = None
            return

        if desired_active not in self._pane_registry:
            desired_active = remaining_order[0] if remaining_order else self._primary_pane_id()
        if desired_active is None:
            desired_active = next(iter(self._pane_registry.keys()))
        self._set_active_pane(desired_active, grab_focus=True)

    def _on_window_key_press(self, _widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        return self._handle_window_key_press(event.keyval, event.state)

    def _handle_window_key_press(self, keyval: int, state: Gdk.ModifierType) -> bool:
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        if ctrl and shift and keyval in (Gdk.KEY_D, Gdk.KEY_d):
            self._split_active_pane(Gtk.Orientation.HORIZONTAL)
            return True
        if ctrl and shift and keyval in (Gdk.KEY_E, Gdk.KEY_e):
            self._split_active_pane(Gtk.Orientation.VERTICAL)
            return True
        if ctrl and shift and keyval in (Gdk.KEY_A, Gdk.KEY_a):
            self._create_agent_pane()
            return True
        if ctrl and keyval == Gdk.KEY_w:
            self._close_active_pane()
            return True
        if ctrl and shift and keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            self._cycle_pane_focus(forward=False)
            return True
        if ctrl and keyval == Gdk.KEY_Tab:
            self._cycle_pane_focus(forward=True)
            return True
        return False

    def _window_is_focused(self) -> bool:
        return bool(self.is_active() or self._window_has_focus)

    @staticmethod
    def _notification_urgency(urgency: str) -> str:
        normalized = str(urgency or "normal").strip().lower()
        if normalized in {"low", "normal", "critical"}:
            return normalized
        if normalized == "urgent":
            return "critical"
        if normalized == "high":
            return "normal"
        return "normal"

    def send_notification(self, title: str, body: str, urgency: str = "normal") -> None:
        if self._window_is_focused():
            return

        title_text = str(title or APP_NAME).strip() or APP_NAME
        body_text = str(body or "").strip()
        normalized_urgency = self._notification_urgency(urgency)

        app = Gio.Application.get_default()
        if isinstance(app, Gio.Application):
            try:
                notification = Gio.Notification.new(title_text)
                if body_text:
                    notification.set_body(body_text)
                priority = {
                    "low": Gio.NotificationPriority.LOW,
                    "normal": Gio.NotificationPriority.NORMAL,
                    "critical": Gio.NotificationPriority.URGENT,
                }.get(normalized_urgency, Gio.NotificationPriority.NORMAL)
                notification.set_priority(priority)
                self._notification_counter += 1
                app.send_notification(f"claude-code-gui-{self._notification_counter}", notification)
                return
            except Exception:
                logger.exception("Could not send Gio notification; falling back to notify-send.")

        command = ["notify-send", title_text, body_text, "--urgency", normalized_urgency]
        try:
            subprocess.run(command, check=False)
        except (OSError, ValueError):
            return

    def _on_window_focus_in(self, _widget: Gtk.Widget, _event: Gdk.EventFocus) -> bool:
        self._window_has_focus = True
        return False

    def _on_window_focus_out(self, _widget: Gtk.Widget, _event: Gdk.EventFocus) -> bool:
        self._window_has_focus = False
        return False

    def _build_sidebar(self) -> Gtk.Box:
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.get_style_context().add_class("sidebar")
        sidebar.set_hexpand(False)
        sidebar.set_vexpand(True)
        sidebar.set_size_request(SIDEBAR_OPEN_WIDTH, -1)
        self._sidebar_container = sidebar

        sidebar_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        toggle_button = Gtk.Button()
        toggle_button.set_relief(Gtk.ReliefStyle.NONE)
        toggle_button.set_halign(Gtk.Align.START)
        toggle_button.get_style_context().add_class("sidebar-toggle-gtk")
        toggle_button.get_style_context().add_class("sidebar-header-toggle")
        toggle_button._drag_blocker = True
        toggle_icon = Gtk.Label(label="☰")
        toggle_icon.get_style_context().add_class("sidebar-toggle-glyph")
        toggle_button.add(toggle_icon)
        toggle_button.connect("clicked", self._on_sidebar_toggle_clicked)
        sidebar_top.pack_start(toggle_button, False, False, 0)
        self._sidebar_toggle_button = toggle_button

        provider_button = Gtk.Button()
        provider_button.set_relief(Gtk.ReliefStyle.NONE)
        provider_button.set_halign(Gtk.Align.START)
        provider_button.get_style_context().add_class("provider-switch-button")
        provider_button._drag_blocker = True
        provider_button.connect("clicked", self._on_provider_toggle_clicked)
        provider_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        provider_button_icon = Gtk.Image()
        provider_button_icon.set_pixel_size(16)
        provider_button_icon.get_style_context().add_class("provider-switch-icon")
        provider_button_label = Gtk.Label(label="")
        provider_button_label.set_xalign(0.0)
        provider_button_box.pack_start(provider_button_icon, False, False, 0)
        provider_button_box.pack_start(provider_button_label, False, False, 0)
        provider_button.add(provider_button_box)
        self._provider_toggle_button_icon = provider_button_icon
        self._provider_toggle_button_label = provider_button_label
        sidebar_top.pack_start(provider_button, False, False, 0)
        self._provider_toggle_button = provider_button

        settings_button = Gtk.Button(label="Settings")
        settings_button.set_relief(Gtk.ReliefStyle.NONE)
        settings_button.set_halign(Gtk.Align.START)
        settings_button.get_style_context().add_class("provider-switch-button")
        settings_button.set_tooltip_text("Open settings to edit colors, models, themes and reasoning options.")
        settings_button._drag_blocker = True
        settings_button.connect("clicked", self._on_settings_button_clicked)
        sidebar_top.pack_start(settings_button, False, False, 0)
        self._settings_button = settings_button

        new_session_button = Gtk.Button(label="+ New Chat")
        new_session_button.set_relief(Gtk.ReliefStyle.NONE)
        new_session_button.set_hexpand(True)
        new_session_button.set_halign(Gtk.Align.FILL)
        new_session_button.get_style_context().add_class("new-session-button")
        new_session_button._drag_blocker = True
        new_session_button.connect("clicked", self._on_new_session_clicked)
        sidebar_top.pack_start(new_session_button, True, True, 0)
        sidebar.pack_start(sidebar_top, False, False, 0)

        sessions_title = Gtk.Label(label="Sessions (0)")
        sessions_title.set_xalign(0.0)
        sessions_title.get_style_context().add_class("sidebar-section-title")
        sidebar.pack_start(sessions_title, False, False, 0)
        self._sessions_title_label = sessions_title

        filter_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_row.get_style_context().add_class("session-filter-row")
        sidebar.pack_start(filter_row, False, False, 0)

        filter_items = (
            ("all", "All"),
            ("active", "Active"),
            ("archived", "Archived"),
        )
        for key, label in filter_items:
            button = Gtk.Button(label=label)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class("session-filter-pill")
            button.connect("clicked", self._on_session_filter_clicked, key)
            filter_row.pack_start(button, False, False, 0)
            self._session_filter_buttons[key] = button

        search_entry = Gtk.Entry()
        search_entry.set_placeholder_text("Search sessions")
        search_entry.get_style_context().add_class("session-search-entry")
        search_entry.connect("changed", self._on_session_search_changed)
        sidebar.pack_start(search_entry, False, False, 0)
        self._session_search_entry = search_entry

        session_scroll = Gtk.ScrolledWindow()
        session_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        session_scroll.set_shadow_type(Gtk.ShadowType.NONE)
        session_scroll.get_style_context().add_class("session-scroll")
        session_scroll.set_vexpand(True)
        sidebar.pack_start(session_scroll, True, True, 0)

        session_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        session_list.get_style_context().add_class("session-list")
        session_scroll.add(session_list)
        self._session_list_box = session_list

        empty = Gtk.Label(label="No chats yet. Click + New Chat.")
        empty.set_line_wrap(True)
        empty.set_xalign(0.0)
        empty.get_style_context().add_class("session-empty")
        session_list.pack_start(empty, False, False, 0)
        self._session_empty_label = empty

        self._update_session_filter_buttons()
        self._sidebar_expanded_only_widgets = [
            new_session_button,
            sessions_title,
            filter_row,
            search_entry,
            session_scroll,
        ]
        self._update_sidebar_toggle_button()
        self._update_provider_toggle_button()
        self._set_sidebar_content_visibility(self._sidebar_expanded)

        return sidebar

    def _build_project_path_bar(self) -> Gtk.Box:
        path_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        path_bar.set_hexpand(True)
        path_bar.get_style_context().add_class("project-path-bar")

        project_entry = Gtk.Entry()
        project_entry.set_hexpand(True)
        project_entry.set_text(self._project_folder)
        project_entry.set_placeholder_text(str(Path.home()))
        project_entry.get_style_context().add_class("project-path-entry")
        project_entry.connect("changed", self._on_project_path_entry_changed)
        project_entry.connect("activate", self._on_project_path_entry_activate)
        self._connect_optional_signal(project_entry, "key-press-event", self._on_project_path_entry_key_press)
        self._connect_optional_signal(project_entry, "focus-in-event", self._on_project_path_entry_focus_in)
        project_entry.connect("notify::has-focus", self._on_project_path_entry_has_focus_changed)
        path_bar.pack_start(project_entry, True, True, 0)
        self._project_path_entry = project_entry

        browse_button = Gtk.Button()
        browse_button.set_relief(Gtk.ReliefStyle.NONE)
        browse_button.set_tooltip_text("Browse folders")
        browse_button.get_style_context().add_class("project-path-browse-button")
        browse_icon = Gtk.Image.new_from_icon_name("folder-open-symbolic", Gtk.IconSize.BUTTON)
        browse_button.add(browse_icon)
        browse_button.connect("clicked", self._on_choose_folder_clicked)
        path_bar.pack_start(browse_button, False, False, 0)

        if GTK4:
            suggestion_popover = Gtk.Popover()
            suggestion_popover.set_parent(project_entry)
        else:
            suggestion_popover = Gtk.Popover.new(project_entry)
        suggestion_popover.set_position(Gtk.PositionType.BOTTOM)
        suggestion_popover.set_modal(False)
        suggestion_popover.get_style_context().add_class("path-suggestion-popover")

        suggestion_scroll = Gtk.ScrolledWindow()
        suggestion_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        suggestion_scroll.set_shadow_type(Gtk.ShadowType.NONE)
        suggestion_scroll.set_size_request(300, 220)
        if hasattr(suggestion_scroll, "set_can_focus"):
            suggestion_scroll.set_can_focus(False)
        suggestion_popover.add(suggestion_scroll)

        suggestion_list = Gtk.ListBox()
        suggestion_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        suggestion_list.set_activate_on_single_click(True)
        if hasattr(suggestion_list, "set_can_focus"):
            suggestion_list.set_can_focus(False)
        if hasattr(suggestion_list, "set_focus_on_click"):
            suggestion_list.set_focus_on_click(False)
        suggestion_list.get_style_context().add_class("path-suggestion-list")
        suggestion_list.connect("row-selected", self._on_project_path_suggestion_selected)
        suggestion_list.connect("row-activated", self._on_project_path_suggestion_activated)
        suggestion_scroll.add(suggestion_list)

        self._project_path_popover = suggestion_popover
        self._project_path_suggestion_scroll = suggestion_scroll
        self._project_path_suggestion_list = suggestion_list
        return path_bar

    def _build_status_bar(self) -> Gtk.Box:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.get_style_context().add_class("bottom-bar")

        dot = Gtk.Label(label="●")
        dot.get_style_context().add_class("connection-dot")
        bar.pack_start(dot, False, False, 0)
        self._connection_dot = dot

        connection_label = Gtk.Label(label="Disconnected")
        connection_label.set_xalign(0.0)
        connection_label.get_style_context().add_class("status-label")
        bar.pack_start(connection_label, False, False, 0)
        self._connection_label = connection_label

        context_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.pack_start(context_box, False, False, 0)

        context_label = Gtk.Label(label="Context: ~0 / 200k")
        context_label.get_style_context().add_class("context-label")
        context_box.pack_start(context_label, False, False, 0)
        self._context_usage_label = context_label

        context_progress = Gtk.ProgressBar()
        context_progress.set_show_text(False)
        context_progress.set_fraction(0.0)
        context_progress.set_size_request(108, 6)
        context_progress.get_style_context().add_class("context-progress")
        context_box.pack_start(context_progress, False, False, 0)
        self._context_progress = context_progress

        sep1 = Gtk.Label(label="·")
        sep1.get_style_context().add_class("status-label")
        bar.pack_start(sep1, False, False, 0)

        session_limit_label = Gtk.Label(label="$0.00")
        session_limit_label.get_style_context().add_class("usage-limit-label")
        session_limit_label.set_tooltip_text("Session cost (API usage)")
        bar.pack_start(session_limit_label, False, False, 0)
        self._session_limit_label = session_limit_label

        weekly_limit_label = Gtk.Label(label="0 tokens")
        weekly_limit_label.get_style_context().add_class("usage-limit-label")
        weekly_limit_label.set_tooltip_text("Total tokens used this session")
        bar.pack_start(weekly_limit_label, False, False, 0)
        self._weekly_limit_label = weekly_limit_label

        status_message = Gtk.Label(label="")
        status_message.set_xalign(0.0)
        status_message.set_hexpand(True)
        status_message.set_single_line_mode(True)
        status_message.set_ellipsize(Pango.EllipsizeMode.END)
        status_message.get_style_context().add_class("status-label")
        bar.pack_start(status_message, True, True, 0)
        self._status_message_label = status_message

        timer = Gtk.Label(label="00:00:00")
        timer.get_style_context().add_class("bottom-timer")
        bar.pack_end(timer, False, False, 0)
        self._session_timer_label = timer

        self._status_fade_widgets = [
            bar,
            dot,
            connection_label,
            context_label,
            context_progress,
            sep1,
            session_limit_label,
            weekly_limit_label,
            status_message,
            timer,
        ]
        for widget in self._status_fade_widgets:
            widget.set_opacity(0.0)

        self._set_connection_state(CONNECTION_DISCONNECTED)
        self._set_status_message("Ready", STATUS_MUTED)
        self._update_context_indicator()
        self._update_status_model_and_permission()

        return bar

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(value, 1.0))

    @staticmethod
    def _ease_out_cubic(progress: float) -> float:
        p = ClaudeCodeWindow._clamp01(progress)
        return 1.0 - (1.0 - p) ** 3

    @staticmethod
    def _ease_in_out_cubic(progress: float) -> float:
        p = ClaudeCodeWindow._clamp01(progress)
        return 3.0 * p * p - 2.0 * p * p * p

    def _session_sort_key(self, session: SessionRecord) -> float:
        return parse_timestamp(session.last_used_at or session.created_at)

    def _find_session(self, session_id: str | None) -> SessionRecord | None:
        if session_id is None:
            return None
        for session in self._sessions:
            if session.id == session_id:
                return session
        return None

    def _get_active_session(self) -> SessionRecord | None:
        return self._find_session(self._active_session_id)

    def _model_index_from_value(self, model_value: str) -> int:
        for index, (_, value) in enumerate(self._model_options):
            if value == model_value:
                return index
        return 0

    def _permission_index_from_value(self, permission_mode: str) -> int:
        for index, (_, value, _) in enumerate(self._permission_options):
            if value == permission_mode:
                return index
        return 0

    def _reasoning_index_from_value(self, value: str) -> int:
        if not self._reasoning_options:
            return 0

        target = str(value or "").strip()
        for i, (_, v, _) in enumerate(self._reasoning_options):
            if v == target:
                return i
        return 0

    def _reasoning_value_from_index(self, index: int) -> str:
        if not self._reasoning_options:
            return "medium"
        safe_index = max(0, min(index, len(self._reasoning_options) - 1))
        return self._reasoning_options[safe_index][1]

    def _provider_reasoning_option_payload(self) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        for title, value, description in self._reasoning_options:
            payload.append(
                {
                    "title": title,
                    "value": value,
                    "description": description or f"{title} reasoning option",
                }
            )
        if not payload:
            payload.append({"title": "Medium", "value": "medium", "description": "Balanced reasoning."})
        return payload

    def _settings_dialog_size_constraints(self) -> tuple[int, int, int, int, int, int]:
        desired_width = 720
        desired_height = 540
        base_min_width = 380
        base_min_height = 280
        hard_min_width = 360
        hard_min_height = 260
        max_width_cap = 760
        max_height_cap = 620
        workarea_margin = 64

        max_width = desired_width
        max_height = desired_height

        if GTK4:
            display = Gdk.Display.get_default()
            if display is not None:
                monitors = display.get_monitors()
                if monitors.get_n_items() > 0:
                    monitor = monitors.get_item(0)
                    if monitor is not None:
                        workarea = monitor.get_geometry()
                        max_width = max(
                            hard_min_width,
                            min(int(workarea.width) - workarea_margin, max_width_cap),
                        )
                        max_height = max(
                            hard_min_height,
                            min(int(workarea.height) - workarea_margin, max_height_cap),
                        )
        else:
            screen = self.get_screen()
            if screen is not None:
                monitor_index = screen.get_primary_monitor()
                if monitor_index < 0:
                    monitor_index = 0
                window = self.get_window()
                if window is not None:
                    monitor_index = screen.get_monitor_at_window(window)
                workarea = Gdk.Rectangle()
                try:
                    screen.get_monitor_workarea(monitor_index, workarea)
                except TypeError:
                    returned_workarea = screen.get_monitor_workarea(monitor_index)
                    if returned_workarea:
                        workarea = returned_workarea
                max_width = max(
                    hard_min_width,
                    min(int(workarea.width) - workarea_margin, max_width_cap),
                )
                max_height = max(
                    hard_min_height,
                    min(int(workarea.height) - workarea_margin, max_height_cap),
                )

        min_width = min(base_min_width, max_width)
        min_height = min(base_min_height, max_height)
        default_width = max(min_width, min(desired_width, max_width))
        default_height = max(min_height, min(desired_height, max_height))
        return default_width, default_height, min_width, min_height, max_width, max_height

    def _save_sessions_safe(self, context: str) -> bool:
        try:
            save_sessions(self._sessions)
            return True
        except (OSError, ValueError, TypeError) as error:
            self._set_status_message(f"{context}: {error}", STATUS_WARNING)
            return False

    def _reset_conversation_state(
        self,
        reason: str,
        reset_timer: bool = True,
        preserve_conversation_id: bool = False,
    ) -> None:
        if reset_timer:
            self._session_started_us = GLib.get_monotonic_time()
        self._interrupt_running_process(reason)
        if not preserve_conversation_id:
            self._conversation_id = None
            self._call_js("setProcessing", False)
        self._allowed_tools = set()
        self._clear_messages()
        self._show_welcome()
        self._set_typing(False)
        self._has_messages = False
        self._last_request_failed = False
        self._active_assistant_message = ""

    def _replay_history(self, history: list[dict[str, str]]) -> None:
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if not role or not content:
                continue
            if role == "user":
                self._has_messages = True
                self._call_js("addUserMessage", content)
            elif role == "assistant":
                self._has_messages = True
                self._call_js("startAssistantMessage")
                self._call_js("appendAssistantChunk", content)
                self._call_js("finishAssistantMessage")
            elif role == "system":
                self._call_js("addSystemMessage", content)

    def _replay_active_session_if_present(self) -> None:
        active_session = self._get_active_session()
        if active_session is None or not active_session.history:
            return
        self._conversation_id = active_session.conversation_id
        self._replay_history(active_session.history)

    def _add_to_history(self, role: str, content: str) -> None:
        if not content:
            return
        active = self._get_active_session()
        if active is not None:
            active.history.append({"role": role, "content": content})
            if len(active.history) > 200:
                active.history = active.history[-200:]

    def _promote_replacement_session(self) -> SessionRecord | None:
        candidates = [
            s
            for s in self._sessions
            if s.provider == self._active_provider_id and s.status != SESSION_STATUS_ARCHIVED
        ]
        if not candidates:
            self._active_session_id = None
            return None
        replacement = max(candidates, key=self._session_sort_key)
        self._active_session_id = replacement.id
        replacement.status = SESSION_STATUS_ACTIVE
        replacement.last_used_at = current_timestamp()
        self._apply_session_to_controls(replacement, add_to_recent=os.path.isdir(replacement.project_path))
        return replacement

    def _cancel_timer(self, attr: str) -> None:
        timer_id = getattr(self, attr, None)
        if timer_id is not None:
            GLib.source_remove(timer_id)
            setattr(self, attr, None)

    def _load_sessions_into_state(self) -> None:
        try:
            self._sessions = load_sessions()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self._sessions = []
            self._active_session_id = None
            self._set_status_message(f"Could not load sessions: {error}", STATUS_WARNING)
            return

        if not self._sessions:
            self._active_session_id = None
            return

        active_candidates = [
            s
            for s in self._sessions
            if s.provider == self._active_provider_id and s.status != SESSION_STATUS_ARCHIVED
        ]
        if not active_candidates:
            self._active_session_id = None
            return

        selected = max(active_candidates, key=self._session_sort_key)
        changed = False

        for session in self._sessions:
            if session.status == SESSION_STATUS_ACTIVE:
                session.status = SESSION_STATUS_ENDED
                changed = True

        self._active_session_id = None
        self._apply_session_to_controls(selected, add_to_recent=os.path.isdir(selected.project_path))
        self._conversation_id = None

        if changed:
            self._save_sessions_safe("Could not save session state")

    def _apply_session_to_controls(self, session: SessionRecord, add_to_recent: bool) -> None:
        session.provider = normalize_provider_id(session.provider)
        self._set_provider_option_lists(
            session.provider,
            preferred_model=session.model,
            preferred_permission=session.permission_mode,
        )
        if self._model_options:
            session.model = self._model_options[self._selected_model_index][1]
        if self._permission_options:
            session.permission_mode = self._permission_options[self._selected_permission_index][1]
        if not self._active_provider.supports_reasoning:
            session.reasoning_level = "medium"

        self._project_folder = session.project_path
        self._selected_reasoning_index = self._reasoning_index_from_value(session.reasoning_level)
        self._set_project_path_entry_text(self._project_folder)

        if add_to_recent and os.path.isdir(self._project_folder):
            self._add_recent_folder(self._project_folder)

        self._update_project_folder_labels()
        self._update_status_model_and_permission()
        self._update_context_indicator()

        self._call_js("setReasoningVisible", self._active_provider.supports_reasoning)
        if self._active_provider.supports_reasoning:
            reasoning_value = self._reasoning_value_from_index(self._selected_reasoning_index)
            self._call_js("updateReasoningLevel", reasoning_value)

    def _build_session_title(self, folder: str, timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(timestamp)
        except ValueError:
            dt = datetime.now().astimezone()
        name = Path(folder).name or folder
        return f"{name} - {dt.strftime('%H:%M')}"

    def _create_session_record(self, folder: str) -> SessionRecord:
        normalized = normalize_folder(folder)
        now = current_timestamp()
        _, model_value = self._model_options[self._selected_model_index]
        _, permission_value, _ = self._permission_options[self._selected_permission_index]
        return SessionRecord(
            id=str(uuid.uuid4()),
            title=self._build_session_title(normalized, now),
            project_path=normalized,
            model=model_value,
            permission_mode=permission_value,
            status=SESSION_STATUS_ACTIVE,
            created_at=now,
            last_used_at=now,
            provider=self._active_provider_id,
        )

    def _set_active_session_status(self, status: str) -> None:
        session = self._get_active_session()
        if session is None:
            return
        if status not in SESSION_STATUSES:
            return
        session.status = status
        session.last_used_at = current_timestamp()
        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

    @staticmethod
    def _clear_box(box: Gtk.Box) -> None:
        for child in box.get_children():
            box.remove(child)

    @staticmethod
    def _session_time_bucket(timestamp_value: str) -> str:
        now = datetime.now().astimezone().date()
        try:
            session_date = datetime.fromisoformat(timestamp_value).astimezone().date()
        except ValueError:
            return "Älter"

        delta_days = (now - session_date).days
        if delta_days <= 0:
            return "Heute"
        if delta_days == 1:
            return "Gestern"
        if delta_days <= 7:
            return "Diese Woche"
        return "Älter"

    @staticmethod
    def _is_permission_request_message(message: str) -> bool:
        raw = str(message or "").strip()
        if not raw:
            return False

        lowered = raw.casefold()
        if "tool confirmation" in lowered:
            return True
        if "permission" in lowered and any(
            token in lowered for token in ("wait", "confirm", "approval", "approve", "allow")
        ):
            return True

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return False

        if not isinstance(parsed, dict):
            return False

        if bool(parsed.get("permission_request")) or bool(parsed.get("requires_confirmation")):
            return True

        status = str(parsed.get("status") or "").casefold()
        if status in {"awaiting_confirmation", "waiting_for_confirmation", "pending_confirmation"}:
            return True

        detail = str(parsed.get("message") or parsed.get("error") or "").casefold()
        return "permission" in detail and "confirm" in detail

    def _update_session_filter_buttons(self) -> None:
        for key, button in self._session_filter_buttons.items():
            context = button.get_style_context()
            if key == self._session_filter:
                context.add_class("session-filter-pill-active")
                continue
            context.remove_class("session-filter-pill-active")

    def _on_session_filter_clicked(self, _button: Gtk.Button, selected_filter: str) -> None:
        if selected_filter not in {"all", "active", "archived"}:
            return
        if self._session_filter == selected_filter:
            return
        self._session_filter = selected_filter
        self._update_session_filter_buttons()
        self._refresh_session_list()

    def _on_session_search_changed(self, entry: Gtk.Entry) -> None:
        self._session_search_query = entry.get_text().strip().casefold()
        self._refresh_session_list()

    def _get_filtered_sessions(self) -> list[SessionRecord]:
        provider_sessions = [s for s in self._sessions if s.provider == self._active_provider_id]
        if self._session_filter == "active":
            candidates = [s for s in provider_sessions if s.status == SESSION_STATUS_ACTIVE]
        elif self._session_filter == "archived":
            candidates = [s for s in provider_sessions if s.status == SESSION_STATUS_ARCHIVED]
        else:
            candidates = [s for s in provider_sessions if s.status != SESSION_STATUS_ARCHIVED]

        if self._session_search_query:
            query = self._session_search_query
            candidates = [
                session
                for session in candidates
                if query in (session.title or "").casefold() or query in (session.project_path or "").casefold()
            ]

        return sorted(candidates, key=self._session_sort_key, reverse=True)

    @staticmethod
    def _get_session_last_message(session: SessionRecord) -> str:
        if not session.history:
            return ""
        for msg in reversed(session.history):
            role = str(msg.get("role") or "").strip().lower()
            if role != "user":
                continue
            content = re.sub(r"\s+", " ", str(msg.get("content") or "").strip())
            if not content:
                continue
            if len(content) > 74:
                return content[:71] + "..."
            return content
        return ""

    @staticmethod
    def _format_session_timestamp(timestamp_value: str) -> str:
        try:
            dt = datetime.fromisoformat(timestamp_value).astimezone()
        except ValueError:
            return "--:--"
        return dt.strftime("%d.%m. %H:%M")

    @staticmethod
    def _truncate_text(value: str, max_chars: int) -> str:
        cleaned = re.sub(r"\s+", " ", str(value or "").strip())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3].rstrip() + "..."

    @staticmethod
    def _safe_slash_name(name: str) -> str:
        raw = str(name or "").strip().strip("/")
        if not raw:
            return ""
        cleaned = re.sub(r"[^a-zA-Z0-9._/-]+", "-", raw)
        cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
        if not cleaned:
            return ""
        return f"/{cleaned}"

    @staticmethod
    def _read_markdown_summary(path: Path) -> str:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return ""

        title = ""
        for raw_line in lines[:80]:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if not title:
                    title = line.lstrip("#").strip()
                continue
            if line.startswith(("```", "---", "<!--")):
                continue
            return line
        return title

    def _discover_custom_slash_commands(self) -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []
        commands_by_key: dict[str, dict[str, Any]] = {}

        def normalize_providers(providers: list[str] | tuple[str, ...]) -> list[str]:
            normalized: list[str] = []
            for provider_id in providers:
                candidate = str(provider_id or "").strip().lower()
                if candidate and candidate in PROVIDERS and candidate not in normalized:
                    normalized.append(candidate)
            return normalized

        def add_command(name: str, icon: str, description: str, providers: list[str] | tuple[str, ...]) -> None:
            safe_name = self._safe_slash_name(name)
            if not safe_name:
                return
            provider_list = normalize_providers(providers)
            if not provider_list:
                return
            key = safe_name.casefold()
            existing = commands_by_key.get(key)
            if existing is not None:
                merged_providers = list(existing.get("providers") or [])
                for provider_id in provider_list:
                    if provider_id not in merged_providers:
                        merged_providers.append(provider_id)
                existing["providers"] = merged_providers
                return

            payload = {
                "name": safe_name,
                "icon": icon,
                "description": self._truncate_text(description, 96),
                "providers": provider_list,
            }
            commands_by_key[key] = payload
            commands.append(payload)

        project_root = Path(self._project_folder)
        codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser()
        all_provider_ids: tuple[str, ...] = tuple(PROVIDERS.keys()) or (DEFAULT_PROVIDER_ID,)
        command_roots: list[tuple[Path, tuple[str, ...]]] = [
            (project_root / ".claude" / "commands", ("claude",)),
            (Path.home() / ".claude" / "commands", ("claude",)),
            (project_root / ".codex" / "commands", ("codex",)),
            (codex_home / "commands", ("codex",)),
            (project_root / ".agents" / "commands", all_provider_ids),
            (Path.home() / ".agents" / "commands", all_provider_ids),
        ]
        for root, providers in command_roots:
            if not root.is_dir():
                continue
            for command_file in sorted(root.rglob("*.md"), key=lambda p: str(p).casefold()):
                if not command_file.is_file():
                    continue
                try:
                    relative = command_file.relative_to(root).with_suffix("")
                except ValueError:
                    continue
                if any(part.startswith(".") for part in relative.parts):
                    continue
                slash_name = "/".join(relative.parts)
                summary = self._read_markdown_summary(command_file) or "Custom slash command"
                add_command(slash_name, "C", f"Custom command: {summary}", providers)

        skill_doc_names = ("SKILL.md", "skill.md", "skill.markdown")
        skill_roots: list[tuple[Path, tuple[str, ...]]] = [
            (project_root / ".agents" / "skills", all_provider_ids),
            (Path.home() / ".agents" / "skills", all_provider_ids),
            (project_root / ".codex" / "skills", ("codex",)),
            (codex_home / "skills", ("codex",)),
            (project_root / ".claude" / "skills", ("claude",)),
            (Path.home() / ".claude" / "skills", ("claude",)),
        ]
        for root, providers in skill_roots:
            if not root.is_dir():
                continue
            discovered_docs: list[Path] = []
            for doc_name in skill_doc_names:
                discovered_docs.extend(root.rglob(doc_name))

            for skill_doc in sorted(discovered_docs, key=lambda p: str(p).casefold()):
                if not skill_doc.is_file():
                    continue
                skill_dir = skill_doc.parent
                if skill_dir == root or skill_dir.name.startswith("."):
                    continue
                summary = self._read_markdown_summary(skill_doc) or "Custom skill"
                add_command(skill_dir.name, "S", f"Custom skill: {summary}", providers)

        return commands

    def _refresh_slash_commands(self) -> None:
        commands = self._discover_custom_slash_commands()
        payload = json.dumps(commands, ensure_ascii=False, sort_keys=True)
        if payload == self._last_slash_commands_cache:
            return
        self._last_slash_commands_cache = payload
        self._call_js("updateSlashCommands", commands)

    def _make_session_row(self, session: SessionRecord, allow_open: bool) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        row.get_style_context().add_class("session-row")
        if session.id == self._active_session_id:
            row.get_style_context().add_class("session-row-active")

        open_button = Gtk.Button()
        open_button.set_relief(Gtk.ReliefStyle.NONE)
        open_button.get_style_context().add_class("session-open-button")
        open_button._drag_blocker = True
        open_button.set_hexpand(True)
        open_button.set_halign(Gtk.Align.FILL)
        open_button.set_sensitive(allow_open)
        open_button.connect("clicked", lambda _button, sid=session.id: self._switch_to_session(sid))

        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        status = session.status if session.status in SESSION_STATUSES else SESSION_STATUS_ENDED
        status_dot = Gtk.Box()
        status_dot.set_size_request(8, 8)
        status_dot.get_style_context().add_class("session-status-dot")
        status_dot.get_style_context().add_class(f"session-status-{status}")
        title_row.pack_start(status_dot, False, False, 0)

        title_text = self._get_session_last_message(session) or session.title or "New chat"
        title = Gtk.Label(label=title_text)
        title.set_xalign(0.0)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_single_line_mode(True)
        title.set_max_width_chars(40)
        title.get_style_context().add_class("session-title")
        title_row.pack_start(title, True, True, 0)
        label_box.pack_start(title_row, False, False, 0)

        meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        meta_time = Gtk.Label(label=self._format_session_timestamp(session.last_used_at or session.created_at))
        meta_time.set_xalign(0.0)
        meta_time.set_single_line_mode(True)
        meta_time.get_style_context().add_class("session-meta")
        meta_time.get_style_context().add_class("session-meta-time")
        meta_row.pack_start(meta_time, False, False, 0)

        path_display = shorten_path(format_path(session.project_path), 30)
        meta_path = Gtk.Label(label=path_display)
        meta_path.set_xalign(0.0)
        meta_path.set_hexpand(True)
        meta_path.set_ellipsize(Pango.EllipsizeMode.END)
        meta_path.set_single_line_mode(True)
        meta_path.set_max_width_chars(32)
        meta_path.get_style_context().add_class("session-meta")
        meta_path.get_style_context().add_class("session-meta-path")
        meta_row.pack_start(meta_path, True, True, 0)

        label_box.pack_start(meta_row, False, False, 0)

        open_button.add(label_box)
        row.pack_start(open_button, True, True, 0)

        menu_button = Gtk.Button(label="...")
        menu_button.set_relief(Gtk.ReliefStyle.NONE)
        menu_button.get_style_context().add_class("session-menu-button")
        menu_button._drag_blocker = True
        active_popover: Gtk.Popover | None = None

        def _close_active_popover() -> None:
            nonlocal active_popover
            if active_popover is None:
                return
            pop = active_popover
            active_popover = None
            try:
                pop.popdown()
            except Exception:
                pop.set_visible(False)
            try:
                parent = pop.get_parent() if hasattr(pop, "get_parent") else None
                if parent is not None and hasattr(pop, "unparent"):
                    pop.unparent()
            except Exception:
                pass
            if hasattr(pop, "destroy"):
                try:
                    pop.destroy()
                except Exception:
                    pass

        def _build_popover() -> Gtk.Popover:
            if GTK4:
                popover = Gtk.Popover.new()
                popover.set_parent(menu_button)
            else:
                popover = Gtk.Popover.new(menu_button)
            popover.get_style_context().add_class("session-popover")

            menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            menu_box.set_border_width(6)

            archive_button = Gtk.ModelButton(label="Archive")
            archive_button.connect(
                "clicked",
                lambda _button, sid=session.id: (
                    self._archive_session(sid),
                    _close_active_popover(),
                ),
            )
            menu_box.pack_start(archive_button, False, False, 0)

            delete_button = Gtk.ModelButton(label="Delete")
            delete_button.connect(
                "clicked",
                lambda _button, sid=session.id: (
                    self._delete_session(sid),
                    _close_active_popover(),
                ),
            )
            menu_box.pack_start(delete_button, False, False, 0)

            popover.add(menu_box)
            menu_box.show_all()
            return popover

        def _toggle_session_popover() -> None:
            nonlocal active_popover
            if active_popover is not None:
                _close_active_popover()
                return
            active_popover = _build_popover()
            try:
                active_popover.popup()
            except Exception:
                active_popover.show_all()
                active_popover.set_visible(True)

        menu_button.connect("clicked", lambda _button: _toggle_session_popover())
        menu_button.connect("destroy", lambda _button: _close_active_popover())
        row.pack_end(menu_button, False, False, 0)

        def on_row_button_press(_widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
            if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
                _toggle_session_popover()
                return True
            return False

        self._connect_optional_signal(row, "button-press-event", on_row_button_press)
        row.connect("destroy", lambda _row: _close_active_popover())

        return row

    def _refresh_session_list(self) -> None:
        if self._session_list_box is None or self._session_empty_label is None:
            return

        provider_sessions = [s for s in self._sessions if s.provider == self._active_provider_id]
        if self._sessions_title_label is not None:
            self._sessions_title_label.set_text(f"Sessions ({len(provider_sessions)})")

        self._clear_box(self._session_list_box)
        visible_sessions = self._get_filtered_sessions()
        if not visible_sessions:
            if self._session_search_query:
                self._session_empty_label.set_text("No sessions match your search.")
            elif self._session_filter == "active":
                self._session_empty_label.set_text("No active sessions.")
            elif self._session_filter == "archived":
                self._session_empty_label.set_text("No archived sessions.")
            else:
                self._session_empty_label.set_text(
                    f"No {self._active_provider.name} chats yet. Click + New Chat."
                )
            self._session_list_box.pack_start(self._session_empty_label, False, False, 0)
            self._session_empty_label.show()
            self._update_all_pane_headers()
            return

        grouped: dict[str, list[SessionRecord]] = {
            "Heute": [],
            "Gestern": [],
            "Diese Woche": [],
            "Älter": [],
        }
        for session in visible_sessions:
            bucket = self._session_time_bucket(session.last_used_at or session.created_at)
            grouped.setdefault(bucket, []).append(session)

        for group_name in ("Heute", "Gestern", "Diese Woche", "Älter"):
            sessions = grouped.get(group_name, [])
            if not sessions:
                continue
            label = Gtk.Label(label=group_name)
            label.set_xalign(0.0)
            label.get_style_context().add_class("session-group-label")
            self._session_list_box.pack_start(label, False, False, 0)

            for session in sessions:
                allow_open = session.status != SESSION_STATUS_ARCHIVED
                row = self._make_session_row(session, allow_open=allow_open)
                self._session_list_box.pack_start(row, False, False, 0)

        self._session_list_box.show_all()
        self._update_all_pane_headers()

    def _refresh_session_list_idle(self) -> bool:
        self._refresh_session_list()
        return False

    def _switch_to_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        if session is None:
            return
        if session.provider != self._active_provider_id:
            if not self._switch_provider(session.provider):
                self._set_status_message(
                    f"Cannot open session: {self._provider_display_name(session.provider)} is unavailable.",
                    STATUS_WARNING,
                )
                return

        if session.status == SESSION_STATUS_ARCHIVED:
            self._set_status_message("Archived sessions cannot be opened", STATUS_WARNING)
            return
        if session.id == self._active_session_id and session.status == SESSION_STATUS_ACTIVE:
            self._set_status_message("Session already active", STATUS_MUTED)
            return

        current = self._get_active_session()
        if current is not None and current.id != session.id and current.status != SESSION_STATUS_ARCHIVED:
            current.status = SESSION_STATUS_ENDED
            current.last_used_at = current_timestamp()

        self._active_session_id = session.id
        session.status = SESSION_STATUS_ACTIVE
        session.last_used_at = current_timestamp()
        self._apply_session_to_controls(session, add_to_recent=os.path.isdir(session.project_path))
        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        self._conversation_id = session.conversation_id
        self._reset_conversation_state("Session switched", preserve_conversation_id=True)

        if session.history:
            self._replay_history(session.history)

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        self._refresh_connection_state()
        msg_count = len(session.history) if session.history else 0
        if msg_count > 0:
            self._set_status_message(f"Session restored with {msg_count} messages.", STATUS_INFO)
        else:
            self._set_status_message("Session switched.", STATUS_INFO)

    def _mutate_session_and_reconcile_active(self, session_id: str, action: str) -> None:
        session = self._find_session(session_id)
        if session is None:
            return

        if action == "archive":
            if session.status == SESSION_STATUS_ARCHIVED:
                return
            active_reason = "Active session archived"
            terminal_reason = "Session archived"
            replacement_message = "Archived session. Switched to replacement."
            terminal_message = "Session archived"
            session.status = SESSION_STATUS_ARCHIVED
            session.last_used_at = current_timestamp()
        elif action == "delete":
            active_reason = "Active session deleted"
            terminal_reason = "Session deleted"
            replacement_message = "Deleted session. Switched to replacement."
            terminal_message = "Session deleted"
            self._sessions = [item for item in self._sessions if item.id != session_id]
        else:
            return

        was_active = session.id == self._active_session_id
        replacement = self._promote_replacement_session() if was_active else None

        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        if was_active and replacement is not None:
            self._reset_conversation_state(active_reason)
            self._refresh_connection_state()
            self._set_status_message(replacement_message, STATUS_INFO)
            return

        if was_active and replacement is None:
            self._reset_conversation_state(terminal_reason, reset_timer=False)
            self._set_status_message(terminal_message, STATUS_MUTED)
            self._refresh_connection_state()
            return

        self._set_status_message(terminal_message, STATUS_MUTED)

    def _archive_session(self, session_id: str) -> None:
        self._mutate_session_and_reconcile_active(session_id, "archive")

    def _delete_session(self, session_id: str) -> None:
        self._mutate_session_and_reconcile_active(session_id, "delete")

    def _start_new_session(self, folder: str, *, reset_conversation: bool = True) -> None:
        normalized = normalize_folder(folder)
        if not os.path.isdir(normalized):
            self._set_status_message("Selected path is not a folder", STATUS_ERROR)
            return

        current = self._get_active_session()
        if current is not None and current.status != SESSION_STATUS_ARCHIVED:
            current.status = SESSION_STATUS_ENDED
            current.last_used_at = current_timestamp()

        created = self._create_session_record(normalized)
        self._sessions.insert(0, created)
        self._active_session_id = created.id
        self._apply_session_to_controls(created, add_to_recent=True)
        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        if reset_conversation:
            self._reset_conversation_state("New session started")

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        self._refresh_connection_state()
        self._set_status_message("New session ready", STATUS_INFO)
        pane_id = self._active_pane_id
        if pane_id is not None:
            GLib.timeout_add(100, lambda pid=pane_id: self._call_js_in_pane(pid, "focusInput"))

    def _set_project_path_entry_text(self, path_value: str) -> None:
        if self._project_path_entry is None:
            return

        text_value = path_value.strip() or str(Path.home())
        if self._project_path_entry.get_text() == text_value:
            return

        self._suppress_project_entry_change = True
        self._project_path_entry.set_text(text_value)
        self._project_path_entry.set_position(-1)
        self._suppress_project_entry_change = False

    def _collect_project_path_suggestions(self, raw_value: str) -> list[str]:
        value = raw_value.strip()
        if not value:
            value = self._project_folder or str(Path.home())

        expanded = os.path.expanduser(value)
        if not os.path.isabs(expanded):
            expanded = os.path.abspath(expanded)

        if value.endswith(os.sep):
            parent = expanded
            prefix = ""
        else:
            parent = os.path.dirname(expanded) or os.sep
            prefix = os.path.basename(expanded)

        if not os.path.isdir(parent):
            # If the user typed deeper than existing folders, walk up to the nearest
            # existing directory and keep the nearest missing segment as prefix.
            probe = expanded.rstrip(os.sep)
            fallback_prefix = prefix
            while probe and not os.path.isdir(probe):
                fallback_prefix = os.path.basename(probe) or fallback_prefix
                next_probe = os.path.dirname(probe)
                if not next_probe or next_probe == probe:
                    break
                probe = next_probe
            if not os.path.isdir(probe):
                return []
            parent = probe
            prefix = fallback_prefix

        matches: list[str] = []
        prefix_lower = prefix.casefold()

        try:
            with os.scandir(parent) as iterator:
                for entry in iterator:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if prefix and not entry.name.casefold().startswith(prefix_lower):
                        continue
                    try:
                        matches.append(normalize_folder(entry.path))
                    except OSError:
                        continue
        except OSError:
            return []

        matches.sort(key=lambda item: item.casefold())
        return matches[:12]

    def _populate_project_path_suggestions(self, suggestions: list[str]) -> None:
        if self._project_path_suggestion_list is None:
            return

        for child in self._project_path_suggestion_list.get_children():
            self._project_path_suggestion_list.remove(child)

        for suggestion in suggestions:
            row = Gtk.ListBoxRow()
            row._completion_path = suggestion
            if hasattr(row, "set_can_focus"):
                row.set_can_focus(False)
            if hasattr(row, "set_focus_on_click"):
                row.set_focus_on_click(False)
            label = Gtk.Label(label=format_path(suggestion))
            label.set_xalign(0.0)
            label.set_single_line_mode(True)
            label.set_ellipsize(Pango.EllipsizeMode.NONE)
            label.set_line_wrap(False)
            label.get_style_context().add_class("path-suggestion-item")
            row.set_tooltip_text(format_path(suggestion))
            row.add(label)
            self._project_path_suggestion_list.add(row)

        self._project_path_suggestion_list.show_all()
        if suggestions:
            self._project_path_selected_index = 0
            first_row = self._project_path_suggestion_list.get_row_at_index(0)
            if first_row is not None:
                self._project_path_suggestion_list.select_row(first_row)
        else:
            self._project_path_selected_index = -1

    def _refresh_project_path_suggestions(self, show_popover: bool) -> None:
        if (
            self._project_path_entry is None
            or self._project_path_suggestion_list is None
            or self._project_path_popover is None
        ):
            return

        suggestions = self._collect_project_path_suggestions(self._project_path_entry.get_text())
        self._project_path_suggestions = suggestions
        self._populate_project_path_suggestions(suggestions)

        if not suggestions:
            self._hide_project_path_suggestions()
            return

        if show_popover:
            self._show_project_path_suggestions()

    def _show_project_path_suggestions(self) -> None:
        if self._project_path_popover is None or self._project_path_entry is None:
            return
        self._project_path_popover.show_all()
        try:
            self._project_path_popover.popup()
        except Exception:
            self._project_path_popover.set_visible(True)
        # Keep typing in the path entry; the suggestion list should never steal keyboard focus.
        self._project_path_entry.grab_focus()

    def _hide_project_path_suggestions(self) -> None:
        if self._project_path_popover is None:
            return
        try:
            self._project_path_popover.popdown()
        except Exception:
            self._project_path_popover.set_visible(False)

    def _get_selected_project_path_suggestion(self) -> str | None:
        if not self._project_path_suggestions:
            return None

        if self._project_path_suggestion_list is not None:
            selected_row = self._project_path_suggestion_list.get_selected_row()
            if selected_row is not None:
                index = selected_row.get_index()
                if 0 <= index < len(self._project_path_suggestions):
                    return self._project_path_suggestions[index]

        if 0 <= self._project_path_selected_index < len(self._project_path_suggestions):
            return self._project_path_suggestions[self._project_path_selected_index]
        return self._project_path_suggestions[0]

    def _move_project_path_selection(self, delta: int) -> None:
        if not self._project_path_suggestions or self._project_path_suggestion_list is None:
            return

        current = self._project_path_selected_index
        if current < 0:
            current = 0

        target = max(0, min(len(self._project_path_suggestions) - 1, current + delta))
        row = self._project_path_suggestion_list.get_row_at_index(target)
        if row is None:
            return

        self._project_path_selected_index = target
        self._project_path_suggestion_list.select_row(row)

    def _scroll_project_path_row_into_view(self, row: Gtk.ListBoxRow) -> None:
        if self._project_path_suggestion_scroll is None:
            return

        adjustment = self._project_path_suggestion_scroll.get_vadjustment()
        allocation = row.get_allocation()
        top = float(allocation.y)
        bottom = top + float(allocation.height)
        adjustment.clamp_page(top, bottom)

    def _apply_project_path_completion(self, suggestion: str) -> None:
        self._set_project_path_entry_text(suggestion)
        if self._project_path_entry is not None:
            self._project_path_entry.grab_focus()
            self._project_path_entry.set_position(-1)
        self._hide_project_path_suggestions()

    def _confirm_project_path_from_entry(self) -> None:
        if self._project_path_entry is None:
            return

        raw_value = self._project_path_entry.get_text().strip()
        candidate = raw_value or self._project_folder or str(Path.home())
        expanded = os.path.expanduser(candidate)
        if not os.path.isabs(expanded):
            expanded = os.path.abspath(expanded)

        self._set_project_folder(expanded, restart_session=self._active_session_id is not None)

    def _on_project_path_entry_changed(self, _entry: Gtk.Entry) -> None:
        if self._suppress_project_entry_change:
            return
        self._refresh_project_path_suggestions(show_popover=True)

    def _on_project_path_entry_activate(self, _entry: Gtk.Entry) -> None:
        selected = self._get_selected_project_path_suggestion()
        if selected is not None:
            self._set_project_path_entry_text(selected)
        self._confirm_project_path_from_entry()

    def _on_project_path_entry_key_press(self, _entry: Gtk.Entry, event: Gdk.EventKey) -> bool:
        if event.keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            selected = self._get_selected_project_path_suggestion()
            if selected is None:
                return False
            self._apply_project_path_completion(selected)
            return True

        if event.keyval == Gdk.KEY_Down:
            self._move_project_path_selection(1)
            return True

        if event.keyval == Gdk.KEY_Up:
            self._move_project_path_selection(-1)
            return True

        if event.keyval == Gdk.KEY_Escape:
            self._hide_project_path_suggestions()
            return True

        return False

    def _on_project_path_entry_focus_in(self, _entry: Gtk.Entry, _event: Gdk.Event) -> bool:
        self._refresh_project_path_suggestions(show_popover=True)
        return False

    def _on_project_path_entry_has_focus_changed(self, entry: Gtk.Entry, _param: Any) -> None:
        try:
            has_focus = bool(entry.get_property("has-focus"))
        except Exception:
            has_focus = False
        if has_focus:
            self._refresh_project_path_suggestions(show_popover=True)
        else:
            self._hide_project_path_suggestions()

    def _on_project_path_suggestion_selected(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if row is None:
            self._project_path_selected_index = -1
            return
        self._project_path_selected_index = row.get_index()
        self._scroll_project_path_row_into_view(row)

    def _on_project_path_suggestion_activated(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        suggestion = getattr(row, "_completion_path", None)
        if not isinstance(suggestion, str):
            return
        self._apply_project_path_completion(suggestion)

    def _update_project_folder_labels(self) -> None:
        full_display = format_path(self._project_folder)

        self._call_js("updateFolder", full_display)

    def _update_status_model_and_permission(self) -> None:
        if not self._model_options or not self._permission_options:
            return
        self._selected_model_index = max(0, min(self._selected_model_index, len(self._model_options) - 1))
        self._selected_permission_index = max(
            0,
            min(self._selected_permission_index, len(self._permission_options) - 1),
        )
        _, model_value = self._model_options[self._selected_model_index]
        _, permission_value, _ = self._permission_options[self._selected_permission_index]
        self._call_js("updateModel", model_value)
        self._call_js("updatePermission", permission_value)

    @staticmethod
    def _format_token_count(value: int) -> str:
        if value >= 100_000:
            return f"{round(value / 1000):.0f}k"
        if value >= 1000:
            return f"{value / 1000:.1f}k"
        return str(value)

    def _update_context_indicator(self) -> None:
        estimated_tokens = max(0, self._context_char_count // 4)
        ratio = max(0.0, min(1.0, estimated_tokens / float(CONTEXT_MAX_TOKENS)))
        formatted_tokens = self._format_token_count(estimated_tokens)

        if self._context_usage_label is not None:
            self._context_usage_label.set_text(f"Context: ~{formatted_tokens} / 200k")

        if self._context_progress is not None:
            self._context_progress.set_fraction(ratio)
            context = self._context_progress.get_style_context()
            context.remove_class("context-warn")
            context.remove_class("context-high")
            if ratio > 0.8:
                context.add_class("context-high")
            elif ratio >= 0.5:
                context.add_class("context-warn")

        tooltip = (
            f"Context usage: ~{estimated_tokens} tokens / {CONTEXT_MAX_TOKENS} max. "
            "Next reset on new session."
        )
        if self._context_usage_label is not None:
            self._context_usage_label.set_tooltip_text(tooltip)
        if self._context_progress is not None:
            self._context_progress.set_tooltip_text(tooltip)

    def _set_connection_state(self, state: str) -> None:
        text_map = {
            CONNECTION_CONNECTED: "Connected",
            CONNECTION_DISCONNECTED: "Disconnected",
            CONNECTION_STARTING: "Starting",
            CONNECTION_ERROR: "Error",
        }
        state_text = text_map.get(state, "Disconnected")

        if self._connection_label is not None:
            self._connection_label.set_text(state_text)

        if self._connection_dot is None:
            return

        context = self._connection_dot.get_style_context()
        for css_class in (
            "state-connected",
            "state-disconnected",
            "state-starting",
            "state-error",
        ):
            context.remove_class(css_class)
        context.add_class(f"state-{state}")
        if self._last_status_message:
            self._connection_dot.set_tooltip_text(f"{state_text}\n{self._last_status_message}")
        else:
            self._connection_dot.set_tooltip_text(state_text)

    def _refresh_connection_state(self) -> None:
        self._update_provider_toggle_button()
        if not binary_exists(self._binary_path):
            self._set_connection_state(CONNECTION_DISCONNECTED)
            return
        if self._claude_process.is_running():
            self._set_connection_state(CONNECTION_STARTING)
            return
        if self._last_request_failed:
            self._set_connection_state(CONNECTION_ERROR)
            return
        if self._active_provider_id == "codex" and not is_codex_authenticated():
            self._set_connection_state(CONNECTION_DISCONNECTED)
            return
        self._set_connection_state(CONNECTION_CONNECTED)

    def _set_status_message(self, message: str, severity: str = STATUS_MUTED) -> None:
        self._last_status_message = message
        self._update_project_folder_labels()
        if self._connection_dot is not None:
            existing = self._connection_dot.get_tooltip_text() or "Disconnected"
            state_text = existing.splitlines()[0] if existing else "Disconnected"
            self._connection_dot.set_tooltip_text(f"{state_text}\n{message}")

        if self._status_message_label is None:
            return

        self._status_message_label.set_text(message)
        context = self._status_message_label.get_style_context()
        for css_class in ("status-muted", "status-info", "status-warning", "status-error"):
            context.remove_class(css_class)

        severity_map = {
            STATUS_MUTED: "status-muted",
            STATUS_INFO: "status-info",
            STATUS_WARNING: "status-warning",
            STATUS_ERROR: "status-error",
        }
        context.add_class(severity_map.get(severity, "status-muted"))

    def _add_recent_folder(self, folder: str) -> None:
        normalized = normalize_folder(folder)
        updated = [normalized] + [item for item in self._recent_folders if item != normalized]
        self._recent_folders = updated[:RECENT_FOLDERS_LIMIT]

        try:
            save_recent_folders(self._recent_folders)
        except OSError as error:
            self._set_status_message(
                f"Could not save recent folders: {error}",
                STATUS_WARNING,
            )

    def _set_project_folder(self, folder: str, restart_session: bool) -> None:
        normalized = normalize_folder(folder)
        if not os.path.isdir(normalized):
            self._set_status_message("Selected path is not a folder", STATUS_ERROR)
            return

        self._project_folder = normalized
        self._set_project_path_entry_text(normalized)
        self._hide_project_path_suggestions()
        self._add_recent_folder(normalized)
        self._update_project_folder_labels()
        self._update_context_indicator()
        self._refresh_slash_commands()

        active_session = self._get_active_session()
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            active_session.project_path = normalized
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()

        self._set_status_message(
            f"Project folder set to {shorten_path(format_path(normalized), 40)}",
            STATUS_INFO,
        )

        if restart_session and self._active_session_id is not None:
            self._interrupt_running_process("Folder changed")
            self._conversation_id = None
            self._allowed_tools = set()
            self._add_system_message("Conversation reset because the project folder changed.")
            self._last_request_failed = False
            self._refresh_connection_state()

    def _cli_caps_for(self, provider_id: str | None = None) -> CliCapabilities:
        normalized_provider_id = normalize_provider_id(provider_id or self._active_provider_id)
        return self._provider_cli_caps.get(normalized_provider_id, CliCapabilities())

    def _set_cli_caps(self, provider_id: str, caps: CliCapabilities | None) -> None:
        normalized_provider_id = normalize_provider_id(provider_id)
        self._provider_cli_caps[normalized_provider_id] = caps or CliCapabilities()

    def _detect_cli_flag_support_async(self, binary_path: str, provider_id: str) -> None:
        normalized_provider_id = normalize_provider_id(provider_id)
        if not binary_path or normalized_provider_id not in PROVIDERS:
            self._set_cli_caps(normalized_provider_id, None)
            self._provider_cli_probe_inflight.discard(normalized_provider_id)
            if normalized_provider_id == self._active_provider_id:
                self._refresh_connection_state()
            return

        if normalized_provider_id in self._provider_cli_probe_inflight:
            return

        import threading

        self._provider_cli_probe_inflight.add(normalized_provider_id)

        def _probe() -> None:
            caps = detect_cli_flag_support(binary_path)
            GLib.idle_add(self._apply_cli_caps, normalized_provider_id, caps)

        threading.Thread(target=_probe, daemon=True).start()

    def _detect_provider_models_async(self, binary_path: str | None, provider_id: str) -> None:
        normalized_provider_id = normalize_provider_id(provider_id)
        if (
            not binary_path
            or normalized_provider_id in self._provider_model_probe_done
            or normalized_provider_id not in PROVIDERS
        ):
            return

        import threading

        def _probe_models() -> None:
            discovered_models = detect_provider_model_options(binary_path, normalized_provider_id)
            if not discovered_models:
                self._provider_model_probe_done.discard(normalized_provider_id)
                return
            GLib.idle_add(
                self._apply_detected_models,
                normalized_provider_id,
                discovered_models,
            )

        self._provider_model_probe_done.add(normalized_provider_id)
        threading.Thread(target=_probe_models, daemon=True).start()

    def _apply_detected_models(
        self,
        provider_id: str,
        detected_model_options: tuple[tuple[str, str], ...],
    ) -> bool:
        if not detected_model_options:
            return False

        refresh_provider_registry(load_settings(), detected_model_options={provider_id: detected_model_options})
        self._provider_binaries = {
            pid: find_provider_binary(list(provider.binary_names))
            for pid, provider in PROVIDERS.items()
        }

        if self._active_provider_id == provider_id:
            previous_model = ""
            if 0 <= self._selected_model_index < len(self._model_options):
                previous_model = self._model_options[self._selected_model_index][1]
            self._set_provider_option_lists(provider_id, preferred_model=previous_model)
            self._update_status_model_and_permission()
            self._sync_provider_state_to_webview()
            self._update_session_filter_buttons()

        return False

    def _apply_cli_caps(self, provider_id: str, caps: CliCapabilities | None) -> bool:
        normalized_provider_id = normalize_provider_id(provider_id)
        self._provider_cli_probe_inflight.discard(normalized_provider_id)
        self._set_cli_caps(normalized_provider_id, caps)
        if normalized_provider_id == self._active_provider_id:
            self._refresh_connection_state()
        return False

    def _show_missing_binary_error(self) -> None:
        provider = self._active_provider
        binary_names = ", ".join(provider.binary_names)
        message = f"{provider.name} CLI was not found. Expected binaries: {binary_names}."
        self.send_notification(f"{provider.name} CLI not found", message, urgency="critical")
        self._add_system_message(message)

        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=f"{provider.name} CLI not found",
        )
        dialog.set_modal(True)
        dialog.format_secondary_text(
            f"Install {provider.name} CLI and ensure one of these executables is available: {binary_names}."
        )
        dialog.run()
        dialog.destroy()

    def _invalidate_active_request(self) -> None:
        self._active_request_token = None

    def _is_current_request(self, request_token: str) -> bool:
        return bool(request_token) and request_token == self._active_request_token

    def _interrupt_running_process(self, reason: str) -> None:
        self._invalidate_active_request()
        self._permission_request_pending = False
        if not self._claude_process.is_running():
            return

        self._claude_process.stop()
        self._set_typing(False)
        self._add_system_message(f"Stopped current request: {reason}")
        self._refresh_connection_state()

    def _prompt_for_project_folder(self) -> None:
        if self._project_path_entry is None:
            return
        self._project_path_entry.grab_focus()
        self._project_path_entry.set_position(-1)
        self._refresh_project_path_suggestions(show_popover=True)
        self._set_status_message("Type a project folder path and press Enter", STATUS_INFO)

    def _choose_project_folder_with_dialog(self) -> str | None:
        dialog = Gtk.FileChooserDialog(
            title="Choose project folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.set_modal(True)
        dialog.set_show_hidden(True)
        dialog.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Select",
            Gtk.ResponseType.OK,
        )
        if os.path.isdir(self._project_folder):
            dialog.set_current_folder(self._project_folder)

        try:
            response = dialog.run()
            if response != Gtk.ResponseType.OK:
                return None
            selected = dialog.get_filename()
        finally:
            dialog.destroy()

        if not selected:
            return None
        return normalize_folder(selected)

    def _on_choose_folder_clicked(self, _button: Gtk.Button) -> None:
        selected = self._choose_project_folder_with_dialog()
        if selected is None:
            return
        self._set_project_path_entry_text(selected)
        self._set_project_folder(selected, restart_session=self._active_session_id is not None)

    def _on_js_change_folder(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        _js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        selected = self._choose_project_folder_with_dialog()
        if selected is None:
            return
        self._set_project_path_entry_text(selected)
        self._set_project_folder(selected, restart_session=self._active_session_id is not None)

    def _apply_session_option(self, kind: str, index: int) -> None:
        if kind == "model":
            options = self._model_options
            selected_index = self._selected_model_index
            running_change_reason = "Model changed"
            status_message = "Model updated"
            should_reset_conversation = True
        elif kind == "permission":
            options = self._permission_options
            selected_index = self._selected_permission_index
            running_change_reason = "Permission mode changed"
            status_message = "Permission mode updated"
            should_reset_conversation = False
        else:
            return

        if index < 0 or index >= len(options):
            return

        if index == selected_index:
            self._update_status_model_and_permission()
            return

        if kind == "model":
            self._selected_model_index = index
        else:
            self._selected_permission_index = index

        self._update_status_model_and_permission()
        self._update_context_indicator()
        active_session = self._get_active_session()
        had_conversation = False
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            had_conversation = active_session.conversation_id is not None
            if kind == "model":
                active_session.model = self._model_options[index][1]
                if had_conversation:
                    active_session.conversation_id = None
            else:
                active_session.permission_mode = self._permission_options[index][1]
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()
            if should_reset_conversation and had_conversation:
                self._reset_conversation_state("Conversation reset for model change")
        if self._has_messages and self._claude_process.is_running():
            self._interrupt_running_process(running_change_reason)
        self._set_status_message(status_message, STATUS_INFO)

    def _on_new_session_clicked(self, _button: Gtk.Button) -> None:
        if not os.path.isdir(self._project_folder):
            self._set_status_message("Current project folder is not available", STATUS_ERROR)
            self._prompt_for_project_folder()
            return
        self._start_new_session(self._project_folder)

    def _on_new_agent_clicked(self, _button: Gtk.Button) -> None:
        self._create_agent_pane()

    def _persist_agent_mode_preference(self) -> None:
        try:
            settings_payload = load_settings()
            settings_payload["agentctl_auto_enabled"] = self._agentctl_auto_enabled
            save_settings(settings_payload)
        except Exception as error:
            logger.exception("Could not persist auto agent control preference")
            self._set_status_message(
                f"Could not save auto agent controls preference: {error}",
                STATUS_WARNING,
            )

    def _sync_agent_mode_to_webviews(self, *, pane_id: str | None = None) -> None:
        target_panes = [pane_id] if pane_id is not None else list(self._pane_registry.keys())
        for target in target_panes:
            if target not in self._pane_registry:
                continue
            with self._pane_context(target):
                self._call_js("setAgentModeEnabled", self._agentctl_auto_enabled)

    def _on_agentctl_auto_toggle(self, toggle: Gtk.ToggleButton) -> None:
        self._agentctl_auto_enabled = bool(toggle.get_active())
        if self._agentctl_auto_enabled:
            toggle.set_tooltip_text("Auto-create agent controls in main chat (on)")
            self._set_status_message("Auto agent controls enabled.", STATUS_INFO)
        else:
            toggle.set_tooltip_text("Auto-create agent controls in main chat (off)")
            self._set_status_message("Auto agent controls disabled.", STATUS_INFO)
        self._persist_agent_mode_preference()
        self._sync_agent_mode_to_webviews()

    @staticmethod
    def _provider_order() -> list[str]:
        return list(PROVIDERS.keys())

    def _next_provider_id(self) -> str | None:
        ordered = self._provider_order()
        if len(ordered) <= 1:
            return None
        try:
            current_index = ordered.index(self._active_provider_id)
        except ValueError:
            return ordered[0]
        return ordered[(current_index + 1) % len(ordered)]

    def _provider_unavailability_reason(
        self,
        provider_id: str,
        *,
        refresh_binary: bool,
        check_auth: bool,
    ) -> str | None:
        normalized_provider_id = normalize_provider_id(provider_id)
        provider = PROVIDERS[normalized_provider_id]

        if refresh_binary or normalized_provider_id not in self._provider_binaries:
            self._provider_binaries[normalized_provider_id] = find_provider_binary(list(provider.binary_names))

        binary_path = self._provider_binaries.get(normalized_provider_id)
        if not binary_path:
            binary_list = ", ".join(provider.binary_names)
            return f"{provider.name} CLI was not found (expected: {binary_list})."

        if check_auth and normalized_provider_id == "codex" and not is_codex_authenticated():
            return "Codex is not authenticated (run `codex login`)."

        return None

    def _show_provider_unavailable_error(self, provider: ProviderConfig, reason: str) -> None:
        title = f"{provider.name} unavailable"
        self._set_status_message(reason, STATUS_ERROR)
        self._add_system_message(reason)
        self.send_notification(title, reason, urgency="critical")

        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=title,
        )
        dialog.set_modal(True)
        dialog.format_secondary_text(reason)
        dialog.run()
        dialog.destroy()

    def _update_provider_toggle_button(self) -> None:
        if self._provider_toggle_button is None:
            return

        active_provider = PROVIDERS[normalize_provider_id(self._active_provider_id)]
        next_provider_id = self._next_provider_id()
        display_provider = active_provider
        if next_provider_id is not None:
            display_provider = PROVIDERS[normalize_provider_id(next_provider_id)]

        icon_path = self._provider_switch_icon_path(display_provider.id)
        if self._provider_toggle_button_icon is not None and self._provider_toggle_button_label is not None:
            if icon_path is None:
                self._provider_toggle_button_icon.set_visible(False)
                self._provider_toggle_button_label.set_text(display_provider.name)
            else:
                self._provider_toggle_button_icon.set_from_file(str(icon_path))
                self._provider_toggle_button_icon.set_pixel_size(16)
                self._provider_toggle_button_icon.set_visible(True)
                self._provider_toggle_button_label.set_text(display_provider.name)
        if next_provider_id is None:
            self._provider_toggle_button.set_sensitive(False)
            self._provider_toggle_button.set_tooltip_text("No additional providers available")
            return

        reason = self._provider_unavailability_reason(
            next_provider_id,
            refresh_binary=True,
            check_auth=True,
        )
        if reason is None:
            next_provider_name = self._provider_display_name(next_provider_id)
            self._provider_toggle_button.set_sensitive(True)
            self._provider_toggle_button.set_tooltip_text(f"Switch to {next_provider_name}")
            return

        self._provider_toggle_button.set_sensitive(False)
        self._provider_toggle_button.set_tooltip_text(reason)

    def _on_provider_toggle_clicked(self, _button: Gtk.Button) -> None:
        next_provider_id = self._next_provider_id()
        if next_provider_id is None:
            return
        self._switch_provider(next_provider_id)

    def _provider_theme_variables(self, provider: ProviderConfig) -> dict[str, str]:
        accent_r, accent_g, accent_b = provider.accent_rgb
        accent_soft_r, accent_soft_g, accent_soft_b = provider.accent_soft_rgb
        colors = provider.colors
        return {
            "bg": colors["window_bg"],
            "sidebar": colors["sidebar_bg"],
            "input-bg": colors["button_bg"],
            "input-border": colors["border"],
            "input-focus": colors["accent_soft"],
            "user-bubble": colors["button_bg_hover"],
            "text": colors["foreground"],
            "muted": colors["foreground_muted"],
            "accent": colors["accent"],
            "accent-soft": f"rgba({accent_soft_r}, {accent_soft_g}, {accent_soft_b}, 0.18)",
            "chip-border": colors["border_soft"],
            "code-bg": colors["popover_bg"],
            "artifacts-panel-bg": colors["menu_bg"],
            "accent-rgb": f"{accent_r}, {accent_g}, {accent_b}",
            "accent-rgba-012": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.12)",
            "accent-rgba-072": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.72)",
            "accent-rgba-055": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.55)",
            "surface-panel": colors["sidebar_toggle_collapsed_bg"],
            "surface-card": colors["button_bg_hover"],
            "surface-card-soft": colors["button_bg"],
            "surface-muted": colors["button_bg"],
            "surface-muted-strong": colors["button_bg_hover"],
            "surface-chip": colors["session_filter_bg"],
            "surface-overlay": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.08)",
            "surface-overlay-soft": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.05)",
            "surface-overlay-border": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.22)",
            "text-soft": colors["session_meta_time"],
            "text-accent-soft": colors["accent_soft"],
            "permission-border": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.65)",
            "permission-gradient-start": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.18)",
            "permission-gradient-end": colors["window_bg"],
            "permission-shadow-soft": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.16)",
            "permission-shadow-strong": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.34)",
            "permission-glow": f"rgba({accent_r}, {accent_g}, {accent_b}, 0.2)",
            "inline-code-bg": colors["sidebar_toggle_collapsed_bg"],
            "inline-code-color": colors["accent_soft"],
            "table-border": colors["border"],
            "code-block-bg": colors["popover_bg"],
            "code-head-muted": colors["foreground_muted"],
        }

    @staticmethod
    def _short_model_title(label: str) -> str:
        candidate = str(label or "").split("(")[0].strip()
        candidate = candidate.replace("Claude ", "")
        return candidate or str(label or "")

    def _provider_model_option_payload(self, provider: ProviderConfig) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        for label, value in provider.model_options:
            payload.append(
                {
                    "value": value,
                    "short": self._short_model_title(label),
                    "title": label,
                    "description": f"{provider.name} model option",
                }
            )
        return payload

    def _provider_permission_option_payload(self, provider: ProviderConfig) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        for label, value, is_advanced in provider.permission_options:
            if value == "auto":
                description = f"{provider.name} asks only when approval is needed."
            elif value == "plan":
                description = f"{provider.name} proposes plans before applying changes."
            elif is_advanced:
                description = "Runs actions directly with fewer confirmations."
            else:
                description = f"{provider.name} permission option"
            payload.append(
                {
                    "value": value,
                    "title": label,
                    "description": description,
                }
            )
        return payload

    def _sync_provider_state_to_webview(self, *, pane_id: str | None = None) -> None:
        provider = self._active_provider
        target_panes = [pane_id] if pane_id is not None else list(self._pane_registry.keys())
        for target in target_panes:
            if target not in self._pane_registry:
                continue
            with self._pane_context(target):
                self._call_js("setReducedMotion", self._reduced_motion_from_gtk())
                self._call_js("applyProviderTheme", self._provider_theme_variables(provider))
                self._call_js("setModelOptions", self._provider_model_option_payload(provider))
                self._call_js("setPermissionOptions", self._provider_permission_option_payload(provider))
                self._call_js("setReasoningOptions", self._provider_reasoning_option_payload())
                self._call_js(
                    "setProviderBranding",
                    {
                        "id": provider.id,
                        "name": provider.name,
                        "iconUrl": self._provider_icon_data_uri(provider.id),
                        "welcomeTitle": f"{provider.name} is ready",
                    },
                )
                self._call_js("setReasoningVisible", provider.supports_reasoning)
                self._update_status_model_and_permission()
                if provider.supports_reasoning:
                    reasoning_value = self._reasoning_value_from_index(self._selected_reasoning_index)
                    self._call_js("updateReasoningLevel", reasoning_value)

    def _apply_settings_payload(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            payload = load_settings()

        refresh_provider_registry(payload)
        self._reasoning_options = get_reasoning_options(payload)

        self._provider_binaries = {
            provider_id: find_provider_binary(list(provider.binary_names))
            for provider_id, provider in PROVIDERS.items()
        }
        self._provider_model_probe_done.clear()
        self._provider_cli_caps.clear()
        self._provider_cli_probe_inflight.clear()
        for provider_id, binary_path in self._provider_binaries.items():
            self._detect_provider_models_async(binary_path, provider_id)
            self._detect_cli_flag_support_async(binary_path, provider_id)

        normalized_provider_id = normalize_provider_id(self._active_provider_id)
        self._active_provider_id = normalized_provider_id
        self._binary_path = self._provider_binaries.get(self._active_provider_id)
        active_session = self._get_active_session()
        if active_session is not None and normalize_provider_id(active_session.provider) != self._active_provider_id:
            self._active_session_id = None

        self._set_provider_option_lists(self._active_provider_id)
        self._ensure_active_session_for_provider(reset_conversation=False)

        active_session = self._get_active_session()
        if active_session is None:
            self._selected_reasoning_index = self._reasoning_index_from_value("medium")
            self._update_status_model_and_permission()
        else:
            if self._active_provider.supports_reasoning:
                self._selected_reasoning_index = self._reasoning_index_from_value(active_session.reasoning_level)
            else:
                self._selected_reasoning_index = self._reasoning_index_from_value("medium")
            self._update_status_model_and_permission()

        self._update_session_filter_buttons()
        self._update_provider_toggle_button()
        self._apply_provider_branding()
        self._swap_css(
            self._active_provider.colors,
            self._active_provider.accent_rgb,
            self._active_provider.accent_soft_rgb,
            reduced_motion=self._reduced_motion_from_gtk(),
        )
        self._refresh_session_list()
        self._refresh_connection_state()

    def _on_settings_button_clicked(self, _button: Gtk.Button) -> None:
        try:
            self._open_settings_editor()
        except Exception as error:
            logger.exception("Could not open settings editor")
            self._set_status_message(f"Could not open settings: {error}", STATUS_ERROR)

    def _open_settings_editor(self) -> None:
        original_payload = load_settings()
        working_payload = copy.deepcopy(original_payload)
        (
            default_width,
            default_height,
            min_width,
            min_height,
            max_width,
            max_height,
        ) = self._settings_dialog_size_constraints()

        dialog = Gtk.Dialog(
            title="App Settings",
            transient_for=self,
        )
        dialog.set_modal(True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.OK)
        dialog.set_resizable(True)
        if hasattr(dialog, "set_geometry_hints"):
            try:
                geometry = Gdk.Geometry()
                geometry.min_width = min_width
                geometry.min_height = min_height
                geometry.max_width = max_width
                geometry.max_height = max_height
                dialog.set_geometry_hints(
                    None,
                    geometry,
                    Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE,
                )
            except Exception:
                logger.debug("Geometry hints are unavailable in the current GDK runtime.", exc_info=True)
        dialog.set_default_size(default_width, default_height)

        content_area = dialog.get_content_area()
        content_area.set_spacing(8)
        content_area.set_border_width(8)

        helper_label = Gtk.Label(
            label="Customize providers, theme colors, model options and reasoning options.",
        )
        helper_label.set_xalign(0.0)
        helper_label.set_line_wrap(True)
        content_area.pack_start(helper_label, False, False, 0)

        notebook = Gtk.Notebook()
        notebook.set_scrollable(True)
        settings_scroller = Gtk.ScrolledWindow()
        settings_scroller.set_hexpand(True)
        settings_scroller.set_vexpand(True)
        settings_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        settings_scroller.set_min_content_width(max(280, min_width - 24))
        settings_scroller.set_min_content_height(240)
        settings_scroller.add(notebook)
        content_area.pack_start(settings_scroller, True, True, 0)

        hex_pattern = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

        def _normalize_hex(raw: str) -> str | None:
            if not isinstance(raw, str):
                return None
            value = raw.strip()
            if not value.startswith("#"):
                return None
            if not hex_pattern.match(value):
                return None
            if len(value) == 4:
                return f"#{value[1]*2}{value[2]*2}{value[3]*2}".lower()
            if len(value) == 7:
                return value.lower()
            return None

        def _to_hex_with_prefix(red: int, green: int, blue: int) -> str:
            return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"

        def _normalize_rgb_component(value: object) -> int:
            try:
                number = int(value)
            except (TypeError, ValueError):
                return 0
            return max(0, min(255, number))

        def _rgba_to_hex(color: Gdk.RGBA) -> str:
            return _to_hex_with_prefix(
                round(color.red * 255),
                round(color.green * 255),
                round(color.blue * 255),
            )

        def _hex_to_rgba(raw: str) -> Gdk.RGBA | None:
            rgba = Gdk.RGBA()
            if rgba.parse(raw):
                return rgba
            return None

        def _set_bg(widget: Gtk.Widget, value: str) -> None:
            color = _hex_to_rgba(value)
            if color is not None and hasattr(widget, "override_background_color"):
                widget.override_background_color(Gtk.StateFlags.NORMAL, color)

        def _set_fg(widget: Gtk.Widget, value: str) -> None:
            color = _hex_to_rgba(value)
            if color is not None and hasattr(widget, "override_color"):
                widget.override_color(Gtk.StateFlags.NORMAL, color)

        def _selected_reasoning_labels() -> list[tuple[str, str]]:
            result: list[tuple[str, str]] = []
            for entry in working_payload.get("reasoning_options", []):
                if not isinstance(entry, dict):
                    continue
                title = str(entry.get("title", "")).strip()
                value = str(entry.get("value", "")).strip()
                if title and value:
                    result.append((title, value))
            return result

        def _sync_reasoning_payload(reasoning_store: Gtk.ListStore) -> None:
            items: list[dict[str, str]] = []
            for row in reasoning_store:
                title = str(row[0]).strip()
                value = str(row[1]).strip()
                description = str(row[2]).strip()
                if not value:
                    value = "medium"
                if not title:
                    title = value
                items.append({"title": title, "value": value, "description": description})
            if not items:
                items.append(
                    {
                        "title": "Medium (Balanced)",
                        "value": "medium",
                        "description": "Balanced reasoning.",
                    },
                )
            working_payload["reasoning_options"] = items

        def _update_provider_model_payload(provider_id: str, model_store: Gtk.ListStore) -> None:
            provider = working_payload["providers"].get(provider_id)
            if not isinstance(provider, dict):
                return
            options: list[dict[str, str]] = []
            for row in model_store:
                label = str(row[0]).strip() or "Model"
                value = str(row[1]).strip() or label.lower().replace(" ", "-")
                options.append({"label": label, "value": value})
            provider["model_options"] = options

        def _normalize_payload() -> bool:
            providers = working_payload.get("providers")
            if not isinstance(providers, dict):
                return False
            for provider in providers.values():
                if not isinstance(provider, dict):
                    return False
                colors = provider.get("colors")
                if not isinstance(colors, dict):
                    return False
                for key, value in list(colors.items()):
                    normalized = _normalize_hex(str(value))
                    if normalized is None:
                        return False
                    colors[key] = normalized

                for key in ("accent_rgb", "accent_soft_rgb"):
                    rgb = provider.get(key)
                    if not isinstance(rgb, list) or len(rgb) < 3:
                        return False
                    provider[key] = [_normalize_rgb_component(v) for v in rgb[:3]]

                model_options = provider.get("model_options", [])
                normalized_models: list[dict[str, str]] = []
                if not isinstance(model_options, list) or not model_options:
                    return False
                for entry in model_options:
                    if not isinstance(entry, dict):
                        continue
                    label = str(entry.get("label", "")).strip() or "Model"
                    value = str(entry.get("value", "")).strip() or label.lower().replace(" ", "-")
                    normalized_models.append({"label": label, "value": value})
                if normalized_models:
                    provider["model_options"] = normalized_models
                else:
                    return False

            return True

        def _build_reasoning_tab() -> Gtk.Widget:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            page.set_border_width(8)

            model = Gtk.ListStore(str, str, str)
            for entry in working_payload.get("reasoning_options", []):
                if not isinstance(entry, dict):
                    continue
                model.append(
                    (
                        str(entry.get("title", "")),
                        str(entry.get("value", "")),
                        str(entry.get("description", "")),
                    ),
                )

            tree = Gtk.TreeView(model=model)
            for column_index, title, width in (
                (0, "Title", 180),
                (1, "Value", 130),
                (2, "Description", 300),
            ):
                renderer = Gtk.CellRendererText()
                renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
                column = Gtk.TreeViewColumn(title, renderer, text=column_index)
                column.set_resizable(True)
                column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
                column.set_fixed_width(width)
                column.set_min_width(width)
                tree.append_column(column)
            tree.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
            tree.set_headers_visible(True)

            scroller = Gtk.ScrolledWindow()
            scroller.set_hexpand(True)
            scroller.set_vexpand(True)
            scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scroller.add(tree)
            page.pack_start(scroller, True, True, 0)

            editor = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            title_entry = Gtk.Entry()
            title_entry.set_placeholder_text("Low (Fast)")
            title_entry.set_hexpand(True)
            value_entry = Gtk.Entry()
            value_entry.set_placeholder_text("low")
            value_entry.set_hexpand(True)
            description_entry = Gtk.Entry()
            description_entry.set_placeholder_text("Description")
            description_entry.set_hexpand(True)
            editor.pack_start(title_entry, True, True, 0)
            editor.pack_start(value_entry, True, True, 0)
            editor.pack_start(description_entry, True, True, 0)
            page.pack_start(editor, False, False, 0)

            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            add_btn = Gtk.Button(label="Add")
            update_btn = Gtk.Button(label="Update")
            remove_btn = Gtk.Button(label="Remove")
            up_btn = Gtk.Button(label="↑")
            down_btn = Gtk.Button(label="↓")
            btn_box.pack_start(add_btn, False, False, 0)
            btn_box.pack_start(update_btn, False, False, 0)
            btn_box.pack_start(remove_btn, False, False, 0)
            btn_box.pack_start(up_btn, False, False, 0)
            btn_box.pack_start(down_btn, False, False, 0)
            page.pack_start(btn_box, False, False, 0)

            selected = {"iter": None}

            def _reasoning_row_from_editor() -> tuple[str, str, str]:
                title = title_entry.get_text().strip()
                value = value_entry.get_text().strip()
                description = description_entry.get_text().strip()
                if not value:
                    value = "medium"
                if not title:
                    title = value
                return (title, value, description)

            def _selection_changed(_selection: Gtk.TreeSelection) -> None:
                _, selected_row = _selection.get_selected()
                selected["iter"] = selected_row
                if selected_row is None:
                    return
                title_entry.set_text(str(model[selected_row][0]))
                value_entry.set_text(str(model[selected_row][1]))
                description_entry.set_text(str(model[selected_row][2]))

            def _swap_items(step: int) -> None:
                row_iter = selected["iter"]
                if row_iter is None:
                    return
                path = model.get_path(row_iter)
                if path is None:
                    return
                index = path.get_indices()[0]
                target_index = index + step
                if target_index < 0 or target_index >= len(model):
                    return

                target = model.get_iter(Gtk.TreePath((target_index,)))
                if step < 0:
                    model.move_before(row_iter, target)
                else:
                    model.move_after(row_iter, target)
                selected["iter"] = row_iter
                tree.get_selection().select_iter(row_iter)
                _sync_reasoning_payload(model)

            def _reasoning_add(_button: Gtk.Button | None = None) -> None:
                row_iter = model.append(_reasoning_row_from_editor())
                selected["iter"] = row_iter
                tree.get_selection().select_iter(row_iter)
                _sync_reasoning_payload(model)

            def _reasoning_update(_button: Gtk.Button | None = None) -> None:
                row_iter = selected["iter"]
                if row_iter is None:
                    return
                title, value, description = _reasoning_row_from_editor()
                model.set_value(row_iter, 0, title)
                model.set_value(row_iter, 1, value)
                model.set_value(row_iter, 2, description)
                _sync_reasoning_payload(model)

            def _reasoning_remove(_button: Gtk.Button | None = None) -> None:
                row_iter = selected["iter"]
                if row_iter is None:
                    return
                model.remove(row_iter)
                selected["iter"] = None
                if len(model) == 0:
                    default_iter = model.append(("Medium (Balanced)", "medium", "Balanced reasoning."))
                    selected["iter"] = default_iter
                    tree.get_selection().select_iter(default_iter)
                _sync_reasoning_payload(model)

            tree.get_selection().connect("changed", _selection_changed)
            add_btn.connect("clicked", _reasoning_add)
            update_btn.connect("clicked", _reasoning_update)
            remove_btn.connect("clicked", _reasoning_remove)
            up_btn.connect("clicked", lambda _button: _swap_items(-1))
            down_btn.connect("clicked", lambda _button: _swap_items(1))
            _sync_reasoning_payload(model)
            return page

        def _build_provider_page(provider_id: str, payload: dict[str, Any]) -> Gtk.Widget:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            page.set_border_width(8)

            provider = working_payload["providers"].get(provider_id, {})
            if not isinstance(provider, dict):
                provider = copy.deepcopy(payload)
                working_payload["providers"][provider_id] = provider

            name = str(payload.get("name", provider_id))
            page.pack_start(Gtk.Label(label=f"Provider: {name}"), False, False, 0)

            support_reasoning = Gtk.CheckButton(label="Enable reasoning controls for this provider")
            support_reasoning.set_active(bool(provider.get("supports_reasoning", True)))
            support_reasoning.connect(
                "toggled",
                lambda button: (
                    provider.__setitem__("supports_reasoning", bool(button.get_active())),
                    _apply_preview(),
                ),
            )
            page.pack_start(support_reasoning, False, False, 0)

            preview_frame = Gtk.Frame(label="Preview")
            preview_root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            preview_root.set_border_width(8)

            preview_title = Gtk.Label(label=f"{name} preview")
            preview_title.set_xalign(0.0)
            preview_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            preview_header.pack_start(preview_title, True, True, 0)

            preview_user = Gtk.Frame()
            preview_user_label = Gtk.Label(label="User message")
            preview_user_label.set_xalign(0.0)
            preview_user_label.set_margin_start(8)
            preview_user_label.set_margin_end(8)
            preview_user_label.set_margin_top(6)
            preview_user_label.set_margin_bottom(6)
            preview_user.add(preview_user_label)

            preview_assistant = Gtk.Frame()
            preview_assistant_label = Gtk.Label(label="Assistant response")
            preview_assistant_label.set_xalign(0.0)
            preview_assistant_label.set_margin_start(8)
            preview_assistant_label.set_margin_end(8)
            preview_assistant_label.set_margin_top(6)
            preview_assistant_label.set_margin_bottom(6)
            preview_assistant.add(preview_assistant_label)

            preview_model_label = Gtk.Label(label="Model: default")
            preview_model_label.set_xalign(0.0)
            preview_reason_label = Gtk.Label(label="Reasoning: medium")
            preview_reason_label.set_xalign(0.0)

            preview_root.pack_start(preview_header, False, False, 0)
            preview_root.pack_start(preview_user, False, False, 0)
            preview_root.pack_start(preview_assistant, False, False, 0)
            preview_root.pack_start(preview_model_label, False, False, 0)
            preview_root.pack_start(preview_reason_label, False, False, 0)
            preview_frame.add(preview_root)

            def _apply_preview() -> None:
                providers_payload = working_payload.get("providers")
                if isinstance(providers_payload, dict):
                    raw_provider = providers_payload.get(provider_id, {})
                else:
                    raw_provider = {}
                current_provider = raw_provider if isinstance(raw_provider, dict) else {}
                raw_colors = current_provider.get("colors", {})
                colors = raw_colors if isinstance(raw_colors, dict) else {}

                window_bg = _normalize_hex(str(colors.get("window_bg", "#1f1f1a"))) or "#1f1f1a"
                header_bg = _normalize_hex(str(colors.get("header_bg", "#262621"))) or "#262621"
                user_bg = _normalize_hex(str(colors.get("button_bg", "#3a3a34"))) or "#3a3a34"
                assistant_bg = _normalize_hex(str(colors.get("chat_bg", "#2f2f2a"))) or "#2f2f2a"
                fg = _normalize_hex(str(colors.get("foreground", "#d4d4c8"))) or "#d4d4c8"

                _set_bg(preview_root, window_bg)
                _set_bg(preview_header, header_bg)
                _set_bg(preview_user, user_bg)
                _set_bg(preview_assistant, assistant_bg)
                _set_fg(preview_title, fg)
                _set_fg(preview_user_label, fg)
                _set_fg(preview_assistant_label, fg)
                _set_fg(preview_model_label, fg)
                _set_fg(preview_reason_label, fg)

                model_options_raw = current_provider.get("model_options", [])
                model_options = model_options_raw if isinstance(model_options_raw, list) else []
                model_value = "default"
                for item in model_options:
                    if not isinstance(item, dict):
                        continue
                    candidate = str(item.get("value", "")).strip()
                    if candidate:
                        model_value = candidate
                        break
                preview_model_label.set_text(f"Model: {model_value}")

                if current_provider.get("supports_reasoning", False):
                    reasons = _selected_reasoning_labels()
                    if reasons:
                        preview_reason_label.set_text(
                            f"Reasoning: {reasons[0][0]} ({reasons[0][1]})",
                        )
                    else:
                        preview_reason_label.set_text("Reasoning: medium")
                else:
                    preview_reason_label.set_text("Reasoning: disabled")

            colors_map = provider.setdefault("colors", {})
            colors_frame = Gtk.Frame(label="Theme Colors")
            colors_grid = Gtk.Grid()
            colors_grid.set_row_spacing(6)
            colors_grid.set_column_spacing(8)
            colors_grid.set_border_width(8)
            colors_frame.add(colors_grid)
            page.pack_start(colors_frame, False, False, 0)

            color_buttons: dict[str, Gtk.ColorButton] = {}

            def _color_sync(entry: Gtk.Entry, pid: str, key: str, button: Gtk.ColorButton) -> None:
                normalized = _normalize_hex(entry.get_text())
                if normalized is None:
                    return
                data_provider = working_payload["providers"].get(pid)
                if not isinstance(data_provider, dict):
                    return
                data_colors = data_provider.setdefault("colors", {})
                if isinstance(data_colors, dict):
                    data_colors[key] = normalized
                button_color = _hex_to_rgba(normalized)
                if button_color is not None:
                    button.set_rgba(button_color)
                _apply_preview()

            def _color_button_sync(button: Gtk.ColorButton, pid: str, key: str, entry: Gtk.Entry) -> None:
                data_provider = working_payload["providers"].get(pid)
                if not isinstance(data_provider, dict):
                    return
                data_colors = data_provider.setdefault("colors", {})
                hex_color = _rgba_to_hex(button.get_rgba())
                data_colors[key] = hex_color
                entry.set_text(hex_color)
                _apply_preview()

            color_items = sorted(colors_map.keys())
            for row, key in enumerate(color_items):
                value = _normalize_hex(str(colors_map.get(key, "#000000"))) or "#000000"
                colors_map[key] = value

                key_label = Gtk.Label(label=key)
                key_label.set_xalign(0.0)
                colors_grid.attach(key_label, 0, row, 1, 1)

                value_entry = Gtk.Entry()
                value_entry.set_width_chars(10)
                value_entry.set_text(value)
                color_button = Gtk.ColorButton()
                color_buttons[key] = color_button
                parsed_rgba = _hex_to_rgba(value)
                if parsed_rgba is not None:
                    color_button.set_rgba(parsed_rgba)
                value_entry.connect(
                    "changed",
                    lambda entry, pid=provider_id, color_key=key, button=color_button: _color_sync(
                        entry,
                        pid,
                        color_key,
                        button,
                    ),
                )
                color_button.connect(
                    "color-set",
                    lambda button, pid=provider_id, color_key=key, field=value_entry: _color_button_sync(
                        button,
                        pid,
                        color_key,
                        field,
                    ),
                )
                colors_grid.attach(value_entry, 1, row, 1, 1)
                colors_grid.attach(color_button, 2, row, 1, 1)

            def _sync_rgb_value(pid: str, rgb_key: str, index: int, spinner: Gtk.SpinButton) -> None:
                data_provider = working_payload["providers"].get(pid)
                if not isinstance(data_provider, dict):
                    return
                rgb = data_provider.get(rgb_key)
                if not isinstance(rgb, list) or len(rgb) < 3:
                    rgb = [0, 0, 0]
                rgb[index] = _normalize_rgb_component(spinner.get_value())
                data_provider[rgb_key] = rgb
                _apply_preview()

            accent_frame = Gtk.Frame(label="Accent RGB")
            accent_grid = Gtk.Grid()
            accent_grid.set_column_spacing(6)
            accent_grid.set_row_spacing(4)
            accent_grid.set_border_width(8)
            accent_frame.add(accent_grid)

            accent_row = 0
            for key in ("accent_rgb", "accent_soft_rgb"):
                accent_grid.attach(Gtk.Label(label=key), 0, accent_row, 1, 1)
                rgb_values = provider.get(key, [0, 0, 0])
                if not isinstance(rgb_values, list) or len(rgb_values) < 3:
                    rgb_values = [0, 0, 0]
                for index, channel in enumerate(("R", "G", "B")):
                    accent_grid.attach(Gtk.Label(label=f"{channel}"), 1 + index * 2, accent_row, 1, 1)
                    adjustment = Gtk.Adjustment(
                        value=float(_normalize_rgb_component(rgb_values[index])),
                        lower=0,
                        upper=255,
                        step_increment=1,
                        page_increment=10,
                        page_size=0,
                    )
                    spin = Gtk.SpinButton(adjustment=adjustment, climb_rate=1.0, digits=0)
                    spin.set_width_chars(4)
                    spin.connect(
                        "value-changed",
                        lambda spinner, pid=provider_id, rgb_name=key, i=index: _sync_rgb_value(
                            pid,
                            rgb_name,
                            i,
                            spinner,
                        ),
                    )
                    accent_grid.attach(spin, 2 + index * 2, accent_row, 1, 1)
                accent_row += 1
            page.pack_start(accent_frame, False, False, 0)

            models_frame = Gtk.Frame(label="Model options")
            models_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            models_box.set_border_width(8)
            models_frame.add(models_box)

            model_store = Gtk.ListStore(str, str)
            for model_entry in provider.get("model_options", []):
                if not isinstance(model_entry, dict):
                    continue
                model_store.append(
                    (
                        str(model_entry.get("label", "")) or "Model",
                        str(model_entry.get("value", "")) or "model",
                    ),
                )

            model_view = Gtk.TreeView(model=model_store)
            model_label_renderer = Gtk.CellRendererText()
            model_label_renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            model_label_column = Gtk.TreeViewColumn("Label", model_label_renderer, text=0)
            model_label_column.set_resizable(True)
            model_label_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            model_label_column.set_fixed_width(190)
            model_label_column.set_min_width(150)
            model_view.append_column(model_label_column)

            model_value_renderer = Gtk.CellRendererText()
            model_value_renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            model_value_column = Gtk.TreeViewColumn("Value", model_value_renderer, text=1)
            model_value_column.set_resizable(True)
            model_value_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            model_value_column.set_fixed_width(250)
            model_value_column.set_min_width(170)
            model_view.append_column(model_value_column)
            model_view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

            model_scroller = Gtk.ScrolledWindow()
            model_scroller.set_hexpand(True)
            model_scroller.set_vexpand(True)
            model_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            model_scroller.set_min_content_height(130)
            model_scroller.add(model_view)
            models_box.pack_start(model_scroller, True, True, 0)

            model_edit = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            model_label_entry = Gtk.Entry()
            model_label_entry.set_placeholder_text("Model label")
            model_label_entry.set_hexpand(True)
            model_value_entry = Gtk.Entry()
            model_value_entry.set_placeholder_text("Model value")
            model_value_entry.set_hexpand(True)
            model_edit.pack_start(model_label_entry, True, True, 0)
            model_edit.pack_start(model_value_entry, True, True, 0)
            models_box.pack_start(model_edit, False, False, 0)

            model_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            model_add_btn = Gtk.Button(label="Add")
            model_update_btn = Gtk.Button(label="Update")
            model_remove_btn = Gtk.Button(label="Remove")
            model_btn_box.pack_start(model_add_btn, False, False, 0)
            model_btn_box.pack_start(model_update_btn, False, False, 0)
            model_btn_box.pack_start(model_remove_btn, False, False, 0)
            models_box.pack_start(model_btn_box, False, False, 0)

            selected_model = {"iter": None}

            def _model_selection_changed(selection: Gtk.TreeSelection) -> None:
                _, model_iter = selection.get_selected()
                selected_model["iter"] = model_iter
                if model_iter is None:
                    return
                model_label_entry.set_text(str(model_store[model_iter][0]))
                model_value_entry.set_text(str(model_store[model_iter][1]))

            def _model_remove_if_selected() -> None:
                row_iter = selected_model["iter"]
                if row_iter is None:
                    return
                model_store.remove(row_iter)
                selected_model["iter"] = None
                if len(model_store) == 0:
                    model_store.append(("Default", "model"))
                _update_provider_model_payload(provider_id, model_store)
                _apply_preview()

            def _model_add(_button: Gtk.Button | None = None) -> None:
                model_store.append(
                    (
                        model_label_entry.get_text().strip() or "Model",
                        model_value_entry.get_text().strip() or "model",
                    ),
                )
                _update_provider_model_payload(provider_id, model_store)
                _apply_preview()

            def _model_update(_button: Gtk.Button | None = None) -> None:
                row_iter = selected_model["iter"]
                if row_iter is None:
                    return
                model_store.set_value(
                    row_iter,
                    0,
                    model_label_entry.get_text().strip() or "Model",
                )
                model_store.set_value(
                    row_iter,
                    1,
                    model_value_entry.get_text().strip() or "model",
                )
                _update_provider_model_payload(provider_id, model_store)
                _apply_preview()

            def _model_remove(_button: Gtk.Button | None = None) -> None:
                _model_remove_if_selected()

            model_view.get_selection().connect("changed", _model_selection_changed)
            model_add_btn.connect("clicked", _model_add)
            model_update_btn.connect("clicked", _model_update)
            model_remove_btn.connect("clicked", _model_remove)
            _update_provider_model_payload(provider_id, model_store)

            page.pack_start(models_frame, True, True, 0)
            page.pack_start(preview_frame, False, False, 0)
            _apply_preview()
            return page

        reasoning_tab = _build_reasoning_tab()
        notebook.append_page(reasoning_tab, Gtk.Label(label="Reasoning"))

        providers = working_payload.get("providers")
        if isinstance(providers, dict):
            for provider_id, provider_payload in providers.items():
                if not isinstance(provider_payload, dict):
                    continue
                page = _build_provider_page(provider_id, provider_payload)
                label = str(provider_payload.get("name", provider_id))
                notebook.append_page(page, Gtk.Label(label=label))

        content_area.show_all()

        while True:
            response = dialog.run()
            if response != Gtk.ResponseType.OK:
                break

            if not _normalize_payload():
                msg = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CLOSE,
                    text="Invalid settings values",
                )
                msg.format_secondary_text(
                    "Invalid hex / rgb fields detected. Use #RRGGBB and 0-255 for colors.",
                )
                msg.run()
                msg.destroy()
                continue

            try:
                save_settings(working_payload)
                self._apply_settings_payload(working_payload)
            except (OSError, ValueError, TypeError) as error:
                msg = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CLOSE,
                    text="Could not save settings",
                )
                msg.format_secondary_text(str(error))
                msg.run()
                msg.destroy()
                continue
            self._set_status_message("Settings saved and applied.", STATUS_INFO)
            break

        dialog.destroy()

    def _apply_provider_branding(self) -> None:
        self.set_title(self._provider_window_title())
        self._sync_provider_state_to_webview()

    def _set_provider_option_lists(
        self,
        provider_id: str,
        *,
        preferred_model: str | None = None,
        preferred_permission: str | None = None,
        preserve_previous_model: bool = True,
    ) -> None:
        provider = PROVIDERS[normalize_provider_id(provider_id)]
        previous_model_value = ""
        if (
            preserve_previous_model
            and 0 <= self._selected_model_index < len(self._model_options)
        ):
            previous_model_value = self._model_options[self._selected_model_index][1]
        previous_permission_value = ""
        if 0 <= self._selected_permission_index < len(self._permission_options):
            previous_permission_value = self._permission_options[self._selected_permission_index][1]

        self._model_options = list(provider.model_options)
        self._permission_options = list(provider.permission_options)

        normalized_model = normalize_model_value(
            preferred_model if preferred_model is not None else previous_model_value,
            provider=provider.id,
        )
        normalized_permission = normalize_permission_value(
            preferred_permission if preferred_permission is not None else previous_permission_value,
            provider=provider.id,
        )
        self._selected_model_index = self._model_index_from_value(normalized_model)
        self._selected_permission_index = self._permission_index_from_value(normalized_permission)
        if not provider.supports_reasoning:
            self._selected_reasoning_index = self._reasoning_index_from_value("medium")
            return

    def _stop_running_request_for_provider_switch(self) -> bool:
        all_stopped = True
        for pane_id, pane in self._pane_registry.items():
            with self._pane_context(pane_id):
                self._invalidate_active_request()
                self._permission_request_pending = False
                process = pane._claude_process
                if process is None or not process.is_running():
                    continue

                process.stop()
                deadline = time.monotonic() + 2.5
                while process.is_running() and time.monotonic() < deadline:
                    while Gtk.events_pending():
                        Gtk.main_iteration_do(False)
                    time.sleep(0.03)

                if process.is_running():
                    process.stop(force=True)
                    force_deadline = time.monotonic() + 1.0
                    while process.is_running() and time.monotonic() < force_deadline:
                        while Gtk.events_pending():
                            Gtk.main_iteration_do(False)
                        time.sleep(0.03)

                if process.is_running():
                    all_stopped = False
                    logger.warning("Pane %s did not stop before provider switch.", pane_id)

        return all_stopped

    def _ensure_active_session_for_provider(self, *, reset_conversation: bool) -> None:
        active_sessions = [
            session
            for session in self._sessions
            if session.provider == self._active_provider_id and session.status != SESSION_STATUS_ARCHIVED
        ]

        if not active_sessions:
            self._active_session_id = None
            self._conversation_id = None
            return

        selected = max(active_sessions, key=self._session_sort_key)
        for session in active_sessions:
            if session.id != selected.id and session.status == SESSION_STATUS_ACTIVE:
                session.status = SESSION_STATUS_ENDED
        self._active_session_id = selected.id
        selected.status = SESSION_STATUS_ACTIVE
        selected.last_used_at = current_timestamp()
        if reset_conversation:
            selected.conversation_id = None
        self._apply_session_to_controls(selected, add_to_recent=os.path.isdir(selected.project_path))
        self._conversation_id = None if reset_conversation else selected.conversation_id

    def _switch_provider(self, new_provider_id: str) -> bool:
        normalized_new_provider_id = normalize_provider_id(new_provider_id)
        if normalized_new_provider_id == self._active_provider_id:
            return True

        new_provider = PROVIDERS[normalized_new_provider_id]
        reason = self._provider_unavailability_reason(
            normalized_new_provider_id,
            refresh_binary=True,
            check_auth=True,
        )
        if reason is not None:
            self._show_provider_unavailable_error(new_provider, reason)
            self._update_provider_toggle_button()
            return False

        new_binary_path = self._provider_binaries.get(normalized_new_provider_id)
        old_provider_id = self._active_provider_id
        old_provider = PROVIDERS[old_provider_id]
        old_binary_path = self._binary_path
        old_model_options = list(self._model_options)
        old_permission_options = list(self._permission_options)
        old_selected_model_index = self._selected_model_index
        old_selected_permission_index = self._selected_permission_index
        old_selected_reasoning_index = self._selected_reasoning_index
        old_active_session_id = self._active_session_id
        old_conversation_id = self._conversation_id
        old_allowed_tools = set(self._allowed_tools)
        old_has_messages = self._has_messages
        old_last_request_failed = self._last_request_failed
        old_active_assistant_message = self._active_assistant_message
        old_active_session = self._get_active_session()
        old_active_session_status = old_active_session.status if old_active_session is not None else None
        old_active_session_last_used = (
            old_active_session.last_used_at if old_active_session is not None else None
        )

        if not self._stop_running_request_for_provider_switch():
            self._update_provider_toggle_button()
            self._set_status_message("Could not stop current request. Provider switch cancelled.", STATUS_ERROR)
            return False

        try:
            self._swap_css(
                new_provider.colors,
                new_provider.accent_rgb,
                new_provider.accent_soft_rgb,
                reduced_motion=self._reduced_motion_from_gtk(),
            )
            self._active_provider_id = normalized_new_provider_id
            self._binary_path = new_binary_path
            self._detect_provider_models_async(new_binary_path, normalized_new_provider_id)
            self._detect_cli_flag_support_async(new_binary_path or "", normalized_new_provider_id)
            self._set_provider_option_lists(
                normalized_new_provider_id,
                preserve_previous_model=False,
            )
            self._collapse_to_primary_pane()
            self._ensure_active_session_for_provider(reset_conversation=True)

            if old_active_session is not None and old_active_session.status == SESSION_STATUS_ACTIVE:
                old_active_session.status = SESSION_STATUS_ENDED
                old_active_session.last_used_at = current_timestamp()

            for pane_id in list(self._pane_registry.keys()):
                with self._pane_context(pane_id):
                    self._conversation_id = None
                    self._allowed_tools = set()
                    self._clear_messages()
                    self._show_welcome()
                    self._set_typing(False)
                    self._has_messages = False
                    self._last_request_failed = False
                    self._active_assistant_message = ""

            self._apply_provider_branding()
            self._refresh_session_list()
            self._update_pane_close_buttons()
            self._update_all_pane_headers()
            self._refresh_slash_commands()
            self._save_sessions_safe("Could not save sessions")
            self._update_provider_toggle_button()

            if self._binary_path is None:
                self._set_connection_state(CONNECTION_DISCONNECTED)
                self._show_missing_binary_error()
            else:
                self._detect_cli_flag_support_async(self._binary_path, self._active_provider_id)
                self._refresh_connection_state()
            self._set_status_message(f"Switched to {new_provider.name}", STATUS_INFO)
            return True
        except Exception as error:
            logger.exception("Provider switch failed; rolling back provider state.")
            self._active_provider_id = old_provider_id
            self._binary_path = old_binary_path
            self._model_options = old_model_options
            self._permission_options = old_permission_options
            self._selected_model_index = old_selected_model_index
            self._selected_permission_index = old_selected_permission_index
            self._selected_reasoning_index = old_selected_reasoning_index
            self._active_session_id = old_active_session_id
            self._conversation_id = old_conversation_id
            self._allowed_tools = old_allowed_tools
            self._has_messages = old_has_messages
            self._last_request_failed = old_last_request_failed
            self._active_assistant_message = old_active_assistant_message
            if old_active_session is not None and old_active_session_status is not None:
                old_active_session.status = old_active_session_status
                if old_active_session_last_used is not None:
                    old_active_session.last_used_at = old_active_session_last_used
            self._swap_css(
                old_provider.colors,
                old_provider.accent_rgb,
                old_provider.accent_soft_rgb,
                reduced_motion=self._reduced_motion_from_gtk(),
            )
            self._apply_provider_branding()
            self._refresh_session_list()
            self._update_provider_toggle_button()
            self._refresh_connection_state()
            self._set_status_message(f"Could not switch provider: {error}", STATUS_ERROR)
            return False

    def _on_sidebar_toggle_clicked(self, _button: Any) -> None:
        self._sidebar_expanded = not self._sidebar_expanded
        self._set_sidebar_content_visibility(self._sidebar_expanded)
        self._update_sidebar_toggle_button()
        self._pulse_sidebar_toggle_button()
        target_width = SIDEBAR_OPEN_WIDTH if self._sidebar_expanded else SIDEBAR_COLLAPSED_WIDTH
        self._animate_sidebar(target_width)

    def _update_sidebar_toggle_button(self) -> None:
        if self._sidebar_toggle_button is None:
            return

        context = self._sidebar_toggle_button.get_style_context()
        context.remove_class("sidebar-toggle-expanded")
        context.remove_class("sidebar-toggle-collapsed")

        if self._sidebar_expanded:
            context.add_class("sidebar-toggle-expanded")
            self._sidebar_toggle_button.set_tooltip_text("Collapse sidebar")
            return

        context.add_class("sidebar-toggle-collapsed")
        self._sidebar_toggle_button.set_tooltip_text("Expand sidebar")

    def _pulse_sidebar_toggle_button(self) -> None:
        if self._sidebar_toggle_button is None:
            return

        if self._sidebar_toggle_pulse_animation_id is not None:
            GLib.source_remove(self._sidebar_toggle_pulse_animation_id)
            self._sidebar_toggle_pulse_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 170.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            envelope = math.sin(progress * math.pi)
            self._sidebar_toggle_button.set_opacity(0.78 + envelope * 0.22)

            if progress >= 1.0:
                self._sidebar_toggle_button.set_opacity(1.0)
                self._sidebar_toggle_pulse_animation_id = None
                return False
            return True

        self._sidebar_toggle_pulse_animation_id = GLib.timeout_add(16, tick)

    def _set_sidebar_content_visibility(self, expanded: bool) -> None:
        for widget in self._sidebar_expanded_only_widgets:
            widget.set_visible(expanded)

        if self._sidebar_container is None:
            return

        style_context = self._sidebar_container.get_style_context()
        if expanded:
            style_context.remove_class("sidebar-collapsed")
            return
        style_context.add_class("sidebar-collapsed")

    def _animate_sidebar(self, target_width: int) -> None:
        if self._sidebar_container is None:
            return

        if self._sidebar_animation_id is not None:
            GLib.source_remove(self._sidebar_animation_id)
            self._sidebar_animation_id = None

        if target_width > 0 and not self._sidebar_container.get_visible():
            self._sidebar_container.set_visible(True)

        start_width = self._sidebar_current_width
        delta = float(target_width) - start_width
        duration_ms = 360.0 if target_width > start_width else 240.0
        start_time_us = GLib.get_monotonic_time()

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            eased = self._ease_in_out_cubic(progress)
            width = start_width + (delta * eased)
            self._set_sidebar_width(width)

            if progress >= 1.0:
                self._set_sidebar_width(float(target_width))
                self._sidebar_animation_id = None
                return False
            return True

        self._sidebar_animation_id = GLib.timeout_add(16, tick)

    def _set_sidebar_width(self, width: float) -> None:
        if self._sidebar_container is None:
            return

        clamped = max(float(SIDEBAR_COLLAPSED_WIDTH), min(float(SIDEBAR_OPEN_WIDTH), width))
        self._sidebar_current_width = clamped

        if not self._sidebar_container.get_visible():
            self._sidebar_container.set_visible(True)

        self._sidebar_container.set_size_request(int(clamped), -1)
        self._sidebar_container.set_opacity(1.0)

    def _on_map_event(self, _widget: Gtk.Widget, _event: Gdk.Event) -> bool:
        if not self._window_fade_started:
            self._window_fade_started = True
            self._start_window_fade_in()
        return False

    def _start_window_fade_in(self) -> None:
        self.set_opacity(0.0)

        if self._window_fade_animation_id is not None:
            GLib.source_remove(self._window_fade_animation_id)
            self._window_fade_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 320.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            eased = self._ease_out_cubic(progress)
            self.set_opacity(eased)
            if progress >= 1.0:
                self._window_fade_animation_id = None
                return False
            return True

        self._window_fade_animation_id = GLib.timeout_add(16, tick)

    def _start_status_fade_in(self) -> None:
        if not self._status_fade_widgets:
            return

        if self._status_fade_animation_id is not None:
            GLib.source_remove(self._status_fade_animation_id)
            self._status_fade_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 360.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            eased = self._ease_out_cubic(progress)

            for widget in self._status_fade_widgets:
                widget.set_opacity(eased)

            if progress >= 1.0:
                self._status_fade_animation_id = None
                return False
            return True

        self._status_fade_animation_id = GLib.timeout_add(16, tick)

    def _start_chat_reveal_in(self) -> None:
        if not self._chat_reveal_widgets:
            return

        if self._chat_reveal_animation_id is not None:
            GLib.source_remove(self._chat_reveal_animation_id)
            self._chat_reveal_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 360.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            done = True

            for widget, delay_ms in self._chat_reveal_widgets:
                local_progress = self._clamp01((elapsed_ms - delay_ms) / duration_ms)
                widget.set_opacity(self._ease_out_cubic(local_progress))
                if local_progress < 1.0:
                    done = False

            if done:
                self._chat_reveal_animation_id = None
                return False
            return True

        self._chat_reveal_animation_id = GLib.timeout_add(16, tick)

    def _pulse_chat_shell(self) -> None:
        if self._chat_shell is None:
            return

        if self._chat_pulse_animation_id is not None:
            GLib.source_remove(self._chat_pulse_animation_id)
            self._chat_pulse_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 480.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            envelope = math.sin(progress * math.pi)
            self._chat_shell.set_opacity(0.92 + envelope * 0.08)

            if progress >= 1.0:
                self._chat_shell.set_opacity(1.0)
                self._chat_pulse_animation_id = None
                return False
            return True

        self._chat_pulse_animation_id = GLib.timeout_add(16, tick)

    def _update_session_timer(self) -> bool:
        if self._session_timer_label is None:
            return False

        elapsed = max(0, (GLib.get_monotonic_time() - self._session_started_us) // 1_000_000)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self._session_timer_label.set_text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        return True

    def _update_usage_display(self) -> None:
        if self._session_limit_label is not None:
            cost = self._session_cost_usd
            self._session_limit_label.set_text(f"${cost:.2f}")
            ctx = self._session_limit_label.get_style_context()
            ctx.remove_class("usage-warn")
            ctx.remove_class("usage-high")
            if cost >= 5.0:
                ctx.add_class("usage-high")
            elif cost >= 2.0:
                ctx.add_class("usage-warn")

        if self._weekly_limit_label is not None:
            tokens = self._session_tokens
            if tokens >= 1_000_000:
                display = f"{tokens / 1_000_000:.1f}M tokens"
            elif tokens >= 1000:
                display = f"{tokens // 1000}k tokens"
            else:
                display = f"{tokens} tokens"
            self._weekly_limit_label.set_text(display)

    def _on_webview_load_changed(
        self,
        pane_id: str,
        _webview: WebKit.WebView,
        load_event: WebKit.LoadEvent,
    ) -> None:
        if load_event != WebKit.LoadEvent.FINISHED:
            return

        with self._pane_context(pane_id):
            self._webview_ready = True
            queued = list(self._pending_webview_scripts)
            self._pending_webview_scripts.clear()

            for script in queued:
                self._run_javascript(script)

            self._call_js("setReducedMotion", self._reduced_motion_from_gtk())
            self._sync_provider_state_to_webview(pane_id=pane_id)
            self._sync_agent_mode_to_webviews(pane_id=pane_id)
            self._show_welcome()
            self._replay_active_session_if_present()
            self._refresh_slash_commands()
            if pane_id == self._active_pane_id:
                GLib.timeout_add(120, lambda pid=pane_id: self._focus_chat_input_in_pane(pid))

    def _focus_chat_input_in_pane(self, pane_id: str) -> bool:
        pane = self._pane_by_id(pane_id)
        if pane is None or pane._webview is None:
            return False
        pane._webview.grab_focus()
        with self._pane_context(pane_id):
            self._call_js("focusInput")
        return False

    def _on_webview_focus_in(
        self,
        pane_id: str,
        _webview: WebKit.WebView,
        _event: Gdk.EventFocus,
    ) -> bool:
        self._set_active_pane(pane_id)
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().add_class("chat-focused")
        return False

    def _on_webview_focus_out(
        self,
        pane_id: str,
        _webview: WebKit.WebView,
        _event: Gdk.EventFocus,
    ) -> bool:
        self._set_active_pane(pane_id)
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().remove_class("chat-focused")
        return False

    def _on_js_change_model(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        raw_value = self._extract_message_from_js_result(js_result)
        model_value = normalize_model_value(raw_value, provider=self._active_provider_id)
        self._apply_session_option("model", self._model_index_from_value(model_value))

    def _on_js_change_permission(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        raw_value = self._extract_message_from_js_result(js_result)
        permission_value = normalize_permission_value(raw_value, provider=self._active_provider_id)
        self._apply_session_option("permission", self._permission_index_from_value(permission_value))

    def _on_js_change_reasoning(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        if not self._active_provider.supports_reasoning:
            self._set_status_message(
                f"Reasoning level is ignored in {self._active_provider.name} mode.",
                STATUS_MUTED,
            )
            self._call_js("setReasoningVisible", False)
            return

        value = self._extract_message_from_js_result(js_result)
        index = self._reasoning_index_from_value(value)
        if index == self._selected_reasoning_index:
            return

        self._selected_reasoning_index = index
        reasoning_value = self._reasoning_value_from_index(self._selected_reasoning_index)

        active = self._get_active_session()
        had_conversation = False
        if active is not None:
            had_conversation = active.conversation_id is not None
            active.reasoning_level = reasoning_value
            if had_conversation:
                active.conversation_id = None
            self._save_sessions_safe("Could not save session reasoning level")
            if had_conversation:
                self._reset_conversation_state("Conversation reset for reasoning change")

        self._set_status_message(f"Reasoning level set to {reasoning_value}", STATUS_MUTED)

    def _on_js_refresh_slash_commands(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        _js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        self._refresh_slash_commands()

    def _on_js_toggle_agent_mode(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        raw_value = self._extract_message_from_js_result(js_result).strip().lower()
        if raw_value == "on":
            next_enabled = True
        elif raw_value == "off":
            next_enabled = False
        elif raw_value in {"true", "yes", "1"}:
            next_enabled = True
        elif raw_value in {"false", "no", "0"}:
            next_enabled = False
        else:
            next_enabled = not self._agentctl_auto_enabled

        if next_enabled == self._agentctl_auto_enabled:
            return

        self._agentctl_auto_enabled = next_enabled
        if next_enabled:
            self._set_status_message("Auto agent controls enabled.", STATUS_INFO)
        else:
            self._set_status_message("Auto agent controls disabled.", STATUS_WARNING)
        self._persist_agent_mode_preference()
        self._sync_agent_mode_to_webviews()

    def _on_js_attach_file(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        _js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        dialog = Gtk.FileChooserDialog(
            title="Attach file",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.set_show_hidden(True)
        dialog.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Attach",
            Gtk.ResponseType.OK,
        )
        dialog.set_modal(True)
        if os.path.isdir(self._project_folder):
            dialog.set_current_folder(self._project_folder)

        image_filter = Gtk.FileFilter()
        image_filter.set_name("Images")
        for mime_type in ("image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"):
            image_filter.add_mime_type(mime_type)
        dialog.add_filter(image_filter)

        text_filter = Gtk.FileFilter()
        text_filter.set_name("Text files")
        for mime_type in (
            "text/plain",
            "text/markdown",
            "application/json",
            "application/x-yaml",
            "text/x-python",
            "text/x-shellscript",
        ):
            text_filter.add_mime_type(mime_type)
        for pattern in ("*.txt", "*.md", "*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml", "*.csv", "*.log"):
            text_filter.add_pattern(pattern)
        dialog.add_filter(text_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)

        response = dialog.run()
        selected = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()

        if not selected:
            return

        try:
            file_size = os.path.getsize(selected)
        except OSError as error:
            self._set_status_message(f"Could not read file: {error}", STATUS_WARNING)
            return

        if file_size > ATTACHMENT_MAX_BYTES:
            self._set_status_message("Attachment is too large", STATUS_WARNING)
            self._add_system_message("Attachment exceeds 12 MB limit.")
            return

        try:
            with open(selected, "rb") as handle:
                raw_bytes = handle.read()
        except OSError as error:
            self._set_status_message(f"Could not read file: {error}", STATUS_WARNING)
            return

        mime_type, _ = mimetypes.guess_type(selected)
        if not mime_type:
            mime_type = "application/octet-stream"
        payload = {
            "name": os.path.basename(selected),
            "path": selected,
            "type": mime_type,
            "data": f"data:{mime_type};base64,{base64.b64encode(raw_bytes).decode('ascii')}",
        }
        self._call_js("addHostAttachment", payload)

    def _on_js_stop_process(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        _js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        if self._claude_process.is_running():
            self._claude_process.stop()
            self._set_status_message("Process stopped by user", STATUS_WARNING)
            self._add_system_message(f"{self._active_provider.name} process stopped.")

    def _on_js_permission_response(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        raw_payload = self._extract_message_from_js_result(js_result)
        if not raw_payload:
            return

        try:
            parsed_payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return

        if not isinstance(parsed_payload, dict):
            return

        action = str(parsed_payload.get("action") or "").strip().lower()
        if action not in {"allow", "deny", "comment", "always_allow"}:
            return

        tool_name = str(parsed_payload.get("toolName") or "").strip()
        comment = str(parsed_payload.get("comment") or "")
        request_id = str(parsed_payload.get("requestId") or "")
        is_denial_card = bool(parsed_payload.get("isDenialCard"))

        if action == "always_allow" and tool_name:
            self._allowed_tools.add(tool_name)
            self._set_status_message(f"Always allowing {tool_name} for this session", STATUS_INFO)
            self._add_system_message(
                f"Tool '{tool_name}' has been added to the allowed list. "
                "It will be pre-approved on future requests in this session."
            )
            if not is_denial_card:
                self._claude_process.send_permission_response(
                    action="allow",
                    request_id=request_id,
                )
            return

        if is_denial_card:
            if action == "allow" and tool_name:
                self._allowed_tools.add(tool_name)
                self._set_status_message(
                    f"Tool '{tool_name}' allowed. Re-send your message to retry.", STATUS_INFO,
                )
                self._add_system_message(
                    f"Tool '{tool_name}' has been allowed. Please re-send your message "
                    f"so {self._active_provider.name} can use this tool."
                )
            elif action == "deny":
                self._set_status_message("Permission denied", STATUS_WARNING)
            return

        sent = self._claude_process.send_permission_response(
            action=action,
            comment=comment,
            request_id=request_id,
        )
        if not sent:
            self._set_status_message("Could not deliver permission response", STATUS_WARNING)
            self._add_system_message(
                f"Could not send permission response to {self._active_provider.name}."
            )
            return

        if action == "allow":
            self._set_status_message("Permission approved", STATUS_INFO)
        elif action == "deny":
            self._set_status_message("Permission denied", STATUS_WARNING)
        else:
            self._set_status_message("Permission comment sent", STATUS_INFO)

    def _on_js_send_message(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        self._set_active_pane(pane_id)
        raw_text = self._extract_message_from_js_result(js_result)
        message, attachments = parse_send_payload(raw_text)
        if not message and not attachments:
            return
        if message and self._handle_agent_command(pane_id, message):
            if attachments:
                self._set_status_message("Attachments are ignored for local /agent commands.", STATUS_MUTED)
            return

        if self._binary_path is None:
            self._refresh_connection_state()
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
            self._add_system_message(f"{self._provider_cli_label()} is not available.")
            return
        if self._active_provider_id == "codex" and not is_codex_authenticated():
            self._refresh_connection_state()
            self._set_status_message(
                "Codex login status could not be confirmed; sending anyway.",
                STATUS_WARNING,
            )

        if self._active_session_id is None:
            if os.path.isdir(self._project_folder):
                self._start_new_session(self._project_folder, reset_conversation=False)
            else:
                self._set_status_message("No active session", STATUS_ERROR)
                self._add_system_message("Create a session first.")
                return

        if self._claude_process.is_running():
            self._add_system_message(f"{self._active_provider.name} is still responding. Please wait.")
            return

        active_session = self._get_active_session()
        if active_session is None:
            self._set_status_message("No active session", STATUS_ERROR)
            self._add_system_message("No active session available.")
            return

        if not os.path.isdir(self._project_folder):
            self._set_status_message("Session folder not found", STATUS_ERROR)
            self._add_system_message("The selected project folder no longer exists.")
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        _, model_value = self._model_options[self._selected_model_index]
        _, permission_value, _ = self._permission_options[self._selected_permission_index]
        reasoning_value = self._reasoning_value_from_index(self._selected_reasoning_index)
        if not self._active_provider.supports_reasoning:
            reasoning_value = "medium"

        attachment_paths = materialize_attachments(attachments)
        composed_message = compose_message_with_attachments(message, attachment_paths)
        if not composed_message.strip():
            cleanup_temp_paths(attachment_paths)
            return

        if self._is_primary_pane(pane_id) and self._agentctl_auto_enabled:
            composed_message = f"{_AGENTCTL_HINT}\n\nUser request:\n{composed_message}"

        self._has_messages = True
        self._context_char_count += len(composed_message)
        self._update_context_indicator()

        # Create the assistant row immediately so users see true live streaming
        # instead of waiting for the first token to create the bubble.
        self._start_assistant_message()
        self._pulse_chat_shell()
        self._set_connection_state(CONNECTION_STARTING)
        self._set_status_message(f"Sending message to {self._active_provider.name}...", STATUS_INFO)
        active_caps = self._cli_caps_for(self._active_provider_id)

        active_session.status = SESSION_STATUS_ACTIVE
        active_session.last_used_at = current_timestamp()
        self._save_sessions_safe("Could not save sessions")
        self._refresh_session_list()

        self._add_to_history("user", composed_message)
        self._permission_request_pending = False

        request_token = str(uuid.uuid4())
        previous_request_token = self._active_request_token
        self._active_request_token = request_token
        config = ClaudeRunConfig(
            binary_path=self._binary_path,
            message=composed_message,
            cwd=self._project_folder,
            model=model_value,
            permission_mode=permission_value,
            conversation_id=self._conversation_id,
            supports_model_flag=active_caps.supports_model_flag,
            supports_permission_flag=active_caps.supports_permission_flag,
            supports_output_format_flag=active_caps.supports_output_format_flag,
            supports_stream_json=active_caps.supports_stream_json,
            supports_json=active_caps.supports_json,
            supports_include_partial_messages=active_caps.supports_include_partial_messages,
            stream_json_requires_verbose=self._stream_json_requires_verbose,
            reasoning_level=reasoning_value,
            supports_reasoning_flag=(active_caps.supports_reasoning_flag or self._active_provider_id == "codex")
            and self._active_provider.supports_reasoning,
            allowed_tools=list(self._allowed_tools) if self._allowed_tools else None,
            provider_id=self._active_provider_id,
        )
        started = self._claude_process.send_message(request_token=request_token, config=config)

        if not started:
            cleanup_temp_paths(attachment_paths)
            self._context_char_count = max(0, self._context_char_count - len(composed_message))
            self._update_context_indicator()
            self._active_request_token = previous_request_token
            self._finish_assistant_message()
            self._set_typing(False)
            self._refresh_connection_state()
            self._set_status_message("A request is already running", STATUS_WARNING)
            return

        self._request_temp_files[request_token] = attachment_paths

    @staticmethod
    def _extract_message_from_js_result(js_result: Any) -> str:
        try:
            raw_obj = js_result
            if hasattr(js_result, "get_js_value"):
                raw_obj = js_result.get_js_value()
            elif hasattr(js_result, "get_value"):
                raw_obj = js_result.get_value()

            if hasattr(raw_obj, "to_string"):
                raw = raw_obj.to_string()
            elif hasattr(raw_obj, "get_string"):
                raw = raw_obj.get_string()
            elif hasattr(raw_obj, "unpack"):
                raw = raw_obj.unpack()
            else:
                raw = raw_obj
        except Exception:
            logger.exception("Could not extract message payload from JavaScript result.")
            return ""

        if raw is None:
            return ""

        text = str(raw)
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            try:
                parsed = json.loads(text)
                if isinstance(parsed, str):
                    return parsed
            except json.JSONDecodeError:
                return text[1:-1]

        return text

    def _on_process_running_changed(self, pane_id: str, request_token: str, running: bool) -> None:
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return

            self._call_js("setProcessing", running)

            if running and self._is_active_pane(pane_id):
                self._set_connection_state(CONNECTION_STARTING)
                self._set_status_message(f"{self._active_provider.name} is responding...", STATUS_INFO)

    def _on_process_assistant_chunk(self, pane_id: str, request_token: str, chunk: str) -> None:
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return
            if not chunk:
                return
            self._set_typing(False)
            self._context_char_count += len(chunk)
            self._update_context_indicator()
            self._append_assistant_chunk(chunk)

    def _on_process_system_message(self, pane_id: str, request_token: str, message: str) -> None:
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return
            if not message:
                return
            self._add_system_message(message)
            if not self._permission_request_pending and self._is_permission_request_message(message):
                self._permission_request_pending = True
                self.send_notification(
                    f"{self._active_provider.name} needs permission",
                    "A tool permission request is waiting for your input.",
                    urgency="critical",
                )

    def _on_process_permission_request(
        self,
        pane_id: str,
        request_token: str,
        payload: dict[str, Any],
    ) -> None:
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return
            if not payload:
                return

            self._set_typing(False)
            self._call_js("addPermissionRequest", payload)
            if self._is_active_pane(pane_id):
                self._set_status_message("Waiting for tool confirmation", STATUS_WARNING)
            if not self._permission_request_pending:
                self._permission_request_pending = True
                self.send_notification(
                    f"{self._active_provider.name} needs permission",
                    "A tool permission request is waiting for your input.",
                    urgency="critical",
                )

    def _on_process_complete(self, pane_id: str, request_token: str, result: ClaudeRunResult) -> None:
        with self._pane_context(pane_id):
            temp_paths = self._request_temp_files.pop(request_token, [])
            cleanup_temp_paths(temp_paths)

            if not self._is_current_request(request_token):
                return

            self._invalidate_active_request()
            self._set_typing(False)
            assistant_output_text = str(self._active_assistant_message or "")
            had_assistant_output = bool(assistant_output_text.strip())
            self._finish_assistant_message()
            self._permission_request_pending = False

            if result.success and result.conversation_id:
                self._conversation_id = result.conversation_id
                active = self._get_active_session()
                if active is not None:
                    active.conversation_id = result.conversation_id

            if result.cost_usd > 0:
                self._session_cost_usd += result.cost_usd
            if result.input_tokens > 0 or result.output_tokens > 0:
                self._session_tokens += result.input_tokens + result.output_tokens
            self._update_usage_display()

            if result.success:
                self._last_request_failed = False
                if self._is_active_pane(pane_id):
                    self._refresh_connection_state()
                    self._set_status_message(f"{self._active_provider.name} response received", STATUS_MUTED)
                self._set_active_session_status(SESSION_STATUS_ACTIVE)
                self._save_sessions_safe("Could not save sessions")
                if had_assistant_output:
                    self._execute_agentctl_from_assistant(pane_id, assistant_output_text)
                if had_assistant_output:
                    self.send_notification(
                        f"{self._active_provider.name} response complete",
                        f"{self._active_provider.name} finished responding.",
                    )
                return

            error_message = result.error_message or f"{self._active_provider.name} request failed"
            self._last_request_failed = True
            if self._is_active_pane(pane_id):
                self._refresh_connection_state()
                self._set_status_message(error_message, STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            self._add_system_message(error_message)
            self.send_notification(f"{self._active_provider.name} error", error_message, urgency="critical")

    def _enqueue_javascript(self, script: str) -> None:
        if not script:
            return

        if self._webview_ready:
            self._run_javascript(script)
            return

        self._pending_webview_scripts.append(script)

    def _run_javascript(self, script: str) -> None:
        if self._webview is None:
            return

        if hasattr(self._webview, "evaluate_javascript"):
            self._webview.evaluate_javascript(script, -1, None, None, None, None, None)
            return

        try:
            self._webview.run_javascript(script, None, None, None)
            return
        except TypeError:
            logger.exception("WebView 4-arg run_javascript signature failed; retrying legacy signature.")

        try:
            self._webview.run_javascript(script, None, None)
            return
        except TypeError:
            logger.exception("WebView 3-arg run_javascript signature failed; retrying bare signature.")

        self._webview.run_javascript(script)

    def _call_js(self, function_name: str, *args: Any) -> None:
        if not re.fullmatch(r"[a-zA-Z0-9_.]+", function_name):
            raise ValueError(f"Invalid JavaScript function name: {function_name}")
        serialized = ", ".join(json.dumps(arg, ensure_ascii=False) for arg in args)
        if serialized:
            script = f"if (typeof {function_name} === 'function') {{ {function_name}({serialized}); }}"
        else:
            script = f"if (typeof {function_name} === 'function') {{ {function_name}(); }}"
        self._enqueue_javascript(script)

    def _call_js_in_pane(self, pane_id: str, function_name: str, *args: Any) -> bool:
        if pane_id not in self._pane_registry:
            return False
        with self._pane_context(pane_id):
            self._call_js(function_name, *args)
        return False

    def _start_assistant_message(self) -> None:
        self._active_assistant_message = ""
        self._call_js("startAssistantMessage")

    def _append_assistant_chunk(self, text: str) -> None:
        self._active_assistant_message += text
        self._call_js("appendAssistantChunk", text)

    def _finish_assistant_message(self) -> None:
        if self._active_assistant_message:
            self._add_to_history("assistant", self._active_assistant_message)
            self._save_sessions_safe("Could not save history")
            self._active_assistant_message = ""
        self._call_js("finishAssistantMessage")

    def _add_system_message(self, text: str) -> None:
        self._call_js("addSystemMessage", text)

    def _set_typing(self, value: bool) -> None:
        self._call_js("setTyping", value)

    def _clear_messages(self) -> None:
        self._has_messages = False
        self._context_char_count = 0
        self._update_context_indicator()
        self._call_js("clearMessages")

    def _show_welcome(self) -> None:
        self._call_js("showWelcome")

    def _on_destroy(self, _widget: Gtk.Window) -> None:
        for pane_id, pane in self._pane_registry.items():
            with self._pane_context(pane_id):
                if pane._claude_process is not None:
                    pane._claude_process.stop()
                for paths in pane._request_temp_files.values():
                    cleanup_temp_paths(paths)
                pane._request_temp_files.clear()

        if self._css_provider is not None:
            if GTK4:
                display = Gdk.Display.get_default()
                if display is not None:
                    Gtk.StyleContext.remove_provider_for_display(display, self._css_provider)
            else:
                screen = Gdk.Screen.get_default()
                if screen is not None:
                    Gtk.StyleContext.remove_provider_for_screen(screen, self._css_provider)
            self._css_provider = None

        for attr in (
            "_sidebar_animation_id",
            "_sidebar_toggle_pulse_animation_id",
            "_window_fade_animation_id",
            "_status_fade_animation_id",
            "_chat_reveal_animation_id",
            "_chat_pulse_animation_id",
            "_session_timer_id",
        ):
            self._cancel_timer(attr)

        Gtk.main_quit()
