"""Main application window with WebKit2 chat UI and session management."""

from __future__ import annotations

import base64
import json
import logging
import math
import mimetypes
import os
import re
import subprocess
import time
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
    detect_cli_flag_support,
    find_provider_binary,
    is_codex_authenticated,
)
from claude_code_gui.storage.config_paths import RECENT_FOLDERS_LIMIT
from claude_code_gui.storage.recent_folders_store import (
    load_recent_folders,
    save_recent_folders,
)
from claude_code_gui.storage.sessions_store import load_sessions, save_sessions


logger = logging.getLogger(__name__)


class ClaudeCodeWindow(Gtk.Window):
    """Single-window Claude Code shell with WebKit2 chat UI and session context."""

    def __init__(self) -> None:
        super().__init__(title=APP_NAME)
        self._active_provider_id: str = DEFAULT_PROVIDER_ID
        self._provider_binaries: dict[str, str | None] = {
            provider_id: find_provider_binary(list(provider.binary_names))
            for provider_id, provider in PROVIDERS.items()
        }
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
        self._provider_toggle_button: Gtk.Button | None = None
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
        self._permission_request_pending = False
        self._notification_counter = 0
        self._allowed_tools: set[str] = set()

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

        self._model_options: list[tuple[str, str]] = list(self._active_provider.model_options)
        self._permission_options: list[tuple[str, str, bool]] = list(self._active_provider.permission_options)
        self._selected_model_index = 1 if len(self._model_options) > 1 else 0
        self._selected_permission_index = 0
        self._selected_reasoning_index = 1

        self._project_folder = normalize_folder(os.getcwd())
        self._recent_folders = load_recent_folders(self._project_folder)

        self._binary_path = self._provider_binaries.get(self._active_provider_id)
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
        self._apply_provider_branding()
        self._load_sessions_into_state()
        self._refresh_session_list()
        self._update_provider_toggle_button()
        GLib.idle_add(self._refresh_session_list_idle)

        self.connect("destroy", self._on_destroy)
        self.connect("map-event", self._on_map_event)
        self.connect("focus-in-event", self._on_window_focus_in)
        self.connect("focus-out-event", self._on_window_focus_out)

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
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
        return f"{provider.icon} {provider.name}"

    def _provider_window_title(self, provider_id: str | None = None) -> str:
        return f"{self._provider_display_name(provider_id)} Code"

    def _install_css(self) -> None:
        provider = self._active_provider
        self._swap_css(
            provider.colors,
            provider.accent_rgb,
            provider.accent_soft_rgb,
        )

    def _swap_css(
        self,
        colors: dict[str, str],
        accent_rgb: tuple[int, int, int],
        accent_soft_rgb: tuple[int, int, int],
    ) -> None:
        css = build_gtk_css(colors, accent_rgb, accent_soft_rgb)
        new_provider = Gtk.CssProvider()
        new_provider.load_from_data(css.encode("utf-8"))

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

        provider_button = Gtk.Button(label=self._provider_button_label())
        provider_button.set_relief(Gtk.ReliefStyle.NONE)
        provider_button.set_halign(Gtk.Align.START)
        provider_button.get_style_context().add_class("provider-switch-button")
        provider_button._drag_blocker = True
        provider_button.connect("clicked", self._on_provider_toggle_clicked)
        sidebar_top.pack_start(provider_button, False, False, 0)
        self._provider_toggle_button = provider_button

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
        manager.register_script_message_handler("refreshSlashCommands")
        manager.connect(
            "script-message-received::refreshSlashCommands",
            self._on_js_refresh_slash_commands,
        )
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
        seen: set[str] = set()

        def normalize_providers(providers: list[str] | tuple[str, ...]) -> list[str]:
            normalized: list[str] = []
            for provider_id in providers:
                candidate = normalize_provider_id(provider_id)
                if candidate not in normalized:
                    normalized.append(candidate)
            return normalized or [DEFAULT_PROVIDER_ID]

        def add_command(name: str, icon: str, description: str, providers: list[str] | tuple[str, ...]) -> None:
            safe_name = self._safe_slash_name(name)
            if not safe_name:
                return
            key = safe_name.casefold()
            if key in seen:
                return
            provider_list = normalize_providers(providers)
            seen.add(key)
            commands.append(
                {
                    "name": safe_name,
                    "icon": icon,
                    "description": self._truncate_text(description, 96),
                    "providers": provider_list,
                }
            )

        project_root = Path(self._project_folder)
        command_roots: list[tuple[Path, tuple[str, ...]]] = [
            (project_root / ".claude" / "commands", ("claude",)),
            (Path.home() / ".claude" / "commands", ("claude",)),
        ]
        if self._active_provider_id == "codex":
            command_roots.extend(
                [
                    (project_root / ".codex" / "commands", ("codex",)),
                    (Path.home() / ".codex" / "commands", ("codex",)),
                ]
            )
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

        if self._active_provider_id == "codex":
            skill_roots: list[tuple[Path, tuple[str, ...]]] = [
                (project_root / ".codex" / "skills", ("codex",)),
                (Path.home() / ".codex" / "skills", ("codex",)),
            ]
        else:
            skill_roots = [
                (project_root / ".agents" / "skills", ("claude",)),
                (Path.home() / ".agents" / "skills", ("claude",)),
            ]
        for root, providers in skill_roots:
            if not root.is_dir():
                continue
            for skill_dir in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
                if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                    continue
                skill_doc = skill_dir / "SKILL.md"
                if not skill_doc.is_file():
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
                    logger.exception("Could not show session row context menu via popup(); using fallback.")
                    popover.show_all()
                return True
            return False

        row.connect("button-press-event", on_row_button_press)

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
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
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

    def _detect_cli_flag_support_async(self, binary_path: str) -> None:
        if not binary_path:
            self._set_cli_caps(None)
            return

        import threading

        def _probe() -> None:
            caps = detect_cli_flag_support(binary_path)
            GLib.idle_add(self._apply_cli_caps, caps)

        threading.Thread(target=_probe, daemon=True).start()

    def _set_cli_caps(self, caps: "CliCapabilities | None") -> None:
        if caps is None:
            self._supports_model_flag = False
            self._supports_permission_flag = False
            self._supports_reasoning_flag = False
            self._supports_output_format_flag = False
            self._supports_stream_json = False
            self._supports_json = False
            self._supports_include_partial_messages = False
            return

        self._supports_model_flag = caps.supports_model_flag
        self._supports_permission_flag = caps.supports_permission_flag
        self._supports_reasoning_flag = caps.supports_reasoning_flag and self._active_provider.supports_reasoning
        self._supports_output_format_flag = caps.supports_output_format_flag
        self._supports_stream_json = caps.supports_stream_json
        self._supports_json = caps.supports_json
        self._supports_include_partial_messages = caps.supports_include_partial_messages

    def _apply_cli_caps(self, caps: "CliCapabilities") -> bool:
        self._set_cli_caps(caps)
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
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=f"{provider.name} CLI not found",
        )
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

    def _apply_session_option(self, kind: str, index: int) -> None:
        if kind == "model":
            options = self._model_options
            selected_index = self._selected_model_index
            running_change_reason = "Model changed"
            status_message = "Model updated"
        elif kind == "permission":
            options = self._permission_options
            selected_index = self._selected_permission_index
            running_change_reason = "Permission mode changed"
            status_message = "Permission mode updated"
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
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            if kind == "model":
                active_session.model = self._model_options[index][1]
            else:
                active_session.permission_mode = self._permission_options[index][1]
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()
        if self._has_messages and self._claude_process.is_running():
            self._interrupt_running_process(running_change_reason)
        self._set_status_message(status_message, STATUS_INFO)

    def _on_new_session_clicked(self, _button: Gtk.Button) -> None:
        if not os.path.isdir(self._project_folder):
            self._set_status_message("Current project folder is not available", STATUS_ERROR)
            return
        self._start_new_session(self._project_folder)

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

        if normalized_provider_id == "codex" and check_auth and not is_codex_authenticated():
            return "Codex is not logged in. Run `codex login` and retry."

        return None

    def _show_provider_unavailable_error(self, provider: ProviderConfig, reason: str) -> None:
        title = f"{provider.name} unavailable"
        self._set_status_message(reason, STATUS_ERROR)
        self._add_system_message(reason)
        self.send_notification(title, reason, urgency="critical")

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=title,
        )
        dialog.format_secondary_text(reason)
        dialog.run()
        dialog.destroy()

    def _update_provider_toggle_button(self) -> None:
        if self._provider_toggle_button is None:
            return

        self._provider_toggle_button.set_label(self._provider_button_label())
        next_provider_id = self._next_provider_id()
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

    def _sync_provider_state_to_webview(self) -> None:
        provider = self._active_provider
        self._call_js("applyProviderTheme", self._provider_theme_variables(provider))
        self._call_js("setModelOptions", self._provider_model_option_payload(provider))
        self._call_js("setPermissionOptions", self._provider_permission_option_payload(provider))
        self._call_js(
            "setProviderBranding",
            {
                "id": provider.id,
                "name": provider.name,
                "icon": provider.icon,
                "welcomeTitle": f"{provider.name} is ready",
            },
        )
        self._call_js("setReasoningVisible", provider.supports_reasoning)
        self._update_status_model_and_permission()
        if provider.supports_reasoning:
            _, reasoning_value = REASONING_LEVEL_OPTIONS[self._selected_reasoning_index]
            self._call_js("updateReasoningLevel", reasoning_value)

    def _apply_provider_branding(self) -> None:
        self.set_title(self._provider_window_title())
        self._sync_provider_state_to_webview()

    def _set_provider_option_lists(
        self,
        provider_id: str,
        *,
        preferred_model: str | None = None,
        preferred_permission: str | None = None,
    ) -> None:
        provider = PROVIDERS[normalize_provider_id(provider_id)]
        previous_model_value = ""
        if 0 <= self._selected_model_index < len(self._model_options):
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

    def _stop_running_request_for_provider_switch(self) -> bool:
        self._invalidate_active_request()
        self._permission_request_pending = False
        if not self._claude_process.is_running():
            return True

        self._claude_process.stop()
        deadline = time.monotonic() + 2.5
        while self._claude_process.is_running() and time.monotonic() < deadline:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(0.03)

        if self._claude_process.is_running():
            self._claude_process.stop(force=True)
            force_deadline = time.monotonic() + 1.0
            while self._claude_process.is_running() and time.monotonic() < force_deadline:
                while Gtk.events_pending():
                    Gtk.main_iteration_do(False)
                time.sleep(0.03)

        return not self._claude_process.is_running()

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
            )
            self._active_provider_id = normalized_new_provider_id
            self._binary_path = new_binary_path
            self._set_provider_option_lists(normalized_new_provider_id)
            self._ensure_active_session_for_provider(reset_conversation=True)

            if old_active_session is not None and old_active_session.status == SESSION_STATUS_ACTIVE:
                old_active_session.status = SESSION_STATUS_ENDED
                old_active_session.last_used_at = current_timestamp()

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
            self._refresh_slash_commands()
            self._save_sessions_safe("Could not save sessions")
            self._update_provider_toggle_button()

            if self._binary_path is None:
                self._set_connection_state(CONNECTION_DISCONNECTED)
                self._show_missing_binary_error()
            else:
                self._detect_cli_flag_support_async(self._binary_path)
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

    def _on_webview_load_changed(self, _webview: WebKit2.WebView, load_event: WebKit2.LoadEvent) -> None:
        if load_event != WebKit2.LoadEvent.FINISHED:
            return

        self._webview_ready = True
        queued = list(self._pending_webview_scripts)
        self._pending_webview_scripts.clear()

        for script in queued:
            self._run_javascript(script)

        self._sync_provider_state_to_webview()
        self._show_welcome()
        self._refresh_slash_commands()
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
        model_value = normalize_model_value(raw_value, provider=self._active_provider_id)
        self._apply_session_option("model", self._model_index_from_value(model_value))

    def _on_js_change_permission(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_value = self._extract_message_from_js_result(js_result)
        permission_value = normalize_permission_value(raw_value, provider=self._active_provider_id)
        self._apply_session_option("permission", self._permission_index_from_value(permission_value))

    def _on_js_change_reasoning(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
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
        _, reasoning_value = REASONING_LEVEL_OPTIONS[index]

        active = self._get_active_session()
        if active is not None:
            active.reasoning_level = reasoning_value
            self._save_sessions_safe("Could not save session reasoning level")

        self._set_status_message(f"Reasoning level set to {reasoning_value}", STATUS_MUTED)

    def _on_js_refresh_slash_commands(
        self,
        _manager: WebKit2.UserContentManager,
        _js_result: WebKit2.JavascriptResult,
    ) -> None:
        self._refresh_slash_commands()

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
            self._add_system_message(f"{self._active_provider.name} process stopped.")

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
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_text = self._extract_message_from_js_result(js_result)
        message, attachments = parse_send_payload(raw_text)
        if not message and not attachments:
            return

        if self._binary_path is None:
            self._refresh_connection_state()
            self._set_status_message(f"{self._active_provider.name} CLI not found", STATUS_ERROR)
            self._add_system_message(f"{self._provider_cli_label()} is not available.")
            return
        if self._active_provider_id == "codex" and not is_codex_authenticated():
            auth_message = "Codex is not logged in. Run `codex login` and retry."
            self._refresh_connection_state()
            self._set_status_message(auth_message, STATUS_ERROR)
            self._add_system_message(auth_message)
            return

        if self._active_session_id is None:
            if os.path.isdir(self._project_folder):
                self._start_new_session(self._project_folder)
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
        _, reasoning_value = REASONING_LEVEL_OPTIONS[self._selected_reasoning_index]
        if not self._active_provider.supports_reasoning:
            reasoning_value = "medium"

        attachment_paths = materialize_attachments(attachments)
        composed_message = compose_message_with_attachments(message, attachment_paths)
        if not composed_message.strip():
            cleanup_temp_paths(attachment_paths)
            return

        self._has_messages = True
        self._context_char_count += len(composed_message)
        self._update_context_indicator()

        # Create the assistant row immediately so users see true live streaming
        # instead of waiting for the first token to create the bubble.
        self._start_assistant_message()
        self._pulse_chat_shell()
        self._set_connection_state(CONNECTION_STARTING)
        self._set_status_message(f"Sending message to {self._active_provider.name}...", STATUS_INFO)

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
    def _extract_message_from_js_result(js_result: WebKit2.JavascriptResult) -> str:
        try:
            js_value = js_result.get_js_value()
            raw = js_value.to_string()
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

    def _on_process_running_changed(self, request_token: str, running: bool) -> None:
        if not self._is_current_request(request_token):
            return

        self._call_js("setProcessing", running)

        if running:
            self._set_connection_state(CONNECTION_STARTING)
            self._set_status_message(f"{self._active_provider.name} is responding...", STATUS_INFO)

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
                f"{self._active_provider.name} needs permission",
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
                f"{self._active_provider.name} needs permission",
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
            self._set_status_message(f"{self._active_provider.name} response received", STATUS_MUTED)
            self._set_active_session_status(SESSION_STATUS_ACTIVE)
            self._save_sessions_safe("Could not save sessions")
            if had_assistant_output:
                self.send_notification(
                    f"{self._active_provider.name} response complete",
                    f"{self._active_provider.name} finished responding.",
                )
            return

        error_message = result.error_message or f"{self._active_provider.name} request failed"
        self._last_request_failed = True
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

        if self._css_provider is not None:
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
