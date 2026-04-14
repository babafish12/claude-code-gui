"""Application-wide constants: sizing, session statuses, model/permission options."""

from __future__ import annotations

from claude_code_gui.domain.provider import DEFAULT_PROVIDER_ID, get_provider_config

APP_NAME = "Claude Code"
APP_MIN_WIDTH = 900
APP_MIN_HEIGHT = 600
APP_DEFAULT_WIDTH = 1440
APP_DEFAULT_HEIGHT = 920
SIDEBAR_OPEN_WIDTH = 292
SIDEBAR_COLLAPSED_WIDTH = 40
CONTEXT_MAX_TOKENS = 200_000
ATTACHMENT_MAX_BYTES = 12 * 1024 * 1024

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_ENDED = "ended"
SESSION_STATUS_ARCHIVED = "archived"
SESSION_STATUS_ERROR = "error"
SESSION_STATUSES = {
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_ENDED,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_ERROR,
}

def get_model_options(provider: str = DEFAULT_PROVIDER_ID) -> list[tuple[str, str]]:
    return list(get_provider_config(provider).model_options)


MODEL_OPTIONS: list[tuple[str, str]] = get_model_options()

LEGACY_MODEL_ALIASES: dict[str, str] = {
    "default": "sonnet",
    "claude-sonnet-4-6": "sonnet",
    "claude-opus-4-6": "opus",
    "claude-haiku-4-5": "haiku",
}

def get_legacy_model_aliases(provider: str = DEFAULT_PROVIDER_ID) -> dict[str, str]:
    if provider == "claude":
        return LEGACY_MODEL_ALIASES
    return {}


def get_permission_options(provider: str = DEFAULT_PROVIDER_ID) -> list[tuple[str, str, bool]]:
    return list(get_provider_config(provider).permission_options)


PERMISSION_OPTIONS: list[tuple[str, str, bool]] = get_permission_options()

LEGACY_PERMISSION_ALIASES: dict[str, str] = {
    "ask": "auto",
    "default": "auto",
    "acceptEdits": "auto",
}


def get_legacy_permission_aliases(provider: str = DEFAULT_PROVIDER_ID) -> dict[str, str]:
    if provider == "claude":
        return LEGACY_PERMISSION_ALIASES
    return {}

CONNECTION_CONNECTED = "connected"
CONNECTION_DISCONNECTED = "disconnected"
CONNECTION_STARTING = "starting"
CONNECTION_ERROR = "error"

STATUS_MUTED = "muted"
STATUS_INFO = "info"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"
