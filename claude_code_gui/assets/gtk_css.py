"""GTK theme color tokens and CSS stylesheet."""

from __future__ import annotations

from claude_code_gui.domain.provider import PROVIDERS
from claude_code_gui.assets.glass_tokens import (
    GLASS_SPRING_CSS,
    GLASS_RADII,
    glass_gtk_define_colors,
)


def build_gtk_css(
    colors: dict[str, str],
    accent_rgb: tuple[int, int, int],
    accent_soft_rgb: tuple[int, int, int],
    reduced_motion: bool = False,
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
    POPOVER_BG = colors["popover_bg"]
    SESSION_FILTER_BG = colors["session_filter_bg"]
    SESSION_FILTER_HOVER_BG = colors["session_filter_hover_bg"]
    SESSION_FILTER_ACTIVE_FG = colors["session_filter_active_fg"]
    STATUS_DOT_ENDED = colors["status_dot_ended"]
    STATUS_DOT_ARCHIVED = colors["status_dot_archived"]
    CONTEXT_TROUGH_BG = colors["context_trough_bg"]
    SESSION_META_TIME = colors["session_meta_time"]

    accent_r, accent_g, accent_b = accent_rgb
    ACCENT_RGBA_018 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.18)"
    ACCENT_RGBA_012 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.12)"
    ACCENT_RGBA_011 = f"rgba({accent_r}, {accent_g}, {accent_b}, 0.11)"
    accent_soft_r, accent_soft_g, accent_soft_b = accent_soft_rgb
    ACCENT_SOFT_RGBA_018 = (
        f"rgba({accent_soft_r}, {accent_soft_g}, {accent_soft_b}, 0.18)"
    )

    button_transition = "0ms" if reduced_motion else "280ms"
    chrome_transition = "none" if reduced_motion else "all 0.15s ease"
    glass_tokens = glass_gtk_define_colors()

    return f"""
{glass_tokens}
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

/* GLASS-PHASE3-START */
.button,
.sidebar-button,
.sidebar-toggle-gtk,
.new-session-button,
.agentctl-toggle-button,
.session-open-button,
.session-filter-pill,
.project-path-browse-button,
.provider-switch-button {{
    background: @glass_tint_base;
    color: {FOREGROUND};
    border: 1px solid {BORDER_SOFT};
    border-radius: {GLASS_RADII["pill"]}px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    box-shadow: none;
    transition:
        background-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        box-shadow {button_transition} {GLASS_SPRING_CSS["standard"]},
        border-color {button_transition} {GLASS_SPRING_CSS["standard"]};
}}

.button:hover,
.sidebar-button:hover,
.sidebar-toggle-gtk:hover,
.new-session-button:hover,
.agentctl-toggle-button:hover {{
    background: @glass_tint_interactive;
    border-color: @glass_tint_interactive_hover;
    box-shadow: none;
}}

.button:active,
.sidebar-button:active,
.sidebar-toggle-gtk:active,
.new-session-button:active,
.agentctl-toggle-button:active {{
    background: @glass_tint_interactive_hover;
    border-color: @glass_tint_interactive_hover_solid;
    box-shadow: none;
    transition-timing-function: {GLASS_SPRING_CSS["press"]};
}}

.button:focus,
.sidebar-button:focus,
.sidebar-toggle-gtk:focus,
.new-session-button:focus,
.agentctl-toggle-button:focus {{
    box-shadow: none;
    border-color: @glass_tint_interactive_hover;
}}
/* GLASS-PHASE3-END */

.new-session-button {{
    border-radius: {GLASS_RADII["control"]}px;
}}

.new-session-button {{
    min-height: 38px;
    background: @glass_tint_base;
    border-color: {BORDER_SOFT};
    color: {FOREGROUND};
    font-weight: 600;
    padding: 0 12px;
}}

.agentctl-toggle-button {{
    min-height: 30px;
    min-width: 56px;
    background: @glass_tint_base;
    border-color: {BORDER_SOFT};
    color: {FOREGROUND};
    font-weight: 700;
    padding: 0 10px;
}}

.agentctl-toggle-button:checked {{
    background: @glass_tint_interactive;
    border-color: @glass_tint_interactive_hover;
}}

.sidebar-toggle-gtk {{
    min-height: 34px;
    min-width: 34px;
    padding: 0;
    border-radius: {GLASS_RADII["control"]}px;
}}

.sidebar-toggle-gtk.sidebar-toggle-expanded {{
    background: @glass_tint_interactive;
}}

.sidebar-toggle-gtk.sidebar-toggle-collapsed {{
    background: @glass_tint_base;
    border-color: {BORDER_SOFT};
}}

.sidebar-toggle-glyph {{
    color: {FOREGROUND};
    font-size: 16px;
    font-weight: 700;
    opacity: 0.92;
}}

.bottom-combo button,
.recent-combo button {{
    background: @glass_tint_base;
    color: {FOREGROUND};
    border: 1px solid {BORDER_SOFT};
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    border-radius: {GLASS_RADII["pill"]}px;
    box-shadow: none;
    transition:
        background-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        box-shadow {button_transition} {GLASS_SPRING_CSS["standard"]},
        border-color {button_transition} {GLASS_SPRING_CSS["standard"]};
}}

.bottom-combo button:hover,
.recent-combo button:hover {{
    background: @glass_tint_interactive;
    border-color: @glass_tint_interactive_hover;
    box-shadow: none;
}}

.bottom-combo button:focus,
.recent-combo button:focus {{
    box-shadow: none;
    border-color: {ACCENT_SOFT};
}}

.bottom-combo button:active,
.recent-combo button:active {{
    background: @glass_tint_interactive_hover;
    box-shadow: none;
    transition-timing-function: {GLASS_SPRING_CSS["press"]};
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
    background-color: {POPOVER_BG};
    border: 1px solid {BORDER_SOFT};
    border-radius: 10px;
    padding: 4px;
}}

menuitem {{
    color: {FOREGROUND};
    border-radius: 8px;
    border: 1px solid transparent;
    background: transparent;
    padding: 6px 9px;
}}

menuitem:hover {{
    border-color: transparent;
    background-color: {SESSION_FILTER_HOVER_BG};
}}

menuitem:disabled {{
    color: {FOREGROUND_MUTED};
}}

.main-content {{
    background-color: {WINDOW_BG};
}}

.settings-content {{
    background:
        radial-gradient(circle at top left, {ACCENT_RGBA_012}, transparent 34%),
        radial-gradient(circle at bottom right, {ACCENT_SOFT_RGBA_018}, transparent 46%),
        {WINDOW_BG};
}}

label.settings-helper {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 500;
}}

label.settings-validation {{
    font-size: 11px;
    font-weight: 600;
}}

notebook.settings-notebook {{
    border: 1px solid {BORDER_SOFT};
    border-radius: 12px;
    background: @glass_tint_base;
}}

notebook.settings-notebook > header {{
    background: transparent;
    border-bottom: 1px solid {BORDER_SOFT};
    padding: 3px 6px;
}}

notebook.settings-notebook > header > tabs > tab {{
    margin: 0 4px 0 0;
    border-radius: {GLASS_RADII["pill"]}px;
    border: 1px solid transparent;
    background: transparent;
    color: {FOREGROUND_MUTED};
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 700;
}}

notebook.settings-notebook > header > tabs > tab:hover {{
    border-color: {ACCENT_SOFT};
    color: {FOREGROUND};
    background: @glass_tint_interactive;
}}

notebook.settings-notebook > header > tabs > tab:checked {{
    border-color: {ACCENT_SOFT};
    color: {FOREGROUND};
    background: @glass_tint_interactive_hover;
}}

notebook.session-tabs-notebook {{
    background: transparent;
    border: none;
}}

notebook.session-tabs-notebook > header {{
    background: transparent;
    border: none;
    padding: 0 0 10px;
}}

notebook.session-tabs-notebook > header > tabs > tab {{
    margin: 0 6px 0 0;
    border: 1px solid {BORDER_SOFT};
    border-radius: {GLASS_RADII["pill"]}px;
    background: @glass_tint_base;
    color: {FOREGROUND_MUTED};
    padding: 5px 12px;
    box-shadow: none;
    transition:
        background-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        border-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        box-shadow {button_transition} {GLASS_SPRING_CSS["standard"]};
}}

notebook.session-tabs-notebook > header > tabs > tab:hover {{
    background: @glass_tint_interactive;
    border-color: @glass_tint_interactive_hover;
}}

notebook.session-tabs-notebook > header > tabs > tab:checked {{
    border-color: {ACCENT_SOFT};
    background: @glass_tint_interactive_hover;
}}

label.session-tab-label {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 700;
}}

notebook.session-tabs-notebook > header > tabs > tab:checked label.session-tab-label {{
    color: {FOREGROUND};
}}

.session-tab-close-button {{
    min-width: 18px;
    min-height: 18px;
    padding: 0;
    border-radius: 9px;
    border: 1px solid transparent;
    background: transparent;
    color: {FOREGROUND_MUTED};
    box-shadow: none;
}}

.session-tab-close-button:hover {{
    background: @glass_tint_interactive_hover;
    border-color: {ACCENT_SOFT};
    color: {FOREGROUND};
}}

notebook.session-tabs-notebook > header > tabs > tab:checked .session-tab-close-button {{
    color: {FOREGROUND};
}}

.settings-page {{
    background: transparent;
}}

label.settings-provider-title {{
    color: {FOREGROUND};
    font-size: 12px;
    font-weight: 700;
}}

label.settings-muted {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
}}

checkbutton.settings-toggle {{
    color: {FOREGROUND};
    font-size: 11px;
    font-weight: 600;
    padding: 2px 0;
}}

checkbutton.settings-toggle check {{
    border-radius: 6px;
    border: 1px solid {BORDER_SOFT};
    background: {BUTTON_BG};
}}

checkbutton.settings-toggle check:checked {{
    border-color: {ACCENT_SOFT};
    background: {ACCENT_RGBA_018};
}}

frame.settings-card {{
    border: 1px solid {BORDER_SOFT};
    border-radius: 12px;
    background: linear-gradient(180deg, @glass_tint_base 0%, @glass_tint_base_solid 100%);
}}

frame.settings-card > border {{
    border-radius: 11px;
}}

entry.settings-entry {{
    min-height: 30px;
    border-radius: 9px;
    border: 1px solid {BORDER_SOFT};
    background-color: {BUTTON_BG};
    color: {FOREGROUND};
    padding: 0 9px;
    font-size: 11px;
}}

entry.settings-entry:focus {{
    border-color: {ACCENT_SOFT};
    box-shadow: none;
}}

treeview.settings-treeview {{
    background-color: {BUTTON_BG};
    color: {FOREGROUND};
}}

treeview.settings-treeview.view:selected,
treeview.settings-treeview.view:focus:selected {{
    background-color: {ACCENT_RGBA_018};
    color: {FOREGROUND};
}}

button.settings-color-button {{
    min-width: 34px;
    min-height: 30px;
    padding: 0;
    border-radius: {GLASS_RADII["control"]}px;
}}

button.settings-preset-button {{
    min-height: 28px;
    padding: 0 10px;
    font-size: 10px;
    font-weight: 700;
}}

.sidebar {{
    background: {SIDEBAR_BG};
    border-right: 1px solid {BORDER_SOFT};
    padding: 12px 10px;
    transition: {chrome_transition};
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
    border-radius: {GLASS_RADII["pill"]}px;
    border: 1px solid {BORDER_SOFT};
    background: @glass_tint_base;
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 700;
}}

.provider-selector-row {{
    margin-top: 2px;
    margin-bottom: 2px;
}}

.provider-select-button {{
    min-height: 30px;
    padding: 0 9px;
    border-radius: {GLASS_RADII["pill"]}px;
}}

.provider-select-button label {{
    font-size: 10px;
    font-weight: 700;
}}

.provider-select-button.provider-select-button-active {{
    color: {FOREGROUND};
    border-color: {ACCENT_SOFT};
    background: {ACCENT_RGBA_018};
}}

.provider-switch-button:hover {{
    border-color: {ACCENT_SOFT};
    background: @glass_tint_interactive;
    color: {FOREGROUND};
    box-shadow: none;
}}

.provider-switch-button:disabled {{
    color: {FOREGROUND_MUTED};
    border-color: {BORDER_SOFT};
    background: transparent;
}}

.provider-switch-icon {{
    min-width: 16px;
    min-height: 16px;
    opacity: 0.96;
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
    box-shadow: none;
}}

.project-path-bar {{
    margin-top: 8px;
}}

.project-path-browse-button {{
    min-height: 34px;
    min-width: 34px;
    padding: 0;
    border-radius: {GLASS_RADII["control"]}px;
    background: @glass_tint_base;
    border: 1px solid {BORDER_SOFT};
    color: {FOREGROUND};
}}

.project-path-browse-button:hover {{
    background: @glass_tint_interactive;
    border-color: @glass_tint_interactive_hover;
    box-shadow: none;
}}

.project-path-browse-button:focus {{
    box-shadow: none;
    border-color: {ACCENT_SOFT};
}}

popover.path-suggestion-popover {{
    background-color: {POPOVER_BG};
    border: 1px solid {BORDER_SOFT};
    border-radius: 10px;
    box-shadow: none;
    min-width: 240px;
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
    border-radius: {GLASS_RADII["pill"]}px;
    border: 1px solid {BORDER_SOFT};
    background: {SESSION_FILTER_BG};
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 600;
}}

.session-mark-toggle {{
    min-width: 24px;
    min-height: 24px;
    padding: 0 6px;
    font-size: 22px;
    font-weight: 700;
    line-height: 1;
}}

.session-filter-pill:hover {{
    background: {SESSION_FILTER_HOVER_BG};
    border-color: {ACCENT_SOFT};
    color: {FOREGROUND};
    box-shadow: none;
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
    box-shadow: none;
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
    background: linear-gradient(180deg, @glass_tint_base 0%, @glass_tint_base_solid 100%);
    transition:
        background-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        border-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        box-shadow {button_transition} {GLASS_SPRING_CSS["standard"]};
    box-shadow: none;
}}

.session-row + .session-row {{
    margin-top: 4px;
}}

.session-row:hover {{
    background: linear-gradient(180deg, @glass_tint_interactive 0%, @glass_tint_interactive_hover 100%);
    border-color: @glass_tint_interactive_hover;
}}

.session-row.session-row-active {{
    background: linear-gradient(180deg, @glass_tint_interactive_hover 0%, @glass_tint_interactive 100%);
    border-color: @glass_tint_interactive_hover;
    box-shadow: none;
}}

.session-open-button {{
    background-color: transparent;
    border: none;
    color: {FOREGROUND};
    padding: 4px 2px;
    font-size: 12px;
    transition: {chrome_transition};
}}

.session-open-button:hover {{
    background-color: transparent;
    border: none;
}}

.session-open-button:focus {{
    box-shadow: none;
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

.session-status-dot.session-status-active,
.session-status-dot.session-status-active-done {{
    background-color: {SUCCESS};
}}

.session-status-dot.session-status-ended,
.session-status-dot.session-status-inactive {{
    background-color: {STATUS_DOT_ENDED};
}}

.session-status-dot.session-status-active-working {{
    background-color: {ACCENT_SOFT};
}}

.session-status-dot.session-status-archived {{
    background-color: {STATUS_DOT_ARCHIVED};
}}

.session-status-dot.session-status-error {{
    background-color: {ERROR};
}}

.session-menu-button {{
    min-height: 22px;
    min-width: 22px;
    padding: 0 2px;
    border-radius: 999px;
    border: none;
    background: transparent;
    box-shadow: none;
    font-size: 13px;
    color: {FOREGROUND_MUTED};
}}

.session-menu-button:hover {{
    background: {SESSION_FILTER_HOVER_BG};
    color: {FOREGROUND};
}}

.session-menu-button:active {{
    background: {SESSION_FILTER_BG};
}}

.session-group-label {{
    color: {FOREGROUND_MUTED};
    font-size: 11px;
    font-weight: 700;
    margin: 10px 6px 2px;
}}

.session-popover button {{
    border-radius: 8px;
    border: 1px solid transparent;
    background: transparent;
    color: {FOREGROUND};
    transition:
        background-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        border-color {button_transition} {GLASS_SPRING_CSS["standard"]},
        color {button_transition} {GLASS_SPRING_CSS["standard"]};
}}

.session-popover button:hover {{
    border-color: transparent;
    background-color: {SESSION_FILTER_HOVER_BG};
    color: {FOREGROUND};
}}

.chat-wrap {{
    padding: 10px 10px 8px;
    background: radial-gradient(circle at top left, {ACCENT_RGBA_011}, transparent 35%), {CHAT_OUTER_BG};
}}

.pane-root {{
    border: none;
    border-radius: 12px;
    background: transparent;
}}

.pane-root.pane-active {{
    border-color: transparent;
}}

.pane-header {{
    min-height: 30px;
    padding: 3px 8px;
    border-bottom: 1px solid {BORDER_SOFT};
    background: {SIDEBAR_BG};
}}

.pane-title {{
    color: {FOREGROUND};
    font-size: 11px;
    font-weight: 700;
}}

.pane-agent-status {{
    border-radius: 999px;
    border: 1px solid {BORDER_SOFT};
    background: {BUTTON_BG};
    color: {FOREGROUND_MUTED};
    font-size: 9px;
    font-weight: 700;
    padding: 1px 7px;
    margin: 0 2px;
}}

.pane-agent-status-working {{
    border-color: {ACCENT_SOFT};
    background: {ACCENT_RGBA_012};
    color: {ACCENT_SOFT};
}}

.pane-agent-status-done {{
    border-color: rgba(107, 190, 120, 0.58);
    background: rgba(107, 190, 120, 0.15);
    color: {SUCCESS};
}}

.pane-agent-status-blocked {{
    border-color: rgba(226, 112, 112, 0.58);
    background: rgba(226, 112, 112, 0.16);
    color: {ERROR};
}}

.pane-session-label {{
    color: {FOREGROUND_MUTED};
    font-size: 10px;
}}

.pane-close-button {{
    min-width: 24px;
    min-height: 24px;
    padding: 0;
    border-radius: 999px;
    border: 1px solid {BORDER_SOFT};
    background: transparent;
    color: {FOREGROUND_MUTED};
}}

.pane-close-button:hover {{
    background: {SESSION_FILTER_HOVER_BG};
    border-color: {ACCENT_SOFT};
    color: {FOREGROUND};
}}

.chat-shell {{
    background-color: {CHAT_BG};
    border: none;
    border-radius: 12px;
    box-shadow: none;
    transition: {chrome_transition};
}}

.chat-shell.chat-focused {{
    border-color: {BORDER};
    box-shadow: none;
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

.launcher-window {{
    border-radius: 24px;
    border: 1px solid {BORDER_SOFT};
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
}}

.launcher-window .app-root {{
    border-radius: 24px;
}}
"""


CSS_STYLES = build_gtk_css(
    PROVIDERS["claude"].colors,
    PROVIDERS["claude"].accent_rgb,
    PROVIDERS["claude"].accent_soft_rgb,
)
