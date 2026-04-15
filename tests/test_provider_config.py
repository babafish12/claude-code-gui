from __future__ import annotations

import copy

import pytest

from claude_code_gui.domain.app_settings import load_settings
from claude_code_gui.domain.provider import (
    PROVIDERS,
    ProviderConfig,
    get_provider_config,
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
    assert set(PROVIDERS.keys()) == {"claude", "codex"}

    claude = PROVIDERS["claude"]
    codex = PROVIDERS["codex"]

    assert claude.binary_names == ("claude", "claude-code")
    assert codex.binary_names == ("codex",)
    assert claude.supports_reasoning is True
    assert codex.supports_reasoning is True

    for config in (claude, codex):
        assert config.model_options
        assert config.permission_options
        assert "accent" in config.colors
        assert len(config.accent_rgb) == 3
        assert len(config.accent_soft_rgb) == 3


def test_refresh_provider_registry_updates_in_place() -> None:
    registry_object_id = id(PROVIDERS)
    original_payload = load_settings()
    test_payload = copy.deepcopy(original_payload)

    test_payload["providers"]["claude"]["colors"]["accent"] = "#123456"
    test_payload["providers"]["claude"]["accent_rgb"] = [18, 52, 86]
    test_payload["providers"]["claude"]["accent_soft_rgb"] = [48, 96, 128]

    try:
        refreshed = refresh_provider_registry(test_payload)
        assert id(PROVIDERS) == registry_object_id
        assert id(refreshed) == registry_object_id
        assert PROVIDERS["claude"].colors["accent"] == "#123456"
        assert PROVIDERS["claude"].accent_rgb == (18, 52, 86)
        assert PROVIDERS["claude"].accent_soft_rgb == (48, 96, 128)
    finally:
        refresh_provider_registry(original_payload)
