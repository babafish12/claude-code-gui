"""Provider registry with display metadata, theme tokens, and capability flags."""

from __future__ import annotations

from dataclasses import dataclass

ModelOption = tuple[str, str]
PermissionOption = tuple[str, str, bool]
ColorTokens = dict[str, str]
AccentRgb = tuple[int, int, int]


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    name: str
    icon: str
    binary_names: tuple[str, ...]
    colors: ColorTokens
    accent_rgb: AccentRgb
    accent_soft_rgb: AccentRgb
    model_options: tuple[ModelOption, ...]
    permission_options: tuple[PermissionOption, ...]
    supports_reasoning: bool

    @property
    def display_name(self) -> str:
        return self.name


CLAUDE_COLORS: ColorTokens = {
    "window_bg": "#2f2f2a",
    "header_bg": "#2c2c27",
    "header_gradient_end": "#252520",
    "sidebar_bg": "#252520",
    "chat_outer_bg": "#2f2f2a",
    "chat_bg": "#2f2f2a",
    "status_bg": "#292923",
    "bottom_gradient_end": "#252520",
    "border": "#4a4a43",
    "border_soft": "#3b3b35",
    "foreground": "#d4d4c8",
    "foreground_muted": "#8a8a7a",
    "accent": "#d97757",
    "accent_soft": "#e09670",
    "warning": "#d5a160",
    "error": "#df7f66",
    "success": "#8bbf8a",
    "button_bg": "#35352f",
    "button_bg_hover": "#3f3f38",
    "button_bg_active": "#484840",
    "new_session_bg": "#31312b",
    "new_session_border": "#3f3f38",
    "sidebar_toggle_collapsed_bg": "#3a3a34",
    "menu_bg": "#34342e",
    "popover_bg": "#30302a",
    "session_filter_bg": "#31312b",
    "session_filter_hover_bg": "#3a3a33",
    "session_filter_active_fg": "#f7efe9",
    "session_row_hover_bg": "#34342f",
    "session_row_active_bg": "#3a3a34",
    "status_dot_ended": "#7b7b70",
    "status_dot_archived": "#585850",
    "context_trough_bg": "#3a3a34",
    "session_meta_time": "#bcb49b",
}

CLAUDE_MODEL_OPTIONS: tuple[ModelOption, ...] = (
    ("Claude Sonnet (Latest)", "sonnet"),
    ("Claude Opus (Latest)", "opus"),
    ("Claude Haiku (Latest)", "haiku"),
)

CLAUDE_PERMISSION_OPTIONS: tuple[PermissionOption, ...] = (
    ("Auto", "auto", False),
    ("Plan mode", "plan", False),
    ("Bypass permissions (Advanced)", "bypassPermissions", True),
)

CODEX_COLORS: ColorTokens = {
    "window_bg": "#1c2220",
    "header_bg": "#181f1c",
    "header_gradient_end": "#121816",
    "sidebar_bg": "#131a18",
    "chat_outer_bg": "#1c2220",
    "chat_bg": "#1c2220",
    "status_bg": "#161d1a",
    "bottom_gradient_end": "#121816",
    "border": "#2d3a34",
    "border_soft": "#24302a",
    "foreground": "#d7e2dc",
    "foreground_muted": "#8ea198",
    "accent": "#10a37f",
    "accent_soft": "#4ade80",
    "warning": "#d0b26f",
    "error": "#d78574",
    "success": "#56c895",
    "button_bg": "#202925",
    "button_bg_hover": "#27322d",
    "button_bg_active": "#2e3b34",
    "new_session_bg": "#212a26",
    "new_session_border": "#2f3b35",
    "sidebar_toggle_collapsed_bg": "#27312d",
    "menu_bg": "#1b2420",
    "popover_bg": "#16201c",
    "session_filter_bg": "#212a26",
    "session_filter_hover_bg": "#27312d",
    "session_filter_active_fg": "#e9f6ef",
    "session_row_hover_bg": "#25302b",
    "session_row_active_bg": "#2a3630",
    "status_dot_ended": "#76887f",
    "status_dot_archived": "#55615b",
    "context_trough_bg": "#27312d",
    "session_meta_time": "#a8bbb1",
}

CODEX_MODEL_OPTIONS: tuple[ModelOption, ...] = (
    ("GPT-5.4", "gpt-5.4"),
    ("GPT-5", "gpt-5"),
    ("GPT-5.3 Codex", "gpt-5.3-codex"),
)

CODEX_PERMISSION_OPTIONS: tuple[PermissionOption, ...] = (
    ("Auto", "auto", False),
    ("Plan mode", "plan", False),
    ("Bypass permissions (Advanced)", "bypassPermissions", True),
)

PROVIDERS: dict[str, ProviderConfig] = {
    "claude": ProviderConfig(
        id="claude",
        name="Claude",
        icon="✺",
        binary_names=("claude", "claude-code"),
        colors=CLAUDE_COLORS,
        accent_rgb=(212, 132, 90),
        accent_soft_rgb=(224, 150, 112),
        model_options=CLAUDE_MODEL_OPTIONS,
        permission_options=CLAUDE_PERMISSION_OPTIONS,
        supports_reasoning=True,
    ),
    "codex": ProviderConfig(
        id="codex",
        name="Codex",
        icon="⌘",
        binary_names=("codex",),
        colors=CODEX_COLORS,
        accent_rgb=(16, 163, 127),
        accent_soft_rgb=(74, 222, 128),
        model_options=CODEX_MODEL_OPTIONS,
        permission_options=CODEX_PERMISSION_OPTIONS,
        supports_reasoning=False,
    ),
}

DEFAULT_PROVIDER_ID = "claude"


def normalize_provider_id(raw_value: str | None) -> str:
    candidate = str(raw_value or DEFAULT_PROVIDER_ID).strip().lower()
    if candidate in PROVIDERS:
        return candidate
    return DEFAULT_PROVIDER_ID


def get_provider_config(provider_id: str | None) -> ProviderConfig:
    return PROVIDERS[normalize_provider_id(provider_id)]
