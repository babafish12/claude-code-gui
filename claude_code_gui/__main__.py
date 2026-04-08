"""Entry point for python -m claude_code_gui."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
try:
    gi.require_version("WebKit2", "4.1")
except ValueError:
    gi.require_version("WebKit2", "4.0")

from gi.repository import Gtk

from claude_code_gui.ui.window import ClaudeCodeWindow


def main() -> None:
    window = ClaudeCodeWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
