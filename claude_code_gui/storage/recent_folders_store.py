"""IO for recent folders list persistence."""

from __future__ import annotations

import json
import os

from claude_code_gui.core.paths import normalize_folder
from claude_code_gui.storage.config_paths import (
    RECENT_FOLDERS_LIMIT,
    RECENT_FOLDERS_PATH,
    ensure_config_dir,
)


def load_recent_folders(default_folder: str) -> list[str]:
    ensure_config_dir()
    folders: list[str] = []

    if RECENT_FOLDERS_PATH.is_file():
        try:
            data = json.loads(RECENT_FOLDERS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        normalized = normalize_folder(item)
                        if os.path.isdir(normalized):
                            folders.append(normalized)
        except (OSError, json.JSONDecodeError, ValueError):
            folders = []

    merged = [normalize_folder(default_folder)] + folders
    deduped: list[str] = []
    for folder in merged:
        if folder not in deduped:
            deduped.append(folder)

    return deduped[:RECENT_FOLDERS_LIMIT]


def save_recent_folders(folders: list[str]) -> None:
    ensure_config_dir()
    RECENT_FOLDERS_PATH.write_text(json.dumps(folders[:RECENT_FOLDERS_LIMIT], indent=2), encoding="utf-8")
