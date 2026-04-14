"""Web-specific glass token injection helpers."""

from __future__ import annotations

from typing import Literal

from claude_code_gui.assets.glass_tokens import (
    glass_css_variables_block,
)


def glass_tokens_style_block(theme: Literal["dark"] = "dark") -> str:
    """Return a full `<style>...</style>` snippet for template insertion."""
    return f"\n<style>\n{glass_css_variables_block(theme)}\n</style>\n"
