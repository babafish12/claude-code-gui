"""Application settings for providers, UI options, and user-editable metadata."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from claude_code_gui.storage.config_paths import APP_SETTINGS_PATH, ensure_config_dir

APP_SETTINGS_DEFAULT_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "default_app_settings.json"
)
APP_THEME_SETTINGS_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "provider_theme_settings.json"
)


def _to_lower_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    return normalized


def _load_provider_theme_settings() -> dict[str, Any]:
    if not APP_THEME_SETTINGS_PATH.is_file():
        return {}

    try:
        payload = json.loads(APP_THEME_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    providers = payload.get("providers")
    if not isinstance(providers, dict):
        return {}

    normalized: dict[str, Any] = {}
    for key, value in providers.items():
        provider_id = _to_lower_str(key)
        if not provider_id or not isinstance(value, dict):
            continue
        normalized[provider_id] = value

    return normalized


def _merge_provider_theme_defaults(
    base_payload: dict[str, Any],
    theme_payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(base_payload, dict):
        return {}
    if not theme_payload:
        return base_payload

    merged_payload = copy.deepcopy(base_payload)
    providers = merged_payload.get("providers")
    if not isinstance(providers, dict):
        return merged_payload

    for raw_provider_id, theme_provider in theme_payload.items():
        if not isinstance(raw_provider_id, str):
            continue
        provider_id = raw_provider_id.strip().lower()
        if not provider_id:
            continue

        provider_payload = providers.get(provider_id)
        if not isinstance(provider_payload, dict):
            providers[provider_id] = copy.deepcopy(theme_provider)
            continue

        merged_provider = dict(provider_payload)
        for key in (
            "colors",
            "accent_rgb",
            "accent_soft_rgb",
            "model_options",
        ):
            if key in theme_provider:
                merged_provider[key] = copy.deepcopy(theme_provider[key])

        providers[provider_id] = merged_provider

    return merged_payload

_BUILTIN_DEFAULT_APP_SETTINGS: dict[str, Any] = {
        "providers": {
            "claude": {
                "id": "claude",
                "name": "Claude",
                "icon": "claude-color.svg",
            "binary_names": ["claude", "claude-code"],
            "colors": {
                "window_bg": "#2f2f2a",
                "header_bg": "#2c2c27",
                "header_gradient_end": "#252520",
                "sidebar_bg": "#252520",
                "chat_outer_bg": "#2f2f2a",
                "chat_bg": "#2f2f2a",
                "status_bg": "#292923",
                "bottom_gradient_end": "#252520",
                "border": "#4a4a43",
                "border_soft": "#3b3b35",
                "foreground": "#d4d4c8",
                "foreground_muted": "#8a8a7a",
                "accent": "#d97757",
                "accent_soft": "#e09670",
                "warning": "#d5a160",
                "error": "#df7f66",
                "success": "#8bbf8a",
                "button_bg": "#35352f",
                "button_bg_hover": "#3f3f38",
                "button_bg_active": "#484840",
                "new_session_bg": "#31312b",
                "new_session_border": "#3f3f38",
                "sidebar_toggle_collapsed_bg": "#3a3a34",
                "menu_bg": "#34342e",
                "popover_bg": "#30302a",
                "session_filter_bg": "#31312b",
                "session_filter_hover_bg": "#3a3a33",
                "session_filter_active_fg": "#f7efe9",
                "session_row_hover_bg": "#34342f",
                "session_row_active_bg": "#3a3a34",
                "status_dot_ended": "#7b7b70",
                "status_dot_archived": "#585850",
                "context_trough_bg": "#3a3a34",
                "session_meta_time": "#bcb49b",
            },
            "accent_rgb": [212, 132, 90],
            "accent_soft_rgb": [224, 150, 112],
            "model_options": [
                {"label": "Claude Sonnet (Latest)", "value": "sonnet"},
                {"label": "Claude Opus (Latest)", "value": "opus"},
                {"label": "Claude Haiku (Latest)", "value": "haiku"},
            ],
            "permission_options": [
                {"label": "Auto", "value": "auto", "is_advanced": False},
                {"label": "Ask", "value": "ask", "is_advanced": False},
                {"label": "Plan mode", "value": "plan", "is_advanced": False},
                {"label": "Bypass permissions (Advanced)", "value": "bypassPermissions", "is_advanced": True},
            ],
            "supports_reasoning": True,
        },
            "codex": {
                "id": "codex",
                "name": "Codex",
                "icon": "codex-white.svg",
            "binary_names": ["codex"],
            "colors": {
                "window_bg": "#1c2220",
                "header_bg": "#181f1c",
                "header_gradient_end": "#121816",
                "sidebar_bg": "#131a18",
                "chat_outer_bg": "#1c2220",
                "chat_bg": "#1c2220",
                "status_bg": "#161d1a",
                "bottom_gradient_end": "#121816",
                "border": "#2d3a34",
                "border_soft": "#24302a",
                "foreground": "#d7e2dc",
                "foreground_muted": "#8ea198",
                "accent": "#10a37f",
                "accent_soft": "#4ade80",
                "warning": "#d0b26f",
                "error": "#d78574",
                "success": "#56c895",
                "button_bg": "#202925",
                "button_bg_hover": "#27322d",
                "button_bg_active": "#2e3b34",
                "new_session_bg": "#212a26",
                "new_session_border": "#2f3b35",
                "sidebar_toggle_collapsed_bg": "#27312d",
                "menu_bg": "#1b2420",
                "popover_bg": "#16201c",
                "session_filter_bg": "#212a26",
                "session_filter_hover_bg": "#27312d",
                "session_filter_active_fg": "#e9f6ef",
                "session_row_hover_bg": "#25302b",
                "session_row_active_bg": "#2a3630",
                "status_dot_ended": "#76887f",
                "status_dot_archived": "#55615b",
                "context_trough_bg": "#27312d",
                "session_meta_time": "#a8bbb1",
            },
            "accent_rgb": [16, 163, 127],
            "accent_soft_rgb": [74, 222, 128],
            "model_options": [
                {"label": "GPT-5.4", "value": "gpt-5.4"},
                {"label": "GPT-5", "value": "gpt-5"},
                {"label": "GPT-5.3 Codex", "value": "gpt-5.3-codex"},
                {"label": "GPT-5.3 Codex Spark", "value": "gpt-5.3-codex-spark"},
            ],
            "permission_options": [
                {"label": "Auto", "value": "auto", "is_advanced": False},
                {"label": "Ask", "value": "ask", "is_advanced": False},
                {"label": "Plan mode", "value": "plan", "is_advanced": False},
                {"label": "Bypass permissions (Advanced)", "value": "bypassPermissions", "is_advanced": True},
            ],
            "supports_reasoning": True,
        },
    },
    "reasoning_options": [
        {
            "title": "Low (Fast)",
            "value": "low",
            "description": "Fast responses with standard reasoning.",
        },
        {
            "title": "Medium (Balanced)",
            "value": "medium",
            "description": "Balanced reasoning for everyday tasks.",
        },
        {
            "title": "High (Deep)",
            "value": "high",
            "description": "Deep reasoning for complex problems.",
        },
    ],
    "agentctl_auto_enabled": True,
    "system_tray_enabled": True,
    "active_provider_id": "claude",
    "stream_render_throttle_ms": 80,
}


def _load_default_app_settings() -> dict[str, Any]:
    """Load baseline defaults from bundled JSON fallback file."""
    try:
        payload = json.loads(APP_SETTINGS_DEFAULT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(_BUILTIN_DEFAULT_APP_SETTINGS)

    if not isinstance(payload, dict):
        return copy.deepcopy(_BUILTIN_DEFAULT_APP_SETTINGS)

    merged = _merge_provider_theme_defaults(
        payload,
        _load_provider_theme_settings(),
    )
    return merged


DEFAULT_APP_SETTINGS = _load_default_app_settings()


def get_default_settings() -> dict[str, Any]:
    """Return a deep copy of the builtin defaults."""
    return copy.deepcopy(DEFAULT_APP_SETTINGS)


def _atomic_write(path: Path, payload: str) -> None:
    if not payload:
        payload = "null"
    temp_file: str | None = None
    try:
        fd, temp_file = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if temp_file is None:
            raise RuntimeError("Failed to allocate temporary file for settings write")
        os.replace(temp_file, path)
    finally:
        if temp_file is not None and os.path.exists(temp_file):
            Path(temp_file).unlink()


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _to_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in {"1", "true", "yes", "on"}:
            return True
        if lower in {"0", "false", "no", "off"}:
            return False
    return fallback


def _to_int(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return fallback
        try:
            return int(float(stripped))
        except ValueError:
            return fallback
    return fallback


def _to_int_range(value: Any, fallback: int, *, minimum: int, maximum: int) -> int:
    converted = _to_int(value, fallback)
    return max(minimum, min(maximum, converted))


def _to_rgb(value: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return fallback
    parts: list[int] = []
    for item in value[:3]:
        try:
            converted = int(item)
        except (TypeError, ValueError):
            return fallback
        if converted < 0 or converted > 255:
            return fallback
        parts.append(converted)
    return (parts[0], parts[1], parts[2])


def _to_string_list(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return list(fallback)
    normalized = [_to_text(item) for item in value]
    normalized = [item for item in normalized if item]
    return normalized if normalized else list(fallback)


def _to_option_entry(value: Any, *, fallback_label: str, fallback_value: str) -> tuple[str, str]:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2:
            label = _to_text(value[0]) or fallback_label
            val = _to_text(value[1]) or fallback_value
            return label, val
        return fallback_label, fallback_value

    if isinstance(value, dict):
        label = _to_text(
            value.get("label") or value.get("title") or value.get("name"),
        ) or fallback_label
        val = _to_text(value.get("value"))
        if not val:
            return fallback_label, fallback_value
        return label, val

    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized, normalized

    return fallback_label, fallback_value


def _to_model_options(value: Any, fallback: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return copy.deepcopy(fallback)
    output: list[dict[str, str]] = []
    for entry in value:
        if isinstance(entry, dict):
            normalized: dict[str, str] = {}
            for key, raw in entry.items():
                if not isinstance(key, str):
                    continue
                candidate = _to_text(raw)
                if candidate:
                    normalized[key.strip()] = candidate

            label = normalized.get("label") or normalized.get("title") or "Model"
            value = normalized.get("value") or "model"
            normalized["label"] = label
            normalized["value"] = value
            output.append(normalized)
            continue

        if isinstance(entry, (list, tuple)):
            label, val = _to_option_entry(
                entry,
                fallback_label="Model",
                fallback_value="model",
            )
            output.append({"label": label, "value": val})
            continue

        if isinstance(entry, str):
            cleaned = entry.strip()
            if cleaned:
                output.append({"label": cleaned, "value": cleaned})
            continue

        label, val = _to_option_entry(
            entry,
            fallback_label="Model",
            fallback_value="model",
        )
        output.append({"label": label, "value": val})
    return output if output else copy.deepcopy(fallback)


def _to_permission_options(value: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return copy.deepcopy(fallback)
    output: list[dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, (list, tuple)):
            label, val = _to_option_entry(
                entry,
                fallback_label="Permission",
                fallback_value="auto",
            )
            is_advanced = _to_bool(
                entry[2] if len(entry) > 2 else False,
                fallback=False,
            )
            output.append({"label": label, "value": val, "is_advanced": is_advanced})
            continue

        if isinstance(entry, dict):
            label = _to_text(
                entry.get("label") or entry.get("title"),
            ) or "Permission"
            val = _to_text(entry.get("value")) or "auto"
            is_advanced = _to_bool(
                entry.get("is_advanced"),
                fallback=False,
            )
            output.append({"label": label, "value": val, "is_advanced": is_advanced})
            continue

        if isinstance(entry, str):
            cleaned = entry.strip()
            if cleaned:
                output.append({"label": cleaned, "value": cleaned, "is_advanced": False})

    return output if output else copy.deepcopy(fallback)


def _to_reasoning_options(value: Any, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return copy.deepcopy(fallback)
    output: list[dict[str, str]] = []
    for entry in value:
        if isinstance(entry, (list, tuple)):
            title = _to_text(entry[0]) or "Reasoning"
            val = _to_text(entry[1]) if len(entry) > 1 else "medium"
            desc = _to_text(entry[2]) if len(entry) > 2 else ""
            if not val:
                continue
            output.append(
                {
                    "title": title,
                    "value": val,
                    "description": desc,
                }
            )
            continue

        if isinstance(entry, dict):
            title = _to_text(entry.get("label") or entry.get("title") or "Reasoning")
            val = _to_text(entry.get("value")) or "medium"
            desc = _to_text(
                entry.get("description"),
            ) or "Reasoning option"
            output.append({"title": title, "value": val, "description": desc})
            continue

        if isinstance(entry, str):
            cleaned = entry.strip()
            if cleaned:
                output.append({"title": cleaned, "value": cleaned, "description": "Reasoning option"})

    return output if output else copy.deepcopy(fallback)


def _normalize_colors(value: Any, fallback: dict[str, str]) -> dict[str, str]:
    normalized = dict(fallback)
    if not isinstance(value, dict):
        return normalized
    for key, val in value.items():
        if not isinstance(key, str):
            continue
        text = _to_text(val)
        if text:
            normalized[key] = text
    return normalized


def _normalize_provider(payload: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    fallback_colors = fallback.get("colors", {})
    fallback_model = fallback.get("model_options", [])
    fallback_perm = fallback.get("permission_options", [])

    if not isinstance(payload, dict):
        return copy.deepcopy(fallback)

    normalized_provider_id = _to_text(payload.get("id")) or _to_text(fallback.get("id")) or "claude"
    provider_default_icon = f"{normalized_provider_id}.svg"
    if normalized_provider_id.lower() == "claude":
        provider_default_icon = "claude-color.svg"
    elif normalized_provider_id.lower() == "codex":
        provider_default_icon = "codex-white.svg"

    normalized: dict[str, Any] = {
        "id": _to_text(payload.get("id")) or fallback.get("id", "claude"),
        "name": _to_text(payload.get("name")) or fallback.get("name", "Claude"),
        "icon": _to_text(payload.get("icon")) or fallback.get("icon") or provider_default_icon,
        "binary_names": _to_string_list(payload.get("binary_names"), fallback.get("binary_names", [])),
        "colors": _normalize_colors(payload.get("colors"), fallback_colors),
        "accent_rgb": _to_rgb(payload.get("accent_rgb"), tuple(fallback.get("accent_rgb", (0, 0, 0)))),
        "accent_soft_rgb": _to_rgb(
            payload.get("accent_soft_rgb"),
            tuple(fallback.get("accent_soft_rgb", (0, 0, 0))),
        ),
        "model_options": _to_model_options(payload.get("model_options"), fallback_model),
        "permission_options": _to_permission_options(payload.get("permission_options"), fallback_perm),
        "supports_reasoning": _to_bool(payload.get("supports_reasoning"), bool(fallback.get("supports_reasoning", True))),
    }

    normalized_provider_id = _to_text(normalized.get("id")) or normalized_provider_id
    provider_id_lower = str(normalized_provider_id).strip().lower()
    icon_value = str(normalized["icon"] or "").strip()
    icon_name = Path(icon_value).name.lower()
    has_explicit_path = ("/" in icon_value) or ("\\" in icon_value) or icon_value.startswith(".")
    if provider_id_lower == "claude" and (
        (
            not has_explicit_path
            and icon_name
            in {
                "claude",
                "claude.svg",
                "claude-color.svg",
                "claude-text.svg",
                "read",
                "✺",
                "claude (1).svg",
                "claude-color (1).svg",
                "claude-text (1).svg",
            }
        )
        or icon_name.startswith("claude-text")
    ):
        normalized["icon"] = "claude-color.svg"
    elif provider_id_lower == "codex" and (
        (not has_explicit_path and icon_name in {
            "codex",
            "codex.svg",
            "codex-color.svg",
            "codex-text.svg",
            "codex-white.svg",
            "read",
            "⌘",
            "codex-text (1).svg",
            "codex (1).svg",
        })
        or (not has_explicit_path and icon_name.startswith("codex-text"))
    ):
        normalized["icon"] = "codex-white.svg"
    elif icon_name == "⌘" and provider_id_lower == "codex":
        normalized["icon"] = "codex-white.svg"

    return normalized


def _normalize_settings(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return get_default_settings()

    fallback = get_default_settings()
    raw_providers = payload.get("providers")
    normalized_providers: dict[str, dict[str, Any]] = {}
    if isinstance(raw_providers, dict):
        for key, value in raw_providers.items():
            if not key:
                continue
            provider_id = _to_text(key)
            fallback_provider = fallback["providers"].get(provider_id)
            if not isinstance(fallback_provider, dict):
                continue
            normalized_providers[provider_id] = _normalize_provider(value, fallback_provider)

    if not normalized_providers:
        normalized_providers = copy.deepcopy(fallback["providers"])

    preferred_provider_id = _to_text(payload.get("active_provider_id")).lower()
    if not preferred_provider_id:
        preferred_provider_id = _to_text(fallback.get("active_provider_id")).lower()
    if preferred_provider_id not in normalized_providers:
        preferred_provider_id = next(iter(normalized_providers.keys()))

    return {
        "providers": normalized_providers,
        "reasoning_options": _to_reasoning_options(
            payload.get("reasoning_options"),
            fallback["reasoning_options"],
        ),
        "agentctl_auto_enabled": _to_bool(
            payload.get("agentctl_auto_enabled"),
            bool(fallback.get("agentctl_auto_enabled", True)),
        ),
        "system_tray_enabled": _to_bool(
            payload.get("system_tray_enabled"),
            bool(fallback.get("system_tray_enabled", True)),
        ),
        "active_provider_id": preferred_provider_id,
        "stream_render_throttle_ms": _to_int_range(
            payload.get("stream_render_throttle_ms"),
            _to_int_range(fallback.get("stream_render_throttle_ms"), 80, minimum=0, maximum=1500),
            minimum=0,
            maximum=1500,
        ),
    }


def get_reasoning_options(payload: dict[str, Any] | None = None) -> list[tuple[str, str, str]]:
    settings_payload = payload if isinstance(payload, dict) else load_settings()
    reasoning_payload = settings_payload.get("reasoning_options")
    options = _to_reasoning_options(reasoning_payload, get_default_settings()["reasoning_options"])
    result: list[tuple[str, str, str]] = []

    for entry in options:
        title = _to_text(entry.get("title"))
        value = _to_text(entry.get("value"))
        if not value:
            continue
        if not title:
            title = value
        description = _to_text(entry.get("description") or "")
        result.append((title, value, description))

    if not result:
        return [("Low (Fast)", "low", "Fast responses with standard reasoning.")]
    return result


def load_settings(*, path: Path | None = None) -> dict[str, Any]:
    """Load settings from disk and normalize them into a stable payload shape."""
    settings_path = path or APP_SETTINGS_PATH
    if settings_path is None or not settings_path.is_file():
        return get_default_settings()
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return get_default_settings()

    return _normalize_settings(payload)


def parse_settings_text(raw_text: str) -> dict[str, Any]:
    """Parse user-entered JSON and normalize the payload."""
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError("Settings JSON cannot be empty.")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid settings JSON: {error}") from error
    return _normalize_settings(payload)


def save_settings(payload: Any, *, path: Path | None = None) -> dict[str, Any]:
    normalized = _normalize_settings(payload)
    settings_path = path or APP_SETTINGS_PATH
    ensure_config_dir()
    _atomic_write(
        settings_path,
        json.dumps(normalized, indent=2, ensure_ascii=False),
    )
    return normalized


def format_settings_payload(payload: Any) -> str:
    return json.dumps(_normalize_settings(payload), indent=2, ensure_ascii=False)
