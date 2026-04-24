from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_mock

from claude_code_gui.services import binary_probe

pytestmark = pytest.mark.unit


def _reset_codex_auth_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(binary_probe, "_codex_auth_cache_value", None)
    monkeypatch.setattr(binary_probe, "_codex_auth_cache_checked_at", 0.0)


def test_find_provider_binary_prefers_first_which_hit(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch(
        "claude_code_gui.services.binary_probe.shutil.which",
        side_effect=lambda name: "/usr/bin/codex" if name == "codex" else None,
    )

    found = binary_probe.find_provider_binary(["", "codex", "codex"])

    assert found == "/usr/bin/codex"


def test_find_provider_binary_uses_claude_fallback(tmp_path: Path, mocker: pytest_mock.MockerFixture) -> None:
    fallback = tmp_path / ".config" / "Claude" / "claude-code" / "bin" / "claude"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("#!/bin/sh\n", encoding="utf-8")

    mocker.patch("claude_code_gui.services.binary_probe.shutil.which", return_value=None)
    mocker.patch("claude_code_gui.services.binary_probe.Path.home", return_value=tmp_path)
    mocker.patch("claude_code_gui.services.binary_probe.os.access", return_value=True)

    found = binary_probe.find_provider_binary(["claude"])

    assert found == str(fallback)


def test_binary_exists_checks_file_and_executable(tmp_path: Path, mocker: pytest_mock.MockerFixture) -> None:
    executable = tmp_path / "tool"
    executable.write_text("x", encoding="utf-8")

    mocker.patch("claude_code_gui.services.binary_probe.os.access", return_value=True)

    assert binary_probe.binary_exists(str(executable)) is True
    assert binary_probe.binary_exists(None) is False


def test_detect_cli_flag_support_parses_help_output(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch(
        "claude_code_gui.services.binary_probe.subprocess.run",
        return_value=SimpleNamespace(
            stdout="--model --permission-mode --effort --output-format stream-json json --include-partial-messages",
            stderr="",
        ),
    )

    caps = binary_probe.detect_cli_flag_support("/usr/bin/cli")

    assert caps.supports_model_flag is True
    assert caps.supports_permission_flag is True
    assert caps.supports_reasoning_flag is True
    assert caps.supports_output_format_flag is True
    assert caps.supports_stream_json is True
    assert caps.supports_json is True
    assert caps.supports_include_partial_messages is True


def test_detect_cli_flag_support_handles_subprocess_error(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch(
        "claude_code_gui.services.binary_probe.subprocess.run",
        side_effect=OSError("nope"),
    )

    caps = binary_probe.detect_cli_flag_support("/usr/bin/cli")

    assert caps == binary_probe.CliCapabilities()


def test_is_codex_authenticated_variants(
    mocker: pytest_mock.MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_codex_auth_cache(monkeypatch)
    mocker.patch("claude_code_gui.services.binary_probe.find_provider_binary", return_value=None)
    assert binary_probe.is_codex_authenticated() is False

    _reset_codex_auth_cache(monkeypatch)
    mocker.patch("claude_code_gui.services.binary_probe.find_provider_binary", return_value="/usr/bin/codex")
    mocker.patch(
        "claude_code_gui.services.binary_probe.subprocess.run",
        return_value=SimpleNamespace(stdout="Logged in", stderr=""),
    )
    assert binary_probe.is_codex_authenticated() is True

    _reset_codex_auth_cache(monkeypatch)
    mocker.patch(
        "claude_code_gui.services.binary_probe.subprocess.run",
        return_value=SimpleNamespace(stdout="not logged in", stderr=""),
    )
    assert binary_probe.is_codex_authenticated() is False

    _reset_codex_auth_cache(monkeypatch)
    mocker.patch(
        "claude_code_gui.services.binary_probe.subprocess.run",
        side_effect=OSError("boom"),
    )
    assert binary_probe.is_codex_authenticated() is False
