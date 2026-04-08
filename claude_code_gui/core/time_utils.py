"""Timestamp helpers."""

from __future__ import annotations

from datetime import datetime


def current_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_timestamp(value: str) -> float:
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0
