"""Main application window with WebKit2 chat UI and session management."""

from __future__ import annotations

import base64
import json
import math
import mimetypes
import os
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from gi.repository import Gdk, Gio, GLib, Gtk, Pango, WebKit2

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
    MODEL_OPTIONS,
    PERMISSION_OPTIONS,
    REASONING_LEVEL_OPTIONS,
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
from claude_code_gui.assets.chat_template import CHAT_WEBVIEW_HTML
from claude_code_gui.assets.gtk_css import CSS_STYLES
from claude_code_gui.core.model_permissions import (
    normalize_model_value,
    normalize_permission_value,
)
from claude_code_gui.core.paths import format_path, normalize_folder, shorten_path
from claude_code_gui.core.time_utils import current_timestamp, parse_timestamp
from claude_code_gui.domain.claude_types import ClaudeRunConfig
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
    detect_cli_flag_support,
    find_claude_binary,
)
from claude_code_gui.storage.config_paths import RECENT_FOLDERS_LIMIT
from claude_code_gui.storage.recent_folders_store import (
    load_recent_folders,
    save_recent_folders,
)
from claude_code_gui.storage.sessions_store import load_sessions, save_sessions


class ClaudeCodeWindow(Gtk.Window):
    """Single-window Claude Code shell with WebKit2 chat UI and session context."""

    def __init__(self) -> None:
        super().__init__(title=APP_NAME)
        self.set_decorated(True)
        self.set_default_size(APP_DEFAULT_WIDTH, APP_DEFAULT_HEIGHT)
        self.set_size_request(APP_MIN_WIDTH, APP_MIN_HEIGHT)

        self._webview: WebKit2.WebView | None = None
        self._webview_user_content_manager: WebKit2.UserContentManager | None = None
        self._webview_ready = False
        self._pending_webview_scripts: list[str] = []
        self._chat_shell: Gtk.EventBox | None = None

        self._sidebar_container: Gtk.Box | None = None
        self._sidebar_toggle_button: Gtk.Button | None = None
        self._sidebar_current_width = float(SIDEBAR_OPEN_WIDTH)
        self._sidebar_expanded = True
        self._sidebar_animation_id: int | None = None
        self._sidebar_expanded_only_widgets: list[Gtk.Widget] = []

        self._window_fade_animation_id: int | None = None
        self._window_fade_started = False

        self._status_fade_animation_id: int | None = None
        self._status_fade_widgets: list[Gtk.Widget] = []
        self._chat_reveal_animation_id: int | None = None
        self._chat_reveal_widgets: list[tuple[Gtk.Widget, float]] = []
        self._chat_pulse_animation_id: int | None = None

        self._project_status_label: Gtk.Label | None = None
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
        self._permission_request_pending = False
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

        self._request_temp_files: dict[str, list[str]] = {}

        self._selected_model_index = 1
        self._selected_permission_index = 0
        self._selected_reasoning_index = 1

        self._project_folder = normalize_folder(os.getcwd())
        self._recent_folders = load_recent_folders(self._project_folder)

        self._binary_path = find_claude_binary()
        self._supports_model_flag = False
        self._supports_permission_flag = False
        self._supports_reasoning_flag = False
        self._supports_output_format_flag = False
        self._supports_stream_json = False
        self._supports_json = False
        self._supports_include_partial_messages = False
        self._stream_json_requires_verbose = True

        self._claude_process = ClaudeProcess(
            on_running_changed=self._on_process_running_changed,
            on_assistant_chunk=self._on_process_assistant_chunk,
            on_system_message=self._on_process_system_message,
            on_permission_request=self._on_process_permission_request,
            on_complete=self._on_process_complete,
        )

        self._conversation_id: str | None = None
        self._active_request_token: str | None = None
        self._has_messages = False
        self._last_request_failed = False
        self._active_assistant_message = ""

        self._session_started_us = GLib.get_monotonic_time()
        self._session_timer_id: int | None = None
        self._sessions: list[SessionRecord] = []
        self._active_session_id: str | None = None

        self._set_dark_theme_preference()
        self._install_css()
        self._build_ui()
        self._load_sessions_into_state()
        self._refresh_session_list()
        GLib.idle_add(self._refresh_session_list_idle)

        self.connect("destroy", self._on_destroy)
        self.connect("map-event", self._on_map_event)
        self.connect("focus-in-event", self._on_window_focus_in)
        self.connect("focus-out-event", self._on_window_focus_out)

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            self._show_missing_binary_error()
            self._start_status_fade_in()
            return

        self._set_connection_state(CONNECTION_CONNECTED)
        if self._active_session_id is None:
            self._set_status_message("No active session. Click + New Chat to start.", STATUS_INFO)
        else:
            self._set_status_message("Session ready. Type a message below.", STATUS_MUTED)

        self._start_status_fade_in()
        self._detect_cli_flag_support_async(self._binary_path)

    @staticmethod
    def _set_dark_theme_preference() -> None:
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_STYLES.encode("utf-8"))

        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("app-root")
        self.add(root)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        content.get_style_context().add_class("main-content")
        root.pack_start(content, True, True, 0)

        sidebar = self._build_sidebar()
        content.pack_start(sidebar, False, False, 0)

        chat_panel = self._build_chat_panel()
        content.pack_start(chat_panel, True, True, 0)

        status_bar = self._build_status_bar()
        root.pack_end(status_bar, False, False, 0)

        self._update_project_folder_labels()
        self._update_status_model_and_permission()
        self._update_context_indicator()
        self._start_chat_reveal_in()

        self._session_timer_id = GLib.timeout_add_seconds(1, self._update_session_timer)

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
                pass

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

        toggle_button = Gtk.Button(label="")
        toggle_button.set_relief(Gtk.ReliefStyle.NONE)
        toggle_button.set_halign(Gtk.Align.START)
        toggle_button.get_style_context().add_class("sidebar-toggle-gtk")
        toggle_button.get_style_context().add_class("sidebar-header-toggle")
        toggle_button._drag_blocker = True
        toggle_button.connect("clicked", self._on_sidebar_toggle_clicked)
        sidebar_top.pack_start(toggle_button, False, False, 0)
        self._sidebar_toggle_button = toggle_button

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
        self._set_sidebar_content_visibility(self._sidebar_expanded)

        return sidebar

    def _build_chat_panel(self) -> Gtk.Box:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.set_hexpand(True)
        panel.set_vexpand(True)

        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrap.get_style_context().add_class("chat-wrap")
        wrap.set_hexpand(True)
        wrap.set_vexpand(True)
        panel.pack_start(wrap, True, True, 0)

        overlay = Gtk.Overlay()
        overlay.set_hexpand(True)
        overlay.set_vexpand(True)
        wrap.pack_start(overlay, True, True, 0)

        shell = Gtk.EventBox()
        shell.set_visible_window(True)
        shell.set_hexpand(True)
        shell.set_vexpand(True)
        shell.get_style_context().add_class("chat-shell")
        overlay.add(shell)
        self._chat_shell = shell
        self._chat_reveal_widgets = [(shell, 60.0)]
        for widget, _ in self._chat_reveal_widgets:
            widget.set_opacity(0.0)

        manager = WebKit2.UserContentManager()
        manager.register_script_message_handler("sendMessage")
        manager.register_script_message_handler("changeModel")
        manager.register_script_message_handler("changePermission")
        manager.register_script_message_handler("changeReasoning")
        manager.register_script_message_handler("changeFolder")
        manager.register_script_message_handler("attachFile")
        manager.register_script_message_handler("permissionResponse")
        manager.connect("script-message-received::sendMessage", self._on_js_send_message)
        manager.connect("script-message-received::changeModel", self._on_js_change_model)
        manager.connect("script-message-received::changePermission", self._on_js_change_permission)
        manager.connect("script-message-received::changeReasoning", self._on_js_change_reasoning)
        manager.connect("script-message-received::changeFolder", self._on_js_change_folder)
        manager.connect("script-message-received::attachFile", self._on_js_attach_file)
        manager.connect("script-message-received::permissionResponse", self._on_js_permission_response)
        manager.register_script_message_handler("stopProcess")
        manager.connect("script-message-received::stopProcess", self._on_js_stop_process)
        self._webview_user_content_manager = manager

        webview = WebKit2.WebView.new_with_user_content_manager(manager)
        webview.set_hexpand(True)
        webview.set_vexpand(True)
        webview.connect("load-changed", self._on_webview_load_changed)
        webview.connect("focus-in-event", self._on_webview_focus_in)
        webview.connect("focus-out-event", self._on_webview_focus_out)

        settings = webview.get_settings()
        if settings is not None:
            settings.set_enable_write_console_messages_to_stdout(False)
            settings.set_enable_developer_extras(False)
            settings.set_enable_javascript(True)

        webview.load_html(CHAT_WEBVIEW_HTML, "")
        shell.add(webview)
        self._webview = webview

        project_path_bar = self._build_project_path_bar()
        wrap.pack_start(project_path_bar, False, False, 8)

        return panel

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
        project_entry.connect("key-press-event", self._on_project_path_entry_key_press)
        project_entry.connect("focus-in-event", self._on_project_path_entry_focus_in)
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

        suggestion_popover = Gtk.Popover.new(project_entry)
        suggestion_popover.set_position(Gtk.PositionType.BOTTOM)
        suggestion_popover.set_modal(False)
        suggestion_popover.get_style_context().add_class("path-suggestion-popover")

        suggestion_scroll = Gtk.ScrolledWindow()
        suggestion_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        suggestion_scroll.set_shadow_type(Gtk.ShadowType.NONE)
        suggestion_scroll.set_size_request(560, 220)
        suggestion_popover.add(suggestion_scroll)

        suggestion_list = Gtk.ListBox()
        suggestion_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        suggestion_list.set_activate_on_single_click(True)
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

        self._project_status_label = None

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
        for index, (_, value) in enumerate(MODEL_OPTIONS):
            if value == model_value:
                return index
        return 0

    def _permission_index_from_value(self, permission_mode: str) -> int:
        for index, (_, value, _) in enumerate(PERMISSION_OPTIONS):
            if value == permission_mode:
                return index
        return 0

    def _reasoning_index_from_value(self, value: str) -> int:
        for i, (_, v) in enumerate(REASONING_LEVEL_OPTIONS):
            if v == value:
                return i
        return 1

    def _save_sessions_safe(self, context: str) -> bool:
        try:
            save_sessions(self._sessions)
            return True
        except (OSError, ValueError, TypeError) as error:
            self._set_status_message(f"{context}: {error}", STATUS_WARNING)
            return False

    def _reset_conversation_state(self, reason: str, reset_timer: bool = True) -> None:
        if reset_timer:
            self._session_started_us = GLib.get_monotonic_time()
        self._interrupt_running_process(reason)
        self._conversation_id = None
        self._clear_messages()
        self._show_welcome()
        self._set_typing(False)
        self._has_messages = False
        self._last_request_failed = False
        self._active_assistant_message = ""

    def _reset_conversation_state_keep_id(self, reason: str) -> None:
        self._session_started_us = GLib.get_monotonic_time()
        self._interrupt_running_process(reason)
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

    def _add_to_history(self, role: str, content: str) -> None:
        if not content:
            return
        active = self._get_active_session()
        if active is not None:
            active.history.append({"role": role, "content": content})
            if len(active.history) > 200:
                active.history = active.history[-200:]

    def _promote_replacement_session(self) -> SessionRecord | None:
        candidates = [s for s in self._sessions if s.status != SESSION_STATUS_ARCHIVED]
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

        active_candidates = [s for s in self._sessions if s.status != SESSION_STATUS_ARCHIVED]
        if not active_candidates:
            self._active_session_id = None
            return

        selected = max(active_candidates, key=self._session_sort_key)
        changed = False

        for session in active_candidates:
            if session.id == selected.id:
                if session.status != SESSION_STATUS_ACTIVE:
                    session.status = SESSION_STATUS_ACTIVE
                    changed = True
            elif session.status == SESSION_STATUS_ACTIVE:
                session.status = SESSION_STATUS_ENDED
                changed = True

        self._active_session_id = selected.id
        self._apply_session_to_controls(selected, add_to_recent=os.path.isdir(selected.project_path))
        self._conversation_id = None

        if changed:
            self._save_sessions_safe("Could not save session state")

    def _apply_session_to_controls(self, session: SessionRecord, add_to_recent: bool) -> None:
        self._project_folder = session.project_path
        self._selected_model_index = self._model_index_from_value(session.model)
        self._selected_permission_index = self._permission_index_from_value(session.permission_mode)
        self._selected_reasoning_index = self._reasoning_index_from_value(session.reasoning_level)
        self._set_project_path_entry_text(self._project_folder)

        if add_to_recent and os.path.isdir(self._project_folder):
            self._add_recent_folder(self._project_folder)

        self._update_project_folder_labels()
        self._update_status_model_and_permission()
        self._update_context_indicator()

        _, reasoning_value = REASONING_LEVEL_OPTIONS[self._selected_reasoning_index]
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
        _, model_value = MODEL_OPTIONS[self._selected_model_index]
        _, permission_value, _ = PERMISSION_OPTIONS[self._selected_permission_index]
        return SessionRecord(
            id=str(uuid.uuid4()),
            title=self._build_session_title(normalized, now),
            project_path=normalized,
            model=model_value,
            permission_mode=permission_value,
            status=SESSION_STATUS_ACTIVE,
            created_at=now,
            last_used_at=now,
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
        if self._session_filter == "active":
            candidates = [s for s in self._sessions if s.status == SESSION_STATUS_ACTIVE]
        elif self._session_filter == "archived":
            candidates = [s for s in self._sessions if s.status == SESSION_STATUS_ARCHIVED]
        else:
            candidates = [s for s in self._sessions if s.status != SESSION_STATUS_ARCHIVED]

        if self._session_search_query:
            query = self._session_search_query
            candidates = [
                session
                for session in candidates
                if query in (session.title or "").casefold() or query in (session.project_path or "").casefold()
            ]

        return sorted(candidates, key=self._session_sort_key, reverse=True)

    @staticmethod
    def _get_session_preview(session: SessionRecord) -> str:
        if not session.history:
            return ""
        for msg in reversed(session.history):
            if msg.get("role") == "user":
                content = str(msg.get("content") or "").strip()
                content = content.replace("\n", " ")
                if len(content) > 50:
                    return content[:47] + "..."
                return content
        return ""

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

        title = Gtk.Label(label=session.title or "New chat")
        title.set_xalign(0.0)
        title.get_style_context().add_class("session-title")
        title_row.pack_start(title, True, True, 0)
        label_box.pack_start(title_row, False, False, 0)

        preview_text = self._get_session_preview(session)
        if preview_text:
            preview = Gtk.Label(label=preview_text)
            preview.set_xalign(0.0)
            preview.set_ellipsize(Pango.EllipsizeMode.END)
            preview.set_max_width_chars(32)
            preview.set_single_line_mode(True)
            preview.get_style_context().add_class("session-preview")
            label_box.pack_start(preview, False, False, 0)

        open_button.add(label_box)
        row.pack_start(open_button, True, True, 0)

        menu_button = Gtk.MenuButton(label="⋯")
        menu_button.set_relief(Gtk.ReliefStyle.NONE)
        menu_button.get_style_context().add_class("session-menu-button")
        menu_button._drag_blocker = True

        popover = Gtk.Popover.new(menu_button)
        popover.get_style_context().add_class("session-popover")
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        menu_box.set_border_width(6)

        archive_button = Gtk.ModelButton(label="Archive")
        archive_button.connect("clicked", lambda _button, sid=session.id: self._archive_session(sid))
        menu_box.pack_start(archive_button, False, False, 0)

        delete_button = Gtk.ModelButton(label="Delete")
        delete_button.connect("clicked", lambda _button, sid=session.id: self._delete_session(sid))
        menu_box.pack_start(delete_button, False, False, 0)

        popover.add(menu_box)
        menu_box.show_all()
        menu_button.set_popover(popover)
        row.pack_end(menu_button, False, False, 0)

        def on_row_button_press(_widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
            if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
                try:
                    menu_button.popup()
                except Exception:
                    popover.show_all()
                return True
            return False

        row.connect("button-press-event", on_row_button_press)

        return row

    def _refresh_session_list(self) -> None:
        if self._session_list_box is None or self._session_empty_label is None:
            return

        if self._sessions_title_label is not None:
            self._sessions_title_label.set_text(f"Sessions ({len(self._sessions)})")

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
                self._session_empty_label.set_text("No chats yet. Click + New Chat.")
            self._session_list_box.pack_start(self._session_empty_label, False, False, 0)
            self._session_empty_label.show()
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

    def _refresh_session_list_idle(self) -> bool:
        self._refresh_session_list()
        return False

    def _switch_to_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        if session is None:
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
        self._reset_conversation_state_keep_id("Session switched")

        if session.history:
            self._replay_history(session.history)

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        self._refresh_connection_state()
        msg_count = len(session.history) if session.history else 0
        if msg_count > 0:
            self._set_status_message(f"Session restored with {msg_count} messages.", STATUS_INFO)
        else:
            self._set_status_message("Session switched.", STATUS_INFO)

    def _archive_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        if session is None or session.status == SESSION_STATUS_ARCHIVED:
            return

        was_active = session.id == self._active_session_id
        session.status = SESSION_STATUS_ARCHIVED
        session.last_used_at = current_timestamp()

        replacement = self._promote_replacement_session() if was_active else None

        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        if was_active and replacement is not None:
            self._reset_conversation_state("Active session archived")
            self._refresh_connection_state()
            self._set_status_message("Archived session. Switched to replacement.", STATUS_INFO)
            return

        if was_active and replacement is None:
            self._reset_conversation_state("Session archived", reset_timer=False)
            self._set_status_message("Session archived", STATUS_MUTED)
            self._refresh_connection_state()
            return

        self._set_status_message("Session archived", STATUS_MUTED)

    def _delete_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        if session is None:
            return

        was_active = session.id == self._active_session_id
        self._sessions = [item for item in self._sessions if item.id != session_id]

        replacement = self._promote_replacement_session() if was_active else None

        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        if was_active and replacement is not None:
            self._reset_conversation_state("Active session deleted")
            self._refresh_connection_state()
            self._set_status_message("Deleted session. Switched to replacement.", STATUS_INFO)
            return

        if was_active and replacement is None:
            self._reset_conversation_state("Session deleted", reset_timer=False)
            self._set_status_message("Session deleted", STATUS_MUTED)
            self._refresh_connection_state()
            return

        self._set_status_message("Session deleted", STATUS_MUTED)

    def _start_new_session(self, folder: str) -> None:
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

        self._reset_conversation_state("New session started")

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        self._refresh_connection_state()
        self._set_status_message("New session ready", STATUS_INFO)
        GLib.timeout_add(100, lambda: self._call_js("focusInput") or False)

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
            return []

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

        if show_popover and self._project_path_entry.is_focus():
            self._project_path_popover.show_all()
            self._project_path_popover.popup()

    def _hide_project_path_suggestions(self) -> None:
        if self._project_path_popover is None:
            return
        self._project_path_popover.popdown()

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

        if self._project_status_label is not None:
            self._project_status_label.set_text(shorten_path(full_display, 44))
            tooltip = full_display
            if self._last_status_message:
                tooltip = f"{full_display}\n{self._last_status_message}"
            self._project_status_label.set_tooltip_text(tooltip)

        self._call_js("updateFolder", full_display)

    def _update_status_model_and_permission(self) -> None:
        _, model_value = MODEL_OPTIONS[self._selected_model_index]
        _, permission_value, _ = PERMISSION_OPTIONS[self._selected_permission_index]
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
        if not binary_exists(self._binary_path):
            self._set_connection_state(CONNECTION_DISCONNECTED)
            return
        if self._claude_process.is_running():
            self._set_connection_state(CONNECTION_STARTING)
            return
        if self._last_request_failed:
            self._set_connection_state(CONNECTION_ERROR)
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
            self._add_system_message("Conversation reset because the project folder changed.")
            self._last_request_failed = False
            self._refresh_connection_state()

    def _detect_cli_flag_support(self, binary_path: str) -> None:
        caps = detect_cli_flag_support(binary_path)
        self._supports_model_flag = caps.supports_model_flag
        self._supports_permission_flag = caps.supports_permission_flag
        self._supports_reasoning_flag = caps.supports_reasoning_flag
        self._supports_output_format_flag = caps.supports_output_format_flag
        self._supports_stream_json = caps.supports_stream_json
        self._supports_json = caps.supports_json
        self._supports_include_partial_messages = caps.supports_include_partial_messages

    def _detect_cli_flag_support_async(self, binary_path: str) -> None:
        import threading

        def _probe() -> None:
            caps = detect_cli_flag_support(binary_path)
            GLib.idle_add(self._apply_cli_caps, caps)

        threading.Thread(target=_probe, daemon=True).start()

    def _apply_cli_caps(self, caps: "CliCapabilities") -> bool:
        self._supports_model_flag = caps.supports_model_flag
        self._supports_permission_flag = caps.supports_permission_flag
        self._supports_reasoning_flag = caps.supports_reasoning_flag
        self._supports_output_format_flag = caps.supports_output_format_flag
        self._supports_stream_json = caps.supports_stream_json
        self._supports_json = caps.supports_json
        self._supports_include_partial_messages = caps.supports_include_partial_messages
        self._refresh_connection_state()
        return False

    def _show_missing_binary_error(self) -> None:
        self.send_notification(
            "Claude CLI not found",
            "Install claude or claude-code so requests can run.",
            urgency="critical",
        )
        self._add_system_message(
            "Claude CLI was not found. Searched for claude, claude-code, and ~/.config/Claude/claude-code/."
        )

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Claude CLI not found",
        )
        dialog.format_secondary_text(
            "Install Claude Code CLI (binary `claude` or `claude-code`) or place it under "
            "~/.config/Claude/claude-code/."
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
        self._project_path_entry.select_region(0, -1)
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
        _manager: WebKit2.UserContentManager,
        _js_result: WebKit2.JavascriptResult,
    ) -> None:
        self._prompt_for_project_folder()

    def _apply_model_selection(self, index: int) -> None:
        if index < 0 or index >= len(MODEL_OPTIONS):
            return

        if index == self._selected_model_index:
            self._update_status_model_and_permission()
            return

        self._selected_model_index = index
        self._update_status_model_and_permission()
        self._update_context_indicator()
        active_session = self._get_active_session()
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            active_session.model = MODEL_OPTIONS[index][1]
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()
        if self._has_messages and self._claude_process.is_running():
            self._interrupt_running_process("Model changed")
        self._set_status_message("Model updated", STATUS_INFO)

    def _apply_permission_selection(self, index: int) -> None:
        if index < 0 or index >= len(PERMISSION_OPTIONS):
            return

        if index == self._selected_permission_index:
            self._update_status_model_and_permission()
            return

        self._selected_permission_index = index
        self._update_status_model_and_permission()
        self._update_context_indicator()
        active_session = self._get_active_session()
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            active_session.permission_mode = PERMISSION_OPTIONS[index][1]
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()
        if self._has_messages and self._claude_process.is_running():
            self._interrupt_running_process("Permission mode changed")
        self._set_status_message("Permission mode updated", STATUS_INFO)

    def _on_new_session_clicked(self, _button: Gtk.Button) -> None:
        if not os.path.isdir(self._project_folder):
            self._set_status_message("Current project folder is not available", STATUS_ERROR)
            return
        self._start_new_session(self._project_folder)

    def _on_new_session_other_folder_clicked(self, _button: Gtk.Button) -> None:
        self._prompt_for_project_folder()

    def _on_sidebar_toggle_clicked(self, _button: Any) -> None:
        self._sidebar_expanded = not self._sidebar_expanded
        self._set_sidebar_content_visibility(self._sidebar_expanded)
        self._update_sidebar_toggle_button()
        target_width = SIDEBAR_OPEN_WIDTH if self._sidebar_expanded else SIDEBAR_COLLAPSED_WIDTH
        self._animate_sidebar(target_width)

    def _update_sidebar_toggle_button(self) -> None:
        if self._sidebar_toggle_button is None:
            return

        if self._sidebar_expanded:
            self._sidebar_toggle_button.set_label("◀")
            self._sidebar_toggle_button.set_tooltip_text("Collapse sidebar")
            return

        self._sidebar_toggle_button.set_label("▶")
        self._sidebar_toggle_button.set_tooltip_text("Expand sidebar")

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
        duration_ms = 260.0
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

    def _on_webview_load_changed(self, _webview: WebKit2.WebView, load_event: WebKit2.LoadEvent) -> None:
        if load_event != WebKit2.LoadEvent.FINISHED:
            return

        self._webview_ready = True
        queued = list(self._pending_webview_scripts)
        self._pending_webview_scripts.clear()

        for script in queued:
            self._run_javascript(script)

        self._update_status_model_and_permission()
        self._show_welcome()
        GLib.timeout_add(100, lambda: self._call_js("focusInput") or False)

    def _on_webview_focus_in(self, _webview: WebKit2.WebView, _event: Gdk.EventFocus) -> bool:
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().add_class("chat-focused")
        return False

    def _on_webview_focus_out(self, _webview: WebKit2.WebView, _event: Gdk.EventFocus) -> bool:
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().remove_class("chat-focused")
        return False

    def _on_js_change_model(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_value = self._extract_message_from_js_result(js_result)
        model_value = normalize_model_value(raw_value)
        self._apply_model_selection(self._model_index_from_value(model_value))

    def _on_js_change_permission(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_value = self._extract_message_from_js_result(js_result)
        permission_value = normalize_permission_value(raw_value)
        self._apply_permission_selection(self._permission_index_from_value(permission_value))

    def _on_js_change_reasoning(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        value = self._extract_message_from_js_result(js_result)
        index = self._reasoning_index_from_value(value)
        if index == self._selected_reasoning_index:
            return

        self._selected_reasoning_index = index
        _, reasoning_value = REASONING_LEVEL_OPTIONS[index]

        active = self._get_active_session()
        if active is not None:
            active.reasoning_level = reasoning_value
            self._save_sessions_safe("Could not save session reasoning level")

        self._set_status_message(f"Reasoning level set to {reasoning_value}", STATUS_MUTED)

    def _on_js_attach_file(
        self,
        _manager: WebKit2.UserContentManager,
        _js_result: WebKit2.JavascriptResult,
    ) -> None:
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
            "type": mime_type,
            "data": f"data:{mime_type};base64,{base64.b64encode(raw_bytes).decode('ascii')}",
        }
        self._call_js("addHostAttachment", payload)

    def _on_js_stop_process(
        self,
        _manager: WebKit2.UserContentManager,
        _js_result: WebKit2.JavascriptResult,
    ) -> None:
        if self._claude_process.is_running():
            self._claude_process.stop()
            self._set_status_message("Process stopped by user", STATUS_WARNING)
            self._add_system_message("Process stopped.")

    def _on_js_permission_response(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
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
        if action not in {"allow", "deny", "comment"}:
            return

        comment = str(parsed_payload.get("comment") or "")
        request_id = str(parsed_payload.get("requestId") or "")
        sent = self._claude_process.send_permission_response(
            action=action,
            comment=comment,
            request_id=request_id,
        )
        if not sent:
            self._set_status_message("Could not deliver permission response", STATUS_WARNING)
            self._add_system_message("Could not send permission response to Claude.")
            return

        if action == "allow":
            self._set_status_message("Permission approved", STATUS_INFO)
        elif action == "deny":
            self._set_status_message("Permission denied", STATUS_WARNING)
        else:
            self._set_status_message("Permission comment sent", STATUS_INFO)

    def _on_js_send_message(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_text = self._extract_message_from_js_result(js_result)
        message, attachments = parse_send_payload(raw_text)
        if not message and not attachments:
            return

        if self._binary_path is None:
            self._refresh_connection_state()
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._add_system_message("Claude CLI is not available.")
            return

        if self._active_session_id is None:
            if os.path.isdir(self._project_folder):
                self._start_new_session(self._project_folder)
            else:
                self._set_status_message("No active session", STATUS_ERROR)
                self._add_system_message("Create a session first.")
                return

        if self._claude_process.is_running():
            self._add_system_message("Claude is still responding. Please wait.")
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

        _, model_value = MODEL_OPTIONS[self._selected_model_index]
        _, permission_value, _ = PERMISSION_OPTIONS[self._selected_permission_index]
        _, reasoning_value = REASONING_LEVEL_OPTIONS[self._selected_reasoning_index]

        attachment_paths = materialize_attachments(attachments)
        composed_message = compose_message_with_attachments(message, attachment_paths)
        if not composed_message.strip():
            cleanup_temp_paths(attachment_paths)
            return

        self._has_messages = True
        self._context_char_count += len(composed_message)
        self._update_context_indicator()

        self._set_typing(True)
        self._pulse_chat_shell()
        self._set_connection_state(CONNECTION_STARTING)
        self._set_status_message("Sending message to Claude...", STATUS_INFO)

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
            supports_model_flag=self._supports_model_flag,
            supports_permission_flag=self._supports_permission_flag,
            supports_output_format_flag=self._supports_output_format_flag,
            supports_stream_json=self._supports_stream_json,
            supports_json=self._supports_json,
            supports_include_partial_messages=self._supports_include_partial_messages,
            stream_json_requires_verbose=self._stream_json_requires_verbose,
            reasoning_level=reasoning_value,
            supports_reasoning_flag=self._supports_reasoning_flag,
        )
        started = self._claude_process.send_message(request_token=request_token, config=config)

        if not started:
            cleanup_temp_paths(attachment_paths)
            self._context_char_count = max(0, self._context_char_count - len(composed_message))
            self._update_context_indicator()
            self._active_request_token = previous_request_token
            self._set_typing(False)
            self._refresh_connection_state()
            self._set_status_message("A request is already running", STATUS_WARNING)
            return

        self._request_temp_files[request_token] = attachment_paths

    @staticmethod
    def _extract_message_from_js_result(js_result: WebKit2.JavascriptResult) -> str:
        try:
            js_value = js_result.get_js_value()
            raw = js_value.to_string()
        except Exception:
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

    def _on_process_running_changed(self, request_token: str, running: bool) -> None:
        if not self._is_current_request(request_token):
            return

        self._call_js("setProcessing", running)

        if running:
            self._set_connection_state(CONNECTION_STARTING)
            self._set_status_message("Claude is responding...", STATUS_INFO)

    def _on_process_assistant_chunk(self, request_token: str, chunk: str) -> None:
        if not self._is_current_request(request_token):
            return
        if not chunk:
            return
        self._set_typing(False)
        self._context_char_count += len(chunk)
        self._update_context_indicator()
        self._append_assistant_chunk(chunk)

    def _on_process_system_message(self, request_token: str, message: str) -> None:
        if not self._is_current_request(request_token):
            return
        if not message:
            return
        self._add_system_message(message)
        if not self._permission_request_pending and self._is_permission_request_message(message):
            self._permission_request_pending = True
            self.send_notification(
                "Claude needs permission",
                "A tool permission request is waiting for your input.",
                urgency="critical",
            )

    def _on_process_permission_request(self, request_token: str, payload: dict[str, Any]) -> None:
        if not self._is_current_request(request_token):
            return
        if not payload:
            return

        self._set_typing(False)
        self._call_js("addPermissionRequest", payload)
        self._set_status_message("Waiting for tool confirmation", STATUS_WARNING)
        if not self._permission_request_pending:
            self._permission_request_pending = True
            self.send_notification(
                "Claude needs permission",
                "A tool permission request is waiting for your input.",
                urgency="critical",
            )

    def _on_process_complete(self, request_token: str, result: ClaudeRunResult) -> None:
        temp_paths = self._request_temp_files.pop(request_token, [])
        cleanup_temp_paths(temp_paths)

        if not self._is_current_request(request_token):
            return

        self._invalidate_active_request()
        self._set_typing(False)
        had_assistant_output = bool(self._active_assistant_message.strip())
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
            self._refresh_connection_state()
            self._set_status_message("Claude response received", STATUS_MUTED)
            self._set_active_session_status(SESSION_STATUS_ACTIVE)
            self._save_sessions_safe("Could not save sessions")
            if had_assistant_output:
                self.send_notification(
                    "Claude response complete",
                    "Claude finished responding.",
                )
            return

        error_message = result.error_message or "Claude request failed"
        self._last_request_failed = True
        self._refresh_connection_state()
        self._set_status_message(error_message, STATUS_ERROR)
        self._set_active_session_status(SESSION_STATUS_ERROR)
        self._add_system_message(error_message)
        self.send_notification("Claude error", error_message, urgency="critical")

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

        try:
            self._webview.run_javascript(script, None, None, None)
            return
        except TypeError:
            pass

        try:
            self._webview.run_javascript(script, None, None)
            return
        except TypeError:
            pass

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

    def _add_user_message(self, text: str) -> None:
        self._has_messages = True
        self._call_js("addUserMessage", text)

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
        self._claude_process.stop()
        for paths in self._request_temp_files.values():
            cleanup_temp_paths(paths)
        self._request_temp_files.clear()

        for attr in (
            "_sidebar_animation_id",
            "_window_fade_animation_id",
            "_status_fade_animation_id",
            "_chat_reveal_animation_id",
            "_chat_pulse_animation_id",
            "_session_timer_id",
        ):
            self._cancel_timer(attr)

        Gtk.main_quit()
