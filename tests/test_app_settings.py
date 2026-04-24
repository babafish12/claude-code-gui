from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_code_gui.domain import app_settings


pytestmark = pytest.mark.unit


def test_agentctl_auto_enabled_roundtrip_with_custom_payload(tmp_path: Path) -> None:
    payload_path = tmp_path / "app_settings.json"
    custom_payload = {
        "providers": {},
        "reasoning_options": [],
        "agentctl_auto_enabled": False,
    }
    payload_path.write_text(json.dumps(custom_payload), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)
    saved = app_settings.save_settings(loaded, path=payload_path)

    assert loaded["agentctl_auto_enabled"] is False
    assert saved["agentctl_auto_enabled"] is False
    assert json.loads(payload_path.read_text(encoding="utf-8"))["agentctl_auto_enabled"] is False


def test_agentctl_auto_enabled_defaults_to_true_when_omitted(tmp_path: Path) -> None:
    payload_path = tmp_path / "app_settings.json"
    payload_path.write_text(json.dumps({"providers": {}, "reasoning_options": []}), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)

    assert loaded["agentctl_auto_enabled"] is True


def test_system_tray_enabled_roundtrip_with_custom_payload(tmp_path: Path) -> None:
    payload_path = tmp_path / "app_settings.json"
    custom_payload = {
        "providers": {},
        "reasoning_options": [],
        "system_tray_enabled": False,
    }
    payload_path.write_text(json.dumps(custom_payload), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)
    saved = app_settings.save_settings(loaded, path=payload_path)

    assert loaded["system_tray_enabled"] is False
    assert saved["system_tray_enabled"] is False
    assert json.loads(payload_path.read_text(encoding="utf-8"))["system_tray_enabled"] is False


def test_system_tray_enabled_defaults_to_true_when_omitted(tmp_path: Path) -> None:
    payload_path = tmp_path / "app_settings.json"
    payload_path.write_text(json.dumps({"providers": {}, "reasoning_options": []}), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)

    assert loaded["system_tray_enabled"] is True


def test_active_provider_id_roundtrip_with_custom_payload(tmp_path: Path) -> None:
    payload_path = tmp_path / "app_settings.json"
    custom_payload = {
        "providers": {},
        "reasoning_options": [],
        "active_provider_id": "codex",
    }
    payload_path.write_text(json.dumps(custom_payload), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)
    saved = app_settings.save_settings(loaded, path=payload_path)

    assert loaded["active_provider_id"] == "codex"
    assert saved["active_provider_id"] == "codex"
    assert json.loads(payload_path.read_text(encoding="utf-8"))["active_provider_id"] == "codex"


def test_startup_provider_mode_defaults_to_last_used_when_omitted(tmp_path: Path) -> None:
    payload_path = tmp_path / "app_settings.json"
    payload_path.write_text(json.dumps({"providers": {}, "reasoning_options": []}), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)
    saved = app_settings.save_settings(loaded, path=payload_path)

    assert loaded["startup_provider_mode"] == app_settings.DEFAULT_STARTUP_PROVIDER_MODE
    assert saved["startup_provider_mode"] == app_settings.DEFAULT_STARTUP_PROVIDER_MODE
    assert (
        json.loads(payload_path.read_text(encoding="utf-8"))["startup_provider_mode"]
        == app_settings.DEFAULT_STARTUP_PROVIDER_MODE
    )


@pytest.mark.parametrize("startup_provider_mode", app_settings.STARTUP_PROVIDER_MODES)
def test_startup_provider_mode_roundtrip_with_custom_payload(
    tmp_path: Path,
    startup_provider_mode: str,
) -> None:
    payload_path = tmp_path / "app_settings.json"
    custom_payload = {
        "providers": {},
        "reasoning_options": [],
        "startup_provider_mode": startup_provider_mode,
    }
    payload_path.write_text(json.dumps(custom_payload), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)
    saved = app_settings.save_settings(loaded, path=payload_path)

    assert loaded["startup_provider_mode"] == startup_provider_mode
    assert saved["startup_provider_mode"] == startup_provider_mode
    assert json.loads(payload_path.read_text(encoding="utf-8"))["startup_provider_mode"] == startup_provider_mode


def test_stream_render_throttle_ms_roundtrip_and_clamp(tmp_path: Path) -> None:
    payload_path = tmp_path / "app_settings.json"
    custom_payload = {
        "providers": {},
        "reasoning_options": [],
        "stream_render_throttle_ms": 5000,
    }
    payload_path.write_text(json.dumps(custom_payload), encoding="utf-8")

    loaded = app_settings.load_settings(path=payload_path)
    saved = app_settings.save_settings(loaded, path=payload_path)

    assert loaded["stream_render_throttle_ms"] == 1500
    assert saved["stream_render_throttle_ms"] == 1500
    assert json.loads(payload_path.read_text(encoding="utf-8"))["stream_render_throttle_ms"] == 1500
