"""GTK theme color tokens and CSS stylesheet."""

from __future__ import annotations

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
