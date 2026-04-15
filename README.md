# Claude Code GUI

A native desktop chat UI for terminal-based AI coding agents — wraps the `claude` and `codex` CLIs in a GTK + WebKit shell so you keep your CLI workflow, but get panes, sessions, attachments, and a proper composer.

![Tests](https://github.com/babafish12/claude-code-gui/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)
![GTK](https://img.shields.io/badge/GTK-4%20%7C%203-green)

## Why

The official `claude` and `codex` CLIs are excellent, but a raw terminal is a poor host for multi-turn coding sessions: no persistent history across projects, no easy file attachments, no side-by-side panes, no image paste. `claude-code-gui` runs the same CLI binaries you already have and layers a first-class desktop chat around them — while staying local, hackable, and dependency-light.

## Features

- Native GTK/WebKit desktop app (GTK4 + WebKit6 preferred, GTK3 + WebKit2 fallback)
- Multi-pane workspace — run several agent sessions side by side
- Provider switching between `claude` / `claude-code` and `codex` with per-provider theming
- Session persistence, chat search, and recent-folder tracking
- Attachments via file picker, drag-and-drop, and clipboard images
- Rich chat rendering: syntax highlighting, markdown, emoji, inline images with lightbox
- Diff/review workflow and artifacts panel
- Tool-call confirmation dialogs and desktop notifications for long-running tasks
- Git/PR cards with CI status indicators
- Settings editor for models, reasoning levels, permissions, and themes
- Hardened persistence: atomic writes, payload validation, pane lifecycle guards

## Requirements

- Python `>= 3.11`
- PyGObject (`gi`) with one of these runtime stacks:
  - **GTK4 + WebKit6** (preferred)
  - **GTK3 + WebKit2** (fallback)
- At least one provider CLI on `PATH`:
  - `claude` or `claude-code` ([install](https://docs.claude.com/en/docs/claude-code))
  - `codex` (optional — requires prior `codex login`)

### System packages

Ubuntu / Debian — GTK4 path:

```bash
sudo apt-get install -y python3-gi gir1.2-gtk-4.0 gir1.2-webkit-6.0
```

Ubuntu / Debian — GTK3 fallback:

```bash
sudo apt-get install -y python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

Arch Linux — GTK4 path:

```bash
sudo pacman -S python-gobject gtk4 webkitgtk-6.0
```

Fedora — GTK4 path:

```bash
sudo dnf install python3-gobject gtk4 webkitgtk6.0
```

## Quick Start

```bash
git clone https://github.com/babafish12/claude-code-gui.git
cd claude-code-gui
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m claude_code_gui
```

## Usage

1. Launch with `python -m claude_code_gui`.
2. Pick a project folder via the folder button near the composer (recent folders are remembered).
3. Type a prompt, or attach files with `+` / drag-and-drop / paste an image from the clipboard.
4. Send. Streaming responses render live in the chat pane.
5. Open a second pane to run a parallel session in the same or a different project.
6. Switch providers from the sidebar; settings per provider (model, reasoning effort, permissions) live in the settings editor.

## Configuration

User state lives under `~/.config/claude-code-gui/`:

| File | Purpose |
|------|---------|
| `sessions.json` | Persisted chat sessions |
| `recent_folders.json` | Recently opened project folders |
| `app_settings.json` | Per-provider models, reasoning levels, permissions, theme |

Bundled defaults ship at:

- `claude_code_gui/config/default_app_settings.json`
- `claude_code_gui/config/provider_theme_settings.json`

Provider binaries are auto-discovered from `PATH` and common install locations (`~/.local/bin`, `~/.nvm/...`, Homebrew prefixes).

## Architecture

| Path | Role |
|------|------|
| `claude_code_gui/ui/window.py` | Main window, pane management, WebView ↔ Python bridge |
| `claude_code_gui/runtime/claude_process.py` | CLI subprocess lifecycle, stream/event parsing |
| `claude_code_gui/domain/cli_dialect.py` | Provider-specific argv building (Claude vs Codex) |
| `claude_code_gui/domain/provider.py` | Provider detection, capability matrix |
| `claude_code_gui/assets/chat_template.py` | Embedded HTML/CSS/JS for the WebView chat frontend |
| `claude_code_gui/services/attachment_service.py` | File / image / clipboard attachment pipeline |
| `claude_code_gui/services/binary_probe.py` | CLI binary discovery and auth probing |
| `claude_code_gui/storage/*.py` | Atomic persistence for sessions, settings, recents |

The WebView renders chat HTML and talks to Python over a JS bridge; Python owns the CLI subprocess and normalizes provider-specific event streams into a single UI model.

## Development

Install with test extras:

```bash
pip install -e .[test]
```

Run the default test suite:

```bash
pytest -m "unit or integration or gtk_css" --cov=claude_code_gui --cov-report=term-missing
```

Optional contract tests (hit real CLI binaries):

```bash
RUN_CONTRACT_TESTS=1 pytest -m "contract" -q
```

Lint:

```bash
ruff check
```

## Troubleshooting

- **"CLI not found"** — install `claude`, `claude-code`, or `codex` and verify it's on `PATH` (`which claude`).
- **Codex shows as unavailable** — run `codex login` in a terminal, then restart the app.
- **Blank window or startup crash** — check that the matching GTK/WebKit GI packages are installed for your stack (see [Requirements](#requirements)). Run with `G_MESSAGES_DEBUG=all python -m claude_code_gui` for verbose logs.
- **Clipboard image paste fails on Wayland** — some compositors require `wl-clipboard`; install it and retry.

## Change History

### 2026-04-15
- Replaced README with full project documentation.
- Hardened WebView bridge handling and persistence across panes (atomic writes, payload validation, pane lifecycle guards).
- Fixed composer toggle wiring and folder/file action routing.
- Added artifacts toggle next to the composer `+` button.

### 2026-04-14
- Added multi-pane workspace — run multiple agent sessions side by side.
- Added long-wait status indicators and chat search.
- Added Codex provider support, broader UX polish, and the initial test suite.

### 2026-04-09
- Added git/PR cards with CI status indicators.
- Added diff/review workflow and artifacts panel.
- Added tool-call confirmation dialog, desktop notifications, and sidebar upgrade.
- Added rich chat rendering: syntax highlighting, emoji, images, and lightbox.
- Fixed message streaming and emoji rendering.
- Fixed XSS vulnerabilities in image rendering and JS bridge.

### 2026-04-08
- Rewrote GUI from a VTE terminal wrapper to a WebKit2 chat UI.
- Refactored the monolithic GUI into a modular Python package.
- Initial commit.

## Contributing

Bug reports and pull requests are welcome — open an issue first for anything larger than a small fix, so we can align on approach.

When contributing:

- Keep tests passing (`pytest`) and linting clean (`ruff check`).
- Match the existing provider dialect abstraction when adding CLI support — don't hardcode provider-specific logic into UI code.
- Don't commit generated coverage, venv, or editor artifacts.

## License

No license file is currently included. Until one is added, all rights are reserved by the authors; treat the code as source-available for personal use and evaluation only.
