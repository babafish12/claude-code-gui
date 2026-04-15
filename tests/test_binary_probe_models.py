from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from claude_code_gui.services import binary_probe

pytestmark = pytest.mark.unit


def test_extract_models_from_json_payload_supports_dict_and_list_shapes() -> None:
    payload = {
        "result": {
            "items": [
                {"id": "gpt-5", "label": "GPT-5"},
                {"value": "gpt-5-mini", "name": "Mini"},
                "o3",
                {"value": "gpt-5", "label": "Duplicate"},
            ]
        }
    }

    extracted = binary_probe._extract_models_from_json_payload(payload)

    assert extracted == (
        ("GPT-5", "gpt-5"),
        ("Mini", "gpt-5-mini"),
        ("o3", "o3"),
    )


def test_extract_models_from_cache_payload_filters_hidden_and_dedupes() -> None:
    payload = {
        "models": [
            {"slug": "gpt-5", "display_name": "GPT-5"},
            {"slug": "gpt-5", "display_name": "Duplicate"},
            {"name": "o3"},
            {"slug": "hidden", "visibility": "hide"},
            "gpt-5-mini",
        ]
    }

    extracted = binary_probe._extract_models_from_cache_payload(payload)

    assert extracted == (
        ("GPT-5", "gpt-5"),
        ("o3", "o3"),
        ("gpt-5-mini", "gpt-5-mini"),
    )


def test_load_codex_cached_models_handles_missing_invalid_and_valid_payloads(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"
    assert binary_probe._load_codex_cached_models(missing_path) == ()

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not-json", encoding="utf-8")
    assert binary_probe._load_codex_cached_models(invalid_path) == ()

    valid_path = tmp_path / "valid.json"
    valid_path.write_text(
        json.dumps({"models": [{"slug": "gpt-5", "display_name": "GPT-5"}, "o3"]}),
        encoding="utf-8",
    )
    assert binary_probe._load_codex_cached_models(valid_path) == (
        ("GPT-5", "gpt-5"),
        ("o3", "o3"),
    )


def test_extract_models_from_text_parses_bullets_patterns_and_tables() -> None:
    output = """
    # Models
    - gpt-5 stable
    gpt-5-mini: Mini model
    foo/bar extra
    | model-x | notes |
    """

    extracted = binary_probe._extract_models_from_text(output)
    values = {value for _, value in extracted}

    assert {"gpt-5", "gpt-5-mini", "foo/bar", "model-x"}.issubset(values)


def test_is_probable_model_value_handles_codex_and_generic_rules() -> None:
    assert binary_probe._is_probable_model_value("gpt-5", provider="codex") is True
    assert binary_probe._is_probable_model_value("o3", provider="codex") is True
    assert binary_probe._is_probable_model_value("sonnet", provider="codex") is True
    assert binary_probe._is_probable_model_value("custom-model", provider="codex") is False
    assert binary_probe._is_probable_model_value("custom-model", provider="claude") is True
    assert binary_probe._is_probable_model_value("json", provider="claude") is False
    assert binary_probe._is_probable_model_value("bad value", provider="claude") is False


def test_detect_provider_model_options_codex_merges_cache_and_cli_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary = "/usr/bin/codex"
    monkeypatch.setattr(
        binary_probe,
        "_load_codex_cached_models",
        lambda _path=None: (("Cached GPT-5", "gpt-5"), ("Cached GPT-4.1", "gpt-4.1")),
    )

    def fake_run(command, **_kwargs):
        key = tuple(command)
        if key == (binary, "models"):
            return SimpleNamespace(stdout="error: non-interactive failure", stderr="", returncode=1)
        if key == (binary, "models", "--json"):
            return SimpleNamespace(
                stdout=json.dumps(
                    {
                        "models": [
                            {"value": "gpt-4.1", "label": "Duplicate"},
                            {"value": "o3", "label": "O3"},
                            {"value": "bad value", "label": "Invalid"},
                        ]
                    }
                ),
                stderr="",
                returncode=0,
            )
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(binary_probe.subprocess, "run", fake_run)

    discovered = binary_probe.detect_provider_model_options(binary, "codex")

    assert discovered == (
        ("Cached GPT-5", "gpt-5"),
        ("Cached GPT-4.1", "gpt-4.1"),
        ("O3", "o3"),
    )


def test_detect_provider_model_options_generic_provider_uses_json_and_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary = "/usr/bin/custom-cli"

    def fake_run(command, **_kwargs):
        key = tuple(command)
        if key == (binary, "model", "list", "--json"):
            return SimpleNamespace(
                stdout=json.dumps({"result": {"items": [{"id": "model-a", "label": "Model A"}]}}),
                stderr="",
                returncode=0,
            )
        if key == (binary, "list", "models"):
            return SimpleNamespace(stdout="- model-b stable", stderr="", returncode=0)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(binary_probe.subprocess, "run", fake_run)

    discovered = binary_probe.detect_provider_model_options(binary, "custom")

    assert discovered == (
        ("Model A", "model-a"),
        ("model-b", "model-b"),
    )


def test_detect_provider_model_options_returns_empty_for_missing_inputs() -> None:
    assert binary_probe.detect_provider_model_options("", "codex") == ()
    assert binary_probe.detect_provider_model_options("/usr/bin/codex", "") == ()


def test_find_provider_binary_supports_recursive_claude_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested = tmp_path / ".config" / "Claude" / "claude-code" / "deep" / "bin" / "claude"
    nested.parent.mkdir(parents=True)
    nested.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(binary_probe.shutil, "which", lambda _name: None)
    monkeypatch.setattr(binary_probe.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(binary_probe.os, "access", lambda _path, _mode: True)

    found = binary_probe.find_provider_binary(["claude"])

    assert found == str(nested)


def test_find_claude_binary_delegates_to_provider_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_lookup(names: list[str]) -> str | None:
        captured.append(names)
        return "/usr/bin/claude"

    monkeypatch.setattr(binary_probe, "find_provider_binary", fake_lookup)

    found = binary_probe.find_claude_binary()

    assert found == "/usr/bin/claude"
    assert captured == [["claude", "claude-code"]]


def test_detect_cli_flag_support_codex_reads_exec_and_features_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary = "/usr/bin/codex"

    def fake_run(command, **_kwargs):
        key = tuple(command)
        if key == (binary, "--help"):
            return SimpleNamespace(stdout="Codex command", stderr="", returncode=0)
        if key == (binary, "exec", "--help"):
            return SimpleNamespace(
                stdout="--json --full-auto --dangerously-bypass-approvals-and-sandbox -c --config",
                stderr="",
                returncode=0,
            )
        if key == (binary, "features", "--help"):
            return SimpleNamespace(stdout="model_reasoning_effort", stderr="", returncode=0)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(binary_probe.subprocess, "run", fake_run)

    caps = binary_probe.detect_cli_flag_support(binary)

    assert caps.supports_json is True
    assert caps.supports_output_format_flag is True
    assert caps.supports_permission_flag is True
    assert caps.supports_reasoning_flag is True


def test_is_codex_authenticated_accepts_second_empty_success_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(binary_probe, "find_provider_binary", lambda _names: "/usr/bin/codex")
    responses = iter(
        [
            SimpleNamespace(stdout="", stderr="", returncode=1),
            SimpleNamespace(stdout="", stderr="", returncode=0),
        ]
    )

    monkeypatch.setattr(binary_probe.subprocess, "run", lambda *_args, **_kwargs: next(responses))

    assert binary_probe.is_codex_authenticated() is True
