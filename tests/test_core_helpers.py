from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime

import pytest

import claude_code_gui
from claude_code_gui.core import model_permissions, paths, time_utils

pytestmark = pytest.mark.unit


def test_package_getattr_rejects_unknown_symbol() -> None:
    with pytest.raises(AttributeError):
        claude_code_gui.__getattr__("NotARealSymbol")


def test_package_getattr_loads_symbol_from_gi_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    fake_runtime = types.ModuleType("claude_code_gui.gi_runtime")
    fake_runtime.Gtk = sentinel  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "claude_code_gui.gi_runtime", fake_runtime)
    monkeypatch.setattr(claude_code_gui, "gi_runtime", fake_runtime, raising=False)
    monkeypatch.delitem(claude_code_gui.__dict__, "Gtk", raising=False)

    value = claude_code_gui.__getattr__("Gtk")

    assert value is sentinel
    assert claude_code_gui.Gtk is sentinel


def test_model_permissions_labels_and_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        model_permissions,
        "get_model_options",
        lambda _provider="claude": [("Default Model", "model-default"), ("Fast", "model-fast")],
    )
    monkeypatch.setattr(
        model_permissions,
        "get_permission_options",
        lambda _provider="claude": [
            ("Auto", "auto", False),
            ("Plan", "plan", False),
        ],
    )
    monkeypatch.setattr(
        model_permissions,
        "get_legacy_model_aliases",
        lambda _provider="claude": {"legacy-fast": "model-fast"},
    )
    monkeypatch.setattr(
        model_permissions,
        "get_legacy_permission_aliases",
        lambda _provider="claude": {"acceptEdits": "auto"},
    )

    assert model_permissions.model_label_from_value("model-fast") == "Fast"
    assert model_permissions.model_label_from_value("unknown") == "Default Model"
    assert model_permissions.permission_label_from_value("plan") == "Plan"
    assert model_permissions.permission_label_from_value("unknown") == "Auto"

    assert model_permissions.normalize_model_value("legacy-fast") == "model-fast"
    assert model_permissions.normalize_model_value("not-valid") == "model-default"
    assert model_permissions.normalize_model_value(None) == "model-default"

    assert model_permissions.normalize_permission_value("acceptEdits") == "auto"
    assert model_permissions.normalize_permission_value("invalid") == "auto"
    assert model_permissions.normalize_permission_value(None) == "auto"

    assert model_permissions.normalize_session_status("active") == "active"
    assert model_permissions.normalize_session_status("invalid") == "ended"
    assert model_permissions.normalize_session_status(None) == "ended"


def test_paths_helpers(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = str(tmp_path / "a" / "..")
    assert paths.normalize_folder(raw) == str(tmp_path.resolve())

    monkeypatch.setattr(paths.Path, "home", lambda: tmp_path)
    assert paths.format_path(str(tmp_path)) == "~"
    assert paths.format_path(str(tmp_path / "project")) == "~/project"
    assert paths.format_path("/opt/project") == "/opt/project"

    long_path = "/very/" + ("long" * 20) + "/path"
    short = paths.shorten_path(long_path, 30)
    assert "…" in short
    assert short.startswith(long_path[:10])
    assert short.endswith(long_path[-10:])
    assert paths.shorten_path("/tmp/x", 50) == "/tmp/x"

    installed_icons = tmp_path / "prefix" / "share" / "claude-code-gui" / "icons"
    installed_icons.mkdir(parents=True)
    icon = installed_icons / "claude.svg"
    icon.write_text("<svg></svg>", encoding="utf-8")
    missing_root = tmp_path / "missing-root"
    missing_root.mkdir()
    monkeypatch.setattr(paths, "project_root", lambda: missing_root)
    monkeypatch.setattr(paths.sys, "prefix", str(tmp_path / "prefix"))
    monkeypatch.setattr(paths.sys, "base_prefix", str(tmp_path / "other-prefix"))
    monkeypatch.chdir(missing_root)
    assert paths.resolve_icons_dir() == installed_icons
    assert paths.resolve_icon_path("claude.svg") == icon


def test_time_utils_helpers() -> None:
    timestamp = time_utils.current_timestamp()
    parsed = datetime.fromisoformat(timestamp)

    assert parsed.microsecond == 0
    assert isinstance(time_utils.parse_timestamp(timestamp), float)
    assert time_utils.parse_timestamp("not-a-timestamp") == 0.0


def _run_main_with_stubs(monkeypatch: pytest.MonkeyPatch, *, gtk4: bool) -> list[str]:
    calls: list[str] = []

    class DummyWindow:
        def __init__(self, **kwargs) -> None:
            calls.append("window_init")

        def present(self) -> None:
            calls.append("present")

        def show_all(self) -> None:
            calls.append("show_all")

        def _split_active_pane(self, *_args) -> None:
            calls.append("split_pane")

    class DummyApp:
        def __init__(self, **kwargs) -> None:
            calls.append("app_init")

        def connect(self, signal, callback) -> None:
            if signal == "activate":
                self.activate_callback = callback
            elif signal == "handle-local-options":
                pass

        def add_main_option(self, *args, **kwargs) -> None:
            pass

        def run(self, argv) -> None:
            calls.append("app_run")
            if hasattr(self, "activate_callback"):
                self.activate_callback(self)

        def get_windows(self) -> list:
            return []

        def quit(self) -> None:
            calls.append("quit")

    class DummyTrayIcon:
        def __init__(self, *_args, **_kwargs) -> None:
            calls.append("tray_init")

    fake_runtime = types.ModuleType("claude_code_gui.gi_runtime")
    fake_runtime.GTK4 = gtk4  # type: ignore[attr-defined]
    fake_runtime.Gtk = types.SimpleNamespace(main=lambda: calls.append("gtk_main"))  # type: ignore[attr-defined]
    fake_runtime.Adw = types.SimpleNamespace(Application=DummyApp) if gtk4 else None # type: ignore[attr-defined]
    fake_runtime.Gio = types.SimpleNamespace(
        ApplicationFlags=types.SimpleNamespace(FLAGS_NONE=0),
        OptionFlags=types.SimpleNamespace(NONE=0),
        OptionArg=types.SimpleNamespace(NONE=0),
    ) # type: ignore[attr-defined]

    fake_window_module = types.ModuleType("claude_code_gui.ui.window")
    fake_window_module.ClaudeCodeWindow = DummyWindow  # type: ignore[attr-defined]
    fake_tray_module = types.ModuleType("claude_code_gui.ui.tray")
    fake_tray_module.TrayIcon = DummyTrayIcon  # type: ignore[attr-defined]
    fake_settings_module = types.ModuleType("claude_code_gui.domain.app_settings")
    fake_settings_module.load_settings = lambda: {"system_tray_enabled": True}  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "claude_code_gui.gi_runtime", fake_runtime)
    monkeypatch.setitem(sys.modules, "claude_code_gui.ui.window", fake_window_module)
    monkeypatch.setitem(sys.modules, "claude_code_gui.ui.tray", fake_tray_module)
    monkeypatch.setitem(sys.modules, "claude_code_gui.domain.app_settings", fake_settings_module)

    # Reload the module to use the mocked gi_runtime
    if "claude_code_gui.__main__" in sys.modules:
        importlib.reload(sys.modules["claude_code_gui.__main__"])
    main_module = importlib.import_module("claude_code_gui.__main__")
    main_module.main()
    return calls


def test_main_uses_present_for_gtk4(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _run_main_with_stubs(monkeypatch, gtk4=True) == [
        "app_init",
        "app_run",
        "window_init",
        "present",
        "tray_init",
    ]


def test_main_uses_show_all_for_gtk3(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _run_main_with_stubs(monkeypatch, gtk4=False) == [
        "window_init",
        "show_all",
        "gtk_main",
    ]
