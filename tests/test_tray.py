import json
import subprocess
from io import StringIO
from unittest.mock import MagicMock

import pytest


class _FakeThread:
    def __init__(self, *, target=None, daemon=None, **_kwargs):
        self._target = target
        self.daemon = daemon

    def start(self) -> None:
        return None


def test_tray_icon_import() -> None:
    from claude_code_gui.ui.tray import TrayIcon

    assert TrayIcon is not None


def test_tray_icon_init_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from claude_code_gui.ui import tray as tray_module
    from claude_code_gui.ui.tray import TrayIcon

    class DummyApp:
        pass

    def dummy_cb() -> None:
        pass

    mock_process = MagicMock()
    mock_process.stdin = StringIO()
    mock_process.stdout = StringIO(json.dumps({"event": "ready"}) + "\n")
    mock_process.poll.return_value = None

    def mock_popen(*args, **kwargs):
        return mock_process

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(tray_module.threading, "Thread", _FakeThread)

    app = DummyApp()
    tray = TrayIcon(app, on_show=dummy_cb, on_new_pane=dummy_cb, on_quit=dummy_cb)

    assert tray.available is False
    tray._read_loop()
    assert tray.available is True

    # Test set_attention writes the correct JSON line
    tray.set_attention(True)
    output = mock_process.stdin.getvalue()
    assert json.loads(output.strip().split("\n")[-1]) == {"cmd": "set_attention", "active": True}

    tray.set_attention(False)
    output = mock_process.stdin.getvalue()
    assert json.loads(output.strip().split("\n")[-1]) == {"cmd": "set_attention", "active": False}


def test_tray_icon_stays_unavailable_when_helper_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from claude_code_gui.ui import tray as tray_module
    from claude_code_gui.ui.tray import TrayIcon

    class DummyApp:
        pass

    mock_process = MagicMock()
    mock_process.stdin = StringIO()
    mock_process.stdout = StringIO(json.dumps({"error": "missing gi"}) + "\n")
    mock_process.poll.return_value = None

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: mock_process)
    monkeypatch.setattr(tray_module.threading, "Thread", _FakeThread)

    tray = TrayIcon(DummyApp())

    assert tray.available is False
    tray._read_loop()
    assert tray.available is False


def test_tray_icon_init_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from claude_code_gui.ui.tray import TrayIcon

    class DummyApp:
        pass

    def dummy_cb() -> None:
        pass

    def mock_popen_fail(*args, **kwargs):
        raise FileNotFoundError("Mock file not found")

    monkeypatch.setattr(subprocess, "Popen", mock_popen_fail)

    app = DummyApp()
    tray = TrayIcon(app, on_show=dummy_cb, on_new_pane=dummy_cb, on_quit=dummy_cb)

    assert tray.available is False

    # Also test set_attention is a no-op
    tray.set_attention(True)
