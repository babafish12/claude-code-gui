"""WebView HTML/CSS/JS payload for the chat UI."""

from __future__ import annotations
from pathlib import Path

from claude_code_gui.assets.glass_tokens_web import glass_tokens_style_block

VENDOR_DIR = Path(__file__).parent / "vendor"
HIGHLIGHT_JS = (VENDOR_DIR / "highlight.min.js").read_text(encoding="utf-8").replace("</script>", "<\\/script>")
HIGHLIGHT_CSS = (VENDOR_DIR / "highlight-dracula.min.css").read_text(encoding="utf-8").replace("</style>", "<\\/style>")
MOTION_ONE_JS = (VENDOR_DIR / "motion.min.js").read_text(encoding="utf-8").replace("</script>", "<\\/script>")
GLASS_STYLE_SNIPPET = glass_tokens_style_block("dark")

CHAT_WEBVIEW_HTML = (
r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
__INLINE_HIGHLIGHT_CSS__
</style>
<script>
__INLINE_HIGHLIGHT_JS__
</script>
<script>
__INLINE_MOTION_ONE_JS__
</script>
__GLASS_STYLE_SNIPPET__
<style>
:root {
    --bg: #2f2f2a;
    --bg-elevated: rgba(58, 58, 52, 0.94);
    --sidebar: #292923;
    --input-bg: #3a3a34;
    --input-border: #4a4a43;
    --input-focus: #5a5a50;
    --user-bubble: #3a3a35;
    --text: #d4d4c8;
    --fg: #d4d4c8;
    --muted: #8a8a7a;
    --accent: #d97757;
    --motion-fast: 120ms;
    --motion-normal: 220ms;
    --motion-slow: 400ms;
    --motion-loop: 1200ms;
    --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
    --ease-enter: cubic-bezier(0, 0, 0.2, 1);
    --ease-exit: cubic-bezier(0.4, 0, 1, 1);
    --accent-soft: rgba(var(--accent-rgb), 0.18);
    --accent-rgb: 217, 119, 87;
    --accent-rgba-012: rgba(var(--accent-rgb), 0.12);
    --accent-rgba-072: rgba(var(--accent-rgb), 0.72);
    --accent-rgba-055: rgba(var(--accent-rgb), 0.55);
    --chip-border: #4a4a43;
    --code-bg: #1a1a16;
    --surface-panel: #3a3a34;
    --surface-card: rgba(58, 58, 52, 0.92);
    --surface-card-soft: rgba(58, 58, 52, 0.9);
    --surface-muted: rgba(58, 58, 52, 0.7);
    --surface-muted-strong: rgba(58, 58, 52, 0.8);
    --surface-chip: rgba(58, 58, 52, 0.66);
    --surface-overlay: rgba(255, 255, 255, 0.06);
    --surface-overlay-soft: rgba(255, 255, 255, 0.04);
    --surface-overlay-border: rgba(255, 255, 255, 0.12);
    --text-soft: #b7b29a;
    --text-accent-soft: #f0c1a6;
    --permission-border: rgba(217, 131, 64, 0.75);
    --permission-gradient-start: rgba(72, 56, 36, 0.66);
    --permission-gradient-end: rgba(47, 47, 42, 0.96);
    --permission-shadow-soft: rgba(217, 131, 64, 0.16);
    --permission-shadow-strong: rgba(217, 131, 64, 0.34);
    --permission-glow: rgba(217, 131, 64, 0.2);
    --inline-code-bg: #3a3a34;
    --inline-code-color: #e06c75;
    --table-border: #4a4a43;
    --border: #4a4a43;
    --code-block-bg: #1e1e1e;
    --code-head-muted: #8a8a8a;
    --artifacts-panel-bg: #2a2a25;
    --artifacts-panel-width: 360px;
    --shadow: 0 12px 36px rgba(0, 0, 0, 0.34);
    --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", "Twemoji Mozilla", sans-serif;
    --emoji-font-stack: "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", "Twemoji Mozilla", sans-serif;
}

* {
    box-sizing: border-box;
}

html,
body {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    background:
        radial-gradient(circle at 14% 4%, rgba(var(--accent-rgb), 0.12), transparent 30%),
        radial-gradient(circle at 85% 96%, rgba(var(--accent-rgb), 0.08), transparent 26%),
        var(--bg);
    color: var(--text);
    font-family: var(--font-stack);
    font-variant-emoji: text;
    font-kerning: normal;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    overflow: hidden;
}

a {
    color: var(--accent);
    text-decoration: none;
    transition: color var(--motion-fast) var(--ease-standard), text-decoration-color var(--motion-fast) var(--ease-standard);
}

a:hover {
    text-decoration: underline;
}

button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
    box-shadow:
        0 0 0 2px color-mix(in srgb, var(--accent) 55%, transparent);
}

button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    filter: saturate(0.75);
}

#app {
    position: relative;
    width: 100%;
    height: 100%;
}

#app.pane-mode-agent #welcomeView {
    display: none !important;
}

#app.pane-mode-agent #chatView {
    display: block;
}

#app.pane-mode-agent #chatToolbar,
#app.pane-mode-agent #artifactsPanel {
    display: none !important;
}

#app.pane-mode-agent #messages {
    padding-right: 10px !important;
}

#app.pane-mode-agent #chatComposer {
    right: 0 !important;
}

#welcomeView,
#chatView {
    width: 100%;
    height: 100%;
}

#welcomeView {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
}

.welcome-shell {
    width: 100%;
    max-width: 820px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 18px;
}

.welcome-icon {
    width: 42px;
    height: 42px;
    object-fit: contain;
    display: block;
    border-radius: 9px;
    margin: 2px 0;
    background: transparent;
}

.welcome-title {
    margin: 0;
    color: var(--text);
    font-size: 28px;
    font-weight: 500;
    letter-spacing: 0.1px;
}

.welcome-provider-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    border: 1px solid var(--chip-border);
    background: var(--accent-rgba-012);
    color: var(--accent);
    font-size: 12px;
    font-weight: 700;
    padding: 5px 10px;
}

.welcome-provider-icon {
    width: 14px;
    height: 14px;
    object-fit: contain;
    vertical-align: middle;
    display: none;
}

.welcome-provider-icon.visible {
    display: inline-block;
}

.welcome-onboarding {
    width: 100%;
    max-width: 740px;
    border-radius: 14px;
    border: 1px solid var(--chip-border);
    background: var(--surface-card-soft);
    padding: 14px;
}

.welcome-onboarding-title {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
}

.composer-card {
    width: 100%;
    max-width: 740px;
    border-radius: 24px;
    border: 1px solid var(--input-border);
    background: var(--surface-card);
    box-shadow: var(--shadow);
    padding: 14px;
}

.composer-input {
    width: 100%;
    resize: none;
    min-height: 54px;
    max-height: 220px;
    border: 1px solid transparent;
    border-radius: 24px;
    outline: none;
    background: transparent;
    color: var(--text);
    padding: 12px 14px;
    font: inherit;
    font-size: 16px;
    line-height: 1.42;
    transition: border-color var(--motion-fast) var(--ease-standard), box-shadow var(--motion-fast) var(--ease-standard);
}

.composer-input::placeholder {
    color: var(--muted);
}

.composer-input:focus {
    outline: none !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

.composer-input:focus-visible {
    outline: none !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

.control-row {
    margin-top: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.control-left {
    display: flex;
    align-items: center;
    gap: 8px;
}

.control-right {
    display: flex;
    align-items: center;
    gap: 8px;
}

.folder-path-btn {
    margin-top: 8px;
    width: 100%;
    border: none;
    background: transparent;
    color: var(--muted);
    border-radius: 10px;
    padding: 4px 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.folder-path-btn:hover {
    background: var(--surface-overlay);
    color: var(--text-soft);
}

.folder-path-icon {
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 12px;
    height: 12px;
}

.folder-path-icon svg {
    width: 12px;
    height: 12px;
    fill: currentColor;
    stroke: currentColor;
    stroke-width: 1.5;
}

.folder-path-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.attachment-strip {
    display: none;
    margin-bottom: 8px;
    flex-wrap: wrap;
    gap: 8px;
    align-items: stretch;
}

.attachment-strip.has-items {
    display: flex;
}

.attachment-chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    border-radius: 12px;
    border: 1px solid var(--chip-border);
    background: var(--surface-card-soft);
    padding: 6px 8px 6px 6px;
    font-size: 12px;
    max-width: min(320px, 100%);
    min-height: 56px;
    transition: border-color var(--motion-fast) var(--ease-standard);
    position: relative;
}

.attachment-chip:hover {
    border-color: var(--accent-rgba-072);
}

.attachment-preview {
    flex: none;
    position: relative;
    width: 44px;
    height: 44px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--chip-border);
    background: var(--surface-overlay);
    display: flex;
    align-items: center;
    justify-content: center;
}

.attachment-thumb {
    width: 44px;
    height: 44px;
    object-fit: cover;
    display: block;
}

.attachment-file-marker {
    font-size: 17px;
    line-height: 1;
}

.attachment-meta {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
}

.attachment-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
    max-width: 180px;
}

.attachment-path {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--muted);
    font-size: 11px;
    max-width: 180px;
}

.attachment-remove {
    border: none;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    padding: 0;
    width: 14px;
    height: 14px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.2);
    transition: color var(--motion-fast) var(--ease-standard);
}

.attachment-remove:hover {
    color: var(--text-accent-soft);
}

.attachment-remove.attachment-remove-image {
    position: absolute;
    top: 4px;
    left: 4px;
}

.attachment-chip-image .attachment-remove {
    position: absolute;
    top: 4px;
    left: 4px;
}

.plus-btn,
.agent-mode-toggle-btn,
.selector-btn,
.permission-btn,
.action-btn,
.assistant-action,
.chip {
    border: 1px solid var(--chip-border);
    background: transparent;
    color: var(--text);
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard),
        color var(--motion-fast) var(--ease-standard);
}

.plus-btn {
    width: 30px;
    height: 30px;
    border-radius: 999px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}

.agent-mode-toggle-btn {
    width: 30px;
    height: 30px;
    border-radius: 999px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}

.agent-mode-toggle-btn:hover {
    background-color: var(--accent-rgba-012);
    border-color: var(--accent-rgba-072);
}

.agent-mode-toggle-btn.active {
    background-color: var(--accent-rgba-012);
    border-color: var(--accent-rgba-072);
}

.plus-btn-icon,
.agent-mode-toggle-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
}

.plus-btn-icon svg,
.agent-mode-toggle-icon svg {
    width: 14px;
    height: 14px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.75;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.toggle-track {
    fill: transparent;
    stroke: currentColor;
    stroke-width: 1.5;
}

.toggle-knob {
    fill: currentColor;
    stroke: none;
    transition: transform var(--motion-fast) var(--glass-spring-standard);
}

.agent-mode-toggle-btn.active .toggle-knob {
    transform: translateX(6px);
}

.plus-btn:hover,
.agent-mode-toggle-btn:hover,
.selector-btn:hover,
.permission-btn:hover,
.chip:hover,
.assistant-action:hover,
.action-btn:hover {
    background-color: var(--accent-rgba-012);
    border-color: var(--accent-rgba-072);
}

.selector-group {
    position: relative;
}

.selector-btn {
    min-height: 30px;
    border-radius: 999px;
    padding: 0 12px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
}

.selector-caret {
    color: var(--muted);
    font-size: 11px;
}

.permission-btn {
    width: 30px;
    height: 30px;
    border-radius: 999px;
    padding: 0;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.permission-btn svg {
    width: 16px;
    height: 16px;
    color: var(--text);
}

.popup-menu {
    position: absolute;
    right: 0;
    bottom: calc(100% + 10px);
    width: auto;
    min-width: 140px;
    max-width: 320px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: var(--glass-tint-interactive);
    backdrop-filter: blur(12px) saturate(150%) brightness(1.02);
    -webkit-backdrop-filter: blur(12px) saturate(150%) brightness(1.02);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.18);
    padding: 3px;
    opacity: 0;
    transform: translateY(6px);
    pointer-events: none;
    transition: opacity var(--motion-fast) var(--ease-standard), transform var(--motion-fast) var(--ease-standard);
    z-index: 40;
}

.popup-menu.open {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
}

.popup-menu.closing {
    opacity: 0;
    transform: translateY(6px);
    pointer-events: none;
    transition: opacity var(--motion-fast) var(--ease-exit), transform var(--motion-fast) var(--ease-exit);
}

.popup-option {
    width: 100%;
    border: 1px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: var(--text);
    text-align: left;
    padding: 7px 10px;
    white-space: nowrap;
    cursor: pointer;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard),
        color var(--motion-fast) var(--ease-standard);
}

.popup-option + .popup-option {
    margin-top: 4px;
}

.popup-option:hover {
    background: rgba(var(--accent-rgb), 0.075);
    border-color: rgba(var(--accent-rgb), 0.18);
}

.popup-option.active {
    background: rgba(var(--accent-rgb), 0.11);
    border-color: rgba(var(--accent-rgb), 0.28);
}

.folder-path-btn,
.plus-btn,
.agent-mode-toggle-btn,
.selector-btn,
.permission-btn,
.permission-selector,
.assistant-action,
.action-btn,
.code-copy-btn,
.chip,
.quick-chip,
.artifact-action-btn,
.stop-process-btn,
.example-prompt {
    position: relative;
    overflow: hidden;
    border-radius: var(--glass-radius-control);
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: none;
    transition-property: transform, box-shadow, background-color, border-color;
    transition-duration: var(--motion-fast);
    transition-timing-function: var(--glass-spring-standard);
    will-change: transform;
}

.folder-path-btn:hover,
.plus-btn:hover,
.agent-mode-toggle-btn:hover,
.selector-btn:hover,
.permission-btn:hover,
.permission-selector:hover,
.assistant-action:hover,
.action-btn:hover,
.code-copy-btn:hover,
.chip:hover,
.quick-chip:hover,
.artifact-action-btn:hover,
.stop-process-btn:hover,
.example-prompt:hover {
    background: var(--glass-tint-interactive-hover);
    border-color: var(--glass-border-highlight);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(12px) saturate(150%) brightness(1.02);
    -webkit-backdrop-filter: blur(12px) saturate(150%) brightness(1.02);
    transform: scale(1.02);
    transition-timing-function: var(--glass-spring-hover);
    transition-duration: var(--motion-hover);
}

.folder-path-btn::before,
.plus-btn::before,
.agent-mode-toggle-btn::before,
.selector-btn::before,
.permission-btn::before,
.permission-selector::before,
.assistant-action::before,
.action-btn::before,
.code-copy-btn::before,
.chip::before,
.quick-chip::before,
.artifact-action-btn::before,
.stop-process-btn::before,
.example-prompt::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: var(--glass-specular-gradient);
    pointer-events: none;
    transition: opacity var(--motion-hover) var(--glass-spring-hover);
    opacity: 0;
}

.folder-path-btn:hover::before,
.plus-btn:hover::before,
.agent-mode-toggle-btn:hover::before,
.selector-btn:hover::before,
.permission-btn:hover::before,
.permission-selector:hover::before,
.assistant-action:hover::before,
.action-btn:hover::before,
.code-copy-btn:hover::before,
.chip:hover::before,
.quick-chip:hover::before,
.artifact-action-btn:hover::before,
.stop-process-btn:hover::before,
.example-prompt:hover::before {
    opacity: 0.72;
}

.folder-path-btn:active,
.plus-btn:active,
.agent-mode-toggle-btn:active,
.selector-btn:active,
.permission-btn:active,
.permission-selector:active,
.assistant-action:active,
.action-btn:active,
.code-copy-btn:active,
.chip:active,
.quick-chip:active,
.artifact-action-btn:active,
.stop-process-btn:active,
.example-prompt:active {
    transform: scale(0.98);
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.35);
    transition-timing-function: var(--glass-spring-press);
    transition-duration: var(--motion-press);
}

.folder-path-btn,
.plus-btn,
.agent-mode-toggle-btn,
.selector-btn,
.permission-btn,
.permission-selector,
.assistant-action,
.action-btn,
.code-copy-btn,
.chip,
.quick-chip,
.artifact-action-btn,
.stop-process-btn,
.example-prompt {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
}

.popup-option {
    position: relative;
    overflow: hidden;
}

.popup-option:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

.popup-title {
    display: block;
    font-size: 13px;
    font-weight: 600;
}

.popup-subtitle {
    display: block;
    margin-top: 2px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.35;
}

.slash-dropdown {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 100%;
    margin-bottom: 6px;
    max-height: 320px;
    overflow-y: auto;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: var(--surface-panel);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.18);
    padding: 3px;
    opacity: 0;
    transform: translateY(6px);
    pointer-events: none;
    transition: opacity var(--motion-fast) var(--ease-standard), transform var(--motion-fast) var(--ease-standard);
    z-index: 50;
}

.slash-dropdown.open {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
}

.slash-dropdown-header {
    padding: 5px 10px 4px;
    font-size: 10px;
    font-weight: 500;
    color: var(--muted);
    text-transform: none;
    letter-spacing: 0.1px;
}

.slash-dropdown-item {
    width: 100%;
    border: 1px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: var(--text);
    text-align: left;
    padding: 6px 10px;
    cursor: pointer;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard),
        color var(--motion-fast) var(--ease-standard);
    display: flex;
    align-items: center;
    gap: 8px;
}

.slash-dropdown-item + .slash-dropdown-item {
    margin-top: 2px;
}

.slash-dropdown-item:hover,
.slash-dropdown-item.selected {
    background: rgba(var(--accent-rgb), 0.075);
    border-color: rgba(var(--accent-rgb), 0.18);
}

.slash-dropdown-item.selected {
    background: rgba(var(--accent-rgb), 0.11);
    border-color: rgba(var(--accent-rgb), 0.28);
}

.slash-dropdown-icon {
    flex: none;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.02);
    color: var(--muted);
    font-size: 13px;
}

.slash-dropdown-info {
    flex: 1;
    min-width: 0;
}

.slash-dropdown-name {
    display: block;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.slash-dropdown-desc {
    display: block;
    margin-top: 1px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.slash-dropdown-empty {
    padding: 12px 10px;
    color: var(--muted);
    font-size: 13px;
    text-align: center;
}

.slash-dropdown::-webkit-scrollbar {
    width: 6px;
}

.slash-dropdown::-webkit-scrollbar-track {
    background: transparent;
}

.slash-dropdown::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
}

.quick-chips {
    width: 100%;
    max-width: 740px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
}

.chip {
    border-radius: 999px;
    padding: 7px 12px;
    font-size: 13px;
    cursor: pointer;
}

.onboarding-steps {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 16px;
}

.onboarding-step {
    display: flex;
    gap: 8px;
    font-size: 13px;
    color: var(--muted);
}

.onboarding-step-number {
    color: var(--accent);
    font-weight: 600;
}

.example-prompts-title {
    margin-top: 14px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-soft);
}

.example-prompts {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-top: 12px;
}

.example-prompt {
    padding: 8px 12px;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    font-size: 12px;
    color: var(--text-soft);
    transition: all var(--motion-fast);
}

.example-prompt:hover {
    border-color: var(--accent);
}

.keyboard-hints {
    display: flex;
    gap: 16px;
    justify-content: center;
    font-size: 11px;
    color: var(--muted);
    margin-top: 24px;
    opacity: 0.7;
    flex-wrap: wrap;
}

.keyboard-hint kbd {
    background: var(--border);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 10px;
}

#chatView {
    display: none;
    position: relative;
    overflow: hidden;
}

#chatView.active {
    display: block;
}

#chatView.artifacts-open #artifactsPanel {
    transform: translateX(0);
    pointer-events: auto;
}

#chatToolbar {
    position: absolute;
    top: 12px;
    right: 14px;
    z-index: 45;
    display: flex;
    align-items: center;
    gap: 8px;
}

.chat-search-bar {
    position: absolute;
    top: 16px;
    right: 16px;
    z-index: 100;
    display: flex;
    gap: 8px;
    align-items: center;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.chat-search-bar input {
    background: transparent;
    border: none;
    outline: none;
    color: var(--fg);
    font-size: 13px;
    min-width: 200px;
}

#chatSearchInput:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
    border-radius: 4px;
}

.chat-search-bar button {
    background: transparent;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: all var(--motion-fast);
}

.chat-search-bar button:hover {
    background: var(--border);
    color: var(--fg);
}

.chat-search-count {
    font-size: 11px;
    color: var(--muted);
}

.chat-search-limit-note {
    font-size: 11px;
    color: var(--muted);
}

.chat-search-bar.no-results {
    border-color: rgba(138, 138, 122, 0.7);
}

.chat-search-bar.no-results input {
    border-bottom: 1px solid rgba(138, 138, 122, 0.7);
}

.search-highlight {
    background: rgba(255, 235, 59, 0.4);
    border-radius: 2px;
}

.search-highlight.current-match {
    background: rgba(255, 193, 7, 0.8);
    color: #000;
}

#artifactsToggleBtn {
    border: 1px solid var(--chip-border);
    background: var(--surface-card-soft);
    color: var(--text);
    border-radius: 999px;
    min-height: 30px;
    padding: 0 12px;
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard),
        color var(--motion-fast) var(--ease-standard);
}

#artifactsToggleBtn:hover,
#artifactsToggleBtn.active {
    border-color: var(--accent-rgba-072);
    background: rgba(var(--accent-rgb), 0.14);
}

#dropOverlay {
    position: absolute;
    inset: 18px 14px 118px;
    border-radius: 18px;
    border: 2px dashed rgba(var(--accent-rgb), 0.75);
    background: rgba(var(--accent-rgb), 0.16);
    color: var(--text-accent-soft);
    display: none;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 600;
    z-index: 55;
    pointer-events: none;
    transition: opacity var(--motion-fast) var(--ease-standard), transform var(--motion-fast) var(--ease-standard);
}

#dropOverlay.active {
    display: flex;
}

#messages {
    position: absolute;
    inset: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 52px 14px 220px;
    scroll-behavior: smooth;
    transition: padding-right var(--motion-normal) var(--ease-standard);
}

#scroll-to-bottom-btn {
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--surface-card-soft);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid var(--surface-overlay-border);
    color: var(--text-soft);
    font-size: 16px;
    cursor: pointer;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--motion-normal) var(--ease-standard), transform var(--motion-normal) var(--ease-standard);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
}

#scroll-to-bottom-btn.visible {
    opacity: 1;
    pointer-events: auto;
}

#scroll-to-bottom-btn:hover {
    background: rgba(60, 60, 55, 0.95);
    color: #e0e0e0;
}

#messages::-webkit-scrollbar {
    width: 8px;
}

#messages::-webkit-scrollbar-track {
    background: transparent;
}

#messages::-webkit-scrollbar-thumb {
    background: #4b4b43;
    border-radius: 999px;
}

.message-row {
    width: 100%;
    display: flex;
    justify-content: center;
    margin-bottom: 16px;
    animation: messageEnter var(--motion-normal) var(--ease-enter) both;
}

@keyframes messageEnter {
    from {
        opacity: 0;
        transform: translateY(12px) scale(0.98);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

.message-row.user {
    animation: slideInRight var(--motion-normal) var(--ease-enter) both;
}

@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(16px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.message-row.assistant {
    animation: slideInLeft var(--motion-normal) var(--ease-enter) both;
}

@keyframes slideInLeft {
    from {
        opacity: 0;
        transform: translateX(-12px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.message-inner {
    width: 100%;
    max-width: 768px;
}

.message-row.user .message-inner {
    display: flex;
    justify-content: flex-end;
}

.user-bubble-wrap {
    max-width: min(90%, 640px);
    display: inline-flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
    position: relative;
}

.user-bubble {
    display: inline-block;
    width: -webkit-fit-content;
    width: fit-content;
    max-width: 100%;
    border-radius: 18px;
    background: var(--user-bubble);
    padding: 12px 18px;
    color: var(--text);
    white-space: pre-wrap;
    line-height: 1.45;
    word-break: break-word;
}

.user-bubble-text {
    display: inline;
    white-space: pre-wrap;
}

.message-attachments {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
}

.message-attachment-image,
.chat-image {
    max-width: 100%;
    max-height: 420px;
    width: auto;
    height: auto;
    border-radius: 10px;
    border: 1px solid var(--table-border);
    object-fit: contain;
    background: var(--surface-muted);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.26);
    cursor: pointer;
    transition: transform var(--motion-fast) var(--ease-standard), filter var(--motion-fast) var(--ease-standard);
}

.message-attachment-image {
    max-width: min(100%, 320px);
}

.chat-image {
    border-radius: 8px;
    margin: 8px 0;
    display: block;
}

.message-attachment-image:hover,
.chat-image:hover {
    transform: scale(1.015);
    filter: brightness(1.06);
}

.message-attachment-file {
    border-radius: 10px;
    border: 1px solid var(--table-border);
    background: var(--surface-muted-strong);
    padding: 6px 9px;
    font-size: 12px;
}

.assistant-block {
    display: block;
}

.assistant-content-wrap {
    min-width: 0;
    position: relative;
}

.assistant-message {
    color: var(--text);
    line-height: 1.65;
    word-break: break-word;
    font-size: 15px;
}

.streaming-cursor {
    display: inline-block;
    width: 2px;
    height: 1.1em;
    background: var(--accent);
    animation: cursorBlink calc(var(--motion-loop) / 2) step-end infinite;
    vertical-align: text-bottom;
    margin-left: 2px;
    border-radius: 1px;
    opacity: 0;
    transition: opacity var(--motion-fast) var(--ease-enter);
}

.streaming-cursor.is-visible {
    opacity: 1;
}

@keyframes cursorBlink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}

.user-bubble,
.assistant-message,
.system-pill,
.composer-input {
    font-family: var(--font-stack);
    font-variant-emoji: text;
}

.user-bubble-text,
.assistant-message,
.system-pill {
    font-family: var(--font-stack), var(--emoji-font-stack);
}

.assistant-message,
.assistant-message p,
.assistant-message li,
.assistant-message blockquote,
.assistant-message td,
.assistant-message th,
.user-bubble,
.system-pill {
    font-variant-numeric: lining-nums proportional-nums;
    letter-spacing: normal;
    word-spacing: normal;
    font-feature-settings: "kern" 1, "liga" 1, "tnum" 0;
}

.assistant-actions {
    margin-top: 8px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    opacity: 0;
    transform: translateY(4px);
    transition: opacity var(--motion-fast) var(--ease-standard), transform var(--motion-fast) var(--ease-standard);
    pointer-events: none;
}

.user-actions {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    opacity: 0;
    transform: translateY(4px);
    transition: opacity var(--motion-fast) var(--ease-standard), transform var(--motion-fast) var(--ease-standard);
    pointer-events: none;
}

.message-row.assistant:hover .assistant-actions {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
}

.message-row.user:hover .user-actions {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
}

.assistant-action {
    width: 26px;
    height: 26px;
    border-radius: 999px;
    cursor: pointer;
    font-size: 13px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.assistant-action.copy-md-action,
.user-action.copy-md-action {
    width: auto;
    min-width: 56px;
    padding: 0 8px;
    font-size: 11px;
}

.assistant-action.active {
    border-color: rgba(var(--accent-rgb), 0.9);
    color: var(--text-accent-soft);
}

.copy-success-badge {
    position: absolute;
    top: -8px;
    right: 8px;
    background: var(--accent);
    color: #ffffff;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1px;
    opacity: 0;
    transition: opacity var(--motion-fast);
    pointer-events: none;
}

.copy-success-badge.visible {
    opacity: 1;
}

.message-row.system .message-inner {
    display: flex;
    justify-content: center;
}

.message-row.system {
    animation: fadeIn var(--motion-slow) var(--ease-enter) both;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.system-pill {
    border-radius: 999px;
    border: 1px solid var(--chip-border);
    background: var(--surface-muted);
    color: var(--muted);
    font-size: 12px;
    padding: 6px 12px;
}

.message-row.error .message-inner {
    display: flex;
    justify-content: center;
}

.error-card {
    width: min(100%, 768px);
    border-radius: 12px;
    border: 1px solid rgba(220, 80, 60, 0.45);
    border-left: 3px solid rgba(220, 80, 60, 0.9);
    background: linear-gradient(180deg, rgba(78, 42, 38, 0.78), rgba(47, 36, 34, 0.92));
    padding: 12px;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: start;
    gap: 10px;
}

.error-card-icon {
    width: 24px;
    height: 24px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #ffb0a5;
    background: rgba(220, 80, 60, 0.2);
    font-size: 13px;
}

.error-card-title {
    font-size: 13px;
    font-weight: 700;
    color: #ffd7cf;
    margin-bottom: 4px;
}

.error-card-text {
    font-size: 12px;
    color: #f2c0b7;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
}

.error-card-action {
    border: 1px solid rgba(220, 80, 60, 0.65);
    border-radius: 999px;
    background: rgba(220, 80, 60, 0.12);
    color: #ffd9d3;
    padding: 5px 11px;
    font-size: 11px;
    cursor: pointer;
    transition: background-color var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}

.error-card-action:hover {
    border-color: rgba(220, 80, 60, 0.85);
    background: rgba(220, 80, 60, 0.22);
}

.message-row.tool .message-inner {
    display: flex;
    justify-content: flex-start;
}

.message-row.tool {
    animation: slideInLeft var(--motion-normal) var(--ease-enter) both;
}

.message-row.tool-summary .message-inner {
    display: flex;
    justify-content: flex-start;
}

.tool-card {
    width: 100%;
    max-width: 768px;
    border-radius: 10px;
    border: 1px solid transparent;
    transition: border-color var(--motion-normal) var(--ease-standard), box-shadow var(--motion-normal) var(--ease-standard);
}

.tool-card:hover {
    border-color: var(--surface-overlay-border);
}

.tool-card.tool-card-highlight {
    box-shadow: 0 0 0 1px var(--accent-rgba-072), 0 0 18px rgba(var(--accent-rgb), 0.2);
}

.tool-header {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--muted);
    font-size: 12px;
    cursor: pointer;
    padding: 3px 0;
    transition: color var(--motion-fast) var(--ease-standard);
}

.tool-header:hover {
    color: var(--text);
}

.tool-name {
    font-weight: 600;
    opacity: 0.8;
}

.tool-path {
    opacity: 0.6;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 11px;
}

.tool-caret {
    font-size: 9px;
    opacity: 0.5;
    transition: transform var(--motion-normal) var(--ease-standard);
}

.tool-caret.open {
    transform: rotate(90deg);
}

.tool-detail {
    display: none;
    margin-top: 4px;
    border-radius: 8px;
    border: 1px solid var(--chip-border);
    background: var(--code-bg);
    overflow: hidden;
    font-size: 12px;
    max-height: 520px;
    overflow-y: auto;
}

.tool-detail.open {
    display: block;
    animation: toolReveal var(--motion-normal) var(--ease-enter);
}

@keyframes toolReveal {
    from { opacity: 0; max-height: 0; }
    to { opacity: 1; max-height: 520px; }
}

.tool-detail-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 10px;
    border-bottom: 1px solid #45453e;
    background: #252520;
}

.tool-detail-actions {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.tool-copy-diff-btn {
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 11px;
    cursor: pointer;
}

.diff-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border-bottom: 1px solid #40403a;
    background: #2a2a25;
}

.diff-header-icon {
    font-size: 12px;
    opacity: 0.9;
}

.diff-header-path {
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 11px;
    color: #e8e5d8;
    opacity: 0.92;
    word-break: break-all;
}

.diff-container {
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    background: #1d1d18;
    border: 1px solid #393932;
    border-radius: 0 0 8px 8px;
    overflow: hidden;
}

.diff-body {
    max-height: 420px;
    overflow: auto;
}

.diff-row {
    display: grid;
    grid-template-columns: 52px 52px 16px 1fr;
    align-items: start;
    min-height: 18px;
    line-height: 1.45;
    font-size: 11px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.diff-line-number {
    display: inline-flex;
    align-items: center;
    justify-content: flex-end;
    padding: 0 8px 0 4px;
    color: #7f7f72;
    text-align: right;
    user-select: none;
}

.diff-line-sign {
    text-align: center;
    color: #a4a392;
}

.diff-line-code {
    padding: 0 10px 0 2px;
    white-space: pre;
    overflow-wrap: anywhere;
    color: #dfdccf;
}

.diff-line-add {
    background: #2d4a2d;
}

.diff-line-add .diff-line-sign,
.diff-line-add .diff-line-code {
    color: #b8e5b8;
}

.diff-line-remove {
    background: #4a2d2d;
}

.diff-line-remove .diff-line-sign,
.diff-line-remove .diff-line-code {
    color: #f1b7b7;
}

.diff-line-context {
    background: #1d1d18;
}

.diff-truncated-note {
    padding: 7px 10px;
    border-top: 1px solid #45453e;
    color: #b8b4a4;
    font-size: 11px;
}

.diff-stat {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-weight: 700;
    letter-spacing: 0.1px;
}

.diff-stat-add {
    color: #89d589;
}

.diff-stat-remove {
    color: #f0a2a2;
}

.tool-summary-card {
    width: 100%;
    max-width: 768px;
    border-radius: 10px;
    border: 1px solid var(--chip-border);
    background: linear-gradient(180deg, var(--surface-card-soft), var(--code-bg));
    padding: 10px;
}

.tool-summary-title {
    font-size: 12px;
    color: var(--text);
    margin-bottom: 8px;
    font-weight: 600;
}

.tool-summary-files {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.diff-summary-file {
    width: 100%;
    border: 1px solid var(--table-border);
    border-radius: 8px;
    background: var(--surface-muted);
    color: var(--text);
    padding: 6px 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    font-size: 11px;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard);
}

.diff-summary-file:hover {
    border-color: var(--accent-rgba-072);
    background: rgba(var(--accent-rgb), 0.11);
}

.diff-summary-filepath {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
}

.diff-summary-total {
    margin-top: 9px;
    padding-top: 8px;
    border-top: 1px solid var(--table-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-soft);
}

.file-status-new {
    border-left: 3px solid #6dbd6d;
    background: rgba(61, 105, 61, 0.4);
}

.file-status-modified {
    border-left: 3px solid #d6b35b;
    background: rgba(120, 98, 48, 0.34);
}

.file-status-deleted {
    border-left: 3px solid #d07d7d;
    background: rgba(122, 58, 58, 0.36);
}

.tool-diff-old {
    background: rgba(220, 80, 60, 0.1);
    color: #e07a6a;
    padding: 6px 10px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-all;
    border-bottom: 1px solid rgba(220, 80, 60, 0.15);
}

.tool-diff-new {
    background: rgba(80, 180, 80, 0.1);
    color: #8bbf8a;
    padding: 6px 10px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-all;
}

.tool-code {
    padding: 6px 10px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-all;
    color: var(--text);
    opacity: 0.85;
}

.message-row.git .message-inner,
.message-row.pr .message-inner,
.message-row.ci .message-inner {
    display: flex;
    justify-content: flex-start;
}

.git-card,
.pr-card,
.ci-status-card {
    width: 100%;
    max-width: 768px;
    border-radius: 12px;
    padding: 11px 12px;
}

.git-card {
    border: 1px solid rgba(var(--accent-rgb), 0.55);
    border-left: 3px solid var(--accent);
    background: linear-gradient(180deg, rgba(53, 43, 36, 0.74), rgba(30, 28, 23, 0.95));
}

.pr-card {
    border: 1px solid rgba(113, 129, 213, 0.62);
    border-left: 3px solid #6c7fd8;
    background: linear-gradient(180deg, rgba(43, 49, 72, 0.72), rgba(29, 31, 45, 0.95));
}

.ci-status-card {
    border: 1px solid rgba(95, 95, 86, 0.9);
    border-left: 3px solid #b0aa96;
    background: linear-gradient(180deg, rgba(45, 45, 39, 0.8), rgba(27, 27, 23, 0.95));
    margin-top: 8px;
}

.cipr-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}

.cipr-title {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: #e8e5d8;
    font-size: 13px;
    font-weight: 600;
}

.cipr-meta {
    margin-top: 6px;
    font-size: 12px;
    color: #c6c2b2;
    word-break: break-word;
}

.cipr-meta-label {
    color: #9f9a86;
    margin-right: 4px;
}

.cipr-link {
    color: #9db6ff;
    text-decoration: underline;
    text-decoration-color: rgba(157, 182, 255, 0.4);
    transition: color var(--motion-fast) var(--ease-standard), text-decoration-color var(--motion-fast) var(--ease-standard);
}

.cipr-link:hover {
    color: #c4d2ff;
    text-decoration-color: rgba(196, 210, 255, 0.9);
}

.cipr-badge {
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid transparent;
    text-transform: capitalize;
}

.cipr-badge.open {
    border-color: rgba(103, 182, 126, 0.65);
    color: #bfe8c8;
    background: rgba(50, 117, 72, 0.35);
}

.cipr-badge.merged {
    border-color: rgba(108, 127, 216, 0.72);
    color: #ced9ff;
    background: rgba(56, 67, 122, 0.42);
}

.cipr-badge.closed {
    border-color: rgba(198, 95, 90, 0.72);
    color: #f1c0bd;
    background: rgba(116, 47, 44, 0.45);
}

.ci-indicator {
    display: inline-flex;
    align-items: center;
    gap: 7px;
}

.ci-icon {
    display: inline-block;
    width: 15px;
    text-align: center;
}

.ci-indicator.pending .ci-icon {
    color: #e7c75e;
    animation: ciSpin 900ms linear infinite;
}

.ci-indicator.passing .ci-icon {
    color: #78d18d;
}

.ci-indicator.failing .ci-icon {
    color: #e28981;
}

@keyframes ciSpin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.ci-fix-btn {
    margin-top: 8px;
    border: 1px solid rgba(198, 95, 90, 0.75);
    border-radius: 8px;
    background: rgba(126, 50, 45, 0.42);
    color: #f3c6c3;
    padding: 6px 10px;
    font-size: 12px;
    cursor: pointer;
    transition: background-color var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}

.ci-fix-btn:hover {
    background: rgba(153, 60, 55, 0.52);
}

.pr-ci-slot {
    margin-top: 8px;
}

.artifact-indicator {
    margin-top: 8px;
    border: 1px solid rgba(var(--accent-rgb), 0.5);
    background: var(--accent-soft);
    color: var(--text-accent-soft);
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 11px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard);
}

.artifact-indicator:hover {
    border-color: rgba(var(--accent-rgb), 0.8);
    background: rgba(var(--accent-rgb), 0.24);
}

.artifact-indicator-icon {
    font-size: 12px;
    line-height: 1;
}

#artifactsPanel {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(var(--artifacts-panel-width), 94vw);
    border-left: 1px solid var(--input-border);
    background:
        radial-gradient(circle at 12% 8%, rgba(var(--accent-rgb), 0.08), transparent 38%),
        var(--artifacts-panel-bg);
    transform: translateX(100%);
    transition: transform var(--motion-normal) var(--ease-standard);
    z-index: 50;
    pointer-events: none;
    display: flex;
    flex-direction: column;
}

.artifacts-panel-header {
    flex: none;
    min-height: 44px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--input-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.artifacts-panel-title {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.1px;
}

.artifacts-close-btn {
    border: 1px solid var(--chip-border);
    background: transparent;
    color: var(--muted);
    width: 26px;
    height: 26px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard),
        color var(--motion-fast) var(--ease-standard);
}

.artifacts-close-btn:hover {
    color: var(--text);
    border-color: var(--accent-rgba-072);
    background: rgba(var(--accent-rgb), 0.1);
}

.artifacts-panel-body {
    min-height: 0;
    display: grid;
    grid-template-rows: minmax(140px, 38%) minmax(180px, 1fr);
    height: 100%;
}

.artifacts-list {
    min-height: 0;
    overflow-y: auto;
    border-bottom: 1px solid var(--input-border);
    padding: 8px;
}

.artifact-empty {
    color: var(--muted);
    font-size: 12px;
    text-align: center;
    padding: 18px 12px;
}

.artifact-row {
    width: 100%;
    border: 1px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: var(--text);
    text-align: left;
    cursor: pointer;
    padding: 8px 9px;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard),
        box-shadow var(--motion-fast) var(--ease-standard);
}

.artifact-row + .artifact-row {
    margin-top: 4px;
}

.artifact-row:hover {
    background: var(--surface-overlay-soft);
}

.artifact-row.selected {
    border-color: var(--accent-rgba-072);
    box-shadow: inset 2px 0 0 rgba(var(--accent-rgb), 0.9);
    background: rgba(var(--accent-rgb), 0.09);
}

.artifact-row-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 2px;
}

.artifact-row-title {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
    font-weight: 600;
}

.artifact-row-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--muted);
    font-size: 11px;
}

.artifact-row-badge {
    border: 1px solid var(--input-border);
    background: var(--surface-chip);
    border-radius: 999px;
    padding: 1px 7px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.35px;
}

.artifact-detail-wrap {
    min-height: 0;
    padding: 10px 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.artifact-detail-empty {
    color: var(--muted);
    font-size: 12px;
    text-align: center;
    padding: 16px 10px;
}

.artifact-detail-view {
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.artifact-hidden {
    display: none !important;
}

.artifact-detail-meta {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.artifact-detail-title {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    word-break: break-all;
}

.artifact-detail-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.artifact-tag {
    border: 1px solid var(--input-border);
    background: var(--surface-chip);
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 10px;
    color: var(--text-soft);
    text-transform: uppercase;
    letter-spacing: 0.35px;
}

.artifact-version-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.artifact-version-label {
    color: var(--muted);
    font-size: 11px;
}

#artifactVersionSelect {
    min-height: 28px;
    border-radius: 8px;
    border: 1px solid var(--chip-border);
    background: #33332d;
    color: var(--text);
    font-size: 12px;
    padding: 0 8px;
}

.artifact-version-delta {
    color: #8bbf8a;
    font-size: 11px;
}

.artifact-detail-actions {
    display: flex;
    align-items: center;
    gap: 6px;
}

.artifact-action-btn {
    border: 1px solid var(--chip-border);
    background: transparent;
    color: var(--text);
    border-radius: 999px;
    min-height: 28px;
    padding: 0 10px;
    font-size: 11px;
    cursor: pointer;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard);
}

.artifact-action-btn:hover {
    border-color: var(--accent-rgba-072);
    background: rgba(var(--accent-rgb), 0.1);
}

.artifact-detail-code {
    min-height: 0;
    flex: 1;
    border-radius: 10px;
    border: 1px solid var(--input-border);
    background: var(--code-bg);
    overflow: auto;
}

.artifact-detail-code pre {
    margin: 0;
    padding: 12px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 12px;
    line-height: 1.45;
}

.artifact-detail-code code.hljs {
    background: transparent;
    padding: 0;
}

.message-row.permission .message-inner {
    display: flex;
    justify-content: flex-start;
}

.permission-request-card {
    width: 100%;
    max-width: 768px;
    border-radius: 12px;
    border: 1px solid var(--permission-border);
    background:
        linear-gradient(135deg, var(--permission-gradient-start), var(--permission-gradient-end)),
        var(--bg);
    box-shadow:
        0 0 0 1px var(--permission-shadow-soft),
        0 10px 28px rgba(0, 0, 0, 0.24);
    padding: 12px;
}

.permission-request-card.pending {
    animation: permissionPulse 1800ms ease-in-out infinite;
}

.permission-request-card.resolved {
    animation: none;
    opacity: 0.82;
}

@keyframes permissionPulse {
    0% {
        box-shadow:
            0 0 0 1px var(--permission-shadow-soft),
            0 10px 28px rgba(0, 0, 0, 0.24);
    }
    50% {
        box-shadow:
            0 0 0 1px var(--permission-shadow-strong),
            0 10px 30px rgba(0, 0, 0, 0.24),
            0 0 18px var(--permission-glow);
    }
    100% {
        box-shadow:
            0 0 0 1px var(--permission-shadow-soft),
            0 10px 28px rgba(0, 0, 0, 0.24);
    }
}

.permission-request-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.permission-request-icon {
    width: 24px;
    height: 24px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--accent-rgb), 0.18);
    color: var(--text-accent-soft);
    font-size: 13px;
}

.permission-request-title {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.permission-request-tool {
    color: var(--text-accent-soft);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.2px;
}

.permission-request-subtitle {
    color: var(--text-soft);
    font-size: 11px;
}

.permission-request-description {
    color: var(--text);
    font-size: 13px;
    line-height: 1.4;
    margin: 0 0 8px;
}

.permission-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
}

.permission-meta-item {
    flex: 1 1 240px;
    min-width: 0;
}

.permission-meta-label {
    color: var(--text-soft);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.35px;
    margin-bottom: 2px;
}

.permission-meta-value {
    color: var(--text);
    font-size: 12px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    word-break: break-word;
}

.permission-preview {
    border-radius: 8px;
    border: 1px solid var(--permission-shadow-soft);
    background: var(--surface-muted);
    overflow: hidden;
    font-size: 11px;
    margin-bottom: 10px;
}

.permission-preview .tool-diff-old,
.permission-preview .tool-diff-new,
.permission-preview .tool-code {
    border-bottom: 1px solid var(--permission-shadow-soft);
}

.permission-preview .tool-code:last-child,
.permission-preview .tool-diff-new:last-child {
    border-bottom: 0;
}

.permission-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.permission-action-btn {
    border: 1px solid var(--surface-overlay-border);
    border-radius: 8px;
    background: var(--surface-card-soft);
    color: var(--text);
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
    transition:
        border-color var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard);
}

.permission-action-btn:hover {
    border-color: var(--accent-rgba-072);
}

.permission-action-btn.allow {
    border-color: rgba(93, 174, 122, 0.72);
    background: rgba(36, 95, 56, 0.4);
    color: #bde9cb;
}

.permission-action-btn.allow:hover {
    background: rgba(52, 130, 76, 0.46);
}

.permission-action-btn.deny {
    border-color: rgba(197, 92, 88, 0.72);
    background: rgba(110, 40, 38, 0.45);
    color: #f1bfbc;
}

.permission-action-btn.deny:hover {
    background: rgba(142, 52, 48, 0.52);
}

.permission-comment-wrap {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: 1 1 300px;
    min-width: 220px;
}

.permission-comment-input {
    flex: 1 1 auto;
    min-width: 140px;
    border: 1px solid var(--surface-overlay-border);
    border-radius: 8px;
    background: var(--surface-muted);
    color: var(--text);
    font-size: 12px;
    padding: 6px 8px;
}

.permission-comment-input:focus {
    outline: none;
    border-color: var(--accent-rgba-072);
    box-shadow: 0 0 0 1px var(--accent-rgba-055);
}

.permission-response-status {
    margin-top: 9px;
    color: var(--text-soft);
    font-size: 11px;
}

.permission-request-card.resolved .permission-action-btn,
.permission-request-card.resolved .permission-comment-input {
    cursor: default;
    opacity: 0.62;
}

.permission-request-card.permission-denied {
    border-color: rgba(197, 92, 88, 0.55);
    background: linear-gradient(135deg, rgba(110, 40, 38, 0.18), rgba(45, 35, 30, 0.92));
}

.permission-request-card.permission-denied.pending {
    animation: permissionDeniedPulse 2200ms ease-in-out infinite;
}

@keyframes permissionDeniedPulse {
    0%, 100% { box-shadow: 0 1px 10px rgba(197, 70, 60, 0.25); }
    50% { box-shadow: 0 2px 22px rgba(220, 80, 70, 0.42); }
}

.permission-action-btn.always-allow {
    border-color: rgba(155, 140, 100, 0.72);
    background: rgba(90, 75, 35, 0.4);
    color: #e4d8a8;
}

.permission-action-btn.always-allow:hover {
    background: rgba(120, 100, 45, 0.5);
}


.markdown-body p {
    margin: 0 0 0.7em;
}

.markdown-body p:last-child {
    margin-bottom: 0;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
    margin: 0 0 0.65em;
    line-height: 1.34;
}

.markdown-body h1 {
    font-size: 1.25em;
}

.markdown-body h2 {
    font-size: 1.16em;
}

.markdown-body h3 {
    font-size: 1.08em;
}

.markdown-body ul,
.markdown-body ol {
    margin: 0 0 0.8em;
    padding-left: 1.6em;
}

.markdown-body li {
    margin: 0.2em 0;
}

.markdown-body a {
    color: var(--accent);
    transition: color var(--motion-fast) var(--ease-standard), text-decoration-color var(--motion-fast) var(--ease-standard);
}

.markdown-body a:hover {
    text-decoration: underline;
}

.markdown-body blockquote {
    margin: 0 0 0.8em;
    padding: 0.45em 0.9em;
    border-left: 3px solid var(--accent);
    background: var(--surface-muted);
    border-radius: 8px;
    font-style: italic;
}

.markdown-body code.inline-code {
    border-radius: 4px;
    border: none;
    background: var(--inline-code-bg);
    padding: 2px 6px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 0.92em;
}

.markdown-body table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 0.8em;
    border: 1px solid var(--table-border);
    border-radius: 8px;
    overflow: hidden;
}

.markdown-body th,
.markdown-body td {
    border: 1px solid var(--table-border);
    padding: 6px 8px;
    text-align: left;
}

.markdown-body th {
    background: var(--surface-muted-strong);
}

.markdown-body hr {
    border: none;
    border-top: 1px solid var(--table-border);
    margin: 0.9em 0;
}

.assistant-message h1 { font-size: 1.35em; font-weight: 700; margin: 1.2em 0 0.5em; }
.assistant-message h2 { font-size: 1.2em; font-weight: 600; margin: 1em 0 0.4em; }
.assistant-message h3 { font-size: 1.05em; font-weight: 600; margin: 0.8em 0 0.3em; }
.assistant-message p { margin: 0 0 0.7em; }
.assistant-message ul, .assistant-message ol { padding-left: 1.5em; margin: 0 0 0.7em; }
.assistant-message li { margin: 0.2em 0; }
.assistant-message blockquote {
    border-left: 3px solid var(--accent);
    padding-left: 1em;
    margin: 0 0 0.7em;
    color: var(--text-soft);
    background: none;
    border-radius: 0;
    font-style: normal;
}
.assistant-message table { border-collapse: collapse; width: 100%; margin: 0.7em 0; font-size: 14px; }
.assistant-message th, .assistant-message td {
    border: 1px solid var(--surface-overlay-border);
    padding: 6px 12px;
    text-align: left;
}
.assistant-message th { background: var(--surface-overlay); font-weight: 600; }
.assistant-message hr { border: none; border-top: 1px solid var(--surface-overlay-border); margin: 1em 0; }
.assistant-message code:not(pre code) {
    background: var(--surface-overlay);
    color: var(--inline-code-color);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.88em;
}

.code-block {
    background: var(--code-block-bg);
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    overflow: hidden;
    margin: 0.75rem 0;
}

.code-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 14px;
    background: var(--surface-overlay-soft);
    border-bottom: 1px solid var(--surface-overlay);
    font-size: 12px;
}

.code-head span {
    color: var(--code-head-muted);
    text-transform: lowercase;
    font-size: 11px;
    font-weight: 500;
}

.action-btn {
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11px;
    cursor: pointer;
}

.code-copy-btn,
.action-btn.copy-action {
    transition:
        background-color var(--motion-fast) var(--ease-standard),
        color var(--motion-fast) var(--ease-standard),
        transform var(--motion-fast) var(--ease-standard);
}

.code-copy-btn:active,
.action-btn.copy-action:active {
    transform: scale(0.92);
}

.code-copy-btn.copied,
.action-btn.copy-action.copied {
    color: #22c55e !important;
    background: rgba(34, 197, 94, 0.1) !important;
}

.code-block pre {
    margin: 0;
    padding: 14px 16px;
    overflow-x: auto;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 13px;
    line-height: 1.6;
}

.code-block pre code.hljs {
    background: transparent;
    padding: 0;
}

.hljs-keyword { color: #c678dd; }
.hljs-string { color: #98c379; }
.hljs-number { color: #d19a66; }
.hljs-comment { color: #5c6370; font-style: italic; }
.hljs-built_in { color: #e6c07b; }
.hljs-literal { color: #56b6c2; }
.hljs-title { color: #61afef; }
.hljs-type { color: #e6c07b; }
.hljs-attr { color: #d19a66; }
.hljs-meta { color: #61afef; }
.hljs-tag { color: var(--inline-code-color); }

#imageLightbox {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgba(8, 8, 8, 0.82);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
}

#imageLightbox.open {
    display: flex;
}

#lightboxImage {
    max-width: min(96vw, 1400px);
    max-height: 90vh;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 16px 56px rgba(0, 0, 0, 0.6);
}

#lightboxCloseBtn {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 40px;
    height: 40px;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 999px;
    background: rgba(12, 12, 12, 0.62);
    color: #f6f2e6;
    font-size: 24px;
    line-height: 1;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: background-color var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}

#lightboxCloseBtn:hover {
    background: rgba(25, 25, 25, 0.9);
    border-color: rgba(255, 255, 255, 0.4);
}

.typing-shell {
    display: flex;
    align-items: center;
    gap: 8px;
}

.token-fade-in {
    animation: token-fade-in var(--motion-fast) var(--ease-enter) forwards;
}

.assistant-message > * {
    animation: token-fade-in var(--motion-fast) var(--ease-enter) forwards;
}

@keyframes token-fade-in {

    from { opacity: 0; transform: translateY(2px); }
    to { opacity: 1; transform: translateY(0); }
}

.thinking-shell {

    display: flex;
    flex-direction: column;
    align-items: flex-start;
}

.thinking-indicator {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 12px 16px;
    width: fit-content;
    animation: messageEnter var(--motion-normal) var(--ease-enter) both;
}

.thinking-indicator span {
    display: block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #94a3b8;
    animation: dotBounce var(--motion-loop) ease-in-out infinite;
}

.thinking-indicator span:nth-child(2) { animation-delay: calc(var(--motion-loop) / 6); }
.thinking-indicator span:nth-child(3) { animation-delay: calc(var(--motion-loop) / 3); }

@keyframes dotBounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
    30% { transform: translateY(-6px); opacity: 1; }
}

.thinking-indicator.fade-out {
    opacity: 0;
    transform: translateY(-4px);
    transition: opacity var(--motion-fast) var(--ease-exit), transform var(--motion-fast) var(--ease-exit);
}

.wait-status-text {
    font-size: 12px;
    color: var(--muted);
    margin-top: 4px;
    opacity: 0;
    transition: opacity var(--motion-normal) var(--ease-standard);
}

.wait-status-text.visible { opacity: 1; }

#chatComposer {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 18px 14px 16px;
    background: linear-gradient(180deg, rgba(47, 47, 42, 0) 0%, rgba(47, 47, 42, 0.95) 30%, rgba(47, 47, 42, 1) 100%);
}

#chatComposer .composer-card {
    margin: 0 auto;
}

.stop-process-slot {
    display: none;
    min-height: 38px;
    justify-content: center;
    align-items: flex-start;
    margin: 0 auto 10px;
}

.stop-process-slot.is-visible {
    display: flex;
}

.stop-process-btn {
    border: 1px solid rgba(220, 80, 60, 0.4);
    background: rgba(220, 80, 60, 0.12);
    color: #e07a6a;
    border-radius: 999px;
    padding: 5px 18px;
    font-size: 13px;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    cursor: pointer;
    transition:
        opacity var(--motion-fast) var(--ease-standard),
        visibility var(--motion-fast) var(--ease-standard),
        background-color var(--motion-fast) var(--ease-standard),
        border-color var(--motion-fast) var(--ease-standard);
}

.stop-process-btn.is-visible {
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
}

.stop-process-btn:hover {
    background: rgba(220, 80, 60, 0.22);
    border-color: rgba(220, 80, 60, 0.65);
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

body.reduced-motion *,
body.reduced-motion *::before,
body.reduced-motion *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    transform: none !important;
}

@media (prefers-reduced-transparency: reduce) {
    .folder-path-btn,
    .plus-btn,
    .agent-mode-toggle-btn,
    .selector-btn,
    .permission-btn,
    .permission-selector,
    .assistant-action,
    .action-btn,
    .code-copy-btn,
    .chip,
    .quick-chip,
    .artifact-action-btn,
    .stop-process-btn,
    .example-prompt,
    .popup-menu {
        --glass-tint-interactive: var(--surface-panel);
        --glass-tint-interactive-hover: var(--surface-panel-elevated, var(--surface-panel));
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }
}

@media (min-width: 1100px) {
    #chatView.artifacts-open #messages {
        padding-right: calc(var(--artifacts-panel-width) + 20px);
    }

    #chatView.artifacts-open #chatComposer {
        right: var(--artifacts-panel-width);
    }

    #chatView.artifacts-open #chatToolbar {
        right: calc(var(--artifacts-panel-width) + 14px);
    }
}

@media (max-width: 1099px) {
    #artifactsPanel {
        width: min(var(--artifacts-panel-width), 100vw);
        box-shadow: -10px 0 28px rgba(0, 0, 0, 0.4);
    }
}

@media (max-width: 900px) {
    .welcome-title {
        font-size: 25px;
    }

    .example-prompts {
        grid-template-columns: 1fr 1fr;
    }

    .composer-card {
        border-radius: 20px;
        padding: 11px;
    }

    #messages {
        padding-left: 10px;
        padding-right: 10px;
        padding-bottom: 210px;
    }

    #chatToolbar {
        top: 10px;
        right: 10px;
    }

    #chatView.artifacts-open #chatToolbar {
        right: 10px;
    }

    #chatComposer {
        padding-left: 10px;
        padding-right: 10px;
    }

    .popup-menu {
        width: min(92vw, 280px);
    }
}

@media (max-width: 640px) {
    .example-prompts {
        grid-template-columns: 1fr;
    }
}
</style>
</head>
<body>
<div id="app">
    <section id="welcomeView">
        <div id="welcomeScreen" class="welcome-shell">
            <img id="welcomeScreenIcon" class="welcome-icon" alt="" aria-hidden="true" hidden>
            <h1 id="welcomeTitle" class="welcome-title">Back at it</h1>
            <div id="welcomeProviderBadge" class="welcome-provider-badge">
                <img id="welcomeProviderIcon" class="welcome-provider-icon" alt="" aria-hidden="true">
                <span id="welcomeProviderName">Claude</span>
            </div>

                <div class="composer-card" style="position:relative;">
                    <div id="welcomeSlashDropdown" class="slash-dropdown" role="listbox" aria-label="Skills"></div>
                    <div id="welcomeAttachments" class="attachment-strip"></div>
                    <textarea id="welcomeInput" class="composer-input" rows="1" placeholder="Type / for skills" title="Enter to send, Shift+Enter for newline, / for slash commands"></textarea>
                    <div class="control-row">
                        <div class="control-left">
                            <button class="plus-btn" type="button" aria-label="Attach files">
                                <span class="plus-btn-icon" aria-hidden="true">
                                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M12 5v14M5 12h14" />
                                    </svg>
                                </span>
                            </button>
                            <button class="agent-mode-toggle-btn" type="button" aria-label="Enable agent mode" aria-pressed="false" title="Agent mode is disabled">
                                <span class="agent-mode-toggle-icon" aria-hidden="true">
                                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <rect class="toggle-track" x="3" y="6" width="18" height="12" rx="6" />
                                        <circle class="toggle-knob" cx="9" cy="12" r="4" />
                                    </svg>
                                </span>
                            </button>
                        </div>
                    <div class="control-right">
                        <div class="selector-group">
                            <button class="selector-btn model-selector" type="button" aria-haspopup="true" aria-expanded="false">
                                <span class="model-label">Opus 4.6</span>
                                <span class="selector-caret">▾</span>
                            </button>
                            <div class="popup-menu model-popup" role="menu"></div>
                        </div>
                        <div class="selector-group">
                            <button class="selector-btn reasoning-selector" type="button" aria-haspopup="true" aria-expanded="false" title="Reasoning level">
                                <span class="reasoning-label">Medium</span>
                                <span class="selector-caret">▾</span>
                            </button>
                            <div class="popup-menu reasoning-popup" role="menu"></div>
                        </div>
                        <div class="selector-group">
                            <button class="permission-btn permission-selector" type="button" aria-haspopup="true" aria-expanded="false" title="Permissions">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M5 7.5H19" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                                    <path d="M5 12H14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                                    <path d="M5 16.5H11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                                </svg>
                            </button>
                            <div class="popup-menu permission-popup" role="menu"></div>
                        </div>
                    </div>
                </div>
                <button class="folder-path-btn" type="button" title="Change project folder">
                    <span class="folder-path-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 6h5.5l1.5 2H21v10H3V6z" />
                            <path d="M4 8h16" />
                        </svg>
                    </span>
                    <span class="folder-path-text">~</span>
                </button>
            </div>

            <div class="quick-chips">
                <button class="chip quick-chip" type="button" data-value="Build a robust implementation plan for this code change."> &lt;/&gt; Code</button>
                <button class="chip quick-chip" type="button" data-value="Create a polished first draft for this project task.">⚙ Create</button>
                <button class="chip quick-chip" type="button" data-value="Teach me the core concepts with practical examples.">📖 Learn</button>
                <button class="chip quick-chip" type="button" data-value="Write concise release notes for the latest changes.">✏ Write</button>
                <button class="chip quick-chip" type="button" data-value="Help me sort out everyday logistics and planning.">☕ Life stuff</button>
            </div>
            <div class="keyboard-hints" aria-label="Keyboard hints">
                <span class="keyboard-hint"><kbd>Enter</kbd> Send</span>
                <span class="keyboard-hint"><kbd>Shift+Enter</kbd> Newline</span>
                <span class="keyboard-hint"><kbd>Esc</kbd> Stop</span>
                <span class="keyboard-hint"><kbd>/</kbd> Slash commands</span>
            </div>
        </div>
    </section>

    <section id="chatView">
        <div id="dropOverlay">Drop file here</div>
        <div id="chatSearchBar" class="chat-search-bar" style="display:none;">
            <input type="text" id="chatSearchInput" placeholder="Search messages..." aria-label="Search messages" />
            <span class="chat-search-count" role="status" aria-live="polite"><span id="chatSearchCurrent">0</span> / <span id="chatSearchTotal">0</span></span>
            <span id="chatSearchLimitNote" class="chat-search-limit-note"></span>
            <button id="chatSearchPrev" type="button" title="Previous (Shift+Enter)" aria-label="Previous match">↑</button>
            <button id="chatSearchNext" type="button" title="Next (Enter)" aria-label="Next match">↓</button>
            <button id="chatSearchClose" type="button" title="Close (Esc)" aria-label="Close search">✕</button>
        </div>
        <div id="chatToolbar">
            <button id="artifactsToggleBtn" type="button" title="Open artifacts panel">📦 Artifacts</button>
        </div>
        <div id="messages"></div>
        <button id="scroll-to-bottom-btn" type="button" aria-label="Scroll to bottom">↓</button>
        <aside id="artifactsPanel" aria-hidden="true">
            <div class="artifacts-panel-header">
                <h2 class="artifacts-panel-title">Artifacts</h2>
                <button id="artifactsCloseBtn" class="artifacts-close-btn" type="button" aria-label="Close artifacts panel">×</button>
            </div>
            <div class="artifacts-panel-body">
                <div id="artifactsList" class="artifacts-list">
                    <div class="artifact-empty">No artifacts yet.</div>
                </div>
                <div class="artifact-detail-wrap">
                    <div id="artifactDetailEmpty" class="artifact-detail-empty">Select an artifact to view its content.</div>
                    <div id="artifactDetailView" class="artifact-detail-view artifact-hidden">
                        <div class="artifact-detail-meta">
                            <h3 id="artifactDetailTitle" class="artifact-detail-title"></h3>
                            <div class="artifact-detail-tags">
                                <span id="artifactDetailTypeTag" class="artifact-tag"></span>
                                <span id="artifactDetailLanguageTag" class="artifact-tag"></span>
                                <span id="artifactDetailVersionTag" class="artifact-tag"></span>
                            </div>
                        </div>
                        <div class="artifact-version-row">
                            <span class="artifact-version-label">Version</span>
                            <select id="artifactVersionSelect"></select>
                            <span id="artifactVersionDelta" class="artifact-version-delta"></span>
                        </div>
                        <div class="artifact-detail-actions">
                            <button id="artifactCopyBtn" class="artifact-action-btn" type="button">Copy</button>
                            <button id="artifactDownloadBtn" class="artifact-action-btn" type="button">Download</button>
                            <button id="artifactOpenTabBtn" class="artifact-action-btn" type="button">Open in new tab</button>
                        </div>
                        <div class="artifact-detail-code">
                            <pre><code id="artifactDetailCode" class="hljs"></code></pre>
                        </div>
                    </div>
                </div>
            </div>
        </aside>

        <div id="chatComposer">
            <div id="stopProcessSlot" class="stop-process-slot">
                <button id="stopBtn" class="stop-process-btn" type="button" title="Stop generating (Esc)">Stop generating</button>
            </div>
            <div class="composer-card" style="position:relative;">
                <div id="chatSlashDropdown" class="slash-dropdown" role="listbox" aria-label="Skills"></div>
                <div id="chatAttachments" class="attachment-strip"></div>
                <textarea id="chatInput" class="composer-input" rows="1" placeholder="Reply..." title="Enter to send, Shift+Enter for newline, / for slash commands"></textarea>
                <div class="control-row">
                    <div class="control-left">
                        <button class="plus-btn" type="button" aria-label="Attach files">
                            <span class="plus-btn-icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M12 5v14M5 12h14" />
                                </svg>
                            </span>
                        </button>
                            <button class="agent-mode-toggle-btn" type="button" aria-label="Enable agent mode" aria-pressed="false" title="Agent mode is disabled">
                            <span class="agent-mode-toggle-icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <rect class="toggle-track" x="3" y="6" width="18" height="12" rx="6" />
                                    <circle class="toggle-knob" cx="9" cy="12" r="4" />
                                </svg>
                            </span>
                        </button>
                    </div>
                    <div class="control-right">
                        <div class="selector-group">
                            <button class="selector-btn model-selector" type="button" aria-haspopup="true" aria-expanded="false">
                                <span class="model-label">Opus 4.6</span>
                                <span class="selector-caret">▾</span>
                            </button>
                            <div class="popup-menu model-popup" role="menu"></div>
                        </div>
                        <div class="selector-group">
                            <button class="selector-btn reasoning-selector" type="button" aria-haspopup="true" aria-expanded="false" title="Reasoning level">
                                <span class="reasoning-label">Medium</span>
                                <span class="selector-caret">▾</span>
                            </button>
                            <div class="popup-menu reasoning-popup" role="menu"></div>
                        </div>
                        <div class="selector-group">
                            <button class="permission-btn permission-selector" type="button" aria-haspopup="true" aria-expanded="false" title="Permissions">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M5 7.5H19" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                                    <path d="M5 12H14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                                    <path d="M5 16.5H11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                                </svg>
                            </button>
                            <div class="popup-menu permission-popup" role="menu"></div>
                        </div>
                    </div>
                </div>
                <button class="folder-path-btn" type="button" title="Change project folder">
                    <span class="folder-path-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 6h5.5l1.5 2H21v10H3V6z" />
                            <path d="M4 8h16" />
                        </svg>
                    </span>
                    <span class="folder-path-text">~</span>
                </button>
            </div>
        </div>
    </section>
</div>
<div id="imageLightbox" aria-hidden="true">
    <button id="lightboxCloseBtn" type="button" aria-label="Close image viewer">×</button>
    <img id="lightboxImage" alt="" />
</div>

<script>
(function () {
    let MODEL_OPTIONS = [
        {
            value: "sonnet",
            short: "Sonnet 4.6",
            title: "Claude Sonnet (Latest)",
            description: "Balanced speed and reasoning for most conversations.",
        },
        {
            value: "opus",
            short: "Opus 4.6",
            title: "Claude Opus (Latest)",
            description: "Deepest reasoning and strongest quality for complex work.",
        },
        {
            value: "haiku",
            short: "Haiku 4.5",
            title: "Claude Haiku (Latest)",
            description: "Fastest responses for lightweight tasks.",
        },
    ];

    let REASONING_OPTIONS = [
        {
            value: "low",
            title: "Low",
            description: "Fast responses with standard reasoning.",
        },
        {
            value: "medium",
            title: "Medium",
            description: "Balanced reasoning for everyday tasks.",
        },
        {
            value: "high",
            title: "High",
            description: "Deep reasoning for complex problems.",
        },
    ];

    let PERMISSION_OPTIONS = [
        {
            value: "auto",
            title: "Auto",
            description: "Asks only when approval is needed.",
        },
        {
            value: "plan",
            title: "Plan mode",
            description: "Proposes plans before applying changes.",
        },
        {
            value: "bypassPermissions",
            title: "Bypass permissions",
            description: "Runs actions directly with fewer confirmations.",
        },
    ];

    const DEFAULT_SLASH_COMMANDS = [
        { name: "/agent", icon: "\u25A7", description: "Main chat: one-shot worker (/agent <task>) + pane controls", providers: ["claude", "codex", "gemini"] },
        { name: "/help", icon: "?", description: "Show available commands and usage tips", providers: ["claude", "codex", "gemini"] },
        { name: "/clear", icon: "\u2716", description: "Clear the current conversation", providers: ["claude", "codex", "gemini"] },
        { name: "/compact", icon: "\u25A3", description: "Compact conversation to save context", providers: ["claude"] },
        { name: "/cost", icon: "$", description: "Show token usage and cost for this session", providers: ["claude"] },
        { name: "/doctor", icon: "\u2695", description: "Check CLI installation health", providers: ["claude"] },
        { name: "/init", icon: "\u2699", description: "Initialize project with CLAUDE.md", providers: ["claude"] },
        { name: "/login", icon: "\u2192", description: "Switch Anthropic accounts", providers: ["claude"] },
        { name: "/logout", icon: "\u2190", description: "Sign out from your Anthropic account", providers: ["claude"] },
        { name: "/memory", icon: "\u2601", description: "Edit CLAUDE.md memory files", providers: ["claude"] },
        { name: "/model", icon: "\u269B", description: "Switch the AI model", providers: ["claude", "codex", "gemini"] },
        { name: "/permissions", icon: "\u26A0", description: "View or update tool permissions", providers: ["claude"] },
        { name: "/pr-review", icon: "\u2714", description: "Review a GitHub pull request", providers: ["claude", "codex", "gemini"] },
        { name: "/review", icon: "\u2606", description: "Review code changes", providers: ["claude", "codex", "gemini"] },
        { name: "/status", icon: "\u2139", description: "Show session and git status", providers: ["claude"] },
        { name: "/terminal-setup", icon: "\u2328", description: "Install Shift+Enter key binding", providers: ["claude"] },
        { name: "/vim", icon: "V", description: "Toggle vim mode for input", providers: ["claude"] },
    ];
    const EXAMPLE_PROMPTS_BY_PROVIDER = Object.freeze({
        claude: [
            "Refactor this function",
            "Explain this codebase",
            "Write tests for X",
        ],
        codex: [
            "Implement feature Y",
            "Debug this error",
            "Run the test suite",
        ],
        gemini: [
            "Plan this implementation",
            "Review this diff",
            "Debug this failing test",
        ],
    });
    var HOST_SLASH_COMMANDS = [];

    const appEl = document.getElementById("app");
    const welcomeViewEl = document.getElementById("welcomeView");
    const welcomeTitleEl = document.getElementById("welcomeTitle");
    const welcomeScreenIconEl = document.getElementById("welcomeScreenIcon");
    const welcomeProviderBadgeEl = document.getElementById("welcomeProviderBadge");
    const welcomeProviderIconEl = document.getElementById("welcomeProviderIcon");
    const welcomeProviderNameEl = document.getElementById("welcomeProviderName");
    const examplePromptsTitleEl = document.getElementById("examplePromptsTitle");
    const welcomeExamplePromptsEl = document.getElementById("welcomeExamplePrompts");
    const chatViewEl = document.getElementById("chatView");
    const messagesEl = document.getElementById("messages");
    const scrollToBottomBtnEl = document.getElementById("scroll-to-bottom-btn");
    const welcomeInputEl = document.getElementById("welcomeInput");
    const chatInputEl = document.getElementById("chatInput");
    const welcomeSlashDropdownEl = document.getElementById("welcomeSlashDropdown");
    const chatSlashDropdownEl = document.getElementById("chatSlashDropdown");
    const dropOverlayEl = document.getElementById("dropOverlay");
    const welcomeAttachmentsEl = document.getElementById("welcomeAttachments");
    const chatAttachmentsEl = document.getElementById("chatAttachments");
    const stopBtnEl = document.getElementById("stopBtn");
    const stopProcessSlotEl = document.getElementById("stopProcessSlot");
    const imageLightboxEl = document.getElementById("imageLightbox");
    const lightboxImageEl = document.getElementById("lightboxImage");
    const lightboxCloseBtnEl = document.getElementById("lightboxCloseBtn");
    const chatSearchBarEl = document.getElementById("chatSearchBar");
    const chatSearchInputEl = document.getElementById("chatSearchInput");
    const chatSearchCurrentEl = document.getElementById("chatSearchCurrent");
    const chatSearchTotalEl = document.getElementById("chatSearchTotal");
    const chatSearchLimitNoteEl = document.getElementById("chatSearchLimitNote");
    const chatSearchPrevEl = document.getElementById("chatSearchPrev");
    const chatSearchNextEl = document.getElementById("chatSearchNext");
    const chatSearchCloseEl = document.getElementById("chatSearchClose");
    const artifactsToggleBtnEl = document.getElementById("artifactsToggleBtn");
    const artifactsPanelEl = document.getElementById("artifactsPanel");
    const artifactsCloseBtnEl = document.getElementById("artifactsCloseBtn");
    const artifactsListEl = document.getElementById("artifactsList");
    const artifactDetailEmptyEl = document.getElementById("artifactDetailEmpty");
    const artifactDetailViewEl = document.getElementById("artifactDetailView");
    const artifactDetailTitleEl = document.getElementById("artifactDetailTitle");
    const artifactDetailTypeTagEl = document.getElementById("artifactDetailTypeTag");
    const artifactDetailLanguageTagEl = document.getElementById("artifactDetailLanguageTag");
    const artifactDetailVersionTagEl = document.getElementById("artifactDetailVersionTag");
    const artifactVersionSelectEl = document.getElementById("artifactVersionSelect");
    const artifactVersionDeltaEl = document.getElementById("artifactVersionDelta");
    const artifactDetailCodeEl = document.getElementById("artifactDetailCode");
    const artifactCopyBtnEl = document.getElementById("artifactCopyBtn");
    const artifactDownloadBtnEl = document.getElementById("artifactDownloadBtn");
    const artifactOpenTabBtnEl = document.getElementById("artifactOpenTabBtn");

    const modelButtons = Array.from(document.querySelectorAll(".model-selector"));
    const reasoningButtons = Array.from(document.querySelectorAll(".reasoning-selector"));
    const permissionButtons = Array.from(document.querySelectorAll(".permission-selector"));
    const modelPopups = Array.from(document.querySelectorAll(".model-popup"));
    const reasoningPopups = Array.from(document.querySelectorAll(".reasoning-popup"));
    const permissionPopups = Array.from(document.querySelectorAll(".permission-popup"));
    const plusButtons = Array.from(document.querySelectorAll(".plus-btn"));
    const agentModeToggleButtons = Array.from(document.querySelectorAll(".agent-mode-toggle-btn"));
    const quickChips = Array.from(document.querySelectorAll(".quick-chip"));
    const folderPathButtons = Array.from(document.querySelectorAll(".folder-path-btn"));
    const folderPathTexts = Array.from(document.querySelectorAll(".folder-path-text"));
    const DIFF_LCS_CELL_LIMIT = 250000;
    const DIFF_HARD_LINE_LIMIT = 1800;
    const DIFF_RENDER_LINE_LIMIT = 1000;
    const DIFF_AUTO_EXPAND_MAX_LINES = 180;
    const MOTION_FAST_MS = 120;
    const DEFAULT_STREAM_RENDER_THROTTLE_MS = 80;
    const WAIT_INACTIVITY_MS = 5000;
    const WAIT_ROTATE_MS = 4000;
    const WAIT_STATUS_MIN_INTERVAL_MS = 1000;
    const WAIT_STATUS_FADE_MS = 180;
    const WAIT_STATUS_MAX_COMMAND_LENGTH = 40;
    const SLASH_REFRESH_DEBOUNCE_MS = 140;
    const WAIT_FALLBACK_MESSAGES = Object.freeze([
        "Thinking...",
        "Still working...",
        "Reviewing context...",
        "Almost there...",
    ]);
    const CHAT_SEARCH_DEBOUNCE_MS = 150;
    const CHAT_SEARCH_MAX_MATCHES = 500;
    const ASSISTANT_PHASE = Object.freeze({
        IDLE: "idle",
        SENDING: "sending",
        WAITING_FIRST_TOKEN: "waiting_first_token",
        STREAMING: "streaming",
        DONE: "done",
        ERROR: "error",
    });

    let hasMessages = false;
    let typingRow = null;
    let thinkingIndicatorRow = null;
    let currentAssistantRow = null;
    let currentAssistantBody = null;
    let currentAssistantRaw = "";
    let assistantHasFirstChunk = false;
    let assistantPhase = ASSISTANT_PHASE.IDLE;
    let renderQueued = false;
    let renderTimerId = null;
    let lastAssistantRenderAt = 0;
    let streamRenderThrottleMs = DEFAULT_STREAM_RENDER_THROTTLE_MS;
    let pendingAssistantText = "";
    let assistantRevealTimer = null;
    let finishAfterPendingReveal = false;
    let lastAssistantChunkText = "";
    let lastAssistantChunkAt = 0;
    let lastSystemMessageText = "";
    let lastSystemMessageAt = 0;
    let waitStatusVisible = false;
    let waitStatusText = "";
    let waitInactivityTimer = null;
    let waitRotateTimer = null;
    let lastActivityTs = 0;
    let waitStatusLastChangeTs = 0;
    let waitStatusPendingTimer = null;
    let waitStatusTransitionTimer = null;
    let waitStatusPendingText = "";
    let waitFallbackIndex = 0;
    let waitStatusSource = "";
    let processingActive = false;
    let userScrolledUp = false;
    let selectedModel = "opus";
    let selectedReasoning = "medium";
    let selectedPermission = "auto";
    let reasoningVisible = true;
    let paneMode = "main";
    let activeProviderId = "claude";
    let activeProviderName = "Claude";
    let activePopup = null;
    let lastUserPayload = null;
    let lastUserPrompt = "";
    let currentFolderDisplay = "~";
    let attachments = [];
    let attachmentCounter = 0;
    let dragDepth = 0;
    let chatSearchOpen = false;
    let chatSearchDebounceId = null;
    let chatSearchMatches = [];
    let chatSearchCurrentIndex = -1;
    let permissionRequestCounter = 0;
    let toolCardCounter = 0;
    let activeToolTurn = null;
    let lastPRUrl = "";
    let artifactsPanelOpen = false;
    let agentModeEnabled = false;
    let artifactCounter = 0;
    let selectedArtifactId = "";
    let selectedArtifactVersion = 0;
    let artifactSnippetCounter = 0;
    const seenPermissionRequests = Object.create(null);
    const seenToolUseIds = Object.create(null);
    const prCardByKey = Object.create(null);
    const prCardByUrl = Object.create(null);
    const ciCardByKey = Object.create(null);
    const artifacts = [];
    const artifactByKey = Object.create(null);
    let slashDropdownOpen = false;
    let slashSelectedIndex = 0;
    let slashFilteredItems = [];
    let activeSlashInput = null;
    let slashRefreshTimer = null;
    const LANGUAGE_EXTENSION_MAP = Object.freeze({
        bash: ".sh",
        c: ".c",
        cpp: ".cpp",
        csharp: ".cs",
        css: ".css",
        dockerfile: ".Dockerfile",
        go: ".go",
        graphql: ".graphql",
        html: ".html",
        ini: ".ini",
        java: ".java",
        javascript: ".js",
        json: ".json",
        jsx: ".jsx",
        kotlin: ".kt",
        lua: ".lua",
        markdown: ".md",
        md: ".md",
        php: ".php",
        powershell: ".ps1",
        proto: ".proto",
        python: ".py",
        ruby: ".rb",
        rust: ".rs",
        scala: ".scala",
        shell: ".sh",
        sql: ".sql",
        swift: ".swift",
        toml: ".toml",
        ts: ".ts",
        tsx: ".tsx",
        typescript: ".ts",
        xml: ".xml",
        yaml: ".yaml",
        yml: ".yml",
    });
    const EXTENSION_LANGUAGE_MAP = Object.freeze({
        c: "c",
        conf: "ini",
        cpp: "cpp",
        cs: "csharp",
        css: "css",
        go: "go",
        graphql: "graphql",
        h: "c",
        htm: "html",
        html: "html",
        ini: "ini",
        java: "java",
        js: "javascript",
        json: "json",
        jsx: "jsx",
        kt: "kotlin",
        lua: "lua",
        md: "markdown",
        php: "php",
        proto: "proto",
        ps1: "powershell",
        py: "python",
        rb: "ruby",
        rs: "rust",
        scala: "scala",
        sh: "bash",
        sql: "sql",
        swift: "swift",
        toml: "toml",
        ts: "typescript",
        tsx: "tsx",
        xml: "xml",
        yaml: "yaml",
        yml: "yaml",
    });

    function compactDisplayPath(pathValue, maxLength) {
        const normalizedRaw = String(pathValue || "").trim();
        if (!normalizedRaw) {
            return "~";
        }
        const limit = Math.max(10, Number(maxLength) || 44);
        if (normalizedRaw.length <= limit) {
            return normalizedRaw;
        }

        const normalized = normalizedRaw.replace(/\\/g, "/");
        const parts = normalized.split("/").filter(function (part) {
            return part.length > 0;
        });
        const startsWithTilde = normalized.indexOf("~/") === 0;
        const startsWithSlash = normalized.charAt(0) === "/";
        const prefix = startsWithTilde ? "~/" : startsWithSlash ? "/" : "";

        if (parts.length <= 1) {
            return normalizedRaw.slice(0, limit - 1) + "…";
        }
        const first = parts[0];
        const last = parts[parts.length - 1];
        let compact = prefix + first + "/…/" + last;
        if (compact.length > limit) {
            const tailBudget = Math.max(8, limit - prefix.length - 3);
            compact = prefix + "…/" + last.slice(Math.max(0, last.length - tailBudget));
        }
        if (compact.length > limit) {
            return compact.slice(0, limit - 1) + "…";
        }
        return compact;
    }

    function updateFolderDisplay(pathValue) {
        const nextValue = String(pathValue || "").trim() || "~";
        currentFolderDisplay = nextValue;
        const compactValue = compactDisplayPath(currentFolderDisplay, 52);
        folderPathTexts.forEach(function (label) {
            label.textContent = compactValue;
            label.setAttribute("title", currentFolderDisplay);
        });
        folderPathButtons.forEach(function (button) {
            button.setAttribute("title", "Change project folder (" + currentFolderDisplay + ")");
        });
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function safeDecodeURIComponent(value) {
        const raw = String(value || "");
        if (!raw) {
            return "";
        }
        try {
            return decodeURIComponent(raw);
        } catch (_error) {
            return raw;
        }
    }

    function normalizeLanguage(language) {
        const raw = String(language || "").trim().toLowerCase();
        if (!raw) {
            return "";
        }
        if (raw === "js") {
            return "javascript";
        }
        if (raw === "ts") {
            return "typescript";
        }
        if (raw === "py") {
            return "python";
        }
        if (raw === "yml") {
            return "yaml";
        }
        return raw;
    }

    function extensionFromFilename(filename) {
        const base = String(filename || "").split(/[\\/]/).pop() || "";
        const dotIndex = base.lastIndexOf(".");
        if (dotIndex <= 0 || dotIndex === base.length - 1) {
            return "";
        }
        return base.slice(dotIndex + 1).toLowerCase();
    }

    function languageFromFilename(filename) {
        const base = String(filename || "").split(/[\\/]/).pop() || "";
        if (base.toLowerCase() === "dockerfile") {
            return "dockerfile";
        }
        const ext = extensionFromFilename(base);
        if (!ext) {
            return "";
        }
        return EXTENSION_LANGUAGE_MAP[ext] || "";
    }

    function looksLikeFilenameToken(token) {
        const raw = String(token || "").trim().replace(/^['"`]+|['"`:;,]+$/g, "");
        if (!raw) {
            return false;
        }
        if (/[\\/]/.test(raw)) {
            return true;
        }
        if (/^\.\w+/.test(raw)) {
            return true;
        }
        if (/^[\w.-]+\.(?:[a-z0-9]{1,12})$/i.test(raw)) {
            return true;
        }
        if (/^(dockerfile|makefile)$/i.test(raw)) {
            return true;
        }
        return false;
    }

    function parseFenceInfo(info) {
        const raw = String(info || "").trim();
        if (!raw) {
            return {
                info: "",
                language: "",
                filename: "",
            };
        }

        const lower = raw.toLowerCase();
        const tokens = raw.split(/\s+/).filter(Boolean);
        let filename = "";
        let language = "";
        const explicitFile = raw.match(/(?:file|filename|path)\s*[:=]\s*([^\s]+)/i);

        if (explicitFile && explicitFile[1]) {
            filename = String(explicitFile[1] || "").replace(/^['"`]+|['"`:;,]+$/g, "");
        }

        if (lower.startsWith("language:")) {
            language = raw.split(":").slice(1).join(":").trim();
        }

        tokens.forEach(function (token) {
            if (!filename && looksLikeFilenameToken(token)) {
                filename = String(token || "").replace(/^['"`]+|['"`:;,]+$/g, "");
                return;
            }
            if (!language) {
                language = String(token || "").replace(/^language[:=]/i, "").replace(/^['"`]+|['"`:;,]+$/g, "");
            }
        });

        if (!language && filename) {
            language = languageFromFilename(filename);
        }

        language = normalizeLanguage(language);
        return {
            info: raw,
            language: language,
            filename: filename,
        };
    }

    function isStructuredLanguage(language) {
        const normalized = normalizeLanguage(language);
        return normalized === "json"
            || normalized === "yaml"
            || normalized === "toml"
            || normalized === "ini"
            || normalized === "xml"
            || normalized === "graphql"
            || normalized === "env";
    }

    function detectStructuredLanguage(content) {
        const text = String(content || "").trim();
        if (!text) {
            return "";
        }

        if (
            (text.startsWith("{") && text.endsWith("}"))
            || (text.startsWith("[") && text.endsWith("]"))
        ) {
            try {
                JSON.parse(text);
                return "json";
            } catch (_error) {}
        }

        if (/^[\w.-]+\s*:\s*[^\n]+/m.test(text) && text.indexOf("{") < 0) {
            return "yaml";
        }

        if (/^\[[^\]]+\]\s*$/m.test(text) && /^[\w.-]+\s*=/m.test(text)) {
            return "ini";
        }

        return "";
    }

    function isLikelyStructured(language, content) {
        const text = String(content || "");
        if (text.length < 180) {
            return false;
        }
        return isStructuredLanguage(language) || !!detectStructuredLanguage(content);
    }

    function createToolTurnState() {
        return {
            toolCount: 0,
            firstToolRow: null,
            summaryRow: null,
            summaryTitleEl: null,
            summaryFilesEl: null,
            summaryTotalEl: null,
            files: Object.create(null),
            totalAdditions: 0,
            totalDeletions: 0,
        };
    }

    function resetToolTurnState() {
        activeToolTurn = createToolTurnState();
    }

    function normalizeTextForDiff(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/\r\n/g, "\n")
            .replace(/\r/g, "\n");
    }

    function splitLinesForDiff(value) {
        const text = normalizeTextForDiff(value);
        if (!text) {
            return [];
        }
        return text.split("\n");
    }

    function classifyDiffStatus(oldText, newText) {
        const hasOld = String(oldText || "").length > 0;
        const hasNew = String(newText || "").length > 0;
        if (!hasOld && hasNew) {
            return "new";
        }
        if (hasOld && !hasNew) {
            return "deleted";
        }
        return "modified";
    }

    function normalizeDiffType(value) {
        if (value === "add" || value === "remove" || value === "context") {
            return value;
        }
        return "context";
    }

    function mergeFileStatus(left, right) {
        if (left === right) {
            return left;
        }
        return "modified";
    }

    function createDiffOp(type, text) {
        return {
            type: normalizeDiffType(type),
            text: String(text === undefined || text === null ? "" : text),
        };
    }

    function buildLcsDiffOperations(oldLines, newLines) {
        const oldLen = oldLines.length;
        const newLen = newLines.length;
        const width = newLen + 1;
        const scores = new Uint32Array((oldLen + 1) * (newLen + 1));

        for (let i = oldLen - 1; i >= 0; i -= 1) {
            const rowOffset = i * width;
            const nextOffset = (i + 1) * width;
            for (let j = newLen - 1; j >= 0; j -= 1) {
                if (oldLines[i] === newLines[j]) {
                    scores[rowOffset + j] = scores[nextOffset + j + 1] + 1;
                } else {
                    const removeScore = scores[nextOffset + j];
                    const addScore = scores[rowOffset + j + 1];
                    scores[rowOffset + j] = removeScore >= addScore ? removeScore : addScore;
                }
            }
        }

        const operations = [];
        let i = 0;
        let j = 0;
        while (i < oldLen && j < newLen) {
            if (oldLines[i] === newLines[j]) {
                operations.push(createDiffOp("context", oldLines[i]));
                i += 1;
                j += 1;
                continue;
            }
            const removeScore = scores[(i + 1) * width + j];
            const addScore = scores[i * width + j + 1];
            if (removeScore >= addScore) {
                operations.push(createDiffOp("remove", oldLines[i]));
                i += 1;
            } else {
                operations.push(createDiffOp("add", newLines[j]));
                j += 1;
            }
        }

        while (i < oldLen) {
            operations.push(createDiffOp("remove", oldLines[i]));
            i += 1;
        }
        while (j < newLen) {
            operations.push(createDiffOp("add", newLines[j]));
            j += 1;
        }

        return operations;
    }

    function buildFallbackDiffOperations(oldLines, newLines) {
        const operations = [];
        let start = 0;
        let oldEnd = oldLines.length - 1;
        let newEnd = newLines.length - 1;

        while (
            start <= oldEnd &&
            start <= newEnd &&
            oldLines[start] === newLines[start]
        ) {
            operations.push(createDiffOp("context", oldLines[start]));
            start += 1;
        }

        const suffix = [];
        while (
            oldEnd >= start &&
            newEnd >= start &&
            oldLines[oldEnd] === newLines[newEnd]
        ) {
            suffix.push(createDiffOp("context", oldLines[oldEnd]));
            oldEnd -= 1;
            newEnd -= 1;
        }

        for (let index = start; index <= oldEnd; index += 1) {
            operations.push(createDiffOp("remove", oldLines[index]));
        }
        for (let index = start; index <= newEnd; index += 1) {
            operations.push(createDiffOp("add", newLines[index]));
        }
        while (suffix.length) {
            operations.push(suffix.pop());
        }

        return operations;
    }

    function computeLineDiffOperations(oldLines, newLines) {
        if (!oldLines.length && !newLines.length) {
            return { operations: [] };
        }
        if (!oldLines.length) {
            return {
                operations: newLines.map(function (line) {
                    return createDiffOp("add", line);
                }),
            };
        }
        if (!newLines.length) {
            return {
                operations: oldLines.map(function (line) {
                    return createDiffOp("remove", line);
                }),
            };
        }

        const cellCount = (oldLines.length + 1) * (newLines.length + 1);
        const needsFallback =
            cellCount > DIFF_LCS_CELL_LIMIT ||
            (oldLines.length + newLines.length) > DIFF_HARD_LINE_LIMIT;
        if (needsFallback) {
            return {
                operations: buildFallbackDiffOperations(oldLines, newLines),
                usedFallback: true,
            };
        }

        return { operations: buildLcsDiffOperations(oldLines, newLines) };
    }

    function annotateDiffRows(operations) {
        const rows = [];
        let oldLine = 1;
        let newLine = 1;
        let additions = 0;
        let deletions = 0;

        operations.forEach(function (op) {
            const type = normalizeDiffType(op.type);
            const row = {
                type: type,
                text: String(op.text || ""),
                oldLine: "",
                newLine: "",
                sign: " ",
            };

            if (type === "remove") {
                row.oldLine = oldLine;
                row.sign = "-";
                oldLine += 1;
                deletions += 1;
            } else if (type === "add") {
                row.newLine = newLine;
                row.sign = "+";
                newLine += 1;
                additions += 1;
            } else {
                row.oldLine = oldLine;
                row.newLine = newLine;
                oldLine += 1;
                newLine += 1;
            }

            rows.push(row);
        });

        return {
            rows: rows,
            additions: additions,
            deletions: deletions,
        };
    }

    function rowCssClassForType(type) {
        if (type === "add") {
            return "diff-line-add";
        }
        if (type === "remove") {
            return "diff-line-remove";
        }
        return "diff-line-context";
    }

    function buildUnifiedDiffText(pathValue, rows) {
        const path = String(pathValue || "file");
        const lines = [
            "--- a/" + path,
            "+++ b/" + path,
        ];
        rows.forEach(function (row) {
            lines.push(String(row.sign || " ") + String(row.text || ""));
        });
        return lines.join("\n");
    }

    function renderDiffRows(rows, truncated) {
        const rowHtml = rows.map(function (row) {
            const className = rowCssClassForType(row.type);
            const oldNum = row.oldLine === "" ? "" : String(row.oldLine);
            const newNum = row.newLine === "" ? "" : String(row.newLine);
            const safeText = row.text.length ? escapeHtml(row.text) : "&nbsp;";
            return [
                '<div class="diff-row ' + className + '">',
                '  <span class="diff-line-number">' + oldNum + "</span>",
                '  <span class="diff-line-number">' + newNum + "</span>",
                '  <span class="diff-line-sign">' + escapeHtml(row.sign || " ") + "</span>",
                '  <span class="diff-line-code">' + safeText + "</span>",
                "</div>",
            ].join("");
        }).join("");

        return [
            '<div class="diff-container">',
            '  <div class="diff-body">' + rowHtml + "</div>",
            truncated
                ? '  <div class="diff-truncated-note">Diff preview truncated for performance.</div>'
                : "",
            "</div>",
        ].join("");
    }

    function buildRenderedDiff(oldText, newText, pathValue) {
        const oldLines = splitLinesForDiff(oldText);
        const newLines = splitLinesForDiff(newText);
        const diffResult = computeLineDiffOperations(oldLines, newLines);
        const annotated = annotateDiffRows(diffResult.operations);
        const sourceRows = annotated.rows.length
            ? annotated.rows
            : [{
                type: "context",
                text: "(empty file)",
                oldLine: "",
                newLine: "",
                sign: " ",
            }];
        const totalLines = sourceRows.length;
        const truncated = totalLines > DIFF_RENDER_LINE_LIMIT;
        const visibleRows = truncated
            ? sourceRows.slice(0, DIFF_RENDER_LINE_LIMIT)
            : sourceRows;

        return {
            html: renderDiffRows(visibleRows, truncated),
            additions: annotated.additions,
            deletions: annotated.deletions,
            totalLines: totalLines,
            truncated: truncated || !!diffResult.usedFallback,
            unifiedText: buildUnifiedDiffText(pathValue, annotated.rows),
        };
    }

    function renderDiff(oldText, newText) {
        return buildRenderedDiff(oldText, newText, "").html;
    }

    function getToolDiffPayload(data) {
        const hasOld = data.old !== undefined || data.old_content !== undefined;
        const hasNew = data.new !== undefined || data.new_content !== undefined;
        const hasContent = data.content !== undefined;

        if (!hasOld && !hasNew && !hasContent) {
            return null;
        }

        let oldText = "";
        let newText = "";

        if (hasOld) {
            oldText = normalizeTextForDiff(
                data.old_content !== undefined ? data.old_content : data.old
            );
        }
        if (hasNew) {
            newText = normalizeTextForDiff(
                data.new_content !== undefined ? data.new_content : data.new
            );
        }
        if (!hasNew && hasContent) {
            newText = normalizeTextForDiff(data.content);
        }

        return {
            oldText: oldText,
            newText: newText,
            status: classifyDiffStatus(oldText, newText),
        };
    }

    function createDiffStatElement(additions, deletions) {
        const stat = document.createElement("span");
        stat.className = "diff-stat";
        stat.innerHTML = [
            '<span class="diff-stat-add">+' + Number(additions || 0) + "</span>",
            '<span class="diff-stat-remove">-' + Number(deletions || 0) + "</span>",
            "<span>lines</span>",
        ].join(" ");
        return stat;
    }

    function ensureToolSummaryCard() {
        if (!activeToolTurn || activeToolTurn.summaryRow) {
            return;
        }
        if (!activeToolTurn.firstToolRow || !activeToolTurn.firstToolRow.parentNode) {
            return;
        }

        const summaryRow = document.createElement("div");
        summaryRow.className = "message-row tool-summary";
        const inner = document.createElement("div");
        inner.className = "message-inner";
        const card = document.createElement("div");
        card.className = "tool-summary-card";

        const title = document.createElement("div");
        title.className = "tool-summary-title";
        card.appendChild(title);

        const files = document.createElement("div");
        files.className = "tool-summary-files";
        card.appendChild(files);

        const total = document.createElement("div");
        total.className = "diff-summary-total";
        card.appendChild(total);

        inner.appendChild(card);
        summaryRow.appendChild(inner);

        activeToolTurn.summaryRow = summaryRow;
        activeToolTurn.summaryTitleEl = title;
        activeToolTurn.summaryFilesEl = files;
        activeToolTurn.summaryTotalEl = total;

        messagesEl.insertBefore(summaryRow, activeToolTurn.firstToolRow);
    }

    function updateToolSummaryCard() {
        if (!activeToolTurn) {
            return;
        }

        const fileEntries = Object.keys(activeToolTurn.files).map(function (key) {
            return activeToolTurn.files[key];
        });

        if (activeToolTurn.toolCount < 2 || !fileEntries.length) {
            if (activeToolTurn.summaryRow) {
                activeToolTurn.summaryRow.remove();
                activeToolTurn.summaryRow = null;
                activeToolTurn.summaryTitleEl = null;
                activeToolTurn.summaryFilesEl = null;
                activeToolTurn.summaryTotalEl = null;
            }
            return;
        }

        ensureToolSummaryCard();
        if (!activeToolTurn.summaryFilesEl || !activeToolTurn.summaryTotalEl || !activeToolTurn.summaryTitleEl) {
            return;
        }

        fileEntries.sort(function (left, right) {
            return String(left.path || "").localeCompare(String(right.path || ""));
        });
        activeToolTurn.summaryTitleEl.textContent = fileEntries.length === 1
            ? "1 changed file in this turn"
            : fileEntries.length + " changed files in this turn";

        activeToolTurn.summaryFilesEl.innerHTML = "";
        fileEntries.forEach(function (entry) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "diff-summary-file file-status-" + entry.status;
            button.setAttribute("data-target-card", entry.cardId);

            const filePathEl = document.createElement("span");
            filePathEl.className = "diff-summary-filepath";
            filePathEl.textContent = String(entry.path || "(unknown)");
            button.appendChild(filePathEl);

            button.appendChild(createDiffStatElement(entry.additions, entry.deletions));
            activeToolTurn.summaryFilesEl.appendChild(button);
        });

        const summaryLabel = document.createElement("span");
        summaryLabel.textContent = "Total";
        const summaryStat = createDiffStatElement(
            activeToolTurn.totalAdditions,
            activeToolTurn.totalDeletions
        );
        activeToolTurn.summaryTotalEl.innerHTML = "";
        activeToolTurn.summaryTotalEl.appendChild(summaryLabel);
        activeToolTurn.summaryTotalEl.appendChild(summaryStat);
    }

    function trackToolEvent(summaryEntry, rowElement) {
        if (!activeToolTurn) {
            resetToolTurnState();
        }

        activeToolTurn.toolCount += 1;
        if (!activeToolTurn.firstToolRow && rowElement) {
            activeToolTurn.firstToolRow = rowElement;
        }

        if (summaryEntry && summaryEntry.path) {
            const key = String(summaryEntry.path);
            const additions = Number(summaryEntry.additions || 0);
            const deletions = Number(summaryEntry.deletions || 0);
            const status = String(summaryEntry.status || "modified");
            const cardId = String(summaryEntry.cardId || "");
            const existing = activeToolTurn.files[key];

            if (existing) {
                existing.additions += additions;
                existing.deletions += deletions;
                existing.status = mergeFileStatus(existing.status, status);
                if (!existing.cardId && cardId) {
                    existing.cardId = cardId;
                }
            } else {
                activeToolTurn.files[key] = {
                    path: key,
                    additions: additions,
                    deletions: deletions,
                    status: status,
                    cardId: cardId,
                };
            }

            activeToolTurn.totalAdditions += additions;
            activeToolTurn.totalDeletions += deletions;
        }

        updateToolSummaryCard();
    }

    function artifactIconForType(type) {
        if (type === "file") {
            return "📄";
        }
        if (type === "data") {
            return "🧱";
        }
        return "💻";
    }

    function artifactTypeLabel(type) {
        if (type === "file") {
            return "file";
        }
        if (type === "data") {
            return "data";
        }
        return "code";
    }

    function languageLabel(language) {
        const normalized = normalizeLanguage(language);
        return normalized || "plain text";
    }

    function formatArtifactTimestamp(timestamp) {
        const date = new Date(timestamp || Date.now());
        if (Number.isNaN(date.getTime())) {
            return "";
        }
        return date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    function artifactDisplayTitle(title, fallbackType, fallbackLanguage) {
        const rawTitle = String(title || "").trim();
        if (rawTitle) {
            return rawTitle;
        }
        artifactSnippetCounter += 1;
        const base = fallbackType === "data"
            ? "structured-data"
            : (normalizeLanguage(fallbackLanguage) || "code");
        return base + "-snippet-" + artifactSnippetCounter;
    }

    function artifactKeyFrom(type, title, language) {
        const normalizedType = String(type || "code").toLowerCase();
        const normalizedTitle = String(title || "").trim().toLowerCase();
        const normalizedLanguage = normalizeLanguage(language);
        if (normalizedType === "file" && normalizedTitle) {
            return "file:" + normalizedTitle;
        }
        if (normalizedType === "data" && normalizedTitle) {
            return "data:" + normalizedTitle;
        }
        return normalizedType + ":" + normalizedTitle + ":" + normalizedLanguage;
    }

    function findArtifactById(artifactId) {
        const id = String(artifactId || "");
        if (!id) {
            return null;
        }
        return artifacts.find(function (artifact) {
            return artifact.id === id;
        }) || null;
    }

    function getArtifactVersionEntry(artifact, versionNumber) {
        if (!artifact || !artifact.versions || !artifact.versions.length) {
            return null;
        }
        const preferred = Number(versionNumber || 0);
        if (preferred > 0) {
            const picked = artifact.versions.find(function (entry) {
                return entry.version === preferred;
            });
            if (picked) {
                return picked;
            }
        }
        return artifact.versions[artifact.versions.length - 1];
    }

    function setArtifactsPanelOpen(isOpen) {
        artifactsPanelOpen = !!isOpen;
        chatViewEl.classList.toggle("artifacts-open", artifactsPanelOpen);
        if (artifactsPanelEl) {
            artifactsPanelEl.setAttribute("aria-hidden", artifactsPanelOpen ? "false" : "true");
        }
        if (artifactsToggleBtnEl) {
            artifactsToggleBtnEl.classList.toggle("active", artifactsPanelOpen);
            artifactsToggleBtnEl.setAttribute("aria-expanded", artifactsPanelOpen ? "true" : "false");
        }
    }

    function setAgentModeEnabled(isEnabled) {
        agentModeEnabled = !!isEnabled;
        if (agentModeToggleButtons.length) {
            agentModeToggleButtons.forEach(function (button) {
                button.classList.toggle("active", agentModeEnabled);
                button.setAttribute("aria-pressed", agentModeEnabled ? "true" : "false");
                button.setAttribute("title", agentModeEnabled ? "Agent mode is enabled" : "Agent mode is disabled");
                button.setAttribute("aria-label", agentModeEnabled ? "Disable agent mode" : "Enable agent mode");
            });
        }
    }

    function toggleArtifactsPanel() {
        setArtifactsPanelOpen(!artifactsPanelOpen);
        if (artifactsPanelOpen && !selectedArtifactId && artifacts.length) {
            selectArtifact(artifacts[0].id, artifacts[0].version);
        }
    }

    function toggleAgentMode() {
        postToHost("toggleAgentMode", agentModeEnabled ? "off" : "on");
    }

    function updateArtifactsToggleButton() {
        if (!artifactsToggleBtnEl) {
            return;
        }
        const count = artifacts.length;
        artifactsToggleBtnEl.textContent = count > 0
            ? "📦 Artifacts (" + count + ")"
            : "📦 Artifacts";
    }

    function renderArtifactsList() {
        if (!artifactsListEl) {
            return;
        }

        artifactsListEl.innerHTML = "";
        if (!artifacts.length) {
            const emptyEl = document.createElement("div");
            emptyEl.className = "artifact-empty";
            emptyEl.textContent = "No artifacts yet.";
            artifactsListEl.appendChild(emptyEl);
            return;
        }

        artifacts.forEach(function (artifact) {
            const row = document.createElement("button");
            row.type = "button";
            row.className = "artifact-row";
            row.setAttribute("data-artifact-id", artifact.id);
            if (artifact.id === selectedArtifactId) {
                row.classList.add("selected");
            }

            const head = document.createElement("div");
            head.className = "artifact-row-head";

            const title = document.createElement("div");
            title.className = "artifact-row-title";
            title.textContent = artifactIconForType(artifact.type) + " " + artifact.title;
            head.appendChild(title);

            const versionBadge = document.createElement("span");
            versionBadge.className = "artifact-row-badge";
            versionBadge.textContent = "v" + artifact.version;
            head.appendChild(versionBadge);
            row.appendChild(head);

            const meta = document.createElement("div");
            meta.className = "artifact-row-meta";
            meta.textContent = artifactTypeLabel(artifact.type) + " • " + formatArtifactTimestamp(artifact.timestamp);
            row.appendChild(meta);

            row.addEventListener("click", function () {
                selectArtifact(artifact.id, artifact.version);
            });

            artifactsListEl.appendChild(row);
        });
    }

    function artifactLineDeltaSummary(currentText, previousText) {
        const currentLines = String(currentText || "").split("\n");
        const previousLines = String(previousText || "").split("\n");
        const maxLen = Math.max(currentLines.length, previousLines.length);
        let additions = 0;
        let deletions = 0;

        for (let index = 0; index < maxLen; index += 1) {
            const currentLine = currentLines[index];
            const previousLine = previousLines[index];
            if (currentLine === previousLine) {
                continue;
            }
            if (currentLine !== undefined) {
                additions += 1;
            }
            if (previousLine !== undefined) {
                deletions += 1;
            }
        }

        if (!additions && !deletions) {
            return "No changes";
        }
        return "+" + additions + " / -" + deletions + " lines";
    }

    function renderArtifactDetail() {
        const artifact = findArtifactById(selectedArtifactId);
        if (!artifact) {
            if (artifactDetailEmptyEl) {
                artifactDetailEmptyEl.classList.remove("artifact-hidden");
            }
            if (artifactDetailViewEl) {
                artifactDetailViewEl.classList.add("artifact-hidden");
            }
            return;
        }

        const versionEntry = getArtifactVersionEntry(artifact, selectedArtifactVersion);
        if (!versionEntry) {
            return;
        }

        selectedArtifactVersion = versionEntry.version;
        if (artifactDetailEmptyEl) {
            artifactDetailEmptyEl.classList.add("artifact-hidden");
        }
        if (artifactDetailViewEl) {
            artifactDetailViewEl.classList.remove("artifact-hidden");
        }
        if (artifactDetailTitleEl) {
            artifactDetailTitleEl.textContent = artifact.title;
        }
        if (artifactDetailTypeTagEl) {
            artifactDetailTypeTagEl.textContent = artifactTypeLabel(artifact.type);
        }
        if (artifactDetailLanguageTagEl) {
            artifactDetailLanguageTagEl.textContent = languageLabel(versionEntry.language || artifact.language);
        }
        if (artifactDetailVersionTagEl) {
            artifactDetailVersionTagEl.textContent = "v" + versionEntry.version;
        }

        if (artifactVersionSelectEl) {
            artifactVersionSelectEl.innerHTML = "";
            artifact.versions.slice().reverse().forEach(function (entry) {
                const option = document.createElement("option");
                option.value = String(entry.version);
                option.textContent = "v" + entry.version + " • " + formatArtifactTimestamp(entry.timestamp);
                if (entry.version === versionEntry.version) {
                    option.selected = true;
                }
                artifactVersionSelectEl.appendChild(option);
            });
        }

        const previousVersion = artifact.versions.find(function (entry) {
            return entry.version === versionEntry.version - 1;
        });
        if (artifactVersionDeltaEl) {
            artifactVersionDeltaEl.textContent = previousVersion
                ? artifactLineDeltaSummary(versionEntry.content, previousVersion.content)
                : "Initial version";
        }

        if (artifactDetailCodeEl) {
            artifactDetailCodeEl.className = versionEntry.language
                ? "hljs language-" + normalizeLanguage(versionEntry.language)
                : "hljs";
            artifactDetailCodeEl.innerHTML = highlightCode(versionEntry.content, versionEntry.language || artifact.language);
        }
    }

    function selectArtifact(artifactId, versionNumber) {
        selectedArtifactId = String(artifactId || "");
        selectedArtifactVersion = Number(versionNumber || 0);
        renderArtifactsList();
        renderArtifactDetail();
    }

    function suggestArtifactFilename(artifact, versionEntry) {
        const rawTitle = String((artifact && artifact.title) || "").trim() || "artifact";
        const baseName = rawTitle.split(/[\\/]/).pop() || "artifact";
        const hasExtension = /\.[a-z0-9]{1,12}$/i.test(baseName);
        const language = normalizeLanguage((versionEntry && versionEntry.language) || (artifact && artifact.language));

        if (hasExtension) {
            return baseName.replace(/[\\:*?"<>|]/g, "_");
        }
        if (language === "dockerfile") {
            return "Dockerfile";
        }
        const extension = LANGUAGE_EXTENSION_MAP[language] || ".txt";
        return (baseName + extension).replace(/[\\:*?"<>|]/g, "_");
    }

    function downloadArtifactContent() {
        const artifact = findArtifactById(selectedArtifactId);
        if (!artifact) {
            return;
        }
        const versionEntry = getArtifactVersionEntry(artifact, selectedArtifactVersion);
        if (!versionEntry) {
            return;
        }

        const blob = new Blob([String(versionEntry.content || "")], {
            type: "text/plain;charset=utf-8",
        });
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = suggestArtifactFilename(artifact, versionEntry);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(function () {
            URL.revokeObjectURL(blobUrl);
        }, 1000);
    }

    function openArtifactInNewTab() {
        const artifact = findArtifactById(selectedArtifactId);
        if (!artifact) {
            return;
        }
        const versionEntry = getArtifactVersionEntry(artifact, selectedArtifactVersion);
        if (!versionEntry) {
            return;
        }

        const blob = new Blob([String(versionEntry.content || "")], {
            type: "text/plain;charset=utf-8",
        });
        const blobUrl = URL.createObjectURL(blob);
        window.open(blobUrl, "_blank", "noopener,noreferrer");
        window.setTimeout(function () {
            URL.revokeObjectURL(blobUrl);
        }, 4000);
    }

    function registerArtifact(artifact) {
        const typeValue = String(artifact && artifact.type ? artifact.type : "code").toLowerCase();
        const type = typeValue === "file" || typeValue === "data" ? typeValue : "code";
        const content = String(artifact && artifact.content ? artifact.content : "");
        if (!content.trim()) {
            return null;
        }

        const language = normalizeLanguage((artifact && artifact.language) || "");
        const title = artifactDisplayTitle(artifact && artifact.title, type, language);
        const timestamp = String((artifact && artifact.timestamp) || new Date().toISOString());
        const key = String((artifact && artifact.key) || artifactKeyFrom(type, title, language)).trim();

        let record = key ? findArtifactById(artifactByKey[key]) : null;
        if (record) {
            const latest = record.versions[record.versions.length - 1];
            const nextLanguage = language || latest.language || record.language;
            const nextContent = content;
            if (latest.content !== nextContent || latest.language !== nextLanguage) {
                const nextVersion = latest.version + 1;
                record.versions.push({
                    version: nextVersion,
                    content: nextContent,
                    language: nextLanguage,
                    timestamp: timestamp,
                });
                record.version = nextVersion;
                record.content = nextContent;
                record.language = nextLanguage;
            }
            record.timestamp = timestamp;
            record.title = title;
            record.type = type;

            const index = artifacts.indexOf(record);
            if (index > 0) {
                artifacts.splice(index, 1);
                artifacts.unshift(record);
            }
        } else {
            artifactCounter += 1;
            const id = artifact && artifact.id ? String(artifact.id) : "artifact-" + artifactCounter;
            record = {
                id: id,
                type: type,
                title: title,
                language: language,
                content: content,
                timestamp: timestamp,
                version: 1,
                key: key,
                versions: [{
                    version: 1,
                    content: content,
                    language: language,
                    timestamp: timestamp,
                }],
            };
            artifacts.unshift(record);
            if (key) {
                artifactByKey[key] = id;
            }
        }

        updateArtifactsToggleButton();
        renderArtifactsList();
        if (selectedArtifactId === record.id) {
            selectedArtifactVersion = record.version;
            renderArtifactDetail();
        }
        return record;
    }

    function appendArtifactIndicator(anchorEl, artifact) {
        return;
    }

    function extractCodeFences(rawText) {
        const source = String(rawText || "").replace(/\r\n/g, "\n");
        const blocks = [];
        let match;
        const regex = /```([^\n`]*)\n?([\s\S]*?)```/g;

        while ((match = regex.exec(source)) !== null) {
            const info = parseFenceInfo(match[1]);
            blocks.push({
                info: info.info,
                lang: info.language,
                filename: info.filename,
                code: match[2] || "",
            });
        }
        return blocks;
    }

    function artifactFromCodeFence(block, index) {
        if (!block) {
            return null;
        }
        const rawCode = String(block.code || "");
        if (!rawCode.trim()) {
            return null;
        }
        const language = normalizeLanguage(block.lang || languageFromFilename(block.filename));
        const title = String(block.filename || "").trim();
        const content = rawCode.trim();
        const structured = isLikelyStructured(language, content);
        const detectedLanguage = language || detectStructuredLanguage(content);
        const type = title ? "file" : (structured ? "data" : "code");
        const fallbackTitle = type === "data"
            ? ((detectedLanguage || "data") + "-output")
            : ((detectedLanguage || "code") + "-snippet-" + (index + 1));
        return {
            type: type,
            title: title || fallbackTitle,
            language: detectedLanguage,
            content: content,
            key: title ? ("file:" + title.toLowerCase()) : "",
        };
    }

    function artifactFromStructuredText(rawText) {
        const trimmed = String(rawText || "").trim();
        if (trimmed.length < 220) {
            return null;
        }
        const language = detectStructuredLanguage(trimmed);
        if (!language) {
            return null;
        }
        return {
            type: "data",
            title: "structured-output." + (language === "yaml" ? "yaml" : language),
            language: language,
            content: trimmed,
            key: "data:structured-output",
        };
    }

    function registerAssistantArtifacts(messageBodyEl, rawText) {
        if (!messageBodyEl) {
            return;
        }

        const parsedBlocks = extractCodeFences(rawText);
        parsedBlocks.forEach(function (block, index) {
            const candidate = artifactFromCodeFence(block, index);
            if (!candidate) {
                return;
            }
            const artifact = registerArtifact(candidate);
            if (!artifact) {
                return;
            }
            const anchor = messageBodyEl.querySelector('.code-block[data-code-index="' + index + '"]');
            if (anchor) {
                appendArtifactIndicator(anchor, artifact);
            }
        });

        if (!parsedBlocks.length) {
            const structuredCandidate = artifactFromStructuredText(rawText);
            if (structuredCandidate) {
                const artifact = registerArtifact(structuredCandidate);
                if (artifact) {
                    appendArtifactIndicator(messageBodyEl, artifact);
                }
            }
        }
    }

    function registerToolArtifact(data, cardEl) {
        if (!data || !cardEl) {
            return;
        }
        const toolName = String(data.name || "").trim().toLowerCase();
        const filePath = String(data.path || "").trim();
        const modifiesFile = toolName === "write" || toolName === "edit" || toolName === "multiedit";
        if (!filePath && !modifiesFile) {
            return;
        }

        let content = "";
        if (data.new !== undefined && data.new !== null && String(data.new).trim()) {
            content = String(data.new);
        } else if (data.content !== undefined && data.content !== null && String(data.content).trim()) {
            content = String(data.content);
        } else if (data.command !== undefined && data.command !== null && String(data.command).trim()) {
            content = "$ " + String(data.command);
        } else if (data.old !== undefined && data.old !== null && String(data.old).trim()) {
            content = String(data.old);
        }

        if (!content.trim()) {
            return;
        }

        const language = normalizeLanguage(languageFromFilename(filePath) || detectStructuredLanguage(content));
        const title = filePath || (toolName + "-artifact");
        const artifact = registerArtifact({
            type: filePath ? "file" : "code",
            title: title,
            language: language,
            content: content,
            key: filePath ? ("file:" + filePath.toLowerCase()) : "",
        });
        if (artifact) {
            appendArtifactIndicator(cardEl, artifact);
        }
    }

    function resetArtifactsSession() {
        artifacts.length = 0;
        Object.keys(artifactByKey).forEach(function (key) {
            delete artifactByKey[key];
        });
        artifactCounter = 0;
        artifactSnippetCounter = 0;
        selectedArtifactId = "";
        selectedArtifactVersion = 0;
        setArtifactsPanelOpen(false);
        renderArtifactsList();
        renderArtifactDetail();
        updateArtifactsToggleButton();
    }

    const EMOJI_SHORTCODES = Object.freeze({
        ":+1:": "👍",
        ":-1:": "👎",
        ":100:": "💯",
        ":airplane:": "✈️",
        ":alarm_clock:": "⏰",
        ":alien:": "👽",
        ":apple:": "🍎",
        ":astonished:": "😲",
        ":balloon:": "🎈",
        ":banana:": "🍌",
        ":bang:": "❗",
        ":beer:": "🍺",
        ":bike:": "🚲",
        ":blush:": "😊",
        ":book:": "📖",
        ":bookmark:": "🔖",
        ":books:": "📚",
        ":boom:": "💥",
        ":broken_heart:": "💔",
        ":brown_heart:": "🤎",
        ":bug:": "🐛",
        ":bulb:": "💡",
        ":bus:": "🚌",
        ":car:": "🚗",
        ":chart_with_downwards_trend:": "📉",
        ":chart_with_upwards_trend:": "📈",
        ":check:": "✅",
        ":clap:": "👏",
        ":clipboard:": "📋",
        ":cloud:": "☁️",
        ":coffee:": "☕",
        ":collision:": "💥",
        ":computer:": "💻",
        ":confetti_ball:": "🎊",
        ":confused:": "😕",
        ":cowboy_hat_face:": "🤠",
        ":credit_card:": "💳",
        ":cross_mark:": "❌",
        ":cry:": "😢",
        ":desktop_computer:": "🖥️",
        ":disappointed:": "😞",
        ":dizzy_face:": "😵",
        ":dna:": "🧬",
        ":dollar:": "💵",
        ":droplet:": "💧",
        ":earth_americas:": "🌎",
        ":email:": "📧",
        ":envelope:": "✉️",
        ":exclamation:": "❗",
        ":exploding_head:": "🤯",
        ":expressionless:": "😑",
        ":eyes:": "👀",
        ":facepalm:": "🤦",
        ":file_folder:": "📁",
        ":fire:": "🔥",
        ":fist:": "✊",
        ":flushed:": "😳",
        ":frowning:": "☹️",
        ":gear:": "⚙️",
        ":gift:": "🎁",
        ":globe_with_meridians:": "🌐",
        ":grin:": "😁",
        ":grinning:": "😀",
        ":green_heart:": "💚",
        ":grey_exclamation:": "❕",
        ":grey_question:": "❔",
        ":hamburger:": "🍔",
        ":hammer:": "🔨",
        ":hear_no_evil:": "🙉",
        ":heart:": "❤️",
        ":heart_eyes:": "😍",
        ":heavy_check_mark:": "✔️",
        ":hourglass:": "⏳",
        ":idea:": "💡",
        ":information_source:": "ℹ️",
        ":innocent:": "😇",
        ":jigsaw:": "🧩",
        ":joy:": "😂",
        ":key:": "🔑",
        ":kissing:": "😗",
        ":kissing_heart:": "😘",
        ":laughing:": "😆",
        ":link:": "🔗",
        ":lock:": "🔒",
        ":mag:": "🔍",
        ":mag_right:": "🔎",
        ":map:": "🗺️",
        ":mask:": "😷",
        ":memo:": "📝",
        ":metal:": "🤘",
        ":microscope:": "🔬",
        ":mobile_phone:": "📱",
        ":moneybag:": "💰",
        ":muscle:": "💪",
        ":nerd_face:": "🤓",
        ":neutral_face:": "😐",
        ":ok_hand:": "👌",
        ":open_file_folder:": "📂",
        ":orange_heart:": "🧡",
        ":package:": "📦",
        ":paintbrush:": "🖌️",
        ":paperclip:": "📎",
        ":partly_sunny:": "⛅",
        ":partying_face:": "🥳",
        ":pencil2:": "✏️",
        ":persevere:": "😣",
        ":pizza:": "🍕",
        ":point_down:": "👇",
        ":point_left:": "👈",
        ":point_right:": "👉",
        ":point_up:": "☝️",
        ":pray:": "🙏",
        ":punch:": "👊",
        ":purple_heart:": "💜",
        ":pushpin:": "📌",
        ":question:": "❓",
        ":rage:": "😡",
        ":rainbow:": "🌈",
        ":raised_fist:": "✊",
        ":raised_hand:": "✋",
        ":relaxed:": "☺️",
        ":rofl:": "🤣",
        ":rocket:": "🚀",
        ":scream:": "😱",
        ":see_no_evil:": "🙈",
        ":shield:": "🛡️",
        ":shrug:": "🤷",
        ":skull:": "💀",
        ":sleeping:": "😴",
        ":sleepy:": "😪",
        ":slightly_smiling_face:": "🙂",
        ":smile:": "😄",
        ":smiley:": "😃",
        ":smirk:": "😏",
        ":snowflake:": "❄️",
        ":sob:": "😭",
        ":sparkles:": "✨",
        ":sparkling_heart:": "💖",
        ":speak_no_evil:": "🙊",
        ":star:": "⭐",
        ":star2:": "🌟",
        ":star_struck:": "🤩",
        ":stopwatch:": "⏱️",
        ":sunglasses:": "😎",
        ":sunny:": "☀️",
        ":sweat:": "😓",
        ":sweat_drops:": "💦",
        ":sweat_smile:": "😅",
        ":tada:": "🎉",
        ":telephone:": "☎️",
        ":test_tube:": "🧪",
        ":thinking:": "🤔",
        ":thumbsdown:": "👎",
        ":thumbsup:": "👍",
        ":train:": "🚆",
        ":triumph:": "😤",
        ":umbrella:": "☔",
        ":unamused:": "😒",
        ":unlock:": "🔓",
        ":upside_down_face:": "🙃",
        ":v:": "✌️",
        ":vulcan_salute:": "🖖",
        ":warning:": "⚠️",
        ":wave:": "👋",
        ":white_check_mark:": "✅",
        ":white_heart:": "🤍",
        ":wink:": "😉",
        ":wrench:": "🔧",
        ":writing_hand:": "✍️",
        ":x:": "❌",
        ":yellow_heart:": "💛",
        ":zap:": "⚡",
    });

    function emojiShortcodeToUnicode(text) {
        return String(text || "").replace(/:([a-z0-9_+\-]+):/gi, function (match, name) {
            const key = ":" + String(name || "").toLowerCase() + ":";
            return Object.prototype.hasOwnProperty.call(EMOJI_SHORTCODES, key)
                ? EMOJI_SHORTCODES[key]
                : match;
        });
    }

    function sanitizeImageUrl(url) {
        const trimmed = String(url || "").trim();
        if (!trimmed) {
            return "";
        }

        const lowered = trimmed.toLowerCase();
        if (lowered.startsWith("data:image/svg")) {
            return "";
        }
        if (
            lowered.startsWith("https://") ||
            lowered.startsWith("http://") ||
            lowered.startsWith("blob:") ||
            lowered.startsWith("data:image/")
        ) {
            return trimmed;
        }

        return "";
    }

    function applyEmojiOutsideCodeTags(html) {
        const preservedCode = [];
        let maskedHtml = String(html || "").replace(/<pre\b[^>]*>[\s\S]*?<\/pre>|<code\b[^>]*>[\s\S]*?<\/code>/gi, function (match) {
            const id = preservedCode.length;
            preservedCode.push(match);
            return "@@CODE_HTML_" + id + "@@";
        });

        maskedHtml = maskedHtml.split(/(<[^>]+>)/g).map(function (part) {
            if (!part || /^<[^>]+>$/.test(part)) {
                return part;
            }
            return emojiShortcodeToUnicode(part);
        }).join("");

        return maskedHtml.replace(/@@CODE_HTML_(\d+)@@/g, function (_, indexStr) {
            const index = Number(indexStr);
            return preservedCode[index] || "";
        });
    }

    function textWithEmojiShortcodes(text) {
        return emojiShortcodeToUnicode(String(text || ""));
    }

    function fallbackHighlightCode(code) {
        let html = escapeHtml(code);
        html = html.replace(/\b(const|let|var|function|class|return|if|else|for|while|import|from|export|try|catch|finally|def|async|await|switch|case|break)\b/g, '<span class="hljs-keyword">$1</span>');
        html = html.replace(/("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g, '<span class="hljs-string">$1</span>');
        html = html.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="hljs-number">$1</span>');
        html = html.replace(/\b(true|false|null|None)\b/g, '<span class="hljs-literal">$1</span>');
        html = html.replace(/(#.*$|\/\/.*$)/gm, '<span class="hljs-comment">$1</span>');
        return html;
    }

    function highlightCode(code, lang) {
        const rawCode = String(code || "");
        const requestedLang = String(lang || "").trim().toLowerCase();

        if (window.hljs && typeof window.hljs.highlight === "function") {
            try {
                if (
                    requestedLang &&
                    typeof window.hljs.getLanguage === "function" &&
                    window.hljs.getLanguage(requestedLang)
                ) {
                    return window.hljs.highlight(rawCode, {
                        language: requestedLang,
                        ignoreIllegals: true,
                    }).value;
                }
                if (typeof window.hljs.highlightAuto === "function") {
                    return window.hljs.highlightAuto(rawCode).value;
                }
            } catch (_error) {}
        }

        return fallbackHighlightCode(rawCode);
    }

    function applyInlineMarkdown(text) {
        let out = String(text || "");
        out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        out = out.replace(/(^|[\s(])(https?:\/\/[^\s<]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>');
        out = out.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
        out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        out = out.replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, "$1<em>$2</em>");
        return out;
    }

    function renderList(listBlock, ordered) {
        const lines = listBlock.trim().split("\n").filter(Boolean);
        const tag = ordered ? "ol" : "ul";
        const items = lines.map(function (line) {
            const cleaned = ordered ? line.replace(/^\d+\.\s+/, "") : line.replace(/^[-*]\s+/, "");
            return "<li>" + applyInlineMarkdown(cleaned.trim()) + "</li>";
        }).join("");
        return "<" + tag + ">" + items + "</" + tag + ">";
    }

    function isTableBlock(part) {
        const lines = String(part || "").trim().split("\n").map(function (line) {
            return line.trim();
        }).filter(Boolean);
        if (lines.length < 2) {
            return false;
        }
        if (lines[0].indexOf("|") === -1) {
            return false;
        }
        const separator = lines[1].replace(/\|/g, "").trim();
        return /^:?-{3,}:?(?:\s+:?-{3,}:?)*$/.test(separator);
    }

    function renderTable(part) {
        const lines = String(part || "").trim().split("\n").map(function (line) {
            let next = line.trim();
            if (next.startsWith("|")) {
                next = next.slice(1);
            }
            if (next.endsWith("|")) {
                next = next.slice(0, -1);
            }
            return next;
        }).filter(Boolean);

        if (lines.length < 2) {
            return "<p>" + applyInlineMarkdown(part) + "</p>";
        }

        const headCells = lines[0].split("|").map(function (cell) {
            return "<th>" + applyInlineMarkdown(cell.trim()) + "</th>";
        }).join("");

        const bodyRows = lines.slice(2).map(function (line) {
            const cols = line.split("|").map(function (cell) {
                return "<td>" + applyInlineMarkdown(cell.trim()) + "</td>";
            }).join("");
            return "<tr>" + cols + "</tr>";
        }).join("");

        return "<table><thead><tr>" + headCells + "</tr></thead><tbody>" + bodyRows + "</tbody></table>";
    }

    function markdownToHtml(input) {
        let source = String(input || "").replace(/\r\n/g, "\n");
        const codeBlocks = [];

        source = source.replace(/```([^\n`]*)\n?([\s\S]*?)```/g, function (_, info, code) {
            const id = codeBlocks.length;
            const parsedInfo = parseFenceInfo(info);
            codeBlocks.push({
                info: parsedInfo.info,
                lang: parsedInfo.language,
                filename: parsedInfo.filename,
                code: code || "",
            });
            return "@@CODEBLOCK_" + id + "@@";
        });

        source = escapeHtml(source);
        source = source.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, function (_, alt, url) {
            const src = sanitizeImageUrl(url);
            if (!src) {
                return "";
            }
            const safeSrc = escapeHtml(src);
            const safeAlt = escapeHtml(alt);
            return '<img src="' + safeSrc + '" alt="' + safeAlt + '" class="chat-image" loading="lazy">';
        });

        source = source.replace(/^###\s+(.+)$/gm, function (_, text) {
            return "<h3>" + applyInlineMarkdown(text.trim()) + "</h3>";
        });
        source = source.replace(/^##\s+(.+)$/gm, function (_, text) {
            return "<h2>" + applyInlineMarkdown(text.trim()) + "</h2>";
        });
        source = source.replace(/^#\s+(.+)$/gm, function (_, text) {
            return "<h1>" + applyInlineMarkdown(text.trim()) + "</h1>";
        });

        source = source.replace(/^>\s?(.+)$/gm, function (_, text) {
            return "<blockquote>" + applyInlineMarkdown(text.trim()) + "</blockquote>";
        });
        source = source.replace(/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/gm, "<hr>");

        source = source.replace(/(?:^|\n)((?:[-*]\s+.*(?:\n|$))+)/g, function (_, block) {
            return "\n" + renderList(block, false) + "\n";
        });
        source = source.replace(/(?:^|\n)((?:\d+\.\s+.*(?:\n|$))+)/g, function (_, block) {
            return "\n" + renderList(block, true) + "\n";
        });

        const parts = source.split(/\n{2,}/);
        const rendered = [];

        for (const rawPart of parts) {
            const part = rawPart.trim();
            if (!part) {
                continue;
            }

            if (/^<(h1|h2|h3|ul|ol|blockquote|hr)/.test(part) || /^@@CODEBLOCK_\d+@@$/.test(part)) {
                rendered.push(part);
                continue;
            }

            if (isTableBlock(part)) {
                rendered.push(renderTable(part));
                continue;
            }

            rendered.push("<p>" + applyInlineMarkdown(part.replace(/\n/g, "<br>")) + "</p>");
        }

        let html = rendered.join("");

        html = html.replace(/@@CODEBLOCK_(\d+)@@/g, function (_, indexStr) {
            const index = Number(indexStr);
            const block = codeBlocks[index] || { lang: "", filename: "", code: "" };
            const code = String(block.code || "");
            const highlighted = highlightCode(code, block.lang);
            const rawEncoded = encodeURIComponent(code);
            const lang = normalizeLanguage(block.lang || "");
            const filename = String(block.filename || "").trim();
            const title = filename || lang || "code";
            const titleEncoded = encodeURIComponent(title);
            const langEncoded = encodeURIComponent(lang);
            const fileEncoded = encodeURIComponent(filename);
            const label = escapeHtml(
                filename && lang
                    ? (filename + " • " + lang)
                    : title
            );
            const codeClass = block.lang ? "hljs language-" + escapeHtml(block.lang) : "hljs";
            return [
                '<div class="code-block" data-code-index="' + index + '" data-code-title="' + titleEncoded + '" data-code-lang="' + langEncoded + '" data-code-filename="' + fileEncoded + '">',
                '  <div class="code-head">',
                "    <span>" + label + "</span>",
                '    <button class="action-btn code-copy-btn copy-action" data-raw="' + rawEncoded + '">Copy</button>',
                "  </div>",
                '  <pre><code class="' + codeClass + '">' + highlighted + '</code></pre>',
                "</div>",
            ].join("");
        });

        html = applyEmojiOutsideCodeTags(html);

        return html || "<p></p>";
    }

    function postToHost(handlerName, payload, aliases) {
        const handlerNames = [handlerName];
        if (Array.isArray(aliases)) {
            aliases.forEach(function (entry) {
                const alias = String(entry || "").trim();
                if (!alias || handlerNames.indexOf(alias) !== -1) {
                    return;
                }
                handlerNames.push(alias);
            });
        }
        if (!(window.webkit && window.webkit.messageHandlers)) {
            return false;
        }
        for (let index = 0; index < handlerNames.length; index += 1) {
            const candidate = handlerNames[index];
            const handler = window.webkit.messageHandlers[candidate];
            if (!handler) {
                continue;
            }
            try {
                handler.postMessage(payload);
                return true;
            } catch (_error) {
                continue;
            }
        }
        return false;
    }

    function parseHostPayload(rawValue) {
        if (typeof rawValue === "string") {
            try {
                return JSON.parse(rawValue);
            } catch (_error) {
                return null;
            }
        }
        return rawValue;
    }

    function toModelOptions(rawValue) {
        const payload = parseHostPayload(rawValue);
        if (!Array.isArray(payload)) {
            return [];
        }
        return payload.map(function (entry, index) {
            if (Array.isArray(entry)) {
                const title = String(entry[0] || "Model " + (index + 1));
                const value = String(entry[1] || "").trim();
                return {
                    value: value,
                    short: title.split("(")[0].trim() || title,
                    title: title,
                    description: "Model option",
                };
            }
            const title = String(entry && entry.title ? entry.title : "Model " + (index + 1));
            const value = String(entry && entry.value ? entry.value : "").trim();
            const short = String(entry && entry.short ? entry.short : title.split("(")[0].trim() || title);
            const description = String(entry && entry.description ? entry.description : "Model option");
            return {
                value: value,
                short: short,
                title: title,
                description: description,
            };
        }).filter(function (option) {
            return option.value.length > 0;
        });
    }

    function toPermissionOptions(rawValue) {
        const payload = parseHostPayload(rawValue);
        if (!Array.isArray(payload)) {
            return [];
        }
        return payload.map(function (entry, index) {
            if (Array.isArray(entry)) {
                return {
                    value: String(entry[1] || "").trim(),
                    title: String(entry[0] || "Permission " + (index + 1)),
                    description: "Permission option",
                };
            }
            return {
                value: String(entry && entry.value ? entry.value : "").trim(),
                title: String(entry && entry.title ? entry.title : "Permission " + (index + 1)),
                description: String(entry && entry.description ? entry.description : "Permission option"),
            };
        }).filter(function (option) {
            return option.value.length > 0;
        });
    }

    function toReasoningOptions(rawValue) {
        const payload = parseHostPayload(rawValue);
        if (!Array.isArray(payload)) {
            return [];
        }
        return payload.map(function (entry, index) {
            if (Array.isArray(entry)) {
                return {
                    value: String(entry[1] || "").trim(),
                    title: String(entry[0] || "Reasoning " + (index + 1)),
                    description: String(entry[2] || "Reasoning option"),
                };
            }
            return {
                value: String(entry && entry.value ? entry.value : "").trim(),
                title: String(entry && entry.title ? entry.title : "Reasoning " + (index + 1)),
                description: String(entry && entry.description ? entry.description : "Reasoning option"),
            };
        }).filter(function (option) {
            return option.value.length > 0;
        });
    }

    function normalizeModelValue(rawValue) {
        const value = String(rawValue || "").trim();
        const valid = MODEL_OPTIONS.some(function (option) {
            return option.value === value;
        });
        if (valid) {
            return value;
        }
        return MODEL_OPTIONS.length > 0 ? MODEL_OPTIONS[0].value : "";
    }

    function normalizePermissionValue(rawValue) {
        const value = String(rawValue || "").trim();
        const valid = PERMISSION_OPTIONS.some(function (option) {
            return option.value === value;
        });
        if (valid) {
            return value;
        }
        return PERMISSION_OPTIONS.length > 0 ? PERMISSION_OPTIONS[0].value : "";
    }

    function normalizeReasoningValue(rawValue) {
        const value = String(rawValue || "").trim();
        const valid = REASONING_OPTIONS.some(function (option) {
            return option.value === value;
        });
        if (valid) {
            return value;
        }
        return REASONING_OPTIONS.length > 0 ? REASONING_OPTIONS[0].value : "";
    }

    function findModelMeta(value) {
        const model = MODEL_OPTIONS.find(function (option) {
            return option.value === value;
        });
        return model || MODEL_OPTIONS[0];
    }

    function findPermissionMeta(value) {
        const permission = PERMISSION_OPTIONS.find(function (option) {
            return option.value === value;
        });
        return permission || PERMISSION_OPTIONS[0];
    }

    function findReasoningMeta(value) {
        if (!REASONING_OPTIONS.length) {
            return {
                value: "medium",
                title: "Medium",
                description: "Balanced reasoning.",
            };
        }
        var reasoning = REASONING_OPTIONS.find(function (option) {
            return option.value === value;
        });
        return reasoning || REASONING_OPTIONS[0];
    }

    function renderSelectorLabels() {
        if (MODEL_OPTIONS.length === 0) {
            return;
        }
        const modelLabel = findModelMeta(selectedModel).short;
        modelButtons.forEach(function (button) {
            const labelEl = button.querySelector(".model-label");
            if (labelEl) {
                labelEl.textContent = modelLabel;
            }
        });

        if (!reasoningVisible) {
            return;
        }
        const reasoningLabel = findReasoningMeta(selectedReasoning).title;
        reasoningButtons.forEach(function (button) {
            const labelEl = button.querySelector(".reasoning-label");
            if (labelEl) {
                labelEl.textContent = reasoningLabel;
            }
        });
    }

    function setReasoningVisible(isVisible) {
        reasoningVisible = !!isVisible;
        reasoningButtons.forEach(function (button) {
            const wrapper = button.closest(".selector-group");
            if (wrapper) {
                wrapper.style.display = reasoningVisible ? "" : "none";
            }
            button.disabled = !reasoningVisible;
        });
        reasoningPopups.forEach(function (popup) {
            closePopup(popup, true);
        });
    }

    function closePopup(popup, immediate) {
        if (!popup) {
            return;
        }

        const triggerButton = popup.parentElement ? popup.parentElement.querySelector("button") : null;
        if (triggerButton) {
            triggerButton.setAttribute("aria-expanded", "false");
        }

        if (immediate) {
            popup.classList.remove("open", "closing");
            if (activePopup === popup) {
                activePopup = null;
            }
            return;
        }

        popup.classList.remove("open");
        popup.classList.add("closing");
        window.setTimeout(function () {
            popup.classList.remove("closing");
            if (activePopup === popup) {
                activePopup = null;
            }
        }, 160);
    }

    function closeActivePopup(immediate) {
        if (!activePopup) {
            return;
        }
        const popup = activePopup;
        closePopup(popup, immediate);
    }

    function buildPopupOption(option, isActive) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "popup-option" + (isActive ? " active" : "");

        const title = document.createElement("span");
        title.className = "popup-title";
        title.textContent = option.title;
        button.appendChild(title);

        const subtitle = document.createElement("span");
        subtitle.className = "popup-subtitle";
        subtitle.textContent = option.description;
        button.appendChild(subtitle);

        return button;
    }

    function renderModelPopup(popup) {
        popup.innerHTML = "";
        MODEL_OPTIONS.forEach(function (option) {
            const button = buildPopupOption(option, option.value === selectedModel);
            button.addEventListener("click", function () {
                selectedModel = option.value;
                renderSelectorLabels();
                postToHost("changeModel", selectedModel);
                closePopup(popup, false);
            });
            popup.appendChild(button);
        });
    }

    function renderPermissionPopup(popup) {
        popup.innerHTML = "";
        PERMISSION_OPTIONS.forEach(function (option) {
            const button = buildPopupOption(option, option.value === selectedPermission);
            button.addEventListener("click", function () {
                selectedPermission = option.value;
                postToHost("changePermission", selectedPermission);
                closePopup(popup, false);
            });
            popup.appendChild(button);
        });
    }

    function renderReasoningPopup(popup) {
        popup.innerHTML = "";
        REASONING_OPTIONS.forEach(function (option) {
            var button = buildPopupOption(option, option.value === selectedReasoning);
            button.addEventListener("click", function () {
                selectedReasoning = option.value;
                renderSelectorLabels();
                postToHost("changeReasoning", selectedReasoning);
                closePopup(popup, false);
            });
            popup.appendChild(button);
        });
    }

    function openPopup(triggerButton, popup, type) {
        closeActivePopup(true);

        if (type === "model") {
            renderModelPopup(popup);
        } else if (type === "reasoning") {
            if (!reasoningVisible) {
                return;
            }
            renderReasoningPopup(popup);
        } else {
            renderPermissionPopup(popup);
        }

        triggerButton.setAttribute("aria-expanded", "true");
        popup.classList.remove("closing");
        popup.classList.add("open");
        activePopup = popup;
    }

    function isAgentPaneMode() {
        return paneMode === "agent";
    }

    function setPaneMode(nextMode) {
        const normalized = String(nextMode || "").trim().toLowerCase();
        paneMode = normalized === "agent" ? "agent" : "main";
        if (appEl) {
            appEl.classList.toggle("pane-mode-agent", isAgentPaneMode());
        }
        if (isAgentPaneMode()) {
            setArtifactsPanelOpen(false);
        }
        setChatState(hasMessages);
    }

    function setChatState(withMessages) {
        hasMessages = !!withMessages;

        if (isAgentPaneMode()) {
            welcomeViewEl.style.display = "none";
            chatViewEl.classList.add("active");
            appEl.classList.add("chat-state");
            userScrolledUp = false;
            updateScrollButtonVisibility();
            setTimeout(function () { chatInputEl.focus(); }, 50);
            return;
        }

        if (hasMessages) {
            welcomeViewEl.style.display = "none";
            chatViewEl.classList.add("active");
            appEl.classList.add("chat-state");
            window.requestAnimationFrame(updateUserScrolledState);
            setTimeout(function () { chatInputEl.focus(); }, 50);
            return;
        }

        welcomeViewEl.style.display = "flex";
        chatViewEl.classList.remove("active");
        appEl.classList.remove("chat-state");
        closeChatSearch({ focusInput: false });
        userScrolledUp = false;
        updateScrollButtonVisibility();
        setTimeout(function () { welcomeInputEl.focus(); }, 50);
    }

    function setAssistantPhase(nextPhase) {
        const normalizedPhase = Object.values(ASSISTANT_PHASE).indexOf(nextPhase) >= 0
            ? nextPhase
            : ASSISTANT_PHASE.IDLE;
        assistantPhase = normalizedPhase;
        const showStopButton =
            assistantPhase === ASSISTANT_PHASE.SENDING
            || assistantPhase === ASSISTANT_PHASE.WAITING_FIRST_TOKEN
            || assistantPhase === ASSISTANT_PHASE.STREAMING;
        if (stopProcessSlotEl) {
            stopProcessSlotEl.classList.toggle("is-visible", showStopButton);
        }
        if (stopBtnEl) {
            stopBtnEl.classList.toggle("is-visible", showStopButton);
        }
    }

    function normalizeWaitStatusText(value) {
        return String(value == null ? "" : value).replace(/\s+/g, " ").trim();
    }

    function truncateWaitStatusText(value, maxLength) {
        const raw = String(value || "");
        if (!maxLength || raw.length <= maxLength) {
            return raw;
        }
        return raw.slice(0, Math.max(0, maxLength - 1)).trimEnd() + "\u2026";
    }

    function sanitizeWaitStatusText(value, maxLength) {
        const normalized = normalizeWaitStatusText(value);
        const truncated = truncateWaitStatusText(normalized, maxLength || 0);
        return escapeHtml(truncated);
    }

    function waitStatusBasename(pathValue) {
        const raw = String(pathValue || "").trim();
        if (!raw) {
            return "";
        }
        const clean = raw.replace(/[?#].*$/, "");
        const parts = clean.split(/[\\/]/);
        return parts[parts.length - 1] || clean;
    }

    function getCurrentWaitStatusElement() {
        const candidates = [thinkingIndicatorRow, typingRow];
        for (let index = 0; index < candidates.length; index += 1) {
            const row = candidates[index];
            if (!row || !row.isConnected) {
                continue;
            }
            const el = row.querySelector(".wait-status-text");
            if (el) {
                return el;
            }
        }
        return null;
    }

    function stopWaitRotateTimer() {
        if (waitRotateTimer) {
            window.clearInterval(waitRotateTimer);
            waitRotateTimer = null;
        }
    }

    function stopWaitInactivityTimer() {
        if (waitInactivityTimer) {
            window.clearTimeout(waitInactivityTimer);
            waitInactivityTimer = null;
        }
    }

    function stopWaitStatusPendingTimer() {
        if (waitStatusPendingTimer) {
            window.clearTimeout(waitStatusPendingTimer);
            waitStatusPendingTimer = null;
        }
    }

    function stopWaitStatusTransitionTimer() {
        if (waitStatusTransitionTimer) {
            window.clearTimeout(waitStatusTransitionTimer);
            waitStatusTransitionTimer = null;
        }
    }

    function renderWaitStatus(immediate) {
        const statusEl = getCurrentWaitStatusElement();
        if (!statusEl) {
            return;
        }

        stopWaitStatusTransitionTimer();

        const applyTextAndVisibility = function () {
            if (!statusEl.isConnected) {
                return;
            }
            statusEl.innerHTML = waitStatusVisible
                ? sanitizeWaitStatusText(waitStatusText, 180)
                : "";
            statusEl.setAttribute("data-wait-status", waitStatusText);
            statusEl.classList.toggle("visible", waitStatusVisible && !!waitStatusText);
        };

        const currentText = statusEl.getAttribute("data-wait-status") || "";
        if (immediate || !currentText || !statusEl.classList.contains("visible") || currentText === waitStatusText || !waitStatusVisible) {
            applyTextAndVisibility();
            return;
        }

        statusEl.classList.remove("visible");
        waitStatusTransitionTimer = window.setTimeout(function () {
            applyTextAndVisibility();
        }, WAIT_STATUS_FADE_MS);
    }

    function clearLongWaitStatusInternal(options) {
        const opts = options || {};
        waitStatusVisible = false;
        waitStatusText = "";
        waitStatusSource = "";
        waitStatusPendingText = "";
        stopWaitRotateTimer();
        stopWaitStatusPendingTimer();
        renderWaitStatus(!!opts.immediate);
    }

    function applyLongWaitStatus(text, options) {
        const opts = options || {};
        const normalized = normalizeWaitStatusText(text);
        const immediate = !!opts.immediate;
        const force = !!opts.force;
        const source = String(opts.source || "").trim();
        if (!normalized) {
            clearLongWaitStatusInternal({ immediate: immediate });
            return;
        }

        if (normalized === waitStatusText && waitStatusVisible) {
            waitStatusSource = source || waitStatusSource;
            renderWaitStatus(immediate);
            return;
        }

        const now = Date.now();
        const elapsed = now - waitStatusLastChangeTs;
        if (!force && waitStatusLastChangeTs && elapsed < WAIT_STATUS_MIN_INTERVAL_MS) {
            waitStatusPendingText = normalized;
            stopWaitStatusPendingTimer();
            waitStatusPendingTimer = window.setTimeout(function () {
                const pendingText = waitStatusPendingText;
                waitStatusPendingText = "";
                applyLongWaitStatus(pendingText, {
                    immediate: false,
                    force: true,
                    source: source,
                });
            }, WAIT_STATUS_MIN_INTERVAL_MS - elapsed);
            return;
        }

        stopWaitStatusPendingTimer();
        waitStatusText = normalized;
        waitStatusVisible = true;
        waitStatusLastChangeTs = now;
        waitStatusSource = source;
        renderWaitStatus(immediate);
    }

    function startFallbackRotation() {
        if (!processingActive || waitStatusText) {
            return;
        }
        stopWaitRotateTimer();
        waitFallbackIndex = waitFallbackIndex % WAIT_FALLBACK_MESSAGES.length;
        applyLongWaitStatus(WAIT_FALLBACK_MESSAGES[waitFallbackIndex], {
            immediate: false,
            source: "fallback",
        });
        waitFallbackIndex = (waitFallbackIndex + 1) % WAIT_FALLBACK_MESSAGES.length;
        waitRotateTimer = window.setInterval(function () {
            if (!processingActive || waitStatusSource !== "fallback") {
                stopWaitRotateTimer();
                return;
            }
            applyLongWaitStatus(WAIT_FALLBACK_MESSAGES[waitFallbackIndex], {
                immediate: false,
                source: "fallback",
            });
            waitFallbackIndex = (waitFallbackIndex + 1) % WAIT_FALLBACK_MESSAGES.length;
        }, WAIT_ROTATE_MS);
    }

    function scheduleWaitInactivityTimer() {
        stopWaitInactivityTimer();
        if (!processingActive) {
            return;
        }
        waitInactivityTimer = window.setTimeout(function () {
            waitInactivityTimer = null;
            if (!processingActive) {
                return;
            }
            const elapsed = Date.now() - lastActivityTs;
            if (elapsed < WAIT_INACTIVITY_MS) {
                scheduleWaitInactivityTimer();
                return;
            }
            if (waitStatusText) {
                return;
            }
            startFallbackRotation();
        }, WAIT_INACTIVITY_MS);
    }

    function noteWaitActivity() {
        lastActivityTs = Date.now();
    }

    function resetLongWaitStatusTimers() {
        noteWaitActivity();
        stopWaitRotateTimer();
        scheduleWaitInactivityTimer();
    }

    function deriveWaitStatusFromTool(data) {
        if (!data || typeof data !== "object") {
            return "";
        }
        const rawName = String(data.name || "tool").trim() || "tool";
        const toolName = rawName.toLowerCase();
        const phase = String(data.phase || "").trim().toLowerCase();
        const output = normalizeWaitStatusText(data.output || "");
        const toolUseId = String(data.toolUseId || data.id || "").trim();
        const isToolResult = (
            toolName === "tool_result"
            || phase === "completed"
            || (toolUseId && !!seenToolUseIds[toolUseId] && !!output)
        );
        if (isToolResult) {
            return "Processing results...";
        }

        const command = normalizeWaitStatusText(data.command || "");
        if (command) {
            return "Running: " + truncateWaitStatusText(command, WAIT_STATUS_MAX_COMMAND_LENGTH);
        }

        const path = normalizeWaitStatusText(data.path || data.file_path || "");
        if (path) {
            const fileName = waitStatusBasename(path);
            const safeName = truncateWaitStatusText(fileName, 80);
            if (toolName === "read" || toolName === "grep" || toolName === "glob") {
                return "Reading " + safeName;
            }
            if (toolName === "edit" || toolName === "write" || toolName === "multiedit") {
                return "Editing " + safeName;
            }
        }

        return "Using " + rawName;
    }

    function updateLongWaitStatusFromTool(data) {
        const nextText = deriveWaitStatusFromTool(data);
        if (!nextText) {
            return;
        }
        noteWaitActivity();
        stopWaitRotateTimer();
        scheduleWaitInactivityTimer();
        applyLongWaitStatus(nextText, {
            immediate: false,
            source: "tool",
        });
    }

    function clearLongWaitStatusAndTimers(immediate) {
        stopWaitInactivityTimer();
        stopWaitRotateTimer();
        stopWaitStatusPendingTimer();
        clearLongWaitStatusInternal({ immediate: !!immediate });
    }

    function createThinkingShellElement() {
        const shell = document.createElement("div");
        shell.className = "thinking-shell";

        const indicator = document.createElement("div");
        indicator.className = "thinking-indicator";
        indicator.innerHTML = "<span></span><span></span><span></span>";
        shell.appendChild(indicator);

        const waitStatusEl = document.createElement("div");
        waitStatusEl.className = "wait-status-text";
        shell.appendChild(waitStatusEl);

        return shell;
    }

    function isImageAttachment(payload) {
        const attachmentType = String(payload && payload.type || "").trim().toLowerCase();
        const data = String(payload && payload.data || "");
        if (attachmentType.indexOf("image/") === 0 || data.indexOf("data:image/") === 0) {
            return true;
        }

        const path = String(payload && payload.path || "").trim().toLowerCase().replace(/\\\\/g, "/");
        const fileName = String(payload && payload.name || "").trim().toLowerCase();
        const fullName = (fileName || path).split("/").pop();
        const extension = (fullName || "").split(".").pop();
        return {
            png: true,
            jpg: true,
            jpeg: true,
            gif: true,
            webp: true,
            svg: true,
            bmp: true,
            avif: true,
            heic: true,
        }[extension] === true;
    }

    function normalizeAttachment(payload) {
        if (!payload || typeof payload !== "object") {
            return null;
        }

        const rawPath = String(payload.path || "").trim();
        const normalizedPath = rawPath.replace(/\\/g, "/");
        const type = String(payload.type || "application/octet-stream").trim() || "application/octet-stream";
        let name = String(payload.name || "").trim();
        if (!name && normalizedPath) {
            const pathParts = normalizedPath.split("/").filter(function (segment) {
                return segment.length > 0;
            });
            name = pathParts.length ? pathParts[pathParts.length - 1] : "";
        }
        if (!name) {
            const extension = type.split("/")[1] || "bin";
            name = "attachment." + extension.replace(/[^a-z0-9.+_-]/gi, "");
        }
        const data = String(payload.data || "").trim();
        if (!data) {
            return null;
        }
        attachmentCounter += 1;
        return {
            id: "att-" + attachmentCounter,
            name: name,
            type: type,
            data: data,
            path: normalizedPath,
        };
    }

    function cloneAttachmentList(listValue) {
        return (Array.isArray(listValue) ? listValue : []).map(function (item) {
            return {
                name: String(item.name || "attachment"),
                type: String(item.type || "application/octet-stream"),
                data: String(item.data || ""),
                path: String(item.path || "").trim(),
            };
        }).filter(function (item) {
            return item.data.length > 0;
        });
    }

    function renderAttachmentStrip(container) {
        if (!container) {
            return;
        }

        container.innerHTML = "";
        container.classList.toggle("has-items", attachments.length > 0);
        if (!attachments.length) {
            return;
        }

        attachments.forEach(function (attachment) {
            const isImage = isImageAttachment(attachment);
            const chip = document.createElement("div");
            chip.className = isImage
                ? "attachment-chip attachment-chip-image"
                : "attachment-chip";

            const preview = document.createElement("div");
            preview.className = "attachment-preview";
            if (isImage) {
                const thumb = document.createElement("img");
                thumb.className = "attachment-thumb";
                thumb.src = attachment.data;
                thumb.alt = attachment.name;
                thumb.addEventListener("click", function () {
                    openImageLightbox(attachment.data, attachment.name);
                });
                preview.appendChild(thumb);
            } else {
                const marker = document.createElement("span");
                marker.className = "attachment-file-marker";
                marker.textContent = "📄";
                preview.appendChild(marker);
            }
            chip.appendChild(preview);

            const meta = document.createElement("div");
            meta.className = "attachment-meta";

            const name = document.createElement("span");
            name.className = "attachment-name";
            name.textContent = attachment.name;
            meta.appendChild(name);

            const attachmentPath = String(attachment.path || "").trim();
            if (attachmentPath && !isImage) {
                const path = document.createElement("span");
                path.className = "attachment-path";
                path.textContent = compactDisplayPath(attachmentPath, 44);
                path.setAttribute("title", attachmentPath);
                meta.appendChild(path);
                chip.setAttribute("title", attachmentPath);
            } else {
                chip.setAttribute("title", attachment.name);
            }
            chip.appendChild(meta);

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = isImage
                ? "attachment-remove attachment-remove-image"
                : "attachment-remove";
            removeButton.setAttribute("aria-label", "Remove attachment");
            removeButton.textContent = "×";
            removeButton.addEventListener("click", function () {
                attachments = attachments.filter(function (item) {
                    return item.id !== attachment.id;
                });
                renderAttachments();
            });
            if (isImage) {
                preview.appendChild(removeButton);
            } else {
                chip.appendChild(removeButton);
            }

            container.appendChild(chip);
        });
    }

    function renderAttachments() {
        renderAttachmentStrip(welcomeAttachmentsEl);
        renderAttachmentStrip(chatAttachmentsEl);
    }

    function addAttachment(payload) {
        const normalized = normalizeAttachment(payload);
        if (!normalized) {
            return;
        }
        attachments.push(normalized);
        renderAttachments();
    }

    function clearAttachments() {
        attachments = [];
        renderAttachments();
    }

    function fileToAttachment(file) {
        return new Promise(function (resolve, reject) {
            if (!file) {
                reject(new Error("No file"));
                return;
            }
            const reader = new FileReader();
            reader.onerror = function () {
                reject(new Error("Could not read file"));
            };
            reader.onload = function () {
                const mimeType = file.type || "application/octet-stream";
                let name = String(file.name || "").trim();
                if (!name) {
                    const extension = (mimeType.split("/")[1] || "bin").replace(/[^a-z0-9.+_-]/gi, "");
                    name = "pasted-image-" + Date.now() + "." + extension;
                }
                resolve({
                    name: name,
                    type: mimeType,
                    data: String(reader.result || ""),
                });
            };
            reader.readAsDataURL(file);
        });
    }

    function addFilesFromList(fileList) {
        const files = Array.from(fileList || []);
        if (!files.length) {
            return;
        }
        Promise.all(files.map(fileToAttachment)).then(function (newAttachments) {
            newAttachments.forEach(addAttachment);
        }).catch(function () {});
    }

    function extractClipboardImageFiles(clipboardData) {
        const files = [];
        const seen = new Set();

        function remember(file) {
            if (!file || !file.type || file.type.indexOf("image/") !== 0) {
                return;
            }
            const key = [
                String(file.name || ""),
                String(file.type || ""),
                String(file.size || 0),
                String(file.lastModified || 0),
            ].join("|");
            if (seen.has(key)) {
                return;
            }
            seen.add(key);
            files.push(file);
        }

        if (clipboardData && clipboardData.items) {
            Array.from(clipboardData.items).forEach(function (item) {
                if (!item || !item.type || item.type.indexOf("image/") !== 0) {
                    return;
                }
                remember(item.getAsFile());
            });
        }
        if (clipboardData && clipboardData.files) {
            Array.from(clipboardData.files).forEach(function (file) {
                remember(file);
            });
        }
        return files;
    }

    function autoResizeInput(inputEl) {
        if (!inputEl) {
            return;
        }
        inputEl.style.height = "auto";
        inputEl.style.height = Math.min(inputEl.scrollHeight, 220) + "px";
    }

    function clearInputs() {
        welcomeInputEl.value = "";
        chatInputEl.value = "";
        autoResizeInput(welcomeInputEl);
        autoResizeInput(chatInputEl);
    }

    function activeInput() {
        if (isAgentPaneMode()) {
            return chatInputEl;
        }
        return hasMessages ? chatInputEl : welcomeInputEl;
    }

    function setComposerPromptValue(value) {
        const text = String(value || "");
        const inputEl = activeInput();
        if (!inputEl) {
            return;
        }
        inputEl.value = text;
        autoResizeInput(inputEl);
        inputEl.focus();
    }

    function getExamplePromptsForProvider(providerId) {
        const normalized = String(providerId || "").trim().toLowerCase();
        return EXAMPLE_PROMPTS_BY_PROVIDER[normalized] || EXAMPLE_PROMPTS_BY_PROVIDER.claude;
    }

    function renderExamplePrompts() {
        if (!welcomeExamplePromptsEl) {
            return;
        }
        const prompts = getExamplePromptsForProvider(activeProviderId);
        welcomeExamplePromptsEl.innerHTML = "";
        prompts.forEach(function (promptText) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "example-prompt";
            button.textContent = promptText;
            button.setAttribute("role", "listitem");
            button.title = "Insert this prompt";
            button.addEventListener("click", function () {
                setComposerPromptValue(promptText);
            });
            welcomeExamplePromptsEl.appendChild(button);
        });
        if (examplePromptsTitleEl) {
            examplePromptsTitleEl.textContent = "Example prompts for " + activeProviderName;
        }
    }

    function sendPayload(payload) {
        const text = String(payload && payload.text ? payload.text : "").trim();
        const outgoingAttachments = cloneAttachmentList(payload ? payload.attachments : []);
        if (!text && !outgoingAttachments.length) {
            return;
        }

        if (text) {
            lastUserPrompt = text;
        }

        const outgoing = {
            text: text,
            attachments: outgoingAttachments,
        };
        lastUserPayload = outgoing;
        setChatState(true);
        setAssistantPhase(ASSISTANT_PHASE.SENDING);
        addUserMessage(outgoing.text, outgoing.attachments);
        postToHost("sendMessage", JSON.stringify(outgoing));
        clearInputs();
        clearAttachments();
        chatInputEl.focus();
    }

    function sendInput(inputEl) {
        sendPayload({
            text: String(inputEl.value || "").trim(),
            attachments: attachments,
        });
    }

    function distanceFromBottom() {
        return messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight;
    }

    function updateScrollButtonVisibility() {
        if (!scrollToBottomBtnEl) {
            return;
        }
        scrollToBottomBtnEl.classList.toggle("visible", hasMessages && userScrolledUp);
    }

    function updateUserScrolledState() {
        userScrolledUp = distanceFromBottom() > 80;
        updateScrollButtonVisibility();
    }

    function scrollToBottom(force, smooth) {
        const nearBottom = distanceFromBottom() < 150;
        if (force || nearBottom) {
            if (smooth && messagesEl.scrollTo) {
                messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: "smooth" });
            } else {
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }
            if (smooth) {
                userScrolledUp = false;
            }
        }
        updateScrollButtonVisibility();
    }

    function clearChatSearchHighlights() {
        if (!messagesEl) {
            return;
        }
        const highlights = Array.from(messagesEl.querySelectorAll("mark.search-highlight"));
        highlights.forEach(function (markEl) {
            const parent = markEl.parentNode;
            if (!parent) {
                return;
            }
            parent.replaceChild(document.createTextNode(markEl.textContent || ""), markEl);
            if (typeof parent.normalize === "function") {
                parent.normalize();
            }
        });
        chatSearchMatches = [];
        chatSearchCurrentIndex = -1;
    }

    function updateChatSearchCounter(limitReached) {
        const total = chatSearchMatches.length;
        const current = total > 0 && chatSearchCurrentIndex >= 0 ? (chatSearchCurrentIndex + 1) : 0;
        if (chatSearchCurrentEl) {
            chatSearchCurrentEl.textContent = String(current);
        }
        if (chatSearchTotalEl) {
            chatSearchTotalEl.textContent = String(total);
        }
        if (chatSearchLimitNoteEl) {
            chatSearchLimitNoteEl.textContent = limitReached ? "... showing first 500" : "";
        }
        if (chatSearchBarEl) {
            const hasQuery = chatSearchInputEl && String(chatSearchInputEl.value || "").trim().length > 0;
            chatSearchBarEl.classList.toggle("no-results", hasQuery && total === 0);
        }
    }

    function setCurrentChatSearchMatch(nextIndex, shouldScroll) {
        if (!chatSearchMatches.length) {
            chatSearchCurrentIndex = -1;
            updateChatSearchCounter(false);
            return;
        }

        if (chatSearchCurrentIndex >= 0 && chatSearchCurrentIndex < chatSearchMatches.length) {
            chatSearchMatches[chatSearchCurrentIndex].classList.remove("current-match");
        }

        const normalizedIndex = ((nextIndex % chatSearchMatches.length) + chatSearchMatches.length) % chatSearchMatches.length;
        chatSearchCurrentIndex = normalizedIndex;
        const currentMatch = chatSearchMatches[chatSearchCurrentIndex];
        currentMatch.classList.add("current-match");
        if (shouldScroll) {
            currentMatch.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
        }
        updateChatSearchCounter(false);
    }

    function escapeRegExp(value) {
        return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function buildChatSearchHighlights(query) {
        const matches = [];
        let limitReached = false;
        const escapedQuery = escapeRegExp(query);
        if (!escapedQuery) {
            return { matches: matches, limitReached: false };
        }

        const matcher = new RegExp(escapedQuery, "giu");
        const messageRows = Array.from(messagesEl.querySelectorAll(".message-row"));
        let stop = false;

        messageRows.some(function (row) {
            const walker = document.createTreeWalker(
                row,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function (node) {
                        if (!node || !node.nodeValue || !node.nodeValue.trim()) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        const parent = node.parentElement;
                        if (!parent) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        const tag = parent.tagName;
                        if (
                            tag === "SCRIPT"
                            || tag === "STYLE"
                            || tag === "TEXTAREA"
                            || tag === "INPUT"
                            || tag === "SELECT"
                            || tag === "OPTION"
                            || tag === "BUTTON"
                            || tag === "MARK"
                        ) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        return NodeFilter.FILTER_ACCEPT;
                    },
                }
            );
            const textNodes = [];
            let node = walker.nextNode();
            while (node) {
                textNodes.push(node);
                node = walker.nextNode();
            }

            textNodes.forEach(function (textNode) {
                if (stop) {
                    return;
                }
                const textValue = textNode.nodeValue || "";
                matcher.lastIndex = 0;
                let match = matcher.exec(textValue);
                if (!match) {
                    return;
                }

                let lastIndex = 0;
                const fragment = document.createDocumentFragment();

                while (match) {
                    if (matches.length >= CHAT_SEARCH_MAX_MATCHES) {
                        limitReached = true;
                        stop = true;
                        break;
                    }
                    const start = match.index;
                    const matchedValue = match[0];
                    if (start > lastIndex) {
                        fragment.appendChild(document.createTextNode(textValue.slice(lastIndex, start)));
                    }
                    const mark = document.createElement("mark");
                    mark.className = "search-highlight";
                    mark.textContent = matchedValue;
                    fragment.appendChild(mark);
                    matches.push(mark);
                    lastIndex = start + matchedValue.length;
                    match = matcher.exec(textValue);
                }

                if (lastIndex < textValue.length) {
                    fragment.appendChild(document.createTextNode(textValue.slice(lastIndex)));
                }

                if (textNode.parentNode) {
                    textNode.parentNode.replaceChild(fragment, textNode);
                }
            });

            return stop;
        });

        return { matches: matches, limitReached: limitReached };
    }

    function runChatSearch(queryValue) {
        const query = String(queryValue || "").trim();
        if (!query) {
            closeChatSearch();
            return;
        }
        clearChatSearchHighlights();
        const result = buildChatSearchHighlights(query);
        chatSearchMatches = result.matches;
        if (chatSearchMatches.length) {
            setCurrentChatSearchMatch(0, true);
        } else {
            chatSearchCurrentIndex = -1;
        }
        updateChatSearchCounter(result.limitReached);
    }

    function scheduleChatSearch() {
        if (!chatSearchInputEl) {
            return;
        }
        if (chatSearchDebounceId) {
            window.clearTimeout(chatSearchDebounceId);
        }
        chatSearchDebounceId = window.setTimeout(function () {
            chatSearchDebounceId = null;
            runChatSearch(chatSearchInputEl.value);
        }, CHAT_SEARCH_DEBOUNCE_MS);
    }

    function refreshChatSearchIfActive() {
        if (!chatSearchOpen || !chatSearchInputEl) {
            return;
        }
        const query = String(chatSearchInputEl.value || "").trim();
        if (!query) {
            return;
        }
        runChatSearch(query);
    }

    function focusPrimaryInput() {
        if (hasMessages || isAgentPaneMode()) {
            chatInputEl.focus();
        } else {
            welcomeInputEl.focus();
        }
    }

    function openChatSearch() {
        if (!chatSearchBarEl || !chatSearchInputEl || !hasMessages) {
            return;
        }
        chatSearchOpen = true;
        chatSearchBarEl.style.display = "flex";
        chatSearchInputEl.focus();
        chatSearchInputEl.select();
        const query = String(chatSearchInputEl.value || "").trim();
        if (query) {
            scheduleChatSearch();
            return;
        }
        clearChatSearchHighlights();
        updateChatSearchCounter(false);
    }

    function closeChatSearch(options) {
        const config = options && typeof options === "object" ? options : {};
        const shouldFocusInput = config.focusInput !== false;
        chatSearchOpen = false;
        if (chatSearchDebounceId) {
            window.clearTimeout(chatSearchDebounceId);
            chatSearchDebounceId = null;
        }
        if (chatSearchInputEl) {
            chatSearchInputEl.value = "";
        }
        if (chatSearchBarEl) {
            chatSearchBarEl.style.display = "none";
            chatSearchBarEl.classList.remove("no-results");
        }
        clearChatSearchHighlights();
        updateChatSearchCounter(false);
        if (shouldFocusInput) {
            focusPrimaryInput();
        }
    }

    function toggleChatSearch() {
        if (chatSearchOpen) {
            closeChatSearch();
            return;
        }
        openChatSearch();
    }

    function goToNextChatSearchMatch() {
        if (!chatSearchMatches.length) {
            return;
        }
        setCurrentChatSearchMatch(chatSearchCurrentIndex + 1, true);
    }

    function goToPreviousChatSearchMatch() {
        if (!chatSearchMatches.length) {
            return;
        }
        setCurrentChatSearchMatch(chatSearchCurrentIndex - 1, true);
    }

    function openImageLightbox(src, alt) {
        if (!imageLightboxEl || !lightboxImageEl) {
            return;
        }
        const imageSrc = sanitizeImageUrl(src);
        if (!imageSrc) {
            return;
        }
        lightboxImageEl.src = imageSrc;
        lightboxImageEl.alt = String(alt || "Chat image");
        imageLightboxEl.classList.add("open");
        imageLightboxEl.setAttribute("aria-hidden", "false");
    }

    function closeImageLightbox() {
        if (!imageLightboxEl || !lightboxImageEl) {
            return;
        }
        imageLightboxEl.classList.remove("open");
        imageLightboxEl.setAttribute("aria-hidden", "true");
        lightboxImageEl.removeAttribute("src");
        lightboxImageEl.alt = "";
    }

    function createMessageRow(kind) {
        const row = document.createElement("div");
        row.className = "message-row " + kind;

        const inner = document.createElement("div");
        inner.className = "message-inner";
        row.appendChild(inner);

        if (thinkingIndicatorRow && thinkingIndicatorRow.isConnected && thinkingIndicatorRow.parentNode === messagesEl) {
            messagesEl.insertBefore(row, thinkingIndicatorRow);
        } else {
            messagesEl.appendChild(row);
        }
        if (chatSearchOpen) {
            window.setTimeout(function () {
                refreshChatSearchIfActive();
            }, 0);
        }

        return { row: row, inner: inner };
    }

    function addUserMessage(text, attachmentList) {
        setChatState(true);
        resetToolTurnState();

        const rowObj = createMessageRow("user");
        const bubbleWrap = document.createElement("div");
        bubbleWrap.className = "user-bubble-wrap";
        const bubble = document.createElement("div");
        bubble.className = "user-bubble";
        const safeText = String(text || "");
        const outgoingAttachments = cloneAttachmentList(attachmentList);
        bubble.dataset.rawMarkdown = safeText;

        if (outgoingAttachments.length) {
            const gallery = document.createElement("div");
            gallery.className = "message-attachments";
            outgoingAttachments.forEach(function (attachment) {
                if (isImageAttachment(attachment) && attachment.data) {
                    const image = document.createElement("img");
                    image.className = "message-attachment-image";
                    image.src = attachment.data;
                    image.alt = attachment.name || "Image attachment";
                    gallery.appendChild(image);
                    return;
                }
                const chip = document.createElement("div");
                chip.className = "message-attachment-file";
                chip.textContent = "📎 " + (attachment.name || "attachment");
                gallery.appendChild(chip);
            });
            bubble.appendChild(gallery);
        }

        if (safeText) {
            const textBlock = document.createElement("div");
            textBlock.className = "user-bubble-text";
            textBlock.textContent = textWithEmojiShortcodes(safeText);
            bubble.appendChild(textBlock);
        }

        const badge = document.createElement("div");
        badge.className = "copy-success-badge";
        badge.textContent = "Copied!";

        const actions = document.createElement("div");
        actions.className = "user-actions";
        actions.innerHTML = [
            '<button class="assistant-action user-action" data-action="copy" type="button" title="Copy">📋</button>',
            '<button class="assistant-action user-action copy-md-action" data-action="copy-md" type="button" title="Copy as Markdown">📋 MD</button>',
        ].join("");

        bubbleWrap.appendChild(bubble);
        bubbleWrap.appendChild(actions);
        bubbleWrap.appendChild(badge);
        rowObj.inner.appendChild(bubbleWrap);
        scrollToBottom(true);
    }

    function addAssistantMessage(text) {
        const raw = String(text || "");
        if (!raw) {
            return;
        }

        setChatState(true);
        resetToolTurnState();

        const rowObj = createMessageRow("assistant");
        const block = document.createElement("div");
        block.className = "assistant-block";

        const wrap = document.createElement("div");
        wrap.className = "assistant-content-wrap";

        const body = document.createElement("div");
        body.className = "assistant-message markdown-body";
        body.dataset.raw = raw;
        body.dataset.rawMarkdown = raw;
        body.innerHTML = markdownToHtml(raw);
        registerAssistantArtifacts(body, raw);

        const badge = document.createElement("div");
        badge.className = "copy-success-badge";
        badge.textContent = "Copied!";

        const actions = document.createElement("div");
        actions.className = "assistant-actions";
        actions.innerHTML = [
            '<button class="assistant-action" data-action="copy" type="button" title="Copy">📋</button>',
            '<button class="assistant-action copy-md-action" data-action="copy-md" type="button" title="Copy as Markdown">📋 MD</button>',
            '<button class="assistant-action" data-action="up" type="button" title="Thumbs up">👍</button>',
            '<button class="assistant-action" data-action="down" type="button" title="Thumbs down">👎</button>',
            '<button class="assistant-action" data-action="retry" type="button" title="Retry">🔄</button>',
        ].join("");

        wrap.appendChild(body);
        wrap.appendChild(actions);
        wrap.appendChild(badge);
        block.appendChild(wrap);
        rowObj.inner.appendChild(block);

        if (!userScrolledUp) {
            scrollToBottom(true);
        }
    }

    function toTitleCase(value) {
        const raw = String(value || "").trim();
        if (!raw) {
            return "";
        }
        return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
    }

    function statusClassName(statusValue) {
        const value = String(statusValue || "").trim().toLowerCase();
        if (value === "merged" || value === "closed" || value === "open" || value === "pending" || value === "passing" || value === "failing") {
            return value;
        }
        return "open";
    }

    function ciStatusIcon(statusValue) {
        const status = statusClassName(statusValue);
        if (status === "passing") {
            return "✓";
        }
        if (status === "failing") {
            return "✕";
        }
        return "◌";
    }

    function appendMetaLine(container, label, value) {
        const text = String(value || "").trim();
        if (!text) {
            return;
        }
        const line = document.createElement("div");
        line.className = "cipr-meta";
        line.innerHTML = '<span class="cipr-meta-label"></span><span class="cipr-meta-value"></span>';
        const labelEl = line.querySelector(".cipr-meta-label");
        const valueEl = line.querySelector(".cipr-meta-value");
        if (labelEl) {
            labelEl.textContent = String(label || "");
        }
        if (valueEl) {
            valueEl.textContent = text;
        }
        container.appendChild(line);
    }

    function deriveCiprFallback(data) {
        const command = String(data && data.command ? data.command : "");
        const output = String(data && data.output ? data.output : "");
        const lowerCommand = command.toLowerCase();
        const lowerOutput = output.toLowerCase();
        const events = {};

        if (/\bgit\s+commit\b/.test(lowerCommand)) {
            events.git = {
                operation: "commit",
                hash: (output.match(/\b([0-9a-f]{7,40})\b/i) || [])[1] || "",
                message: (output.match(/\[[^\]]+\]\s+(.+)/) || [])[1] || "",
                filesChanged: Number((output.match(/(\d+)\s+files?\s+changed/i) || [])[1] || 0),
            };
        } else if (/\bgit\s+push\b/.test(lowerCommand)) {
            events.git = {
                operation: "push",
                branch: (command.match(/\bgit\s+push(?:\s+-[^\s]+|\s+--[^\s]+)*\s+[^\s]+\s+([^\s]+)/i) || [])[1] || "",
                remote: (command.match(/\bgit\s+push(?:\s+-[^\s]+|\s+--[^\s]+)*\s+([^\s]+)/i) || [])[1] || "origin",
            };
        } else if (/\bgit\s+(?:checkout\s+-b|switch\s+-c|branch)\b/.test(lowerCommand)) {
            events.git = {
                operation: "branch",
                branch: (command.match(/\bgit\s+(?:checkout\s+-b|switch\s+-c|branch)\s+([^\s]+)/i) || [])[1] || "",
            };
        }

        const prUrlMatch = output.match(/https?:\/\/[^\s)]+\/pull\/\d+/i) || command.match(/https?:\/\/[^\s)]+\/pull\/\d+/i);
        if (/\bgh\s+pr\s+create\b/.test(lowerCommand) || prUrlMatch) {
            const prUrl = prUrlMatch ? prUrlMatch[0] : "";
            const number = (prUrl.match(/\/pull\/(\d+)/i) || [])[1] || "";
            events.pr = {
                title: number ? ("PR #" + number) : "Pull Request",
                number: number,
                url: prUrl,
                status: lowerOutput.indexOf("merged") >= 0 ? "merged" : (lowerOutput.indexOf("closed") >= 0 ? "closed" : "open"),
                sourceBranch: events.git && events.git.operation === "push" ? String(events.git.branch || "") : "",
            };
        }

        const ciCommandSignal = (
            /\bgh\s+pr\s+checks\b/.test(lowerCommand)
            || /\bgh\s+run\b/.test(lowerCommand)
            || /\bgh\s+workflow\b/.test(lowerCommand)
            || /\bbuildkite\b/.test(lowerCommand)
            || /\bjenkins\b/.test(lowerCommand)
            || /\bcircleci\b/.test(lowerCommand)
        );
        const ciUrl = (
            output.match(/https?:\/\/[^\s)]+(?:actions\/runs\/\d+|runs\/\d+|pipelines\/[^\s)]+)/i)
            || command.match(/https?:\/\/[^\s)]+(?:actions\/runs\/\d+|runs\/\d+|pipelines\/[^\s)]+)/i)
            || []
        )[0] || "";
        const ciOutputSignal = (
            /\bgithub actions\b/i.test(output)
            || /\bbuildkite\b/i.test(output)
            || /\bjenkins\b/i.test(output)
            || /\bcircleci\b/i.test(output)
            || /\bgh\s+pr\s+checks\b/i.test(output)
            || /\bgh\s+run\b/i.test(output)
            || /\bgh\s+workflow\b/i.test(output)
            || /\bcheck suite\b/i.test(output)
            || /\bworkflow\s+(?:run|id|name)\b/i.test(output)
            || /\bpipeline\s+(?:id|name|url)\b/i.test(output)
        );

        if (ciCommandSignal || !!ciUrl || ciOutputSignal) {
            let status = "";
            if (/\b(fail|failed|failing|error)\b/i.test(output)) {
                status = "failing";
            } else if (/\b(pass|passed|success|successful)\b/i.test(output)) {
                status = "passing";
            } else if (/\b(pending|queued|in progress|running)\b/i.test(output)) {
                status = "pending";
            } else if (ciCommandSignal) {
                status = "pending";
            }

            if (status) {
                events.ci = {
                    status: status,
                    url: ciUrl,
                    prUrl: events.pr && events.pr.url ? events.pr.url : "",
                    suggestFix: status === "failing",
                };
            }
        }

        return events;
    }

    function addGitCard(data) {
        if (!data || typeof data !== "object") {
            return;
        }
        const operation = String(data.operation || "").trim().toLowerCase();
        if (!operation) {
            return;
        }

        const rowObj = createMessageRow("tool git");
        const card = document.createElement("div");
        card.className = "git-card";

        const head = document.createElement("div");
        head.className = "cipr-head";
        const title = document.createElement("div");
        title.className = "cipr-title";
        title.textContent = "⑂ Git " + toTitleCase(operation);
        head.appendChild(title);
        card.appendChild(head);

        if (operation === "commit") {
            appendMetaLine(card, "Hash", data.hash || "");
            appendMetaLine(card, "Message", data.message || "");
            if (data.filesChanged !== undefined && data.filesChanged !== null && String(data.filesChanged) !== "") {
                appendMetaLine(card, "Files", String(data.filesChanged));
            }
        } else if (operation === "push") {
            appendMetaLine(card, "Branch", data.branch || "");
            appendMetaLine(card, "Remote", data.remote || "origin");
            if (data.commitCount !== undefined && data.commitCount !== null && String(data.commitCount) !== "") {
                appendMetaLine(card, "Commits", String(data.commitCount));
            }
        } else if (operation === "branch") {
            appendMetaLine(card, "Branch", data.branch || "");
            appendMetaLine(card, "Created from", data.createdFrom || "");
        }

        rowObj.inner.appendChild(card);
        scrollToBottom(true);
    }

    function updatePRCardView(refs, data) {
        if (!refs || !refs.card) {
            return;
        }
        const statusValue = statusClassName(data.status || "open");
        const titleText = String(data.title || "").trim() || "Pull Request";
        const numberText = String(data.number || "").trim();
        refs.titleEl.textContent = numberText ? (titleText + " #" + numberText) : titleText;
        refs.statusEl.className = "cipr-badge " + statusValue;
        refs.statusEl.textContent = toTitleCase(statusValue);

        const sourceBranch = String(data.sourceBranch || "").trim();
        const targetBranch = String(data.targetBranch || "").trim();
        refs.branchEl.textContent = sourceBranch || targetBranch
            ? ("Branch: " + (sourceBranch || "?") + " \u2192 " + (targetBranch || "?"))
            : "";
        refs.branchEl.style.display = refs.branchEl.textContent ? "block" : "none";

        refs.fileSummaryEl.textContent = String(data.fileSummary || "").trim();
        refs.fileSummaryEl.style.display = refs.fileSummaryEl.textContent ? "block" : "none";

        const url = String(data.url || "").trim();
        if (/^https?:\/\//i.test(url)) {
            refs.linkEl.href = url;
            refs.linkEl.textContent = url;
            refs.linkWrap.style.display = "block";
            lastPRUrl = url;
        } else {
            refs.linkWrap.style.display = "none";
        }
    }

    function addPRCard(data) {
        if (!data || typeof data !== "object") {
            return;
        }
        const key = String(data.url || data.number || data.title || "").trim().toLowerCase();
        if (!key) {
            return;
        }

        let refs = prCardByKey[key];
        if (!refs) {
            const rowObj = createMessageRow("tool pr");
            const card = document.createElement("div");
            card.className = "pr-card";

            const head = document.createElement("div");
            head.className = "cipr-head";

            const title = document.createElement("div");
            title.className = "cipr-title";
            head.appendChild(title);

            const status = document.createElement("span");
            status.className = "cipr-badge open";
            status.textContent = "Open";
            head.appendChild(status);

            card.appendChild(head);

            const linkWrap = document.createElement("div");
            linkWrap.className = "cipr-meta";
            linkWrap.innerHTML = '<span class="cipr-meta-label">PR</span>';
            const linkEl = document.createElement("a");
            linkEl.className = "cipr-link";
            linkEl.target = "_blank";
            linkEl.rel = "noopener noreferrer";
            linkWrap.appendChild(linkEl);
            card.appendChild(linkWrap);

            const branchEl = document.createElement("div");
            branchEl.className = "cipr-meta";
            card.appendChild(branchEl);

            const fileSummaryEl = document.createElement("div");
            fileSummaryEl.className = "cipr-meta";
            card.appendChild(fileSummaryEl);

            const ciSlot = document.createElement("div");
            ciSlot.className = "pr-ci-slot";
            card.appendChild(ciSlot);

            rowObj.inner.appendChild(card);

            refs = {
                card: card,
                titleEl: title,
                statusEl: status,
                linkWrap: linkWrap,
                linkEl: linkEl,
                branchEl: branchEl,
                fileSummaryEl: fileSummaryEl,
                ciSlot: ciSlot,
            };
            prCardByKey[key] = refs;
        }

        updatePRCardView(refs, data);

        const urlKey = String(data.url || "").trim();
        if (urlKey) {
            prCardByUrl[urlKey] = refs;
            lastPRUrl = urlKey;
        }

        scrollToBottom(true);
    }

    function upsertCIStatusCard(container, key) {
        const existing = ciCardByKey[key];
        if (existing) {
            return existing;
        }

        let hostContainer = container;
        if (!hostContainer) {
            const rowObj = createMessageRow("tool ci");
            hostContainer = rowObj.inner;
        }

        const card = document.createElement("div");
        card.className = "ci-status-card";

        const head = document.createElement("div");
        head.className = "cipr-head";
        card.appendChild(head);

        const indicator = document.createElement("div");
        indicator.className = "ci-indicator pending";
        const icon = document.createElement("span");
        icon.className = "ci-icon";
        icon.textContent = ciStatusIcon("pending");
        const title = document.createElement("span");
        title.className = "cipr-title";
        title.textContent = "CI Pending";
        indicator.appendChild(icon);
        indicator.appendChild(title);
        head.appendChild(indicator);

        const linkWrap = document.createElement("div");
        linkWrap.className = "cipr-meta";
        const linkLabel = document.createElement("span");
        linkLabel.className = "cipr-meta-label";
        linkLabel.textContent = "Run";
        const linkEl = document.createElement("a");
        linkEl.className = "cipr-link";
        linkEl.target = "_blank";
        linkEl.rel = "noopener noreferrer";
        linkWrap.appendChild(linkLabel);
        linkWrap.appendChild(linkEl);
        card.appendChild(linkWrap);

        const pipelineEl = document.createElement("div");
        pipelineEl.className = "cipr-meta";
        card.appendChild(pipelineEl);

        const durationEl = document.createElement("div");
        durationEl.className = "cipr-meta";
        card.appendChild(durationEl);

        const fixButton = document.createElement("button");
        fixButton.type = "button";
        fixButton.className = "ci-fix-btn";
        fixButton.textContent = activeProviderName + " can try to fix this";
        fixButton.style.display = "none";
        fixButton.addEventListener("click", function () {
            const inputEl = activeInput();
            if (!inputEl) {
                return;
            }
            inputEl.value = "CI is failing. Please inspect the failing pipeline and apply a fix.";
            autoResizeInput(inputEl);
            inputEl.focus();
        });
        card.appendChild(fixButton);

        hostContainer.appendChild(card);

        const refs = {
            card: card,
            indicator: indicator,
            icon: icon,
            title: title,
            linkWrap: linkWrap,
            linkEl: linkEl,
            pipelineEl: pipelineEl,
            durationEl: durationEl,
            fixButton: fixButton,
        };
        ciCardByKey[key] = refs;
        return refs;
    }

    function addCIStatus(data) {
        if (!data || typeof data !== "object") {
            return;
        }
        const status = statusClassName(data.status || "pending");
        const prUrl = String(data.prUrl || "").trim() || lastPRUrl;
        const pipeline = String(data.pipeline || "").trim();
        const runUrl = String(data.url || "").trim();
        const key = (prUrl || "global") + "|" + (pipeline || runUrl || "default");

        let container = null;
        if (prUrl && prCardByUrl[prUrl] && prCardByUrl[prUrl].ciSlot) {
            container = prCardByUrl[prUrl].ciSlot;
        }
        const refs = upsertCIStatusCard(container, key);
        if (!refs) {
            return;
        }

        refs.indicator.className = "ci-indicator " + status;
        refs.icon.textContent = ciStatusIcon(status);
        refs.title.textContent = "CI " + toTitleCase(status);

        refs.pipelineEl.textContent = pipeline ? ("Pipeline: " + pipeline) : "";
        refs.pipelineEl.style.display = refs.pipelineEl.textContent ? "block" : "none";

        refs.durationEl.textContent = String(data.duration || "").trim()
            ? ("Duration: " + String(data.duration || "").trim())
            : "";
        refs.durationEl.style.display = refs.durationEl.textContent ? "block" : "none";

        if (/^https?:\/\//i.test(runUrl)) {
            refs.linkEl.href = runUrl;
            refs.linkEl.textContent = runUrl;
            refs.linkWrap.style.display = "block";
        } else {
            refs.linkWrap.style.display = "none";
        }

        refs.fixButton.style.display = (status === "failing" || data.suggestFix) ? "inline-flex" : "none";
        scrollToBottom(true);
    }

    function isErrorSystemMessage(raw) {
        const text = String(raw || "").trim();
        if (!text) {
            return false;
        }
        if (/\b(no|0)\s+errors?\b/i.test(text)) {
            return false;
        }
        return /\b(error|failed|failure|exception|traceback|denied|unable to|could not)\b/i.test(text);
    }

    function addErrorMessage(raw) {
        const text = String(raw || "").trim();
        if (!text) {
            return;
        }

        hideThinkingIndicator(true);
        if (renderTimerId) {
            window.clearTimeout(renderTimerId);
            renderTimerId = null;
        }
        setAssistantPhase(ASSISTANT_PHASE.ERROR);

        const rowObj = createMessageRow("error");
        const card = document.createElement("div");
        card.className = "error-card";

        const icon = document.createElement("div");
        icon.className = "error-card-icon";
        icon.textContent = "⚠";
        card.appendChild(icon);

        const content = document.createElement("div");
        const title = document.createElement("div");
        title.className = "error-card-title";
        title.textContent = /\bdenied\b/i.test(text)
            ? "Request denied"
            : "Request failed";
        content.appendChild(title);

        const message = document.createElement("div");
        message.className = "error-card-text";
        message.textContent = textWithEmojiShortcodes(text);
        content.appendChild(message);
        card.appendChild(content);

        const action = document.createElement("button");
        action.type = "button";
        action.className = "error-card-action";
        if (lastUserPayload) {
            action.textContent = "Retry";
            action.addEventListener("click", function () {
                sendPayload(lastUserPayload);
            });
        } else {
            action.textContent = "Dismiss";
            action.addEventListener("click", function () {
                const row = action.closest(".message-row");
                if (row) {
                    row.remove();
                }
            });
        }
        card.appendChild(action);

        rowObj.inner.appendChild(card);
    }

    function addSystemMessage(text) {
        setChatState(true);

        var raw = String(text || "").trim();
        if (!raw) return;

        const now = Date.now();
        if (
            raw.length >= 6
            && raw === lastSystemMessageText
            && (now - lastSystemMessageAt) < 1500
        ) {
            return;
        }
        lastSystemMessageText = raw;
        lastSystemMessageAt = now;

        try {
            var parsed = JSON.parse(raw);
            if (parsed && parsed.__permission_request__) {
                addPermissionRequest(parsed);
                return;
            }
            if (parsed && parsed.__git_card__) {
                addGitCard(parsed.__git_card__);
                return;
            }
            if (parsed && parsed.__pr_card__) {
                addPRCard(parsed.__pr_card__);
                return;
            }
            if (parsed && parsed.__ci_status__) {
                addCIStatus(parsed.__ci_status__);
                return;
            }
            if (parsed && parsed.__tool__) {
                updateLongWaitStatusFromTool(parsed);
                addToolMessage(parsed);
                return;
            }
            if (parsed && (parsed.continue !== undefined || parsed.hookSpecificOutput || parsed.suppressOutput !== undefined)) {
                return;
            }
        } catch (e) {}

        if (raw.indexOf("<session-restore>") >= 0 || raw.indexOf("<project-memory-context>") >= 0 || raw.indexOf("hookEventName") >= 0) {
            return;
        }

        if (isErrorSystemMessage(raw)) {
            addErrorMessage(raw);
            if (!userScrolledUp) {
                scrollToBottom(true);
            }
            return;
        }

        const rowObj = createMessageRow("system");
        const pill = document.createElement("div");
        pill.className = "system-pill";
        pill.textContent = textWithEmojiShortcodes(raw);

        rowObj.inner.appendChild(pill);
        if (!userScrolledUp) {
            scrollToBottom(true);
        }
    }

    function addToolMessage(data) {
        if (currentAssistantBody && currentAssistantRaw.trim()) {
            finalizeAssistantSegmentForInterleaving();
        }

        var toolUseId = data && typeof data.toolUseId === "string" ? data.toolUseId.trim() : "";
        if (toolUseId) {
            var hasOutput = !!(data.output && String(data.output).trim());
            if (seenToolUseIds[toolUseId]) {
                if (hasOutput) {
                    var existingCard = seenToolUseIds[toolUseId];
                    if (existingCard && existingCard.parentNode) {
                        var existingDetail = existingCard.querySelector(".tool-detail");
                        if (existingDetail) {
                            var outputBlock = document.createElement("div");
                            outputBlock.className = "tool-output";
                            var outputPre = document.createElement("pre");
                            outputPre.textContent = String(data.output).slice(0, 12000);
                            outputBlock.appendChild(outputPre);
                            existingDetail.appendChild(outputBlock);
                        }
                    }
                }
                /* Duplicate tool-use ID: skip card creation below but still
                   process git/pr/ci event data that may arrive with the update. */
                const dupFallback = deriveCiprFallback(data);
                const dupGitEvent = data && data.git_event && typeof data.git_event === "object"
                    ? data.git_event
                    : (dupFallback.git || null);
                const dupPrEvent = data && data.pr_event && typeof data.pr_event === "object"
                    ? data.pr_event
                    : (dupFallback.pr || null);
                const dupCiEvent = data && data.ci_event && typeof data.ci_event === "object"
                    ? data.ci_event
                    : (dupFallback.ci || null);
                if (dupGitEvent) { addGitCard(dupGitEvent); }
                if (dupPrEvent) { addPRCard(dupPrEvent); }
                if (dupCiEvent) { addCIStatus(dupCiEvent); }
                return;
            }
        }
        const fallback = deriveCiprFallback(data);
        const gitEvent = data && data.git_event && typeof data.git_event === "object"
            ? data.git_event
            : (fallback.git || null);
        const prEvent = data && data.pr_event && typeof data.pr_event === "object"
            ? data.pr_event
            : (fallback.pr || null);
        const ciEvent = data && data.ci_event && typeof data.ci_event === "object"
            ? data.ci_event
            : (fallback.ci || null);

        if (gitEvent) {
            addGitCard(gitEvent);
        }
        if (prEvent) {
            addPRCard(prEvent);
        }
        if (ciEvent) {
            addCIStatus(ciEvent);
        }

        const toolName = String(data.name || "tool");
        const filePath = String(data.path || data.command || "");
        const commandText = String(data.command || "");
        const outputText = String(data.output || "");
        const diffPayload = getToolDiffPayload(data);
        const hasDiff = !!diffPayload;
        const hasDetail = hasDiff || !!commandText || !!outputText;

        const rowObj = createMessageRow("tool");
        const details = document.createElement("details");
        details.className = "tool-card";
        toolCardCounter += 1;
        details.id = "tool-card-" + toolCardCounter;

        const summary = document.createElement("summary");
        summary.className = "tool-header";

        const nameEl = document.createElement("span");
        nameEl.className = "tool-name";
        nameEl.textContent = toolName;
        summary.appendChild(nameEl);

        if (filePath) {
            const pathEl = document.createElement("span");
            pathEl.className = "tool-path";
            var displayPath = filePath;
            if (displayPath.length > 60) {
                displayPath = "\u2026" + displayPath.slice(-57);
            }
            pathEl.textContent = displayPath;
            summary.appendChild(pathEl);
        }

        details.appendChild(summary);

        var detailEl = null;
        var summaryEntry = null;

        if (hasDetail) {
            detailEl = document.createElement("div");
            detailEl.className = "tool-detail";

            if (hasDiff && diffPayload) {
                const renderedDiff = buildRenderedDiff(
                    diffPayload.oldText,
                    diffPayload.newText,
                    filePath || toolName || "file"
                );
                const toolbar = document.createElement("div");
                toolbar.className = "tool-detail-toolbar";
                toolbar.appendChild(
                    createDiffStatElement(renderedDiff.additions, renderedDiff.deletions)
                );

                const actions = document.createElement("div");
                actions.className = "tool-detail-actions";
                const copyDiffBtn = document.createElement("button");
                copyDiffBtn.type = "button";
                copyDiffBtn.className = "tool-copy-diff-btn";
                copyDiffBtn.textContent = "Copy diff";
                copyDiffBtn.setAttribute(
                    "data-diff-raw",
                    encodeURIComponent(renderedDiff.unifiedText || "")
                );
                actions.appendChild(copyDiffBtn);
                toolbar.appendChild(actions);
                detailEl.appendChild(toolbar);

                const diffHeader = document.createElement("div");
                diffHeader.className = "diff-header";
                const iconEl = document.createElement("span");
                iconEl.className = "diff-header-icon";
                if (diffPayload.status === "new") {
                    iconEl.textContent = "＋";
                } else if (diffPayload.status === "deleted") {
                    iconEl.textContent = "−";
                } else {
                    iconEl.textContent = "±";
                }
                diffHeader.appendChild(iconEl);
                const pathEl = document.createElement("span");
                pathEl.className = "diff-header-path";
                pathEl.textContent = filePath || "(inline content)";
                diffHeader.appendChild(pathEl);
                detailEl.appendChild(diffHeader);

                const diffBody = document.createElement("div");
                diffBody.innerHTML = renderedDiff.html;
                detailEl.appendChild(diffBody);

                if (filePath) {
                    summaryEntry = {
                        path: filePath,
                        additions: renderedDiff.additions,
                        deletions: renderedDiff.deletions,
                        status: diffPayload.status,
                        cardId: card.id,
                    };
                }
                openByDefault = (
                    renderedDiff.totalLines <= DIFF_AUTO_EXPAND_MAX_LINES
                    && !renderedDiff.truncated
                );
            }

            if (commandText) {
                const cmdBlock = document.createElement("div");
                cmdBlock.className = "tool-code";
                cmdBlock.textContent = "$ " + commandText;
                detailEl.appendChild(cmdBlock);
            }

            if (outputText) {
                const outputBlock = document.createElement("div");
                outputBlock.className = "tool-code";
                outputBlock.textContent = outputText;
                detailEl.appendChild(outputBlock);
            }

            details.appendChild(detailEl);
            if (openByDefault) {
                details.open = true;
            }
        }

        registerToolArtifact(data, details);
        rowObj.inner.appendChild(details);
        if (toolUseId) {
            seenToolUseIds[toolUseId] = details;
        }
        trackToolEvent(summaryEntry, rowObj.row);
        scrollToBottom(true);
    }

    function permissionIconForTool(toolName) {
        const name = String(toolName || "").trim().toLowerCase();
        if (name === "bash") {
            return "⌘";
        }
        if (name === "edit" || name === "multiedit" || name === "write") {
            return "✎";
        }
        if (name === "read" || name === "grep" || name === "glob") {
            return "📄";
        }
        return "⚠";
    }

    function addPermissionRequest(data) {
        setChatState(true);
        noteWaitActivity();
        stopWaitRotateTimer();
        scheduleWaitInactivityTimer();
        applyLongWaitStatus("Waiting for your approval...", {
            immediate: false,
            source: "permission",
        });

        const toolName = String(data.name || "Tool");
        const isDenialCard = !!data.__permission_denied__;
        const description = String(
            data.description || (activeProviderName + " requests approval before running this tool.")
        );
        const proposedAction = String(data.proposedAction || "");
        const filePath = String(data.path || "");
        const command = String(data.command || "");
        const choices = Array.isArray(data.choices) ? data.choices.filter(function (item) {
            return String(item || "").trim();
        }).map(function (item) {
            return String(item).trim().slice(0, 120);
        }) : [];
        const defaultChoice = String(data.defaultChoice || data.default_choice || "").trim();
        const oldText = (data.old !== undefined || data.old_content !== undefined)
            ? String(data.old_content !== undefined ? data.old_content : (data.old || ""))
            : "";
        const newText = (data.new !== undefined || data.new_content !== undefined)
            ? String(data.new_content !== undefined ? data.new_content : (data.new || ""))
            : "";
        const contentText = String(data.content || "");

        permissionRequestCounter += 1;
        const requestId = String(data.requestId || "").trim() || ("permission-" + permissionRequestCounter);
        if (seenPermissionRequests[requestId]) {
            return;
        }
        seenPermissionRequests[requestId] = true;

        const rowObj = createMessageRow("permission");
        const card = document.createElement("div");
        card.className = isDenialCard
            ? "permission-request-card pending permission-denied"
            : "permission-request-card pending";
        card.setAttribute("data-request-id", requestId);

        const header = document.createElement("div");
        header.className = "permission-request-header";

        const icon = document.createElement("span");
        icon.className = "permission-request-icon";
        icon.textContent = isDenialCard ? "\u26D4" : permissionIconForTool(toolName);
        header.appendChild(icon);

        const titleWrap = document.createElement("div");
        titleWrap.className = "permission-request-title";

        const toolLabel = document.createElement("div");
        toolLabel.className = "permission-request-tool";
        toolLabel.textContent = toolName;
        titleWrap.appendChild(toolLabel);

        const subtitle = document.createElement("div");
        subtitle.className = "permission-request-subtitle";
        subtitle.textContent = isDenialCard ? "Permission denied" : "Permission required";
        titleWrap.appendChild(subtitle);

        header.appendChild(titleWrap);
        card.appendChild(header);

        const descriptionEl = document.createElement("p");
        descriptionEl.className = "permission-request-description";
        descriptionEl.textContent = description;
        card.appendChild(descriptionEl);

        const meta = document.createElement("div");
        meta.className = "permission-meta";

        if (proposedAction) {
            const actionItem = document.createElement("div");
            actionItem.className = "permission-meta-item";
            actionItem.innerHTML = [
                '<div class="permission-meta-label">Proposed action</div>',
                '<div class="permission-meta-value"></div>',
            ].join("");
            const valueEl = actionItem.querySelector(".permission-meta-value");
            if (valueEl) {
                valueEl.textContent = proposedAction;
            }
            meta.appendChild(actionItem);
        }

        if (filePath) {
            const fileItem = document.createElement("div");
            fileItem.className = "permission-meta-item";
            fileItem.innerHTML = [
                '<div class="permission-meta-label">Path</div>',
                '<div class="permission-meta-value"></div>',
            ].join("");
            const valueEl = fileItem.querySelector(".permission-meta-value");
            if (valueEl) {
                valueEl.textContent = filePath;
            }
            meta.appendChild(fileItem);
        }

        if (command) {
            const commandItem = document.createElement("div");
            commandItem.className = "permission-meta-item";
            commandItem.innerHTML = [
                '<div class="permission-meta-label">Command</div>',
                '<div class="permission-meta-value"></div>',
            ].join("");
            const valueEl = commandItem.querySelector(".permission-meta-value");
            if (valueEl) {
                valueEl.textContent = command;
            }
            meta.appendChild(commandItem);
        }

        if (meta.children.length > 0) {
            card.appendChild(meta);
        }

        const hasPreview = !!(oldText || newText || contentText || command);
        if (hasPreview) {
            const preview = document.createElement("div");
            preview.className = "permission-preview";

            if (oldText || newText) {
                if (oldText) {
                    const oldBlock = document.createElement("div");
                    oldBlock.className = "tool-diff-old";
                    oldBlock.textContent = "- " + oldText.replace(/\n/g, "\n- ");
                    preview.appendChild(oldBlock);
                }
                if (newText) {
                    const newBlock = document.createElement("div");
                    newBlock.className = "tool-diff-new";
                    newBlock.textContent = "+ " + newText.replace(/\n/g, "\n+ ");
                    preview.appendChild(newBlock);
                }
            } else if (contentText) {
                const contentBlock = document.createElement("div");
                contentBlock.className = "tool-code";
                contentBlock.textContent = contentText;
                preview.appendChild(contentBlock);
            } else if (command) {
                const commandBlock = document.createElement("div");
                commandBlock.className = "tool-code";
                commandBlock.textContent = "$ " + command;
                preview.appendChild(commandBlock);
            }

            card.appendChild(preview);
        }

        const actions = document.createElement("div");
        actions.className = "permission-actions";

        if (isDenialCard) {
            const allowForSessionBtn = document.createElement("button");
            allowForSessionBtn.type = "button";
            allowForSessionBtn.className = "permission-action-btn allow";
            allowForSessionBtn.textContent = "Allow " + toolName + " (re-send to retry)";
            actions.appendChild(allowForSessionBtn);

            const alwaysAllowBtn = document.createElement("button");
            alwaysAllowBtn.type = "button";
            alwaysAllowBtn.className = "permission-action-btn always-allow";
            alwaysAllowBtn.textContent = "Always Allow " + toolName;
            actions.appendChild(alwaysAllowBtn);

            const denyButton = document.createElement("button");
            denyButton.type = "button";
            denyButton.className = "permission-action-btn deny";
            denyButton.textContent = "Keep Denied";
            actions.appendChild(denyButton);

            const status = document.createElement("div");
            status.className = "permission-response-status";
            status.textContent = "This tool was denied. Allow it and re-send your message to retry.";
            card.appendChild(actions);
            card.appendChild(status);

            let resolved = false;

            function resolveDenialCard(action) {
                if (resolved) return;
                resolved = true;
                card.classList.remove("pending");
                card.classList.add("resolved");
                allowForSessionBtn.disabled = true;
                alwaysAllowBtn.disabled = true;
                denyButton.disabled = true;

                if (action === "allow" || action === "always_allow") {
                    status.textContent = toolName + " allowed for this session. Re-send your message to retry.";
                } else {
                    status.textContent = "Permission remains denied.";
                }
            }

            allowForSessionBtn.addEventListener("click", function () {
                postToHost("permissionResponse", JSON.stringify({
                    action: "allow",
                    toolName: toolName,
                    requestId: requestId,
                    isDenialCard: true,
                }));
                resolveDenialCard("allow");
            });

            alwaysAllowBtn.addEventListener("click", function () {
                postToHost("permissionResponse", JSON.stringify({
                    action: "always_allow",
                    toolName: toolName,
                    requestId: requestId,
                    isDenialCard: true,
                }));
                resolveDenialCard("always_allow");
            });

            denyButton.addEventListener("click", function () {
                postToHost("permissionResponse", JSON.stringify({
                    action: "deny",
                    toolName: toolName,
                    requestId: requestId,
                    isDenialCard: true,
                }));
                resolveDenialCard("deny");
            });
        } else {
            const hasChoices = choices.length > 0;
            const normalizedDefaultChoice = defaultChoice.toLowerCase();

            const commentWrap = document.createElement("div");
            commentWrap.className = "permission-comment-wrap";

            const commentInput = document.createElement("input");
            commentInput.type = "text";
            commentInput.className = "permission-comment-input";
            commentInput.placeholder = "Reply in text (or pick a button)";
            commentWrap.appendChild(commentInput);

            const commentButton = document.createElement("button");
            commentButton.type = "button";
            commentButton.className = "permission-action-btn";
            commentButton.textContent = "Send";
            commentWrap.appendChild(commentButton);

            if (hasChoices) {
                const choiceGrid = document.createElement("div");
                choiceGrid.className = "permission-actions";

                for (let index = 0; index < choices.length; index += 1) {
                    const choice = choices[index];
                    const isDefault = choice.toLowerCase() === normalizedDefaultChoice;
                    const button = document.createElement("button");
                    button.type = "button";
                    button.className = isDefault
                        ? "permission-action-btn allow"
                        : "permission-action-btn";
                    button.textContent = choice;
                    choiceGrid.appendChild(button);

                    button.addEventListener("click", function () {
                        const normalizedChoice = String(choice || "").trim().toLowerCase();
                        if (["y", "yes", "ja", "j", "allow", "approve", "approved", "ok", "okay", "true", "1"].includes(normalizedChoice)) {
                            submitResponse("allow", choice);
                            return;
                        }
                        if (["n", "no", "nein", "deny", "denied", "reject", "rejected", "false", "0"].includes(normalizedChoice)) {
                            submitResponse("deny", choice);
                            return;
                        }
                        submitResponse("comment", choice);
                    });
                }
                actions.appendChild(choiceGrid);
            } else {
                const allowButton = document.createElement("button");
                allowButton.type = "button";
                allowButton.className = "permission-action-btn allow";
                allowButton.textContent = "Allow";
                actions.appendChild(allowButton);

                const alwaysAllowBtn = document.createElement("button");
                alwaysAllowBtn.type = "button";
                alwaysAllowBtn.className = "permission-action-btn always-allow";
                alwaysAllowBtn.textContent = "Always Allow " + toolName;
                actions.appendChild(alwaysAllowBtn);

                const denyButton = document.createElement("button");
                denyButton.type = "button";
                denyButton.className = "permission-action-btn deny";
                denyButton.textContent = "Deny";
                actions.appendChild(denyButton);
            }

            actions.appendChild(commentWrap);
            card.appendChild(actions);

            const status = document.createElement("div");
            status.className = "permission-response-status";
            status.textContent = "Waiting for your decision.";
            card.appendChild(status);

            let resolved = false;

            function resolveCard(action, commentText) {
                if (resolved) {
                    return;
                }
                resolved = true;
                card.classList.remove("pending");
                card.classList.add("resolved");

                commentButton.disabled = true;
                commentInput.disabled = true;

                const actionButtons = actions.querySelectorAll(".permission-action-btn");
                for (let index = 0; index < actionButtons.length; index += 1) {
                    actionButtons[index].disabled = true;
                }

                if (action === "allow" || action === "always_allow") {
                    status.textContent = "Approved. Sent to " + activeProviderName + ".";
                    return;
                }
                if (action === "deny") {
                    status.textContent = "Denied. " + activeProviderName + " will not run this action.";
                    return;
                }
                status.textContent = commentText
                    ? 'Answer sent: "' + commentText + '"'
                    : ("Answer sent to " + activeProviderName + ".");
            }

            function submitResponse(action, commentText) {
                if (resolved) {
                    return;
                }

                const trimmedComment = typeof commentText === "string"
                    ? String(commentText).trim()
                    : String(commentInput.value || "").trim();
                if (action === "comment" && !trimmedComment) {
                    commentInput.focus();
                    return;
                }

                postToHost("permissionResponse", JSON.stringify({
                    action: action,
                    toolName: toolName,
                    comment: action === "comment" ? trimmedComment : "",
                    requestId: requestId,
                    isDenialCard: false,
                }));
                resolveCard(action, trimmedComment);
            }

            commentButton.addEventListener("click", function () {
                submitResponse("comment");
            });

            commentInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                    submitResponse("comment");
                }
            });

            if (!hasChoices) {
                const allowButton = actions.querySelector(".permission-action-btn.allow");
                const alwaysAllowBtn = actions.querySelector(".permission-action-btn.always-allow");
                const denyButton = actions.querySelector(".permission-action-btn.deny");

                if (alwaysAllowBtn) {
                    alwaysAllowBtn.classList.remove("allow");
                }

                if (allowButton) {
                    allowButton.addEventListener("click", function () {
                        submitResponse("allow");
                    });
                }
                if (alwaysAllowBtn) {
                    alwaysAllowBtn.addEventListener("click", function () {
                        submitResponse("always_allow");
                    });
                }
                if (denyButton) {
                    denyButton.addEventListener("click", function () {
                        submitResponse("deny");
                    });
                }
            }
        }

        rowObj.inner.appendChild(card);
        scrollToBottom(true);
    }

    function showThinkingIndicator() {
        if (thinkingIndicatorRow) {
            return;
        }

        const rowObj = createMessageRow("assistant");
        rowObj.inner.appendChild(createThinkingShellElement());
        thinkingIndicatorRow = rowObj.row;
        renderWaitStatus(true);
        if (!userScrolledUp) {
            scrollToBottom(true);
        } else {
            updateScrollButtonVisibility();
        }
    }

    function hideThinkingIndicator(immediate) {
        if (!thinkingIndicatorRow) {
            return;
        }

        const el = thinkingIndicatorRow;
        thinkingIndicatorRow = null;
        if (immediate) {
            if (el.isConnected) {
                el.remove();
            }
            updateUserScrolledState();
            return;
        }

        const indicator = el.querySelector(".thinking-indicator");
        if (indicator) {
            indicator.classList.add("fade-out");
        }

        window.setTimeout(function () {
            if (el.isConnected) {
                el.remove();
            }
            updateUserScrolledState();
        }, MOTION_FAST_MS);
    }

    function ensureAssistantMessageRow() {
        if (currentAssistantBody) {
            return;
        }

        const rowObj = createMessageRow("assistant");
        const block = document.createElement("div");
        block.className = "assistant-block";

        const wrap = document.createElement("div");
        wrap.className = "assistant-content-wrap";

        const body = document.createElement("div");
        body.className = "assistant-message markdown-body";

        const badge = document.createElement("div");
        badge.className = "copy-success-badge";
        badge.textContent = "Copied!";

        const actions = document.createElement("div");
        actions.className = "assistant-actions";
        actions.innerHTML = [
            '<button class="assistant-action" data-action="copy" type="button" title="Copy">📋</button>',
            '<button class="assistant-action copy-md-action" data-action="copy-md" type="button" title="Copy as Markdown">📋 MD</button>',
            '<button class="assistant-action" data-action="up" type="button" title="Thumbs up">👍</button>',
            '<button class="assistant-action" data-action="down" type="button" title="Thumbs down">👎</button>',
            '<button class="assistant-action" data-action="retry" type="button" title="Retry">🔄</button>',
        ].join("");

        wrap.appendChild(body);
        wrap.appendChild(actions);
        wrap.appendChild(badge);

        block.appendChild(wrap);
        rowObj.inner.appendChild(block);

        currentAssistantRow = rowObj.row;
        currentAssistantBody = body;
    }

    function startAssistantMessage() {
        setChatState(true);
        setAssistantPhase(ASSISTANT_PHASE.WAITING_FIRST_TOKEN);
        showThinkingIndicator();

        if (currentAssistantBody) {
            return;
        }

        currentAssistantRaw = "";
        assistantHasFirstChunk = false;

        if (!userScrolledUp) {
            scrollToBottom(true);
        }
    }

    function renderAssistantContent(showCursor) {
        if (!currentAssistantBody) {
            return;
        }
        currentAssistantBody.innerHTML = markdownToHtml(currentAssistantRaw);
        currentAssistantBody.dataset.raw = currentAssistantRaw;
        currentAssistantBody.dataset.rawMarkdown = currentAssistantRaw;
        if (showCursor) {
            const cursor = document.createElement("span");
            cursor.className = "streaming-cursor";
            currentAssistantBody.appendChild(cursor);
            window.requestAnimationFrame(function () {
                cursor.classList.add("is-visible");
            });
        }
    }

    function normalizeStreamRenderThrottle(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return DEFAULT_STREAM_RENDER_THROTTLE_MS;
        }
        return Math.max(0, Math.min(1500, Math.round(numeric)));
    }

    function queueAssistantRenderFrame() {
        if (renderQueued) {
            return;
        }

        renderQueued = true;
        window.requestAnimationFrame(function () {
            renderQueued = false;
            lastAssistantRenderAt = Date.now();
            renderAssistantContent(true);
            if (!userScrolledUp) {
                scrollToBottom(true);
            } else {
                updateScrollButtonVisibility();
            }
        });
    }

    function scheduleAssistantRender(forceImmediate) {
        if (!currentAssistantBody) {
            return;
        }

        if (forceImmediate) {
            if (renderTimerId) {
                window.clearTimeout(renderTimerId);
                renderTimerId = null;
            }
            queueAssistantRenderFrame();
            return;
        }

        if (renderTimerId || renderQueued) {
            return;
        }

        const elapsed = Date.now() - lastAssistantRenderAt;
        const delay = Math.max(0, streamRenderThrottleMs - elapsed);
        if (delay === 0) {
            queueAssistantRenderFrame();
            return;
        }

        renderTimerId = window.setTimeout(function () {
            renderTimerId = null;
            queueAssistantRenderFrame();
        }, delay);
    }

    function stopAssistantRevealTimer() {
        if (assistantRevealTimer) {
            window.clearTimeout(assistantRevealTimer);
            assistantRevealTimer = null;
        }
    }

    function assistantRevealChunkSize() {
        if (streamRenderThrottleMs <= 0) {
            return Number.MAX_SAFE_INTEGER;
        }
        if (streamRenderThrottleMs <= 30) {
            return 120;
        }
        if (streamRenderThrottleMs <= 80) {
            return 80;
        }
        if (streamRenderThrottleMs <= 160) {
            return 42;
        }
        if (streamRenderThrottleMs <= 280) {
            return 24;
        }
        return 16;
    }

    function completeAssistantMessageNow() {
        const lingeringIndicators = messagesEl.querySelectorAll(".thinking-indicator");
        lingeringIndicators.forEach(function (indicator) {
            const row = indicator.closest(".message-row");
            if (row) {
                row.remove();
                return;
            }
            indicator.remove();
        });

        if (!currentAssistantBody && currentAssistantRaw.trim()) {
            ensureAssistantMessageRow();
        }

        if (currentAssistantBody) {
            if (!hasMessages) {
                setChatState(true);
            }
            renderAssistantContent(false);
            registerAssistantArtifacts(currentAssistantBody, currentAssistantRaw);
            if (!currentAssistantRaw.trim() && currentAssistantRow) {
                currentAssistantRow.remove();
            }
        }

        const cursors = messagesEl.querySelectorAll(".streaming-cursor");
        cursors.forEach(function (cursor) {
            cursor.remove();
        });

        currentAssistantBody = null;
        currentAssistantRow = null;
        currentAssistantRaw = "";
        pendingAssistantText = "";
        finishAfterPendingReveal = false;
        assistantHasFirstChunk = false;
        lastAssistantChunkText = "";
        lastAssistantChunkAt = 0;
        refreshChatSearchIfActive();
        setAssistantPhase(ASSISTANT_PHASE.DONE);
        if (!userScrolledUp) {
            scrollToBottom(true);
        }
    }

    function flushPendingAssistantText(immediate) {
        if (!pendingAssistantText) {
            if (finishAfterPendingReveal) {
                finishAfterPendingReveal = false;
                completeAssistantMessageNow();
            }
            return;
        }

        if (immediate || streamRenderThrottleMs <= 0) {
            currentAssistantRaw += pendingAssistantText;
            pendingAssistantText = "";
            stopAssistantRevealTimer();
            scheduleAssistantRender(true);
            if (finishAfterPendingReveal) {
                finishAfterPendingReveal = false;
                completeAssistantMessageNow();
            }
            return;
        }

        if (assistantRevealTimer) {
            return;
        }

        const revealStep = function () {
            assistantRevealTimer = null;
            if (!pendingAssistantText) {
                if (finishAfterPendingReveal) {
                    finishAfterPendingReveal = false;
                    completeAssistantMessageNow();
                }
                return;
            }

            const size = assistantRevealChunkSize();
            const segment = pendingAssistantText.slice(0, size);
            pendingAssistantText = pendingAssistantText.slice(segment.length);
            currentAssistantRaw += segment;
            scheduleAssistantRender(true);

            if (pendingAssistantText) {
                assistantRevealTimer = window.setTimeout(revealStep, streamRenderThrottleMs);
                return;
            }

            if (finishAfterPendingReveal) {
                finishAfterPendingReveal = false;
                completeAssistantMessageNow();
            }
        };

        revealStep();
    }

    function appendAssistantChunk(text) {
        if (!text) {
            return;
        }

        const chunkText = String(text);
        const now = Date.now();
        if (
            chunkText.length >= 8
            && chunkText === lastAssistantChunkText
            && (now - lastAssistantChunkAt) < 1500
        ) {
            return;
        }
        lastAssistantChunkText = chunkText;
        lastAssistantChunkAt = now;

        let normalizedChunk = chunkText;
        const combinedAssistantRaw = currentAssistantRaw + pendingAssistantText;
        if (combinedAssistantRaw) {
            if (normalizedChunk === combinedAssistantRaw) {
                return;
            }
            if (normalizedChunk.startsWith(combinedAssistantRaw)) {
                normalizedChunk = normalizedChunk.slice(combinedAssistantRaw.length);
            } else if (combinedAssistantRaw.startsWith(normalizedChunk)) {
                return;
            } else if (normalizedChunk.length >= 24 && combinedAssistantRaw.indexOf(normalizedChunk) >= 0) {
                return;
            } else {
                const maxOverlap = Math.min(combinedAssistantRaw.length, normalizedChunk.length, 768);
                let overlap = 0;
                for (let size = maxOverlap; size >= 12; size -= 1) {
                    if (combinedAssistantRaw.slice(-size) === normalizedChunk.slice(0, size)) {
                        overlap = size;
                        break;
                    }
                }
                if (overlap > 0) {
                    normalizedChunk = normalizedChunk.slice(overlap);
                }
            }
        }

        if (!normalizedChunk) {
            return;
        }

        if (!currentAssistantBody && !thinkingIndicatorRow) {
            if (processingActive && assistantPhase === ASSISTANT_PHASE.STREAMING) {
                ensureAssistantMessageRow();
                assistantHasFirstChunk = true;
            } else {
                startAssistantMessage();
            }
        }

        clearLongWaitStatusInternal({ immediate: true });
        resetLongWaitStatusTimers();

        if (!assistantHasFirstChunk) {
            assistantHasFirstChunk = true;
            ensureAssistantMessageRow();
            hideThinkingIndicator(false);
            setAssistantPhase(ASSISTANT_PHASE.STREAMING);
        }

        pendingAssistantText += normalizedChunk;
        flushPendingAssistantText(false);
    }

    function finalizeAssistantSegmentForInterleaving() {
        flushPendingAssistantText(true);
        if (!currentAssistantBody) {
            return;
        }

        if (currentAssistantRaw.trim()) {
            renderAssistantContent(false);
            registerAssistantArtifacts(currentAssistantBody, currentAssistantRaw);
        } else if (currentAssistantRow) {
            currentAssistantRow.remove();
        }

        currentAssistantBody = null;
        currentAssistantRow = null;
        currentAssistantRaw = "";
        assistantHasFirstChunk = false;
    }

    function finishAssistantMessage() {
        processingActive = false;
        clearLongWaitStatusAndTimers(true);
        hideThinkingIndicator(true);
        if (renderTimerId) {
            window.clearTimeout(renderTimerId);
            renderTimerId = null;
        }
        if (pendingAssistantText) {
            finishAfterPendingReveal = true;
            setAssistantPhase(ASSISTANT_PHASE.DONE);
            flushPendingAssistantText(false);
            return;
        }
        completeAssistantMessageNow();
    }

    function setTyping(isTyping) {
        const shouldShow = !!isTyping;

        if (shouldShow && !typingRow) {
            setChatState(true);
            setAssistantPhase(ASSISTANT_PHASE.WAITING_FIRST_TOKEN);

            const rowObj = createMessageRow("assistant");
            const shell = document.createElement("div");
            shell.className = "typing-shell";
            shell.appendChild(createThinkingShellElement());
            rowObj.inner.appendChild(shell);
            typingRow = rowObj.row;
            renderWaitStatus(true);
            if (!userScrolledUp) {
                scrollToBottom(true);
            }
            return;
        }

        if (!shouldShow && typingRow) {
            typingRow.remove();
            typingRow = null;
            setAssistantPhase(ASSISTANT_PHASE.DONE);
            if (!userScrolledUp) {
                scrollToBottom(true);
            }
        }
    }

    function clearMessages() {
        renderQueued = false;
        if (renderTimerId) {
            window.clearTimeout(renderTimerId);
            renderTimerId = null;
        }
        stopAssistantRevealTimer();
        processingActive = false;
        clearLongWaitStatusAndTimers(true);
        lastAssistantRenderAt = 0;
        currentAssistantRaw = "";
        pendingAssistantText = "";
        finishAfterPendingReveal = false;
        currentAssistantBody = null;
        currentAssistantRow = null;
        assistantHasFirstChunk = false;
        lastAssistantChunkText = "";
        lastAssistantChunkAt = 0;
        lastSystemMessageText = "";
        lastSystemMessageAt = 0;
        typingRow = null;
        thinkingIndicatorRow = null;
        setAssistantPhase(ASSISTANT_PHASE.IDLE);
        userScrolledUp = false;
        resetToolTurnState();
        toolCardCounter = 0;
        lastPRUrl = "";
        Object.keys(prCardByKey).forEach(function (key) {
            delete prCardByKey[key];
        });
        Object.keys(prCardByUrl).forEach(function (key) {
            delete prCardByUrl[key];
        });
        Object.keys(ciCardByKey).forEach(function (key) {
            delete ciCardByKey[key];
        });
        Object.keys(seenToolUseIds).forEach(function (key) {
            delete seenToolUseIds[key];
        });
        resetArtifactsSession();
        closeImageLightbox();

        messagesEl.innerHTML = "";
        updateScrollButtonVisibility();
        setChatState(false);
        clearInputs();
        clearAttachments();
    }

    function showWelcome() {
        clearMessages();
    }

    function copyText(raw, onDone) {
        const text = String(raw || "");
        if (!text) {
            return;
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(function () {
                if (typeof onDone === "function") {
                    onDone();
                }
            }).catch(function () {});
            return;
        }

        const temp = document.createElement("textarea");
        temp.value = text;
        document.body.appendChild(temp);
        temp.select();
        try {
            document.execCommand("copy");
            if (typeof onDone === "function") {
                onDone();
            }
        } catch (_error) {
        } finally {
            temp.remove();
        }
    }

    function copyMarkdownText(rawMarkdown, onDone) {
        const text = String(rawMarkdown || "");
        if (!text) {
            return;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(function () {
                if (typeof onDone === "function") {
                    onDone();
                }
            }).catch(function () {
                copyText(text, onDone);
            });
            return;
        }
        copyText(text, onDone);
    }

    function showCopySuccessBadge(button) {
        if (!button) {
            return;
        }
        const container = button.closest(".assistant-content-wrap, .user-bubble-wrap");
        if (!container) {
            return;
        }
        const badge = container.querySelector(".copy-success-badge");
        if (!badge) {
            return;
        }
        if (badge._hideTimer) {
            window.clearTimeout(badge._hideTimer);
        }
        badge.classList.add("visible");
        badge._hideTimer = window.setTimeout(function () {
            badge.classList.remove("visible");
            badge._hideTimer = null;
        }, 1200);
    }

    function showCopiedFeedback(button) {
        if (!button) {
            return;
        }
        if (!button.dataset.originalLabel) {
            button.dataset.originalLabel = button.textContent || "Copy";
        }
        if (button._copyFeedbackTimer) {
            window.clearTimeout(button._copyFeedbackTimer);
        }
        button.classList.add("copied");
        button.textContent = "Copied!";
        button._copyFeedbackTimer = window.setTimeout(function () {
            button.classList.remove("copied");
            button.textContent = button.dataset.originalLabel || "Copy";
            button._copyFeedbackTimer = null;
        }, 2000);
    }

var GLASS_BUTTON_SELECTOR = [
    ".folder-path-btn",
    ".plus-btn",
    ".agent-mode-toggle-btn",
    ".selector-btn",
    ".permission-btn",
        ".permission-selector",
        ".assistant-action",
        ".action-btn",
        ".code-copy-btn",
        ".chip",
        ".quick-chip",
        ".artifact-action-btn",
        ".stop-process-btn",
        ".example-prompt",
        ".popup-menu",
    ];
    var GLASS_REDUCED_MOTION_CLASS = "reduced-motion";
    var GLASS_ACTIVE_ANIMATIONS = typeof WeakMap === "function" ? new WeakMap() : new Map();

    function setReducedMotionState(isReduced) {
        if (!document.body) {
            return;
        }
        if (isReduced) {
            document.body.classList.add(GLASS_REDUCED_MOTION_CLASS);
            return;
        }
        document.body.classList.remove(GLASS_REDUCED_MOTION_CLASS);
    }

    window.setReducedMotion = function (isReduced) {
        setReducedMotionState(!!isReduced);
    };

    function glassHover(target, isHover) {
        if (!target || !target.classList) {
            return;
        }
        var reduced = document.body && document.body.classList.contains(GLASS_REDUCED_MOTION_CLASS);
        if (reduced) {
            target.style.willChange = "auto";
            target.style.transform = isHover ? "scale(1.02)" : "";
            return;
        }

        if (!window.Motion || !window.Motion.animate) {
            target.style.transform = isHover ? "scale(1.02)" : "";
            return;
        }

        var existing = GLASS_ACTIVE_ANIMATIONS.get(target);
        if (existing && typeof existing.stop === "function") {
            existing.stop();
        }

        target.style.willChange = "transform";
        var animation = window.Motion.animate(
            target,
            { transform: isHover ? [1, 1.02] : [1.02, 1] },
            {
                duration: 0.22,
                easing: window.Motion.spring(240, 22, 1),
            },
        );
        GLASS_ACTIVE_ANIMATIONS.set(target, animation);
        animation.finished.then(function () {
            if (GLASS_ACTIVE_ANIMATIONS.get(target) === animation) {
                target.style.willChange = "auto";
                GLASS_ACTIVE_ANIMATIONS.delete(target);
            }
        });
    }

    function glassPress(target) {
        if (!target || !target.classList) {
            return;
        }

        if (document.body && document.body.classList.contains(GLASS_REDUCED_MOTION_CLASS)) {
            target.style.transform = "scale(0.96)";
            window.setTimeout(function () {
                target.style.transform = "";
            }, 80);
            return;
        }
        if (!window.Motion || !window.Motion.animate) {
            target.style.transform = "scale(0.96)";
            return;
        }

        var existing = GLASS_ACTIVE_ANIMATIONS.get(target);
        if (existing && typeof existing.stop === "function") {
            existing.stop();
        }

        target.style.willChange = "transform";
        var pressed = window.Motion.animate(
            target,
            { transform: [1, 0.96, 1] },
            {
                duration: 0.28,
                easing: window.Motion.spring(200, 24, 1),
            },
        );
        GLASS_ACTIVE_ANIMATIONS.set(target, pressed);
        pressed.finished.then(function () {
            if (GLASS_ACTIVE_ANIMATIONS.get(target) !== pressed) {
                return;
            }
            target.style.willChange = "auto";
            GLASS_ACTIVE_ANIMATIONS.delete(target);
            target.style.transform = "";
        });
    }

    function wireGlassButtons() {
        var reducedMotionQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
        if (reducedMotionQuery && typeof reducedMotionQuery.matches !== "undefined") {
            setReducedMotionState(!!reducedMotionQuery.matches);
            if (typeof reducedMotionQuery.addEventListener === "function") {
                reducedMotionQuery.addEventListener("change", function (event) {
                    setReducedMotionState(!!event.matches);
                });
            } else if (typeof reducedMotionQuery.addListener === "function") {
                reducedMotionQuery.addListener(function (event) {
                    setReducedMotionState(!!event.matches);
                });
            }
        }

        var selectors = GLASS_BUTTON_SELECTOR.join(", ");
        var pressHandler = function (event) {
            var target = event.target.closest(selectors);
            if (!target) {
                return;
            }
            if (!event.button || event.button === 0 || event.type === "pointerdown") {
                glassPress(target);
            }
        };
        var hoverHandler = function (event) {
            var target = event.target.closest(selectors);
            if (!target) {
                return;
            }
            if (event.type === "pointerover") {
                glassHover(target, true);
                return;
            }
            glassHover(target, false);
        };

        document.body.addEventListener("pointerdown", pressHandler, true);
        document.body.addEventListener("pointerover", hoverHandler, true);
        document.body.addEventListener("pointerout", hoverHandler, true);
    }

    function markActionPressed(button) {
        const action = button.getAttribute("data-action");
        if (action === "up" || action === "down") {
            const parent = button.parentElement;
            if (parent) {
                const opposite = parent.querySelector('[data-action="' + (action === "up" ? "down" : "up") + '"]');
                if (opposite) {
                    opposite.classList.remove("active");
                }
            }
            button.classList.toggle("active");
            return;
        }

        const previous = button.textContent;
        button.classList.add("active");
        button.textContent = "✓";
        window.setTimeout(function () {
            button.classList.remove("active");
            button.textContent = previous;
        }, 700);
    }

    function getSlashDropdownForInput(inputEl) {
        if (inputEl === welcomeInputEl) return welcomeSlashDropdownEl;
        if (inputEl === chatInputEl) return chatSlashDropdownEl;
        return null;
    }

    function normalizeCommandProviders(rawProviders) {
        if (!Array.isArray(rawProviders)) {
            return ["claude", "codex", "gemini"];
        }
        var normalized = [];
        rawProviders.forEach(function (entry) {
            var provider = String(entry || "").trim().toLowerCase();
            if ((provider === "claude" || provider === "codex" || provider === "gemini") && normalized.indexOf(provider) === -1) {
                normalized.push(provider);
            }
        });
        return normalized.length ? normalized : ["claude", "codex", "gemini"];
    }

    function allSlashCommands() {
        var merged = [];
        var seen = Object.create(null);
        var provider = String(activeProviderId || "claude").trim().toLowerCase() || "claude";

        function pushUnique(list) {
            list.forEach(function (cmd) {
                if (!cmd || typeof cmd !== "object") {
                    return;
                }
                var name = String(cmd.name || "").trim();
                if (!name) {
                    return;
                }
                var key = name.toLowerCase();
                if (seen[key]) {
                    return;
                }
                var providers = normalizeCommandProviders(cmd.providers);
                if (providers.indexOf(provider) === -1) {
                    return;
                }
                seen[key] = true;
                merged.push({
                    name: name,
                    icon: String(cmd.icon || "/").trim() || "/",
                    description: String(cmd.description || "").trim(),
                    providers: providers,
                });
            });
        }

        pushUnique(HOST_SLASH_COMMANDS);
        pushUnique(DEFAULT_SLASH_COMMANDS);
        return merged;
    }

    function filterSlashCommands(query) {
        var q = query.toLowerCase();
        var commands = allSlashCommands();
        if (!q || q === "/") return commands.slice();
        return commands.filter(function (cmd) {
            return cmd.name.toLowerCase().indexOf(q) === 0 ||
                   cmd.description.toLowerCase().indexOf(q.replace(/^\//, "")) !== -1;
        });
    }

    function requestSlashCommandsRefresh() {
        if (slashRefreshTimer) {
            return;
        }
        slashRefreshTimer = window.setTimeout(function () {
            slashRefreshTimer = null;
            postToHost("refreshSlashCommands", "refresh");
        }, SLASH_REFRESH_DEBOUNCE_MS);
    }

    function renderSlashDropdown(dropdownEl, items) {
        dropdownEl.innerHTML = "";
        if (!items.length) {
            var empty = document.createElement("div");
            empty.className = "slash-dropdown-empty";
            empty.textContent = "No matching commands";
            dropdownEl.appendChild(empty);
            return;
        }
        var header = document.createElement("div");
        header.className = "slash-dropdown-header";
        header.textContent = "Commands and Skills";
        dropdownEl.appendChild(header);
        items.forEach(function (cmd, idx) {
            var item = document.createElement("button");
            item.type = "button";
            item.className = "slash-dropdown-item" + (idx === slashSelectedIndex ? " selected" : "");
            item.setAttribute("role", "option");
            item.setAttribute("data-index", String(idx));

            var iconWrap = document.createElement("span");
            iconWrap.className = "slash-dropdown-icon";
            iconWrap.textContent = cmd.icon || "/";
            item.appendChild(iconWrap);

            var info = document.createElement("span");
            info.className = "slash-dropdown-info";
            var nameSpan = document.createElement("span");
            nameSpan.className = "slash-dropdown-name";
            nameSpan.textContent = cmd.name;
            info.appendChild(nameSpan);
            var descSpan = document.createElement("span");
            descSpan.className = "slash-dropdown-desc";
            descSpan.textContent = cmd.description;
            info.appendChild(descSpan);
            item.appendChild(info);

            item.addEventListener("mousedown", function (e) {
                e.preventDefault();
                selectSlashCommand(cmd);
            });
            item.addEventListener("mouseenter", function () {
                slashSelectedIndex = idx;
                updateSlashSelection(dropdownEl);
            });
            dropdownEl.appendChild(item);
        });
    }

    function updateSlashSelection(dropdownEl) {
        var items = dropdownEl.querySelectorAll(".slash-dropdown-item");
        items.forEach(function (el, i) {
            el.classList.toggle("selected", i === slashSelectedIndex);
        });
        var selected = items[slashSelectedIndex];
        if (selected) {
            selected.scrollIntoView({ block: "nearest" });
        }
    }

    function openSlashDropdown(inputEl) {
        var dropdownEl = getSlashDropdownForInput(inputEl);
        if (!dropdownEl) return;
        requestSlashCommandsRefresh();
        var text = String(inputEl.value || "");
        slashFilteredItems = filterSlashCommands(text);
        slashSelectedIndex = 0;
        activeSlashInput = inputEl;
        renderSlashDropdown(dropdownEl, slashFilteredItems);
        dropdownEl.classList.add("open");
        slashDropdownOpen = true;
    }

    function closeSlashDropdown() {
        if (welcomeSlashDropdownEl) welcomeSlashDropdownEl.classList.remove("open");
        if (chatSlashDropdownEl) chatSlashDropdownEl.classList.remove("open");
        slashDropdownOpen = false;
        slashFilteredItems = [];
        slashSelectedIndex = 0;
        activeSlashInput = null;
    }

    function updateSlashDropdown(inputEl) {
        var dropdownEl = getSlashDropdownForInput(inputEl);
        if (!dropdownEl) return;
        var text = String(inputEl.value || "");
        if (!text.startsWith("/")) {
            closeSlashDropdown();
            return;
        }
        var spaceIndex = text.indexOf(" ");
        if (spaceIndex !== -1) {
            closeSlashDropdown();
            return;
        }
        slashFilteredItems = filterSlashCommands(text);
        slashSelectedIndex = Math.min(slashSelectedIndex, Math.max(0, slashFilteredItems.length - 1));
        renderSlashDropdown(dropdownEl, slashFilteredItems);
        dropdownEl.classList.add("open");
        slashDropdownOpen = true;
        activeSlashInput = inputEl;
    }

    function selectSlashCommand(cmd) {
        var inputEl = activeSlashInput || activeInput();
        inputEl.value = cmd.name + " ";
        autoResizeInput(inputEl);
        closeSlashDropdown();
        inputEl.focus();
        inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length);
    }

    window.updateSlashCommands = function (commands) {
        if (!Array.isArray(commands)) {
            HOST_SLASH_COMMANDS = [];
            return;
        }

        HOST_SLASH_COMMANDS = commands.map(function (entry) {
            var name = String(entry && entry.name ? entry.name : "").trim();
            if (!name) {
                return null;
            }
            if (!name.startsWith("/")) {
                name = "/" + name.replace(/^\/+/, "");
            }
            return {
                name: name,
                icon: String(entry && entry.icon ? entry.icon : "S").trim() || "S",
                description: String(entry && entry.description ? entry.description : "Custom skill").trim(),
                providers: normalizeCommandProviders(entry && entry.providers),
            };
        }).filter(Boolean);

        if (slashDropdownOpen && activeSlashInput) {
            updateSlashDropdown(activeSlashInput);
        }
    };

    function attachInputBehavior(inputEl) {
        inputEl.addEventListener("keydown", function (event) {
            if (slashDropdownOpen && activeSlashInput === inputEl) {
                if (event.key === "ArrowDown") {
                    event.preventDefault();
                    if (slashFilteredItems.length > 0) {
                        slashSelectedIndex = (slashSelectedIndex + 1) % slashFilteredItems.length;
                        var dd = getSlashDropdownForInput(inputEl);
                        if (dd) updateSlashSelection(dd);
                    }
                    return;
                }
                if (event.key === "ArrowUp") {
                    event.preventDefault();
                    if (slashFilteredItems.length > 0) {
                        slashSelectedIndex = (slashSelectedIndex - 1 + slashFilteredItems.length) % slashFilteredItems.length;
                        var dd = getSlashDropdownForInput(inputEl);
                        if (dd) updateSlashSelection(dd);
                    }
                    return;
                }
                if (event.key === "Enter" || event.key === "Tab") {
                    if (slashFilteredItems.length > 0) {
                        event.preventDefault();
                        selectSlashCommand(slashFilteredItems[slashSelectedIndex]);
                        return;
                    }
                }
                if (event.key === "Escape") {
                    event.preventDefault();
                    closeSlashDropdown();
                    return;
                }
            }
            if (event.key === "ArrowUp" && !inputEl.value.trim() && lastUserPrompt) {
                event.preventDefault();
                inputEl.value = lastUserPrompt;
                autoResizeInput(inputEl);
                inputEl.focus();
                inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length);
                return;
            }
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendInput(inputEl);
            }
        });

        inputEl.addEventListener("input", function () {
            autoResizeInput(inputEl);
            var text = String(inputEl.value || "");
            if (text.startsWith("/") && text.indexOf(" ") === -1) {
                if (!slashDropdownOpen || activeSlashInput !== inputEl) {
                    openSlashDropdown(inputEl);
                } else {
                    updateSlashDropdown(inputEl);
                }
            } else {
                if (slashDropdownOpen && activeSlashInput === inputEl) {
                    closeSlashDropdown();
                }
            }
        });

        inputEl.addEventListener("paste", function (event) {
            const clipboard = event.clipboardData;
            const imageFiles = extractClipboardImageFiles(clipboard);
            if (imageFiles.length) {
                event.preventDefault();
                addFilesFromList(imageFiles);
                return;
            }

            if (navigator.clipboard && typeof navigator.clipboard.read === "function") {
                navigator.clipboard.read().then(function (items) {
                    if (!Array.isArray(items)) {
                        return;
                    }
                    items.forEach(function (item, itemIndex) {
                        const imageType = (item.types || []).find(function (type) {
                            return String(type || "").indexOf("image/") === 0;
                        });
                        if (!imageType) {
                            return;
                        }
                        item.getType(imageType).then(function (blob) {
                            if (!blob) {
                                return;
                            }
                            const extension = imageType.split("/")[1] || "png";
                            const name = "pasted-image-" + Date.now() + "-" + itemIndex + "." + extension;
                            const file = new File([blob], name, { type: imageType });
                            fileToAttachment(file).then(addAttachment).catch(function () {});
                        }).catch(function () {});
                    });
                }).catch(function () {});
            }
        });

        inputEl.addEventListener("blur", function () {
            window.setTimeout(function () {
                if (activeSlashInput === inputEl) {
                    closeSlashDropdown();
                }
            }, 150);
        });

        autoResizeInput(inputEl);
    }

    modelButtons.forEach(function (button, index) {
        button.addEventListener("click", function (event) {
            event.stopPropagation();
            const popup = modelPopups[index];
            if (!popup) {
                return;
            }

            const alreadyOpen = popup.classList.contains("open") && activePopup === popup;
            if (alreadyOpen) {
                closePopup(popup, false);
                return;
            }

            openPopup(button, popup, "model");
        });
    });

    reasoningButtons.forEach(function (button, index) {
        button.addEventListener("click", function (event) {
            event.stopPropagation();
            var popup = reasoningPopups[index];
            if (!popup) {
                return;
            }

            var alreadyOpen = popup.classList.contains("open") && activePopup === popup;
            if (alreadyOpen) {
                closePopup(popup, false);
                return;
            }

            openPopup(button, popup, "reasoning");
        });
    });

    permissionButtons.forEach(function (button, index) {
        button.addEventListener("click", function (event) {
            event.stopPropagation();
            const popup = permissionPopups[index];
            if (!popup) {
                return;
            }

            const alreadyOpen = popup.classList.contains("open") && activePopup === popup;
            if (alreadyOpen) {
                closePopup(popup, false);
                return;
            }

            openPopup(button, popup, "permission");
        });
    });

    plusButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            postToHost(
                "attachFile",
                JSON.stringify({ action: "attach_file", source: "plus_button" }),
                ["attach_file", "openFile", "open_file"],
            );
        });
    });

    if (stopBtnEl) {
        stopBtnEl.addEventListener("click", function () {
            postToHost("stopProcess", "stop");
            setAssistantPhase(ASSISTANT_PHASE.DONE);
        });
    }

    folderPathButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            postToHost(
                "changeFolder",
                JSON.stringify({ action: "change_folder", source: "folder_button" }),
                ["change_folder", "openFolder", "open_folder"],
            );
        });
    });

    quickChips.forEach(function (chip) {
        chip.addEventListener("click", function () {
            const value = chip.getAttribute("data-value") || "";
            setComposerPromptValue(value);
        });
    });

    if (artifactsToggleBtnEl) {
        artifactsToggleBtnEl.addEventListener("click", function () {
            toggleArtifactsPanel();
        });
    }

    agentModeToggleButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            toggleAgentMode();
        });
    });

    if (artifactsCloseBtnEl) {
        artifactsCloseBtnEl.addEventListener("click", function () {
            setArtifactsPanelOpen(false);
        });
    }

    if (artifactVersionSelectEl) {
        artifactVersionSelectEl.addEventListener("change", function () {
            const version = Number(artifactVersionSelectEl.value || 0);
            if (selectedArtifactId) {
                selectArtifact(selectedArtifactId, version);
            }
        });
    }

    if (artifactCopyBtnEl) {
        artifactCopyBtnEl.addEventListener("click", function () {
            const artifact = findArtifactById(selectedArtifactId);
            if (!artifact) {
                return;
            }
            const versionEntry = getArtifactVersionEntry(artifact, selectedArtifactVersion);
            if (!versionEntry) {
                return;
            }
            copyText(versionEntry.content, function () {
                const previous = artifactCopyBtnEl.textContent;
                artifactCopyBtnEl.textContent = "Copied";
                window.setTimeout(function () {
                    artifactCopyBtnEl.textContent = previous;
                }, 900);
            });
        });
    }

    if (artifactDownloadBtnEl) {
        artifactDownloadBtnEl.addEventListener("click", function () {
            downloadArtifactContent();
        });
    }

    if (artifactOpenTabBtnEl) {
        artifactOpenTabBtnEl.addEventListener("click", function () {
            openArtifactInNewTab();
        });
    }

    if (lightboxCloseBtnEl) {
        lightboxCloseBtnEl.addEventListener("click", function () {
            closeImageLightbox();
        });
    }

    if (imageLightboxEl) {
        imageLightboxEl.addEventListener("click", function (event) {
            if (event.target === imageLightboxEl) {
                closeImageLightbox();
            }
        });
    }

    if (messagesEl) {
        messagesEl.addEventListener("scroll", function () {
            updateUserScrolledState();
        }, { passive: true });
    }

    if (scrollToBottomBtnEl) {
        scrollToBottomBtnEl.addEventListener("click", function () {
            scrollToBottom(true, true);
        });
    }

    if (chatSearchInputEl) {
        chatSearchInputEl.addEventListener("input", function () {
            const query = String(chatSearchInputEl.value || "").trim();
            if (!query) {
                closeChatSearch();
                return;
            }
            scheduleChatSearch();
        });

        chatSearchInputEl.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                closeChatSearch();
                return;
            }
            if (event.key === "Enter") {
                event.preventDefault();
                event.stopPropagation();
                if (event.shiftKey) {
                    goToPreviousChatSearchMatch();
                } else {
                    goToNextChatSearchMatch();
                }
            }
        });
    }

    if (chatSearchPrevEl) {
        chatSearchPrevEl.addEventListener("click", function () {
            goToPreviousChatSearchMatch();
        });
    }

    if (chatSearchNextEl) {
        chatSearchNextEl.addEventListener("click", function () {
            goToNextChatSearchMatch();
        });
    }

    if (chatSearchCloseEl) {
        chatSearchCloseEl.addEventListener("click", function () {
            closeChatSearch();
        });
    }

    document.addEventListener("dragenter", function (event) {
        const hasFiles = event.dataTransfer && Array.from(event.dataTransfer.types || []).indexOf("Files") >= 0;
        if (!hasFiles) {
            return;
        }
        dragDepth += 1;
        event.preventDefault();
        if (dropOverlayEl) {
            dropOverlayEl.classList.add("active");
        }
    });

    document.addEventListener("dragover", function (event) {
        const hasFiles = event.dataTransfer && Array.from(event.dataTransfer.types || []).indexOf("Files") >= 0;
        if (!hasFiles) {
            return;
        }
        event.preventDefault();
        if (dropOverlayEl) {
            dropOverlayEl.classList.add("active");
        }
    });

    document.addEventListener("dragleave", function (event) {
        const hasFiles = event.dataTransfer && Array.from(event.dataTransfer.types || []).indexOf("Files") >= 0;
        if (!hasFiles) {
            return;
        }
        event.preventDefault();
        dragDepth = Math.max(0, dragDepth - 1);
        if (dragDepth === 0 && dropOverlayEl) {
            dropOverlayEl.classList.remove("active");
        }
    });

    document.addEventListener("drop", function (event) {
        const hasFiles = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files.length > 0;
        if (!hasFiles) {
            return;
        }
        event.preventDefault();
        dragDepth = 0;
        if (dropOverlayEl) {
            dropOverlayEl.classList.remove("active");
        }
        addFilesFromList(event.dataTransfer.files);
    });

    document.addEventListener("click", function (event) {
        const searchAction = event.target.closest('[data-action="search-chat"]');
        if (searchAction) {
            event.preventDefault();
            openChatSearch();
            return;
        }

        const imageEl = event.target.closest(".chat-image, .message-attachment-image");
        if (imageEl) {
            const safeSrc = sanitizeImageUrl(imageEl.getAttribute("src"));
            if (safeSrc) {
                openImageLightbox(safeSrc, imageEl.getAttribute("alt"));
            }
            return;
        }

        const ciprLink = event.target.closest(".cipr-link");
        if (ciprLink) {
            const href = String(ciprLink.getAttribute("href") || "").trim();
            if (/^https?:\/\//i.test(href)) {
                event.preventDefault();
                window.open(href, "_blank", "noopener,noreferrer");
            }
            return;
        }

        const codeCopyButton = event.target.closest(".code-copy-btn");
        if (codeCopyButton) {
            const encoded = codeCopyButton.getAttribute("data-raw") || "";
            const raw = safeDecodeURIComponent(encoded);

            copyText(raw, function () {
                showCopiedFeedback(codeCopyButton);
            });
            return;
        }

        const toolDiffCopyButton = event.target.closest(".tool-copy-diff-btn");
        if (toolDiffCopyButton) {
            const encoded = toolDiffCopyButton.getAttribute("data-diff-raw") || "";
            const rawDiff = safeDecodeURIComponent(encoded);
            copyText(rawDiff, function () {
                const previous = toolDiffCopyButton.textContent;
                toolDiffCopyButton.textContent = "Copied";
                window.setTimeout(function () {
                    toolDiffCopyButton.textContent = previous;
                }, 900);
            });
            return;
        }

        const diffSummaryFileButton = event.target.closest(".diff-summary-file");
        if (diffSummaryFileButton) {
            const targetCardId = String(diffSummaryFileButton.getAttribute("data-target-card") || "");
            const targetCard = targetCardId ? document.getElementById(targetCardId) : null;
            if (targetCard) {
                targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
                targetCard.classList.add("tool-card-highlight");
                window.setTimeout(function () {
                    targetCard.classList.remove("tool-card-highlight");
                }, 1200);

                if (targetCard.tagName === "DETAILS" && !targetCard.open) {
                    targetCard.open = true;
                }
            }
            return;
        }

        const userActionButton = event.target.closest(".user-action");
        if (userActionButton) {
            const action = userActionButton.getAttribute("data-action");
            const bubble = userActionButton.closest(".user-bubble-wrap")
                ? userActionButton.closest(".user-bubble-wrap").querySelector(".user-bubble")
                : null;
            const rawMarkdown = bubble
                ? (bubble.dataset.rawMarkdown || bubble.textContent || "")
                : "";

            if (action === "copy-md") {
                copyMarkdownText(rawMarkdown, function () {
                    showCopySuccessBadge(userActionButton);
                });
                return;
            }

            if (action === "copy") {
                copyText(rawMarkdown, function () {
                    markActionPressed(userActionButton);
                });
                return;
            }
        }

        const actionButton = event.target.closest(".assistant-action");
        if (actionButton) {
            const action = actionButton.getAttribute("data-action");
            const messageBody = actionButton.closest(".assistant-content-wrap")
                ? actionButton.closest(".assistant-content-wrap").querySelector(".assistant-message")
                : null;
            const raw = messageBody ? (messageBody.dataset.raw || messageBody.textContent || "") : "";
            const rawMarkdown = messageBody
                ? (messageBody.dataset.rawMarkdown || messageBody.dataset.raw || messageBody.textContent || "")
                : "";

            if (action === "copy") {
                copyText(raw, function () {
                    markActionPressed(actionButton);
                });
                return;
            }

            if (action === "copy-md") {
                copyMarkdownText(rawMarkdown, function () {
                    showCopySuccessBadge(actionButton);
                });
                return;
            }

            if (action === "retry") {
                if (lastUserPayload) {
                    sendPayload(lastUserPayload);
                }
                markActionPressed(actionButton);
                return;
            }

            markActionPressed(actionButton);
            return;
        }

        if (!event.target.closest(".selector-group")) {
            closeActivePopup(false);
        }
        if (slashDropdownOpen && !event.target.closest(".slash-dropdown") && !event.target.closest(".composer-input")) {
            closeSlashDropdown();
        }
    });

    document.addEventListener("keydown", function (event) {
        const findShortcut = (event.ctrlKey || event.metaKey) && !event.altKey && String(event.key || "").toLowerCase() === "f";
        if (findShortcut && hasMessages) {
            event.preventDefault();
            toggleChatSearch();
            return;
        }

        if (event.key === "Escape") {
            if (chatSearchOpen) {
                closeChatSearch();
                return;
            }
            if (slashDropdownOpen) {
                closeSlashDropdown();
                return;
            }
            if (imageLightboxEl && imageLightboxEl.classList.contains("open")) {
                closeImageLightbox();
                return;
            }
            if (artifactsPanelOpen) {
                setArtifactsPanelOpen(false);
                return;
            }
            closeActivePopup(false);
        }
    });

    attachInputBehavior(welcomeInputEl);
    attachInputBehavior(chatInputEl);

    window.handleWindowKeyUp = function () {
        const inputEl = activeInput();
        if (inputEl && !inputEl.value.trim() && lastUserPrompt) {
            inputEl.value = lastUserPrompt;
            autoResizeInput(inputEl);
            inputEl.focus();
            inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length);
        }
    };

    window.addUserMessage = addUserMessage;
    window.addAssistantMessage = addAssistantMessage;
    window.startAssistantMessage = startAssistantMessage;
    window.externalFileDropped = function (path) {
        if (!path) return;
        postToHost("attachFile", { path: path });
    };

    window.appendAssistantChunk = appendAssistantChunk;
    window.finishAssistantMessage = finishAssistantMessage;
    window.addSystemMessage = addSystemMessage;
    window.addPermissionRequest = addPermissionRequest;
    window.setTyping = setTyping;
    window.clearMessages = clearMessages;
    window.showWelcome = showWelcome;
    window.addHostAttachment = function (attachments) {
        if (Array.isArray(attachments)) {
            attachments.forEach(addAttachment);
            return;
        }
        addAttachment(attachments);
    };
    window.registerArtifact = function (artifact) {
        return registerArtifact(artifact);
    };
    window.openArtifactsPanel = function (artifactId, version) {
        setArtifactsPanelOpen(true);
        if (artifactId) {
            selectArtifact(artifactId, version || 0);
        }
    };
    window.openChatSearch = openChatSearch;
    window.closeChatSearch = closeChatSearch;

    window.applyProviderTheme = function (colorsJson) {
        const colors = parseHostPayload(colorsJson);
        if (!colors || typeof colors !== "object") {
            return;
        }
        Object.keys(colors).forEach(function (key) {
            const value = String(colors[key] == null ? "" : colors[key]).trim();
            if (!value) {
                return;
            }
            document.documentElement.style.setProperty("--" + key, value);
        });
    };

    window.setModelOptions = function (optionsJson) {
        const nextOptions = toModelOptions(optionsJson);
        if (nextOptions.length === 0) {
            return;
        }
        MODEL_OPTIONS = nextOptions;
        selectedModel = normalizeModelValue(selectedModel);
        renderSelectorLabels();
    };

    window.setPermissionOptions = function (optionsJson) {
        const nextOptions = toPermissionOptions(optionsJson);
        if (nextOptions.length === 0) {
            return;
        }
        PERMISSION_OPTIONS = nextOptions;
        selectedPermission = normalizePermissionValue(selectedPermission);
    };

    window.setAgentModeEnabled = function (isEnabled) {
        setAgentModeEnabled(!!isEnabled);
    };
    window.setPaneMode = function (mode) {
        setPaneMode(mode);
    };
    window.setStreamRenderThrottleMs = function (value) {
        streamRenderThrottleMs = normalizeStreamRenderThrottle(value);
        if (pendingAssistantText) {
            stopAssistantRevealTimer();
            flushPendingAssistantText(false);
        }
    };

    window.setReasoningOptions = function (optionsJson) {
        const nextOptions = toReasoningOptions(optionsJson);
        if (nextOptions.length === 0) {
            return;
        }
        REASONING_OPTIONS = nextOptions;
        selectedReasoning = normalizeReasoningValue(selectedReasoning);
        renderSelectorLabels();
    };

    window.setProviderBranding = function (payload) {
        const data = parseHostPayload(payload);
        if (!data || typeof data !== "object") {
            return;
        }
        activeProviderId = String(data.id || activeProviderId).trim().toLowerCase() || activeProviderId;
        activeProviderName = String(data.name || activeProviderName).trim() || activeProviderName;
        const welcomeTitle = String(data.welcomeTitle || (activeProviderName + " is ready"));
        const iconUrl = String(data.iconUrl || "").trim();
        if (welcomeTitleEl) {
            welcomeTitleEl.textContent = welcomeTitle;
        }
        if (welcomeScreenIconEl) {
            if (iconUrl) {
                welcomeScreenIconEl.src = iconUrl;
                welcomeScreenIconEl.setAttribute("aria-label", activeProviderName + " logo");
            } else {
                welcomeScreenIconEl.removeAttribute("src");
            }
            welcomeScreenIconEl.hidden = !iconUrl;
        }
        if (welcomeProviderIconEl) {
            if (iconUrl) {
                welcomeProviderIconEl.src = iconUrl;
                welcomeProviderIconEl.setAttribute("aria-label", activeProviderName + " logo");
                welcomeProviderIconEl.classList.add("visible");
            } else {
                welcomeProviderIconEl.removeAttribute("src");
                welcomeProviderIconEl.classList.remove("visible");
            }
            welcomeProviderIconEl.hidden = !iconUrl;
        }
        if (welcomeProviderNameEl) {
            welcomeProviderNameEl.textContent = activeProviderName;
        } else if (welcomeProviderBadgeEl) {
            welcomeProviderBadgeEl.textContent = activeProviderName;
        }
        Array.from(document.querySelectorAll(".ci-fix-btn")).forEach(function (button) {
            button.textContent = activeProviderName + " can try to fix this";
        });
        renderExamplePrompts();
        if (slashDropdownOpen && activeSlashInput) {
            updateSlashDropdown(activeSlashInput);
        }
    };

    window.setReasoningVisible = function (isVisible) {
        setReasoningVisible(!!isVisible);
    };

    window.updateReasoningLevel = function (value) {
        selectedReasoning = normalizeReasoningValue(value);
        renderSelectorLabels();
    };

    window.updateModel = function (modelValue) {
        selectedModel = normalizeModelValue(modelValue);
        renderSelectorLabels();
    };

    window.updatePermission = function (permissionValue) {
        selectedPermission = normalizePermissionValue(permissionValue);
    };
    window.setProcessing = function (isProcessing) {
        if (isProcessing) {
            processingActive = true;
            clearLongWaitStatusInternal({ immediate: true });
            resetLongWaitStatusTimers();
            if (assistantPhase === ASSISTANT_PHASE.IDLE || assistantPhase === ASSISTANT_PHASE.DONE || assistantPhase === ASSISTANT_PHASE.ERROR) {
                setAssistantPhase(ASSISTANT_PHASE.SENDING);
            }
            return;
        }
        processingActive = false;
        clearLongWaitStatusAndTimers(true);
        if (assistantPhase !== ASSISTANT_PHASE.STREAMING) {
            setAssistantPhase(ASSISTANT_PHASE.DONE);
        }
    };
    window.updateLongWaitStatus = function (text) {
        noteWaitActivity();
        stopWaitRotateTimer();
        scheduleWaitInactivityTimer();
        applyLongWaitStatus(text, {
            immediate: false,
            source: "external",
        });
    };
    window.clearLongWaitStatus = function () {
        clearLongWaitStatusInternal({ immediate: true });
        scheduleWaitInactivityTimer();
    };
    window.focusInput = function () {
        if (hasMessages || isAgentPaneMode()) {
            chatInputEl.focus();
        } else {
            welcomeInputEl.focus();
        }
    };
    window.hostSendMessage = function (textValue) {
        sendPayload({
            text: String(textValue || "").trim(),
            attachments: [],
        });
    };
    window.updateFolder = function (pathValue) {
        updateFolderDisplay(pathValue);
    };
    wireGlassButtons();

    resetToolTurnState();
    setChatState(false);
    setReasoningVisible(true);
    renderSelectorLabels();
    updateFolderDisplay("~");
    renderExamplePrompts();
    renderAttachments();
    renderArtifactsList();
    renderArtifactDetail();
    updateArtifactsToggleButton();
    setArtifactsPanelOpen(false);
})();
</script>
</body>
</html>
"""
    .replace("__INLINE_HIGHLIGHT_CSS__", HIGHLIGHT_CSS)
    .replace("__INLINE_HIGHLIGHT_JS__", HIGHLIGHT_JS)
    .replace("__INLINE_MOTION_ONE_JS__", MOTION_ONE_JS)
    .replace("__GLASS_STYLE_SNIPPET__", GLASS_STYLE_SNIPPET)
)
