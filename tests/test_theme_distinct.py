from __future__ import annotations

import pytest

from claude_code_gui.assets.gtk_css import build_gtk_css
from claude_code_gui.domain.provider import PROVIDERS

pytestmark = pytest.mark.gtk_css


def test_codex_theme_css_differs_from_claude() -> None:
    claude_css = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
    )
    codex_css = build_gtk_css(
        PROVIDERS["codex"].colors,
        PROVIDERS["codex"].accent_rgb,
        PROVIDERS["codex"].accent_soft_rgb,
    )

    assert codex_css != claude_css
    assert PROVIDERS["claude"].colors["accent"] in claude_css
    assert PROVIDERS["codex"].colors["accent"] in codex_css


def test_gemini_theme_css_differs_from_claude_and_codex() -> None:
    claude_css = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
    )
    codex_css = build_gtk_css(
        PROVIDERS["codex"].colors,
        PROVIDERS["codex"].accent_rgb,
        PROVIDERS["codex"].accent_soft_rgb,
    )
    gemini_css = build_gtk_css(
        PROVIDERS["gemini"].colors,
        PROVIDERS["gemini"].accent_rgb,
        PROVIDERS["gemini"].accent_soft_rgb,
    )

    assert gemini_css != claude_css
    assert gemini_css != codex_css
    assert PROVIDERS["gemini"].colors["accent"] in gemini_css
