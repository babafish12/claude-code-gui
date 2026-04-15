# Claude Code GUI

Desktop chat UI for Claude/Codex CLIs, built with GTK + WebKit.

![Tests](https://github.com/babafish12/claude-code-gui/actions/workflows/tests.yml/badge.svg)

## What It Is

`claude-code-gui` is a local desktop shell around terminal-based AI coding agents.
It gives you a chat composer, session history, pane/agent workflows, file attachments, and provider-aware settings while still using your installed CLI binaries.

## Key Features

- GTK/WebKit desktop interface (GTK4 first, GTK3 fallback)
- Provider switching (`claude` and `codex`)
- Session persistence and recent-folder tracking
- Multi-pane workflow with agent-oriented controls
- File attachments from picker, drag-and-drop, and clipboard images
- Settings editor for models, reasoning levels, permissions, and provider themes
- Defensive persistence and runtime hardening (atomic writes, payload validation, pane lifecycle guards)

## Requirements

- Python `>= 3.11`
- PyGObject (`gi`) with one supported runtime stack:
- GTK4 + WebKit6, or
- GTK3 + WebKit2
- At least one provider CLI installed:
- `claude` or `claude-code`
- `codex` (optional)

### Linux Packages (Example: Ubuntu/Debian)

GTK4 path:

```bash
sudo apt-get update
sudo apt-get install -y python3-gi gir1.2-gtk-4.0 gir1.2-webkit-6.0
```

GTK3 fallback path:

```bash
sudo apt-get update
sudo apt-get install -y python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1
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

## Provider Setup

The app auto-detects providers from your PATH and known fallback locations.

- Claude binaries searched: `claude`, `claude-code`
- Codex binary searched: `codex`

For Codex, authentication is checked before use. Make sure `codex` is logged in.

## Usage

1. Start the app with `python -m claude_code_gui`.
2. Select a project folder (folder button near the composer).
3. Attach files with `+` if needed.
4. Send prompts in chat.
5. Toggle agent mode from the composer toggle.
6. Switch provider from the sidebar/provider control.

## Data and Config Paths

The app stores local state under:

- `~/.config/claude-code-gui/sessions.json`
- `~/.config/claude-code-gui/recent_folders.json`
- `~/.config/claude-code-gui/app_settings.json`

Bundled defaults live in:

- `claude_code_gui/config/default_app_settings.json`
- `claude_code_gui/config/provider_theme_settings.json`

## Development

Install dev/test extras:

```bash
pip install -e .[test]
```

Run tests:

```bash
pytest -m "unit or integration or gtk_css" --cov=claude_code_gui --cov-report=term-missing --cov-fail-under=80
```

Optional contract tests:

```bash
RUN_CONTRACT_TESTS=1 pytest -m "contract" -q
```

## Architecture (High Level)

- `claude_code_gui/ui/window.py`
The main window/controller, pane management, WebView bridge handlers.
- `claude_code_gui/runtime/claude_process.py`
CLI subprocess lifecycle and stream/event handling.
- `claude_code_gui/domain/cli_dialect.py`
Provider-specific argv building and event parsing (Claude/Codex dialects).
- `claude_code_gui/assets/chat_template.py`
Embedded HTML/CSS/JS for the WebView chat frontend.
- `claude_code_gui/storage/*.py`
Session, settings, and recent-folder persistence.

## Troubleshooting

- "CLI not found"
Ensure `claude`, `claude-code`, or `codex` is installed and in `PATH`.
- Codex appears unavailable
Check authentication state in your terminal and re-open the app.
- Blank or broken UI at startup
Verify GTK/WebKit GI packages are installed for your system stack.

## Contributing

Contributions are welcome. Open an issue for bugs or feature requests, then send a PR.

## License

No project license file is currently included.
