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
