"""Entry point for python -m claude_code_gui."""

from __future__ import annotations

def main() -> None:
    from claude_code_gui.gi_runtime import Gtk, GTK4
    from claude_code_gui.ui.window import ClaudeCodeWindow

    window = ClaudeCodeWindow()
    if GTK4:
        window.present()
    else:
        window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
