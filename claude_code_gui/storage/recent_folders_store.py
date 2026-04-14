"""IO for recent folders list persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

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


def _atomic_write(path: Path, payload: str) -> None:
    if not payload:
        payload = "[]"
    temp_file: str | None = None
    try:
        fd, temp_file = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if temp_file is None:
            raise RuntimeError("Failed to allocate temporary file for recent folders write")
        os.replace(temp_file, path)
        _fsync_parent_dir(path)
    finally:
        if temp_file is not None and os.path.exists(temp_file):
            Path(temp_file).unlink()


def _fsync_parent_dir(path: Path) -> None:
    parent = path.parent
    if not parent.exists():
        return
    try:
        dir_fd = os.open(str(parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        return
    finally:
        os.close(dir_fd)


def save_recent_folders(folders: list[str]) -> None:
    ensure_config_dir()
    _atomic_write(
        RECENT_FOLDERS_PATH,
        json.dumps(folders[:RECENT_FOLDERS_LIMIT], indent=2),
    )
