"""Filesystem locations for application config and data."""

from __future__ import annotations

from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "claude-code-gui"
RECENT_FOLDERS_PATH = CONFIG_DIR / "recent_folders.json"
SESSIONS_PATH = CONFIG_DIR / "sessions.json"
APP_SETTINGS_PATH = CONFIG_DIR / "app_settings.json"
RECENT_FOLDERS_LIMIT = 10


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR
