from __future__ import annotations

import pytest

from claude_code_gui.assets.gtk_css import CSS_STYLES, build_gtk_css
from claude_code_gui.assets.glass_tokens import glass_gtk_define_colors, GLASS_SPRING_CSS
from claude_code_gui.domain.provider import PROVIDERS

pytestmark = pytest.mark.gtk_css


def test_glass_define_colors_prelude_is_present() -> None:
    generated = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
    )

    prelude = glass_gtk_define_colors()
    assert "@define-color glass_" in generated
    assert prelude.strip() in generated
    start = generated.find(prelude)
    assert start != -1
    assert "var(--" not in generated[start : start + len(prelude)]


def test_glass_bezier_present() -> None:
    generated = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
    )
    assert GLASS_SPRING_CSS["press"] in generated


def test_reduced_motion_kwarg_disables_transitions() -> None:
    generated = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
        reduced_motion=True,
    )

    assert "transition:" in generated
    assert " 0ms " in generated


def test_phase3_button_rules_have_no_raw_rgba_outside_prelude() -> None:
    generated = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
    )
    start = generated.find("/* GLASS-PHASE3-START */")
    end = generated.find("/* GLASS-PHASE3-END */")
    assert start != -1 and end != -1 and end > start
    phase_block = generated[start:end]
    assert "var(--" not in phase_block


def test_claude_css_is_byte_identical() -> None:
    generated = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
    )

    assert CSS_STYLES.encode("utf-8") == generated.encode("utf-8")
