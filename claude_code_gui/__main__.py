"""Entry point for python -m claude_code_gui."""

from __future__ import annotations

import argparse
import importlib
import sys


def main(argv: list[str] | None = None) -> None:
    from claude_code_gui.core.paths import resolve_icon_path

    try:
        gi_runtime = importlib.import_module("claude_code_gui.gi_runtime")
    except ModuleNotFoundError as error:
        if error.name == "gi":
            print(
                "Could not import PyGObject (`gi`). Install python3-gi and run from "
                "system Python or create the venv with --system-site-packages.",
                file=sys.stderr,
            )
            sys.exit(1)
        raise
    window_module = importlib.import_module("claude_code_gui.ui.window")
    tray_module = importlib.import_module("claude_code_gui.ui.tray")
    settings_module = importlib.import_module("claude_code_gui.domain.app_settings")

    ClaudeCodeWindow = window_module.ClaudeCodeWindow
    TrayIcon = tray_module.TrayIcon
    load_settings = settings_module.load_settings

    Gtk = gi_runtime.Gtk
    Adw = gi_runtime.Adw
    GTK4 = gi_runtime.GTK4
    Gio = gi_runtime.Gio
    option_types = getattr(gi_runtime, "GLib", Gio)
    argv = list(sys.argv if argv is None else argv)
    tray_icon_path = resolve_icon_path("claude.svg")

    parser = argparse.ArgumentParser(description="Claude Code GUI")
    parser.add_argument("--toggle-launcher", action="store_true", help="Toggle the launcher window via DBus")
    args, _unknown = parser.parse_known_args(argv[1:])
    app_argv = [argv[0]]
    if args.toggle_launcher:
        app_argv.append("--toggle-launcher")

    if GTK4 and Adw:
        app = Adw.Application(
            application_id="com.vube.ClaudeCodeGui",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        def on_activate(app):
            # Check if window already exists
            for win in app.get_windows():
                if isinstance(win, ClaudeCodeWindow):
                    win.present()
                    return
            win = ClaudeCodeWindow(application=app)
            win.present()
            settings_payload = load_settings()
            if bool(settings_payload.get("system_tray_enabled", True)):
                app._tray = TrayIcon(
                    app,
                    on_show=win.present,
                    on_new_pane=lambda: win._split_active_pane(Gtk.Orientation.HORIZONTAL),
                    on_quit=getattr(app, "quit", None),
                    icon_name=str(tray_icon_path) if tray_icon_path is not None else "",
                )

        app.add_main_option(
            "toggle-launcher",
            ord("t"),
            option_types.OptionFlags.NONE,
            option_types.OptionArg.NONE,
            "Toggle the launcher window",
            None
        )

        def on_handle_local_options(app, options):
            if options.contains("toggle-launcher"):
                app.register(None)
                app.activate()
                # Find the window and toggle it
                for win in app.get_windows():
                    if isinstance(win, ClaudeCodeWindow):
                        if win.is_visible():
                            win.set_visible(False)
                        else:
                            win.present()
                return 0
            return -1

        app.connect("handle-local-options", on_handle_local_options)
        app.connect("activate", on_activate)
        app.run(app_argv)
    else:
        if args.toggle_launcher:
            print("Toggle launcher requires GTK4 and Libadwaita.")
            sys.exit(1)
        window = ClaudeCodeWindow()
        if GTK4:
            window.present()
        else:
            window.show_all()
        Gtk.main()


if __name__ == "__main__":
    main()
