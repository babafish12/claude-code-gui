"""Main application window with WebKit2 chat UI and session management."""

from __future__ import annotations

import ast
import base64
from contextlib import contextmanager
import copy
from types import SimpleNamespace
import json
import logging
import math
import mimetypes
import os
import re
import shlex
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_code_gui.gi_runtime import Adw, Gdk, Gio, GLib, Gtk, Pango, WebKit, GTK4

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
from claude_code_gui.domain.claude_types import ClaudeRunConfig, ClaudeRunResult
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
    MAX_ATTACHMENTS_PER_MESSAGE,
    MAX_ATTACHMENT_TOTAL_BYTES,
    cleanup_temp_paths,
    compose_message_with_attachments,
    materialize_attachments,
    parse_send_payload,
)
from claude_code_gui.services.binary_probe import (
    binary_exists,
    CliCapabilities,
    detect_cli_flag_support,
    find_provider_binary,
    detect_provider_model_options,
    get_cached_codex_authentication,
    refresh_codex_authentication_cache,
)
from claude_code_gui.storage.config_paths import RECENT_FOLDERS_LIMIT
from claude_code_gui.storage.recent_folders_store import (
    load_recent_folders,
    save_recent_folders,
)
from claude_code_gui.storage.sessions_store import load_sessions, save_sessions

from claude_code_gui.ui.window_js_handlers import (
    extract_action_from_js_result,
    extract_message_from_js_result,
    on_js_attach_file,
    on_js_permission_response,
    on_js_send_message,
)
from claude_code_gui.ui.window_settings_editor import open_settings_editor


logger = logging.getLogger(__name__)

_AGENTCTL_HINT = (
    "APP_CONTEXT: CLAUDE_CODE_GUI\n"
    "You are in claude-code-gui desktop with local pane orchestration.\n"
    "Critical rule: '/agent ...' commands are host-side app commands, NOT external tools.\n"
    "Only the main pane may orchestrate panes. Worker panes must never orchestrate.\n"
    "\n"
    "Execution protocol:\n"
    "1) For simple tasks: solve directly in main pane without /agent.\n"
    "2) For delegated work: either use one-shot '/agent <task>' or explicit '/agent new <name> -- <task>'.\n"
    "3) To delegate to existing workers use '/agent send <target> <task>'.\n"
    "4) Worker completion block is mandatory:\n"
    "   AGENT_STATUS: DONE | BLOCKED\n"
    "   AGENT_SUMMARY: <one short summary>\n"
    "   AGENT_FILES: <changed files or none>\n"
    "   AGENT_NEXT: <next step or none>\n"
    "5) App behavior: worker results are posted back to main chat; DONE workers auto-close.\n"
    "6) Never call external multi-agent/meta systems (omc team, spawn_agent, etc.).\n"
    "7) If orchestration is needed, output only plain '/agent ...' lines, one command per line, no markdown.\n"
    "\n"
    "Available commands: new [name] [-- prompt], list, focus <target>, send <target> <prompt>, "
    "summarize <target> <source1> <source2>..., close <target>."
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

_MAX_JS_OPTION_PAYLOAD_CHARS = 512
_MAX_JS_PERMISSION_PAYLOAD_CHARS = 64_000
_MAX_JS_SEND_PAYLOAD_CHARS = int((MAX_ATTACHMENT_TOTAL_BYTES * 4) / 3) + (MAX_ATTACHMENTS_PER_MESSAGE * 2048) + 256_000

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


def _resolve_app_icon_path() -> Path | None:
    """Resolve an application icon file, preferring user-provided root images."""
    cwd = Path.cwd()
    project_root = Path(__file__).resolve().parents[2]
    fixed_candidates = [
        cwd / "Gemini_Generated_Image_1vk3hx1vk3hx1vk3.png",
        project_root / "Gemini_Generated_Image_1vk3hx1vk3hx1vk3.png",
        cwd / "app-icon.png",
        project_root / "app-icon.png",
        cwd / "app_icon.png",
        project_root / "app_icon.png",
        cwd / "icon.png",
        project_root / "icon.png",
        _ICONS_DIR / "app-icon.png",
        _ICONS_DIR / "app_icon.png",
        _ICONS_DIR / "icon.png",
        _ICONS_DIR / "codex.webp",
    ]
    for candidate in fixed_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    for pattern in ("Gemini_Generated_Image*.png", "*app*icon*.png", "*icon*.png", "*logo*.png"):
        for base_dir in (cwd, project_root):
            matches = sorted(
                base_dir.glob(pattern),
                key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
                reverse=True,
            )
            for candidate in matches:
                if candidate.exists() and candidate.is_file():
                    return candidate
    return None


class PaneController:
    """Encapsulates one pane's WebView, process and request state."""

    def __init__(self, pane_id: str) -> None:
        self.pane_id = pane_id
        self._container: Gtk.Box | None = None
        self._header: Gtk.Box | None = None
        self._close_button: Gtk.Button | None = None
        self._title_label: Gtk.Label | None = None
        self._agent_status_label: Gtk.Label | None = None
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
        self._active_request_session_id: str | None = None
        self._active_assistant_message = ""
        self._pending_assistant_chunk_buffer = ""
        self._pending_assistant_chunk_flush_id: int | None = None
        self._request_temp_files: dict[str, list[str]] = {}
        self._permission_request_pending = False
        self._allowed_tools: set[str] = set()
        self._has_messages = False
        self._last_request_failed = False
        self._is_agent = False
        self._agent_name: str | None = None
        self._agent_status: str = ""
        self._typing_cleared_request_token: str | None = None


class ClaudeCodeWindow(Adw.ApplicationWindow if (Adw and GTK4) else Gtk.Window):
    """Single-window Claude Code shell with WebKit2 chat UI and session context."""

    def __init__(self, **kwargs) -> None:
        self._launcher_mode = kwargs.pop("launcher_mode", False)
        if "title" not in kwargs:
            kwargs["title"] = APP_NAME
        super().__init__(**kwargs)
        if self._launcher_mode:
            self.set_decorated(False)
            self.get_style_context().add_class("launcher-window")
        initial_settings = load_settings()
        preferred_provider = normalize_provider_id(str(initial_settings.get("active_provider_id") or DEFAULT_PROVIDER_ID))
        self._active_provider_id: str = preferred_provider
        self._provider_binaries: dict[str, str | None] = {
            provider_id: find_provider_binary(list(provider.binary_names))
            for provider_id, provider in PROVIDERS.items()
        }
        self._agentctl_auto_enabled = bool(initial_settings.get("agentctl_auto_enabled", True))
        self._system_tray_enabled = bool(initial_settings.get("system_tray_enabled", True))
        self._stream_render_throttle_ms = self._normalize_stream_render_throttle_ms(
            initial_settings.get("stream_render_throttle_ms", 80)
        )
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
        self._provider_button_row: Gtk.Box | None = None
        self._provider_buttons: dict[str, Gtk.Button] = {}
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
        self._context_indicator_throttle_id: int | None = None
        self._context_indicator_last_update_us = 0
        self._last_slash_commands_cache = ""
        self._slash_commands_cached_entries: list[dict[str, Any]] = []
        self._slash_commands_cache_signature: tuple[tuple[str, str, tuple[str, ...], int], ...] | None = None
        self._slash_commands_scan_inflight = False
        self._slash_commands_refresh_requested = False

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
        self._session_multi_select_toggle: Gtk.ToggleButton | None = None
        self._session_delete_selected_button: Gtk.Button | None = None
        self._session_multi_select_mode = False
        self._session_selected_ids: set[str] = set()
        self._skip_history_replay_for_panes: set[str] = set()
        self._session_filter_buttons: dict[str, Gtk.Button] = {}
        self._session_filter = "all"
        self._session_search_query = ""
        self._session_search_debounce_id: int | None = None
        self._window_has_focus = True
        self._notification_counter = 0
        self._app_icon_path: Path | None = _resolve_app_icon_path()
        self._tray_icon: Any = None
        self._tray_menu: Gtk.Menu | None = None
        self._tray_menu_model: Any = None
        self._tray_action_group: Any = None
        self._tray_backend = ""
        self._force_quit = False

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
        self._codex_auth_probe_inflight = False

        self._session_started_us = GLib.get_monotonic_time()
        self._session_timer_id: int | None = None
        self._sessions: list[SessionRecord] = []

        self._set_dark_theme_preference()
        self._apply_app_icon()
        self._bind_gtk_animation_setting()
        self._install_css()
        self._build_ui()
        self._install_drop_target()
        self._apply_provider_branding()
        self._load_sessions_into_state()
        self._refresh_session_list()
        self._update_provider_toggle_button()
        GLib.idle_add(self._refresh_session_list_idle)

        self.connect("destroy", self._on_destroy)
        self._connect_optional_signal(self, "delete-event", self._on_window_delete_event)
        self._connect_optional_signal(self, "close-request", self._on_window_close_request)
        if not self._connect_optional_signal(self, "map-event", self._on_map_event):
            GLib.idle_add(self._on_window_mapped_fallback)
        if not self._connect_optional_signal(self, "focus-in-event", self._on_window_focus_in):
            self.connect("notify::is-active", self._on_window_active_changed)
        self._connect_optional_signal(self, "focus-out-event", self._on_window_focus_out)
        if not self._connect_optional_signal(self, "key-press-event", self._on_window_key_press):
            self._install_window_key_controller()

        if self._active_session_id is None:
            self._set_status_message("New chat ready. Type a message to start a fresh session.", STATUS_INFO)
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

        self._setup_system_tray()
        self._start_status_fade_in()
        self._refresh_connection_state()

    def set_launcher_mode(self, enabled: bool) -> None:
        if self._launcher_mode == enabled:
            return
        self._launcher_mode = enabled
        self.set_decorated(not enabled)
        if enabled:
            self.get_style_context().add_class("launcher-window")
            if self._sidebar_container:
                self._sidebar_container.set_visible(False)
        else:
            self.get_style_context().remove_class("launcher-window")
            if self._sidebar_container:
                self._sidebar_container.set_visible(self._sidebar_expanded)

    def _install_drop_target(self) -> None:
        if not GTK4:
            return
        target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        target.connect("drop", self._on_drop)
        self.add_controller(target)

    def _on_drop(self, _target: Gtk.DropTarget, value: Gio.File, _x: float, _y: float) -> bool:
        if not value:
            return False
        path = value.get_path()
        if path:
            self._handle_external_file_attach(path)
            return True
        return False

    def _handle_external_file_attach(self, path: str) -> None:
        # Re-use existing attachment logic
        if self._active_pane_id:
            self._call_js_in_pane(self._active_pane_id, "externalFileDropped", path)

    @staticmethod
    def _set_dark_theme_preference() -> None:
        if Adw and GTK4:
            try:
                style_manager = Adw.StyleManager.get_default()
                if style_manager is not None and hasattr(style_manager, "set_color_scheme"):
                    color_scheme = getattr(Adw.ColorScheme, "PREFER_DARK", None)
                    if color_scheme is None:
                        color_scheme = getattr(Adw.ColorScheme, "FORCE_DARK", None)
                    if color_scheme is not None:
                        style_manager.set_color_scheme(color_scheme)
            except Exception:
                pass
            return

        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)

    def _apply_app_icon(self) -> None:
        icon_path = self._app_icon_path
        if icon_path is None:
            return
        icon_file = str(icon_path)

        try:
            if hasattr(self, "set_icon_from_file"):
                self.set_icon_from_file(icon_file)
        except Exception:
            logger.exception("Could not apply window icon from file: %s", icon_file)

        try:
            if hasattr(Gtk.Window, "set_default_icon_from_file"):
                Gtk.Window.set_default_icon_from_file(icon_file)
        except Exception:
            logger.exception("Could not apply default app icon from file: %s", icon_file)

    @staticmethod
    def _load_appindicator_module() -> Any | None:
        try:
            import gi  # pylint: disable=import-outside-toplevel
        except Exception:
            return None

        for module_name in (
            "AyatanaAppIndicator3",
            "AppIndicator3",
            "AyatanaAppIndicator",
            "AppIndicator",
        ):
            try:
                gi.require_version(module_name, "0.1")
                module = __import__(
                    "gi.repository",
                    fromlist=[module_name],
                )
                return getattr(module, module_name)
            except Exception as error:
                detail = str(error)
                if "Gtk" in detail and "3.0" in detail and "4.0" in detail:
                    logger.info(
                        "AppIndicator namespace '%s' requires GTK3 but GTK4 is already loaded.",
                        module_name,
                    )
                continue
        return None

    def _build_tray_menu(self) -> Gtk.Menu | None:
        if not hasattr(Gtk, "Menu") or not hasattr(Gtk, "MenuItem"):
            return None

        menu = Gtk.Menu()
        toggle_item = Gtk.MenuItem(label="Show / Hide")
        toggle_item.connect("activate", lambda *_args: self._on_tray_toggle_window())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda *_args: self._on_tray_quit())

        menu.append(toggle_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(quit_item)
        menu.show_all()
        return menu

    def _ensure_tray_action_group(self) -> bool:
        if self._tray_action_group is not None:
            return True
        if not hasattr(Gio, "SimpleActionGroup") or not hasattr(Gio, "SimpleAction"):
            return False
        if not hasattr(self, "insert_action_group"):
            return False
        try:
            action_group = Gio.SimpleActionGroup()
            toggle_action = Gio.SimpleAction.new("toggle", None)
            quit_action = Gio.SimpleAction.new("quit", None)
            toggle_action.connect("activate", lambda *_args: self._on_tray_toggle_window())
            quit_action.connect("activate", lambda *_args: self._on_tray_quit())
            action_group.add_action(toggle_action)
            action_group.add_action(quit_action)
            self.insert_action_group("tray", action_group)
        except Exception:
            logger.exception("Could not initialize tray action group.")
            return False
        self._tray_action_group = action_group
        return True

    def _build_tray_menu_model(self) -> Any | None:
        if not hasattr(Gio, "Menu"):
            return None
        if not self._ensure_tray_action_group():
            return None
        try:
            menu_model = Gio.Menu()
            menu_model.append("Show / Hide", "tray.toggle")
            menu_model.append("Quit", "tray.quit")
        except Exception:
            logger.exception("Could not build tray menu model.")
            return None
        return menu_model

    def _setup_system_tray(self) -> None:
        if not self._system_tray_enabled:
            self._teardown_system_tray()
            return
        if self._tray_icon is not None or self._app_icon_path is None:
            return

        if self._setup_system_tray_appindicator():
            return
        if self._setup_system_tray_status_icon():
            return
        logger.info("System tray is enabled, but no supported tray backend is available in this runtime.")

    def _setup_system_tray_appindicator(self) -> bool:
        app_indicator = self._load_appindicator_module()
        if app_indicator is None:
            return False

        tray_menu = self._build_tray_menu()
        tray_menu_model = self._build_tray_menu_model()

        icon_file = str(self._app_icon_path)
        icon_name = self._app_icon_path.name
        icon_theme_path = str(self._app_icon_path.parent)
        try:
            category = getattr(app_indicator.IndicatorCategory, "APPLICATION_STATUS", 0)
            indicator = app_indicator.Indicator.new(
                "claude-code-gui-tray",
                icon_name,
                category,
            )
            if hasattr(indicator, "set_title"):
                indicator.set_title(APP_NAME)
            if hasattr(indicator, "set_icon_theme_path"):
                indicator.set_icon_theme_path(icon_theme_path)
            if hasattr(indicator, "set_icon_full"):
                indicator.set_icon_full(icon_name, APP_NAME)
            elif hasattr(indicator, "set_icon"):
                indicator.set_icon(icon_name)
            elif hasattr(indicator, "set_icon_theme_path"):
                # Some indicator implementations require absolute path fallback.
                indicator.set_icon_theme_path(str(Path(icon_file).parent))
            if hasattr(indicator, "set_status") and hasattr(app_indicator, "IndicatorStatus"):
                indicator.set_status(app_indicator.IndicatorStatus.ACTIVE)
            has_menu_api = False
            if tray_menu is not None and hasattr(indicator, "set_menu"):
                indicator.set_menu(tray_menu)
                has_menu_api = True
            elif tray_menu_model is not None and hasattr(indicator, "set_menu_model"):
                indicator.set_menu_model(tray_menu_model)
                has_menu_api = True
            if not has_menu_api:
                logger.info("AppIndicator module found but no compatible tray menu API is available.")
                return False
        except Exception:
            logger.exception("Could not initialize system tray via AppIndicator.")
            return False

        self._tray_icon = indicator
        self._tray_menu = tray_menu
        self._tray_menu_model = tray_menu_model
        self._tray_backend = "appindicator"
        return True

    def _setup_system_tray_status_icon(self) -> bool:
        if GTK4 or not hasattr(Gtk, "StatusIcon"):
            return False

        if self._app_icon_path is None:
            return False

        tray_menu = self._build_tray_menu()
        if tray_menu is None:
            return False

        icon_file = str(self._app_icon_path)
        try:
            status_icon = Gtk.StatusIcon.new_from_file(icon_file)
            status_icon.set_visible(True)
            status_icon.set_tooltip_text(APP_NAME)
            status_icon.connect("activate", lambda *_args: self._on_tray_toggle_window())
            status_icon.connect("popup-menu", self._on_tray_popup_menu)
        except Exception:
            logger.exception("Could not initialize legacy Gtk.StatusIcon tray icon.")
            return False

        self._tray_icon = status_icon
        self._tray_menu = tray_menu
        self._tray_menu_model = None
        self._tray_backend = "statusicon"
        return True

    def _on_tray_popup_menu(self, _status_icon: Any, button: int, activate_time: int) -> None:
        if self._tray_menu is None:
            return
        try:
            self._tray_menu.popup(None, None, None, None, button, activate_time)
            return
        except Exception:
            pass

        try:
            self._tray_menu.popup_at_pointer(None)
        except Exception:
            logger.exception("Could not open system tray menu.")

    def _on_tray_toggle_window(self) -> None:
        if self.get_visible():
            self.hide()
            self._window_has_focus = False
            return

        if not GTK4:
            self.show_all()
            if hasattr(self, "deiconify"):
                self.deiconify()
        self.present()
        self._window_has_focus = True

    def _on_tray_quit(self) -> None:
        self._force_quit = True
        try:
            self.destroy()
        except Exception:
            Gtk.main_quit()

    def _teardown_system_tray(self) -> None:
        if self._tray_icon is not None:
            try:
                if self._tray_backend == "statusicon" and hasattr(self._tray_icon, "set_visible"):
                    self._tray_icon.set_visible(False)
                elif self._tray_backend == "appindicator" and hasattr(self._tray_icon, "set_status"):
                    app_indicator = self._load_appindicator_module()
                    if app_indicator is not None and hasattr(app_indicator, "IndicatorStatus"):
                        self._tray_icon.set_status(app_indicator.IndicatorStatus.PASSIVE)
            except Exception:
                logger.exception("Could not clean up system tray icon.")
        self._tray_icon = None
        self._tray_menu = None
        self._tray_menu_model = None
        self._tray_backend = ""
        if self._tray_action_group is not None and hasattr(self, "insert_action_group"):
            try:
                self.insert_action_group("tray", None)
            except Exception:
                logger.exception("Could not remove tray action group.")
            finally:
                self._tray_action_group = None

    def _on_window_delete_event(self, _widget: Gtk.Widget, _event: Any) -> bool:
        if self._force_quit or self._tray_icon is None:
            return False
        self.hide()
        self._window_has_focus = False
        return True

    def _on_window_close_request(self, _widget: Gtk.Widget, *_args: Any) -> bool:
        if self._force_quit or self._tray_icon is None:
            return False
        self.hide()
        self._window_has_focus = False
        return True

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
            elif provider_key == "gemini" and (
                icon_value_lower in {
                    "gemini",
                    "gemini.svg",
                    "gemini-color.svg",
                    "google-gemini.svg",
                }
                or icon_name.startswith("gemini")
            ):
                icon_value = "gemini-color.svg"

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
        elif provider_key == "gemini":
            icon_candidates.extend(
                [
                    Path("gemini-color.svg"),
                    Path("gemini.svg"),
                    Path("google-gemini.svg"),
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
        if provider_key == "gemini":
            for name in ("gemini-switch.svg", "gemini-color.svg", "gemini.svg", "google-gemini.svg"):
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
            # Do not fall back to active pane when a context pane was removed.
            # Falling back can route async callbacks into the wrong pane state.
            return self._pane_by_id(self._pane_context_id)
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
    def _active_request_session_id(self) -> str | None:
        pane = self._state_pane()
        return pane._active_request_session_id if pane is not None else None

    @_active_request_session_id.setter
    def _active_request_session_id(self, value: str | None) -> None:
        pane = self._state_pane()
        if pane is not None:
            pane._active_request_session_id = value

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

        if Adw and GTK4:
            header = Adw.HeaderBar()
            root.append(header)
            # Add a title widget
            title = Adw.WindowTitle(title=APP_NAME)
            header.set_title_widget(title)
        
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
        pane._header = header
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

        agent_status_label = Gtk.Label(label="")
        agent_status_label.set_xalign(0.5)
        agent_status_label.get_style_context().add_class("pane-agent-status")
        agent_status_label.set_visible(False)
        header.pack_start(agent_status_label, False, False, 0)
        pane._agent_status_label = agent_status_label

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
            "change_folder",
            "openFolder",
            "open_folder",
            "attachFile",
            "attach_file",
            "openFile",
            "open_file",
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
            "script-message-received::change_folder",
            lambda manager, result, pid=pane_id: self._on_js_change_folder(pid, manager, result),
        )
        manager.connect(
            "script-message-received::openFolder",
            lambda manager, result, pid=pane_id: self._on_js_change_folder(pid, manager, result),
        )
        manager.connect(
            "script-message-received::open_folder",
            lambda manager, result, pid=pane_id: self._on_js_change_folder(pid, manager, result),
        )
        manager.connect(
            "script-message-received::attachFile",
            lambda manager, result, pid=pane_id: self._on_js_attach_file(pid, manager, result),
        )
        manager.connect(
            "script-message-received::attach_file",
            lambda manager, result, pid=pane_id: self._on_js_attach_file(pid, manager, result),
        )
        manager.connect(
            "script-message-received::openFile",
            lambda manager, result, pid=pane_id: self._on_js_attach_file(pid, manager, result),
        )
        manager.connect(
            "script-message-received::open_file",
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

    def _activate_existing_pane(self, pane_id: str, *, grab_focus: bool = False) -> bool:
        if pane_id not in self._pane_registry:
            return False
        self._set_active_pane(pane_id, grab_focus=grab_focus)
        return True

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
        self._update_pane_status_badge(pane)

    def _update_pane_status_badge(self, pane: PaneController) -> None:
        status_label = pane._agent_status_label
        if status_label is None:
            return

        context = status_label.get_style_context()
        for class_name in (
            "pane-agent-status-working",
            "pane-agent-status-done",
            "pane-agent-status-blocked",
        ):
            context.remove_class(class_name)

        status = str(pane._agent_status or "").strip().lower()
        if (not pane._is_agent) or status not in {"working", "done", "blocked"}:
            status_label.set_text("")
            status_label.set_visible(False)
            return

        if status == "working":
            status_label.set_text("WORKING")
            context.add_class("pane-agent-status-working")
        elif status == "done":
            status_label.set_text("DONE")
            context.add_class("pane-agent-status-done")
        else:
            status_label.set_text("BLOCKED")
            context.add_class("pane-agent-status-blocked")
        status_label.set_visible(True)

    def _set_pane_agent_status(self, pane_id: str, status: str) -> None:
        pane = self._pane_by_id(pane_id)
        if pane is None:
            return
        normalized = str(status or "").strip().lower()
        if normalized not in {"working", "done", "blocked"}:
            normalized = ""
        if pane._agent_status == normalized:
            return
        pane._agent_status = normalized
        self._update_pane_header(pane_id)

    def _should_show_pane_headers(self) -> bool:
        if len(self._pane_registry) > 1:
            return True
        return any(pane._is_agent for pane in self._pane_registry.values())

    def _session_is_active_in_any_pane(self, session_id: str) -> bool:
        target = str(session_id or "").strip()
        if not target:
            return False
        for pane in self._pane_registry.values():
            if str(pane._active_session_id or "").strip() == target:
                return True
        return False

    def _session_is_working_in_any_pane(self, session_id: str) -> bool:
        target = str(session_id or "").strip()
        if not target:
            return False
        for pane in self._pane_registry.values():
            process = pane._claude_process
            if process is None or not process.is_running():
                continue
            if str(pane._active_request_session_id or "").strip() == target:
                return True
        return False

    def _session_status_dot_class(self, session: SessionRecord) -> str:
        if session.status == SESSION_STATUS_ARCHIVED:
            return "session-status-archived"
        if session.status == SESSION_STATUS_ERROR:
            return "session-status-error"
        if self._session_is_working_in_any_pane(session.id):
            return "session-status-active-working"
        if self._session_is_active_in_any_pane(session.id):
            return "session-status-active-done"
        return "session-status-inactive"

    @staticmethod
    def _extract_agent_status_marker(text: str) -> str:
        raw = str(text or "")
        if not raw:
            return ""

        status = ""
        for match in re.finditer(
            r"(?im)^\s*(?:[-*+]\s*)?agent_status\s*:\s*([^\n\r]+)\s*$",
            raw,
        ):
            value = str(match.group(1) or "").strip().lower()
            if not value:
                continue
            if "block" in value or "fail" in value or "error" in value:
                status = "blocked"
                continue
            if "work" in value or "running" in value or "progress" in value:
                status = "working"
                continue
            if "done" in value or "complete" in value or "success" in value or value == "ok":
                status = "done"
        return status

    @staticmethod
    def _extract_agent_summary_marker(text: str) -> str:
        raw = str(text or "")
        if not raw:
            return ""
        summary = ""
        for match in re.finditer(
            r"(?im)^\s*(?:[-*+]\s*)?agent_summary\s*:\s*([^\n\r]+)\s*$",
            raw,
        ):
            summary = str(match.group(1) or "").strip()
        return summary[:400]

    @staticmethod
    def _extract_agent_files_marker(text: str) -> str:
        raw = str(text or "")
        if not raw:
            return ""
        files = ""
        for match in re.finditer(
            r"(?im)^\s*(?:[-*+]\s*)?agent_files\s*:\s*([^\n\r]+)\s*$",
            raw,
        ):
            files = str(match.group(1) or "").strip()
        return files[:400]

    def _publish_agent_result_to_main_chat(
        self,
        *,
        agent_pane_id: str,
        status: str,
        assistant_text: str,
    ) -> None:
        primary = self._primary_pane_id()
        if not primary or primary == agent_pane_id:
            return

        normalized_status = str(status or "").strip().lower()
        if normalized_status not in {"done", "blocked", "working"}:
            normalized_status = "done"

        agent_name = self._pane_display_name(agent_pane_id)
        summary = self._extract_agent_summary_marker(assistant_text)
        files = self._extract_agent_files_marker(assistant_text)

        if not summary:
            compact = re.sub(r"\s+", " ", str(assistant_text or "")).strip()
            if compact:
                summary = compact[:220]
            else:
                summary = "No summary provided."

        payload = f"{agent_name} [{normalized_status.upper()}]: {summary}"
        if files and files.lower() not in {"none", "n/a", "-"}:
            payload += f" | Files: {files}"

        self._call_js_in_pane(primary, "addSystemMessage", payload)

    def _wake_main_after_agent_result(
        self,
        *,
        agent_pane_id: str,
        status: str,
        assistant_text: str,
    ) -> None:
        primary = self._primary_pane_id()
        if not primary or primary == agent_pane_id:
            return
        if not self._agentctl_auto_enabled:
            return

        primary_pane = self._pane_by_id(primary)
        if primary_pane is None:
            return
        with self._pane_context(primary):
            if self._claude_process.is_running():
                return

        normalized_status = str(status or "").strip().lower()
        if normalized_status not in {"done", "blocked", "working"}:
            normalized_status = "done"

        agent_name = self._pane_display_name(agent_pane_id)
        summary = self._extract_agent_summary_marker(assistant_text)
        files = self._extract_agent_files_marker(assistant_text)
        if not summary:
            compact = re.sub(r"\s+", " ", str(assistant_text or "")).strip()
            summary = compact[:320] if compact else "No summary provided."
        files_display = files if files and files.lower() not in {"none", "n/a", "-"} else "none"

        followup_prompt = (
            "Worker result received in claude-code-gui.\n"
            f"WORKER: {agent_name}\n"
            f"STATUS: {normalized_status.upper()}\n"
            f"SUMMARY: {summary}\n"
            f"FILES: {files_display}\n\n"
            "Continue the original main task now.\n"
            "First synthesize this worker result in the final answer.\n"
            "Do not create another worker for the same completed subtask unless the user explicitly requests it."
        )
        keep_focus = self._active_pane_id if self._active_pane_id in self._pane_registry else None
        if self._send_prompt_to_pane(primary, followup_prompt, keep_focus_on=keep_focus):
            self._set_status_message("Main pane resumed with latest agent result.", STATUS_MUTED)

    def _update_all_pane_headers(self) -> None:
        show_headers = self._should_show_pane_headers()
        for pane_id, pane in self._pane_registry.items():
            if pane._header is not None:
                pane._header.set_visible(show_headers)
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

    def _build_agentctl_hint(self, pane_id: str) -> str:
        primary = self._primary_pane_id() or "unknown"
        ordered = self._ordered_pane_ids() or list(self._pane_registry.keys())
        agent_names: list[str] = []
        for pid in ordered:
            if pid == primary:
                continue
            pane = self._pane_by_id(pid)
            if pane is None or not pane._is_agent:
                continue
            agent_names.append(self._pane_display_name(pid))
        agents_line = ", ".join(agent_names) if agent_names else "none"
        return (
            f"{_AGENTCTL_HINT}\n"
            f"MAIN_PANE_ID: {primary}\n"
            f"CURRENT_PANE_ID: {pane_id}\n"
            f"KNOWN_AGENT_PANES: {agents_line}"
        )

    @staticmethod
    def _split_name_and_prompt(args: list[str]) -> tuple[str, str]:
        if not args:
            return "", ""
        if "--" not in args:
            return " ".join(args).strip(), ""
        marker_index = args.index("--")
        name = " ".join(args[:marker_index]).strip()
        prompt = " ".join(args[marker_index + 1 :]).strip()
        return name, prompt

    def _build_worker_handoff_prompt(
        self,
        *,
        target_pane_id: str,
        prompt: str,
    ) -> str:
        pane = self._pane_by_id(target_pane_id)
        worker_name = self._pane_display_name(target_pane_id)
        if pane is not None and pane._is_agent and pane._agent_name:
            worker_name = pane._agent_name

        task_text = str(prompt or "").strip()
        return (
            "APP_CONTEXT: CLAUDE_CODE_GUI\n"
            f"You are {worker_name}, a worker agent.\n"
            "Important rules:\n"
            "- Do NOT orchestrate panes.\n"
            "- Never output or execute /agent, /pane, @agentctl, agentctl commands.\n"
            "- Never use external multi-agent/meta tools (e.g. omc team, spawn_agent).\n"
            "- Do only the delegated task below.\n"
            "- If information is missing, state exactly what is missing.\n"
            "- Do not create loops (no repeated 'checking status' narration).\n"
            "- Return exactly one final result block at the end.\n"
            "- Finish with these exact lines:\n"
            "AGENT_STATUS: DONE or BLOCKED\n"
            "AGENT_SUMMARY: <one concise summary>\n"
            "AGENT_FILES: <changed files or 'none'>\n"
            "AGENT_NEXT: <next step or 'none'>\n"
            "\n"
            "Delegated task:\n"
            f"{task_text}"
        )

    @staticmethod
    def _extract_agentctl_commands(assistant_text: str) -> list[str]:
        text = str(assistant_text or "")
        commands: list[str] = []
        seen: set[str] = set()

        for block_match in re.finditer(r"```(agentctl|agent)\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL):
            block_body = str(block_match.group(2) or "")
            for raw_line in block_body.splitlines():
                command = ClaudeCodeWindow._normalize_agentctl_line(raw_line, allow_prefixless=False)
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
        subcommand = tokens[1].lower()
        if subcommand in _AGENTCTL_COMMAND_KEYWORDS:
            if subcommand in {"send", "ask", "run"} and len(tokens) < 3:
                return None
            if subcommand in {"summarize", "summary", "merge"} and len(tokens) < 4:
                return None
            return command
        if tokens[0].lower() == "/agent":
            # One-shot shorthand: /agent <prompt>
            return command
        return None

    def _execute_agentctl_from_assistant(self, pane_id: str, assistant_text: str) -> int:
        if not self._is_primary_pane(pane_id):
            return 0

        commands = self._extract_agentctl_commands(assistant_text)
        if not commands:
            return 0

        executed = 0
        for command in commands[:12]:
            target_command = command if command.startswith("/agent") else f"/agent {command}"
            if self._handle_agent_command(pane_id, target_command, allow_non_primary=False):
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
            pane._agent_status = ""
            self._update_pane_header(primary)
            self._sync_pane_mode_to_webviews(pane_id=primary)
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
        known_subcommands = {
            "help",
            "h",
            "?",
            "new",
            "create",
            "add",
            "spawn",
            "list",
            "ls",
            "focus",
            "switch",
            "goto",
            "go",
            "send",
            "ask",
            "run",
            "summarize",
            "summary",
            "merge",
            "close",
            "kill",
            "remove",
        }
        if subcommand in {"help", "h", "?"}:
            self._add_system_message(
                "Agent commands:\n"
                "/agent <prompt> - create a worker and send prompt in one command\n"
                "/agent new [name] [-- prompt] - create agent (optional immediate prompt)\n"
                "/agent list - list panes and agents\n"
                "/agent focus <target> - focus pane (target: 1, pane-2, next, prev, Agent 1)\n"
                "/agent send <target> <prompt> - send prompt to pane without leaving main chat\n"
                "/agent summarize <target> <source...> - create summary from source agent outputs\n"
                "/agent close [target] - close pane (default: current)\n"
                "/agent help - show this help",
            )
            return True

        if subcommand in {"new", "create", "add", "spawn"}:
            custom_name, inline_prompt = self._split_name_and_prompt(tokens[2:])
            new_pane_id = self._create_agent_pane(name=custom_name or None)
            if new_pane_id and inline_prompt:
                delegated_prompt = self._build_worker_handoff_prompt(
                    target_pane_id=new_pane_id,
                    prompt=inline_prompt,
                )
                if self._send_prompt_to_pane(new_pane_id, delegated_prompt, keep_focus_on=pane_id):
                    self._set_pane_agent_status(new_pane_id, "working")
                    self._set_status_message(
                        f"Created {self._pane_display_name(new_pane_id)} and dispatched task.",
                        STATUS_INFO,
                    )
                else:
                    self._set_status_message(
                        f"Created {self._pane_display_name(new_pane_id)}, but prompt dispatch failed.",
                        STATUS_WARNING,
                    )
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
            prompt_to_send = prompt_text
            if not self._is_primary_pane(target_pane_id):
                prompt_to_send = self._build_worker_handoff_prompt(
                    target_pane_id=target_pane_id,
                    prompt=prompt_text,
                )
            if not self._send_prompt_to_pane(target_pane_id, prompt_to_send, keep_focus_on=pane_id):
                self._add_system_message("Could not dispatch prompt to target pane.")
                return True
            if not self._is_primary_pane(target_pane_id):
                self._set_pane_agent_status(target_pane_id, "working")
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

        if root == "/agent" and len(tokens) > 1 and subcommand not in known_subcommands:
            inline_prompt = " ".join(tokens[1:]).strip()
            if not inline_prompt:
                self._add_system_message("Usage: /agent <prompt>")
                return True
            new_pane_id = self._create_agent_pane()
            if new_pane_id is None:
                return True
            delegated_prompt = self._build_worker_handoff_prompt(
                target_pane_id=new_pane_id,
                prompt=inline_prompt,
            )
            if self._send_prompt_to_pane(new_pane_id, delegated_prompt, keep_focus_on=pane_id):
                self._set_pane_agent_status(new_pane_id, "working")
                self._set_status_message(
                    f"Created {self._pane_display_name(new_pane_id)} and dispatched task.",
                    STATUS_INFO,
                )
            else:
                self._set_status_message(
                    f"Created {self._pane_display_name(new_pane_id)}, but prompt dispatch failed.",
                    STATUS_WARNING,
                )
            return True

        self._add_system_message("Unknown /agent command. Use /agent help.")
        return True

    def _create_agent_pane(self, *, name: str | None = None) -> str | None:
        try:
            ordered = self._ordered_pane_ids() or list(self._pane_registry.keys())
            existing_agents: list[str] = []
            for pid in ordered:
                pane = self._pane_by_id(pid)
                if pane is None or not pane._is_agent:
                    continue
                existing_agents.append(pid)

            if existing_agents:
                orientation = Gtk.Orientation.VERTICAL
                split_target = (
                    self._active_pane_id
                    if self._active_pane_id in existing_agents
                    else existing_agents[-1]
                )
            else:
                orientation = Gtk.Orientation.HORIZONTAL
                split_target = self._primary_pane_id() or self._active_pane_id

            if split_target and split_target in self._pane_registry:
                self._set_active_pane(split_target)

            new_pane_id = self._split_active_pane(orientation)
            if new_pane_id is None:
                return None
            pane = self._pane_by_id(new_pane_id)
            if pane is None:
                return None
            pane._is_agent = True
            custom_name = str(name or "").strip()
            pane._agent_name = custom_name or self._next_agent_name()
            self._update_pane_header(new_pane_id)
            self._sync_pane_mode_to_webviews(pane_id=new_pane_id)
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

        primary = self._primary_pane_id()
        all_non_primary_are_agents = True
        for pane_id in ordered_ids:
            if pane_id == primary:
                continue
            pane = self._pane_by_id(pane_id)
            if pane is None or not pane._is_agent:
                all_non_primary_are_agents = False
                break

        root: Gtk.Widget | None = None
        if (
            primary is not None
            and primary in ordered_ids
            and len(ordered_ids) >= 2
            and all_non_primary_are_agents
        ):
            primary_pane = self._pane_by_id(primary)
            primary_view = primary_pane._container if primary_pane is not None else None
            if primary_view is not None:
                ordered_agents = [pane_id for pane_id in ordered_ids if pane_id != primary]
                agent_root: Gtk.Widget | None = None
                for pane_id in ordered_agents:
                    pane = self._pane_by_id(pane_id)
                    if pane is None or pane._container is None:
                        continue
                    if agent_root is None:
                        agent_root = pane._container
                        continue
                    vertical = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
                    vertical.set_wide_handle(True)
                    vertical.pack1(agent_root, True, False)
                    vertical.pack2(pane._container, True, False)
                    agent_root = vertical

                if agent_root is not None:
                    horizontal = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
                    horizontal.set_wide_handle(True)
                    horizontal.pack1(primary_view, True, False)
                    horizontal.pack2(agent_root, True, False)
                    root = horizontal

        if root is None:
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
            self._cancel_pending_assistant_chunk_flush(pane)
            pane._pending_assistant_chunk_buffer = ""
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

        if keyval == Gdk.KEY_Escape:
            self._on_cancel_request()
            return True

        if keyval == Gdk.KEY_Up:
            # We only want to trigger this if the input might be empty.
            # But the window doesn't know the input state.
            # We'll call a JS function that checks it.
            if self._active_pane_id:
                self._call_js_in_pane(self._active_pane_id, "handleWindowKeyUp")
            return False

        return False

    def _on_cancel_request(self) -> None:
        if self._active_pane_id:
            pane = self._pane_registry[self._active_pane_id]
            if pane._claude_process and pane._claude_process.is_running():
                pane._claude_process.stop()
                self._set_status_message("Request cancelled.", STATUS_INFO)

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

        settings_button = Gtk.Button(label="Settings")
        settings_button.set_relief(Gtk.ReliefStyle.NONE)
        settings_button.set_halign(Gtk.Align.START)
        settings_button.get_style_context().add_class("provider-switch-button")
        settings_button.set_tooltip_text("Open settings to edit theme colors, model options, and tray behavior.")
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

        provider_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        provider_row.get_style_context().add_class("provider-selector-row")
        provider_row.set_hexpand(True)
        self._provider_button_row = provider_row
        sidebar.pack_start(provider_row, False, False, 0)

        self._provider_buttons = {}
        for provider_id in self._provider_display_order():
            provider = PROVIDERS.get(provider_id)
            if provider is None:
                continue
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_halign(Gtk.Align.FILL)
            button.set_hexpand(True)
            button.get_style_context().add_class("provider-switch-button")
            button.get_style_context().add_class("provider-select-button")
            button._drag_blocker = True
            button.connect("clicked", self._on_provider_button_clicked, provider_id)

            button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            icon = Gtk.Image()
            icon.set_pixel_size(16)
            icon.get_style_context().add_class("provider-switch-icon")
            icon_path = self._provider_switch_icon_path(provider_id)
            if icon_path is not None:
                icon.set_from_file(str(icon_path))
            label = Gtk.Label(label=provider.name)
            label.set_xalign(0.0)
            button_box.pack_start(icon, False, False, 0)
            button_box.pack_start(label, False, False, 0)
            button.add(button_box)

            provider_row.pack_start(button, True, True, 0)
            self._provider_buttons[provider_id] = button

        sessions_title = Gtk.Label(label="Sessions (0)")
        sessions_title.set_xalign(0.0)
        sessions_title.get_style_context().add_class("sidebar-section-title")
        sidebar.pack_start(sessions_title, False, False, 0)
        self._sessions_title_label = sessions_title

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

        bulk_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bulk_row.get_style_context().add_class("session-filter-row")
        sidebar.pack_start(bulk_row, False, False, 0)

        multi_select_toggle = Gtk.ToggleButton(label="☑")
        multi_select_toggle.set_relief(Gtk.ReliefStyle.NONE)
        multi_select_toggle.get_style_context().add_class("session-filter-pill")
        multi_select_toggle.get_style_context().add_class("session-mark-toggle")
        multi_select_toggle.set_tooltip_text("Mehrere Sessions markieren")
        multi_select_toggle.connect("toggled", self._on_session_multi_select_toggled)
        bulk_row.pack_start(multi_select_toggle, False, False, 0)
        self._session_multi_select_toggle = multi_select_toggle

        delete_selected_button = Gtk.Button(label="Ausgewählte löschen")
        delete_selected_button.set_relief(Gtk.ReliefStyle.NONE)
        delete_selected_button.get_style_context().add_class("session-filter-pill")
        delete_selected_button.set_sensitive(False)
        delete_selected_button.set_visible(False)
        delete_selected_button.connect("clicked", self._on_delete_selected_sessions_clicked)
        bulk_row.pack_start(delete_selected_button, False, False, 0)
        self._session_delete_selected_button = delete_selected_button

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

        self._update_session_filter_buttons()
        self._sidebar_expanded_only_widgets = [
            provider_row,
            new_session_button,
            sessions_title,
            search_entry,
            session_scroll,
            bulk_row,
            filter_row,
        ]
        self._update_session_bulk_actions()
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
        if GTK4:
            key_controller = Gtk.EventControllerKey.new()
            if hasattr(key_controller, "set_propagation_phase") and hasattr(Gtk, "PropagationPhase"):
                key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

            def _on_key_pressed(
                _controller: Gtk.EventControllerKey,
                keyval: int,
                _keycode: int,
                state: Gdk.ModifierType,
            ) -> bool:
                return self._on_project_path_entry_key_press(
                    project_entry,
                    SimpleNamespace(keyval=keyval, state=state),
                )

            key_controller.connect("key-pressed", _on_key_pressed)
            project_entry.add_controller(key_controller)

            focus_controller = Gtk.EventControllerFocus.new()
            focus_controller.connect("enter", lambda _controller: self._on_project_path_entry_focus_in(project_entry, None))
            project_entry.add_controller(focus_controller)
        else:
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

        suggestion_scroll = Gtk.ScrolledWindow()
        suggestion_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        suggestion_scroll.set_shadow_type(Gtk.ShadowType.NONE)
        suggestion_scroll.set_size_request(300, 220)
        if hasattr(suggestion_scroll, "set_can_focus"):
            suggestion_scroll.set_can_focus(False)

        if GTK4:
            suggestion_popover = Gtk.Popover()
            suggestion_popover.set_parent(project_entry)
            if hasattr(suggestion_popover, "set_child"):
                suggestion_popover.set_child(suggestion_scroll)
            else:
                suggestion_popover.add(suggestion_scroll)
        else:
            suggestion_popover = Gtk.Popover.new(project_entry)
            if hasattr(suggestion_popover, "add"):
                suggestion_popover.add(suggestion_scroll)
            else:
                suggestion_popover.set_child(suggestion_scroll)
        suggestion_popover.set_position(Gtk.PositionType.BOTTOM)
        suggestion_popover.set_modal(False)
        if hasattr(suggestion_popover, "set_autohide"):
            suggestion_popover.set_autohide(False)
        if hasattr(suggestion_popover, "set_has_arrow"):
            suggestion_popover.set_has_arrow(False)
        suggestion_popover.get_style_context().add_class("path-suggestion-popover")

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
        if hasattr(suggestion_scroll, "set_child"):
            suggestion_scroll.set_child(suggestion_list)
        else:
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

    @staticmethod
    def _normalize_stream_render_throttle_ms(value: Any) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            numeric = 80
        return max(0, min(1500, numeric))

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
                self._call_js("addAssistantMessage", content)
            elif role == "system":
                self._call_js("addSystemMessage", content)

    def _replay_active_session_if_present(self) -> None:
        active_session = self._get_active_session()
        if active_session is None or not active_session.history:
            return
        self._conversation_id = active_session.conversation_id
        self._replay_history(active_session.history)

    def _add_to_history(self, role: str, content: str, *, session_id: str | None = None) -> None:
        if not content:
            return
        target = self._find_session(session_id) if session_id else self._get_active_session()
        if target is not None:
            target.history.append({"role": role, "content": content})
            if len(target.history) > 200:
                target.history = target.history[-200:]

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
            self._conversation_id = None
            self._set_status_message(f"Could not load sessions: {error}", STATUS_WARNING)
            return

        # Startup should always open in a fresh "new chat" state: no restored active session.
        self._active_session_id = None
        self._conversation_id = None

        changed = False
        for session in self._sessions:
            if session.status == SESSION_STATUS_ACTIVE:
                session.status = SESSION_STATUS_ENDED
                changed = True

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

    def _set_active_session_status(self, status: str, *, session_id: str | None = None) -> None:
        session = self._find_session(session_id) if session_id else self._get_active_session()
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

    def _update_session_bulk_actions(self) -> None:
        active_provider_session_ids = {
            session.id
            for session in self._sessions
            if session.provider == self._active_provider_id
        }
        self._session_selected_ids.intersection_update(active_provider_session_ids)

        selected_count = len(self._session_selected_ids)
        if self._session_multi_select_toggle is not None:
            if bool(self._session_multi_select_toggle.get_active()) != self._session_multi_select_mode:
                self._session_multi_select_toggle.set_active(self._session_multi_select_mode)
            context = self._session_multi_select_toggle.get_style_context()
            if self._session_multi_select_mode:
                context.add_class("session-filter-pill-active")
            else:
                context.remove_class("session-filter-pill-active")

        if self._session_delete_selected_button is not None:
            self._session_delete_selected_button.set_visible(self._session_multi_select_mode)
            if selected_count > 0:
                self._session_delete_selected_button.set_label(f"Löschen ({selected_count})")
            else:
                self._session_delete_selected_button.set_label("Ausgewählte löschen")
            self._session_delete_selected_button.set_sensitive(
                self._session_multi_select_mode and selected_count > 0
            )

    def _on_session_multi_select_toggled(self, toggle: Gtk.ToggleButton) -> None:
        self._session_multi_select_mode = bool(toggle.get_active())
        if not self._session_multi_select_mode:
            self._session_selected_ids.clear()
        self._update_session_bulk_actions()
        self._refresh_session_list()

    def _on_session_row_multi_select_toggled(self, session_id: str, enabled: bool) -> None:
        if enabled:
            self._session_selected_ids.add(session_id)
        else:
            self._session_selected_ids.discard(session_id)
        self._update_session_bulk_actions()

    def _delete_selected_sessions(self) -> None:
        selected_ids = [
            session_id
            for session_id in self._session_selected_ids
            if any(
                session.id == session_id and session.provider == self._active_provider_id
                for session in self._sessions
            )
        ]
        if not selected_ids:
            self._update_session_bulk_actions()
            return

        selected_set = set(selected_ids)
        deleted_count = len(selected_set)
        active_deleted = self._active_session_id in selected_set
        self._sessions = [session for session in self._sessions if session.id not in selected_set]
        self._session_selected_ids.difference_update(selected_set)
        replacement = self._promote_replacement_session() if active_deleted else None

        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        if active_deleted and replacement is not None:
            self._reset_conversation_state("Active session deleted")
            self._refresh_connection_state()
            self._set_status_message(
                f"{deleted_count} sessions deleted. Switched to replacement.",
                STATUS_INFO,
            )
        elif active_deleted and replacement is None:
            self._reset_conversation_state("Session deleted", reset_timer=False)
            self._refresh_connection_state()
            self._set_status_message(f"{deleted_count} sessions deleted.", STATUS_MUTED)
        else:
            self._set_status_message(f"{deleted_count} sessions deleted.", STATUS_MUTED)

        self._update_session_bulk_actions()

    def _on_delete_selected_sessions_clicked(self, _button: Gtk.Button) -> None:
        if not self._session_multi_select_mode:
            return
        self._delete_selected_sessions()

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
        self._cancel_timer("_session_search_debounce_id")
        self._session_search_debounce_id = GLib.timeout_add(150, self._refresh_session_search_debounced)

    def _refresh_session_search_debounced(self) -> bool:
        self._session_search_debounce_id = None
        self._refresh_session_list()
        return False

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

    def _slash_command_roots(self) -> tuple[list[tuple[Path, tuple[str, ...]]], list[tuple[Path, tuple[str, ...]]]]:
        project_root = Path(self._project_folder)
        codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser()
        all_provider_ids: tuple[str, ...] = tuple(PROVIDERS.keys()) or (DEFAULT_PROVIDER_ID,)
        command_roots: list[tuple[Path, tuple[str, ...]]] = [
            (project_root / ".claude" / "commands", ("claude",)),
            (Path.home() / ".claude" / "commands", ("claude",)),
            (project_root / ".codex" / "commands", ("codex",)),
            (codex_home / "commands", ("codex",)),
            (project_root / ".gemini" / "commands", ("gemini",)),
            (Path.home() / ".gemini" / "commands", ("gemini",)),
            (project_root / ".agents" / "commands", all_provider_ids),
            (Path.home() / ".agents" / "commands", all_provider_ids),
        ]
        skill_roots: list[tuple[Path, tuple[str, ...]]] = [
            (project_root / ".agents" / "skills", all_provider_ids),
            (Path.home() / ".agents" / "skills", all_provider_ids),
            (project_root / ".codex" / "skills", ("codex",)),
            (codex_home / "skills", ("codex",)),
            (project_root / ".gemini" / "skills", ("gemini",)),
            (Path.home() / ".gemini" / "skills", ("gemini",)),
            (project_root / ".claude" / "skills", ("claude",)),
            (Path.home() / ".claude" / "skills", ("claude",)),
        ]
        return command_roots, skill_roots

    @staticmethod
    def _slash_roots_signature(
        command_roots: list[tuple[Path, tuple[str, ...]]],
        skill_roots: list[tuple[Path, tuple[str, ...]]],
    ) -> tuple[tuple[str, str, tuple[str, ...], int], ...]:
        signature: list[tuple[str, str, tuple[str, ...], int]] = []

        def root_mtime_ns(root: Path) -> int:
            try:
                return root.stat().st_mtime_ns if root.is_dir() else -1
            except OSError:
                return -1

        for root, providers in command_roots:
            signature.append(("commands", str(root), tuple(providers), root_mtime_ns(root)))
        for root, providers in skill_roots:
            signature.append(("skills", str(root), tuple(providers), root_mtime_ns(root)))
        return tuple(signature)

    @classmethod
    def _discover_custom_slash_commands_from_roots(
        cls,
        command_roots: list[tuple[Path, tuple[str, ...]]],
        skill_roots: list[tuple[Path, tuple[str, ...]]],
    ) -> list[dict[str, Any]]:
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
            safe_name = cls._safe_slash_name(name)
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
                "description": cls._truncate_text(description, 96),
                "providers": provider_list,
            }
            commands_by_key[key] = payload
            commands.append(payload)

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
                summary = cls._read_markdown_summary(command_file) or "Custom slash command"
                add_command(slash_name, "C", f"Custom command: {summary}", providers)

        skill_doc_names = ("SKILL.md", "skill.md", "skill.markdown")
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
                summary = cls._read_markdown_summary(skill_doc) or "Custom skill"
                add_command(skill_dir.name, "S", f"Custom skill: {summary}", providers)

        return commands

    def _publish_slash_commands(self, commands: list[dict[str, Any]]) -> None:
        payload = json.dumps(commands, ensure_ascii=False, sort_keys=True)
        if payload == self._last_slash_commands_cache:
            return
        self._last_slash_commands_cache = payload
        self._call_js("updateSlashCommands", commands)

    def _apply_discovered_slash_commands(
        self,
        signature: tuple[tuple[str, str, tuple[str, ...], int], ...],
        commands: list[dict[str, Any]],
    ) -> bool:
        self._slash_commands_scan_inflight = False
        self._slash_commands_cache_signature = signature
        self._slash_commands_cached_entries = list(commands)
        self._publish_slash_commands(commands)
        if self._slash_commands_refresh_requested:
            self._slash_commands_refresh_requested = False
            self._refresh_slash_commands()
        return False

    def _refresh_slash_commands(self) -> None:
        command_roots, skill_roots = self._slash_command_roots()
        signature = self._slash_roots_signature(command_roots, skill_roots)
        if signature == self._slash_commands_cache_signature:
            self._publish_slash_commands(self._slash_commands_cached_entries)
            return
        if self._slash_commands_scan_inflight:
            self._slash_commands_refresh_requested = True
            return

        self._slash_commands_scan_inflight = True
        self._slash_commands_refresh_requested = False

        import threading

        def _scan() -> None:
            discovered = self._discover_custom_slash_commands_from_roots(command_roots, skill_roots)
            GLib.idle_add(self._apply_discovered_slash_commands, signature, discovered)

        threading.Thread(target=_scan, daemon=True).start()

    def _make_session_row(self, session: SessionRecord, allow_open: bool) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        row.get_style_context().add_class("session-row")
        if session.id == self._active_session_id:
            row.get_style_context().add_class("session-row-active")

        select_checkbox = Gtk.CheckButton()
        select_checkbox.get_style_context().add_class("session-select-checkbox")
        select_checkbox.set_visible(self._session_multi_select_mode)
        select_checkbox.set_active(session.id in self._session_selected_ids)
        select_checkbox.connect(
            "toggled",
            lambda button, sid=session.id: self._on_session_row_multi_select_toggled(
                sid,
                bool(button.get_active()),
            ),
        )
        row.pack_start(select_checkbox, False, False, 0)

        open_button = Gtk.Button()
        open_button.set_relief(Gtk.ReliefStyle.NONE)
        open_button.get_style_context().add_class("session-open-button")
        open_button._drag_blocker = True
        open_button.set_hexpand(True)
        open_button.set_halign(Gtk.Align.FILL)
        open_button.set_sensitive(allow_open and not self._session_multi_select_mode)
        open_button.connect("clicked", lambda _button, sid=session.id: self._switch_to_session(sid))

        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        status_dot = Gtk.Box()
        status_dot.set_size_request(8, 8)
        status_dot.get_style_context().add_class("session-status-dot")
        status_dot.get_style_context().add_class(self._session_status_dot_class(session))
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
        if not self._session_multi_select_mode:
            self._session_selected_ids.clear()
        else:
            provider_session_ids = {session.id for session in provider_sessions}
            self._session_selected_ids.intersection_update(provider_session_ids)
        self._update_session_bulk_actions()
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
            self._update_session_bulk_actions()
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
        self._update_session_bulk_actions()
        self._update_all_pane_headers()

    def _refresh_session_list_idle(self) -> bool:
        self._refresh_session_list()
        return False

    def _is_request_bound_to_session(self, session_id: str | None) -> bool:
        target = str(session_id or "").strip()
        if not target:
            return False
        if not self._active_request_token:
            return False
        if str(self._active_request_session_id or "").strip() != target:
            return False
        return self._claude_process.is_running()

    def _render_active_session_view(self) -> None:
        session = self._get_active_session()
        self._clear_messages()
        if session is not None and session.history:
            self._replay_history(session.history)

        running_for_active_session = session is not None and self._is_request_bound_to_session(session.id)
        self._call_js("setProcessing", running_for_active_session)
        if running_for_active_session:
            if self._active_assistant_message:
                self._call_js("startAssistantMessage")
                self._call_js("appendAssistantChunk", self._active_assistant_message)
            else:
                self._set_typing(True)
        else:
            self._set_typing(False)

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
        request_running = bool(self._active_request_token) and self._claude_process.is_running()
        background_request_on_current = (
            request_running
            and current is not None
            and str(self._active_request_session_id or "").strip() == current.id
            and current.id != session.id
        )
        if current is not None and current.id != session.id and current.status != SESSION_STATUS_ARCHIVED:
            current.status = SESSION_STATUS_ACTIVE if background_request_on_current else SESSION_STATUS_ENDED

        self._active_session_id = session.id
        session.status = SESSION_STATUS_ACTIVE
        self._apply_session_to_controls(session, add_to_recent=os.path.isdir(session.project_path))
        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        self._conversation_id = session.conversation_id
        self._allowed_tools = set()
        self._permission_request_pending = False
        self._last_request_failed = False
        self._render_active_session_view()

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        self._refresh_connection_state()
        msg_count = len(session.history) if session.history else 0
        if background_request_on_current:
            self._set_status_message("Session switched. Previous chat continues in background.", STATUS_INFO)
            return
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
        self._set_project_path_entry_caret(len(text_value))
        self._suppress_project_entry_change = False

    @staticmethod
    def _extract_entry_selection(entry: Gtk.Entry) -> tuple[int, int] | None:
        try:
            selection = entry.get_selection_bounds()
        except Exception:
            return None

        if isinstance(selection, tuple):
            if len(selection) == 3 and isinstance(selection[0], bool):
                has_selection, start, end = selection
                if not has_selection:
                    return None
            elif len(selection) == 2:
                start, end = selection
            else:
                return None
        elif isinstance(selection, list):
            if len(selection) == 2:
                start, end = selection
            else:
                return None
        else:
            return None

        if not isinstance(start, int) or not isinstance(end, int):
            try:
                start = int(start)
                end = int(end)
            except (TypeError, ValueError):
                return None

        return (start, end)

    def _set_project_path_entry_caret(self, position: int) -> None:
        if self._project_path_entry is None:
            return

        text_length = len(self._project_path_entry.get_text())
        safe_position = max(0, min(text_length, position))
        if hasattr(self._project_path_entry, "select_region"):
            self._project_path_entry.select_region(safe_position, safe_position)
        if hasattr(self._project_path_entry, "set_position"):
            self._project_path_entry.set_position(safe_position)

    def _defer_project_path_entry_caret(self, position: int) -> None:
        GLib.idle_add(
            lambda: (
                self._set_project_path_entry_caret(position),
                False,
            )[1]
        )

    @staticmethod
    def _run_dialog(dialog: Gtk.Dialog) -> int:
        if hasattr(dialog, "run"):
            try:
                return int(dialog.run())
            except Exception:
                pass

        response_holder = {"value": Gtk.ResponseType.CANCEL}
        loop = GLib.MainLoop()

        def _on_response(_dialog: Gtk.Dialog, response_id: int) -> None:
            response_holder["value"] = int(response_id)
            if loop.is_running():
                loop.quit()

        if hasattr(dialog, "connect"):
            try:
                dialog.connect("response", _on_response)
            except Exception:
                pass

        if hasattr(dialog, "present"):
            dialog.present()
        elif hasattr(dialog, "show"):
            dialog.show()
        elif hasattr(dialog, "show_all"):
            dialog.show_all()

        loop.run()
        return response_holder["value"]

    @staticmethod
    def _is_dialog_accept_response(response: int) -> bool:
        return response in {
            int(Gtk.ResponseType.OK),
            int(Gtk.ResponseType.ACCEPT),
            int(Gtk.ResponseType.YES),
            int(Gtk.ResponseType.APPLY),
        }

    @staticmethod
    def _run_native_chooser(chooser: Any) -> int:
        response_holder = {"value": Gtk.ResponseType.CANCEL}
        loop = GLib.MainLoop()

        def _on_response(_chooser: Any, response_id: int) -> None:
            response_holder["value"] = int(response_id)
            if loop.is_running():
                loop.quit()

        if hasattr(chooser, "connect"):
            try:
                chooser.connect("response", _on_response)
            except Exception:
                pass

        if hasattr(chooser, "show"):
            chooser.show()
        elif hasattr(chooser, "present"):
            chooser.present()

        loop.run()
        return int(response_holder["value"])

    @staticmethod
    def _extract_selected_paths_from_chooser(chooser: Any) -> list[str]:
        selected_paths: list[str] = []

        if hasattr(chooser, "get_filenames"):
            try:
                values = chooser.get_filenames() or []
            except Exception:
                values = []
            for item in values:
                if isinstance(item, str) and item:
                    selected_paths.append(item)

        if hasattr(chooser, "get_files"):
            try:
                files_obj = chooser.get_files()
            except Exception:
                files_obj = None

            if hasattr(files_obj, "get_n_items") and hasattr(files_obj, "get_item"):
                try:
                    count = int(files_obj.get_n_items())
                except Exception:
                    count = 0
                for index in range(max(0, count)):
                    file_obj = files_obj.get_item(index)
                    if isinstance(file_obj, Gio.File):
                        selected_path = file_obj.get_path()
                        if selected_path:
                            selected_paths.append(selected_path)
            elif isinstance(files_obj, (list, tuple)):
                for file_obj in files_obj:
                    if isinstance(file_obj, Gio.File):
                        selected_path = file_obj.get_path()
                        if selected_path:
                            selected_paths.append(selected_path)
            elif files_obj is not None:
                try:
                    for file_obj in files_obj:
                        if isinstance(file_obj, Gio.File):
                            selected_path = file_obj.get_path()
                            if selected_path:
                                selected_paths.append(selected_path)
                except Exception:
                    pass

        if not selected_paths and hasattr(chooser, "get_file"):
            try:
                selected_file = chooser.get_file()
            except Exception:
                selected_file = None
            if isinstance(selected_file, Gio.File):
                selected_path = selected_file.get_path()
                if selected_path:
                    selected_paths.append(selected_path)

        deduped: list[str] = []
        seen: set[str] = set()
        for path in selected_paths:
            if not path or path in seen:
                continue
            seen.add(path)
            deduped.append(path)
        return deduped

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
            if hasattr(self._project_path_popover, "popup"):
                self._project_path_popover.popup()
            elif hasattr(self._project_path_popover, "present"):
                self._project_path_popover.present()
            else:
                self._project_path_popover.set_visible(True)
        except Exception:
            self._project_path_popover.set_visible(True)
        # Keep typing in the path entry without forcing focus repeatedly during input.
        try:
            has_focus = bool(self._project_path_entry.get_property("has-focus"))
        except Exception:
            has_focus = False
        if not has_focus:
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
            self._set_project_path_entry_caret(len(suggestion))
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
        selection = self._extract_entry_selection(_entry)
        if selection is not None:
            start, end = selection
            text = _entry.get_text()
            if start == 0 and end == len(text):
                keyval = int(getattr(event, "keyval", 0) or 0)
                navigation_keys = {
                    int(Gdk.KEY_BackSpace),
                    int(Gdk.KEY_Delete),
                    int(Gdk.KEY_Tab),
                    int(Gdk.KEY_ISO_Left_Tab),
                    int(Gdk.KEY_Down),
                    int(Gdk.KEY_Up),
                    int(Gdk.KEY_Escape),
                    int(Gdk.KEY_Return),
                    int(Gdk.KEY_KP_Enter),
                    int(Gdk.KEY_Left),
                    int(Gdk.KEY_Right),
                    int(Gdk.KEY_Home),
                    int(Gdk.KEY_End),
                }
                state_bits = int(getattr(event, "state", 0) or 0)
                ctrl_mask = int(getattr(Gdk.ModifierType, "CONTROL_MASK", 0))
                alt_mask = int(getattr(Gdk.ModifierType, "MOD1_MASK", 0))
                super_mask = int(getattr(Gdk.ModifierType, "SUPER_MASK", 0))
                has_modifier = bool(state_bits & (ctrl_mask | alt_mask | super_mask))
                if keyval not in navigation_keys and not has_modifier:
                    self._set_project_path_entry_caret(len(text))

        if event.keyval in (Gdk.KEY_BackSpace, Gdk.KEY_Delete):
            if selection is None:
                return False

            start, end = selection
            if start == 0 and end == len(text):
                if event.keyval == Gdk.KEY_BackSpace and text:
                    # Consume this key directly to avoid deleting the full selection.
                    _entry.delete_text(len(text) - 1, len(text))
                    return True
                if event.keyval == Gdk.KEY_Delete and text:
                    _entry.delete_text(0, 1)
                    return True

                return False
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
        entry_text = _entry.get_text()
        self._defer_project_path_entry_caret(len(entry_text))
        return False

    def _on_project_path_entry_has_focus_changed(self, entry: Gtk.Entry, _param: Any) -> None:
        try:
            has_focus = bool(entry.get_property("has-focus"))
        except Exception:
            has_focus = False
        if has_focus:
            self._refresh_project_path_suggestions(show_popover=True)
            self._defer_project_path_entry_caret(len(entry.get_text()))
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

    def _flush_context_indicator_update(self) -> bool:
        self._context_indicator_throttle_id = None
        self._context_indicator_last_update_us = GLib.get_monotonic_time()
        self._update_context_indicator()
        return False

    def _queue_context_indicator_update(self, *, immediate: bool = False) -> None:
        if immediate:
            self._cancel_timer("_context_indicator_throttle_id")
            self._context_indicator_last_update_us = GLib.get_monotonic_time()
            self._update_context_indicator()
            return

        if self._context_indicator_throttle_id is not None:
            return

        now_us = GLib.get_monotonic_time()
        if self._context_indicator_last_update_us <= 0:
            elapsed_ms = 1_000_000
        else:
            elapsed_ms = int((now_us - self._context_indicator_last_update_us) / 1000)
        if elapsed_ms >= 250:
            self._context_indicator_last_update_us = now_us
            self._update_context_indicator()
            return

        delay_ms = max(1, 250 - max(0, elapsed_ms))
        self._context_indicator_throttle_id = GLib.timeout_add(delay_ms, self._flush_context_indicator_update)

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
        if self._active_provider_id == "codex":
            auth_state, is_fresh = get_cached_codex_authentication(max_age_seconds=30.0)
            if not is_fresh:
                self._refresh_codex_auth_async()
            if auth_state is not True:
                self._set_connection_state(CONNECTION_DISCONNECTED)
                return
        self._set_connection_state(CONNECTION_CONNECTED)

    def _set_status_message(self, message: str, severity: str = STATUS_MUTED) -> None:
        self._last_status_message = message
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

    def _refresh_codex_auth_async(self, *, force: bool = False) -> None:
        if self._codex_auth_probe_inflight and not force:
            return
        self._codex_auth_probe_inflight = True

        import threading

        def _probe() -> None:
            authenticated = refresh_codex_authentication_cache()
            GLib.idle_add(self._apply_codex_auth_probe_result, authenticated)

        threading.Thread(target=_probe, daemon=True).start()

    def _apply_codex_auth_probe_result(self, _authenticated: bool) -> bool:
        self._codex_auth_probe_inflight = False
        if self._active_provider_id == "codex":
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
        self._run_dialog(dialog)
        dialog.destroy()

    def _invalidate_active_request(self) -> None:
        self._active_request_token = None
        self._active_request_session_id = None

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
        self._set_project_path_entry_caret(len(self._project_path_entry.get_text()))
        self._refresh_project_path_suggestions(show_popover=True)
        self._set_status_message("Type a project folder path and press Enter", STATUS_INFO)

    def _choose_project_folder_with_dialog(self) -> str | None:
        current_folder = str(Path.home())
        if os.path.isdir(self._project_folder):
            current_folder = self._project_folder

        if GTK4 and hasattr(Gtk, "FileChooserNative"):
            chooser = Gtk.FileChooserNative.new(
                "Choose project folder",
                self,
                Gtk.FileChooserAction.SELECT_FOLDER,
                "Select",
                "Cancel",
            )
            chooser.set_modal(True)
            try:
                chooser.set_current_folder(Gio.File.new_for_path(current_folder))
            except Exception:
                pass

            try:
                response = self._run_native_chooser(chooser)
                if not self._is_dialog_accept_response(response):
                    return None
                selected_paths = self._extract_selected_paths_from_chooser(chooser)
                selected = selected_paths[0] if selected_paths else None
            finally:
                chooser.destroy()
        else:
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
            try:
                dialog.set_current_folder(current_folder)
            except Exception:
                pass

            try:
                response = self._run_dialog(dialog)
                if not self._is_dialog_accept_response(response):
                    return None
                selected_paths = self._extract_selected_paths_from_chooser(dialog)
                selected = selected_paths[0] if selected_paths else None
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
        js_result: WebKit.JavascriptResult,
    ) -> None:
        if not self._activate_existing_pane(pane_id):
            return

        raw_payload = self._extract_message_from_js_result(
            js_result,
            max_chars=_MAX_JS_OPTION_PAYLOAD_CHARS,
        )
        direct_path = ""
        try:
            parsed_payload = json.loads(raw_payload) if raw_payload else None
        except json.JSONDecodeError:
            try:
                parsed_payload = ast.literal_eval(raw_payload) if raw_payload else None
            except (SyntaxError, ValueError):
                parsed_payload = None
        if isinstance(parsed_payload, dict):
            direct_path = str(
                parsed_payload.get("path")
                or parsed_payload.get("folder")
                or parsed_payload.get("directory")
                or ""
            ).strip()

        if direct_path:
            expanded = os.path.expanduser(direct_path)
            if not os.path.isabs(expanded):
                expanded = os.path.abspath(expanded)
            if os.path.isdir(expanded):
                selected = normalize_folder(expanded)
                self._set_project_path_entry_text(selected)
                self._set_project_folder(selected, restart_session=self._active_session_id is not None)
                return

        action = self._extract_action_from_js_result(
            js_result,
            allowed_actions={
                "change",
                "open",
                "browse",
                "select",
                "folder",
                "changefolder",
                "change_folder",
                "openfolder",
                "open_folder",
            },
        )
        normalized_payload = raw_payload.strip().lower()
        if action is None and normalized_payload in {"", "null", "none", "undefined"}:
            action = "change"
        if action is None:
            return
        self._set_status_message("Opening folder chooser...", STATUS_INFO)
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

    def _persist_active_provider_preference(self) -> None:
        try:
            settings_payload = load_settings()
            settings_payload["active_provider_id"] = self._active_provider_id
            save_settings(settings_payload)
        except Exception as error:
            logger.exception("Could not persist active provider preference")
            self._set_status_message(
                f"Could not save active provider preference: {error}",
                STATUS_WARNING,
            )

    def _sync_agent_mode_to_webviews(self, *, pane_id: str | None = None) -> None:
        target_panes = [pane_id] if pane_id is not None else list(self._pane_registry.keys())
        for target in target_panes:
            if target not in self._pane_registry:
                continue
            with self._pane_context(target):
                self._call_js("setAgentModeEnabled", self._agentctl_auto_enabled)

    def _sync_stream_render_throttle_to_webviews(self, *, pane_id: str | None = None) -> None:
        target_panes = [pane_id] if pane_id is not None else list(self._pane_registry.keys())
        for target in target_panes:
            if target not in self._pane_registry:
                continue
            with self._pane_context(target):
                self._call_js("setStreamRenderThrottleMs", self._stream_render_throttle_ms)

    def _sync_pane_mode_to_webviews(self, *, pane_id: str | None = None) -> None:
        target_panes = [pane_id] if pane_id is not None else list(self._pane_registry.keys())
        for target in target_panes:
            pane = self._pane_by_id(target)
            if pane is None:
                continue
            pane_mode = "agent" if pane._is_agent else "main"
            with self._pane_context(target):
                self._call_js("setPaneMode", pane_mode)

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
    def _provider_display_order() -> list[str]:
        preferred = ["claude", "codex", "gemini"]
        ordered: list[str] = []
        for provider_id in preferred:
            if provider_id in PROVIDERS and provider_id not in ordered:
                ordered.append(provider_id)
        for provider_id in PROVIDERS.keys():
            if provider_id not in ordered:
                ordered.append(provider_id)
        return ordered

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
        self._run_dialog(dialog)
        dialog.destroy()

    def _update_provider_toggle_button(self) -> None:
        if not self._provider_buttons:
            return

        active_provider_id = normalize_provider_id(self._active_provider_id)
        for provider_id, button in self._provider_buttons.items():
            normalized = normalize_provider_id(provider_id)
            context = button.get_style_context()
            context.remove_class("provider-select-button-active")
            if normalized == active_provider_id:
                context.add_class("provider-select-button-active")
                button.set_sensitive(True)
                button.set_tooltip_text(f"{self._provider_display_name(normalized)} (active)")
                continue

            reason = self._provider_unavailability_reason(
                normalized,
                refresh_binary=True,
                check_auth=True,
            )
            if reason is None:
                button.set_sensitive(True)
                button.set_tooltip_text(f"Switch to {self._provider_display_name(normalized)}")
            else:
                button.set_sensitive(False)
                button.set_tooltip_text(reason)

    def _on_provider_button_clicked(self, _button: Gtk.Button, provider_id: str) -> None:
        normalized_provider_id = normalize_provider_id(provider_id)
        if normalized_provider_id == self._active_provider_id:
            return
        self._switch_provider(normalized_provider_id)

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
            elif value == "ask":
                description = f"{provider.name} asks for each approval step before running tools."
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
            pane = self._pane_by_id(target)
            pane_mode = "agent" if (pane is not None and pane._is_agent) else "main"
            with self._pane_context(target):
                self._call_js("setReducedMotion", self._reduced_motion_from_gtk())
                self._call_js("applyProviderTheme", self._provider_theme_variables(provider))
                self._call_js("setModelOptions", self._provider_model_option_payload(provider))
                self._call_js("setPermissionOptions", self._provider_permission_option_payload(provider))
                self._call_js("setReasoningOptions", self._provider_reasoning_option_payload())
                self._call_js("setPaneMode", pane_mode)
                self._call_js("setStreamRenderThrottleMs", self._stream_render_throttle_ms)
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

    def _reload_all_webviews(self, *, skip_history_replay: bool = False) -> None:
        pane_ids = list(self._pane_registry.keys())
        for pane_id in pane_ids:
            pane = self._pane_registry.get(pane_id)
            if pane is None or pane._webview is None:
                continue
            with self._pane_context(pane_id):
                self._webview_ready = False
                self._pending_webview_scripts.clear()
                if skip_history_replay:
                    self._skip_history_replay_for_panes.add(pane_id)
                try:
                    # The chat shell is loaded via load_html(); reloading that URI directly can
                    # produce a blank white page on some GTK4/WebKit builds.
                    self._webview.load_html(CHAT_WEBVIEW_HTML, "")
                except Exception:
                    logger.exception("Could not rebuild WebView content for pane '%s' after settings update.", pane_id)
        self.queue_draw()

    def _apply_settings_payload(
        self,
        payload: dict[str, Any],
        *,
        reload_webviews: bool = False,
        show_startscreen_after_reload: bool = False,
    ) -> None:
        if not isinstance(payload, dict):
            payload = load_settings()

        self._system_tray_enabled = bool(payload.get("system_tray_enabled", True))
        refresh_provider_registry(payload)
        self._reasoning_options = get_reasoning_options(payload)

        self._provider_binaries = {
            provider_id: find_provider_binary(list(provider.binary_names))
            for provider_id, provider in PROVIDERS.items()
        }
        self._stream_render_throttle_ms = self._normalize_stream_render_throttle_ms(
            payload.get("stream_render_throttle_ms", self._stream_render_throttle_ms)
        )

        normalized_provider_id = normalize_provider_id(
            str(payload.get("active_provider_id") or self._active_provider_id)
        )
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
        if reload_webviews:
            self._reload_all_webviews(skip_history_replay=show_startscreen_after_reload)
        self._refresh_session_list()
        self._refresh_connection_state()
        self._setup_system_tray()

    def _on_settings_button_clicked(self, _button: Gtk.Button) -> None:
        try:
            self._open_settings_editor()
        except Exception as error:
            logger.exception("Could not open settings editor")
            self._set_status_message(f"Could not open settings: {error}", STATUS_ERROR)

    def _open_settings_editor(self) -> None:
        open_settings_editor(self)

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
                if process.is_running():
                    process.stop(force=True)
                if process.is_running():
                    all_stopped = False
                    logger.warning("Pane %s still reports running during provider switch; continuing.", pane_id)

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
            self._session_multi_select_mode = False
            self._session_selected_ids.clear()
            self._update_session_bulk_actions()

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
            self._persist_active_provider_preference()
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
        if pane_id not in self._pane_registry:
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
            if pane_id in self._skip_history_replay_for_panes:
                self._skip_history_replay_for_panes.discard(pane_id)
            else:
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
        if not self._activate_existing_pane(pane_id):
            return False
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().add_class("chat-focused")
        return False

    def _on_webview_focus_out(
        self,
        pane_id: str,
        _webview: WebKit.WebView,
        _event: Gdk.EventFocus,
    ) -> bool:
        if not self._activate_existing_pane(pane_id):
            return False
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().remove_class("chat-focused")
        return False

    def _on_js_change_model(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        if not self._activate_existing_pane(pane_id):
            return
        raw_value = self._extract_message_from_js_result(
            js_result,
            max_chars=_MAX_JS_OPTION_PAYLOAD_CHARS,
        )
        model_value = normalize_model_value(raw_value, provider=self._active_provider_id)
        self._apply_session_option("model", self._model_index_from_value(model_value))

    def _on_js_change_permission(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        if not self._activate_existing_pane(pane_id):
            return
        raw_value = self._extract_message_from_js_result(
            js_result,
            max_chars=_MAX_JS_OPTION_PAYLOAD_CHARS,
        )
        permission_value = normalize_permission_value(raw_value, provider=self._active_provider_id)
        self._apply_session_option("permission", self._permission_index_from_value(permission_value))

    def _on_js_change_reasoning(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        if not self._activate_existing_pane(pane_id):
            return
        if not self._active_provider.supports_reasoning:
            self._set_status_message(
                f"Reasoning level is ignored in {self._active_provider.name} mode.",
                STATUS_MUTED,
            )
            self._call_js("setReasoningVisible", False)
            return

        value = self._extract_message_from_js_result(
            js_result,
            max_chars=_MAX_JS_OPTION_PAYLOAD_CHARS,
        )
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
        js_result: WebKit.JavascriptResult,
    ) -> None:
        if not self._activate_existing_pane(pane_id):
            return
        if self._extract_action_from_js_result(
            js_result,
            allowed_actions={"refresh"},
        ) is None:
            return
        self._refresh_slash_commands()

    def _on_js_toggle_agent_mode(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        if not self._activate_existing_pane(pane_id):
            return
        raw_value = self._extract_message_from_js_result(
            js_result,
            max_chars=_MAX_JS_OPTION_PAYLOAD_CHARS,
        ).strip().lower()
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
        js_result: WebKit.JavascriptResult,
    ) -> None:
        on_js_attach_file(
            self,
            pane_id,
            js_result,
            max_option_payload_chars=_MAX_JS_OPTION_PAYLOAD_CHARS,
        )

    def _on_js_stop_process(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        if not self._activate_existing_pane(pane_id):
            return
        if self._extract_action_from_js_result(
            js_result,
            allowed_actions={"stop"},
        ) is None:
            return
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
        on_js_permission_response(
            self,
            pane_id,
            js_result,
            max_permission_payload_chars=_MAX_JS_PERMISSION_PAYLOAD_CHARS,
        )

    def _on_js_send_message(
        self,
        pane_id: str,
        _manager: WebKit.UserContentManager,
        js_result: WebKit.JavascriptResult,
    ) -> None:
        on_js_send_message(
            self,
            pane_id,
            js_result,
            max_send_payload_chars=_MAX_JS_SEND_PAYLOAD_CHARS,
            agentctl_hint=self._build_agentctl_hint(pane_id),
        )

    @staticmethod
    def _extract_message_from_js_result(
        js_result: Any,
        *,
        max_chars: int | None = None,
    ) -> str:
        return extract_message_from_js_result(js_result, max_chars=max_chars)

    @staticmethod
    def _extract_action_from_js_result(
        js_result: Any,
        *,
        allowed_actions: set[str],
        max_chars: int = _MAX_JS_OPTION_PAYLOAD_CHARS,
    ) -> str | None:
        return extract_action_from_js_result(
            js_result,
            allowed_actions=allowed_actions,
            max_chars=max_chars,
        )

    def _on_process_running_changed(self, pane_id: str, request_token: str, running: bool) -> None:
        if pane_id not in self._pane_registry:
            return
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return
            pane = self._pane_by_id(pane_id)
            if pane is not None and running:
                pane._typing_cleared_request_token = None
            request_session_id = self._active_request_session_id
            request_visible = bool(request_session_id) and request_session_id == self._active_session_id

            logger.info(
                "pane=%s request=%s provider=%s running=%s",
                pane_id,
                request_token,
                self._active_provider_id,
                running,
            )

            self._call_js("setProcessing", running if request_visible else False)
            if request_visible:
                self._set_typing(running)
            if not running:
                if pane is not None:
                    self._flush_buffered_assistant_chunks(pane_id, request_token)
                self._queue_context_indicator_update(immediate=True)

            if running and pane is not None and pane._is_agent:
                self._set_pane_agent_status(pane_id, "working")

            if running and request_visible and self._is_active_pane(pane_id):
                self._set_connection_state(CONNECTION_STARTING)
                self._set_status_message(f"{self._active_provider.name} is responding...", STATUS_INFO)

    def _on_process_assistant_chunk(self, pane_id: str, request_token: str, chunk: str) -> None:
        if pane_id not in self._pane_registry:
            return
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return
            if not chunk:
                return
            request_session_id = self._active_request_session_id
            request_visible = bool(request_session_id) and request_session_id == self._active_session_id
            pane = self._pane_by_id(pane_id)
            if request_visible and pane is not None and pane._typing_cleared_request_token != request_token:
                self._set_typing(False)
                pane._typing_cleared_request_token = request_token
            self._context_char_count += len(chunk)
            self._queue_context_indicator_update()
            if pane is not None:
                pane._pending_assistant_chunk_buffer += chunk
                self._schedule_buffered_assistant_chunk_flush(pane_id, request_token)

    def _on_process_system_message(self, pane_id: str, request_token: str, message: str) -> None:
        if pane_id not in self._pane_registry:
            return
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return
            if not message:
                return
            request_session_id = self._active_request_session_id
            request_visible = bool(request_session_id) and request_session_id == self._active_session_id
            if request_visible:
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
        if pane_id not in self._pane_registry:
            return
        with self._pane_context(pane_id):
            if not self._is_current_request(request_token):
                return
            if not payload:
                return

            logger.info(
                "pane=%s request=%s provider=%s permission_request tool=%s",
                pane_id,
                request_token,
                self._active_provider_id,
                str(payload.get("toolName") or ""),
            )

            request_session_id = self._active_request_session_id
            request_visible = bool(request_session_id) and request_session_id == self._active_session_id
            if request_visible:
                self._set_typing(False)
                self._call_js("addPermissionRequest", payload)
            if request_visible and self._is_active_pane(pane_id):
                self._set_status_message("Waiting for tool confirmation", STATUS_WARNING)
            if not self._permission_request_pending:
                self._permission_request_pending = True
                self.send_notification(
                    f"{self._active_provider.name} needs permission",
                    "A tool permission request is waiting for your input.",
                    urgency="critical",
                )

    def _on_process_complete(self, pane_id: str, request_token: str, result: ClaudeRunResult) -> None:
        if pane_id not in self._pane_registry:
            return
        with self._pane_context(pane_id):
            temp_paths = self._request_temp_files.pop(request_token, [])
            cleanup_temp_paths(temp_paths)
            pane = self._pane_by_id(pane_id)
            if pane is not None:
                self._flush_buffered_assistant_chunks(pane_id, request_token)

            if not self._is_current_request(request_token):
                return

            request_session_id = self._active_request_session_id
            request_visible = bool(request_session_id) and request_session_id == self._active_session_id
            self._invalidate_active_request()
            self._queue_context_indicator_update(immediate=True)
            if request_visible:
                self._set_typing(False)
            assistant_output_text = str(self._active_assistant_message or "")
            had_assistant_output = bool(assistant_output_text.strip())
            self._finish_assistant_message(
                target_session_id=request_session_id,
                sync_ui=request_visible,
            )
            self._permission_request_pending = False

            if result.success and result.conversation_id:
                if request_visible:
                    self._conversation_id = result.conversation_id
                target_session = self._find_session(request_session_id) if request_session_id else self._get_active_session()
                if target_session is not None:
                    target_session.conversation_id = result.conversation_id

            if result.cost_usd > 0:
                self._session_cost_usd += result.cost_usd
            if result.input_tokens > 0 or result.output_tokens > 0:
                self._session_tokens += result.input_tokens + result.output_tokens
            self._update_usage_display()

            if result.success:
                logger.info(
                    "pane=%s request=%s provider=%s complete success=1",
                    pane_id,
                    request_token,
                    self._active_provider_id,
                )
                self._last_request_failed = False
                if self._is_active_pane(pane_id):
                    self._refresh_connection_state()
                    if request_visible:
                        self._set_status_message(f"{self._active_provider.name} response received", STATUS_MUTED)
                    else:
                        self._set_status_message("Background session finished.", STATUS_MUTED)
                self._set_active_session_status(SESSION_STATUS_ACTIVE, session_id=request_session_id)
                self._save_sessions_safe("Could not save sessions")
                pane = self._pane_by_id(pane_id)
                should_close_agent_pane = False
                closed_agent_name = ""
                if pane is not None and pane._is_agent:
                    parsed_status = self._extract_agent_status_marker(assistant_output_text if had_assistant_output else "")
                    final_status = parsed_status or "done"
                    self._set_pane_agent_status(pane_id, final_status)
                    self._publish_agent_result_to_main_chat(
                        agent_pane_id=pane_id,
                        status=final_status,
                        assistant_text=assistant_output_text if had_assistant_output else "",
                    )
                    self._wake_main_after_agent_result(
                        agent_pane_id=pane_id,
                        status=final_status,
                        assistant_text=assistant_output_text if had_assistant_output else "",
                    )
                    if final_status == "done" and not self._is_primary_pane(pane_id):
                        should_close_agent_pane = True
                        closed_agent_name = self._pane_display_name(pane_id)
                if had_assistant_output:
                    self._execute_agentctl_from_assistant(pane_id, assistant_output_text)
                if had_assistant_output:
                    self.send_notification(
                        f"{self._active_provider.name} response complete",
                        f"{self._active_provider.name} finished responding.",
                    )
                if should_close_agent_pane:
                    self._close_pane(pane_id)
                    self._set_status_message(f"{closed_agent_name} finished and was closed.", STATUS_INFO)
                return

            error_message = result.error_message or f"{self._active_provider.name} request failed"
            logger.warning(
                "pane=%s request=%s provider=%s complete success=0 error=%s",
                pane_id,
                request_token,
                self._active_provider_id,
                error_message,
            )
            self._last_request_failed = True
            pane = self._pane_by_id(pane_id)
            if pane is not None and pane._is_agent:
                self._set_pane_agent_status(pane_id, "blocked")
                self._publish_agent_result_to_main_chat(
                    agent_pane_id=pane_id,
                    status="blocked",
                    assistant_text=assistant_output_text if had_assistant_output else error_message,
                )
                self._wake_main_after_agent_result(
                    agent_pane_id=pane_id,
                    status="blocked",
                    assistant_text=assistant_output_text if had_assistant_output else error_message,
                )
            if self._is_active_pane(pane_id):
                self._refresh_connection_state()
                self._set_status_message(error_message, STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR, session_id=request_session_id)
            if request_visible:
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

    @staticmethod
    def _cancel_pending_assistant_chunk_flush(pane: PaneController) -> None:
        if pane._pending_assistant_chunk_flush_id is not None:
            GLib.source_remove(pane._pending_assistant_chunk_flush_id)
            pane._pending_assistant_chunk_flush_id = None

    def _flush_buffered_assistant_chunks(self, pane_id: str, request_token: str, *, from_timer: bool = False) -> bool:
        pane = self._pane_by_id(pane_id)
        if pane is None:
            return False
        with self._pane_context(pane_id):
            if not from_timer and pane._pending_assistant_chunk_flush_id is not None:
                GLib.source_remove(pane._pending_assistant_chunk_flush_id)
            pane._pending_assistant_chunk_flush_id = None
            buffered_chunk = pane._pending_assistant_chunk_buffer
            pane._pending_assistant_chunk_buffer = ""
            if not buffered_chunk:
                return False
            if not self._is_current_request(request_token):
                return False
            request_session_id = self._active_request_session_id
            request_visible = bool(request_session_id) and request_session_id == self._active_session_id
            self._append_assistant_chunk(buffered_chunk, sync_ui=request_visible)
        return False

    def _flush_buffered_assistant_chunks_timer(self, pane_id: str, request_token: str) -> bool:
        return self._flush_buffered_assistant_chunks(pane_id, request_token, from_timer=True)

    def _schedule_buffered_assistant_chunk_flush(self, pane_id: str, request_token: str) -> None:
        pane = self._pane_by_id(pane_id)
        if pane is None or pane._pending_assistant_chunk_flush_id is not None:
            return
        pane._pending_assistant_chunk_flush_id = GLib.timeout_add(
            25,
            self._flush_buffered_assistant_chunks_timer,
            pane_id,
            request_token,
        )

    def _start_assistant_message(self) -> None:
        pane = self._state_pane()
        if pane is not None:
            self._cancel_pending_assistant_chunk_flush(pane)
            pane._pending_assistant_chunk_buffer = ""
        self._active_assistant_message = ""
        self._call_js("startAssistantMessage")

    def _append_assistant_chunk(self, text: str, *, sync_ui: bool = True) -> None:
        self._active_assistant_message += text
        if sync_ui:
            self._call_js("appendAssistantChunk", text)

    def _finish_assistant_message(self, *, target_session_id: str | None = None, sync_ui: bool = True) -> None:
        if self._active_assistant_message:
            self._add_to_history("assistant", self._active_assistant_message, session_id=target_session_id)
            self._save_sessions_safe("Could not save history")
            self._active_assistant_message = ""
        if sync_ui:
            self._call_js("finishAssistantMessage")

    def _add_system_message(self, text: str) -> None:
        self._call_js("addSystemMessage", text)

    def _set_typing(self, value: bool) -> None:
        self._call_js("setTyping", value)

    def _clear_messages(self) -> None:
        pane = self._state_pane()
        if pane is not None:
            self._cancel_pending_assistant_chunk_flush(pane)
            pane._pending_assistant_chunk_buffer = ""
        self._has_messages = False
        self._context_char_count = 0
        self._update_context_indicator()
        self._call_js("clearMessages")

    def _show_welcome(self) -> None:
        self._call_js("showWelcome")

    def _on_destroy(self, _widget: Gtk.Window) -> None:
        self._force_quit = True

        for pane_id, pane in self._pane_registry.items():
            with self._pane_context(pane_id):
                self._cancel_pending_assistant_chunk_flush(pane)
                pane._pending_assistant_chunk_buffer = ""
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
            "_context_indicator_throttle_id",
            "_session_search_debounce_id",
        ):
            self._cancel_timer(attr)

        self._teardown_system_tray()

        Gtk.main_quit()
