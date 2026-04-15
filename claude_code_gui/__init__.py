"""Claude Code GUI package."""

from __future__ import annotations

from typing import Any

__all__ = ["Gtk", "Gdk", "Gio", "GLib", "Pango", "WebKit", "GTK4", "WEBKIT6"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    # Keep GI runtime imports lazy so entrypoints can set runtime env vars first.
    from claude_code_gui import gi_runtime as _gi_runtime

    value = getattr(_gi_runtime, name)
    globals()[name] = value
    return value
