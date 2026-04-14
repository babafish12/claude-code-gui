"""Model and permission normalization and label helpers."""

from __future__ import annotations

from claude_code_gui.app.constants import (
    SESSION_STATUS_ENDED,
    SESSION_STATUSES,
    get_legacy_model_aliases,
    get_legacy_permission_aliases,
    get_model_options,
    get_permission_options,
)


def model_label_from_value(model_value: str, provider: str = "claude") -> str:
    model_options = get_model_options(provider)
    for label, value in model_options:
        if value == model_value:
            return label
    return model_options[0][0]


def permission_label_from_value(permission_mode: str, provider: str = "claude") -> str:
    permission_options = get_permission_options(provider)
    for label, value, _ in permission_options:
        if value == permission_mode:
            return label
    return permission_options[0][0]


def normalize_model_value(raw_value: str | None, provider: str = "claude") -> str:
    model_options = get_model_options(provider)
    legacy_aliases = get_legacy_model_aliases(provider)
    candidate = str(raw_value or model_options[0][1]).strip()
    candidate = legacy_aliases.get(candidate, candidate)
    if candidate in {value for _, value in model_options}:
        return candidate
    return model_options[0][1]


def normalize_permission_value(raw_value: str | None, provider: str = "claude") -> str:
    permission_options = get_permission_options(provider)
    legacy_aliases = get_legacy_permission_aliases(provider)
    candidate = str(raw_value or permission_options[0][1]).strip()
    candidate = legacy_aliases.get(candidate, candidate)
    if candidate in {value for _, value, _ in permission_options}:
        return candidate
    return permission_options[0][1]


def normalize_session_status(raw_value: str | None) -> str:
    status = str(raw_value or SESSION_STATUS_ENDED).strip()
    if status in SESSION_STATUSES:
        return status
    return SESSION_STATUS_ENDED
