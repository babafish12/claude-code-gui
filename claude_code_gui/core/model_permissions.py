"""Model and permission normalization and label helpers."""

from __future__ import annotations

from claude_code_gui.app.constants import (
    LEGACY_MODEL_ALIASES,
    LEGACY_PERMISSION_ALIASES,
    MODEL_OPTIONS,
    PERMISSION_OPTIONS,
    SESSION_STATUS_ENDED,
    SESSION_STATUSES,
)


def model_label_from_value(model_value: str) -> str:
    for label, value in MODEL_OPTIONS:
        if value == model_value:
            return label
    return MODEL_OPTIONS[0][0]


def permission_label_from_value(permission_mode: str) -> str:
    for label, value, _ in PERMISSION_OPTIONS:
        if value == permission_mode:
            return label
    return PERMISSION_OPTIONS[0][0]


def normalize_model_value(raw_value: str | None) -> str:
    candidate = str(raw_value or MODEL_OPTIONS[0][1]).strip()
    candidate = LEGACY_MODEL_ALIASES.get(candidate, candidate)
    if candidate in {value for _, value in MODEL_OPTIONS}:
        return candidate
    return MODEL_OPTIONS[0][1]


def normalize_permission_value(raw_value: str | None) -> str:
    candidate = str(raw_value or PERMISSION_OPTIONS[0][1]).strip()
    candidate = LEGACY_PERMISSION_ALIASES.get(candidate, candidate)
    if candidate in {value for _, value, _ in PERMISSION_OPTIONS}:
        return candidate
    return PERMISSION_OPTIONS[0][1]


def normalize_session_status(raw_value: str | None) -> str:
    status = str(raw_value or SESSION_STATUS_ENDED).strip()
    if status in SESSION_STATUSES:
        return status
    return SESSION_STATUS_ENDED
