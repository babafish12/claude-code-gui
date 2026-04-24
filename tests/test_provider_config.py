from __future__ import annotations

import copy

import pytest

from claude_code_gui.domain.app_settings import get_default_settings, load_settings
from claude_code_gui.domain.provider import (
    PROVIDERS,
    ProviderConfig,
    get_provider_config,
    get_providers,
    normalize_provider_id,
    refresh_provider_registry,
)

pytestmark = pytest.mark.unit


def test_provider_config_display_name_matches_name() -> None:
    config = ProviderConfig(
        id="x",
        name="Display",
        icon="*",
        binary_names=("x",),
        colors={"accent": "#fff"},
        accent_rgb=(1, 2, 3),
        accent_soft_rgb=(4, 5, 6),
        model_options=(("Model", "value"),),
        permission_options=(("Auto", "auto", False),),
        supports_reasoning=False,
    )

    assert config.display_name == "Display"


def test_normalize_provider_id_and_lookup() -> None:
    assert normalize_provider_id("CoDeX") == "codex"
    assert normalize_provider_id("unknown") == "claude"
    assert get_provider_config("unknown").id == "claude"


def test_providers_registry_contains_expected_entries() -> None:
    assert {"claude", "codex", "gemini"}.issubset(set(PROVIDERS.keys()))

    claude = PROVIDERS["claude"]
    codex = PROVIDERS["codex"]
    gemini = PROVIDERS["gemini"]

    assert claude.binary_names == ("claude", "claude-code")
    assert codex.binary_names == ("codex",)
    assert gemini.binary_names == ("gemini",)
    assert claude.supports_reasoning is True
    assert codex.supports_reasoning is True
    assert gemini.supports_reasoning is False
    for config in (claude, codex, gemini):
        assert config.model_options
        assert config.permission_options
        assert "accent" in config.colors
        assert len(config.accent_rgb) == 3
        assert len(config.accent_soft_rgb) == 3


def test_default_permission_options_keep_codex_non_interactive() -> None:
    original_payload = load_settings()
    try:
        defaults = refresh_provider_registry(get_default_settings())
        claude = defaults["claude"]
        codex = defaults["codex"]
        gemini = defaults["gemini"]

        assert "ask" in {value for _label, value, _advanced in claude.permission_options}
        assert "ask" not in {value for _label, value, _advanced in codex.permission_options}
        assert "ask" not in {value for _label, value, _advanced in gemini.permission_options}
    finally:
        refresh_provider_registry(original_payload)


def test_refresh_provider_registry_swaps_snapshot_and_updates_alias() -> None:
    registry_alias_id = id(PROVIDERS)
    original_snapshot = get_providers()
    original_payload = load_settings()
    test_payload = copy.deepcopy(original_payload)

    test_payload["providers"]["claude"]["colors"]["accent"] = "#123456"
    test_payload["providers"]["claude"]["accent_rgb"] = [18, 52, 86]
    test_payload["providers"]["claude"]["accent_soft_rgb"] = [48, 96, 128]

    try:
        refreshed = refresh_provider_registry(test_payload)
        assert id(PROVIDERS) == registry_alias_id
        assert refreshed is get_providers()
        assert refreshed is not original_snapshot
        assert PROVIDERS["claude"].colors["accent"] == "#123456"
        assert PROVIDERS["claude"].accent_rgb == (18, 52, 86)
        assert PROVIDERS["claude"].accent_soft_rgb == (48, 96, 128)
    finally:
        refresh_provider_registry(original_payload)
