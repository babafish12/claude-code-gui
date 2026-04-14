"""Shared design tokens for the Liquid Glass visual pass."""

from __future__ import annotations

from typing import Literal

GLASS_RADII = {
    "element": 12,
    "control": 16,
    "card": 20,
    "pill": 999,
}

GLASS_TINT_DARK = {
    "base": "rgba(255, 255, 255, 0.08)",
    "base_solid": "#3a3a34",
    "elevated": "rgba(255, 255, 255, 0.12)",
    "elevated_solid": "#3a3a34",
    "overlay": "rgba(255, 255, 255, 0.04)",
    "overlay_solid": "#3a3a34",
    "interactive": "rgba(255, 255, 255, 0.16)",
    "interactive_hover": "rgba(255, 255, 255, 0.23)",
    "interactive_solid": "#2f2f2a",
    "interactive_hover_solid": "#3a3a34",
}

GLASS_BLUR = {
    "interactive": 18,
    "surface": 24,
    "large": 36,
}

GLASS_BORDER_HIGHLIGHT = "rgba(255, 255, 255, 0.22)"
GLASS_BORDER_HIGHLIGHT_INSET = "rgba(255, 255, 255, 0.08)"

GLASS_SPECULAR_GRADIENT = (
    "linear-gradient(180deg, rgba(255,255,255,0.32) 0%, rgba(255,255,255,0.0) 45%)"
)

GLASS_SHADOWS = {
    "rest": "0 10px 24px rgba(0, 0, 0, 0.28)",
    "hover": "0 12px 28px rgba(0, 0, 0, 0.34)",
    "press": "0 8px 20px rgba(0, 0, 0, 0.34)",
}

GLASS_SPRING_CSS = {
    "press": "cubic-bezier(0.34, 1.56, 0.64, 1)",
    "hover": "cubic-bezier(0.2, 0.9, 0.3, 1)",
    "standard": "cubic-bezier(0.4, 0, 0.2, 1)",
}

GLASS_SPRING_MOTION_ONE = {"stiffness": 200, "damping": 24, "mass": 1}

GLASS_DURATIONS = {"press": 180, "hover": 220, "enter": 320, "exit": 260}


def glass_css_variables_block(theme: Literal["dark"] = "dark") -> str:
    """Return the WebKit-only CSS variable block.

    Light theme is intentionally not supported in this iteration and is kept as a
    signature-compatible guard only.
    """
    if theme != "dark":
        theme = "dark"

    return (
        ":root {{"
        "\n    --glass-radius-element: {element}px;"
        "\n    --glass-radius-control: {control}px;"
        "\n    --glass-radius-card: {card}px;"
        "\n    --glass-radius-pill: {pill}px;"
        "\n    --glass-tint-base: {tint_base};"
        "\n    --glass-tint-base-solid: {tint_base_solid};"
        "\n    --glass-tint-elevated: {tint_elevated};"
        "\n    --glass-tint-elevated-solid: {tint_elevated_solid};"
        "\n    --glass-tint-overlay: {tint_overlay};"
        "\n    --glass-tint-overlay-solid: {tint_overlay_solid};"
        "\n    --glass-tint-interactive: {tint_interactive};"
        "\n    --glass-tint-interactive-hover: {tint_interactive_hover};"
        "\n    --glass-tint-interactive-solid: {tint_interactive_solid};"
        "\n    --glass-tint-interactive-hover-solid: {tint_interactive_hover_solid};"
        "\n    --glass-blur-interactive: {blur_interactive}px;"
        "\n    --glass-blur-surface: {blur_surface}px;"
        "\n    --glass-blur-large: {blur_large}px;"
        "\n    --glass-border-highlight: {border_highlight};"
        "\n    --glass-border-highlight-inset: {border_highlight_inset};"
        "\n    --glass-specular-gradient: {specular};"
        "\n    --glass-shadow-rest: {shadow_rest};"
        "\n    --glass-shadow-hover: {shadow_hover};"
        "\n    --glass-shadow-press: {shadow_press};"
        "\n    --glass-spring-press: {spring_press};"
        "\n    --glass-spring-hover: {spring_hover};"
        "\n    --glass-spring-standard: {spring_standard};"
        "\n    --glass-spring-press-stiffness: {motion_stiffness};"
        "\n    --glass-spring-press-damping: {motion_damping};"
        "\n    --glass-spring-press-mass: {motion_mass};"
        "\n    --glass-duration-press: {dur_press}ms;"
        "\n    --glass-duration-hover: {dur_hover}ms;"
        "\n    --glass-duration-enter: {dur_enter}ms;"
        "\n    --glass-duration-exit: {dur_exit}ms;"
        "\n    --motion-press: 180ms;"
        "\n    --motion-hover: 220ms;"
        "\n}}"
    ).format(
        element=GLASS_RADII["element"],
        control=GLASS_RADII["control"],
        card=GLASS_RADII["card"],
        pill=GLASS_RADII["pill"],
        tint_base=GLASS_TINT_DARK["base"],
        tint_base_solid=GLASS_TINT_DARK["base_solid"],
        tint_elevated=GLASS_TINT_DARK["elevated"],
        tint_elevated_solid=GLASS_TINT_DARK["elevated_solid"],
        tint_overlay=GLASS_TINT_DARK["overlay"],
        tint_overlay_solid=GLASS_TINT_DARK["overlay_solid"],
        tint_interactive=GLASS_TINT_DARK["interactive"],
        tint_interactive_hover=GLASS_TINT_DARK["interactive_hover"],
        tint_interactive_solid=GLASS_TINT_DARK["interactive_solid"],
        tint_interactive_hover_solid=GLASS_TINT_DARK["interactive_hover_solid"],
        blur_interactive=GLASS_BLUR["interactive"],
        blur_surface=GLASS_BLUR["surface"],
        blur_large=GLASS_BLUR["large"],
        border_highlight=GLASS_BORDER_HIGHLIGHT,
        border_highlight_inset=GLASS_BORDER_HIGHLIGHT_INSET,
        specular=GLASS_SPECULAR_GRADIENT,
        shadow_rest=GLASS_SHADOWS["rest"],
        shadow_hover=GLASS_SHADOWS["hover"],
        shadow_press=GLASS_SHADOWS["press"],
        spring_press=GLASS_SPRING_CSS["press"],
        spring_hover=GLASS_SPRING_CSS["hover"],
        spring_standard=GLASS_SPRING_CSS["standard"],
        motion_stiffness=GLASS_SPRING_MOTION_ONE["stiffness"],
        motion_damping=GLASS_SPRING_MOTION_ONE["damping"],
        motion_mass=GLASS_SPRING_MOTION_ONE["mass"],
        dur_press=GLASS_DURATIONS["press"],
        dur_hover=GLASS_DURATIONS["hover"],
        dur_enter=GLASS_DURATIONS["enter"],
        dur_exit=GLASS_DURATIONS["exit"],
    )


def glass_gtk_define_colors() -> str:
    return (
        "@define-color glass_tint_base {};\n"
        "@define-color glass_tint_base_solid {};\n"
        "@define-color glass_tint_elevated {};\n"
        "@define-color glass_tint_elevated_solid {};\n"
        "@define-color glass_tint_overlay {};\n"
        "@define-color glass_tint_overlay_solid {};\n"
        "@define-color glass_tint_interactive {};\n"
        "@define-color glass_tint_interactive_hover {};\n"
        "@define-color glass_tint_interactive_solid {};\n"
        "@define-color glass_tint_interactive_hover_solid {};\n"
        "@define-color glass_border_highlight {};\n"
        "@define-color glass_border_highlight_inset {};\n"
        "@define-color glass_specular_top rgba(255, 255, 255, 0.22);\n"
        "@define-color glass_specular_top_hover rgba(255, 255, 255, 0.32);\n"
        "@define-color glass_specular_fade rgba(255, 255, 255, 0.0);\n"
    ).format(
        GLASS_TINT_DARK["base"],
        GLASS_TINT_DARK["base_solid"],
        GLASS_TINT_DARK["elevated"],
        GLASS_TINT_DARK["elevated_solid"],
        GLASS_TINT_DARK["overlay"],
        GLASS_TINT_DARK["overlay_solid"],
        GLASS_TINT_DARK["interactive"],
        GLASS_TINT_DARK["interactive_hover"],
        GLASS_TINT_DARK["interactive_solid"],
        GLASS_TINT_DARK["interactive_hover_solid"],
        GLASS_BORDER_HIGHLIGHT,
        GLASS_BORDER_HIGHLIGHT_INSET,
    )
