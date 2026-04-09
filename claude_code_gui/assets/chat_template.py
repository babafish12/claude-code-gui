"""WebView HTML/CSS/JS payload for the chat UI."""

from __future__ import annotations

CHAT_WEBVIEW_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/atom-one-dark.min.css" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>
<style>
:root {
    --bg: #2f2f2a;
    --sidebar: #292923;
    --input-bg: #3a3a34;
    --input-border: #4a4a43;
    --input-focus: #5a5a50;
    --user-bubble: #3a3a35;
    --text: #d4d4c8;
    --muted: #8a8a7a;
    --accent: #d97757;
    --accent-soft: rgba(217, 119, 87, 0.18);
    --chip-border: #4a4a43;
    --code-bg: #1a1a16;
    --artifacts-panel-bg: #2a2a25;
    --artifacts-panel-width: 360px;
    --shadow: 0 12px 36px rgba(0, 0, 0, 0.34);
    --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", "Twemoji Mozilla", sans-serif;
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
        radial-gradient(circle at 14% 4%, rgba(212, 132, 90, 0.12), transparent 30%),
        radial-gradient(circle at 85% 96%, rgba(212, 132, 90, 0.08), transparent 26%),
        var(--bg);
    color: var(--text);
    font-family: var(--font-stack);
    overflow: hidden;
}

a {
    color: #D97757;
    text-decoration: none;
    transition: all 0.15s ease;
}

a:hover {
    text-decoration: underline;
}

#app {
    position: relative;
    width: 100%;
    height: 100%;
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
    color: var(--accent);
}

.welcome-title {
    margin: 0;
    color: var(--text);
    font-size: 28px;
    font-weight: 500;
    letter-spacing: 0.1px;
}

.composer-card {
    width: 100%;
    max-width: 740px;
    border-radius: 24px;
    border: 1px solid var(--input-border);
    background: rgba(58, 58, 52, 0.92);
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
    transition: all 0.15s ease;
}

.composer-input::placeholder {
    color: var(--muted);
}

.composer-input:focus {
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
    color: #8a8a7a;
    border-radius: 10px;
    padding: 4px 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    transition: all 0.15s ease;
}

.folder-path-btn:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #b7b29a;
}

.folder-path-icon {
    flex: none;
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
}

.attachment-strip.has-items {
    display: flex;
}

.attachment-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border-radius: 999px;
    border: 1px solid var(--chip-border);
    background: rgba(58, 58, 52, 0.9);
    padding: 3px 10px 3px 5px;
    font-size: 12px;
    max-width: 280px;
    transition: all 0.15s ease;
}

.attachment-chip:hover {
    border-color: rgba(212, 132, 90, 0.72);
}

.attachment-thumb {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    object-fit: cover;
    border: 1px solid var(--chip-border);
}

.attachment-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.attachment-remove {
    border: none;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    padding: 0;
    transition: all 0.15s ease;
}

.attachment-remove:hover {
    color: #f0c1a6;
}

.plus-btn,
.selector-btn,
.permission-btn,
.action-btn,
.assistant-action,
.chip {
    border: 1px solid var(--chip-border);
    background: transparent;
    color: var(--text);
    transition: all 0.15s ease;
}

.plus-btn {
    width: 30px;
    height: 30px;
    border-radius: 999px;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
}

.plus-btn:hover,
.selector-btn:hover,
.permission-btn:hover,
.chip:hover,
.assistant-action:hover,
.action-btn:hover {
    background-color: rgba(212, 132, 90, 0.12);
    border-color: rgba(212, 132, 90, 0.72);
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
    width: 280px;
    border-radius: 16px;
    border: 1px solid var(--input-border);
    background: #3a3a34;
    box-shadow: 0 18px 34px rgba(0, 0, 0, 0.34);
    padding: 6px;
    opacity: 0;
    transform: translateY(10px);
    pointer-events: none;
    transition: all 0.15s ease;
    z-index: 40;
}

.popup-menu.open {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
}

.popup-menu.closing {
    opacity: 0;
    transform: translateY(10px);
    pointer-events: none;
    transition: all 0.15s ease;
}

.popup-option {
    width: 100%;
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    color: var(--text);
    text-align: left;
    padding: 10px 10px;
    cursor: pointer;
    transition: all 0.15s ease;
}

.popup-option + .popup-option {
    margin-top: 4px;
}

.popup-option:hover {
    background: rgba(255, 255, 255, 0.06);
}

.popup-option.active {
    background: rgba(212, 132, 90, 0.13);
    border-color: rgba(212, 132, 90, 0.55);
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

#artifactsToggleBtn {
    border: 1px solid var(--chip-border);
    background: rgba(42, 42, 37, 0.9);
    color: var(--text);
    border-radius: 999px;
    min-height: 30px;
    padding: 0 12px;
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    transition: all 0.15s ease;
}

#artifactsToggleBtn:hover,
#artifactsToggleBtn.active {
    border-color: rgba(212, 132, 90, 0.72);
    background: rgba(212, 132, 90, 0.14);
}

#dropOverlay {
    position: absolute;
    inset: 18px 14px 118px;
    border-radius: 18px;
    border: 2px dashed rgba(217, 119, 87, 0.75);
    background: rgba(26, 26, 22, 0.78);
    color: #f0c1a6;
    display: none;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 600;
    z-index: 55;
    pointer-events: none;
    transition: all 0.15s ease;
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
    transition: padding-right 250ms ease;
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
    animation: messageReveal 300ms ease-out;
}

@keyframes messageReveal {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
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

.user-bubble {
    max-width: min(90%, 640px);
    border-radius: 18px;
    background: var(--user-bubble);
    padding: 12px 18px;
    color: var(--text);
    white-space: pre-wrap;
    line-height: 1.45;
    word-break: break-word;
}

.user-bubble-text {
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
    border: 1px solid #4a4a43;
    object-fit: contain;
    background: rgba(26, 26, 22, 0.5);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.26);
    cursor: pointer;
    transition: transform 0.15s ease, filter 0.15s ease;
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
    border: 1px solid #4a4a43;
    background: rgba(26, 26, 22, 0.65);
    padding: 6px 9px;
    font-size: 12px;
}

.assistant-block {
    display: block;
}

.assistant-content-wrap {
    min-width: 0;
}

.sparkle-small {
    width: 20px;
    height: 20px;
    color: var(--accent);
    margin: 0 0 8px;
    display: block;
}

.assistant-message {
    color: var(--text);
    line-height: 1.5;
    word-break: break-word;
    font-size: 1rem;
}

.user-bubble,
.assistant-message,
.system-pill,
.composer-input {
    font-family: var(--font-stack);
}

.assistant-actions {
    margin-top: 8px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    opacity: 0;
}

.message-row.assistant:hover .assistant-actions {
    opacity: 1;
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

.assistant-action.active {
    border-color: rgba(212, 132, 90, 0.9);
    color: #f0c1a6;
}

.message-row.system .message-inner {
    display: flex;
    justify-content: center;
}

.system-pill {
    border-radius: 999px;
    border: 1px solid var(--chip-border);
    background: rgba(58, 58, 52, 0.7);
    color: var(--muted);
    font-size: 12px;
    padding: 6px 12px;
}

.message-row.tool .message-inner {
    display: flex;
    justify-content: flex-start;
}

.message-row.tool-summary .message-inner {
    display: flex;
    justify-content: flex-start;
}

.tool-card {
    width: 100%;
    max-width: 768px;
    border-radius: 10px;
    transition: box-shadow 0.2s ease;
}

.tool-card.tool-card-highlight {
    box-shadow: 0 0 0 1px rgba(217, 119, 87, 0.72), 0 0 18px rgba(217, 119, 87, 0.2);
}

.tool-header {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--muted);
    font-size: 12px;
    cursor: pointer;
    padding: 3px 0;
    transition: color 0.15s ease;
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
    transition: transform 0.2s ease;
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
    animation: toolReveal 200ms ease-out;
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
    background: linear-gradient(180deg, rgba(41, 41, 36, 0.98), rgba(30, 30, 25, 0.95));
    padding: 10px;
}

.tool-summary-title {
    font-size: 12px;
    color: #d2cec0;
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
    border: 1px solid #4a4a43;
    border-radius: 8px;
    background: rgba(24, 24, 20, 0.7);
    color: var(--text);
    padding: 6px 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    font-size: 11px;
    transition: all 0.15s ease;
}

.diff-summary-file:hover {
    border-color: rgba(217, 119, 87, 0.72);
    background: rgba(217, 119, 87, 0.11);
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
    border-top: 1px solid #4a4a43;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    color: #b7b29a;
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
    border: 1px solid rgba(217, 119, 87, 0.55);
    border-left: 3px solid #d97757;
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
    transition: color 0.15s ease, text-decoration-color 0.15s ease;
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
    transition: all 0.15s ease;
}

.ci-fix-btn:hover {
    background: rgba(153, 60, 55, 0.52);
}

.pr-ci-slot {
    margin-top: 8px;
}

.artifact-indicator {
    margin-top: 8px;
    border: 1px solid rgba(212, 132, 90, 0.5);
    background: var(--accent-soft);
    color: #f0c1a6;
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 11px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
}

.artifact-indicator:hover {
    border-color: rgba(212, 132, 90, 0.8);
    background: rgba(212, 132, 90, 0.24);
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
    border-left: 1px solid #3f3f38;
    background:
        radial-gradient(circle at 12% 8%, rgba(217, 119, 87, 0.08), transparent 38%),
        var(--artifacts-panel-bg);
    transform: translateX(100%);
    transition: transform 250ms ease;
    z-index: 50;
    pointer-events: none;
    display: flex;
    flex-direction: column;
}

.artifacts-panel-header {
    flex: none;
    min-height: 44px;
    padding: 10px 12px;
    border-bottom: 1px solid #3f3f38;
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
    transition: all 0.15s ease;
}

.artifacts-close-btn:hover {
    color: var(--text);
    border-color: rgba(212, 132, 90, 0.72);
    background: rgba(212, 132, 90, 0.1);
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
    border-bottom: 1px solid #3f3f38;
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
    transition: all 0.15s ease;
}

.artifact-row + .artifact-row {
    margin-top: 4px;
}

.artifact-row:hover {
    background: rgba(255, 255, 255, 0.04);
}

.artifact-row.selected {
    border-color: rgba(212, 132, 90, 0.72);
    box-shadow: inset 2px 0 0 rgba(212, 132, 90, 0.9);
    background: rgba(212, 132, 90, 0.09);
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
    border: 1px solid #4c4c45;
    background: rgba(58, 58, 52, 0.66);
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
    border: 1px solid #4c4c45;
    background: rgba(58, 58, 52, 0.66);
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 10px;
    color: #bcb7a4;
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
    transition: all 0.15s ease;
}

.artifact-action-btn:hover {
    border-color: rgba(212, 132, 90, 0.72);
    background: rgba(212, 132, 90, 0.1);
}

.artifact-detail-code {
    min-height: 0;
    flex: 1;
    border-radius: 10px;
    border: 1px solid #43433c;
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
    border: 1px solid rgba(217, 131, 64, 0.75);
    background:
        linear-gradient(135deg, rgba(72, 56, 36, 0.66), rgba(47, 47, 42, 0.96)),
        #2f2f2a;
    box-shadow:
        0 0 0 1px rgba(217, 131, 64, 0.16),
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
            0 0 0 1px rgba(217, 131, 64, 0.16),
            0 10px 28px rgba(0, 0, 0, 0.24);
    }
    50% {
        box-shadow:
            0 0 0 1px rgba(217, 131, 64, 0.34),
            0 10px 30px rgba(0, 0, 0, 0.24),
            0 0 18px rgba(217, 131, 64, 0.2);
    }
    100% {
        box-shadow:
            0 0 0 1px rgba(217, 131, 64, 0.16),
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
    background: rgba(217, 131, 64, 0.18);
    color: #f8c16d;
    font-size: 13px;
}

.permission-request-title {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.permission-request-tool {
    color: #f7d9b0;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.2px;
}

.permission-request-subtitle {
    color: #c8b9a0;
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
    color: #c3a882;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.35px;
    margin-bottom: 2px;
}

.permission-meta-value {
    color: #e4ddd0;
    font-size: 12px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    word-break: break-word;
}

.permission-preview {
    border-radius: 8px;
    border: 1px solid rgba(217, 131, 64, 0.28);
    background: rgba(20, 20, 16, 0.5);
    overflow: hidden;
    font-size: 11px;
    margin-bottom: 10px;
}

.permission-preview .tool-diff-old,
.permission-preview .tool-diff-new,
.permission-preview .tool-code {
    border-bottom: 1px solid rgba(217, 131, 64, 0.16);
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
    border: 1px solid rgba(110, 110, 100, 0.85);
    border-radius: 8px;
    background: rgba(56, 56, 50, 0.9);
    color: #ddd6c9;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s ease;
}

.permission-action-btn:hover {
    border-color: rgba(217, 131, 64, 0.72);
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
    border: 1px solid rgba(110, 110, 100, 0.85);
    border-radius: 8px;
    background: rgba(30, 30, 25, 0.7);
    color: var(--text);
    font-size: 12px;
    padding: 6px 8px;
}

.permission-comment-input:focus {
    outline: none;
    border-color: rgba(217, 131, 64, 0.78);
    box-shadow: 0 0 0 1px rgba(217, 131, 64, 0.34);
}

.permission-response-status {
    margin-top: 9px;
    color: #d6c6ad;
    font-size: 11px;
}

.permission-request-card.resolved .permission-action-btn,
.permission-request-card.resolved .permission-comment-input {
    cursor: default;
    opacity: 0.62;
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
    color: #D97757;
    transition: all 0.15s ease;
}

.markdown-body a:hover {
    text-decoration: underline;
}

.markdown-body blockquote {
    margin: 0 0 0.8em;
    padding: 0.45em 0.9em;
    border-left: 3px solid #D97757;
    background: rgba(26, 26, 22, 0.7);
    border-radius: 8px;
    font-style: italic;
}

.markdown-body code.inline-code {
    border-radius: 4px;
    border: none;
    background: #3a3a34;
    padding: 2px 6px;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 0.92em;
}

.markdown-body table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 0.8em;
    border: 1px solid #4a4a43;
    border-radius: 8px;
    overflow: hidden;
}

.markdown-body th,
.markdown-body td {
    border: 1px solid #4a4a43;
    padding: 6px 8px;
    text-align: left;
}

.markdown-body th {
    background: rgba(58, 58, 52, 0.8);
}

.markdown-body hr {
    border: none;
    border-top: 1px solid #4a4a43;
    margin: 0.9em 0;
}

.code-block {
    margin: 0 0 0.85em;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #4a4a43;
    background: var(--code-bg);
}

.code-head {
    height: 34px;
    padding: 0 10px;
    border-bottom: 1px solid #4a4a43;
    background: #21211c;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #aea892;
    font-size: 12px;
}

.action-btn {
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11px;
    cursor: pointer;
}

.code-block pre {
    margin: 0;
    padding: 12px;
    overflow-x: auto;
    font-family: "JetBrains Mono", "SFMono-Regular", "Consolas", monospace;
    font-size: 13px;
    line-height: 1.45;
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
.hljs-tag { color: #e06c75; }

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
    transition: all 0.15s ease;
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

.typing-shell .sparkle-small {
    margin: 0;
}

.sparkle-pulse {
    animation: sparkle-pulse 1.3s ease-in-out infinite;
    filter: drop-shadow(0 0 10px rgba(217, 119, 87, 0.6));
}

@keyframes sparkle-pulse {
    0%, 100% {
        transform: scale(1) rotate(0deg);
        filter: drop-shadow(0 0 8px rgba(217, 119, 87, 0.55));
    }
    33% {
        transform: scale(1.18) rotate(12deg);
        filter: drop-shadow(0 0 20px rgba(240, 193, 166, 0.85));
    }
    66% {
        transform: scale(1.05) rotate(-6deg);
        filter: drop-shadow(0 0 14px rgba(217, 150, 110, 0.7));
    }
}

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

.stop-process-btn {
    display: block;
    margin: 0 auto 10px;
    border: 1px solid rgba(220, 80, 60, 0.4);
    background: rgba(220, 80, 60, 0.12);
    color: #e07a6a;
    border-radius: 999px;
    padding: 5px 18px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
}

.stop-process-btn:hover {
    background: rgba(220, 80, 60, 0.22);
    border-color: rgba(220, 80, 60, 0.65);
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
</style>
</head>
<body>
<div id="app">
    <section id="welcomeView">
        <div class="welcome-shell">
            <div class="welcome-icon" aria-hidden="true">
                <svg width="42" height="42" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <g transform="translate(50,50)">
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(0)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(30)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(60)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(90)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(120)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(150)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(180)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(210)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(240)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(270)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(300)"/></g>
                        <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(330)"/></g>
                    </g>
                </svg>
            </div>
            <h1 class="welcome-title">Back at it, steve</h1>

            <div class="composer-card">
                <div id="welcomeAttachments" class="attachment-strip"></div>
                <textarea id="welcomeInput" class="composer-input" rows="1" placeholder="Type / for skills"></textarea>
                <div class="control-row">
                    <button class="plus-btn" type="button" aria-label="Add">+</button>
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
                    <span class="folder-path-icon" aria-hidden="true">📁</span>
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
        </div>
    </section>

    <section id="chatView">
        <div id="dropOverlay">Drop file here</div>
        <div id="chatToolbar">
            <button id="artifactsToggleBtn" type="button" title="Open artifacts panel">📦 Artifacts</button>
        </div>
        <div id="messages"></div>
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
            <button id="stopBtn" class="stop-process-btn" type="button" style="display:none;">Stop generating</button>
            <div class="composer-card">
                <div id="chatAttachments" class="attachment-strip"></div>
                <textarea id="chatInput" class="composer-input" rows="1" placeholder="Reply..."></textarea>
                <div class="control-row">
                    <button class="plus-btn" type="button" aria-label="Add">+</button>
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
                    <span class="folder-path-icon" aria-hidden="true">📁</span>
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
    const MODEL_OPTIONS = [
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

    const REASONING_OPTIONS = [
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

    const PERMISSION_OPTIONS = [
        {
            value: "auto",
            title: "Auto",
            description: "Claude asks only when approval is needed.",
        },
        {
            value: "plan",
            title: "Plan mode",
            description: "Claude proposes plans before applying changes.",
        },
        {
            value: "bypassPermissions",
            title: "Bypass permissions",
            description: "Runs actions directly with fewer confirmations.",
        },
    ];

    const appEl = document.getElementById("app");
    const welcomeViewEl = document.getElementById("welcomeView");
    const chatViewEl = document.getElementById("chatView");
    const messagesEl = document.getElementById("messages");
    const welcomeInputEl = document.getElementById("welcomeInput");
    const chatInputEl = document.getElementById("chatInput");
    const dropOverlayEl = document.getElementById("dropOverlay");
    const welcomeAttachmentsEl = document.getElementById("welcomeAttachments");
    const chatAttachmentsEl = document.getElementById("chatAttachments");
    const stopBtnEl = document.getElementById("stopBtn");
    const imageLightboxEl = document.getElementById("imageLightbox");
    const lightboxImageEl = document.getElementById("lightboxImage");
    const lightboxCloseBtnEl = document.getElementById("lightboxCloseBtn");
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
    const quickChips = Array.from(document.querySelectorAll(".quick-chip"));
    const folderPathButtons = Array.from(document.querySelectorAll(".folder-path-btn"));
    const folderPathTexts = Array.from(document.querySelectorAll(".folder-path-text"));
    const DIFF_LCS_CELL_LIMIT = 250000;
    const DIFF_HARD_LINE_LIMIT = 1800;
    const DIFF_RENDER_LINE_LIMIT = 1000;
    const DIFF_AUTO_EXPAND_MAX_LINES = 180;

    let hasMessages = false;
    let typingRow = null;
    let currentAssistantRow = null;
    let currentAssistantBody = null;
    let currentAssistantRaw = "";
    let renderQueued = false;
    let selectedModel = "opus";
    let selectedReasoning = "medium";
    let selectedPermission = "auto";
    let activePopup = null;
    let lastUserPayload = null;
    let currentFolderDisplay = "~";
    let attachments = [];
    let attachmentCounter = 0;
    let dragDepth = 0;
    let permissionRequestCounter = 0;
    let toolCardCounter = 0;
    let activeToolTurn = null;
    let lastPRUrl = "";
    let artifactsPanelOpen = false;
    let artifactCounter = 0;
    let selectedArtifactId = "";
    let selectedArtifactVersion = 0;
    let artifactSnippetCounter = 0;
    const seenPermissionRequests = Object.create(null);
    const prCardByKey = Object.create(null);
    const prCardByUrl = Object.create(null);
    const ciCardByKey = Object.create(null);
    const artifacts = [];
    const artifactByKey = Object.create(null);
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

    function sparkleSvg(size, className) {
        const svgClass = className || "";
        return [
            '<svg class="' + svgClass + '" width="' + size + '" height="' + size + '" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">',
            '  <g transform="translate(50,50)">',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(0)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(30)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(60)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(90)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(120)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(150)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(180)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(210)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(240)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(270)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(300)"/></g>',
            '    <g><rect x="-5" y="-42" width="10" height="42" rx="5" fill="#D97757" transform="rotate(330)"/></g>',
            "  </g>",
            "</svg>",
        ].join("");
    }

    function updateFolderDisplay(pathValue) {
        const nextValue = String(pathValue || "").trim() || "~";
        currentFolderDisplay = nextValue;
        folderPathTexts.forEach(function (label) {
            label.textContent = currentFolderDisplay;
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

    function createArtifactIndicator(artifact) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "artifact-indicator";
        button.setAttribute("data-artifact-id", artifact.id);
        button.setAttribute("data-artifact-version", String(artifact.version));

        const icon = document.createElement("span");
        icon.className = "artifact-indicator-icon";
        icon.textContent = artifactIconForType(artifact.type);
        button.appendChild(icon);

        const label = document.createElement("span");
        label.textContent = "Open in Artifacts • " + artifact.title;
        button.appendChild(label);
        return button;
    }

    function appendArtifactIndicator(anchorEl, artifact) {
        if (!anchorEl || !artifact) {
            return;
        }

        const existing = anchorEl.nextElementSibling;
        if (
            existing
            && existing.classList
            && existing.classList.contains("artifact-indicator")
            && existing.getAttribute("data-artifact-id") === artifact.id
        ) {
            existing.setAttribute("data-artifact-version", String(artifact.version));
            return;
        }

        const indicator = createArtifactIndicator(artifact);
        anchorEl.insertAdjacentElement("afterend", indicator);
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
        const language = normalizeLanguage(block.lang || languageFromFilename(block.filename));
        const content = String(block.code || "");
        const title = String(block.filename || "").trim();
        const structured = isLikelyStructured(language, content);
        const hasMeta = !!(title || language);

        if (!hasMeta && !structured) {
            return null;
        }

        const type = title ? "file" : (structured ? "data" : "code");
        const fallbackTitle = type === "data"
            ? ((language || detectStructuredLanguage(content) || "data") + "-output")
            : ((language || "code") + "-snippet-" + (index + 1));
        return {
            type: type,
            title: title || fallbackTitle,
            language: language || detectStructuredLanguage(content),
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
            return '<img src="' + src + '" alt="' + alt + '" class="chat-image" loading="lazy">';
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
                '    <button class="action-btn code-copy-btn" data-raw="' + rawEncoded + '">Copy</button>',
                "  </div>",
                '  <pre><code class="' + codeClass + '">' + highlighted + '</code></pre>',
                "</div>",
            ].join("");
        });

        html = applyEmojiOutsideCodeTags(html);

        return html || "<p></p>";
    }

    function postToHost(handlerName, payload) {
        if (
            window.webkit &&
            window.webkit.messageHandlers &&
            window.webkit.messageHandlers[handlerName]
        ) {
            window.webkit.messageHandlers[handlerName].postMessage(payload);
        }
    }

    function normalizeModelValue(rawValue) {
        const value = String(rawValue || "").trim();
        const valid = MODEL_OPTIONS.some(function (option) {
            return option.value === value;
        });
        return valid ? value : "sonnet";
    }

    function normalizePermissionValue(rawValue) {
        const value = String(rawValue || "").trim();
        const valid = PERMISSION_OPTIONS.some(function (option) {
            return option.value === value;
        });
        return valid ? value : "auto";
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
        var reasoning = REASONING_OPTIONS.find(function (option) {
            return option.value === value;
        });
        return reasoning || REASONING_OPTIONS[1];
    }

    function renderSelectorLabels() {
        const modelLabel = findModelMeta(selectedModel).short;
        modelButtons.forEach(function (button) {
            const labelEl = button.querySelector(".model-label");
            if (labelEl) {
                labelEl.textContent = modelLabel;
            }
        });

        const reasoningLabel = findReasoningMeta(selectedReasoning).title;
        reasoningButtons.forEach(function (button) {
            const labelEl = button.querySelector(".reasoning-label");
            if (labelEl) {
                labelEl.textContent = reasoningLabel;
            }
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
            renderReasoningPopup(popup);
        } else {
            renderPermissionPopup(popup);
        }

        triggerButton.setAttribute("aria-expanded", "true");
        popup.classList.remove("closing");
        popup.classList.add("open");
        activePopup = popup;
    }

    function setChatState(withMessages) {
        hasMessages = !!withMessages;

        if (hasMessages) {
            welcomeViewEl.style.display = "none";
            chatViewEl.classList.add("active");
            appEl.classList.add("chat-state");
            setTimeout(function () { chatInputEl.focus(); }, 50);
            return;
        }

        welcomeViewEl.style.display = "flex";
        chatViewEl.classList.remove("active");
        appEl.classList.remove("chat-state");
        setTimeout(function () { welcomeInputEl.focus(); }, 50);
    }

    function normalizeAttachment(payload) {
        if (!payload || typeof payload !== "object") {
            return null;
        }
        const name = String(payload.name || "attachment").trim() || "attachment";
        const type = String(payload.type || "application/octet-stream").trim() || "application/octet-stream";
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
        };
    }

    function cloneAttachmentList(listValue) {
        return (Array.isArray(listValue) ? listValue : []).map(function (item) {
            return {
                name: String(item.name || "attachment"),
                type: String(item.type || "application/octet-stream"),
                data: String(item.data || ""),
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
            const chip = document.createElement("div");
            chip.className = "attachment-chip";

            if (attachment.type.indexOf("image/") === 0) {
                const thumb = document.createElement("img");
                thumb.className = "attachment-thumb";
                thumb.src = attachment.data;
                thumb.alt = attachment.name;
                chip.appendChild(thumb);
            } else {
                const marker = document.createElement("span");
                marker.textContent = "📄";
                chip.appendChild(marker);
            }

            const name = document.createElement("span");
            name.className = "attachment-name";
            name.textContent = attachment.name;
            chip.appendChild(name);

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "attachment-remove";
            removeButton.setAttribute("aria-label", "Remove attachment");
            removeButton.textContent = "×";
            removeButton.addEventListener("click", function () {
                attachments = attachments.filter(function (item) {
                    return item.id !== attachment.id;
                });
                renderAttachments();
            });
            chip.appendChild(removeButton);

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
                resolve({
                    name: file.name || "attachment",
                    type: file.type || "application/octet-stream",
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
        return hasMessages ? chatInputEl : welcomeInputEl;
    }

    function sendPayload(payload) {
        const text = String(payload && payload.text ? payload.text : "").trim();
        const outgoingAttachments = cloneAttachmentList(payload ? payload.attachments : []);
        if (!text && !outgoingAttachments.length) {
            return;
        }

        const outgoing = {
            text: text,
            attachments: outgoingAttachments,
        };
        lastUserPayload = outgoing;
        setChatState(true);
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

    function scrollToBottom(force) {
        const nearBottom = (messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight) < 150;
        if (force || nearBottom) {
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }
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
        messagesEl.appendChild(row);

        return { row: row, inner: inner };
    }

    function addUserMessage(text, attachmentList) {
        setChatState(true);
        resetToolTurnState();

        const rowObj = createMessageRow("user");
        const bubble = document.createElement("div");
        bubble.className = "user-bubble";
        const safeText = String(text || "");
        const outgoingAttachments = cloneAttachmentList(attachmentList);

        if (outgoingAttachments.length) {
            const gallery = document.createElement("div");
            gallery.className = "message-attachments";
            outgoingAttachments.forEach(function (attachment) {
                if (attachment.type.indexOf("image/") === 0 && attachment.data) {
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
            textBlock.textContent = safeText;
            bubble.appendChild(textBlock);
        }

        rowObj.inner.appendChild(bubble);
        scrollToBottom(true);
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

        if (
            /\bgh\s+pr\s+checks\b/.test(lowerCommand)
            || /\bgh\s+run\b/.test(lowerCommand)
            || lowerOutput.indexOf("pipeline") >= 0
            || lowerOutput.indexOf("workflow") >= 0
        ) {
            let status = "pending";
            if (/\b(fail|failed|failing|error)\b/i.test(output)) {
                status = "failing";
            } else if (/\b(pass|passed|success|successful)\b/i.test(output)) {
                status = "passing";
            }
            events.ci = {
                status: status,
                url: (output.match(/https?:\/\/[^\s)]+(?:actions\/runs\/\d+|runs\/\d+|pipelines\/[^\s)]+)/i) || [])[0] || "",
                prUrl: events.pr && events.pr.url ? events.pr.url : "",
                suggestFix: status === "failing",
            };
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
        fixButton.textContent = "Claude can try to fix this";
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

    function addSystemMessage(text) {
        setChatState(true);

        var raw = String(text || "").trim();
        if (!raw) return;

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

        const rowObj = createMessageRow("system");
        const pill = document.createElement("div");
        pill.className = "system-pill";
        pill.textContent = raw;

        rowObj.inner.appendChild(pill);
        scrollToBottom(true);
    }

    function addToolMessage(data) {
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
        const card = document.createElement("div");
        card.className = "tool-card";
        toolCardCounter += 1;
        card.id = "tool-card-" + toolCardCounter;

        const header = document.createElement("div");
        header.className = "tool-header";

        var caretEl = null;
        if (hasDetail) {
            caretEl = document.createElement("span");
            caretEl.className = "tool-caret";
            caretEl.textContent = "\u25B6";
            header.appendChild(caretEl);
        }

        const nameEl = document.createElement("span");
        nameEl.className = "tool-name";
        nameEl.textContent = toolName;
        header.appendChild(nameEl);

        if (filePath) {
            const pathEl = document.createElement("span");
            pathEl.className = "tool-path";
            var displayPath = filePath;
            if (displayPath.length > 60) {
                displayPath = "\u2026" + displayPath.slice(-57);
            }
            pathEl.textContent = displayPath;
            header.appendChild(pathEl);
        }

        card.appendChild(header);

        var detailEl = null;
        var summaryEntry = null;
        var openByDefault = false;

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

            card.appendChild(detailEl);
            detailEl.classList.toggle("open", openByDefault);
            if (caretEl) {
                caretEl.classList.toggle("open", openByDefault);
            }

            header.addEventListener("click", function () {
                var isOpen = detailEl.classList.toggle("open");
                if (caretEl) {
                    caretEl.classList.toggle("open", isOpen);
                }
                scrollToBottom(false);
            });
        }

        registerToolArtifact(data, card);
        rowObj.inner.appendChild(card);
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

        const toolName = String(data.name || "Tool");
        const description = String(data.description || "Claude requests approval before running this tool.");
        const proposedAction = String(data.proposedAction || "");
        const filePath = String(data.path || "");
        const command = String(data.command || "");
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
        card.className = "permission-request-card pending";
        card.setAttribute("data-request-id", requestId);

        const header = document.createElement("div");
        header.className = "permission-request-header";

        const icon = document.createElement("span");
        icon.className = "permission-request-icon";
        icon.textContent = permissionIconForTool(toolName);
        header.appendChild(icon);

        const titleWrap = document.createElement("div");
        titleWrap.className = "permission-request-title";

        const toolLabel = document.createElement("div");
        toolLabel.className = "permission-request-tool";
        toolLabel.textContent = toolName;
        titleWrap.appendChild(toolLabel);

        const subtitle = document.createElement("div");
        subtitle.className = "permission-request-subtitle";
        subtitle.textContent = "Permission required";
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

        const allowButton = document.createElement("button");
        allowButton.type = "button";
        allowButton.className = "permission-action-btn allow";
        allowButton.textContent = "Allow";
        actions.appendChild(allowButton);

        const denyButton = document.createElement("button");
        denyButton.type = "button";
        denyButton.className = "permission-action-btn deny";
        denyButton.textContent = "Deny";
        actions.appendChild(denyButton);

        const commentWrap = document.createElement("div");
        commentWrap.className = "permission-comment-wrap";

        const commentInput = document.createElement("input");
        commentInput.type = "text";
        commentInput.className = "permission-comment-input";
        commentInput.placeholder = "Add comment or modification request";
        commentWrap.appendChild(commentInput);

        const commentButton = document.createElement("button");
        commentButton.type = "button";
        commentButton.className = "permission-action-btn";
        commentButton.textContent = "Send";
        commentWrap.appendChild(commentButton);

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

            allowButton.disabled = true;
            denyButton.disabled = true;
            commentButton.disabled = true;
            commentInput.disabled = true;

            if (action === "allow") {
                status.textContent = "Approved. Sent to Claude.";
                return;
            }
            if (action === "deny") {
                status.textContent = "Denied. Claude will not run this action.";
                return;
            }
            status.textContent = commentText
                ? 'Comment sent: "' + commentText + '"'
                : "Comment sent to Claude.";
        }

        function submitResponse(action) {
            if (resolved) {
                return;
            }

            const trimmedComment = String(commentInput.value || "").trim();
            if (action === "comment" && !trimmedComment) {
                commentInput.focus();
                return;
            }

            postToHost("permissionResponse", JSON.stringify({
                action: action,
                comment: action === "comment" ? trimmedComment : "",
                requestId: requestId,
            }));
            resolveCard(action, trimmedComment);
        }

        allowButton.addEventListener("click", function () {
            submitResponse("allow");
        });

        denyButton.addEventListener("click", function () {
            submitResponse("deny");
        });

        commentButton.addEventListener("click", function () {
            submitResponse("comment");
        });

        commentInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                submitResponse("comment");
            }
        });

        rowObj.inner.appendChild(card);
        scrollToBottom(true);
    }

    function startAssistantMessage() {
        if (currentAssistantBody) {
            return;
        }

        setChatState(true);

        const rowObj = createMessageRow("assistant");
        const block = document.createElement("div");
        block.className = "assistant-block";

        const icon = document.createElement("div");
        icon.className = "sparkle-small sparkle-live";
        icon.innerHTML = sparkleSvg(20, "sparkle-pulse");

        const wrap = document.createElement("div");
        wrap.className = "assistant-content-wrap";

        const body = document.createElement("div");
        body.className = "assistant-message markdown-body";

        const actions = document.createElement("div");
        actions.className = "assistant-actions";
        actions.innerHTML = [
            '<button class="assistant-action" data-action="copy" type="button" title="Copy">📋</button>',
            '<button class="assistant-action" data-action="up" type="button" title="Thumbs up">👍</button>',
            '<button class="assistant-action" data-action="down" type="button" title="Thumbs down">👎</button>',
            '<button class="assistant-action" data-action="retry" type="button" title="Retry">🔄</button>',
        ].join("");

        wrap.appendChild(body);
        wrap.appendChild(actions);

        block.appendChild(icon);
        block.appendChild(wrap);
        rowObj.inner.appendChild(block);

        currentAssistantRow = rowObj.row;
        currentAssistantBody = body;
        currentAssistantRaw = "";

        scrollToBottom(true);
    }

    function scheduleAssistantRender() {
        if (renderQueued) {
            return;
        }

        renderQueued = true;
        window.requestAnimationFrame(function () {
            renderQueued = false;
            if (currentAssistantBody) {
                currentAssistantBody.innerHTML = markdownToHtml(currentAssistantRaw);
                currentAssistantBody.dataset.raw = currentAssistantRaw;
            }
            scrollToBottom(false);
        });
    }

    function appendAssistantChunk(text) {
        if (!text) {
            return;
        }

        if (!currentAssistantBody) {
            startAssistantMessage();
        }

        currentAssistantRaw += String(text);
        scheduleAssistantRender();
    }

    function finishAssistantMessage() {
        if (currentAssistantBody) {
            currentAssistantBody.innerHTML = markdownToHtml(currentAssistantRaw);
            currentAssistantBody.dataset.raw = currentAssistantRaw;
            if (!currentAssistantRaw.trim() && currentAssistantRow) {
                currentAssistantRow.remove();
            }
        }

        if (currentAssistantRow) {
            const liveSparkle = currentAssistantRow.querySelector(".sparkle-live");
            if (liveSparkle) {
                liveSparkle.remove();
            }
        }

        currentAssistantBody = null;
        currentAssistantRow = null;
        currentAssistantRaw = "";
        scrollToBottom(true);
    }

    function setTyping(isTyping) {
        const shouldShow = !!isTyping;

        if (shouldShow && !typingRow) {
            setChatState(true);

            const rowObj = createMessageRow("assistant");
            const shell = document.createElement("div");
            shell.className = "typing-shell";

            const sparkle = document.createElement("div");
            sparkle.className = "sparkle-small";
            sparkle.innerHTML = sparkleSvg(20, "sparkle-pulse");

            shell.appendChild(sparkle);
            rowObj.inner.appendChild(shell);
            typingRow = rowObj.row;
            scrollToBottom(true);
            return;
        }

        if (!shouldShow && typingRow) {
            typingRow.remove();
            typingRow = null;
            scrollToBottom(true);
        }
    }

    function clearMessages() {
        renderQueued = false;
        currentAssistantRaw = "";
        currentAssistantBody = null;
        currentAssistantRow = null;
        typingRow = null;
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
        resetArtifactsSession();
        closeImageLightbox();

        messagesEl.innerHTML = "";
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
            navigator.clipboard.writeText(text).then(onDone).catch(function () {});
            return;
        }

        const temp = document.createElement("textarea");
        temp.value = text;
        document.body.appendChild(temp);
        temp.select();
        try {
            document.execCommand("copy");
            onDone();
        } catch (_error) {
        } finally {
            temp.remove();
        }
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

    function attachInputBehavior(inputEl) {
        inputEl.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendInput(inputEl);
            }
        });

        inputEl.addEventListener("input", function () {
            autoResizeInput(inputEl);
        });

        inputEl.addEventListener("paste", function (event) {
            const clipboard = event.clipboardData;
            if (!clipboard || !clipboard.items) {
                return;
            }
            const imageItems = Array.from(clipboard.items).filter(function (item) {
                return item && item.type && item.type.indexOf("image/") === 0;
            });
            if (!imageItems.length) {
                return;
            }
            event.preventDefault();
            imageItems.forEach(function (item) {
                const file = item.getAsFile();
                if (!file) {
                    return;
                }
                fileToAttachment(file).then(addAttachment).catch(function () {});
            });
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
            postToHost("attachFile", "open");
        });
    });

    if (stopBtnEl) {
        stopBtnEl.addEventListener("click", function () {
            postToHost("stopProcess", "stop");
            stopBtnEl.style.display = "none";
        });
    }

    folderPathButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            postToHost("changeFolder", "change");
        });
    });

    quickChips.forEach(function (chip) {
        chip.addEventListener("click", function () {
            const value = chip.getAttribute("data-value") || "";
            welcomeInputEl.value = value;
            autoResizeInput(welcomeInputEl);
            welcomeInputEl.focus();
        });
    });

    if (artifactsToggleBtnEl) {
        artifactsToggleBtnEl.addEventListener("click", function () {
            setArtifactsPanelOpen(!artifactsPanelOpen);
            if (artifactsPanelOpen && !selectedArtifactId && artifacts.length) {
                selectArtifact(artifacts[0].id, artifacts[0].version);
            }
        });
    }

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
                const previous = codeCopyButton.textContent;
                codeCopyButton.textContent = "Copied";
                window.setTimeout(function () {
                    codeCopyButton.textContent = previous;
                }, 900);
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

                const targetDetail = targetCard.querySelector(".tool-detail");
                const targetCaret = targetCard.querySelector(".tool-caret");
                if (targetDetail && !targetDetail.classList.contains("open")) {
                    targetDetail.classList.add("open");
                    if (targetCaret) {
                        targetCaret.classList.add("open");
                    }
                }
            }
            return;
        }

        const artifactButton = event.target.closest(".artifact-indicator");
        if (artifactButton) {
            const artifactId = String(artifactButton.getAttribute("data-artifact-id") || "");
            const artifactVersion = Number(artifactButton.getAttribute("data-artifact-version") || 0);
            if (artifactId) {
                setArtifactsPanelOpen(true);
                selectArtifact(artifactId, artifactVersion);
            }
            return;
        }

        const actionButton = event.target.closest(".assistant-action");
        if (actionButton) {
            const action = actionButton.getAttribute("data-action");
            const messageBody = actionButton.closest(".assistant-content-wrap")
                ? actionButton.closest(".assistant-content-wrap").querySelector(".assistant-message")
                : null;
            const raw = messageBody ? (messageBody.dataset.raw || messageBody.textContent || "") : "";

            if (action === "copy") {
                copyText(raw, function () {
                    markActionPressed(actionButton);
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
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
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

    window.addUserMessage = addUserMessage;
    window.startAssistantMessage = startAssistantMessage;
    window.appendAssistantChunk = appendAssistantChunk;
    window.finishAssistantMessage = finishAssistantMessage;
    window.addSystemMessage = addSystemMessage;
    window.addPermissionRequest = addPermissionRequest;
    window.setTyping = setTyping;
    window.clearMessages = clearMessages;
    window.showWelcome = showWelcome;
    window.addHostAttachment = function (attachment) {
        addAttachment(attachment);
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

    window.updateReasoningLevel = function (value) {
        selectedReasoning = value;
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
        if (stopBtnEl) {
            stopBtnEl.style.display = isProcessing ? "block" : "none";
        }
    };
    window.focusInput = function () {
        if (hasMessages) {
            chatInputEl.focus();
        } else {
            welcomeInputEl.focus();
        }
    };
    window.updateFolder = function (pathValue) {
        updateFolderDisplay(pathValue);
    };

    resetToolTurnState();
    setChatState(false);
    renderSelectorLabels();
    updateFolderDisplay("~");
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
