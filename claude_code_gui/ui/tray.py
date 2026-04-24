"""System tray integration for Claude Code GUI using an out-of-process helper."""

from __future__ import annotations

import atexit
import json
import logging
import os
import subprocess
import sys
import threading
from typing import Any

from claude_code_gui.core.paths import resolve_icon_path

logger = logging.getLogger(__name__)

class TrayIcon:
    """System tray icon using out-of-process AyatanaAppIndicator3."""

    available: bool = False

    def __init__(
        self,
        app: Any,
        *,
        on_show: Any = None,
        on_new_pane: Any = None,
        on_quit: Any = None,
        icon_name: str = "",
        app_id: str = "claude-code-gui",
    ) -> None:
        self.app = app
        self._on_show = on_show
        self._on_new_pane = on_new_pane
        self._on_quit = on_quit
        self.available = False
        self._process = None
        self._lock = threading.Lock()
        resolved_icon_name = icon_name
        if not resolved_icon_name:
            icon_path = resolve_icon_path("claude.svg")
            resolved_icon_name = str(icon_path) if icon_path is not None else "claude.svg"

        try:
            cmd = [
                sys.executable,
                "-m",
                "claude_code_gui.ui._tray_helper",
                "--icon-name",
                resolved_icon_name,
            ]
            
            env = os.environ.copy()
            
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1, # Line buffered
            )

            # Start background thread to read events
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            
            atexit.register(self._cleanup)
        except Exception as e:
            logger.warning("Failed to initialize TrayIcon helper: %s", e)
            self.available = False

    def _cleanup(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                try:
                    if self._process.stdin:
                        self._process.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                        self._process.stdin.flush()
                    self._process.wait(timeout=1.0)
                except Exception:
                    self._process.terminate()

    def _read_loop(self) -> None:
        if not self._process or not self._process.stdout:
            return
            
        try:
            from gi.repository import GLib
        except ImportError:
            GLib = None
            
        for line in self._process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                event = msg.get("event")
                if event == "ready":
                    self.available = True
                    continue
                if msg.get("error"):
                    self.available = False
                    logger.warning("Tray helper reported initialization failure: %s", msg.get("error"))
                    return
                if event == "show":
                    if GLib and callable(self._on_show):
                        GLib.idle_add(self._on_show)
                    elif callable(self._on_show):
                        self._on_show()
                elif event == "new_pane":
                    if GLib and callable(self._on_new_pane):
                        GLib.idle_add(self._on_new_pane)
                    elif callable(self._on_new_pane):
                        self._on_new_pane()
                elif event == "quit":
                    if GLib and callable(self._on_quit):
                        GLib.idle_add(self._on_quit)
                    elif callable(self._on_quit):
                        self._on_quit()
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.debug("Error handling tray event: %s", e)

    def set_attention(self, active: bool) -> None:
        """Switch indicator status between ACTIVE and ATTENTION."""
        if not self.available:
            return
        with self._lock:
            if self._process and self._process.poll() is None and self._process.stdin:
                try:
                    msg = {"cmd": "set_attention", "active": active}
                    self._process.stdin.write(json.dumps(msg) + "\n")
                    self._process.stdin.flush()
                except Exception as e:
                    logger.debug("Failed to set indicator attention status: %s", e)
                    self.available = False
