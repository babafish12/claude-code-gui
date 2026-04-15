from __future__ import annotations

import copy
import json

import pytest

from claude_code_gui.domain import app_settings

pytestmark = pytest.mark.unit


def test_basic_coercion_helpers() -> None:
    assert app_settings._to_lower_str("  Codex ") == "codex"
    assert app_settings._to_lower_str(1) == ""

    assert app_settings._to_bool("yes", False) is True
    assert app_settings._to_bool("off", True) is False
    assert app_settings._to_bool("unknown", True) is True

    assert app_settings._to_int("12.9", 0) == 12
    assert app_settings._to_int(True, 0) == 1
    assert app_settings._to_int("bad", 9) == 9

    assert app_settings._to_int_range(5000, 80, minimum=0, maximum=1500) == 1500
    assert app_settings._to_int_range(-5, 80, minimum=0, maximum=1500) == 0

    assert app_settings._to_rgb(["1", 2, 3], (9, 9, 9)) == (1, 2, 3)
    assert app_settings._to_rgb(["1", 2, 999], (9, 9, 9)) == (9, 9, 9)

    assert app_settings._to_string_list(["a", "", " b "], ["fallback"]) == ["a", "b"]
    assert app_settings._to_string_list("bad", ["fallback"]) == ["fallback"]


def test_option_and_reasoning_normalization() -> None:
    assert app_settings._to_option_entry(["Label", "value"], fallback_label="X", fallback_value="Y") == (
        "Label",
        "value",
    )
    assert app_settings._to_option_entry({"title": "T", "value": "v"}, fallback_label="X", fallback_value="Y") == (
        "T",
        "v",
    )
    assert app_settings._to_option_entry("raw", fallback_label="X", fallback_value="Y") == ("raw", "raw")

    model_options = app_settings._to_model_options(
        [
            {"label": "A", "value": "a"},
            ("B", "b"),
            "c",
        ],
        fallback=[{"label": "Fallback", "value": "fallback"}],
    )
    assert [entry["value"] for entry in model_options] == ["a", "b", "c"]

    permission_options = app_settings._to_permission_options(
        [
            ("Auto", "auto", False),
            {"label": "Plan", "value": "plan", "is_advanced": True},
            "ask",
        ],
        fallback=[{"label": "Fallback", "value": "auto", "is_advanced": False}],
    )
    assert permission_options[0]["value"] == "auto"
    assert permission_options[1]["is_advanced"] is True
    assert permission_options[2]["value"] == "ask"

    reasoning_options = app_settings._to_reasoning_options(
        [
            ("Low", "low", "fast"),
            {"title": "High", "value": "high", "description": "deep"},
            "medium",
        ],
        fallback=[{"title": "Fallback", "value": "medium", "description": "x"}],
    )
    assert [entry["value"] for entry in reasoning_options] == ["low", "high", "medium"]


def test_theme_payload_loading_and_merging(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    theme_file = tmp_path / "provider_theme_settings.json"
    theme_file.write_text(
        json.dumps(
            {
                "providers": {
                    " CODEX ": {
                        "colors": {"accent": "#00ffaa"},
                        "accent_rgb": [1, 2, 3],
                    },
                    "invalid": "ignored",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(app_settings, "APP_THEME_SETTINGS_PATH", theme_file)
    loaded_theme = app_settings._load_provider_theme_settings()
    assert "codex" in loaded_theme
    assert "invalid" not in loaded_theme

    base = {
        "providers": {
            "codex": {"colors": {"accent": "#111111"}, "accent_rgb": [9, 9, 9]},
            "claude": {"colors": {"accent": "#222222"}},
        }
    }
    merged = app_settings._merge_provider_theme_defaults(base, loaded_theme)
    assert merged["providers"]["codex"]["colors"]["accent"] == "#00ffaa"
    assert merged["providers"]["claude"]["colors"]["accent"] == "#222222"


def test_normalize_provider_and_settings_icon_and_provider_selection() -> None:
    fallback_provider = copy.deepcopy(app_settings.DEFAULT_APP_SETTINGS["providers"]["codex"])

    normalized_provider = app_settings._normalize_provider(
        {
            "id": "codex",
            "name": "Codex",
            "icon": "codex-text.svg",
            "binary_names": [" codex ", ""],
            "supports_reasoning": "false",
        },
        fallback_provider,
    )
    assert normalized_provider["icon"] == "codex-white.svg"
    assert normalized_provider["binary_names"] == ["codex"]
    assert normalized_provider["supports_reasoning"] is False

    gemini_fallback = copy.deepcopy(app_settings.DEFAULT_APP_SETTINGS["providers"]["gemini"])
    normalized_gemini_provider = app_settings._normalize_provider(
        {
            "id": "gemini",
            "name": "Gemini",
            "icon": "gemini.svg",
            "binary_names": [" gemini ", ""],
        },
        gemini_fallback,
    )
    assert normalized_gemini_provider["icon"] == "gemini-color.svg"
    assert normalized_gemini_provider["binary_names"] == ["gemini"]

    normalized_settings = app_settings._normalize_settings(
        {
            "providers": {"codex": {"id": "codex", "name": "Codex", "icon": "⌘"}},
            "active_provider_id": "missing",
            "stream_render_throttle_ms": "1700",
            "reasoning_options": [("Quick", "low", "fast")],
        }
    )
    assert normalized_settings["active_provider_id"] == "codex"
    assert normalized_settings["providers"]["codex"]["icon"] == "codex-white.svg"
    assert "gemini" in normalized_settings["providers"]
    assert normalized_settings["stream_render_throttle_ms"] == 1500
    assert normalized_settings["reasoning_options"][0]["value"] == "low"


def test_parse_and_format_settings_payloads() -> None:
    with pytest.raises(ValueError):
        app_settings.parse_settings_text("")
    with pytest.raises(ValueError):
        app_settings.parse_settings_text("{not-json")

    normalized = app_settings.parse_settings_text(
        json.dumps({"providers": {"claude": {"id": "claude", "name": "Claude"}}})
    )
    assert "providers" in normalized

    formatted = app_settings.format_settings_payload(
        {"providers": {"claude": {"id": "claude", "name": "Claude"}}}
    )
    parsed = json.loads(formatted)
    assert parsed["active_provider_id"] == "claude"


def test_load_default_app_settings_falls_back_to_builtin(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing_defaults = tmp_path / "missing_defaults.json"
    missing_theme = tmp_path / "missing_theme.json"
    monkeypatch.setattr(app_settings, "APP_SETTINGS_DEFAULT_PATH", missing_defaults)
    monkeypatch.setattr(app_settings, "APP_THEME_SETTINGS_PATH", missing_theme)

    defaults = app_settings._load_default_app_settings()
    assert "providers" in defaults
    assert "claude" in defaults["providers"]
