"""Provider CLI discovery and capability probing."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CliCapabilities:
    supports_model_flag: bool = False
    supports_permission_flag: bool = False
    supports_reasoning_flag: bool = False
    supports_output_format_flag: bool = False
    supports_stream_json: bool = False
    supports_json: bool = False
    supports_include_partial_messages: bool = False


def find_provider_binary(binary_names: list[str]) -> str | None:
    normalized_names: list[str] = []
    for binary_name in binary_names:
        candidate_name = str(binary_name or "").strip()
        if not candidate_name:
            continue
        if candidate_name not in normalized_names:
            normalized_names.append(candidate_name)

    if not normalized_names:
        return None

    for executable in normalized_names:
        found = shutil.which(executable)
        if found:
            return found

    # Keep existing Claude-specific fallback probing for backwards compatibility.
    if any(name in {"claude", "claude-code"} for name in normalized_names):
        config_root = Path.home() / ".config" / "Claude" / "claude-code"
        candidates = (
            config_root / "claude",
            config_root / "claude-code",
            config_root / "bin" / "claude",
            config_root / "bin" / "claude-code",
        )
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)

        if config_root.is_dir():
            for binary_name in ("claude", "claude-code"):
                for candidate in config_root.rglob(binary_name):
                    if candidate.is_file() and os.access(candidate, os.X_OK):
                        return str(candidate)

    return None


def find_claude_binary() -> str | None:
    return find_provider_binary(["claude", "claude-code"])


def binary_exists(path: str | None) -> bool:
    if not path:
        return False
    return os.path.isfile(path) and os.access(path, os.X_OK)


def detect_cli_flag_support(binary_path: str) -> CliCapabilities:
    caps = CliCapabilities()
    try:
        result = subprocess.run(
            [binary_path, "--help"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return caps

    output = f"{result.stdout}\n{result.stderr}".lower()
    caps.supports_model_flag = "--model" in output
    caps.supports_permission_flag = "--permission-mode" in output
    caps.supports_reasoning_flag = "--effort" in output
    caps.supports_output_format_flag = "--output-format" in output
    caps.supports_stream_json = "stream-json" in output
    caps.supports_json = '"json"' in output or "json" in output
    caps.supports_include_partial_messages = "--include-partial-messages" in output
    return caps


def is_codex_authenticated() -> bool:
    codex_binary = find_provider_binary(["codex"])
    if not codex_binary:
        return False

    try:
        result = subprocess.run(
            [codex_binary, "login", "status"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    output = f"{result.stdout}\n{result.stderr}".strip().lower()
    if "not logged in" in output or "logged out" in output:
        return False
    return "logged in" in output
