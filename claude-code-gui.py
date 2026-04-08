#!/usr/bin/env python3
"""Modern GTK3 wrapper for Claude Code CLI with embedded WebKit2 chat UI."""

from __future__ import annotations

import base64
import json
import math
import mimetypes
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote_to_bytes

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
try:
    gi.require_version("WebKit2", "4.1")
except ValueError:
    gi.require_version("WebKit2", "4.0")

from gi.repository import Gdk, GLib, Gtk, Pango, WebKit2

APP_NAME = "Claude Code"
APP_MIN_WIDTH = 900
APP_MIN_HEIGHT = 600
APP_DEFAULT_WIDTH = 1440
APP_DEFAULT_HEIGHT = 920
SIDEBAR_OPEN_WIDTH = 292
CONTEXT_MAX_TOKENS = 200_000
ATTACHMENT_MAX_BYTES = 12 * 1024 * 1024

CONFIG_DIR = Path.home() / ".config" / "claude-code-gui"
RECENT_FOLDERS_PATH = CONFIG_DIR / "recent_folders.json"
SESSIONS_PATH = CONFIG_DIR / "sessions.json"
RECENT_FOLDERS_LIMIT = 10

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_ENDED = "ended"
SESSION_STATUS_ARCHIVED = "archived"
SESSION_STATUS_ERROR = "error"
SESSION_STATUSES = {
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_ENDED,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_ERROR,
}

MODEL_OPTIONS: list[tuple[str, str]] = [
    ("Claude Sonnet (Latest)", "sonnet"),
    ("Claude Opus (Latest)", "opus"),
    ("Claude Haiku (Latest)", "haiku"),
]

LEGACY_MODEL_ALIASES: dict[str, str] = {
    "default": "sonnet",
    "claude-sonnet-4-6": "sonnet",
    "claude-opus-4-6": "opus",
    "claude-haiku-4-5": "haiku",
}

PERMISSION_OPTIONS: list[tuple[str, str, bool]] = [
    ("Auto", "auto", False),
    ("Plan mode", "plan", False),
    ("Bypass permissions (Advanced)", "bypassPermissions", True),
]

LEGACY_PERMISSION_ALIASES: dict[str, str] = {
    "ask": "auto",
    "default": "auto",
    "acceptEdits": "auto",
}

CONNECTION_CONNECTED = "connected"
CONNECTION_DISCONNECTED = "disconnected"
CONNECTION_STARTING = "starting"
CONNECTION_ERROR = "error"

STATUS_MUTED = "muted"
STATUS_INFO = "info"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"

WINDOW_BG = "#2f2f2a"
HEADER_BG = "#2c2c27"
SIDEBAR_BG = "#252520"
CHAT_OUTER_BG = "#2f2f2a"
CHAT_BG = "#2f2f2a"
STATUS_BG = "#292923"
BORDER = "#4a4a43"
BORDER_SOFT = "#3b3b35"
FOREGROUND = "#d4d4c8"
FOREGROUND_MUTED = "#8a8a7a"
ACCENT = "#d97757"
ACCENT_SOFT = "#e09670"
WARNING = "#d5a160"
ERROR = "#df7f66"
SUCCESS = "#8bbf8a"
BUTTON_BG = "#35352f"
BUTTON_BG_HOVER = "#3f3f38"
BUTTON_BG_ACTIVE = "#484840"

CSS_STYLES = f"""
window,
.app-root {{
    background-color: {WINDOW_BG};
    color: {FOREGROUND};
}}

.header-shell {{
    background: linear-gradient(180deg, {HEADER_BG}, #252520);
    border-bottom: 1px solid {BORDER_SOFT};
}}

.header-row {{
    padding: 6px 10px;
}}

.brand-icon {{
    color: {ACCENT};
    font-size: 12px;
    font-weight: 700;
}}

.brand-title {{
    color: {FOREGROUND};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}

.control-group,
.window-controls {{
    padding: 0;
}}

.button,
.sidebar-button,
.sidebar-toggle-gtk,
.new-session-button,
.session-menu-button {{
    background-color: {BUTTON_BG};
    color: {FOREGROUND};
    border: 1px solid {BORDER_SOFT};
    border-radius: 999px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.15s ease;
}}

.button:hover,
.sidebar-button:hover,
.sidebar-toggle-gtk:hover,
.new-session-button:hover,
.session-menu-button:hover {{
    background-color: {BUTTON_BG_HOVER};
    border-color: {ACCENT_SOFT};
    box-shadow: 0 2px 9px rgba(0, 0, 0, 0.2);
}}

.button:active,
.sidebar-button:active,
.sidebar-toggle-gtk:active,
.new-session-button:active,
.session-menu-button:active {{
    background-color: {BUTTON_BG_ACTIVE};
    box-shadow: none;
}}

.button:focus,
.sidebar-button:focus,
.sidebar-toggle-gtk:focus,
.new-session-button:focus,
.session-menu-button:focus {{
    box-shadow: 0 0 0 2px rgba(212, 132, 90, 0.35);
}}

.new-session-button {{
    border-radius: 12px;
}}

.new-session-button {{
    min-height: 38px;
    background: #31312b;
    border-color: #3f3f38;
    color: {FOREGROUND};
    font-weight: 600;
    padding: 0 12px;
}}

.sidebar-toggle-gtk {{
    min-height: 30px;
    min-width: 30px;
    padding: 0;
}}

.bottom-combo button,
.recent-combo button {{
    background-color: {BUTTON_BG};
    color: {FOREGROUND};
    border: 1px solid {BORDER_SOFT};
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.15s ease;
}}

.bottom-combo button:hover,
.recent-combo button:hover {{
    background-color: {BUTTON_BG_HOVER};
    border-color: {ACCENT_SOFT};
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
}}

.bottom-combo button:focus,
.recent-combo button:focus {{
    box-shadow: 0 0 0 2px rgba(212, 132, 90, 0.35);
}}

.bottom-combo button:active,
.recent-combo button:active {{
    background-color: {BUTTON_BG_ACTIVE};
}}

.bottom-combo:disabled button,
.recent-combo:disabled button {{
    color: {FOREGROUND_MUTED};
    opacity: 0.72;
}}

.bottom-combo arrow,
.recent-combo arrow {{
    color: {FOREGROUND_MUTED};
    min-width: 10px;
}}

.permission-combo.permission-advanced button {{
    border-color: rgba(240, 181, 97, 0.55);
    color: {WARNING};
}}

menu {{
    background-color: #34342e;
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 4px;
}}

menuitem {{
    color: {FOREGROUND};
    border-radius: 8px;
    padding: 6px 10px;
}}

menuitem:hover {{
    background-color: rgba(212, 132, 90, 0.2);
}}

menuitem:disabled {{
    color: {FOREGROUND_MUTED};
}}

.main-content {{
    background-color: {WINDOW_BG};
}}

.sidebar {{
    background: {SIDEBAR_BG};
    border-right: 1px solid {BORDER_SOFT};
    padding: 12px 10px;
    transition: all 0.15s ease;
}}

.sidebar-section-title {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2px;
    margin-top: 10px;
    margin-bottom: 3px;
}}

.session-scroll {{
    border: none;
    background-color: transparent;
}}

.session-list {{
    padding: 4px 0;
}}

.session-empty {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    padding: 8px;
}}

.session-row {{
    border: 1px solid transparent;
    border-radius: 12px;
    background-color: transparent;
    padding: 4px 6px;
    transition: all 0.15s ease;
    box-shadow: none;
}}

.session-row + .session-row {{
    margin-top: 4px;
}}

.session-row:hover {{
    background-color: #34342f;
}}

.session-row.session-row-active {{
    background-color: #3a3a34;
    border-color: rgba(224, 150, 112, 0.4);
    box-shadow: inset 0 0 0 1px rgba(224, 150, 112, 0.18);
}}

.session-open-button {{
    background-color: transparent;
    border: none;
    color: {FOREGROUND};
    padding: 4px 2px;
    font-size: 12px;
    transition: all 0.15s ease;
}}

.session-open-button:hover {{
    background-color: transparent;
    border: none;
}}

.session-open-button:focus {{
    box-shadow: 0 0 0 2px rgba(212, 132, 90, 0.35);
}}

.session-title {{
    color: {FOREGROUND};
    font-size: 12px;
    font-weight: 600;
}}

.session-menu-button {{
    min-height: 24px;
    min-width: 24px;
    padding: 0;
    border-radius: 999px;
    background: transparent;
    border-color: transparent;
}}

.session-group-label {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 700;
    margin: 10px 6px 2px;
}}

.session-popover button {{
    border-radius: 9px;
    border: 1px solid transparent;
    transition: all 0.15s ease;
}}

.session-popover button:hover {{
    border-color: rgba(212, 132, 90, 0.45);
    background-color: rgba(212, 132, 90, 0.12);
}}

.chat-wrap {{
    padding: 10px 10px 8px;
    background: radial-gradient(circle at top left, rgba(212, 132, 90, 0.11), transparent 35%), {CHAT_OUTER_BG};
}}

.chat-shell {{
    background-color: {CHAT_BG};
    border: 1px solid {BORDER};
    border-radius: 12px;
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.23);
    transition: all 0.15s ease;
}}

.chat-shell.chat-focused {{
    border-color: {ACCENT};
    box-shadow: 0 0 0 1px rgba(212, 132, 90, 0.34), 0 14px 28px rgba(0, 0, 0, 0.28);
}}

.chat-overlay-toggle {{
    background: transparent;
    padding: 8px;
}}

.bottom-bar {{
    background: linear-gradient(180deg, {STATUS_BG}, #252520);
    border-top: 1px solid {BORDER_SOFT};
    min-height: 30px;
    padding: 4px 10px;
}}

.bottom-project,
.bottom-timer,
.status-label,
.status-muted {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
}}

.status-info {{
    color: {ACCENT_SOFT};
    font-size: 11px;
}}

.status-warning {{
    color: {WARNING};
    font-size: 11px;
}}

.status-error {{
    color: {ERROR};
    font-size: 11px;
}}

.connection-dot {{
    font-size: 10px;
}}

.connection-dot.state-connected {{
    color: {SUCCESS};
}}

.connection-dot.state-disconnected {{
    color: {FOREGROUND_MUTED};
}}

.connection-dot.state-starting {{
    color: {WARNING};
}}

.connection-dot.state-error {{
    color: {ERROR};
}}

.context-label {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
}}

.context-progress {{
    min-height: 6px;
}}

.context-progress trough {{
    min-height: 6px;
    border-radius: 999px;
    background-color: #3a3a34;
}}

.context-progress progress {{
    min-height: 6px;
    border-radius: 999px;
    background-color: {SUCCESS};
}}

.context-progress.context-warn progress {{
    background-color: {WARNING};
}}

.context-progress.context-high progress {{
    background-color: {ERROR};
}}
"""

CHAT_WEBVIEW_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
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
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
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

.message-attachment-image {
    max-width: 240px;
    max-height: 180px;
    border-radius: 10px;
    border: 1px solid #4a4a43;
    object-fit: cover;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.26);
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

.tok-keyword {
    color: #f1b388;
}

.tok-string {
    color: #b7d6a8;
}

.tok-number {
    color: #f1d38e;
}

.tok-comment {
    color: #8f8a76;
}

.tok-boolean {
    color: #86c5df;
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
    animation: sparkle-pulse 1.5s ease-in-out infinite;
    filter: drop-shadow(0 0 6px rgba(217, 119, 87, 0.45));
}

@keyframes sparkle-pulse {
    0%,
    100% {
        transform: scale(1);
        opacity: 1;
    }
    50% {
        transform: scale(1.15);
        opacity: 0.7;
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
                            <button class="permission-btn permission-selector" type="button" aria-haspopup="true" aria-expanded="false" title="Reasoning mode">
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
                            <button class="permission-btn permission-selector" type="button" aria-haspopup="true" aria-expanded="false" title="Reasoning mode">
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

    const modelButtons = Array.from(document.querySelectorAll(".model-selector"));
    const permissionButtons = Array.from(document.querySelectorAll(".permission-selector"));
    const modelPopups = Array.from(document.querySelectorAll(".model-popup"));
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
    let pendingChars = [];
    let typewriterTimer = null;
    let renderQueued = false;
    let selectedModel = "opus";
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

    function highlightCode(code) {
        let html = escapeHtml(code);
        html = html.replace(/\b(const|let|var|function|class|return|if|else|for|while|import|from|export|try|catch|finally|def|async|await|switch|case|break)\b/g, '<span class="tok-keyword">$1</span>');
        html = html.replace(/("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g, '<span class="tok-string">$1</span>');
        html = html.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="tok-number">$1</span>');
        html = html.replace(/\b(true|false|null|None)\b/g, '<span class="tok-boolean">$1</span>');
        html = html.replace(/(#.*$|\/\/.*$)/gm, '<span class="tok-comment">$1</span>');
        return html;
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
            codeBlocks.push({ lang: lang || "code", code: code || "" });
            return "@@CODEBLOCK_" + id + "@@";
        });

        source = escapeHtml(source);

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
            const block = codeBlocks[index] || { lang: "code", code: "" };
            const code = String(block.code || "");
            const highlighted = highlightCode(code);
            const rawEncoded = encodeURIComponent(code);
            const lang = escapeHtml(block.lang || "code");
            return [
                '<div class="code-block">',
                '  <div class="code-head">',
                "    <span>" + lang + "</span>",
                '    <button class="action-btn code-copy-btn" data-raw="' + rawEncoded + '">Copy</button>',
                "  </div>",
                '  <pre><code>' + highlighted + '</code></pre>',
                "</div>",
            ].join("");
        });

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

    function renderSelectorLabels() {
        const modelLabel = findModelMeta(selectedModel).short;
        modelButtons.forEach(function (button) {
            const labelEl = button.querySelector(".model-label");
            if (labelEl) {
                labelEl.textContent = modelLabel;
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

    function openPopup(triggerButton, popup, type) {
        closeActivePopup(true);

        if (type === "model") {
            renderModelPopup(popup);
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
            return;
        }

        welcomeViewEl.style.display = "flex";
        chatViewEl.classList.remove("active");
        appEl.classList.remove("chat-state");
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

        const rowObj = createMessageRow("system");
        const pill = document.createElement("div");
        pill.className = "system-pill";
        pill.textContent = String(text || "");

        rowObj.inner.appendChild(pill);
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
        icon.className = "sparkle-small";
        icon.innerHTML = sparkleSvg(20, "");

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
        pendingChars = [];

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

    function flushAssistantChars() {
        if (!pendingChars.length) {
            if (typewriterTimer) {
                window.clearInterval(typewriterTimer);
                typewriterTimer = null;
            }
            return;
        }

        const step = Math.min(8, pendingChars.length);
        const next = pendingChars.splice(0, step).join("");
        currentAssistantRaw += next;
        scheduleAssistantRender();
    }

    function appendAssistantChunk(text) {
        if (!text) {
            return;
        }

        if (!currentAssistantBody) {
            startAssistantMessage();
        }

        String(text).split("").forEach(function (ch) {
            pendingChars.push(ch);
        });

        if (!typewriterTimer) {
            typewriterTimer = window.setInterval(flushAssistantChars, 12);
        }
    }

    function finishAssistantMessage() {
        if (typewriterTimer) {
            window.clearInterval(typewriterTimer);
            typewriterTimer = null;
        }

        if (pendingChars.length) {
            currentAssistantRaw += pendingChars.join("");
            pendingChars = [];
        }

        if (currentAssistantBody) {
            currentAssistantBody.innerHTML = markdownToHtml(currentAssistantRaw);
            currentAssistantBody.dataset.raw = currentAssistantRaw;
            if (!currentAssistantRaw.trim() && currentAssistantRow) {
                currentAssistantRow.remove();
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
        if (typewriterTimer) {
            window.clearInterval(typewriterTimer);
            typewriterTimer = null;
        }

        pendingChars = [];
        currentAssistantRaw = "";
        currentAssistantBody = null;
        currentAssistantRow = null;
        typingRow = null;

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

    window.updateModel = function (modelValue) {
        selectedModel = normalizeModelValue(modelValue);
        renderSelectorLabels();
    };

    window.updatePermission = function (permissionValue) {
        selectedPermission = normalizePermissionValue(permissionValue);
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


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def normalize_folder(path_value: str) -> str:
    return str(Path(path_value).expanduser().resolve())


def format_path(path_value: str) -> str:
    home = str(Path.home())
    if path_value == home:
        return "~"
    if path_value.startswith(home + os.sep):
        return "~" + path_value[len(home) :]
    return path_value


def shorten_path(path_value: str, max_length: int) -> str:
    if len(path_value) <= max_length:
        return path_value
    keep = max(10, (max_length - 1) // 2)
    return f"{path_value[:keep]}…{path_value[-keep:]}"


def load_recent_folders(default_folder: str) -> list[str]:
    ensure_config_dir()
    folders: list[str] = []

    if RECENT_FOLDERS_PATH.is_file():
        try:
            data = json.loads(RECENT_FOLDERS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        normalized = normalize_folder(item)
                        if os.path.isdir(normalized):
                            folders.append(normalized)
        except (OSError, json.JSONDecodeError, ValueError):
            folders = []

    merged = [normalize_folder(default_folder)] + folders
    deduped: list[str] = []
    for folder in merged:
        if folder not in deduped:
            deduped.append(folder)

    return deduped[:RECENT_FOLDERS_LIMIT]


def save_recent_folders(folders: list[str]) -> None:
    ensure_config_dir()
    RECENT_FOLDERS_PATH.write_text(json.dumps(folders[:RECENT_FOLDERS_LIMIT], indent=2), encoding="utf-8")


def current_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_timestamp(value: str) -> float:
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0


def model_label_from_value(model_value: str) -> str:
    for label, value in MODEL_OPTIONS:
        if value == model_value:
            return label
    return MODEL_OPTIONS[0][0]


def permission_label_from_value(permission_mode: str) -> str:
    for label, value, _ in PERMISSION_OPTIONS:
        if value == permission_mode:
            return label
    return PERMISSION_OPTIONS[0][0]


def normalize_model_value(raw_value: str | None) -> str:
    candidate = str(raw_value or MODEL_OPTIONS[0][1]).strip()
    candidate = LEGACY_MODEL_ALIASES.get(candidate, candidate)
    if candidate in {value for _, value in MODEL_OPTIONS}:
        return candidate
    return MODEL_OPTIONS[0][1]


def normalize_permission_value(raw_value: str | None) -> str:
    candidate = str(raw_value or PERMISSION_OPTIONS[0][1]).strip()
    candidate = LEGACY_PERMISSION_ALIASES.get(candidate, candidate)
    if candidate in {value for _, value, _ in PERMISSION_OPTIONS}:
        return candidate
    return PERMISSION_OPTIONS[0][1]


def normalize_session_status(raw_value: str | None) -> str:
    status = str(raw_value or SESSION_STATUS_ENDED).strip()
    if status in SESSION_STATUSES:
        return status
    return SESSION_STATUS_ENDED


def _session_payloads_from_raw(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    if isinstance(raw, dict):
        sessions = raw.get("sessions")
        if isinstance(sessions, list):
            return [item for item in sessions if isinstance(item, dict)]

    raise ValueError("Unsupported sessions.json format")


@dataclass
class SessionRecord:
    id: str
    title: str
    project_path: str
    model: str
    permission_mode: str
    status: str
    created_at: str
    last_used_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionRecord":
        model = normalize_model_value(payload.get("model"))
        permission_mode = normalize_permission_value(
            payload.get("permission_mode") or payload.get("mode")
        )
        status = normalize_session_status(payload.get("status"))

        created_at = str(payload.get("created_at") or current_timestamp())
        last_used_at = str(payload.get("last_used_at") or payload.get("updated_at") or created_at)

        folder_value = str(
            payload.get("project_path")
            or payload.get("working_dir")
            or payload.get("cwd")
            or str(Path.home())
        )
        try:
            project_path = normalize_folder(folder_value)
        except OSError:
            project_path = str(Path.home())

        title = str(payload.get("title") or "Untitled Session").strip() or "Untitled Session"
        return cls(
            id=str(payload.get("id") or uuid.uuid4()),
            title=title,
            project_path=project_path,
            model=model,
            permission_mode=permission_mode,
            status=status,
            created_at=created_at,
            last_used_at=last_used_at,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "project_path": self.project_path,
            "model": self.model,
            "permission_mode": self.permission_mode,
            "status": self.status,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
        }


def load_sessions() -> list[SessionRecord]:
    ensure_config_dir()
    if not SESSIONS_PATH.is_file():
        return []

    raw = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
    payloads = _session_payloads_from_raw(raw)

    loaded: list[SessionRecord] = []
    seen_ids: set[str] = set()

    for item in payloads:
        session = SessionRecord.from_dict(item)
        if session.id in seen_ids:
            session.id = str(uuid.uuid4())
        seen_ids.add(session.id)
        loaded.append(session)

    return loaded


def save_sessions(sessions: list[SessionRecord]) -> None:
    ensure_config_dir()
    payload = [session.to_dict() for session in sessions]
    SESSIONS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@dataclass
class ClaudeRunResult:
    success: bool
    assistant_text: str
    streamed_assistant: bool
    conversation_id: str | None
    error_message: str | None


@dataclass
class ClaudeRunConfig:
    binary_path: str
    message: str
    cwd: str
    model: str
    permission_mode: str
    conversation_id: str | None
    supports_model_flag: bool
    supports_permission_flag: bool
    supports_output_format_flag: bool
    supports_stream_json: bool
    supports_json: bool
    stream_json_requires_verbose: bool


class ClaudeProcess:
    """Runs Claude CLI non-interactively and emits parsed events back to GTK main thread."""

    def __init__(
        self,
        on_running_changed: Callable[[str, bool], None],
        on_assistant_chunk: Callable[[str, str], None],
        on_system_message: Callable[[str, str], None],
        on_complete: Callable[[str, ClaudeRunResult], None],
    ) -> None:
        self._on_running_changed = on_running_changed
        self._on_assistant_chunk = on_assistant_chunk
        self._on_system_message = on_system_message
        self._on_complete = on_complete

        self._lock = threading.Lock()
        self._running = False
        self._stop_requested = False
        self._process: subprocess.Popen[str] | None = None

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def stop(self) -> None:
        with self._lock:
            self._stop_requested = True
            process = self._process

        if process is None:
            return

        if process.poll() is None:
            try:
                process.terminate()
            except OSError:
                return

    def send_message(self, *, request_token: str, config: ClaudeRunConfig) -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._stop_requested = False

        worker = threading.Thread(
            target=self._run,
            args=(request_token, config),
            daemon=True,
        )
        worker.start()
        return True

    def _run(self, request_token: str, config: ClaudeRunConfig) -> None:
        self._emit_running_changed(request_token, True)

        modes: list[str] = []
        if config.supports_output_format_flag:
            if config.supports_stream_json:
                modes.append("stream-json")
            if config.supports_json:
                modes.append("json")
        modes.append("text")

        final_result = ClaudeRunResult(
            success=False,
            assistant_text="",
            streamed_assistant=False,
            conversation_id=config.conversation_id,
            error_message="Claude CLI execution failed.",
        )

        try:
            for index, mode in enumerate(modes):
                if index > 0:
                    label = "JSON" if mode == "json" else "Plain text"
                    self._emit_system_message(request_token, f"Falling back to {label} output mode.")

                result, unsupported_output = self._run_single_attempt(
                    request_token=request_token,
                    config=config,
                    mode=mode,
                )

                final_result = result
                if unsupported_output and index < len(modes) - 1:
                    continue
                break
        finally:
            with self._lock:
                self._running = False
                self._process = None
                was_stopped = self._stop_requested

            if was_stopped and not final_result.success and not final_result.error_message:
                final_result.error_message = "Request stopped"

            self._emit_running_changed(request_token, False)
            self._emit_complete(request_token, final_result)

    def _run_single_attempt(
        self,
        *,
        request_token: str,
        config: ClaudeRunConfig,
        mode: str,
    ) -> tuple[ClaudeRunResult, bool]:
        argv = [config.binary_path, "-p", config.message]

        if mode in {"stream-json", "json"}:
            argv.extend(["--output-format", mode])

        if mode == "stream-json" and config.stream_json_requires_verbose:
            argv.append("--verbose")

        if config.supports_model_flag:
            argv.extend(["--model", config.model])

        if config.supports_permission_flag:
            argv.extend(["--permission-mode", config.permission_mode])

        if config.conversation_id:
            argv.extend(["--resume", config.conversation_id])

        try:
            process = subprocess.Popen(
                argv,
                cwd=config.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as error:
            return (
                ClaudeRunResult(
                    success=False,
                    assistant_text="",
                    streamed_assistant=False,
                    conversation_id=config.conversation_id,
                    error_message=f"Could not start Claude CLI: {error}",
                ),
                False,
            )

        with self._lock:
            self._process = process

        assistant_parts: list[str] = []
        streamed_assistant = False
        detected_conversation_id = config.conversation_id
        result_text: str | None = None
        error_messages: list[str] = []
        captured_output: list[str] = []
        parsed_json = False

        stdout = process.stdout
        if stdout is not None:
            for raw_line in stdout:
                if raw_line is None:
                    continue

                line = raw_line.rstrip("\n")
                stripped = line.strip()
                if stripped:
                    captured_output.append(stripped)
                    if len(captured_output) > 120:
                        captured_output = captured_output[-120:]

                with self._lock:
                    if self._stop_requested:
                        break

                if mode == "stream-json":
                    event = self._parse_json_line(stripped)
                    if event is None:
                        continue
                    parsed_json = True
                    event_type = str(event.get("type") or "")

                    if event_type == "assistant":
                        texts, tools = self._extract_assistant_content(event.get("message"))
                        for tool_message in tools:
                            self._emit_system_message(request_token, tool_message)
                        for text_chunk in texts:
                            assistant_parts.append(text_chunk)
                            streamed_assistant = True
                            self._emit_assistant_chunk(request_token, text_chunk)
                        continue

                    if event_type == "result":
                        raw_conversation_id = event.get("conversation_id") or event.get("session_id")
                        if isinstance(raw_conversation_id, str) and raw_conversation_id.strip():
                            detected_conversation_id = raw_conversation_id.strip()

                        raw_result = event.get("result")
                        if isinstance(raw_result, str):
                            result_text = raw_result

                        if bool(event.get("is_error")):
                            if isinstance(raw_result, str) and raw_result.strip():
                                error_messages.append(raw_result.strip())
                            else:
                                error_messages.append("Claude returned an error result.")
                        continue

                    if event_type == "error":
                        message_text = event.get("error") or event.get("message")
                        if isinstance(message_text, str) and message_text.strip():
                            error_messages.append(message_text.strip())
                        continue

                    if event_type == "system":
                        subtype = str(event.get("subtype") or "")
                        if subtype in {"error", "warning"}:
                            raw_message = event.get("message") or event.get("output")
                            if isinstance(raw_message, str) and raw_message.strip():
                                self._emit_system_message(request_token, raw_message.strip())
                        continue

                elif mode == "json":
                    event = self._parse_json_line(stripped)
                    if event is None:
                        continue
                    parsed_json = True

                    raw_conversation_id = event.get("conversation_id") or event.get("session_id")
                    if isinstance(raw_conversation_id, str) and raw_conversation_id.strip():
                        detected_conversation_id = raw_conversation_id.strip()

                    raw_result = event.get("result")
                    if isinstance(raw_result, str):
                        result_text = raw_result

                    if bool(event.get("is_error")):
                        if isinstance(raw_result, str) and raw_result.strip():
                            error_messages.append(raw_result.strip())
                        else:
                            error_messages.append("Claude returned an error result.")

                else:
                    if line:
                        assistant_parts.append(line + "\n")
                        streamed_assistant = True
                        self._emit_assistant_chunk(request_token, line + "\n")

        return_code = process.wait()

        unsupported_output = False
        if mode in {"stream-json", "json"}:
            combined = "\n".join(captured_output).lower()
            unsupported_output = (
                "output-format" in combined
                and (
                    "unknown option" in combined
                    or "invalid value" in combined
                    or "requires --verbose" in combined
                    or "only works with --print" in combined
                    or "must be one of" in combined
                )
            )
            if mode == "stream-json" and not parsed_json and return_code != 0:
                unsupported_output = unsupported_output or "error" in combined

        assistant_text = "".join(assistant_parts)
        if not assistant_text.strip() and isinstance(result_text, str) and result_text.strip():
            assistant_text = result_text
            streamed_assistant = True
            self._emit_assistant_chunk(request_token, result_text)

        error_message: str | None = None
        if error_messages:
            error_message = error_messages[-1]
        elif return_code != 0:
            output_hint = captured_output[-1] if captured_output else "Claude exited with an error."
            error_message = output_hint

        success = return_code == 0 and not error_messages

        return (
            ClaudeRunResult(
                success=success,
                assistant_text=assistant_text,
                streamed_assistant=streamed_assistant,
                conversation_id=detected_conversation_id,
                error_message=error_message,
            ),
            unsupported_output,
        )

    @staticmethod
    def _parse_json_line(value: str) -> dict[str, Any] | None:
        if not value:
            return None
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None

    @staticmethod
    def _extract_assistant_content(message: Any) -> tuple[list[str], list[str]]:
        texts: list[str] = []
        tools: list[str] = []

        if not isinstance(message, dict):
            return texts, tools

        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = str(block.get("type") or "")

                if block_type == "text":
                    chunk = block.get("text")
                    if isinstance(chunk, str) and chunk:
                        texts.append(chunk)
                    continue

                if block_type == "tool_use":
                    tool_name = str(block.get("name") or "tool")
                    tools.append(f"Tool use: {tool_name}")
                    continue

            return texts, tools

        if isinstance(content, str) and content:
            texts.append(content)

        return texts, tools

    def _emit_running_changed(self, request_token: str, running: bool) -> None:
        GLib.idle_add(self._on_running_changed, request_token, running)

    def _emit_assistant_chunk(self, request_token: str, chunk: str) -> None:
        GLib.idle_add(self._on_assistant_chunk, request_token, chunk)

    def _emit_system_message(self, request_token: str, message: str) -> None:
        GLib.idle_add(self._on_system_message, request_token, message)

    def _emit_complete(self, request_token: str, result: ClaudeRunResult) -> None:
        GLib.idle_add(self._on_complete, request_token, result)


class ClaudeCodeWindow(Gtk.Window):
    """Single-window Claude Code shell with WebKit2 chat UI and session context."""

    def __init__(self) -> None:
        super().__init__(title=APP_NAME)
        self.set_decorated(True)
        self.set_default_size(APP_DEFAULT_WIDTH, APP_DEFAULT_HEIGHT)
        self.set_size_request(APP_MIN_WIDTH, APP_MIN_HEIGHT)

        self._webview: WebKit2.WebView | None = None
        self._webview_user_content_manager: WebKit2.UserContentManager | None = None
        self._webview_ready = False
        self._pending_webview_scripts: list[str] = []
        self._chat_shell: Gtk.EventBox | None = None

        self._sidebar_container: Gtk.Box | None = None
        self._sidebar_current_width = float(SIDEBAR_OPEN_WIDTH)
        self._sidebar_expanded = True
        self._sidebar_animation_id: int | None = None

        self._window_fade_animation_id: int | None = None
        self._window_fade_started = False

        self._status_fade_animation_id: int | None = None
        self._status_fade_widgets: list[Gtk.Widget] = []
        self._chat_reveal_animation_id: int | None = None
        self._chat_reveal_widgets: list[tuple[Gtk.Widget, float]] = []
        self._chat_pulse_animation_id: int | None = None

        self._project_status_label: Gtk.Label | None = None
        self._recent_folder_combo: Gtk.ComboBoxText | None = None
        self._recent_folder_values: list[str] = []
        self._session_list_box: Gtk.Box | None = None
        self._session_empty_label: Gtk.Label | None = None

        self._connection_dot: Gtk.Label | None = None
        self._connection_label: Gtk.Label | None = None
        self._context_usage_label: Gtk.Label | None = None
        self._context_progress: Gtk.ProgressBar | None = None
        self._status_message_label: Gtk.Label | None = None
        self._session_timer_label: Gtk.Label | None = None
        self._last_status_message = ""
        self._context_char_count = 0

        self._suppress_recent_combo_change = False
        self._request_temp_files: dict[str, list[str]] = {}

        self._selected_model_index = 1
        self._selected_permission_index = 0

        self._project_folder = normalize_folder(os.getcwd())
        self._recent_folders = load_recent_folders(self._project_folder)

        self._binary_path = self._find_claude_binary()
        self._supports_model_flag = False
        self._supports_permission_flag = False
        self._supports_output_format_flag = False
        self._supports_stream_json = False
        self._supports_json = False
        self._stream_json_requires_verbose = True

        self._claude_process = ClaudeProcess(
            on_running_changed=self._on_process_running_changed,
            on_assistant_chunk=self._on_process_assistant_chunk,
            on_system_message=self._on_process_system_message,
            on_complete=self._on_process_complete,
        )

        self._conversation_id: str | None = None
        self._active_request_token: str | None = None
        self._has_messages = False
        self._last_request_failed = False

        self._session_started_us = GLib.get_monotonic_time()
        self._session_timer_id: int | None = None
        self._sessions: list[SessionRecord] = []
        self._active_session_id: str | None = None

        self._set_dark_theme_preference()
        self._install_css()
        self._build_ui()
        self._load_sessions_into_state()
        self._refresh_session_list()
        GLib.idle_add(self._refresh_session_list_idle)

        self.connect("destroy", self._on_destroy)
        self.connect("map-event", self._on_map_event)

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            self._show_missing_binary_error()
            self._start_status_fade_in()
            return

        self._detect_cli_flag_support(self._binary_path)
        self._refresh_connection_state()

        if self._active_session_id is None:
            self._set_status_message("No active session. Click + New Chat to start.", STATUS_INFO)
        else:
            self._set_status_message("Session ready. Type a message below.", STATUS_MUTED)

        self._start_status_fade_in()

    @staticmethod
    def _set_dark_theme_preference() -> None:
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_STYLES.encode("utf-8"))

        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("app-root")
        self.add(root)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        content.get_style_context().add_class("main-content")
        root.pack_start(content, True, True, 0)

        sidebar = self._build_sidebar()
        content.pack_start(sidebar, False, False, 0)

        chat_panel = self._build_chat_panel()
        content.pack_start(chat_panel, True, True, 0)

        status_bar = self._build_status_bar()
        root.pack_end(status_bar, False, False, 0)

        self._refresh_recent_folder_combo()
        self._update_project_folder_labels()
        self._update_status_model_and_permission()
        self._update_context_indicator()
        self._start_chat_reveal_in()

        self._session_timer_id = GLib.timeout_add_seconds(1, self._update_session_timer)

    def _build_sidebar(self) -> Gtk.Box:
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.get_style_context().add_class("sidebar")
        sidebar.set_hexpand(False)
        sidebar.set_vexpand(True)
        sidebar.set_size_request(SIDEBAR_OPEN_WIDTH, -1)
        self._sidebar_container = sidebar

        new_session_button = Gtk.Button(label="+ New Chat")
        new_session_button.set_relief(Gtk.ReliefStyle.NONE)
        new_session_button.set_hexpand(True)
        new_session_button.set_halign(Gtk.Align.FILL)
        new_session_button.get_style_context().add_class("new-session-button")
        new_session_button._drag_blocker = True
        new_session_button.connect("clicked", self._on_new_session_clicked)
        sidebar.pack_start(new_session_button, False, False, 0)

        sessions_title = Gtk.Label(label="Sessions")
        sessions_title.set_xalign(0.0)
        sessions_title.get_style_context().add_class("sidebar-section-title")
        sidebar.pack_start(sessions_title, False, False, 0)

        session_scroll = Gtk.ScrolledWindow()
        session_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        session_scroll.set_shadow_type(Gtk.ShadowType.NONE)
        session_scroll.get_style_context().add_class("session-scroll")
        session_scroll.set_vexpand(True)
        sidebar.pack_start(session_scroll, True, True, 0)

        session_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        session_list.get_style_context().add_class("session-list")
        session_scroll.add(session_list)
        self._session_list_box = session_list

        empty = Gtk.Label(label="No chats yet. Click + New Chat.")
        empty.set_line_wrap(True)
        empty.set_xalign(0.0)
        empty.get_style_context().add_class("session-empty")
        session_list.pack_start(empty, False, False, 0)
        self._session_empty_label = empty

        return sidebar

    def _build_chat_panel(self) -> Gtk.Box:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel.set_hexpand(True)
        panel.set_vexpand(True)

        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrap.get_style_context().add_class("chat-wrap")
        wrap.set_hexpand(True)
        wrap.set_vexpand(True)
        panel.pack_start(wrap, True, True, 0)

        overlay = Gtk.Overlay()
        overlay.set_hexpand(True)
        overlay.set_vexpand(True)
        wrap.pack_start(overlay, True, True, 0)

        shell = Gtk.EventBox()
        shell.set_visible_window(True)
        shell.set_hexpand(True)
        shell.set_vexpand(True)
        shell.get_style_context().add_class("chat-shell")
        overlay.add(shell)
        self._chat_shell = shell
        self._chat_reveal_widgets = [(shell, 60.0)]
        for widget, _ in self._chat_reveal_widgets:
            widget.set_opacity(0.0)

        sidebar_toggle = Gtk.Button(label="☰")
        sidebar_toggle.set_relief(Gtk.ReliefStyle.NONE)
        sidebar_toggle.get_style_context().add_class("sidebar-toggle-gtk")
        sidebar_toggle.get_style_context().add_class("chat-overlay-toggle")
        sidebar_toggle.set_halign(Gtk.Align.START)
        sidebar_toggle.set_valign(Gtk.Align.START)
        sidebar_toggle.set_margin_start(8)
        sidebar_toggle.set_margin_top(8)
        sidebar_toggle._drag_blocker = True
        sidebar_toggle.connect("clicked", self._on_sidebar_toggle_clicked)
        overlay.add_overlay(sidebar_toggle)

        manager = WebKit2.UserContentManager()
        manager.register_script_message_handler("sendMessage")
        manager.register_script_message_handler("changeModel")
        manager.register_script_message_handler("changePermission")
        manager.register_script_message_handler("changeFolder")
        manager.register_script_message_handler("attachFile")
        manager.connect("script-message-received::sendMessage", self._on_js_send_message)
        manager.connect("script-message-received::changeModel", self._on_js_change_model)
        manager.connect("script-message-received::changePermission", self._on_js_change_permission)
        manager.connect("script-message-received::changeFolder", self._on_js_change_folder)
        manager.connect("script-message-received::attachFile", self._on_js_attach_file)
        self._webview_user_content_manager = manager

        webview = WebKit2.WebView.new_with_user_content_manager(manager)
        webview.set_hexpand(True)
        webview.set_vexpand(True)
        webview.connect("load-changed", self._on_webview_load_changed)
        webview.connect("focus-in-event", self._on_webview_focus_in)
        webview.connect("focus-out-event", self._on_webview_focus_out)

        settings = webview.get_settings()
        if settings is not None:
            settings.set_enable_write_console_messages_to_stdout(False)
            settings.set_enable_developer_extras(False)
            settings.set_enable_javascript(True)

        webview.load_html(CHAT_WEBVIEW_HTML, "")
        shell.add(webview)
        self._webview = webview

        return panel

    def _build_status_bar(self) -> Gtk.Box:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.get_style_context().add_class("bottom-bar")

        dot = Gtk.Label(label="●")
        dot.get_style_context().add_class("connection-dot")
        bar.pack_start(dot, False, False, 0)
        self._connection_dot = dot

        connection_label = Gtk.Label(label="Disconnected")
        connection_label.set_xalign(0.0)
        connection_label.get_style_context().add_class("status-label")
        bar.pack_start(connection_label, False, False, 0)
        self._connection_label = connection_label

        context_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.pack_start(context_box, False, False, 0)

        context_label = Gtk.Label(label="Context: ~0 / 200k")
        context_label.get_style_context().add_class("context-label")
        context_box.pack_start(context_label, False, False, 0)
        self._context_usage_label = context_label

        context_progress = Gtk.ProgressBar()
        context_progress.set_show_text(False)
        context_progress.set_fraction(0.0)
        context_progress.set_size_request(108, 6)
        context_progress.get_style_context().add_class("context-progress")
        context_box.pack_start(context_progress, False, False, 0)
        self._context_progress = context_progress

        status_message = Gtk.Label(label="")
        status_message.set_xalign(0.0)
        status_message.set_hexpand(True)
        status_message.set_single_line_mode(True)
        status_message.set_ellipsize(Pango.EllipsizeMode.END)
        status_message.get_style_context().add_class("status-label")
        bar.pack_start(status_message, True, True, 0)
        self._status_message_label = status_message

        self._project_status_label = None

        timer = Gtk.Label(label="00:00:00")
        timer.get_style_context().add_class("bottom-timer")
        bar.pack_end(timer, False, False, 0)
        self._session_timer_label = timer

        self._status_fade_widgets = [
            bar,
            dot,
            connection_label,
            context_label,
            context_progress,
            status_message,
            timer,
        ]
        for widget in self._status_fade_widgets:
            widget.set_opacity(0.0)

        self._set_connection_state(CONNECTION_DISCONNECTED)
        self._set_status_message("Ready", STATUS_MUTED)
        self._update_context_indicator()
        self._update_status_model_and_permission()

        return bar

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(value, 1.0))

    @staticmethod
    def _ease_out_cubic(progress: float) -> float:
        p = ClaudeCodeWindow._clamp01(progress)
        return 1.0 - (1.0 - p) ** 3

    @staticmethod
    def _ease_in_out_cubic(progress: float) -> float:
        p = ClaudeCodeWindow._clamp01(progress)
        return 3.0 * p * p - 2.0 * p * p * p

    def _session_sort_key(self, session: SessionRecord) -> float:
        return parse_timestamp(session.last_used_at or session.created_at)

    def _find_session(self, session_id: str | None) -> SessionRecord | None:
        if session_id is None:
            return None
        for session in self._sessions:
            if session.id == session_id:
                return session
        return None

    def _get_active_session(self) -> SessionRecord | None:
        return self._find_session(self._active_session_id)

    def _model_index_from_value(self, model_value: str) -> int:
        for index, (_, value) in enumerate(MODEL_OPTIONS):
            if value == model_value:
                return index
        return 0

    def _permission_index_from_value(self, permission_mode: str) -> int:
        for index, (_, value, _) in enumerate(PERMISSION_OPTIONS):
            if value == permission_mode:
                return index
        return 0

    def _save_sessions_safe(self, context: str) -> bool:
        try:
            save_sessions(self._sessions)
            return True
        except (OSError, ValueError, TypeError) as error:
            self._set_status_message(f"{context}: {error}", STATUS_WARNING)
            return False

    def _reset_conversation_state(self, reason: str, reset_timer: bool = True) -> None:
        if reset_timer:
            self._session_started_us = GLib.get_monotonic_time()
        self._interrupt_running_process(reason)
        self._conversation_id = None
        self._clear_messages()
        self._show_welcome()
        self._set_typing(False)
        self._has_messages = False
        self._last_request_failed = False

    def _promote_replacement_session(self) -> SessionRecord | None:
        candidates = [s for s in self._sessions if s.status != SESSION_STATUS_ARCHIVED]
        if not candidates:
            self._active_session_id = None
            return None
        replacement = max(candidates, key=self._session_sort_key)
        self._active_session_id = replacement.id
        replacement.status = SESSION_STATUS_ACTIVE
        replacement.last_used_at = current_timestamp()
        self._apply_session_to_controls(replacement, add_to_recent=os.path.isdir(replacement.project_path))
        return replacement

    def _cancel_timer(self, attr: str) -> None:
        timer_id = getattr(self, attr, None)
        if timer_id is not None:
            GLib.source_remove(timer_id)
            setattr(self, attr, None)

    def _load_sessions_into_state(self) -> None:
        try:
            self._sessions = load_sessions()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self._sessions = []
            self._active_session_id = None
            self._set_status_message(f"Could not load sessions: {error}", STATUS_WARNING)
            return

        if not self._sessions:
            self._active_session_id = None
            return

        active_candidates = [s for s in self._sessions if s.status != SESSION_STATUS_ARCHIVED]
        if not active_candidates:
            self._active_session_id = None
            return

        selected = max(active_candidates, key=self._session_sort_key)
        changed = False

        for session in active_candidates:
            if session.id == selected.id:
                if session.status != SESSION_STATUS_ACTIVE:
                    session.status = SESSION_STATUS_ACTIVE
                    changed = True
            elif session.status == SESSION_STATUS_ACTIVE:
                session.status = SESSION_STATUS_ENDED
                changed = True

        self._active_session_id = selected.id
        self._apply_session_to_controls(selected, add_to_recent=os.path.isdir(selected.project_path))
        self._conversation_id = None

        if changed:
            self._save_sessions_safe("Could not save session state")

    def _apply_session_to_controls(self, session: SessionRecord, add_to_recent: bool) -> None:
        self._project_folder = session.project_path
        self._selected_model_index = self._model_index_from_value(session.model)
        self._selected_permission_index = self._permission_index_from_value(session.permission_mode)

        if add_to_recent and os.path.isdir(self._project_folder):
            self._add_recent_folder(self._project_folder)

        self._refresh_recent_folder_combo()
        self._update_project_folder_labels()
        self._update_status_model_and_permission()
        self._update_context_indicator()

    def _build_session_title(self, folder: str, timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(timestamp)
        except ValueError:
            dt = datetime.now().astimezone()
        name = Path(folder).name or folder
        return f"{name} - {dt.strftime('%H:%M')}"

    def _create_session_record(self, folder: str) -> SessionRecord:
        normalized = normalize_folder(folder)
        now = current_timestamp()
        _, model_value = MODEL_OPTIONS[self._selected_model_index]
        _, permission_value, _ = PERMISSION_OPTIONS[self._selected_permission_index]
        return SessionRecord(
            id=str(uuid.uuid4()),
            title=self._build_session_title(normalized, now),
            project_path=normalized,
            model=model_value,
            permission_mode=permission_value,
            status=SESSION_STATUS_ACTIVE,
            created_at=now,
            last_used_at=now,
        )

    def _set_active_session_status(self, status: str) -> None:
        session = self._get_active_session()
        if session is None:
            return
        if status not in SESSION_STATUSES:
            return
        session.status = status
        session.last_used_at = current_timestamp()
        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

    @staticmethod
    def _clear_box(box: Gtk.Box) -> None:
        for child in box.get_children():
            box.remove(child)

    @staticmethod
    def _session_time_bucket(timestamp_value: str) -> str:
        now = datetime.now().astimezone().date()
        try:
            session_date = datetime.fromisoformat(timestamp_value).astimezone().date()
        except ValueError:
            return "Älter"

        delta_days = (now - session_date).days
        if delta_days <= 0:
            return "Heute"
        if delta_days == 1:
            return "Gestern"
        if delta_days <= 7:
            return "Diese Woche"
        return "Älter"

    def _make_session_row(self, session: SessionRecord, allow_open: bool) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        row.get_style_context().add_class("session-row")
        if session.id == self._active_session_id:
            row.get_style_context().add_class("session-row-active")

        open_button = Gtk.Button()
        open_button.set_relief(Gtk.ReliefStyle.NONE)
        open_button.get_style_context().add_class("session-open-button")
        open_button._drag_blocker = True
        open_button.set_hexpand(True)
        open_button.set_halign(Gtk.Align.FILL)
        open_button.set_sensitive(allow_open)
        open_button.connect("clicked", lambda _button, sid=session.id: self._switch_to_session(sid))
        title = Gtk.Label(label=session.title or "New chat")
        title.set_xalign(0.0)
        title.get_style_context().add_class("session-title")

        open_button.add(title)
        row.pack_start(open_button, True, True, 0)

        menu_button = Gtk.MenuButton(label="⋯")
        menu_button.set_relief(Gtk.ReliefStyle.NONE)
        menu_button.get_style_context().add_class("session-menu-button")
        menu_button._drag_blocker = True

        popover = Gtk.Popover.new(menu_button)
        popover.get_style_context().add_class("session-popover")
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        menu_box.set_border_width(6)

        archive_button = Gtk.ModelButton(label="Archive")
        archive_button.connect("clicked", lambda _button, sid=session.id: self._archive_session(sid))
        menu_box.pack_start(archive_button, False, False, 0)

        delete_button = Gtk.ModelButton(label="Delete")
        delete_button.connect("clicked", lambda _button, sid=session.id: self._delete_session(sid))
        menu_box.pack_start(delete_button, False, False, 0)

        popover.add(menu_box)
        menu_box.show_all()
        menu_button.set_popover(popover)
        row.pack_end(menu_button, False, False, 0)

        def on_row_button_press(_widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
            if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
                try:
                    menu_button.popup()
                except Exception:
                    popover.show_all()
                return True
            return False

        row.connect("button-press-event", on_row_button_press)

        return row

    def _refresh_session_list(self) -> None:
        if self._session_list_box is None or self._session_empty_label is None:
            return

        self._clear_box(self._session_list_box)
        visible_sessions = sorted(
            [s for s in self._sessions if s.status != SESSION_STATUS_ARCHIVED],
            key=self._session_sort_key,
            reverse=True,
        )
        if not visible_sessions:
            self._session_list_box.pack_start(self._session_empty_label, False, False, 0)
            self._session_empty_label.show()
            return

        grouped: dict[str, list[SessionRecord]] = {
            "Heute": [],
            "Gestern": [],
            "Diese Woche": [],
            "Älter": [],
        }
        for session in visible_sessions:
            bucket = self._session_time_bucket(session.last_used_at or session.created_at)
            grouped.setdefault(bucket, []).append(session)

        for group_name in ("Heute", "Gestern", "Diese Woche", "Älter"):
            sessions = grouped.get(group_name, [])
            if not sessions:
                continue
            label = Gtk.Label(label=group_name)
            label.set_xalign(0.0)
            label.get_style_context().add_class("session-group-label")
            self._session_list_box.pack_start(label, False, False, 0)

            for session in sessions:
                row = self._make_session_row(session, allow_open=True)
                self._session_list_box.pack_start(row, False, False, 0)

        self._session_list_box.show_all()

    def _refresh_session_list_idle(self) -> bool:
        self._refresh_session_list()
        return False

    def _show_folder_dialog(self, title: str) -> str | None:
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.set_create_folders(True)
        dialog.set_show_hidden(True)
        dialog.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Select Folder",
            Gtk.ResponseType.OK,
        )
        dialog.set_modal(True)
        if os.path.isdir(self._project_folder):
            dialog.set_current_folder(self._project_folder)

        response = dialog.run()
        selected = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        return selected

    def _switch_to_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        if session is None:
            return
        if session.status == SESSION_STATUS_ARCHIVED:
            self._set_status_message("Archived sessions cannot be opened", STATUS_WARNING)
            return
        if session.id == self._active_session_id and session.status == SESSION_STATUS_ACTIVE:
            self._set_status_message("Session already active", STATUS_MUTED)
            return

        current = self._get_active_session()
        if current is not None and current.id != session.id and current.status != SESSION_STATUS_ARCHIVED:
            current.status = SESSION_STATUS_ENDED
            current.last_used_at = current_timestamp()

        self._active_session_id = session.id
        session.status = SESSION_STATUS_ACTIVE
        session.last_used_at = current_timestamp()
        self._apply_session_to_controls(session, add_to_recent=os.path.isdir(session.project_path))
        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        self._reset_conversation_state("Session switched")

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        self._refresh_connection_state()
        self._set_status_message("Session switched. Conversation reset.", STATUS_INFO)

    def _archive_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        if session is None or session.status == SESSION_STATUS_ARCHIVED:
            return

        was_active = session.id == self._active_session_id
        session.status = SESSION_STATUS_ARCHIVED
        session.last_used_at = current_timestamp()

        replacement = self._promote_replacement_session() if was_active else None

        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        if was_active and replacement is not None:
            self._reset_conversation_state("Active session archived")
            self._refresh_connection_state()
            self._set_status_message("Archived session. Switched to replacement.", STATUS_INFO)
            return

        if was_active and replacement is None:
            self._reset_conversation_state("Session archived", reset_timer=False)
            self._set_status_message("Session archived", STATUS_MUTED)
            self._refresh_connection_state()
            self._refresh_recent_folder_combo()
            return

        self._set_status_message("Session archived", STATUS_MUTED)

    def _delete_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        if session is None:
            return

        was_active = session.id == self._active_session_id
        self._sessions = [item for item in self._sessions if item.id != session_id]

        replacement = self._promote_replacement_session() if was_active else None

        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        if was_active and replacement is not None:
            self._reset_conversation_state("Active session deleted")
            self._refresh_connection_state()
            self._set_status_message("Deleted session. Switched to replacement.", STATUS_INFO)
            return

        if was_active and replacement is None:
            self._reset_conversation_state("Session deleted", reset_timer=False)
            self._set_status_message("Session deleted", STATUS_MUTED)
            self._refresh_connection_state()
            return

        self._set_status_message("Session deleted", STATUS_MUTED)

    def _start_new_session(self, folder: str) -> None:
        normalized = normalize_folder(folder)
        if not os.path.isdir(normalized):
            self._set_status_message("Selected path is not a folder", STATUS_ERROR)
            return

        current = self._get_active_session()
        if current is not None and current.status != SESSION_STATUS_ARCHIVED:
            current.status = SESSION_STATUS_ENDED
            current.last_used_at = current_timestamp()

        created = self._create_session_record(normalized)
        self._sessions.insert(0, created)
        self._active_session_id = created.id
        self._apply_session_to_controls(created, add_to_recent=True)
        self._refresh_session_list()
        self._save_sessions_safe("Could not save sessions")

        self._reset_conversation_state("New session started")

        if self._binary_path is None:
            self._set_connection_state(CONNECTION_DISCONNECTED)
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        self._refresh_connection_state()
        self._set_status_message("New session ready", STATUS_INFO)

    def _refresh_recent_folder_combo(self) -> None:
        if self._recent_folder_combo is None:
            return

        folders: list[str] = []
        for raw_folder in self._recent_folders:
            candidate = str(raw_folder).strip()
            if not candidate:
                continue
            try:
                normalized = normalize_folder(candidate)
            except OSError:
                continue
            if not os.path.isdir(normalized):
                continue
            if normalized in folders:
                continue
            folders.append(normalized)

        if os.path.isdir(self._project_folder) and self._project_folder not in folders:
            folders.insert(0, self._project_folder)

        self._recent_folders = folders[:RECENT_FOLDERS_LIMIT]

        self._suppress_recent_combo_change = True
        self._recent_folder_combo.remove_all()
        self._recent_folder_values = list(self._recent_folders)

        for folder in self._recent_folder_values:
            formatted = format_path(folder)
            self._recent_folder_combo.append_text(shorten_path(formatted, 52))

        if self._recent_folder_values:
            active_index = 0
            if self._project_folder in self._recent_folder_values:
                active_index = self._recent_folder_values.index(self._project_folder)

            self._recent_folder_combo.set_active(active_index)
            self._recent_folder_combo.set_tooltip_text(
                format_path(self._recent_folder_values[active_index])
            )
            self._recent_folder_combo.set_sensitive(True)
        else:
            self._recent_folder_combo.set_active(-1)
            self._recent_folder_combo.set_tooltip_text("No recent folders")
            self._recent_folder_combo.set_sensitive(False)

        self._suppress_recent_combo_change = False

    def _update_project_folder_labels(self) -> None:
        full_display = format_path(self._project_folder)

        if self._project_status_label is not None:
            self._project_status_label.set_text(shorten_path(full_display, 44))
            tooltip = full_display
            if self._last_status_message:
                tooltip = f"{full_display}\n{self._last_status_message}"
            self._project_status_label.set_tooltip_text(tooltip)

        self._call_js("updateFolder", full_display)

    def _update_status_model_and_permission(self) -> None:
        _, model_value = MODEL_OPTIONS[self._selected_model_index]
        _, permission_value, _ = PERMISSION_OPTIONS[self._selected_permission_index]
        self._call_js("updateModel", model_value)
        self._call_js("updatePermission", permission_value)

    @staticmethod
    def _format_token_count(value: int) -> str:
        if value >= 100_000:
            return f"{round(value / 1000):.0f}k"
        if value >= 1000:
            return f"{value / 1000:.1f}k"
        return str(value)

    def _update_context_indicator(self) -> None:
        estimated_tokens = max(0, self._context_char_count // 4)
        ratio = max(0.0, min(1.0, estimated_tokens / float(CONTEXT_MAX_TOKENS)))
        formatted_tokens = self._format_token_count(estimated_tokens)

        if self._context_usage_label is not None:
            self._context_usage_label.set_text(f"Context: ~{formatted_tokens} / 200k")

        if self._context_progress is not None:
            self._context_progress.set_fraction(ratio)
            context = self._context_progress.get_style_context()
            context.remove_class("context-warn")
            context.remove_class("context-high")
            if ratio > 0.8:
                context.add_class("context-high")
            elif ratio >= 0.5:
                context.add_class("context-warn")

        tooltip = (
            f"Context usage: ~{estimated_tokens} tokens / {CONTEXT_MAX_TOKENS} max. "
            "Next reset on new session."
        )
        if self._context_usage_label is not None:
            self._context_usage_label.set_tooltip_text(tooltip)
        if self._context_progress is not None:
            self._context_progress.set_tooltip_text(tooltip)

    def _set_connection_state(self, state: str) -> None:
        text_map = {
            CONNECTION_CONNECTED: "Connected",
            CONNECTION_DISCONNECTED: "Disconnected",
            CONNECTION_STARTING: "Starting",
            CONNECTION_ERROR: "Error",
        }
        state_text = text_map.get(state, "Disconnected")

        if self._connection_label is not None:
            self._connection_label.set_text(state_text)

        if self._connection_dot is None:
            return

        context = self._connection_dot.get_style_context()
        for css_class in (
            "state-connected",
            "state-disconnected",
            "state-starting",
            "state-error",
        ):
            context.remove_class(css_class)
        context.add_class(f"state-{state}")
        if self._last_status_message:
            self._connection_dot.set_tooltip_text(f"{state_text}\n{self._last_status_message}")
        else:
            self._connection_dot.set_tooltip_text(state_text)

    def _binary_exists(self) -> bool:
        if not self._binary_path:
            return False
        return os.path.isfile(self._binary_path) and os.access(self._binary_path, os.X_OK)

    def _refresh_connection_state(self) -> None:
        if not self._binary_exists():
            self._set_connection_state(CONNECTION_DISCONNECTED)
            return
        if self._claude_process.is_running():
            self._set_connection_state(CONNECTION_STARTING)
            return
        if self._last_request_failed:
            self._set_connection_state(CONNECTION_ERROR)
            return
        self._set_connection_state(CONNECTION_CONNECTED)

    def _set_status_message(self, message: str, severity: str = STATUS_MUTED) -> None:
        self._last_status_message = message
        self._update_project_folder_labels()
        if self._connection_dot is not None:
            existing = self._connection_dot.get_tooltip_text() or "Disconnected"
            state_text = existing.splitlines()[0] if existing else "Disconnected"
            self._connection_dot.set_tooltip_text(f"{state_text}\n{message}")

        if self._status_message_label is None:
            return

        self._status_message_label.set_text(message)
        context = self._status_message_label.get_style_context()
        for css_class in ("status-muted", "status-info", "status-warning", "status-error"):
            context.remove_class(css_class)

        severity_map = {
            STATUS_MUTED: "status-muted",
            STATUS_INFO: "status-info",
            STATUS_WARNING: "status-warning",
            STATUS_ERROR: "status-error",
        }
        context.add_class(severity_map.get(severity, "status-muted"))

    def _add_recent_folder(self, folder: str) -> None:
        normalized = normalize_folder(folder)
        updated = [normalized] + [item for item in self._recent_folders if item != normalized]
        self._recent_folders = updated[:RECENT_FOLDERS_LIMIT]

        try:
            save_recent_folders(self._recent_folders)
        except OSError as error:
            self._set_status_message(
                f"Could not save recent folders: {error}",
                STATUS_WARNING,
            )

    def _set_project_folder(self, folder: str, restart_session: bool) -> None:
        normalized = normalize_folder(folder)
        if not os.path.isdir(normalized):
            self._set_status_message("Selected path is not a folder", STATUS_ERROR)
            return

        self._project_folder = normalized
        self._add_recent_folder(normalized)
        self._refresh_recent_folder_combo()
        self._update_project_folder_labels()
        self._update_context_indicator()

        active_session = self._get_active_session()
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            active_session.project_path = normalized
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()

        self._set_status_message(
            f"Project folder set to {shorten_path(format_path(normalized), 40)}",
            STATUS_INFO,
        )

        if restart_session and self._active_session_id is not None:
            self._interrupt_running_process("Folder changed")
            self._conversation_id = None
            self._add_system_message("Conversation reset because the project folder changed.")
            self._last_request_failed = False
            self._refresh_connection_state()

    def _detect_cli_flag_support(self, binary_path: str) -> None:
        self._supports_model_flag = False
        self._supports_permission_flag = False
        self._supports_output_format_flag = False
        self._supports_stream_json = False
        self._supports_json = False

        try:
            result = subprocess.run(
                [binary_path, "--help"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return

        output = f"{result.stdout}\n{result.stderr}".lower()
        self._supports_model_flag = "--model" in output
        self._supports_permission_flag = "--permission-mode" in output
        self._supports_output_format_flag = "--output-format" in output
        self._supports_stream_json = "stream-json" in output
        self._supports_json = '"json"' in output or "json" in output

    @staticmethod
    def _find_claude_binary() -> str | None:
        for executable in ("claude", "claude-code"):
            found = shutil.which(executable)
            if found:
                return found

        config_root = Path.home() / ".config" / "Claude" / "claude-code"
        candidates = (
            config_root / "claude",
            config_root / "claude-code",
            config_root / "bin" / "claude",
            config_root / "bin" / "claude-code",
        )
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)

        if config_root.is_dir():
            for binary_name in ("claude", "claude-code"):
                for candidate in config_root.rglob(binary_name):
                    if candidate.is_file() and os.access(candidate, os.X_OK):
                        return str(candidate)

        return None

    def _show_missing_binary_error(self) -> None:
        self._add_system_message(
            "Claude CLI was not found. Searched for claude, claude-code, and ~/.config/Claude/claude-code/."
        )

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Claude CLI not found",
        )
        dialog.format_secondary_text(
            "Install Claude Code CLI (binary `claude` or `claude-code`) or place it under "
            "~/.config/Claude/claude-code/."
        )
        dialog.run()
        dialog.destroy()

    def _invalidate_active_request(self) -> None:
        self._active_request_token = None

    def _is_current_request(self, request_token: str) -> bool:
        return bool(request_token) and request_token == self._active_request_token

    def _interrupt_running_process(self, reason: str) -> None:
        self._invalidate_active_request()
        if not self._claude_process.is_running():
            return

        self._claude_process.stop()
        self._set_typing(False)
        self._add_system_message(f"Stopped current request: {reason}")
        self._refresh_connection_state()

    def _prompt_for_project_folder(self) -> None:
        selected = self._show_folder_dialog("Select Project Folder")
        if selected is None:
            return

        self._set_project_folder(selected, restart_session=self._active_session_id is not None)

    def _on_choose_folder_clicked(self, _button: Gtk.Button) -> None:
        self._prompt_for_project_folder()

    def _on_recent_folder_changed(self, combo: Gtk.ComboBoxText) -> None:
        if self._suppress_recent_combo_change:
            return

        index = combo.get_active()
        if index < 0 or index >= len(self._recent_folder_values):
            return

        chosen_folder = self._recent_folder_values[index]
        if chosen_folder == self._project_folder:
            return

        self._set_project_folder(chosen_folder, restart_session=self._active_session_id is not None)

    def _on_js_change_folder(
        self,
        _manager: WebKit2.UserContentManager,
        _js_result: WebKit2.JavascriptResult,
    ) -> None:
        self._prompt_for_project_folder()

    def _apply_model_selection(self, index: int) -> None:
        if index < 0 or index >= len(MODEL_OPTIONS):
            return

        if index == self._selected_model_index:
            self._update_status_model_and_permission()
            return

        self._selected_model_index = index
        self._update_status_model_and_permission()
        self._update_context_indicator()
        active_session = self._get_active_session()
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            active_session.model = MODEL_OPTIONS[index][1]
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()
        if self._has_messages and self._claude_process.is_running():
            self._interrupt_running_process("Model changed")
        if self._has_messages:
            self._conversation_id = None
            self._set_status_message("Model updated. Next message starts a new Claude conversation.", STATUS_INFO)
            return
        self._set_status_message("Model updated", STATUS_INFO)

    def _apply_permission_selection(self, index: int) -> None:
        if index < 0 or index >= len(PERMISSION_OPTIONS):
            return

        if index == self._selected_permission_index:
            self._update_status_model_and_permission()
            return

        self._selected_permission_index = index
        self._update_status_model_and_permission()
        self._update_context_indicator()
        active_session = self._get_active_session()
        if active_session is not None and active_session.status != SESSION_STATUS_ARCHIVED:
            active_session.permission_mode = PERMISSION_OPTIONS[index][1]
            active_session.last_used_at = current_timestamp()
            self._save_sessions_safe("Could not save sessions")
            self._refresh_session_list()
        if self._has_messages and self._claude_process.is_running():
            self._interrupt_running_process("Permission mode changed")
        if self._has_messages:
            self._conversation_id = None
            self._set_status_message(
                "Permission mode updated. Next message starts a new Claude conversation.",
                STATUS_INFO,
            )
            return
        self._set_status_message("Permission mode updated", STATUS_INFO)

    def _on_new_session_clicked(self, _button: Gtk.Button) -> None:
        if not os.path.isdir(self._project_folder):
            self._set_status_message("Current project folder is not available", STATUS_ERROR)
            return
        self._start_new_session(self._project_folder)

    def _on_new_session_other_folder_clicked(self, _button: Gtk.Button) -> None:
        selected = self._show_folder_dialog("Start New Session in Folder")
        if selected is None:
            return
        self._start_new_session(selected)

    def _on_sidebar_toggle_clicked(self, _button: Any) -> None:
        target_width = 0 if self._sidebar_expanded else SIDEBAR_OPEN_WIDTH
        self._sidebar_expanded = not self._sidebar_expanded
        self._animate_sidebar(target_width)

    def _animate_sidebar(self, target_width: int) -> None:
        if self._sidebar_container is None:
            return

        if self._sidebar_animation_id is not None:
            GLib.source_remove(self._sidebar_animation_id)
            self._sidebar_animation_id = None

        if target_width > 0 and not self._sidebar_container.get_visible():
            self._sidebar_container.set_visible(True)

        start_width = self._sidebar_current_width
        delta = float(target_width) - start_width
        duration_ms = 260.0
        start_time_us = GLib.get_monotonic_time()

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            eased = self._ease_in_out_cubic(progress)
            width = start_width + (delta * eased)
            self._set_sidebar_width(width)

            if progress >= 1.0:
                self._set_sidebar_width(float(target_width))
                self._sidebar_animation_id = None
                return False
            return True

        self._sidebar_animation_id = GLib.timeout_add(16, tick)

    def _set_sidebar_width(self, width: float) -> None:
        if self._sidebar_container is None:
            return

        clamped = max(0.0, min(float(SIDEBAR_OPEN_WIDTH), width))
        self._sidebar_current_width = clamped

        if clamped < 1.0:
            self._sidebar_container.set_size_request(0, -1)
            self._sidebar_container.set_opacity(0.0)
            if self._sidebar_container.get_visible():
                self._sidebar_container.set_visible(False)
            return

        if not self._sidebar_container.get_visible():
            self._sidebar_container.set_visible(True)

        self._sidebar_container.set_size_request(int(clamped), -1)
        self._sidebar_container.set_opacity(clamped / float(SIDEBAR_OPEN_WIDTH))

    def _on_map_event(self, _widget: Gtk.Widget, _event: Gdk.Event) -> bool:
        if not self._window_fade_started:
            self._window_fade_started = True
            self._start_window_fade_in()
        return False

    def _start_window_fade_in(self) -> None:
        self.set_opacity(0.0)

        if self._window_fade_animation_id is not None:
            GLib.source_remove(self._window_fade_animation_id)
            self._window_fade_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 320.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            eased = self._ease_out_cubic(progress)
            self.set_opacity(eased)
            if progress >= 1.0:
                self._window_fade_animation_id = None
                return False
            return True

        self._window_fade_animation_id = GLib.timeout_add(16, tick)

    def _start_status_fade_in(self) -> None:
        if not self._status_fade_widgets:
            return

        if self._status_fade_animation_id is not None:
            GLib.source_remove(self._status_fade_animation_id)
            self._status_fade_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 360.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            eased = self._ease_out_cubic(progress)

            for widget in self._status_fade_widgets:
                widget.set_opacity(eased)

            if progress >= 1.0:
                self._status_fade_animation_id = None
                return False
            return True

        self._status_fade_animation_id = GLib.timeout_add(16, tick)

    def _start_chat_reveal_in(self) -> None:
        if not self._chat_reveal_widgets:
            return

        if self._chat_reveal_animation_id is not None:
            GLib.source_remove(self._chat_reveal_animation_id)
            self._chat_reveal_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 360.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            done = True

            for widget, delay_ms in self._chat_reveal_widgets:
                local_progress = self._clamp01((elapsed_ms - delay_ms) / duration_ms)
                widget.set_opacity(self._ease_out_cubic(local_progress))
                if local_progress < 1.0:
                    done = False

            if done:
                self._chat_reveal_animation_id = None
                return False
            return True

        self._chat_reveal_animation_id = GLib.timeout_add(16, tick)

    def _pulse_chat_shell(self) -> None:
        if self._chat_shell is None:
            return

        if self._chat_pulse_animation_id is not None:
            GLib.source_remove(self._chat_pulse_animation_id)
            self._chat_pulse_animation_id = None

        start_time_us = GLib.get_monotonic_time()
        duration_ms = 480.0

        def tick() -> bool:
            elapsed_ms = (GLib.get_monotonic_time() - start_time_us) / 1000.0
            progress = self._clamp01(elapsed_ms / duration_ms)
            envelope = math.sin(progress * math.pi)
            self._chat_shell.set_opacity(0.92 + envelope * 0.08)

            if progress >= 1.0:
                self._chat_shell.set_opacity(1.0)
                self._chat_pulse_animation_id = None
                return False
            return True

        self._chat_pulse_animation_id = GLib.timeout_add(16, tick)

    def _update_session_timer(self) -> bool:
        if self._session_timer_label is None:
            return False

        elapsed = max(0, (GLib.get_monotonic_time() - self._session_started_us) // 1_000_000)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self._session_timer_label.set_text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return True

    def _on_webview_load_changed(self, _webview: WebKit2.WebView, load_event: WebKit2.LoadEvent) -> None:
        if load_event != WebKit2.LoadEvent.FINISHED:
            return

        self._webview_ready = True
        queued = list(self._pending_webview_scripts)
        self._pending_webview_scripts.clear()

        for script in queued:
            self._run_javascript(script)

        self._update_status_model_and_permission()
        self._show_welcome()

    def _on_webview_focus_in(self, _webview: WebKit2.WebView, _event: Gdk.EventFocus) -> bool:
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().add_class("chat-focused")
        return False

    def _on_webview_focus_out(self, _webview: WebKit2.WebView, _event: Gdk.EventFocus) -> bool:
        if self._chat_shell is not None:
            self._chat_shell.get_style_context().remove_class("chat-focused")
        return False

    def _on_js_change_model(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_value = self._extract_message_from_js_result(js_result)
        model_value = normalize_model_value(raw_value)
        self._apply_model_selection(self._model_index_from_value(model_value))

    def _on_js_change_permission(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_value = self._extract_message_from_js_result(js_result)
        permission_value = normalize_permission_value(raw_value)
        self._apply_permission_selection(self._permission_index_from_value(permission_value))

    def _on_js_attach_file(
        self,
        _manager: WebKit2.UserContentManager,
        _js_result: WebKit2.JavascriptResult,
    ) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Attach file",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.set_show_hidden(True)
        dialog.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Attach",
            Gtk.ResponseType.OK,
        )
        dialog.set_modal(True)
        if os.path.isdir(self._project_folder):
            dialog.set_current_folder(self._project_folder)

        image_filter = Gtk.FileFilter()
        image_filter.set_name("Images")
        for mime_type in ("image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"):
            image_filter.add_mime_type(mime_type)
        dialog.add_filter(image_filter)

        text_filter = Gtk.FileFilter()
        text_filter.set_name("Text files")
        for mime_type in (
            "text/plain",
            "text/markdown",
            "application/json",
            "application/x-yaml",
            "text/x-python",
            "text/x-shellscript",
        ):
            text_filter.add_mime_type(mime_type)
        for pattern in ("*.txt", "*.md", "*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml", "*.csv", "*.log"):
            text_filter.add_pattern(pattern)
        dialog.add_filter(text_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)

        response = dialog.run()
        selected = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()

        if not selected:
            return

        try:
            file_size = os.path.getsize(selected)
        except OSError as error:
            self._set_status_message(f"Could not read file: {error}", STATUS_WARNING)
            return

        if file_size > ATTACHMENT_MAX_BYTES:
            self._set_status_message("Attachment is too large", STATUS_WARNING)
            self._add_system_message("Attachment exceeds 12 MB limit.")
            return

        try:
            with open(selected, "rb") as handle:
                raw_bytes = handle.read()
        except OSError as error:
            self._set_status_message(f"Could not read file: {error}", STATUS_WARNING)
            return

        mime_type, _ = mimetypes.guess_type(selected)
        if not mime_type:
            mime_type = "application/octet-stream"
        payload = {
            "name": os.path.basename(selected),
            "type": mime_type,
            "data": f"data:{mime_type};base64,{base64.b64encode(raw_bytes).decode('ascii')}",
        }
        self._call_js("addHostAttachment", payload)

    @staticmethod
    def _decode_data_url(data_url: str) -> tuple[str, bytes] | None:
        if not data_url.startswith("data:"):
            return None
        header, separator, payload = data_url.partition(",")
        if not separator:
            return None
        meta = header[5:]
        is_base64 = ";base64" in meta
        mime_type = meta.split(";")[0].strip() or "application/octet-stream"
        try:
            data = base64.b64decode(payload) if is_base64 else unquote_to_bytes(payload)
        except (ValueError, TypeError):
            return None
        return mime_type, data

    @staticmethod
    def _parse_send_payload(raw_text: str) -> tuple[str, list[dict[str, str]]]:
        parsed_text = raw_text.strip()
        if not parsed_text:
            return "", []
        try:
            payload = json.loads(parsed_text)
        except json.JSONDecodeError:
            return parsed_text, []

        if not isinstance(payload, dict):
            return parsed_text, []

        message = str(payload.get("text") or "").strip()
        raw_attachments = payload.get("attachments")
        attachments: list[dict[str, str]] = []
        if isinstance(raw_attachments, list):
            for item in raw_attachments:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "attachment").strip() or "attachment"
                file_type = str(item.get("type") or "application/octet-stream").strip() or "application/octet-stream"
                data = str(item.get("data") or "").strip()
                if not data:
                    continue
                attachments.append({"name": name, "type": file_type, "data": data})
        return message, attachments

    def _materialize_attachments(self, attachments: list[dict[str, str]]) -> list[str]:
        temp_paths: list[str] = []
        for attachment in attachments:
            decoded = self._decode_data_url(attachment.get("data", ""))
            if decoded is None:
                continue
            mime_type, raw_bytes = decoded
            if len(raw_bytes) > ATTACHMENT_MAX_BYTES:
                continue

            original_name = attachment.get("name", "attachment")
            _, suffix = os.path.splitext(original_name)
            if not suffix:
                guessed = mimetypes.guess_extension(mime_type)
                suffix = guessed or ""

            try:
                handle = tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix="claude-gui-attachment-",
                    suffix=suffix,
                    delete=False,
                )
            except OSError:
                continue

            with handle:
                handle.write(raw_bytes)
            temp_paths.append(handle.name)
        return temp_paths

    @staticmethod
    def _compose_message_with_attachments(message: str, attachment_paths: list[str]) -> str:
        base_text = message.strip()
        if not attachment_paths:
            return base_text
        attachment_block = "\n".join(f"- {path}" for path in attachment_paths)
        if not base_text:
            base_text = "Please use the attached files as context."
        return f"{base_text}\n\nAttached files:\n{attachment_block}"

    @staticmethod
    def _cleanup_temp_paths(paths: list[str]) -> None:
        for path in paths:
            if not path:
                continue
            try:
                os.unlink(path)
            except OSError:
                continue

    def _on_js_send_message(
        self,
        _manager: WebKit2.UserContentManager,
        js_result: WebKit2.JavascriptResult,
    ) -> None:
        raw_text = self._extract_message_from_js_result(js_result)
        message, attachments = self._parse_send_payload(raw_text)
        if not message and not attachments:
            return

        if self._binary_path is None:
            self._refresh_connection_state()
            self._set_status_message("CLI not found", STATUS_ERROR)
            self._add_system_message("Claude CLI is not available.")
            return

        if self._active_session_id is None:
            if os.path.isdir(self._project_folder):
                self._start_new_session(self._project_folder)
            else:
                self._set_status_message("No active session", STATUS_ERROR)
                self._add_system_message("Create a session first.")
                return

        if self._claude_process.is_running():
            self._add_system_message("Claude is still responding. Please wait.")
            return

        active_session = self._get_active_session()
        if active_session is None:
            self._set_status_message("No active session", STATUS_ERROR)
            self._add_system_message("No active session available.")
            return

        if not os.path.isdir(self._project_folder):
            self._set_status_message("Session folder not found", STATUS_ERROR)
            self._add_system_message("The selected project folder no longer exists.")
            self._set_active_session_status(SESSION_STATUS_ERROR)
            return

        _, model_value = MODEL_OPTIONS[self._selected_model_index]
        _, permission_value, _ = PERMISSION_OPTIONS[self._selected_permission_index]

        attachment_paths = self._materialize_attachments(attachments)
        composed_message = self._compose_message_with_attachments(message, attachment_paths)
        if not composed_message.strip():
            self._cleanup_temp_paths(attachment_paths)
            return

        self._has_messages = True
        self._context_char_count += len(composed_message)
        self._update_context_indicator()

        self._set_typing(True)
        self._pulse_chat_shell()
        self._set_connection_state(CONNECTION_STARTING)
        self._set_status_message("Sending message to Claude...", STATUS_INFO)

        active_session.status = SESSION_STATUS_ACTIVE
        active_session.last_used_at = current_timestamp()
        self._save_sessions_safe("Could not save sessions")
        self._refresh_session_list()

        request_token = str(uuid.uuid4())
        previous_request_token = self._active_request_token
        self._active_request_token = request_token
        config = ClaudeRunConfig(
            binary_path=self._binary_path,
            message=composed_message,
            cwd=self._project_folder,
            model=model_value,
            permission_mode=permission_value,
            conversation_id=self._conversation_id,
            supports_model_flag=self._supports_model_flag,
            supports_permission_flag=self._supports_permission_flag,
            supports_output_format_flag=self._supports_output_format_flag,
            supports_stream_json=self._supports_stream_json,
            supports_json=self._supports_json,
            stream_json_requires_verbose=self._stream_json_requires_verbose,
        )
        started = self._claude_process.send_message(request_token=request_token, config=config)

        if not started:
            self._cleanup_temp_paths(attachment_paths)
            self._context_char_count = max(0, self._context_char_count - len(composed_message))
            self._update_context_indicator()
            self._active_request_token = previous_request_token
            self._set_typing(False)
            self._refresh_connection_state()
            self._set_status_message("A request is already running", STATUS_WARNING)
            return

        self._request_temp_files[request_token] = attachment_paths

    @staticmethod
    def _extract_message_from_js_result(js_result: WebKit2.JavascriptResult) -> str:
        try:
            js_value = js_result.get_js_value()
            raw = js_value.to_string()
        except Exception:
            return ""

        if raw is None:
            return ""

        text = str(raw)
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            try:
                parsed = json.loads(text)
                if isinstance(parsed, str):
                    return parsed
            except json.JSONDecodeError:
                return text[1:-1]

        return text

    def _on_process_running_changed(self, request_token: str, running: bool) -> None:
        if not self._is_current_request(request_token):
            return

        if running:
            self._set_connection_state(CONNECTION_STARTING)
            self._set_status_message("Claude is responding...", STATUS_INFO)

    def _on_process_assistant_chunk(self, request_token: str, chunk: str) -> None:
        if not self._is_current_request(request_token):
            return
        if not chunk:
            return
        self._set_typing(False)
        self._context_char_count += len(chunk)
        self._update_context_indicator()
        self._append_assistant_chunk(chunk)

    def _on_process_system_message(self, request_token: str, message: str) -> None:
        if not self._is_current_request(request_token):
            return
        if not message:
            return
        self._add_system_message(message)

    def _on_process_complete(self, request_token: str, result: ClaudeRunResult) -> None:
        temp_paths = self._request_temp_files.pop(request_token, [])
        self._cleanup_temp_paths(temp_paths)

        if not self._is_current_request(request_token):
            return

        self._invalidate_active_request()
        self._set_typing(False)
        self._finish_assistant_message()

        if result.success and result.conversation_id:
            self._conversation_id = result.conversation_id

        if result.success:
            self._last_request_failed = False
            self._refresh_connection_state()
            self._set_status_message("Claude response received", STATUS_MUTED)
            self._set_active_session_status(SESSION_STATUS_ACTIVE)
            return

        error_message = result.error_message or "Claude request failed"
        self._last_request_failed = True
        self._refresh_connection_state()
        self._set_status_message(error_message, STATUS_ERROR)
        self._set_active_session_status(SESSION_STATUS_ERROR)
        self._add_system_message(error_message)

    def _enqueue_javascript(self, script: str) -> None:
        if not script:
            return

        if self._webview_ready:
            self._run_javascript(script)
            return

        self._pending_webview_scripts.append(script)

    def _run_javascript(self, script: str) -> None:
        if self._webview is None:
            return

        try:
            self._webview.run_javascript(script, None, None, None)
            return
        except TypeError:
            pass

        try:
            self._webview.run_javascript(script, None, None)
            return
        except TypeError:
            pass

        self._webview.run_javascript(script)

    def _call_js(self, function_name: str, *args: Any) -> None:
        serialized = ", ".join(json.dumps(arg, ensure_ascii=False) for arg in args)
        if serialized:
            script = f"if (typeof {function_name} === 'function') {{ {function_name}({serialized}); }}"
        else:
            script = f"if (typeof {function_name} === 'function') {{ {function_name}(); }}"
        self._enqueue_javascript(script)

    def _add_user_message(self, text: str) -> None:
        self._has_messages = True
        self._call_js("addUserMessage", text)

    def _start_assistant_message(self) -> None:
        self._call_js("startAssistantMessage")

    def _append_assistant_chunk(self, text: str) -> None:
        self._call_js("appendAssistantChunk", text)

    def _finish_assistant_message(self) -> None:
        self._call_js("finishAssistantMessage")

    def _add_system_message(self, text: str) -> None:
        self._call_js("addSystemMessage", text)

    def _set_typing(self, value: bool) -> None:
        self._call_js("setTyping", value)

    def _clear_messages(self) -> None:
        self._has_messages = False
        self._context_char_count = 0
        self._update_context_indicator()
        self._call_js("clearMessages")

    def _show_welcome(self) -> None:
        self._call_js("showWelcome")

    def _on_destroy(self, _widget: Gtk.Window) -> None:
        self._claude_process.stop()
        for paths in self._request_temp_files.values():
            self._cleanup_temp_paths(paths)
        self._request_temp_files.clear()

        for attr in (
            "_sidebar_animation_id",
            "_window_fade_animation_id",
            "_status_fade_animation_id",
            "_chat_reveal_animation_id",
            "_chat_pulse_animation_id",
            "_session_timer_id",
        ):
            self._cancel_timer(attr)

        Gtk.main_quit()


def main() -> None:
    window = ClaudeCodeWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
