"""Application-wide constants: sizing, session statuses, model/permission options."""

from __future__ import annotations

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

MODEL_OPTIONS: list[tuple[str, str]] = [
    ("Claude Sonnet (Latest)", "sonnet"),
    ("Claude Opus (Latest)", "opus"),
    ("Claude Haiku (Latest)", "haiku"),
]

LEGACY_MODEL_ALIASES: dict[str, str] = {
    "default": "sonnet",
    "claude-sonnet-4-6": "sonnet",
    "claude-opus-4-6": "opus",
    "claude-haiku-4-5": "haiku",
}

PERMISSION_OPTIONS: list[tuple[str, str, bool]] = [
    ("Auto", "auto", False),
    ("Plan mode", "plan", False),
    ("Bypass permissions (Advanced)", "bypassPermissions", True),
]

REASONING_LEVEL_OPTIONS: list[tuple[str, str]] = [
    ("Low (Fast)", "low"),
    ("Medium (Balanced)", "medium"),
    ("High (Deep)", "high"),
]

LEGACY_PERMISSION_ALIASES: dict[str, str] = {
    "ask": "auto",
    "default": "auto",
    "acceptEdits": "auto",
}

CONNECTION_CONNECTED = "connected"
CONNECTION_DISCONNECTED = "disconnected"
CONNECTION_STARTING = "starting"
CONNECTION_ERROR = "error"

STATUS_MUTED = "muted"
STATUS_INFO = "info"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"
