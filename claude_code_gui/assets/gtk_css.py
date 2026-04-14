"""GTK theme color tokens and CSS stylesheet."""

from __future__ import annotations

from claude_code_gui.domain.provider import PROVIDERS


def build_gtk_css(
    colors: dict[str, str],
    accent_rgb: tuple[int, int, int],
    accent_soft_rgb: tuple[int, int, int],
) -> str:
    WINDOW_BG = colors["window_bg"]
    HEADER_BG = colors["header_bg"]
    HEADER_GRADIENT_END = colors["header_gradient_end"]
    SIDEBAR_BG = colors["sidebar_bg"]
    CHAT_OUTER_BG = colors["chat_outer_bg"]
    CHAT_BG = colors["chat_bg"]
    STATUS_BG = colors["status_bg"]
    BOTTOM_GRADIENT_END = colors["bottom_gradient_end"]
    BORDER = colors["border"]
    BORDER_SOFT = colors["border_soft"]
    FOREGROUND = colors["foreground"]
    FOREGROUND_MUTED = colors["foreground_muted"]
    ACCENT = colors["accent"]
    ACCENT_SOFT = colors["accent_soft"]
    WARNING = colors["warning"]
    ERROR = colors["error"]
    SUCCESS = colors["success"]
    BUTTON_BG = colors["button_bg"]
    BUTTON_BG_HOVER = colors["button_bg_hover"]
    BUTTON_BG_ACTIVE = colors["button_bg_active"]
    NEW_SESSION_BG = colors["new_session_bg"]
    NEW_SESSION_BORDER = colors["new_session_border"]
    SIDEBAR_TOGGLE_COLLAPSED_BG = colors["sidebar_toggle_collapsed_bg"]
    MENU_BG = colors["menu_bg"]
    POPOVER_BG = colors["popover_bg"]
    SESSION_FILTER_BG = colors["session_filter_bg"]
    SESSION_FILTER_HOVER_BG = colors["session_filter_hover_bg"]
    SESSION_FILTER_ACTIVE_FG = colors["session_filter_active_fg"]
    SESSION_ROW_HOVER_BG = colors["session_row_hover_bg"]
    SESSION_ROW_ACTIVE_BG = colors["session_row_active_bg"]
    STATUS_DOT_ENDED = colors["status_dot_ended"]
    STATUS_DOT_ARCHIVED = colors["status_dot_archived"]
    CONTEXT_TROUGH_BG = colors["context_trough_bg"]
    SESSION_META_TIME = colors["session_meta_time"]

    accent_r, accent_g, accent_b = accent_rgb
    ACCENT_RGBA_035 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.35)"
    ACCENT_RGBA_03 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.3)"
    ACCENT_RGBA_025 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.25)"
    ACCENT_RGBA_02 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.2)"
    ACCENT_RGBA_018 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.18)"
    ACCENT_RGBA_045 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.45)"
    ACCENT_RGBA_012 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.12)"
    ACCENT_RGBA_011 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.11)"
    ACCENT_RGBA_034 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.34)"
    accent_soft_r, accent_soft_g, accent_soft_b = accent_soft_rgb
    ACCENT_SOFT_RGBA_045 = (
        f"rgba({accent_soft_r}, {accent_soft_g}, {accent_soft_b}, 0.45)"
    )
    ACCENT_SOFT_RGBA_04 = (
        f"rgba({accent_soft_r}, {accent_soft_g}, {accent_soft_b}, 0.4)"
    )
    ACCENT_SOFT_RGBA_018 = (
        f"rgba({accent_soft_r}, {accent_soft_g}, {accent_soft_b}, 0.18)"
    )

    return f"""
window,
.app-root {{
    background-color: {WINDOW_BG};
    color: {FOREGROUND};
}}

.header-shell {{
    background: linear-gradient(180deg, {HEADER_BG}, {HEADER_GRADIENT_END});
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
    box-shadow: 0 0 0 2px {ACCENT_RGBA_035};
}}

.new-session-button {{
    border-radius: 12px;
}}

.new-session-button {{
    min-height: 38px;
    background: {NEW_SESSION_BG};
    border-color: {NEW_SESSION_BORDER};
    color: {FOREGROUND};
    font-weight: 600;
    padding: 0 12px;
}}

.sidebar-toggle-gtk {{
    min-height: 34px;
    min-width: 34px;
    padding: 0;
    border-radius: 10px;
}}

.sidebar-toggle-gtk.sidebar-toggle-expanded {{
    background-color: {NEW_SESSION_BG};
}}

.sidebar-toggle-gtk.sidebar-toggle-collapsed {{
    background-color: {SIDEBAR_TOGGLE_COLLAPSED_BG};
    border-color: {ACCENT_SOFT_RGBA_045};
}}

.sidebar-toggle-glyph {{
    color: {FOREGROUND};
    font-size: 16px;
    font-weight: 700;
    opacity: 0.92;
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
    box-shadow: 0 0 0 2px {ACCENT_RGBA_035};
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
    background-color: {MENU_BG};
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
    background-color: {ACCENT_RGBA_02};
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

.sidebar.sidebar-collapsed {{
    padding: 12px 4px;
    border-right-color: transparent;
    background: transparent;
}}

.sidebar-header-toggle {{
    min-height: 30px;
    min-width: 30px;
    padding: 0;
    border-radius: 10px;
}}

.provider-switch-button {{
    min-height: 30px;
    padding: 0 10px;
    border-radius: 10px;
    border: 1px solid {ACCENT_SOFT_RGBA_045};
    background: {ACCENT_RGBA_012};
    color: {ACCENT_SOFT};
    font-size: 11px;
    font-weight: 700;
}}

.provider-switch-button:hover {{
    border-color: {ACCENT_SOFT};
    background: {ACCENT_RGBA_018};
    color: {FOREGROUND};
}}

.provider-switch-button:disabled {{
    color: {FOREGROUND_MUTED};
    border-color: {BORDER_SOFT};
    background: transparent;
}}

.sidebar-section-title {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2px;
    margin-top: 10px;
    margin-bottom: 3px;
}}

.project-path-entry {{
    min-height: 34px;
    border-radius: 10px;
    border: 1px solid {BORDER_SOFT};
    background-color: {BUTTON_BG};
    color: {FOREGROUND};
    padding: 0 10px;
    font-size: 12px;
}}

.project-path-entry:focus {{
    border-color: {ACCENT_SOFT};
    box-shadow: 0 0 0 2px {ACCENT_RGBA_03};
}}

.project-path-bar {{
    margin-top: 8px;
}}

.project-path-browse-button {{
    min-height: 34px;
    min-width: 34px;
    padding: 0;
    border-radius: 10px;
    background-color: {BUTTON_BG};
    border: 1px solid {BORDER_SOFT};
    color: {FOREGROUND};
}}

.project-path-browse-button:hover {{
    background-color: {BUTTON_BG_HOVER};
    border-color: {ACCENT_SOFT};
}}

.project-path-browse-button:focus {{
    box-shadow: 0 0 0 2px {ACCENT_RGBA_035};
}}

popover.path-suggestion-popover {{
    background-color: {POPOVER_BG};
    border: 1px solid {BORDER};
    border-radius: 10px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
    min-width: 560px;
}}

.path-suggestion-list row {{
    border-radius: 8px;
    padding: 3px 8px;
}}

.path-suggestion-list row:hover {{
    background-color: rgba(255, 255, 255, 0.04);
}}

.path-suggestion-list row:selected {{
    background-color: {ACCENT_RGBA_018};
}}

.path-suggestion-item {{
    color: {FOREGROUND};
    font-size: 12px;
    padding: 2px 0;
}}

.session-scroll {{
    border: none;
    background-color: transparent;
}}

.session-filter-row {{
    margin-top: 2px;
}}

.session-filter-pill {{
    min-height: 24px;
    padding: 0 10px;
    border-radius: 999px;
    border: 1px solid {BORDER_SOFT};
    background-color: {SESSION_FILTER_BG};
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 600;
}}

.session-filter-pill:hover {{
    background-color: {SESSION_FILTER_HOVER_BG};
    border-color: {ACCENT_SOFT};
    color: {FOREGROUND};
}}

.session-filter-pill.session-filter-pill-active {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: {SESSION_FILTER_ACTIVE_FG};
}}

.session-search-entry {{
    min-height: 30px;
    border-radius: 9px;
    border: 1px solid {BORDER_SOFT};
    background-color: {BUTTON_BG};
    color: {FOREGROUND};
    padding: 0 10px;
    font-size: 11px;
}}

.session-search-entry:focus {{
    border-color: {ACCENT_SOFT};
    box-shadow: 0 0 0 2px {ACCENT_RGBA_025};
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
    background-color: {SESSION_ROW_HOVER_BG};
}}

.session-row.session-row-active {{
    background-color: {SESSION_ROW_ACTIVE_BG};
    border-color: {ACCENT_SOFT_RGBA_04};
    box-shadow: inset 0 0 0 1px {ACCENT_SOFT_RGBA_018};
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
    box-shadow: 0 0 0 2px {ACCENT_RGBA_035};
}}

.session-title {{
    color: {FOREGROUND};
    font-size: 12px;
    font-weight: 600;
}}

.session-status-dot {{
    min-width: 8px;
    min-height: 8px;
    border-radius: 999px;
    margin-top: 4px;
}}

.session-status-dot.session-status-active {{
    background-color: {SUCCESS};
}}

.session-status-dot.session-status-ended {{
    background-color: {STATUS_DOT_ENDED};
}}

.session-status-dot.session-status-archived {{
    background-color: {STATUS_DOT_ARCHIVED};
}}

.session-status-dot.session-status-error {{
    background-color: {ERROR};
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
    border-color: {ACCENT_RGBA_045};
    background-color: {ACCENT_RGBA_012};
}}

.chat-wrap {{
    padding: 10px 10px 8px;
    background: radial-gradient(circle at top left, {ACCENT_RGBA_011}, transparent 35%), {CHAT_OUTER_BG};
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
    box-shadow: 0 0 0 1px {ACCENT_RGBA_034}, 0 14px 28px rgba(0, 0, 0, 0.28);
}}

.chat-overlay-toggle {{
    background: transparent;
    padding: 8px;
}}

.bottom-bar {{
    background: linear-gradient(180deg, {STATUS_BG}, {BOTTOM_GRADIENT_END});
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
    background-color: {CONTEXT_TROUGH_BG};
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

.session-preview {{
    color: {FOREGROUND_MUTED};
    font-size: 10px;
    font-weight: 400;
    opacity: 0.65;
}}

.session-meta {{
    font-size: 10px;
    font-weight: 500;
    opacity: 0.76;
}}

.session-meta-time {{
    color: {SESSION_META_TIME};
}}

.session-meta-path {{
    color: {FOREGROUND_MUTED};
}}

.usage-limit-label {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 500;
}}

.usage-limit-label.usage-warn {{
    color: {WARNING};
}}

.usage-limit-label.usage-high {{
    color: {ERROR};
}}
"""


CSS_STYLES = build_gtk_css(
    PROVIDERS["claude"].colors,
    PROVIDERS["claude"].accent_rgb,
    PROVIDERS["claude"].accent_soft_rgb,
)
