# Claude Code GUI

This repository contains a GTK/WebKit based desktop interface for Claude Code.

## Changes made

### Chat composer controls

- The left control cluster in the composer now has:
  - `+` **Attach files** button that opens a file chooser and adds selected files.
  - An adjacent **agent-mode toggle** button (no longer wired to the artifacts panel).
- Added a project-folder button action in both composer views that opens a native folder chooser.
- Replaced the folder path button emoji with an SVG folder icon for the project path button.
- Removed the sidebar `+ New Agent` button; agent mode is now controlled only via the composer toggle.

### Behavior

- Both toggle buttons in welcome/chat composers target the same host handler and stay synchronized.
- The webview now syncs agent-mode state on load and after any toggle change.
- Folder and plus buttons are both wired to host handlers (`changeFolder`, `attachFile`).

### Refactor performed

- Small refactor in `claude_code_gui/ui/window.py` to centralize agent mode persistence/sync in `_persist_agent_mode_preference`.

## Notes

- No functional regressions were flagged after local review of the requested changes.
