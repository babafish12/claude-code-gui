"""Provider registry backed by application settings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import threading
from types import MappingProxyType

from claude_code_gui.domain.app_settings import DEFAULT_APP_SETTINGS, load_settings

ModelOption = tuple[str, str]
PermissionOption = tuple[str, str, bool]
ColorTokens = dict[str, str]
AccentRgb = tuple[int, int, int]

_DISCOVERED_MODEL_OPTIONS: dict[str, tuple[ModelOption, ...]] = {}
_PROVIDERS_LOCK = threading.RLock()


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    name: str
    icon: str
    binary_names: tuple[str, ...]
    colors: ColorTokens
    accent_rgb: AccentRgb
    accent_soft_rgb: AccentRgb
    model_options: tuple[ModelOption, ...]
    permission_options: tuple[PermissionOption, ...]
    supports_reasoning: bool

    @property
    def display_name(self) -> str:
        return self.name


def _coerce_rgb(raw_value: object, fallback: AccentRgb) -> AccentRgb:
    if not isinstance(raw_value, (list, tuple)) or len(raw_value) < 3:
        return fallback
    output: list[int] = []
    for value in raw_value[:3]:
        try:
            item = int(value)
        except (TypeError, ValueError):
            return fallback
        if item < 0 or item > 255:
            return fallback
        output.append(item)
    return (output[0], output[1], output[2])


def _coerce_text(value: object, *, fallback: str) -> str:
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return fallback


def _coerce_model_options(raw_value: object, fallback: tuple[ModelOption, ...]) -> tuple[ModelOption, ...]:
    if not fallback:
        fallback = (
            ("claude", "sonnet"),
            ("opus", "opus"),
            ("haiku", "haiku"),
        )

    if not isinstance(raw_value, list) or not raw_value:
        return fallback or (
            ("claude", "sonnet"),
            ("opus", "opus"),
            ("haiku", "haiku"),
        )

    options: list[ModelOption] = []
    for entry in raw_value:
        if isinstance(entry, (list, tuple)):
            if len(entry) >= 2:
                label = _coerce_text(entry[0], fallback="Model")
                value = _coerce_text(entry[1], fallback="model")
                options.append((label, value))
            continue
        if isinstance(entry, dict):
            label = _coerce_text(entry.get("label") or entry.get("title"), fallback="Model")
            value = _coerce_text(entry.get("value"), fallback="model")
            options.append((label, value))
            continue
        if isinstance(entry, str):
            label = _coerce_text(entry, fallback="Model")
            options.append((label, label))
    return tuple(options) if options else (("Model", "model"),)


def _coerce_discovered_model_options(raw_value: object) -> tuple[ModelOption, ...]:
    if not isinstance(raw_value, (list, tuple)):
        return ()

    options: list[ModelOption] = []
    for entry in raw_value:
        if isinstance(entry, (tuple, list)):
            if len(entry) >= 2:
                label = _coerce_text(entry[0], fallback="Model")
                value = _coerce_text(entry[1], fallback="model")
                options.append((label, value))
            continue
        if isinstance(entry, dict):
            label = _coerce_text(
                entry.get("label") or entry.get("title"),
                fallback=_coerce_text(entry.get("value"), fallback="Model"),
            )
            value = _coerce_text(entry.get("value"), fallback="model")
            options.append((label, value))
            continue
        if isinstance(entry, str):
            value = _coerce_text(entry, fallback="model")
            options.append((value, value))

    deduped: list[ModelOption] = []
    seen: set[str] = set()
    for label, value in options:
        normalized_value = _coerce_text(value, fallback="")
        if not normalized_value or normalized_value in seen:
            continue
        seen.add(normalized_value)
        deduped.append((label, normalized_value))

    return tuple(deduped)


def _merge_model_options(
    discovered: tuple[ModelOption, ...],
    configured: tuple[ModelOption, ...],
) -> tuple[ModelOption, ...]:
    merged: list[ModelOption] = []
    seen: set[str] = set()
    for label, value in discovered + configured:
        normalized = _coerce_text(value, fallback="")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append((label, normalized))
    return tuple(merged) if merged else configured


def _normalize_discovered_model_overrides(
    discovered_model_options: object | None,
) -> dict[str, tuple[ModelOption, ...]]:
    if not isinstance(discovered_model_options, dict):
        return {}

    normalized: dict[str, tuple[ModelOption, ...]] = {}
    for provider_id, raw_models in discovered_model_options.items():
        if not isinstance(provider_id, str):
            continue
        provider_key = provider_id.strip().lower()
        if not provider_key:
            continue
        normalized_models = _coerce_discovered_model_options(raw_models)
        if normalized_models:
            normalized[provider_key] = normalized_models
    return normalized


def _coerce_permission_options(raw_value: object) -> tuple[PermissionOption, ...]:
    if not isinstance(raw_value, list) or not raw_value:
        return (
            ("Auto", "auto", False),
            ("Plan mode", "plan", False),
            ("Bypass permissions", "bypassPermissions", True),
        )

    options: list[PermissionOption] = []
    for entry in raw_value:
        if isinstance(entry, (list, tuple)):
            if len(entry) >= 2:
                label = _coerce_text(entry[0], fallback="Permission")
                value = _coerce_text(entry[1], fallback="auto")
                is_advanced = bool(entry[2]) if len(entry) > 2 else False
                options.append((label, value, is_advanced))
            continue
        if isinstance(entry, dict):
            label = _coerce_text(entry.get("label") or entry.get("title"), fallback="Permission")
            value = _coerce_text(entry.get("value"), fallback="auto")
            advanced = bool(entry.get("is_advanced"))
            options.append((label, value, advanced))
            continue
        if isinstance(entry, str):
            label = _coerce_text(entry, fallback="Permission")
            options.append((label, label, False))
    return tuple(options) if options else (("Permission", "auto", False),)


def _coerce_provider_colors(raw_value: object, fallback: ColorTokens) -> ColorTokens:
    if not isinstance(fallback, dict):
        fallback = DEFAULT_APP_SETTINGS["providers"]["claude"]["colors"]
    colors = dict(fallback)
    if not isinstance(raw_value, dict):
        return colors
    for key, value in raw_value.items():
        if not isinstance(key, str):
            continue
        text = _coerce_text(value, fallback="")
        if text:
            colors[key] = text
    return colors


def _coerce_provider(
    payload: object,
    provider_id: str,
    discovered_models: dict[str, tuple[ModelOption, ...]],
) -> ProviderConfig:
    provider_key = str(provider_id or "").strip().lower()
    provider_payload = payload if isinstance(payload, dict) else {}
    fallback_payload = DEFAULT_APP_SETTINGS["providers"].get(provider_id, {})
    fallback_models = _coerce_discovered_model_options(fallback_payload.get("model_options"))
    configured_model_options = _coerce_model_options(
        provider_payload.get("model_options")
        if isinstance(provider_payload, dict)
        else fallback_payload.get("model_options"),
        fallback=fallback_models,
    )
    colors = _coerce_provider_colors(
        provider_payload.get("colors") if isinstance(provider_payload, dict) else None,
        fallback_payload.get("colors", {}),
    )

    icon = _coerce_text(
        provider_payload.get("icon") if isinstance(provider_payload, dict) else fallback_payload.get("icon", ""),
        fallback=fallback_payload.get("icon", ""),
    )
    if not icon:
        icon = str(fallback_payload.get("icon", "")).strip() or f"{provider_id}.svg"
    icon_name = str(icon).strip().lower()
    has_explicit_path = ("/" in icon_name) or ("\\" in icon_name) or icon_name.startswith(".")
    if provider_id == "claude" and (
        (not has_explicit_path and icon_name in {
            "claude",
            "claude.svg",
            "claude-color.svg",
            "claude-text.svg",
            "read",
            "✺",
            "claude (1).svg",
            "claude-color (1).svg",
            "claude-text (1).svg",
        })
        or icon_name.startswith("claude-text")
    ):
        icon = "claude-color.svg"
    elif provider_id == "codex" and (
        icon_name == "⌘"
        or icon_name == "codex-white.svg"
        or icon_name == "codex-white"
        or (not has_explicit_path and icon_name in {
            "codex-color.svg",
            "codex-text.svg",
            "codex.svg",
            "codex-text (1).svg",
            "codex (1).svg",
            "read",
            "codex",
        })
        or icon_name.startswith("codex-text")
    ):
        icon = "codex-white.svg"
    elif provider_id == "gemini" and (
        (not has_explicit_path and icon_name in {
            "gemini",
            "gemini.svg",
            "gemini-color.svg",
            "google-gemini.svg",
        })
        or (not has_explicit_path and icon_name.startswith("gemini"))
    ):
        icon = "gemini-color.svg"
    if not icon:
        icon = str(fallback_payload.get("icon", "")).strip()

    raw_binary_names = (
        provider_payload.get("binary_names")
        if isinstance(provider_payload, dict) and isinstance(provider_payload.get("binary_names"), list)
        else fallback_payload.get("binary_names", [])
    )
    if not isinstance(raw_binary_names, list):
        raw_binary_names = []

    supports_reasoning = bool(
        provider_payload.get("supports_reasoning", fallback_payload.get("supports_reasoning", True))
        if isinstance(provider_payload, dict)
        else fallback_payload.get("supports_reasoning", True),
    )
    if provider_key == "gemini":
        supports_reasoning = False

    return ProviderConfig(
        id=_coerce_text(provider_payload.get("id"), fallback=provider_id),
        name=_coerce_text(provider_payload.get("name"), fallback=fallback_payload.get("name", "Claude")),
        icon=icon or _coerce_text(fallback_payload.get("icon"), fallback=f"{provider_id}.svg"),
        binary_names=tuple(
            _coerce_text(name, fallback="").lower().strip()
            for name in raw_binary_names
            if isinstance(name, str) and _coerce_text(name, fallback="").strip()
        ),
        colors=colors,
        accent_rgb=_coerce_rgb(
            provider_payload.get("accent_rgb"),
            _coerce_rgb(
                fallback_payload.get("accent_rgb"),
                fallback=(0, 0, 0),
            ),
        ),
        accent_soft_rgb=_coerce_rgb(
            provider_payload.get("accent_soft_rgb"),
            _coerce_rgb(
                fallback_payload.get("accent_soft_rgb"),
                fallback=(0, 0, 0),
            ),
        ),
        model_options=_merge_model_options(
            discovered_models.get(provider_id, ()),
            configured_model_options,
        ),
        permission_options=_coerce_permission_options(
            provider_payload.get("permission_options")
            if isinstance(provider_payload, dict)
            else fallback_payload.get("permission_options"),
        ),
        supports_reasoning=supports_reasoning,
    )


def _build_providers(
    payload: dict[str, object] | None = None,
    discovered_model_options: dict[str, tuple[ModelOption, ...]] | None = None,
) -> dict[str, ProviderConfig]:
    normalized = load_settings() if payload is None else payload
    if not isinstance(normalized, dict):
        normalized = DEFAULT_APP_SETTINGS

    raw_default = DEFAULT_APP_SETTINGS.get("providers", {})
    raw_from_payload = normalized.get("providers", {}) if isinstance(normalized, dict) else {}
    merged_payload: dict[str, object] = {}

    if isinstance(raw_default, dict):
        for provider_id, provider_data in raw_default.items():
            merged_payload[str(provider_id)] = provider_data if isinstance(provider_data, dict) else {}

    if isinstance(raw_from_payload, dict):
        for provider_id, provider_data in raw_from_payload.items():
            if isinstance(provider_id, str) and provider_id.strip() and isinstance(provider_data, dict):
                merged_payload[provider_id.strip()] = provider_data

    providers: dict[str, ProviderConfig] = {}
    provider_discovery = _DISCOVERED_MODEL_OPTIONS
    if discovered_model_options is not None:
        provider_discovery = dict(_DISCOVERED_MODEL_OPTIONS)
        provider_discovery.update(discovered_model_options)

    for provider_id, provider_payload in merged_payload.items():
        providers[provider_id] = _coerce_provider(
            provider_payload,
            provider_id,
            provider_discovery,
        )

    return providers


DEFAULT_PROVIDER_ID = "claude"
_providers_view: Mapping[str, ProviderConfig] = MappingProxyType(_build_providers())


class _ProviderRegistryAlias(Mapping[str, ProviderConfig]):
    """Read-only alias that always resolves against the latest registry snapshot."""

    def __getitem__(self, key: str) -> ProviderConfig:
        return _providers_view[key]

    def __iter__(self):
        return iter(_providers_view)

    def __len__(self) -> int:
        return len(_providers_view)


PROVIDERS: Mapping[str, ProviderConfig] = _ProviderRegistryAlias()


def get_providers() -> Mapping[str, ProviderConfig]:
    return _providers_view


def refresh_provider_registry(
    payload: dict[str, object] | None = None,
    *,
    detected_model_options: dict[str, object] | None = None,
) -> Mapping[str, ProviderConfig]:
    """Reload providers from app settings and update the global registry."""
    global _providers_view
    normalized_discovery = _normalize_discovered_model_overrides(detected_model_options)
    with _PROVIDERS_LOCK:
        if normalized_discovery:
            _DISCOVERED_MODEL_OPTIONS.update(normalized_discovery)
        updated_registry = _build_providers(payload, _DISCOVERED_MODEL_OPTIONS)
        _providers_view = MappingProxyType(updated_registry)
    return _providers_view


def normalize_provider_id(raw_value: str | None) -> str:
    providers = get_providers()
    candidate = str(raw_value or DEFAULT_PROVIDER_ID).strip().lower()
    if candidate in providers:
        return candidate
    if DEFAULT_PROVIDER_ID in providers:
        return DEFAULT_PROVIDER_ID
    return next(iter(providers.keys()), DEFAULT_PROVIDER_ID)


def get_provider_config(provider_id: str) -> ProviderConfig:
    providers = get_providers()
    return providers[normalize_provider_id(provider_id)]
