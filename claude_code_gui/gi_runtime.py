"""GI runtime compatibility layer (GTK4-first, GTK3 fallback)."""

from __future__ import annotations

import gi


GTK4 = False
WEBKIT6 = False

try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("WebKit", "6.0")
    GTK4 = True
    WEBKIT6 = True
    from gi.repository import Gdk, Gio, GLib, Gtk, Pango, WebKit
except ValueError:
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    try:
        gi.require_version("WebKit2", "4.1")
    except ValueError:
        gi.require_version("WebKit2", "4.0")
    from gi.repository import Gdk, Gio, GLib, Gtk, Pango, WebKit2 as WebKit


if GTK4:
    _main_loop: GLib.MainLoop | None = None

    if not hasattr(Gtk, "ReliefStyle"):
        class _ReliefStyle:
            NONE = 0

        Gtk.ReliefStyle = _ReliefStyle

    if not hasattr(Gtk, "ShadowType"):
        class _ShadowType:
            NONE = 0

        Gtk.ShadowType = _ShadowType

    if not hasattr(Gtk, "IconSize"):
        class _IconSize:
            BUTTON = 1

        Gtk.IconSize = _IconSize
    elif not hasattr(Gtk.IconSize, "BUTTON"):
        Gtk.IconSize.BUTTON = 1

    if not hasattr(Gtk, "ModelButton"):
        Gtk.ModelButton = Gtk.Button

    if not hasattr(Gtk, "main"):
        def _gtk_main() -> None:
            global _main_loop
            if _main_loop is None:
                _main_loop = GLib.MainLoop()
            _main_loop.run()

        Gtk.main = _gtk_main

    if not hasattr(Gtk, "main_quit"):
        def _gtk_main_quit() -> None:
            global _main_loop
            if _main_loop is not None and _main_loop.is_running():
                _main_loop.quit()
            _main_loop = None

        Gtk.main_quit = _gtk_main_quit

    if not hasattr(Gtk.Button, "set_relief"):
        Gtk.Button.set_relief = lambda self, _relief: None
    if hasattr(Gtk, "MenuButton") and not hasattr(Gtk.MenuButton, "set_relief"):
        Gtk.MenuButton.set_relief = lambda self, _relief: None

    if not hasattr(Gtk.Label, "set_line_wrap"):
        Gtk.Label.set_line_wrap = lambda self, enabled: self.set_wrap(enabled)

    if not hasattr(Gtk.Widget, "show_all"):
        Gtk.Widget.show_all = lambda self: self.set_visible(True)

    if not hasattr(Gtk.Widget, "show"):
        Gtk.Widget.show = lambda self: self.set_visible(True)
    if not hasattr(Gtk.Widget, "set_border_width"):
        Gtk.Widget.set_border_width = lambda self, w: (
            self.set_margin_start(w),
            self.set_margin_end(w),
            self.set_margin_top(w),
            self.set_margin_bottom(w),
        )

    def _rgba_to_css(rgba) -> str:
        red = max(0, min(255, round(float(rgba.red) * 255)))
        green = max(0, min(255, round(float(rgba.green) * 255)))
        blue = max(0, min(255, round(float(rgba.blue) * 255)))
        alpha = max(0.0, min(1.0, float(rgba.alpha)))
        return f"rgba({red}, {green}, {blue}, {alpha:.3f})"

    def _apply_widget_override_css(widget: Gtk.Widget, *, bg: str | None = None, fg: str | None = None) -> None:
        styles = getattr(widget, "_compat_override_styles", {})
        if bg is not None:
            styles["background-color"] = bg
        if fg is not None:
            styles["color"] = fg
        if not styles:
            return

        name = widget.get_name() if hasattr(widget, "get_name") else ""
        if not name or name.startswith("Gtk"):
            name = f"compat-override-{id(widget)}"
            if hasattr(widget, "set_name"):
                widget.set_name(name)

        css_body = " ".join(f"{prop}: {value};" for prop, value in styles.items())
        provider = getattr(widget, "_compat_override_provider", None)
        if provider is None:
            provider = Gtk.CssProvider()
            widget._compat_override_provider = provider

        try:
            provider.load_from_data(f"#{name} {{ {css_body} }}".encode("utf-8"))
            context = widget.get_style_context()
            if not getattr(widget, "_compat_override_provider_installed", False):
                context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                widget._compat_override_provider_installed = True
            widget._compat_override_styles = styles
        except Exception:
            return

    if not hasattr(Gtk.Widget, "override_background_color"):
        def _override_background_color(self, _state, rgba) -> None:
            if rgba is None:
                return
            _apply_widget_override_css(self, bg=_rgba_to_css(rgba))

        Gtk.Widget.override_background_color = _override_background_color

    if not hasattr(Gtk.Widget, "override_color"):
        def _override_color(self, _state, rgba) -> None:
            if rgba is None:
                return
            _apply_widget_override_css(self, fg=_rgba_to_css(rgba))

        Gtk.Widget.override_color = _override_color

    _image_ctor = Gtk.Image.new_from_icon_name
    Gtk.Image.new_from_icon_name = staticmethod(lambda icon_name, *_args: _image_ctor(icon_name))

    if not hasattr(Gtk.Window, "add"):
        Gtk.Window.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.Button, "add"):
        Gtk.Button.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.Overlay, "add"):
        Gtk.Overlay.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.ScrolledWindow, "add"):
        Gtk.ScrolledWindow.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.ScrolledWindow, "set_shadow_type"):
        Gtk.ScrolledWindow.set_shadow_type = lambda self, _shadow_type: None

    if not hasattr(Gtk.Popover, "add"):
        Gtk.Popover.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.Popover, "set_modal"):
        Gtk.Popover.set_modal = lambda self, _modal: None

    _popover_new = Gtk.Popover.new

    def _popover_new_compat(*args):
        popover = _popover_new()
        relative = args[0] if args else None
        if relative is not None:
            try:
                if hasattr(popover, "set_relative_to"):
                    popover.set_relative_to(relative)
                elif hasattr(popover, "set_parent"):
                    popover.set_parent(relative)
            except Exception:
                pass
        return popover

    Gtk.Popover.new = staticmethod(_popover_new_compat)

    if not hasattr(Gtk.Frame, "add"):
        Gtk.Frame.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.ListBoxRow, "add"):
        Gtk.ListBoxRow.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.Box, "pack_start"):
        Gtk.Box.pack_start = lambda self, child, _expand, _fill, _padding: self.append(child)

    if not hasattr(Gtk.Box, "pack_end"):
        Gtk.Box.pack_end = lambda self, child, _expand, _fill, _padding: self.append(child)

    if not hasattr(Gtk.Paned, "pack1"):
        Gtk.Paned.pack1 = lambda self, child, _resize, _shrink: self.set_start_child(child)

    if not hasattr(Gtk.Paned, "pack2"):
        Gtk.Paned.pack2 = lambda self, child, _resize, _shrink: self.set_end_child(child)

    if not hasattr(Gtk.Paned, "get_child1"):
        Gtk.Paned.get_child1 = lambda self: self.get_start_child()

    if not hasattr(Gtk.Paned, "get_child2"):
        Gtk.Paned.get_child2 = lambda self: self.get_end_child()

    if not hasattr(Gtk.Box, "get_children"):
        def _box_get_children(self: Gtk.Box) -> list[Gtk.Widget]:
            children: list[Gtk.Widget] = []
            child = self.get_first_child()
            while child is not None:
                children.append(child)
                child = child.get_next_sibling()
            return children

        Gtk.Box.get_children = _box_get_children

    if not hasattr(Gtk.ListBox, "get_children"):
        def _listbox_get_children(self: Gtk.ListBox) -> list[Gtk.Widget]:
            children: list[Gtk.Widget] = []
            child = self.get_first_child()
            while child is not None:
                children.append(child)
                child = child.get_next_sibling()
            return children

        Gtk.ListBox.get_children = _listbox_get_children
    if not hasattr(Gtk.ListBox, "add"):
        Gtk.ListBox.add = lambda self, child: self.append(child)

    if not hasattr(Gtk.StyleContext, "add_provider_for_screen"):
        def _add_provider_for_screen(_screen, provider, priority) -> None:
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.add_provider_for_display(display, provider, priority)

        Gtk.StyleContext.add_provider_for_screen = _add_provider_for_screen

    if not hasattr(Gtk.StyleContext, "remove_provider_for_screen"):
        def _remove_provider_for_screen(_screen, provider) -> None:
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.remove_provider_for_display(display, provider)

        Gtk.StyleContext.remove_provider_for_screen = _remove_provider_for_screen

    if not hasattr(Gtk, "EventBox"):
        class EventBox(Gtk.Box):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def set_visible_window(self, _visible: bool) -> None:
                return None

            def add(self, child: Gtk.Widget) -> None:
                self.append(child)

        Gtk.EventBox = EventBox

    if not hasattr(Gtk.Dialog, "run"):
        def _dialog_run(self: Gtk.Dialog) -> int:
            loop = GLib.MainLoop()
            response_holder = {"value": int(Gtk.ResponseType.CANCEL)}

            def _on_response(_dialog: Gtk.Dialog, response_id: int) -> None:
                response_holder["value"] = int(response_id)
                if loop.is_running():
                    loop.quit()

            handler_id = self.connect("response", _on_response)
            self.set_visible(True)
            loop.run()
            self.disconnect(handler_id)
            return int(response_holder["value"])

        Gtk.Dialog.run = _dialog_run
