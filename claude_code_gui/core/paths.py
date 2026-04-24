"""Path normalization and user-facing path formatting."""

from __future__ import annotations

import os
from pathlib import Path


def normalize_folder(path_value: str) -> str:
    return str(Path(path_value).expanduser().resolve())


def format_path(path_value: str) -> str:
    home = str(Path.home())
    if path_value == home:
        return "~"
    if path_value.startswith(home + os.sep):
        return "~" + path_value[len(home) :]
    return path_value


def shorten_path(path_value: str, max_length: int) -> str:
    if len(path_value) <= max_length:
        return path_value
    keep = max(10, (max_length - 1) // 2)
    return f"{path_value[:keep]}…{path_value[-keep:]}"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_icon_path(icon_name: str = "claude.svg") -> Path | None:
    candidate = project_root() / "icons" / icon_name
    if candidate.is_file():
        return candidate
    return None
