# Claude Code GUI

This repository contains a GTK/WebKit based desktop interface for Claude Code.

## Changes made

### Chat composer controls

- Added a compact **artifacts toggle button** next to the file attach (`+`) button in the composer control row.
- Updated the plus button visual to a stable SVG icon.
- Replaced the folder path button emoji with an SVG folder icon for the project path button.
- Kept both welcome and chat composer rows in sync so behavior matches in both views.

### Behavior

- Both new toggle buttons share the same logic and stay in sync with the current artifact panel state.
- The toggle updates `aria-pressed` for accessibility and keeps the top toolbar button behavior unchanged.
- Folder and plus buttons continue to open existing host actions (`changeFolder`, `attachFile`).

### Refactor performed

- Small refactor in `claude_code_gui/assets/chat_template.py` to centralize artifact panel toggle behavior in one helper (`toggleArtifactsPanel`).

## Notes

- No functional regressions were flagged in the review.
