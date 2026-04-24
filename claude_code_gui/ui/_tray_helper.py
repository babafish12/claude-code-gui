"""Out-of-process helper for system tray indicator.

This script runs in its own process, enforcing GTK 3.0 so that
AyatanaAppIndicator3 can be loaded without conflicting with the main
application's GTK 4.0 usage.
"""

import argparse
import json
import sys
import threading
from typing import Any

AyatanaAppIndicator3 = None
GLib = None
Gtk = None


class TrayHelper:
    def __init__(self, icon_name: str) -> None:
        self.icon_name = icon_name
        self.indicator = None

        category = getattr(AyatanaAppIndicator3.IndicatorCategory, "APPLICATION_STATUS", 0)
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "claude-code-gui",
            icon_name,
            category,
        )
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)

        menu = Gtk.Menu()

        item_show = Gtk.MenuItem.new_with_label("Show Window")
        item_show.connect("activate", self._on_show)
        menu.append(item_show)

        item_new_pane = Gtk.MenuItem.new_with_label("New Pane")
        item_new_pane.connect("activate", self._on_new_pane)
        menu.append(item_new_pane)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem.new_with_label("Quit")
        item_quit.connect("activate", self._on_quit)
        menu.append(item_quit)

        menu.show_all()
        self.indicator.set_menu(menu)
        self._send_event("ready")

    def _on_show(self, _widget: Any) -> None:
        self._send_event("show")

    def _on_new_pane(self, _widget: Any) -> None:
        self._send_event("new_pane")

    def _on_quit(self, _widget: Any) -> None:
        self._send_event("quit")
        GLib.idle_add(Gtk.main_quit)

    def _send_event(self, event: str) -> None:
        print(json.dumps({"event": event}), flush=True)

    def _handle_command(self, cmd: str, data: dict[str, Any]) -> None:
        if cmd == "set_attention":
            active = data.get("active", False)
            if active:
                self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ATTENTION)
            else:
                self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        elif cmd == "quit":
            Gtk.main_quit()

    def run_stdin_loop(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                cmd = msg.get("cmd")
                if cmd:
                    GLib.idle_add(self._handle_command, cmd, msg)
            except json.JSONDecodeError:
                pass
        GLib.idle_add(Gtk.main_quit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Claude Code GUI Tray Helper")
    parser.add_argument("--icon-name", default="", help="Absolute icon path for the tray")
    args = parser.parse_args()

    global AyatanaAppIndicator3, GLib, Gtk
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as _AyatanaAppIndicator3
        from gi.repository import GLib as _GLib
        from gi.repository import Gtk as _Gtk

        AyatanaAppIndicator3 = _AyatanaAppIndicator3
        GLib = _GLib
        Gtk = _Gtk
    except (ImportError, ValueError, AttributeError) as error:
        print(json.dumps({"error": str(error)}), flush=True)
        sys.exit(1)

    try:
        helper = TrayHelper(args.icon_name)
    except Exception as e:
        print(json.dumps({"error": str(e)}), flush=True)
        sys.exit(1)

    # Start stdin reader thread
    thread = threading.Thread(target=helper.run_stdin_loop, daemon=True)
    thread.start()

    Gtk.main()


if __name__ == "__main__":
    main()
