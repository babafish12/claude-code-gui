"""Entry point for python -m claude_code_gui."""

from __future__ import annotations

def main() -> None:
    import sys
    import argparse
    from claude_code_gui import gi_runtime
    from claude_code_gui.ui.window import ClaudeCodeWindow

    Gtk = gi_runtime.Gtk
    Adw = gi_runtime.Adw
    GTK4 = gi_runtime.GTK4
    Gio = gi_runtime.Gio
    option_types = getattr(gi_runtime, "GLib", Gio)

    parser = argparse.ArgumentParser(description="Claude Code GUI")
    parser.add_argument("--toggle-launcher", action="store_true", help="Toggle the launcher window via DBus")
    args, unknown = parser.parse_known_args()

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
        app.run(sys.argv)
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
