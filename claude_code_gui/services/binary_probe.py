"""Provider CLI discovery and capability probing."""

from __future__ import annotations

import json
import re
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


_MODEL_NAME_PATTERN = re.compile(r"^(?:[0-9]+[.)]?\s*)?(?P<name>[a-zA-Z0-9._/\-]+)(?:\s*[:=-]\s*(?P<label>.+))?$")
_CODEX_MODELS_CACHE_PATH = Path.home() / ".codex" / "models_cache.json"


def _strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", value)


def _normalize_model_value(value: str) -> str:
    return value.strip()


def _extract_models_from_json_payload(payload: object) -> tuple[tuple[str, str], ...]:
    if isinstance(payload, dict):
        for key in ("models", "data", "result", "items"):
            raw_items = payload.get(key)
            if raw_items is not None:
                if isinstance(raw_items, dict):
                    discovered: list[tuple[str, str]] = []
                    for model_name, model_data in raw_items.items():
                        candidate = _normalize_model_value(str(model_name))
                        if not candidate:
                            continue
                        label = candidate
                        if isinstance(model_data, dict):
                            resolved = _normalize_model_value(
                                str(model_data.get("name") or model_data.get("id") or ""),
                            )
                            if resolved:
                                candidate = resolved
                            label = _normalize_model_value(
                                str(model_data.get("label") or model_data.get("title") or label),
                            ) or label
                        discovered.append((label, candidate))

                    if discovered:
                        deduped: list[tuple[str, str]] = []
                        seen: set[str] = set()
                        for label, value in discovered:
                            if value in seen:
                                continue
                            seen.add(value)
                            deduped.append((label, value))
                        return tuple(deduped)

                result = _extract_models_from_json_payload(raw_items)
                if result:
                    return result
        return ()

    if not isinstance(payload, (list, tuple)):
        return ()

    discovered: list[tuple[str, str]] = []
    for entry in payload:
        if isinstance(entry, str):
            model_value = _normalize_model_value(entry)
            if model_value:
                discovered.append((model_value, model_value))
            continue

        if not isinstance(entry, dict):
            continue

        candidate = _normalize_model_value(str(entry.get("value") or entry.get("id") or entry.get("name") or "").strip())
        label = _normalize_model_value(str(entry.get("label") or entry.get("name") or candidate or "Model").strip())
        if candidate and not candidate.isspace():
            discovered.append((label, candidate))

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, value in discovered:
        if value in seen:
            continue
        seen.add(value)
        deduped.append((label, value))
    return tuple(deduped)


def _extract_models_from_cache_payload(payload: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(payload, dict):
        return ()

    raw_models = payload.get("models")
    if not isinstance(raw_models, list):
        return ()

    discovered: list[tuple[str, str]] = []
    for entry in raw_models:
        if isinstance(entry, str):
            model_slug = _normalize_model_value(entry)
            if model_slug:
                discovered.append((model_slug, model_slug))
            continue

        if not isinstance(entry, dict):
            continue

        visibility = str(entry.get("visibility") or "").strip().lower()
        if visibility == "hide":
            continue

        model_slug = _normalize_model_value(str(entry.get("slug") or entry.get("name") or ""))
        if not model_slug:
            continue

        model_label = _normalize_model_value(
            str(entry.get("display_name") or entry.get("label") or model_slug)
        )
        discovered.append((model_label or model_slug, model_slug))

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, value in discovered:
        if value in seen:
            continue
        seen.add(value)
        deduped.append((label, value))
    return tuple(deduped)


def _load_codex_cached_models(cache_path: Path | None = None) -> tuple[tuple[str, str], ...]:
    source = cache_path or _CODEX_MODELS_CACHE_PATH
    if not source.is_file():
        return ()

    try:
        raw_payload = source.read_text(encoding="utf-8")
    except OSError:
        return ()

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return ()

    return _extract_models_from_cache_payload(payload)


def _extract_models_from_text(value: str) -> tuple[tuple[str, str], ...]:
    if not value:
        return ()

    discovered: list[tuple[str, str]] = []
    for raw_line in _strip_ansi(value).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith(("#", "name", "id", "model", "available")):
            if "|" in line or ":" in line or "  " in line:
                continue

        if line.startswith(("-", "•", "*")):
            candidate = _normalize_model_value(line[1:]).split(" ", 1)[0]
            if candidate:
                discovered.append((candidate, candidate))
            continue

        match = _MODEL_NAME_PATTERN.match(line)
        if match:
            model_name = _normalize_model_value(match.group("name") or "")
            label = _normalize_model_value(match.group("label") or model_name or "Model")
            if model_name:
                discovered.append((label, model_name))
            continue

        if "/" in line:
            compact = _normalize_model_value(line.split()[0])
            if compact and compact not in {value for _, value in discovered}:
                discovered.append((compact, compact))
                continue

        if "|" in line and line.count("|") >= 1:
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) >= 2:
                for cell in cells[:2]:
                    if cell and cell != "---":
                        model_name = _normalize_model_value(cell)
                        if model_name:
                            discovered.append((model_name, model_name))
                            break

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, value in discovered:
        if value in seen:
            continue
        seen.add(value)
        deduped.append((label, value))
    return tuple(deduped)


def _is_probable_model_value(value: str, *, provider: str = "claude") -> bool:
    normalized = value.strip().lower()
    if normalized in {
        "error",
        "json",
        "usage",
        "help",
        "command",
        "commands",
        "unknown",
        "model",
        "models",
        "available",
        "list",
        "option",
        "options",
        "flag",
    }:
        return False

    candidate = _normalize_model_value(value)
    if not candidate or len(candidate) < 2:
        return False
    if " " in candidate or "\t" in candidate:
        return False
    if "," in candidate:
        return False
    if candidate[0] in {".", "-", "_"}:
        return False
    if re.fullmatch(r"[a-zA-Z0-9._/-]+", candidate) is None:
        return False
    if provider == "codex":
        if normalized.startswith("gpt-"):
            return True
        if normalized.startswith("claude-"):
            return True
        if normalized in {"sonnet", "opus", "haiku"}:
            return True
        if normalized.startswith("o") and len(normalized) > 1 and normalized[1].isdigit():
            return True
        return False
    return True


def detect_provider_model_options(binary_path: str, provider_id: str) -> tuple[tuple[str, str], ...]:
    if not binary_path:
        return ()

    provider = (provider_id or "").strip().lower()
    if not provider:
        return ()

    discovered: list[tuple[str, str]] = []
    seen: set[str] = set()

    model_commands: list[list[str]] = []
    def _add_command(command: list[str]) -> None:
        if command not in model_commands:
            model_commands.append(command)

    if provider == "claude":
        _add_command([binary_path, "models"])
        _add_command([binary_path, "model", "list"])
        _add_command([binary_path, "models", "--json"])
        _add_command([binary_path, "model", "list", "--json"])
    elif provider == "codex":
        discovered = list(_load_codex_cached_models())
        seen = {value for _, value in discovered}
        _add_command([binary_path, "models"])
        _add_command([binary_path, "models", "--json"])
        _add_command([binary_path, "model", "list"])
        _add_command([binary_path, "model", "list", "--json"])
        _add_command([binary_path, "list", "models"])
        _add_command([binary_path, "list", "models", "--json"])
        _add_command([binary_path, "help", "models"])
        _add_command([binary_path, "features"])
        _add_command([binary_path, "exec", "--help"])
        _add_command([binary_path, "help", "exec"])
        _add_command([binary_path, "features", "--help"])
        _add_command([binary_path, "help"])
    else:
        _add_command([binary_path, "model", "list"])
        _add_command([binary_path, "model", "list", "--json"])
        _add_command([binary_path, "list", "models"])
        _add_command([binary_path, "list", "models", "--json"])
        _add_command([binary_path, "help", "models"])
        _add_command([binary_path, "help", "model"])
        _add_command([binary_path, "help", "models", "--json"])
        _add_command([binary_path, "list"])
        _add_command([binary_path, "list", "--json"])
        _add_command([binary_path, "help"])

    for command in model_commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue

        output = f"{result.stdout}\n{result.stderr}"
        if not output.strip():
            continue

        # `codex models` often fails in non-interactive mode on some setups.
        # Keep parsing but don't treat these lines as hard failures.
        if provider == "codex" and str(output).strip().lower().startswith("error:"):
            continue

        payload = None
        parsed_models: tuple[tuple[str, str], ...] = ()
        try:
            payload = json.loads(output.strip())
        except json.JSONDecodeError:
            payload = None

        if payload is not None:
            parsed_models = _extract_models_from_json_payload(payload)
        if not parsed_models:
            parsed_models = _extract_models_from_text(output)

        parsed_models = tuple(
            (label, value)
            for label, value in parsed_models
            if _is_probable_model_value(value, provider=provider)
        )
        if parsed_models:
            for label, value in parsed_models:
                if value in seen:
                    continue
                seen.add(value)
                discovered.append((label, value))

    deduped: list[tuple[str, str]] = []
    deduped_values: set[str] = set()
    for label, value in discovered:
        if value in deduped_values:
            continue
        deduped_values.add(value)
        deduped.append((label, value))

    return tuple(deduped)


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
    binary_name = Path(binary_path).name.lower()
    is_codex = binary_name == "codex"
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
    if is_codex:
        for command in ([binary_path, "exec", "--help"], [binary_path, "features", "--help"]):
            try:
                feature_result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=4,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            output += "\n" + f"{feature_result.stdout}\n{feature_result.stderr}".lower()

    caps.supports_model_flag = "--model" in output
    caps.supports_permission_flag = "--permission-mode" in output
    caps.supports_reasoning_flag = (
        "--effort" in output
        or "--reasoning" in output
        or "model_reasoning_effort" in output
    )
    if is_codex:
        caps.supports_reasoning_flag = (
            caps.supports_reasoning_flag
            or "model_reasoning_effort" in output
            or "-c" in output
            or "--config" in output
        )
        caps.supports_permission_flag = (
            "--full-auto" in output
            or "--dangerously-bypass-approvals-and-sandbox" in output
            or "-a" in output
            or caps.supports_permission_flag
        )
    caps.supports_output_format_flag = "--output-format" in output or "output format" in output
    caps.supports_stream_json = "stream-json" in output
    caps.supports_json = '"json"' in output or "--json" in output or " json " in output
    if is_codex:
        caps.supports_json = caps.supports_json or "--json" in output
        caps.supports_output_format_flag = caps.supports_output_format_flag or "--json" in output
    caps.supports_include_partial_messages = "--include-partial-messages" in output
    return caps


def is_codex_authenticated() -> bool:
    codex_binary = find_provider_binary(["codex"])
    if not codex_binary:
        return False

    checks = [
        ["login", "status"],
        ["auth", "status"],
        ["status"],
    ]

    for command in checks:
        try:
            result = subprocess.run(
                [codex_binary, *command],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue

        output = f"{result.stdout}\n{result.stderr}".strip().lower()

        if not output:
            if result.returncode == 0:
                return True
            continue

        if any(marker in output for marker in ("not logged in", "logged out", "not authenticated", "authentication required", "please log in", "login required")):
            return False
        if any(marker in output for marker in ("logged in", "authenticated", "already logged in", "you are logged in")):
            return True

    return False
