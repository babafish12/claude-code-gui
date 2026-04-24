from __future__ import annotations

import json

import pytest

from claude_code_gui.storage import recent_folders_store

pytestmark = pytest.mark.unit


def _patch_store_paths(
    monkeypatch: pytest.MonkeyPatch,
    *,
    path,
    limit: int,
) -> None:
    monkeypatch.setattr(recent_folders_store, "RECENT_FOLDERS_PATH", path)
    monkeypatch.setattr(recent_folders_store, "RECENT_FOLDERS_LIMIT", limit)
    monkeypatch.setattr(recent_folders_store, "ensure_config_dir", lambda: path.parent)


def test_load_recent_folders_filters_invalid_entries_and_dedupes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_folder = tmp_path / "default"
    extra_folder = tmp_path / "extra"
    missing_folder = tmp_path / "missing"
    default_folder.mkdir()
    extra_folder.mkdir()

    store_path = tmp_path / "recent_folders.json"
    store_path.write_text(
        json.dumps([str(extra_folder), str(missing_folder), str(default_folder), str(extra_folder)]),
        encoding="utf-8",
    )

    _patch_store_paths(monkeypatch, path=store_path, limit=10)
    loaded = recent_folders_store.load_recent_folders(str(default_folder))

    assert loaded == [str(default_folder.resolve()), str(extra_folder.resolve())]


def test_load_recent_folders_returns_default_for_invalid_json(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_folder = tmp_path / "default"
    default_folder.mkdir()
    store_path = tmp_path / "recent_folders.json"
    store_path.write_text("{not-json", encoding="utf-8")

    _patch_store_paths(monkeypatch, path=store_path, limit=10)
    loaded = recent_folders_store.load_recent_folders(str(default_folder))

    assert loaded == [str(default_folder.resolve())]


def test_save_recent_folders_persists_limited_payload(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_path = tmp_path / "recent_folders.json"
    _patch_store_paths(monkeypatch, path=store_path, limit=2)

    recent_folders_store.save_recent_folders(["/a", "/b", "/c"])

    saved = json.loads(store_path.read_text(encoding="utf-8"))
    assert saved == ["/a", "/b"]


def test_save_recent_folders_merges_existing_entries_without_losing_them(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_path = tmp_path / "recent_folders.json"
    store_path.write_text(json.dumps(["/disk-a", "/disk-b"]), encoding="utf-8")
    _patch_store_paths(monkeypatch, path=store_path, limit=4)

    recent_folders_store.save_recent_folders(["/memory-a", "/disk-a"])

    saved = json.loads(store_path.read_text(encoding="utf-8"))
    assert saved == ["/memory-a", "/disk-a", "/disk-b"]


def test_atomic_write_handles_empty_payload(tmp_path) -> None:
    target = tmp_path / "recent_folders.json"

    recent_folders_store._atomic_write(target, "")

    assert json.loads(target.read_text(encoding="utf-8")) == []


def test_fsync_parent_dir_handles_missing_parent(tmp_path) -> None:
    missing_parent_target = tmp_path / "missing-parent" / "recent_folders.json"
    recent_folders_store._fsync_parent_dir(missing_parent_target)
