#!/usr/bin/env python3
"""Native GTK3 wrapper for Claude Code CLI using an embedded VTE terminal."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")

from gi.repository import Gdk, GLib, Gtk, Vte


class ClaudeCodeWindow(Gtk.Window):
    """Single-purpose Claude Code desktop shell."""

    WINDOW_BG = "#1a1a1a"
    SIDEBAR_BG = "#1e1c1b"
    HEADER_BG = "#262624"
    STATUS_BG = "#1e1c1b"
    TERMINAL_BG = "#1e1e1e"
    FOREGROUND = "#e8e4de"
    FOREGROUND_MUTED = "#8a8780"
    ACCENT = "#da7b3a"
    BORDER = "#2e2c2a"
    BUTTON_HOVER = "#3a3836"
    SELECTION_BG = "#3a3a38"
    SUCCESS = "#4caf50"

    SIDEBAR_OPEN_WIDTH = 250

    def __init__(self) -> None:
        super().__init__(title="Claude Code")
        self.set_default_size(1400, 900)
        self.set_size_request(900, 600)

        self._terminal: Vte.Terminal | None = None
        self._terminal_shell: Gtk.EventBox | None = None
        self._status_label: Gtk.Label | None = None
        self._connection_label: Gtk.Label | None = None
        self._connection_dot: Gtk.Label | None = None
        self._session_timer_label: Gtk.Label | None = None
        self._child_pid: int | None = None

        self._sidebar_container: Gtk.Box | None = None
        self._sidebar_toggle_button: Gtk.Button | None = None
        self._sidebar_current_width = float(self.SIDEBAR_OPEN_WIDTH)
        self._sidebar_expanded = True
        self._sidebar_animation_id: int | None = None

        self._status_fade_animation_id: int | None = None
        self._status_fade_widgets: list[Gtk.Widget] = []

        self._window_fade_animation_id: int | None = None
        self._window_fade_started = False

        self._maximize_button: Gtk.Button | None = None
        self._window_is_maximized = False

        self._session_started_us = GLib.get_monotonic_time()

        self._set_dark_theme_preference()
        self._install_css()
        self._build_ui()

        self.connect("destroy", self._on_destroy)
        self.connect("map-event", self._on_map_event)
        self.connect("window-state-event", self._on_window_state_event)

        binary_path = self._find_claude_binary()
        if binary_path is None:
            self._set_connection_status(False)
            self._show_missing_binary_error()
            self._start_status_fade_in()
            return

        self._launch_claude(binary_path)

    @staticmethod
    def _set_dark_theme_preference() -> None:
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)

    def _install_css(self) -> None:
        css = f"""
        window,
        .app-root {{
            background-color: {self.WINDOW_BG};
            color: {self.FOREGROUND};
        }}

        .header-shell {{
            background-color: {self.HEADER_BG};
            border-bottom: 1px solid {self.BORDER};
            box-shadow: 0 1px 0 rgba(0, 0, 0, 0.25);
        }}

        .header-row {{
            padding: 8px 10px;
        }}

        .brand-icon {{
            color: {self.ACCENT};
            font-weight: 700;
            font-size: 18px;
        }}

        .brand-title {{
            color: {self.FOREGROUND};
            font-weight: 700;
            font-size: 14px;
        }}

        .control-button,
        .new-session-button,
        .sidebar-toggle {{
            background-color: transparent;
            color: {self.FOREGROUND};
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 6px 10px;
            transition: background-color 140ms ease-in-out, border-color 140ms ease-in-out;
        }}

        .control-button:hover,
        .new-session-button:hover,
        .sidebar-toggle:hover {{
            background-color: {self.BUTTON_HOVER};
            border-color: {self.BORDER};
        }}

        .control-close:hover {{
            background-color: #4a2723;
            border-color: #5a322d;
        }}

        .content-row {{
            background-color: {self.WINDOW_BG};
        }}

        .sidebar {{
            background-color: {self.SIDEBAR_BG};
            border-right: 1px solid {self.BORDER};
            padding: 14px;
        }}

        .sidebar-title {{
            color: {self.FOREGROUND};
            font-weight: 600;
            font-size: 12px;
        }}

        .sidebar-muted {{
            color: {self.FOREGROUND_MUTED};
            font-size: 11px;
        }}

        .new-session-button {{
            border: 1px solid {self.BORDER};
            background-image: none;
            background-color: #2b2927;
            font-weight: 600;
            padding: 8px 12px;
        }}

        .history-frame {{
            background-color: {self.WINDOW_BG};
            border: 1px solid {self.BORDER};
            border-radius: 10px;
            padding: 10px;
        }}

        .terminal-wrap {{
            padding: 4px;
            background-color: {self.WINDOW_BG};
        }}

        .terminal-shell {{
            background-color: {self.TERMINAL_BG};
            border: 1px solid {self.BORDER};
            border-radius: 11px;
        }}

        .terminal-shell.terminal-focused {{
            border-color: {self.ACCENT};
            box-shadow: 0 0 0 1px rgba(218, 123, 58, 0.35);
        }}

        .status-bar {{
            background-color: {self.STATUS_BG};
            border-top: 1px solid {self.BORDER};
            padding: 6px 12px;
        }}

        .status-text {{
            color: {self.FOREGROUND};
            font-size: 11px;
        }}

        .status-muted {{
            color: {self.FOREGROUND_MUTED};
            font-size: 11px;
        }}

        .connection-dot {{
            font-size: 12px;
            color: {self.SUCCESS};
        }}

        .connection-dot.disconnected {{
            color: #a15d52;
        }}
        """.encode("utf-8")

        provider = Gtk.CssProvider()
        provider.load_from_data(css)

        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self) -> None:
        header_shell = Gtk.EventBox()
        header_shell.set_visible_window(True)
        header_shell.get_style_context().add_class("header-shell")
        header_shell.connect("button-press-event", self._on_header_button_press)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_row.get_style_context().add_class("header-row")
        header_shell.add(header_row)

        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        sidebar_toggle = Gtk.Button(label="◀")
        sidebar_toggle.set_relief(Gtk.ReliefStyle.NONE)
        sidebar_toggle.get_style_context().add_class("sidebar-toggle")
        sidebar_toggle.connect("clicked", self._on_sidebar_toggle_clicked)
        self._sidebar_toggle_button = sidebar_toggle
        brand.pack_start(sidebar_toggle, False, False, 0)

        icon_label = Gtk.Label(label="✦")
        icon_label.get_style_context().add_class("brand-icon")
        brand.pack_start(icon_label, False, False, 0)

        title_label = Gtk.Label(label="Claude Code")
        title_label.get_style_context().add_class("brand-title")
        brand.pack_start(title_label, False, False, 0)

        header_row.pack_start(brand, False, False, 0)
        header_row.pack_start(Gtk.Box(), True, True, 0)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        minimize_button = self._make_window_control("—", self._on_minimize_clicked)
        maximize_button = self._make_window_control("□", self._on_maximize_clicked)
        close_button = self._make_window_control("✕", self._on_close_clicked, close=True)

        self._maximize_button = maximize_button

        controls.pack_start(minimize_button, False, False, 0)
        controls.pack_start(maximize_button, False, False, 0)
        controls.pack_start(close_button, False, False, 0)
        header_row.pack_end(controls, False, False, 0)

        self.set_titlebar(header_shell)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("app-root")
        self.add(root)

        content_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        content_row.get_style_context().add_class("content-row")
        root.pack_start(content_row, True, True, 0)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.get_style_context().add_class("sidebar")
        sidebar.set_size_request(self.SIDEBAR_OPEN_WIDTH, -1)
        sidebar.set_hexpand(False)
        sidebar.set_vexpand(True)
        self._sidebar_container = sidebar
        content_row.pack_start(sidebar, False, False, 0)

        project_title = Gtk.Label(label="Project")
        project_title.set_xalign(0.0)
        project_title.get_style_context().add_class("sidebar-title")
        sidebar.pack_start(project_title, False, False, 0)

        cwd_label = Gtk.Label(label=os.getcwd())
        cwd_label.set_xalign(0.0)
        cwd_label.set_line_wrap(True)
        cwd_label.get_style_context().add_class("sidebar-muted")
        sidebar.pack_start(cwd_label, False, False, 0)

        new_session_button = Gtk.Button(label="New Session")
        new_session_button.set_relief(Gtk.ReliefStyle.NONE)
        new_session_button.get_style_context().add_class("new-session-button")
        new_session_button.connect("clicked", self._on_new_session_clicked)
        sidebar.pack_start(new_session_button, False, False, 6)

        history_title = Gtk.Label(label="Session History")
        history_title.set_xalign(0.0)
        history_title.get_style_context().add_class("sidebar-title")
        sidebar.pack_start(history_title, False, False, 8)

        history_frame = Gtk.Frame()
        history_frame.set_shadow_type(Gtk.ShadowType.NONE)
        history_frame.get_style_context().add_class("history-frame")
        history_frame.set_hexpand(True)
        history_frame.set_vexpand(True)
        sidebar.pack_start(history_frame, True, True, 0)

        history_placeholder = Gtk.Label(label="No previous sessions yet")
        history_placeholder.set_xalign(0.0)
        history_placeholder.get_style_context().add_class("sidebar-muted")
        history_frame.add(history_placeholder)

        terminal_host = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        terminal_host.set_hexpand(True)
        terminal_host.set_vexpand(True)
        content_row.pack_start(terminal_host, True, True, 0)

        terminal_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        terminal_wrap.get_style_context().add_class("terminal-wrap")
        terminal_wrap.set_hexpand(True)
        terminal_wrap.set_vexpand(True)
        terminal_host.pack_start(terminal_wrap, True, True, 0)

        terminal_shell = Gtk.EventBox()
        terminal_shell.set_visible_window(True)
        terminal_shell.set_hexpand(True)
        terminal_shell.set_vexpand(True)
        terminal_shell.get_style_context().add_class("terminal-shell")
        self._terminal_shell = terminal_shell
        terminal_wrap.pack_start(terminal_shell, True, True, 0)

        self._terminal = Vte.Terminal()
        self._terminal.set_hexpand(True)
        self._terminal.set_vexpand(True)
        self._terminal.set_scrollback_lines(10000)
        self._terminal.set_scroll_on_keystroke(True)
        self._terminal.set_scroll_on_output(False)
        self._terminal.connect("child-exited", self._on_child_exited)
        self._terminal.connect("focus-in-event", self._on_terminal_focus_in)
        self._terminal.connect("focus-out-event", self._on_terminal_focus_out)
        terminal_shell.add(self._terminal)

        self._apply_terminal_colors()

        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_bar.get_style_context().add_class("status-bar")
        root.pack_end(status_bar, False, False, 0)

        connection_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        connection_dot = Gtk.Label(label="●")
        connection_dot.get_style_context().add_class("connection-dot")
        connection_text = Gtk.Label(label="Connected")
        connection_text.get_style_context().add_class("status-text")
        connection_box.pack_start(connection_dot, False, False, 0)
        connection_box.pack_start(connection_text, False, False, 0)
        status_bar.pack_start(connection_box, False, False, 0)
        self._connection_dot = connection_dot
        self._connection_label = connection_text

        model_label = Gtk.Label(label="Claude Opus 4.6")
        model_label.get_style_context().add_class("status-text")
        status_bar.pack_start(model_label, False, False, 0)

        status_label = Gtk.Label(label="Starting Claude Code...")
        status_label.set_xalign(0.0)
        status_label.get_style_context().add_class("status-muted")
        status_bar.pack_start(status_label, True, True, 0)
        self._status_label = status_label

        timer_label = Gtk.Label(label="00:00:00")
        timer_label.get_style_context().add_class("status-muted")
        status_bar.pack_end(timer_label, False, False, 0)
        self._session_timer_label = timer_label

        self._status_fade_widgets = [
            status_bar,
            connection_box,
            connection_dot,
            connection_text,
            model_label,
            status_label,
            timer_label,
        ]
        for widget in self._status_fade_widgets:
            widget.set_opacity(0.0)

        GLib.timeout_add_seconds(1, self._update_session_timer)

    def _make_window_control(
        self,
        label: str,
        callback: callable,
        close: bool = False,
    ) -> Gtk.Button:
        button = Gtk.Button(label=label)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class("control-button")
        if close:
            button.get_style_context().add_class("control-close")
        button.connect("clicked", callback)
        return button

    def _apply_terminal_colors(self) -> None:
        if self._terminal is None:
            return

        foreground = self._rgba(self.FOREGROUND)
        background = self._rgba(self.TERMINAL_BG)
        accent = self._rgba(self.ACCENT)
        selection_bg = self._rgba(self.SELECTION_BG)

        self._terminal.set_color_foreground(foreground)
        self._terminal.set_color_background(background)
        self._terminal.set_color_bold(foreground)
        self._terminal.set_color_cursor(accent)
        self._terminal.set_color_cursor_foreground(background)
        self._terminal.set_color_highlight(selection_bg)
        self._terminal.set_color_highlight_foreground(foreground)

    @staticmethod
    def _rgba(hex_color: str) -> Gdk.RGBA:
        rgba = Gdk.RGBA()
        if not rgba.parse(hex_color):
            rgba.parse("#ffffff")
        return rgba

    def _set_status(self, message: str) -> None:
        if self._status_label is not None and self._status_label.get_parent() is not None:
            self._status_label.set_text(message)

    def _set_connection_status(self, connected: bool) -> None:
        if self._connection_label is not None:
            self._connection_label.set_text("Connected" if connected else "Disconnected")

        if self._connection_dot is None:
            return

        style = self._connection_dot.get_style_context()
        if connected:
            style.remove_class("disconnected")
        else:
            style.add_class("disconnected")

    def _on_new_session_clicked(self, _button: Gtk.Button) -> None:
        self._set_status("New session placeholder")

    def _on_sidebar_toggle_clicked(self, _button: Gtk.Button) -> None:
        target_width = 0 if self._sidebar_expanded else self.SIDEBAR_OPEN_WIDTH
        self._sidebar_expanded = not self._sidebar_expanded

        if self._sidebar_toggle_button is not None:
            self._sidebar_toggle_button.set_label("◀" if self._sidebar_expanded else "▶")

        self._animate_sidebar(target_width)

    def _animate_sidebar(self, target_width: int) -> None:
        if self._sidebar_container is None:
            return

        if self._sidebar_animation_id is not None:
            GLib.source_remove(self._sidebar_animation_id)
            self._sidebar_animation_id = None

        start_width = self._sidebar_current_width
        delta = float(target_width) - start_width
        duration_ms = 220.0
        start_time_us = GLib.get_monotonic_time()

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = min(elapsed_ms / duration_ms, 1.0)
            eased = 1.0 - (1.0 - progress) ** 3
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

        clamped = max(0.0, min(float(self.SIDEBAR_OPEN_WIDTH), width))
        self._sidebar_current_width = clamped
        self._sidebar_container.set_size_request(int(clamped), -1)
        self._sidebar_container.set_opacity(clamped / float(self.SIDEBAR_OPEN_WIDTH))

    def _on_terminal_focus_in(self, _terminal: Vte.Terminal, _event: Gdk.EventFocus) -> bool:
        if self._terminal_shell is not None:
            self._terminal_shell.get_style_context().add_class("terminal-focused")
        return False

    def _on_terminal_focus_out(self, _terminal: Vte.Terminal, _event: Gdk.EventFocus) -> bool:
        if self._terminal_shell is not None:
            self._terminal_shell.get_style_context().remove_class("terminal-focused")
        return False

    def _on_header_button_press(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        return False

    def _on_minimize_clicked(self, _button: Gtk.Button) -> None:
        self.iconify()

    def _on_maximize_clicked(self, _button: Gtk.Button) -> None:
        if self._window_is_maximized:
            self.unmaximize()
        else:
            self.maximize()

    def _on_close_clicked(self, _button: Gtk.Button) -> None:
        self.close()

    def _on_window_state_event(self, _widget: Gtk.Window, event: Gdk.EventWindowState) -> bool:
        self._window_is_maximized = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        if self._maximize_button is not None:
            self._maximize_button.set_label("❐" if self._window_is_maximized else "□")
        return False

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
        duration_ms = 260.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = min(elapsed_ms / duration_ms, 1.0)
            eased = 1.0 - (1.0 - progress) ** 3
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
        duration_ms = 320.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = min(elapsed_ms / duration_ms, 1.0)
            eased = 1.0 - (1.0 - progress) ** 3
            for widget in self._status_fade_widgets:
                widget.set_opacity(eased)

            if progress >= 1.0:
                self._status_fade_animation_id = None
                return False
            return True

        self._status_fade_animation_id = GLib.timeout_add(16, tick)

    def _update_session_timer(self) -> bool:
        if self._session_timer_label is None:
            return False

        elapsed_seconds = max(0, (GLib.get_monotonic_time() - self._session_started_us) // 1_000_000)
        hours = elapsed_seconds // 3600
        minutes = (elapsed_seconds % 3600) // 60
        seconds = elapsed_seconds % 60
        self._session_timer_label.set_text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return True

    @staticmethod
    def _find_claude_binary() -> str | None:
        for executable in ("claude", "claude-code"):
            found = shutil.which(executable)
            if found:
                return found

        config_root = Path.home() / ".config" / "Claude" / "claude-code"
        candidates = (
            config_root / "claude",
            config_root / "claude-code",
            config_root / "bin" / "claude",
            config_root / "bin" / "claude-code",
        )
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)

        if config_root.is_dir():
            for binary_name in ("claude", "claude-code"):
                for candidate in config_root.rglob(binary_name):
                    if candidate.is_file() and os.access(candidate, os.X_OK):
                        return str(candidate)

        return None

    def _launch_claude(self, binary_path: str) -> None:
        if self._terminal is None:
            return

        working_dir = os.getcwd()
        argv = [binary_path]
        envv = [f"{key}={value}" for key, value in os.environ.items()]

        try:
            _, child_pid = self._terminal.spawn_sync(
                Vte.PtyFlags.DEFAULT,
                working_dir,
                argv,
                envv,
                GLib.SpawnFlags.DEFAULT,
                None,
                None,
                None,
            )
        except GLib.Error as error:
            self._set_connection_status(False)
            self._set_status(f"Failed to start Claude Code: {error.message}")
            self._write_terminal_notice(
                "Failed to start Claude Code.\r\n"
                f"Command: {binary_path}\r\n"
                f"Error: {error.message}\r\n"
            )
            self._start_status_fade_in()
            return

        self._child_pid = child_pid
        self._set_connection_status(True)
        self._set_status(f"Running {Path(binary_path).name} in {working_dir}")
        GLib.timeout_add(120, self._trigger_status_fade)

    def _trigger_status_fade(self) -> bool:
        self._start_status_fade_in()
        return False

    def _show_missing_binary_error(self) -> None:
        self._set_status("Claude CLI not found")
        self._write_terminal_notice(
            "Claude Code CLI was not found.\r\n\r\n"
            "Searched for: claude, claude-code, and ~/.config/Claude/claude-code/*\r\n"
            "Install Claude Code CLI or add it to your PATH, then restart this app.\r\n"
        )

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Claude CLI not found",
        )
        dialog.format_secondary_text(
            "Install Claude Code CLI (binary `claude` or `claude-code`) "
            "or place it under ~/.config/Claude/claude-code/."
        )
        dialog.run()
        dialog.destroy()

    def _write_terminal_notice(self, text: str) -> None:
        if self._terminal is not None:
            self._terminal.feed(text)

    def _on_child_exited(self, _terminal: Vte.Terminal, status: int) -> None:
        self._set_connection_status(False)
        self._set_status(f"Claude Code exited with status {status}")

    def _on_destroy(self, _widget: Gtk.Window) -> None:
        if self._sidebar_animation_id is not None:
            GLib.source_remove(self._sidebar_animation_id)
            self._sidebar_animation_id = None

        if self._status_fade_animation_id is not None:
            GLib.source_remove(self._status_fade_animation_id)
            self._status_fade_animation_id = None

        if self._window_fade_animation_id is not None:
            GLib.source_remove(self._window_fade_animation_id)
            self._window_fade_animation_id = None

        Gtk.main_quit()


def main() -> None:
    window = ClaudeCodeWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
