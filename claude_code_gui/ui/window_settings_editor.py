"""Settings dialog implementation extracted from the main window module."""

from __future__ import annotations

import copy
import logging
import re
from typing import TYPE_CHECKING, Any

from claude_code_gui.app.constants import STATUS_INFO
from claude_code_gui.domain.app_settings import get_default_settings, load_settings, save_settings
from claude_code_gui.gi_runtime import Gdk, Gtk, Pango

if TYPE_CHECKING:
    from claude_code_gui.ui.window import ClaudeCodeWindow


logger = logging.getLogger(__name__)


def open_settings_editor(window: "ClaudeCodeWindow") -> None:
    original_payload = load_settings()
    working_payload = copy.deepcopy(original_payload)
    (
        default_width,
        default_height,
        min_width,
        min_height,
        max_width,
        max_height,
    ) = window._settings_dialog_size_constraints()

    dialog = Gtk.Dialog(
        title="App Settings",
        transient_for=window,
    )
    dialog.set_modal(True)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Save", Gtk.ResponseType.OK)
    dialog.set_resizable(True)

    def _add_css_classes(widget: Gtk.Widget, *class_names: str) -> None:
        context = widget.get_style_context()
        for class_name in class_names:
            if class_name:
                context.add_class(class_name)

    _add_css_classes(dialog, "settings-dialog")
    action_area = dialog.get_action_area() if hasattr(dialog, "get_action_area") else None
    if action_area is not None:
        _add_css_classes(action_area, "settings-actions")

    if hasattr(dialog, "set_geometry_hints"):
        try:
            geometry = Gdk.Geometry()
            geometry.min_width = min_width
            geometry.min_height = min_height
            geometry.max_width = max_width
            geometry.max_height = max_height
            dialog.set_geometry_hints(
                None,
                geometry,
                Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE,
            )
        except Exception:
            logger.debug("Geometry hints are unavailable in the current GDK runtime.", exc_info=True)
    dialog.set_default_size(default_width, default_height)

    content_area = dialog.get_content_area()
    content_area.set_spacing(10)
    content_area.set_border_width(10)
    _add_css_classes(content_area, "settings-content")

    helper_label = Gtk.Label(
        label="Customize provider themes, model options, and tray behavior.",
    )
    helper_label.set_xalign(0.0)
    helper_label.set_line_wrap(True)
    _add_css_classes(helper_label, "settings-helper")
    content_area.pack_start(helper_label, False, False, 0)

    validation_label = Gtk.Label(label="")
    validation_label.set_xalign(0.0)
    validation_label.set_line_wrap(True)
    validation_label.set_visible(False)
    _add_css_classes(validation_label, "status-warning", "settings-validation")
    content_area.pack_start(validation_label, False, False, 0)

    tray_toggle = Gtk.CheckButton(label="Enable system tray integration when available")
    tray_toggle.set_active(bool(working_payload.get("system_tray_enabled", True)))
    tray_toggle.connect(
        "toggled",
        lambda button: working_payload.__setitem__("system_tray_enabled", bool(button.get_active())),
    )
    _add_css_classes(tray_toggle, "settings-toggle")
    content_area.pack_start(tray_toggle, False, False, 0)

    stream_speed_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    stream_speed_label = Gtk.Label(label="Chat text reveal speed")
    stream_speed_label.set_xalign(0.0)
    stream_speed_label.set_hexpand(True)
    _add_css_classes(stream_speed_label, "settings-muted")
    stream_speed_row.pack_start(stream_speed_label, True, True, 0)

    stream_speed_combo = Gtk.ComboBoxText()
    stream_speed_options: list[tuple[str, int]] = [
        ("Instant", 0),
        ("Fast", 30),
        ("Normal", 80),
        ("Slow", 160),
        ("Very slow", 280),
    ]
    for label, _value in stream_speed_options:
        stream_speed_combo.append_text(label)

    try:
        current_stream_ms = int(working_payload.get("stream_render_throttle_ms", 80))
    except (TypeError, ValueError):
        current_stream_ms = 80
    current_stream_ms = max(0, min(1500, current_stream_ms))
    default_index = min(
        range(len(stream_speed_options)),
        key=lambda idx: abs(stream_speed_options[idx][1] - current_stream_ms),
    )
    stream_speed_combo.set_active(default_index)
    working_payload["stream_render_throttle_ms"] = stream_speed_options[default_index][1]

    def _on_stream_speed_changed(combo: Gtk.ComboBoxText) -> None:
        index = combo.get_active()
        if index < 0 or index >= len(stream_speed_options):
            return
        working_payload["stream_render_throttle_ms"] = stream_speed_options[index][1]

    stream_speed_combo.connect("changed", _on_stream_speed_changed)
    stream_speed_row.pack_start(stream_speed_combo, False, False, 0)
    content_area.pack_start(stream_speed_row, False, False, 0)

    notebook = Gtk.Notebook()
    notebook.set_scrollable(True)
    _add_css_classes(notebook, "settings-notebook")

    settings_scroller = Gtk.ScrolledWindow()
    settings_scroller.set_hexpand(True)
    settings_scroller.set_vexpand(True)
    settings_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    settings_scroller.set_min_content_width(max(280, min_width - 24))
    settings_scroller.set_min_content_height(240)
    settings_scroller.add(notebook)
    _add_css_classes(settings_scroller, "settings-scroller")
    content_area.pack_start(settings_scroller, True, True, 0)

    hex_pattern = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

    def _normalize_hex(raw: str) -> str | None:
        if not isinstance(raw, str):
            return None
        value = raw.strip()
        if not value.startswith("#"):
            return None
        if not hex_pattern.match(value):
            return None
        if len(value) == 4:
            return f"#{value[1]*2}{value[2]*2}{value[3]*2}".lower()
        if len(value) == 7:
            return value.lower()
        return None

    def _to_hex_with_prefix(red: int, green: int, blue: int) -> str:
        return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"

    def _normalize_rgb_component(value: object) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(255, number))

    def _normalize_rgb_list(raw: object) -> list[int] | None:
        if not isinstance(raw, list) or len(raw) < 3:
            return None
        return [_normalize_rgb_component(value) for value in raw[:3]]

    def _hex_to_rgb(raw: str) -> tuple[int, int, int] | None:
        normalized = _normalize_hex(raw)
        if normalized is None:
            return None
        return (
            int(normalized[1:3], 16),
            int(normalized[3:5], 16),
            int(normalized[5:7], 16),
        )

    def _mix_rgb(
        source: tuple[int, int, int],
        target: tuple[int, int, int],
        amount: float,
    ) -> tuple[int, int, int]:
        weight = max(0.0, min(1.0, amount))
        return (
            round(source[0] + (target[0] - source[0]) * weight),
            round(source[1] + (target[1] - source[1]) * weight),
            round(source[2] + (target[2] - source[2]) * weight),
        )

    def _lighten_rgb(source: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        return _mix_rgb(source, (255, 255, 255), amount)

    def _darken_rgb(source: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        return _mix_rgb(source, (0, 0, 0), amount)

    def _rgba_to_hex(color: Gdk.RGBA) -> str:
        return _to_hex_with_prefix(
            round(color.red * 255),
            round(color.green * 255),
            round(color.blue * 255),
        )

    def _hex_to_rgba(raw: str) -> Gdk.RGBA | None:
        rgba = Gdk.RGBA()
        if rgba.parse(raw):
            return rgba
        return None

    def _set_bg(widget: Gtk.Widget, value: str) -> None:
        color = _hex_to_rgba(value)
        if color is not None and hasattr(widget, "override_background_color"):
            widget.override_background_color(Gtk.StateFlags.NORMAL, color)

    def _set_fg(widget: Gtk.Widget, value: str) -> None:
        color = _hex_to_rgba(value)
        if color is not None and hasattr(widget, "override_color"):
            widget.override_color(Gtk.StateFlags.NORMAL, color)

    theme_category_entry_map: dict[tuple[str, str], Gtk.Entry] = {}
    provider_theme_categories: dict[str, dict[str, str]] = {}
    theme_category_order: tuple[tuple[str, str], ...] = (
        ("background", "Hintergrund"),
        ("text", "Text"),
        ("accent", "Akzent"),
        ("status", "Status"),
    )

    def _set_entry_validation(entry: Gtk.Entry | None, message: str | None) -> None:
        if entry is None:
            return
        context = entry.get_style_context()
        context.remove_class("error")
        if message:
            context.add_class("error")
            entry.set_tooltip_text(message)
            return
        entry.set_tooltip_text(None)

    def _clear_theme_entry_validation() -> None:
        for entry in theme_category_entry_map.values():
            _set_entry_validation(entry, None)

    def _extract_provider_theme_categories(provider: dict[str, Any]) -> dict[str, str]:
        colors_payload = provider.get("colors")
        colors = colors_payload if isinstance(colors_payload, dict) else {}
        accent_rgb_payload = provider.get("accent_rgb")
        accent_rgb = (
            _to_hex_with_prefix(
                _normalize_rgb_component(accent_rgb_payload[0]),
                _normalize_rgb_component(accent_rgb_payload[1]),
                _normalize_rgb_component(accent_rgb_payload[2]),
            )
            if isinstance(accent_rgb_payload, list) and len(accent_rgb_payload) >= 3
            else None
        )
        return {
            "background": _normalize_hex(str(colors.get("window_bg", ""))) or "#1e2524",
            "text": _normalize_hex(str(colors.get("foreground", ""))) or "#e7f0ed",
            "accent": _normalize_hex(str(colors.get("accent", ""))) or accent_rgb or "#10a37f",
            "status": _normalize_hex(str(colors.get("success", ""))) or "#61c592",
        }

    def _copy_provider_theme(provider: dict[str, Any], source: dict[str, Any]) -> None:
        source_colors_payload = source.get("colors")
        source_colors = source_colors_payload if isinstance(source_colors_payload, dict) else {}
        provider["colors"] = copy.deepcopy(source_colors)

        for key in ("accent_rgb", "accent_soft_rgb"):
            raw = source.get(key)
            if isinstance(raw, list) and len(raw) >= 3:
                provider[key] = [_normalize_rgb_component(value) for value in raw[:3]]

    def _derive_theme_colors(
        categories: dict[str, str],
    ) -> tuple[dict[str, str], tuple[int, int, int], tuple[int, int, int]]:
        background_rgb = _hex_to_rgb(categories.get("background", ""))
        text_rgb = _hex_to_rgb(categories.get("text", ""))
        accent_rgb = _hex_to_rgb(categories.get("accent", ""))
        status_rgb = _hex_to_rgb(categories.get("status", ""))

        if background_rgb is None:
            background_rgb = (30, 37, 36)
        if text_rgb is None:
            text_rgb = (231, 240, 237)
        if accent_rgb is None:
            accent_rgb = (16, 163, 127)
        if status_rgb is None:
            status_rgb = (97, 197, 146)

        accent_soft_rgb = _lighten_rgb(accent_rgb, 0.26)
        button_base = _lighten_rgb(background_rgb, 0.06)
        button_hover = _lighten_rgb(background_rgb, 0.10)
        button_active = _lighten_rgb(background_rgb, 0.14)
        muted_text = _mix_rgb(text_rgb, background_rgb, 0.55)
        warning_rgb = _mix_rgb(status_rgb, (217, 168, 94), 0.70)
        error_rgb = _mix_rgb(status_rgb, (212, 124, 115), 0.75)

        colors = {
            "window_bg": _to_hex_with_prefix(*background_rgb),
            "header_bg": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.06)),
            "header_gradient_end": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.14)),
            "sidebar_bg": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.10)),
            "chat_outer_bg": _to_hex_with_prefix(*background_rgb),
            "chat_bg": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.04)),
            "status_bg": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.09)),
            "bottom_gradient_end": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.16)),
            "border": _to_hex_with_prefix(*_lighten_rgb(background_rgb, 0.20)),
            "border_soft": _to_hex_with_prefix(*_lighten_rgb(background_rgb, 0.12)),
            "foreground": _to_hex_with_prefix(*text_rgb),
            "foreground_muted": _to_hex_with_prefix(*muted_text),
            "accent": _to_hex_with_prefix(*accent_rgb),
            "accent_soft": _to_hex_with_prefix(*accent_soft_rgb),
            "warning": _to_hex_with_prefix(*warning_rgb),
            "error": _to_hex_with_prefix(*error_rgb),
            "success": _to_hex_with_prefix(*status_rgb),
            "button_bg": _to_hex_with_prefix(*button_base),
            "button_bg_hover": _to_hex_with_prefix(*button_hover),
            "button_bg_active": _to_hex_with_prefix(*button_active),
            "new_session_bg": _to_hex_with_prefix(*button_base),
            "new_session_border": _to_hex_with_prefix(*_lighten_rgb(button_base, 0.14)),
            "sidebar_toggle_collapsed_bg": _to_hex_with_prefix(*button_hover),
            "menu_bg": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.12)),
            "popover_bg": _to_hex_with_prefix(*_darken_rgb(background_rgb, 0.10)),
            "session_filter_bg": _to_hex_with_prefix(*button_base),
            "session_filter_hover_bg": _to_hex_with_prefix(*button_hover),
            "session_filter_active_fg": _to_hex_with_prefix(*_lighten_rgb(text_rgb, 0.08)),
            "session_row_hover_bg": _to_hex_with_prefix(*_lighten_rgb(background_rgb, 0.06)),
            "session_row_active_bg": _to_hex_with_prefix(*_lighten_rgb(background_rgb, 0.11)),
            "status_dot_ended": _to_hex_with_prefix(*_mix_rgb(status_rgb, background_rgb, 0.55)),
            "status_dot_archived": _to_hex_with_prefix(*_mix_rgb(status_rgb, background_rgb, 0.72)),
            "context_trough_bg": _to_hex_with_prefix(*_lighten_rgb(background_rgb, 0.10)),
            "session_meta_time": _to_hex_with_prefix(*_mix_rgb(text_rgb, background_rgb, 0.22)),
        }
        return colors, accent_rgb, accent_soft_rgb

    def _apply_theme_categories(provider_id: str, categories: dict[str, str]) -> None:
        providers = working_payload.get("providers")
        if not isinstance(providers, dict):
            return
        provider_payload = providers.get(provider_id)
        if not isinstance(provider_payload, dict):
            return

        normalized_categories: dict[str, str] = {}
        for category_key, _label in theme_category_order:
            normalized_categories[category_key] = (
                _normalize_hex(categories.get(category_key, "")) or _extract_provider_theme_categories(provider_payload)[category_key]
            )

        derived_colors, accent_rgb, accent_soft_rgb = _derive_theme_colors(normalized_categories)
        colors_payload = provider_payload.get("colors")
        if not isinstance(colors_payload, dict):
            colors_payload = {}

        merged_colors = dict(colors_payload)
        merged_colors.update(derived_colors)

        provider_payload["colors"] = merged_colors
        provider_payload["accent_rgb"] = list(accent_rgb)
        provider_payload["accent_soft_rgb"] = list(accent_soft_rgb)
        provider_theme_categories[provider_id] = normalized_categories

    def _update_provider_model_payload(provider_id: str, model_store: Gtk.ListStore) -> None:
        provider = working_payload["providers"].get(provider_id)
        if not isinstance(provider, dict):
            return
        options: list[dict[str, str]] = []
        for row in model_store:
            label = str(row[0]).strip() or "Model"
            value = str(row[1]).strip() or label.lower().replace(" ", "-")
            options.append({"label": label, "value": value})
        provider["model_options"] = options

    def _normalize_payload() -> tuple[bool, str, Gtk.Entry | None]:
        _clear_theme_entry_validation()
        providers = working_payload.get("providers")
        if not isinstance(providers, dict):
            return (False, "Settings payload is missing providers.", None)
        working_payload["system_tray_enabled"] = bool(working_payload.get("system_tray_enabled", True))

        categories_by_provider: dict[str, dict[str, str]] = {}
        for (provider_id, category_key), entry in theme_category_entry_map.items():
            normalized = _normalize_hex(entry.get_text())
            if normalized is None:
                _set_entry_validation(entry, "Use #RRGGBB")
                return (
                    False,
                    f"Invalid theme category value in {provider_id}.{category_key}. Use #RRGGBB.",
                    entry,
                )
            _set_entry_validation(entry, None)
            if entry.get_text().strip().lower() != normalized:
                entry.set_text(normalized)
            categories_by_provider.setdefault(provider_id, {})[category_key] = normalized

        for provider_id, provider in providers.items():
            if not isinstance(provider, dict):
                return (False, f"Provider '{provider_id}' is invalid.", None)
            fallback_categories = _extract_provider_theme_categories(provider)
            merged_categories = dict(fallback_categories)
            merged_categories.update(provider_theme_categories.get(provider_id, {}))
            merged_categories.update(categories_by_provider.get(provider_id, {}))
            if merged_categories != fallback_categories:
                _apply_theme_categories(provider_id, merged_categories)

        for provider_id, provider in providers.items():
            if not isinstance(provider, dict):
                return (False, f"Provider '{provider_id}' is invalid.", None)
            colors = provider.get("colors")
            if not isinstance(colors, dict):
                return (False, f"Provider '{provider_id}' colors are missing.", None)
            for key, value in list(colors.items()):
                normalized = _normalize_hex(str(value))
                if normalized is None:
                    return (
                        False,
                        f"Invalid color value in {provider_id}.{key}. Use #RRGGBB.",
                        None,
                    )
                colors[key] = normalized

            defaults = get_default_settings()
            defaults_providers = defaults.get("providers")
            default_provider = (
                defaults_providers.get(provider_id)
                if isinstance(defaults_providers, dict)
                else None
            )
            default_provider_payload = default_provider if isinstance(default_provider, dict) else {}

            accent_rgb = _normalize_rgb_list(provider.get("accent_rgb"))
            if accent_rgb is None:
                accent_hex = _normalize_hex(str(colors.get("accent", "")))
                parsed_accent_rgb = _hex_to_rgb(accent_hex) if accent_hex is not None else None
                accent_rgb = list(parsed_accent_rgb) if parsed_accent_rgb is not None else None
            if accent_rgb is None:
                accent_rgb = _normalize_rgb_list(default_provider_payload.get("accent_rgb"))
            if accent_rgb is None:
                accent_rgb = [16, 163, 127]
            provider["accent_rgb"] = accent_rgb

            accent_soft_rgb = _normalize_rgb_list(provider.get("accent_soft_rgb"))
            if accent_soft_rgb is None:
                accent_soft_hex = _normalize_hex(str(colors.get("accent_soft", "")))
                parsed_accent_soft_rgb = _hex_to_rgb(accent_soft_hex) if accent_soft_hex is not None else None
                accent_soft_rgb = list(parsed_accent_soft_rgb) if parsed_accent_soft_rgb is not None else None
            if accent_soft_rgb is None:
                accent_soft_rgb = _normalize_rgb_list(default_provider_payload.get("accent_soft_rgb"))
            if accent_soft_rgb is None:
                accent_soft_rgb = list(_lighten_rgb((accent_rgb[0], accent_rgb[1], accent_rgb[2]), 0.26))
            provider["accent_soft_rgb"] = accent_soft_rgb

            model_options = provider.get("model_options", [])
            normalized_models: list[dict[str, str]] = []
            if not isinstance(model_options, list) or not model_options:
                return (False, f"Provider '{provider_id}' must define at least one model option.", None)
            for entry in model_options:
                if not isinstance(entry, dict):
                    continue
                label = str(entry.get("label", "")).strip() or "Model"
                value = str(entry.get("value", "")).strip() or label.lower().replace(" ", "-")
                normalized_models.append({"label": label, "value": value})
            if normalized_models:
                provider["model_options"] = normalized_models
            else:
                return (False, f"Provider '{provider_id}' has invalid model options.", None)

        return (True, "", None)

    def _build_provider_page(provider_id: str, payload: dict[str, Any]) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(8)
        _add_css_classes(page, "settings-page")

        provider = working_payload["providers"].get(provider_id, {})
        if not isinstance(provider, dict):
            provider = copy.deepcopy(payload)
            working_payload["providers"][provider_id] = provider
        extracted_categories = _extract_provider_theme_categories(provider)
        provider_theme_categories[provider_id] = extracted_categories

        name = str(payload.get("name", provider_id))
        provider_label = Gtk.Label(label=f"Provider: {name}")
        provider_label.set_xalign(0.0)
        _add_css_classes(provider_label, "settings-provider-title")
        page.pack_start(provider_label, False, False, 0)

        is_gemini_provider = provider_id.strip().lower() == "gemini"
        support_reasoning: Gtk.CheckButton | None = None
        if is_gemini_provider:
            provider["supports_reasoning"] = False
        else:
            support_reasoning = Gtk.CheckButton(label="Enable reasoning controls for this provider")
            support_reasoning.set_active(bool(provider.get("supports_reasoning", True)))

        preview_frame = Gtk.Frame(label="Preview")
        _add_css_classes(preview_frame, "settings-card")
        preview_root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_root.set_border_width(10)

        preview_title = Gtk.Label(label=f"{name} preview")
        preview_title.set_xalign(0.0)
        preview_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preview_header.pack_start(preview_title, True, True, 0)

        preview_user = Gtk.Frame()
        preview_user_label = Gtk.Label(label="User message")
        preview_user_label.set_xalign(0.0)
        preview_user_label.set_margin_start(8)
        preview_user_label.set_margin_end(8)
        preview_user_label.set_margin_top(6)
        preview_user_label.set_margin_bottom(6)
        preview_user.add(preview_user_label)

        preview_assistant = Gtk.Frame()
        preview_assistant_label = Gtk.Label(label="Assistant response")
        preview_assistant_label.set_xalign(0.0)
        preview_assistant_label.set_margin_start(8)
        preview_assistant_label.set_margin_end(8)
        preview_assistant_label.set_margin_top(6)
        preview_assistant_label.set_margin_bottom(6)
        preview_assistant.add(preview_assistant_label)

        preview_model_label = Gtk.Label(label="Model: default")
        preview_model_label.set_xalign(0.0)
        preview_reason_label = Gtk.Label(label="Reasoning controls: enabled")
        preview_reason_label.set_xalign(0.0)

        preview_root.pack_start(preview_header, False, False, 0)
        preview_root.pack_start(preview_user, False, False, 0)
        preview_root.pack_start(preview_assistant, False, False, 0)
        preview_root.pack_start(preview_model_label, False, False, 0)
        preview_root.pack_start(preview_reason_label, False, False, 0)
        preview_frame.add(preview_root)

        def _apply_preview() -> None:
            providers_payload = working_payload.get("providers")
            if isinstance(providers_payload, dict):
                raw_provider = providers_payload.get(provider_id, {})
            else:
                raw_provider = {}
            current_provider = raw_provider if isinstance(raw_provider, dict) else {}
            raw_colors = current_provider.get("colors", {})
            colors = raw_colors if isinstance(raw_colors, dict) else {}

            window_bg = _normalize_hex(str(colors.get("window_bg", "#1f1f1a"))) or "#1f1f1a"
            header_bg = _normalize_hex(str(colors.get("header_bg", "#262621"))) or "#262621"
            user_bg = _normalize_hex(str(colors.get("button_bg", "#3a3a34"))) or "#3a3a34"
            assistant_bg = _normalize_hex(str(colors.get("chat_bg", "#2f2f2a"))) or "#2f2f2a"
            fg = _normalize_hex(str(colors.get("foreground", "#d4d4c8"))) or "#d4d4c8"

            _set_bg(preview_root, window_bg)
            _set_bg(preview_header, header_bg)
            _set_bg(preview_user, user_bg)
            _set_bg(preview_assistant, assistant_bg)
            _set_fg(preview_title, fg)
            _set_fg(preview_user_label, fg)
            _set_fg(preview_assistant_label, fg)
            _set_fg(preview_model_label, fg)
            _set_fg(preview_reason_label, fg)

            model_options_raw = current_provider.get("model_options", [])
            model_options = model_options_raw if isinstance(model_options_raw, list) else []
            model_value = "default"
            for item in model_options:
                if not isinstance(item, dict):
                    continue
                candidate = str(item.get("value", "")).strip()
                if candidate:
                    model_value = candidate
                    break
            preview_model_label.set_text(f"Model: {model_value}")

            if current_provider.get("supports_reasoning", False):
                preview_reason_label.set_text("Reasoning controls: enabled")
            else:
                preview_reason_label.set_text("Reasoning controls: disabled")

        if support_reasoning is not None:
            support_reasoning.connect(
                "toggled",
                lambda button: (
                    provider.__setitem__("supports_reasoning", bool(button.get_active())),
                    _apply_preview(),
                ),
            )
            _add_css_classes(support_reasoning, "settings-toggle")
            page.pack_start(support_reasoning, False, False, 0)

        theme_frame = Gtk.Frame(label="Theme")
        _add_css_classes(theme_frame, "settings-card")
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        theme_box.set_border_width(10)

        theme_hint = Gtk.Label(
            label="Farbkategorien: Hintergrund, Text, Akzent, Status.",
        )
        theme_hint.set_xalign(0.0)
        theme_hint.set_line_wrap(True)
        _add_css_classes(theme_hint, "settings-muted")
        theme_box.pack_start(theme_hint, False, False, 0)
        category_grid = Gtk.Grid()
        category_grid.set_row_spacing(6)
        category_grid.set_column_spacing(8)
        current_categories = dict(provider_theme_categories.get(provider_id, {}))

        def _theme_category_changed(
            entry: Gtk.Entry,
            pid: str,
            category_key: str,
            button: Gtk.ColorButton,
        ) -> None:
            raw_text = entry.get_text().strip()
            # Ignore partial typing states to keep the dialog responsive.
            if raw_text and len(raw_text) < 7:
                return
            normalized = _normalize_hex(raw_text)
            if normalized is None:
                _set_entry_validation(entry, "Use #RRGGBB")
                return
            _set_entry_validation(entry, None)
            provider_categories = dict(provider_theme_categories.get(pid, {}))
            provider_categories[category_key] = normalized
            _apply_theme_categories(pid, provider_categories)
            button_color = _hex_to_rgba(normalized)
            if button_color is not None:
                button.set_rgba(button_color)
            _apply_preview()

        def _theme_category_button_changed(button: Gtk.ColorButton, field: Gtk.Entry) -> None:
            field.set_text(_rgba_to_hex(button.get_rgba()))

        def _reset_theme_to_default(_button: Gtk.Button | None = None) -> None:
            defaults = get_default_settings()
            providers_payload = defaults.get("providers")
            if not isinstance(providers_payload, dict):
                return
            default_provider = providers_payload.get(provider_id)
            if not isinstance(default_provider, dict):
                return
            default_categories = _extract_provider_theme_categories(default_provider)
            _copy_provider_theme(provider, default_provider)
            provider_theme_categories[provider_id] = default_categories
            for category_key, _label in theme_category_order:
                entry = theme_category_entry_map.get((provider_id, category_key))
                if entry is not None:
                    entry.set_text(default_categories[category_key])
            _apply_preview()

        for row, (category_key, category_label) in enumerate(theme_category_order):
            label = Gtk.Label(label=category_label)
            label.set_xalign(0.0)
            _add_css_classes(label, "settings-muted")
            category_grid.attach(label, 0, row, 1, 1)

            value_entry = Gtk.Entry()
            value_entry.set_width_chars(10)
            value_entry.set_placeholder_text("#000000")
            _add_css_classes(value_entry, "settings-entry")

            category_value = _normalize_hex(current_categories.get(category_key, "")) or "#000000"
            value_entry.set_text(category_value)
            theme_category_entry_map[(provider_id, category_key)] = value_entry

            color_button = Gtk.ColorButton()
            color_button.set_use_alpha(False)
            _add_css_classes(color_button, "settings-color-button", "button")
            parsed_rgba = _hex_to_rgba(category_value)
            if parsed_rgba is not None:
                color_button.set_rgba(parsed_rgba)

            value_entry.connect(
                "changed",
                lambda entry, pid=provider_id, cat=category_key, button=color_button: _theme_category_changed(
                    entry,
                    pid,
                    cat,
                    button,
                ),
            )
            color_button.connect(
                "color-set",
                lambda button, field=value_entry: _theme_category_button_changed(button, field),
            )

            category_grid.attach(value_entry, 1, row, 1, 1)
            category_grid.attach(color_button, 2, row, 1, 1)

        reset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        reset_button = Gtk.Button(label="Auf Standard zurücksetzen")
        _add_css_classes(reset_button, "button", "settings-preset-button")
        reset_button.connect("clicked", _reset_theme_to_default)
        reset_row.pack_start(reset_button, False, False, 0)

        theme_box.pack_start(category_grid, False, False, 0)
        theme_box.pack_start(reset_row, False, False, 0)

        theme_frame.add(theme_box)
        page.pack_start(theme_frame, False, False, 0)

        models_frame = Gtk.Frame(label="Model options")
        _add_css_classes(models_frame, "settings-card")
        models_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        models_box.set_border_width(10)
        models_frame.add(models_box)

        model_store = Gtk.ListStore(str, str)
        for model_entry in provider.get("model_options", []):
            if not isinstance(model_entry, dict):
                continue
            model_store.append(
                (
                    str(model_entry.get("label", "")) or "Model",
                    str(model_entry.get("value", "")) or "model",
                ),
            )

        model_view = Gtk.TreeView(model=model_store)
        _add_css_classes(model_view, "settings-treeview")

        model_label_renderer = Gtk.CellRendererText()
        model_label_renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        model_label_column = Gtk.TreeViewColumn("Label", model_label_renderer, text=0)
        model_label_column.set_resizable(True)
        model_label_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        model_label_column.set_fixed_width(190)
        model_label_column.set_min_width(150)
        model_view.append_column(model_label_column)

        model_value_renderer = Gtk.CellRendererText()
        model_value_renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        model_value_column = Gtk.TreeViewColumn("Value", model_value_renderer, text=1)
        model_value_column.set_resizable(True)
        model_value_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        model_value_column.set_fixed_width(250)
        model_value_column.set_min_width(170)
        model_view.append_column(model_value_column)
        model_view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        model_scroller = Gtk.ScrolledWindow()
        model_scroller.set_hexpand(True)
        model_scroller.set_vexpand(True)
        model_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        model_scroller.set_min_content_height(130)
        model_scroller.add(model_view)
        _add_css_classes(model_scroller, "settings-inner-scroller")
        models_box.pack_start(model_scroller, True, True, 0)

        model_edit = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        model_label_entry = Gtk.Entry()
        model_label_entry.set_placeholder_text("Model label")
        model_label_entry.set_hexpand(True)
        _add_css_classes(model_label_entry, "settings-entry")

        model_value_entry = Gtk.Entry()
        model_value_entry.set_placeholder_text("Model value")
        model_value_entry.set_hexpand(True)
        _add_css_classes(model_value_entry, "settings-entry")

        model_edit.pack_start(model_label_entry, True, True, 0)
        model_edit.pack_start(model_value_entry, True, True, 0)
        models_box.pack_start(model_edit, False, False, 0)

        model_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        model_add_btn = Gtk.Button(label="Add")
        model_update_btn = Gtk.Button(label="Update")
        model_remove_btn = Gtk.Button(label="Remove")
        _add_css_classes(model_add_btn, "button")
        _add_css_classes(model_update_btn, "button")
        _add_css_classes(model_remove_btn, "button")
        model_btn_box.pack_start(model_add_btn, False, False, 0)
        model_btn_box.pack_start(model_update_btn, False, False, 0)
        model_btn_box.pack_start(model_remove_btn, False, False, 0)
        models_box.pack_start(model_btn_box, False, False, 0)

        selected_model = {"iter": None}

        def _model_selection_changed(selection: Gtk.TreeSelection) -> None:
            _, model_iter = selection.get_selected()
            selected_model["iter"] = model_iter
            if model_iter is None:
                return
            model_label_entry.set_text(str(model_store[model_iter][0]))
            model_value_entry.set_text(str(model_store[model_iter][1]))

        def _model_remove_if_selected() -> None:
            row_iter = selected_model["iter"]
            if row_iter is None:
                return
            model_store.remove(row_iter)
            selected_model["iter"] = None
            if len(model_store) == 0:
                model_store.append(("Default", "model"))
            _update_provider_model_payload(provider_id, model_store)
            _apply_preview()

        def _model_add(_button: Gtk.Button | None = None) -> None:
            model_store.append(
                (
                    model_label_entry.get_text().strip() or "Model",
                    model_value_entry.get_text().strip() or "model",
                ),
            )
            _update_provider_model_payload(provider_id, model_store)
            _apply_preview()

        def _model_update(_button: Gtk.Button | None = None) -> None:
            row_iter = selected_model["iter"]
            if row_iter is None:
                return
            model_store.set_value(
                row_iter,
                0,
                model_label_entry.get_text().strip() or "Model",
            )
            model_store.set_value(
                row_iter,
                1,
                model_value_entry.get_text().strip() or "model",
            )
            _update_provider_model_payload(provider_id, model_store)
            _apply_preview()

        def _model_remove(_button: Gtk.Button | None = None) -> None:
            _model_remove_if_selected()

        model_view.get_selection().connect("changed", _model_selection_changed)
        model_add_btn.connect("clicked", _model_add)
        model_update_btn.connect("clicked", _model_update)
        model_remove_btn.connect("clicked", _model_remove)
        _update_provider_model_payload(provider_id, model_store)

        page.pack_start(models_frame, True, True, 0)
        page.pack_start(preview_frame, False, False, 0)

        _apply_preview()
        return page

    providers = working_payload.get("providers")
    if isinstance(providers, dict):
        for provider_id, provider_payload in providers.items():
            if not isinstance(provider_payload, dict):
                continue
            page = _build_provider_page(provider_id, provider_payload)
            label = Gtk.Label(label=str(provider_payload.get("name", provider_id)))
            _add_css_classes(label, "settings-tab-label")
            notebook.append_page(page, label)

    content_area.show_all()

    while True:
        response = window._run_dialog(dialog)
        if response != Gtk.ResponseType.OK:
            break

        valid_payload, validation_error, invalid_entry = _normalize_payload()
        if not valid_payload:
            validation_label.set_text(validation_error or "Invalid settings values.")
            validation_label.set_visible(True)
            if invalid_entry is not None:
                invalid_entry.grab_focus()
            continue
        validation_label.set_visible(False)

        try:
            save_settings(working_payload)
            persisted_payload = load_settings()
            window._apply_settings_payload(
                persisted_payload,
                reload_webviews=True,
                show_startscreen_after_reload=False,
            )
        except (OSError, ValueError, TypeError) as error:
            msg = Gtk.MessageDialog(
                transient_for=window,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Could not save settings",
            )
            msg.format_secondary_text(str(error))
            window._run_dialog(msg)
            msg.destroy()
            continue
        window._set_status_message("Settings saved and applied.", STATUS_INFO)
        break

    dialog.destroy()
