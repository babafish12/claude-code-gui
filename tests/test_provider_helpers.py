from __future__ import annotations

import copy

import pytest

from claude_code_gui.domain.app_settings import load_settings
from claude_code_gui.domain import provider

pytestmark = pytest.mark.unit


def test_coerce_rgb_and_text_helpers() -> None:
    assert provider._coerce_rgb(["1", 2, 3], fallback=(9, 9, 9)) == (1, 2, 3)
    assert provider._coerce_rgb([300, 2, 3], fallback=(9, 9, 9)) == (9, 9, 9)
    assert provider._coerce_rgb("bad", fallback=(9, 9, 9)) == (9, 9, 9)

    assert provider._coerce_text("  value  ", fallback="fallback") == "value"
    assert provider._coerce_text("   ", fallback="fallback") == "fallback"
    assert provider._coerce_text(123, fallback="fallback") == "fallback"


def test_model_option_coercion_and_dedupe() -> None:
    fallback = (("Fallback", "fallback"),)
    raw = [
        ["Label A", "model-a"],
        {"label": "Label B", "value": "model-b"},
        "model-c",
    ]
    coerced = provider._coerce_model_options(raw, fallback=fallback)
    assert coerced == (
        ("Label A", "model-a"),
        ("Label B", "model-b"),
        ("model-c", "model-c"),
    )

    discovered = provider._coerce_discovered_model_options(
        [
            ("Model A", "model-a"),
            {"value": "model-a", "label": "Duplicate"},
            {"value": "model-b", "title": "Model B"},
            "model-c",
        ]
    )
    assert discovered == (
        ("Model A", "model-a"),
        ("Model B", "model-b"),
        ("model-c", "model-c"),
    )

    merged = provider._merge_model_options(
        discovered=(("Discovered", "model-d"), ("Duplicate", "model-a")),
        configured=(("Configured", "model-a"), ("Configured 2", "model-e")),
    )
    assert merged == (
        ("Discovered", "model-d"),
        ("Duplicate", "model-a"),
        ("Configured 2", "model-e"),
    )


def test_discovered_model_overrides_and_permission_coercion() -> None:
    normalized = provider._normalize_discovered_model_overrides(
        {
            " CODEX ": [{"label": "GPT-5", "value": "gpt-5"}],
            "": [{"value": "ignored"}],
            1: [{"value": "ignored"}],
            "claude": "invalid",
        }
    )
    assert normalized == {"codex": (("GPT-5", "gpt-5"),)}

    permissions = provider._coerce_permission_options(
        [
            ("Auto", "auto", False),
            {"label": "Plan", "value": "plan", "is_advanced": True},
            "ask",
        ]
    )
    assert permissions == (
        ("Auto", "auto", False),
        ("Plan", "plan", True),
        ("ask", "ask", False),
    )


def test_provider_color_and_icon_normalization() -> None:
    fallback_colors = {"accent": "#111111"}
    colors = provider._coerce_provider_colors(
        {"accent": "#222222", "muted": "  #333333  ", 1: "ignored"},
        fallback=fallback_colors,
    )
    assert colors["accent"] == "#222222"
    assert colors["muted"] == "#333333"

    claude = provider._coerce_provider(
        payload={"id": "claude", "name": "Claude", "icon": "claude-text.svg"},
        provider_id="claude",
        discovered_models={},
    )
    codex = provider._coerce_provider(
        payload={"id": "codex", "name": "Codex", "icon": "⌘"},
        provider_id="codex",
        discovered_models={},
    )
    gemini = provider._coerce_provider(
        payload={"id": "gemini", "name": "Gemini", "icon": "gemini.svg"},
        provider_id="gemini",
        discovered_models={},
    )

    assert claude.icon == "claude-color.svg"
    assert codex.icon == "codex-white.svg"
    assert gemini.icon == "gemini-color.svg"


def test_refresh_provider_registry_applies_discovered_models() -> None:
    original_discovered = copy.deepcopy(provider._DISCOVERED_MODEL_OPTIONS)
    try:
        refreshed = provider.refresh_provider_registry(
            payload=None,
            detected_model_options={"codex": [{"label": "Custom GPT", "value": "gpt-custom"}]},
        )
        codex_values = [value for _, value in refreshed["codex"].model_options]
        assert "gpt-custom" in codex_values
    finally:
        provider._DISCOVERED_MODEL_OPTIONS.clear()
        provider._DISCOVERED_MODEL_OPTIONS.update(original_discovered)
        provider.refresh_provider_registry(load_settings())
