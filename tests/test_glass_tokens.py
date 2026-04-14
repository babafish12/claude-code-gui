"""Tests for shared glass token module."""

from __future__ import annotations

from claude_code_gui.assets.glass_tokens import (
    GLASS_BLUR,
    GLASS_DURATIONS,
    GLASS_RADII,
    GLASS_SHADOWS,
    GLASS_SPRING_CSS,
    GLASS_SPRING_MOTION_ONE,
    GLASS_TINT_DARK,
    glass_css_variables_block,
    glass_gtk_define_colors,
)


def test_glass_groups_are_populated() -> None:
    assert isinstance(GLASS_RADII, dict) and GLASS_RADII
    assert isinstance(GLASS_TINT_DARK, dict) and GLASS_TINT_DARK
    assert isinstance(GLASS_BLUR, dict) and GLASS_BLUR
    assert isinstance(GLASS_SHADOWS, dict) and GLASS_SHADOWS
    assert isinstance(GLASS_SPRING_CSS, dict) and GLASS_SPRING_CSS


def test_glass_token_values_have_expected_types() -> None:
    for values in (GLASS_RADII, GLASS_BLUR, GLASS_DURATIONS):
        for value in values.values():
            assert isinstance(value, int)

    for values in (GLASS_TINT_DARK, GLASS_SHADOWS, GLASS_SPRING_CSS):
        for value in values.values():
            assert isinstance(value, str)
            assert value

    for key in ("stiffness", "damping", "mass"):
        assert isinstance(GLASS_SPRING_MOTION_ONE[key], (int, float))


def test_glass_css_variable_block_includes_key_tokens() -> None:
    block = glass_css_variables_block("dark")
    assert block.startswith(":root {")
    assert "--glass-tint-elevated" in block
    assert "--glass-spring-press" in block
    assert "--glass-duration-press" in block


def test_glass_define_colors_has_gtk_prefix() -> None:
    define_block = glass_gtk_define_colors()
    assert define_block.startswith("@define-color glass_")
    assert "var(--" not in define_block
    assert "glass_tint_interactive" in define_block


def test_glass_css_variables_block_rejects_unknown_theme() -> None:
    assert glass_css_variables_block("light") == glass_css_variables_block("dark")
