from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import pytest
import pytest_mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _install_gi_stub() -> None:
    try:
        import gi  # type: ignore
        from gi.repository import GLib  # type: ignore

        def _idle_add(callback: Any, *args: Any, **_kwargs: Any) -> Any:
            return callback(*args)

        GLib.idle_add = _idle_add  # type: ignore[assignment]
        _ = gi
        return
    except Exception:
        pass

    gi_module = types.ModuleType("gi")

    def require_version(*_args: Any, **_kwargs: Any) -> None:
        return None

    repository_module = types.ModuleType("gi.repository")

    class _GLib:
        @staticmethod
        def idle_add(callback: Any, *args: Any, **_kwargs: Any) -> Any:
            return callback(*args)

    gi_module.require_version = require_version  # type: ignore[attr-defined]
    gi_module.repository = repository_module  # type: ignore[attr-defined]
    repository_module.GLib = _GLib  # type: ignore[attr-defined]

    sys.modules["gi"] = gi_module
    sys.modules["gi.repository"] = repository_module


_install_gi_stub()


class FakeStdin:
    def __init__(self) -> None:
        self.writes: list[str] = []

    def write(self, payload: str) -> None:
        self.writes.append(payload)

    def flush(self) -> None:
        return None


class FakeStdout:
    def __init__(self, lines: Iterable[str]) -> None:
        self._lines = [line if line.endswith("\n") else f"{line}\n" for line in lines]

    def __iter__(self):
        return iter(self._lines)


class FakePopen:
    def __init__(self, *, lines: Iterable[str], returncode: int) -> None:
        self.stdin = FakeStdin()
        self.stdout = FakeStdout(lines)
        self._returncode = returncode
        self._terminated = False
        self._killed = False

    def poll(self) -> int | None:
        if self._terminated or self._killed:
            return self._returncode
        return None

    def wait(self) -> int:
        return self._returncode

    def terminate(self) -> None:
        self._terminated = True

    def kill(self) -> None:
        self._killed = True


@dataclass
class _PopenSpec:
    lines: list[str]
    returncode: int = 0


@pytest.fixture
def fake_subprocess(mocker: pytest_mock.MockerFixture):
    queue: list[_PopenSpec] = []
    instances: list[FakePopen] = []
    calls: list[dict[str, Any]] = []

    def enqueue(*, lines: Iterable[str], returncode: int = 0) -> None:
        queue.append(_PopenSpec(lines=list(lines), returncode=returncode))

    def _fake_popen(*args: Any, **kwargs: Any) -> FakePopen:
        spec = queue.pop(0) if queue else _PopenSpec(lines=[], returncode=0)
        proc = FakePopen(lines=spec.lines, returncode=spec.returncode)
        instances.append(proc)
        calls.append({"args": args, "kwargs": kwargs})
        return proc

    patched = mocker.patch("subprocess.Popen", side_effect=_fake_popen)
    return SimpleNamespace(
        enqueue=enqueue,
        instances=instances,
        calls=calls,
        patched=patched,
    )
