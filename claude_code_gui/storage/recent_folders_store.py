"""IO for recent folders list persistence."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from claude_code_gui.core.paths import normalize_folder
from claude_code_gui.storage.config_paths import (
    RECENT_FOLDERS_LIMIT,
    RECENT_FOLDERS_PATH,
    ensure_config_dir,
)


def _lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


@contextmanager
def _store_lock(path: Path, *, exclusive: bool):
    lock_path = _lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_recent_folders(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []

    folders: list[str] = []
    for item in data:
        if not isinstance(item, str):
            continue
        try:
            folders.append(normalize_folder(item))
        except (OSError, ValueError):
            continue
    return folders


def _merge_recent_folders(memory_folders: list[str], file_folders: list[str]) -> list[str]:
    merged: list[str] = []
    for folder in list(memory_folders) + list(file_folders):
        if not isinstance(folder, str):
            continue
        try:
            normalized = normalize_folder(folder)
        except (OSError, ValueError):
            continue
        if normalized not in merged:
            merged.append(normalized)
    return merged[:RECENT_FOLDERS_LIMIT]


def load_recent_folders(default_folder: str) -> list[str]:
    ensure_config_dir()
    folders: list[str] = []

    with _store_lock(RECENT_FOLDERS_PATH, exclusive=False):
        for item in _read_recent_folders(RECENT_FOLDERS_PATH):
            if os.path.isdir(item):
                folders.append(item)

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
    with _store_lock(RECENT_FOLDERS_PATH, exclusive=True):
        merged = _merge_recent_folders(
            folders,
            _read_recent_folders(RECENT_FOLDERS_PATH),
        )
        _atomic_write(
            RECENT_FOLDERS_PATH,
            json.dumps(merged, indent=2),
        )
