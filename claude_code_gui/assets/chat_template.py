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
    --chip-border: #4a4a43;
    --code-bg: #1a1a16;
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
}

#chatView.active {
    display: block;
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
    padding: 26px 14px 220px;
    scroll-behavior: smooth;
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

.tool-card {
    max-width: 768px;
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
    max-height: 300px;
    overflow-y: auto;
}

.tool-detail.open {
    display: block;
    animation: toolReveal 200ms ease-out;
}

@keyframes toolReveal {
    from { opacity: 0; max-height: 0; }
    to { opacity: 1; max-height: 300px; }
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
        <div id="messages"></div>

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

        source = source.replace(/```([a-zA-Z0-9_-]+)?\n?([\s\S]*?)```/g, function (_, lang, code) {
            const id = codeBlocks.length;
            codeBlocks.push({ lang: String(lang || "").trim(), code: code || "" });
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
            const block = codeBlocks[index] || { lang: "", code: "" };
            const code = String(block.code || "");
            const highlighted = highlightCode(code, block.lang);
            const rawEncoded = encodeURIComponent(code);
            const lang = escapeHtml(block.lang || "code");
            const codeClass = block.lang ? "hljs language-" + escapeHtml(block.lang) : "hljs";
            return [
                '<div class="code-block">',
                '  <div class="code-head">',
                "    <span>" + lang + "</span>",
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

    function addSystemMessage(text) {
        setChatState(true);

        var raw = String(text || "").trim();
        if (!raw) return;

        try {
            var parsed = JSON.parse(raw);
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
        const toolName = String(data.name || "tool");
        const filePath = String(data.path || data.command || "");
        const hasDetail = !!(data.old || data.new || data.content || data.command);

        const rowObj = createMessageRow("tool");
        const card = document.createElement("div");
        card.className = "tool-card";

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
        if (hasDetail) {
            detailEl = document.createElement("div");
            detailEl.className = "tool-detail";

            if (data.old !== undefined || data.new !== undefined) {
                if (data.old) {
                    const oldBlock = document.createElement("div");
                    oldBlock.className = "tool-diff-old";
                    oldBlock.textContent = "- " + String(data.old).replace(/\n/g, "\n- ");
                    detailEl.appendChild(oldBlock);
                }
                if (data.new) {
                    const newBlock = document.createElement("div");
                    newBlock.className = "tool-diff-new";
                    newBlock.textContent = "+ " + String(data.new).replace(/\n/g, "\n+ ");
                    detailEl.appendChild(newBlock);
                }
            } else if (data.content) {
                const codeBlock = document.createElement("div");
                codeBlock.className = "tool-code";
                codeBlock.textContent = String(data.content);
                detailEl.appendChild(codeBlock);
            } else if (data.command) {
                const cmdBlock = document.createElement("div");
                cmdBlock.className = "tool-code";
                cmdBlock.textContent = "$ " + String(data.command);
                detailEl.appendChild(cmdBlock);
            }

            card.appendChild(detailEl);

            header.addEventListener("click", function () {
                var isOpen = detailEl.classList.toggle("open");
                if (caretEl) {
                    caretEl.classList.toggle("open", isOpen);
                }
                scrollToBottom(false);
            });
        }

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

        const codeCopyButton = event.target.closest(".code-copy-btn");
        if (codeCopyButton) {
            const encoded = codeCopyButton.getAttribute("data-raw") || "";
            let raw = "";
            try {
                raw = decodeURIComponent(encoded);
            } catch (_error) {
                raw = "";
            }

            copyText(raw, function () {
                const previous = codeCopyButton.textContent;
                codeCopyButton.textContent = "Copied";
                window.setTimeout(function () {
                    codeCopyButton.textContent = previous;
                }, 900);
            });
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
    window.setTyping = setTyping;
    window.clearMessages = clearMessages;
    window.showWelcome = showWelcome;
    window.addHostAttachment = function (attachment) {
        addAttachment(attachment);
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

    setChatState(false);
    renderSelectorLabels();
    updateFolderDisplay("~");
    renderAttachments();
})();
</script>
</body>
</html>
"""
