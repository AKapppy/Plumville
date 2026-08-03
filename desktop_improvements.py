from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import legacy_core as base
import path_detection
from plumville.desktop import inspector
from plumville.desktop import workspace


ROUTE_FIT_MIN_SPAN = 900.0
ROUTE_FIT_MARGIN_PIXELS = 72.0
WEB_BG = "#080b0d"
WEB_PANEL = "#101417"
WEB_PANEL_RAISED = "#151b1f"
WEB_PANEL_INSET = "#090c0e"
WEB_PANEL_HOVER = "#20282d"
WEB_INK = "#f5f7f2"
WEB_MUTED = "#9aa59f"
WEB_FAINT = "#68736d"
WEB_LINE = "#2b3439"
WEB_BORDER_LIGHT = "#465159"
WEB_BORDER_DARK = "#050708"
WEB_FIELD = "#090c0e"
WEB_FIELD_ACTIVE = "#12181c"
WEB_EMERALD = "#55b86a"
WEB_GOLD = "#f0c75e"
WEB_REDSTONE = "#de5750"
WEB_DIAMOND = "#72c9ec"
WEB_FOCUS_RING = "#5e9cb5"
WORLDGEN_COMPLETE_COLOR = WEB_EMERALD
DESKTOP_MODE_DEFAULT_KEY = "all"
MMCP_SURFACE = WEB_PANEL
MMCP_SURFACE_ALT = WEB_PANEL_RAISED
MMCP_SURFACE_RAISED = WEB_FIELD_ACTIVE
MMCP_BORDER = WEB_BORDER_LIGHT
MMCP_BORDER_DIM = WEB_LINE
MMCP_DIAMOND = WEB_DIAMOND
MMCP_EMERALD = WEB_EMERALD
MMCP_GOLD = WEB_GOLD
MMCP_REDSTONE = WEB_REDSTONE
MMCP_MUTED = WEB_MUTED
MMCP_TEXT_DARK = "#091117"
MMCP_MONO_FONT = "Courier"
MMCP_SYMBOL_STATION = "◆"
MMCP_SYMBOL_JUNCTION = "◆◆"

_ORIGINAL_BUILD_ROUTE_PANEL: Callable[..., None] | None = None
_ORIGINAL_REFRESH_CURRENT_ROUTE: Callable[..., None] | None = None
_ORIGINAL_PLAN_ROUTE: Callable[..., None] | None = None
_ORIGINAL_ON_ROUTE_OPTIONS_CHANGED: Callable[..., None] | None = None
_ORIGINAL_SET_WORLD_MAP_STATUS_TEXT: Callable[..., None] | None = None
_ORIGINAL_REFRESH_PRIORITY_LIST: Callable[..., None] | None = None
_ORIGINAL_REDRAW: Callable[..., None] | None = None
_ORIGINAL_CENTER_DIALOG: Callable[..., None] | None = None
_ORIGINAL_CENTER_TOPLEVEL: Callable[..., None] | None = None
_NORMAL_DRAW_SELECTED_STOP_INFO: Callable[..., None] | None = None
_ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO: Callable[..., None] | None = None
_ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO: Callable[..., None] | None = None
_ORIGINAL_MAKE_COLLAPSIBLE_SIDEBAR_SECTION: (
    Callable[..., tk.Frame] | None
) = None
_ORIGINAL_MAKE_SIDEBAR_CAPTION: Callable[..., tk.Label] | None = None
_ORIGINAL_MAKE_SIDEBAR_HINT: Callable[..., tk.Label] | None = None
_ORIGINAL_MAKE_SIDEBAR_ENTRY: Callable[..., tk.Entry] | None = None
_ORIGINAL_MAKE_SIDEBAR_OPTION_MENU: (
    Callable[..., tk.Menubutton] | None
) = None
_ORIGINAL_MAKE_SIDEBAR_BUTTON: Callable[..., tk.Label] | None = None
_ORIGINAL_CONFIGURE_SIDEBAR_BUTTON: Callable[..., None] | None = None
_ORIGINAL_MAKE_SIDEBAR_CHECKBOX: (
    Callable[..., tk.Checkbutton] | None
) = None
_ORIGINAL_MAKE_INFO_BUTTON: Callable[..., tk.Label] | None = None
_APPLIED = False
_APPLIED_ATTR = "_plumville_desktop_improvements_applied"
_ORIGINAL_ATTRS = {
    "_ORIGINAL_BUILD_ROUTE_PANEL": (
        "_plumville_desktop_original_build_route_panel"
    ),
    "_ORIGINAL_REFRESH_CURRENT_ROUTE": (
        "_plumville_desktop_original_refresh_current_route"
    ),
    "_ORIGINAL_PLAN_ROUTE": (
        "_plumville_desktop_original_plan_route"
    ),
    "_ORIGINAL_ON_ROUTE_OPTIONS_CHANGED": (
        "_plumville_desktop_original_on_route_options_changed"
    ),
    "_ORIGINAL_SET_WORLD_MAP_STATUS_TEXT": (
        "_plumville_desktop_original_set_world_map_status_text"
    ),
    "_ORIGINAL_REFRESH_PRIORITY_LIST": (
        "_plumville_desktop_original_refresh_priority_list"
    ),
    "_ORIGINAL_REDRAW": (
        "_plumville_desktop_original_redraw"
    ),
    "_ORIGINAL_CENTER_DIALOG": (
        "_plumville_desktop_original_center_dialog"
    ),
    "_ORIGINAL_CENTER_TOPLEVEL": (
        "_plumville_desktop_original_center_toplevel"
    ),
    "_NORMAL_DRAW_SELECTED_STOP_INFO": (
        "_plumville_desktop_normal_draw_selected_stop_info"
    ),
    "_ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO": (
        "_plumville_desktop_original_draw_selected_metro_segment_info"
    ),
    "_ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO": (
        "_plumville_desktop_original_draw_selected_path_node_info"
    ),
    "_ORIGINAL_MAKE_COLLAPSIBLE_SIDEBAR_SECTION": (
        "_plumville_desktop_original_make_collapsible_sidebar_section"
    ),
    "_ORIGINAL_MAKE_SIDEBAR_CAPTION": (
        "_plumville_desktop_original_make_sidebar_caption"
    ),
    "_ORIGINAL_MAKE_SIDEBAR_HINT": (
        "_plumville_desktop_original_make_sidebar_hint"
    ),
    "_ORIGINAL_MAKE_SIDEBAR_ENTRY": (
        "_plumville_desktop_original_make_sidebar_entry"
    ),
    "_ORIGINAL_MAKE_SIDEBAR_OPTION_MENU": (
        "_plumville_desktop_original_make_sidebar_option_menu"
    ),
    "_ORIGINAL_MAKE_SIDEBAR_BUTTON": (
        "_plumville_desktop_original_make_sidebar_button"
    ),
    "_ORIGINAL_CONFIGURE_SIDEBAR_BUTTON": (
        "_plumville_desktop_original_configure_sidebar_button"
    ),
    "_ORIGINAL_MAKE_SIDEBAR_CHECKBOX": (
        "_plumville_desktop_original_make_sidebar_checkbox"
    ),
    "_ORIGINAL_MAKE_INFO_BUTTON": (
        "_plumville_desktop_original_make_info_button"
    ),
}


@dataclass(slots=True)
class PackedWidgetRecord:
    widget: tk.Widget
    pack_options: dict[str, object]
    next_sibling: tk.Widget | None


@dataclass(frozen=True, slots=True)
class DesktopMode:
    key: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class MmcpButtonPalette:
    background: str
    active_background: str
    foreground: str
    border: str


@dataclass(slots=True)
class PackedSectionRecord:
    title: str
    widget: tk.Widget
    pack_options: dict[str, object]
    next_sibling: tk.Widget | None
    body_widget: tk.Widget | None = None


DESKTOP_MODES: tuple[DesktopMode, ...] = (
    DesktopMode(
        "all",
        "All",
        "Show all major desktop sections at once.",
    ),
    DesktopMode(
        "explore",
        "Explore",
        "Browse, search, inspect stations, and use the existing map tools.",
    ),
    DesktopMode(
        "directions",
        "Directions",
        "Plan and compare routes.",
    ),
    DesktopMode(
        "construction",
        "Construction",
        "Review railway and station completion work.",
    ),
    DesktopMode(
        "edit",
        "Edit",
        "Edit stations, paths, line metadata, and map annotations.",
    ),
    DesktopMode(
        "world",
        "World",
        "Render and inspect the Minecraft world map.",
    ),
    DesktopMode(
        "advanced",
        "Advanced",
        "Use experimental or rarely needed maintenance tools.",
    ),
)

MODE_SECTION_TITLES: dict[str, tuple[str, ...]] = {
    "all": (
        "Checklist",
        "Directions",
        "Pathing",
        "Railways",
        "Show/Hide",
        "Priority List",
        "World Map",
        "Advanced / Experimental",
    ),
    "explore": (
        "Checklist",
        "Show/Hide",
        "Priority List",
    ),
    "directions": (
        "Directions",
        "Show/Hide",
    ),
    "construction": (
        "Checklist",
        "Priority List",
        "Railways",
    ),
    "edit": (
        "Pathing",
        "Railways",
        "Show/Hide",
    ),
    "world": (
        "World Map",
        "Show/Hide",
    ),
    "advanced": (
        "Advanced / Experimental",
        "World Map",
    ),
}

MODE_SECTION_DEFAULT_EXPANDED: dict[str, tuple[str, ...]] = {
    "all": (),
    "explore": (),
    "directions": ("Directions",),
    "construction": ("Railways",),
    "edit": ("Pathing",),
    "world": ("World Map",),
    "advanced": ("Advanced / Experimental",),
}


def _line_badge_foreground(hex_color: str) -> str:
    if len(hex_color) != 7 or not hex_color.startswith("#"):
        return base.TEXT_COLOR
    try:
        red = int(hex_color[1:3], 16)
        green = int(hex_color[3:5], 16)
        blue = int(hex_color[5:7], 16)
    except ValueError:
        return base.TEXT_COLOR
    brightness = (red * 299) + (green * 587) + (blue * 114)
    return MMCP_TEXT_DARK if brightness >= 140000 else base.TEXT_COLOR


def _station_marker_text(stop_var: str) -> str:
    line_count = len(base.STOP_LINE_NAMES.get(stop_var, ()))
    return (
        MMCP_SYMBOL_JUNCTION
        if line_count >= 2
        else MMCP_SYMBOL_STATION
    )


def _station_marker_radius(stop_var: str) -> int:
    line_count = len(base.STOP_LINE_NAMES.get(stop_var, ()))
    return 8 if line_count >= 2 else 6


def _diamond_marker_points(
    center_x: float,
    center_y: float,
    radius: float,
) -> tuple[float, ...]:
    return (
        center_x,
        center_y - radius,
        center_x + radius,
        center_y,
        center_x,
        center_y + radius,
        center_x - radius,
        center_y,
    )


def _mmcp_button_palette(text: str) -> MmcpButtonPalette:
    normalized = text.casefold()
    if normalized in {"go", "route"}:
        return MmcpButtonPalette(
            background="#397b49",
            active_background="#2a6338",
            foreground=WEB_INK,
            border="#4f8e5c",
        )
    if normalized.startswith("fit"):
        return MmcpButtonPalette(
            background=WEB_PANEL_RAISED,
            active_background=WEB_PANEL_HOVER,
            foreground=WEB_DIAMOND,
            border=WEB_BORDER_LIGHT,
        )
    if any(
        keyword in normalized
        for keyword in ("detect", "experimental")
    ):
        return MmcpButtonPalette(
            background="#2a2415",
            active_background="#3a311c",
            foreground=WEB_GOLD,
            border="#8c743a",
        )
    return MmcpButtonPalette(
        background=WEB_PANEL_RAISED,
        active_background=WEB_PANEL_HOVER,
        foreground=WEB_INK,
        border=WEB_BORDER_LIGHT,
    )


def _style_mmcp_button(
    button: tk.Label,
    *,
    text: str,
) -> None:
    palette = _mmcp_button_palette(text)
    button.configure(
        text=text,
        bg=palette.background,
        fg=palette.foreground,
        activebackground=palette.active_background,
        activeforeground=palette.foreground,
        bd=1,
        relief="solid",
        highlightthickness=1,
        highlightbackground=palette.border,
        highlightcolor=WEB_DIAMOND,
        padx=11,
        pady=7,
        font=(
            "Helvetica",
            base.INFO_BUTTON_FONT_SIZE,
            "bold",
        ),
    )


def _apply_web_palette_to_base() -> None:
    base.BACKGROUND_COLOR = WEB_BG
    base.TEXT_COLOR = WEB_INK
    base.INFO_BOX_BACKGROUND = WEB_PANEL
    base.INFO_BOX_BORDER = WEB_BORDER_LIGHT
    base.INFO_BUTTON_BACKGROUND = WEB_PANEL_RAISED
    base.INFO_BUTTON_ACTIVE_BACKGROUND = WEB_PANEL_HOVER
    base.INFO_CHECKBOX_TEXT_COLOR = WEB_MUTED
    base.SIDEBAR_INPUT_BACKGROUND = WEB_FIELD
    base.SIDEBAR_INPUT_ACTIVE_BACKGROUND = WEB_FIELD_ACTIVE
    base.SIDEBAR_INPUT_BORDER = WEB_BORDER_LIGHT
    base.CURSOR_INFO_BACKGROUND = WEB_PANEL
    base.CURSOR_INFO_BORDER = WEB_BORDER_LIGHT
    base.ROUTE_HIGHLIGHT_OUTLINE = WEB_INK


def _style_sidebar_text_panel(widget: object) -> None:
    if not isinstance(widget, tk.Text):
        return
    widget.configure(
        bg=WEB_PANEL_RAISED,
        fg=WEB_INK,
        insertbackground=WEB_DIAMOND,
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground=WEB_BORDER_LIGHT,
        highlightcolor=WEB_DIAMOND,
        wrap="word",
        padx=10,
        pady=8,
        font=("Helvetica", base.SIDEBAR_TEXT_FONT_SIZE),
    )


def _apply_web_sidebar_shell_style(
    self: "base.MetroMapViewer",
) -> None:
    root = getattr(self, "root", None)
    if isinstance(root, tk.Misc):
        root.configure(bg=WEB_BG)
    sidebar_container = getattr(
        self,
        "sidebar_container",
        None,
    )
    if isinstance(sidebar_container, tk.Misc):
        sidebar_container.configure(
            bg=WEB_PANEL,
            highlightbackground=WEB_BORDER_LIGHT,
            highlightthickness=1,
            bd=0,
        )
    sidebar_canvas = getattr(
        self,
        "sidebar_canvas",
        None,
    )
    if isinstance(sidebar_canvas, tk.Canvas):
        sidebar_canvas.configure(
            bg=WEB_PANEL,
            highlightthickness=0,
            bd=0,
        )
    sidebar = getattr(self, "sidebar", None)
    if isinstance(sidebar, tk.Misc):
        sidebar.configure(bg=WEB_PANEL)

    _style_sidebar_text_panel(
        getattr(self, "route_steps_text", None)
    )
    _style_sidebar_text_panel(
        getattr(self, "world_map_status_text", None)
    )


def _style_dialog_widget_tree(widget: object) -> None:
    if not isinstance(widget, tk.Misc):
        return

    if isinstance(widget, tk.Toplevel):
        widget.configure(bg=WEB_BG)
    elif isinstance(widget, tk.Frame):
        widget.configure(bg=WEB_PANEL)
    elif isinstance(widget, tk.Label):
        text = str(widget.cget("text") or "")
        is_heading = bool(
            text
            and (
                text.isupper()
                or len(text.split()) <= 3
                and any(char.isalpha() for char in text)
            )
        )
        widget.configure(
            bg=WEB_PANEL,
            fg=WEB_INK if is_heading else WEB_MUTED,
            font=(
                MMCP_MONO_FONT if is_heading else "Helvetica",
                base.SIDEBAR_TEXT_FONT_SIZE if is_heading else max(10, base.SIDEBAR_TEXT_FONT_SIZE - 1),
                "bold" if is_heading else "normal",
            ),
        )
    elif isinstance(widget, tk.Entry):
        widget.configure(
            bg=WEB_FIELD,
            fg=WEB_INK,
            insertbackground=WEB_DIAMOND,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=WEB_BORDER_LIGHT,
            highlightcolor=WEB_DIAMOND,
        )
    elif isinstance(widget, tk.Text):
        widget.configure(
            bg=WEB_PANEL_RAISED,
            fg=WEB_INK,
            insertbackground=WEB_DIAMOND,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=WEB_BORDER_LIGHT,
            highlightcolor=WEB_DIAMOND,
            padx=10,
            pady=8,
        )
    elif isinstance(widget, tk.Listbox):
        widget.configure(
            bg=WEB_FIELD,
            fg=WEB_INK,
            selectbackground=WEB_PANEL_HOVER,
            selectforeground=WEB_INK,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=WEB_BORDER_LIGHT,
            highlightcolor=WEB_DIAMOND,
        )
    elif isinstance(widget, tk.Menubutton):
        widget.configure(
            bg=WEB_FIELD,
            fg=WEB_INK,
            activebackground=WEB_FIELD_ACTIVE,
            activeforeground=WEB_INK,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=WEB_BORDER_LIGHT,
            highlightcolor=WEB_DIAMOND,
        )
    elif isinstance(widget, tk.OptionMenu):
        widget.configure(
            bg=WEB_FIELD,
            fg=WEB_INK,
            activebackground=WEB_FIELD_ACTIVE,
            activeforeground=WEB_INK,
            highlightthickness=1,
            highlightbackground=WEB_BORDER_LIGHT,
            highlightcolor=WEB_DIAMOND,
            relief="solid",
            bd=1,
        )
        try:
            menu = widget.nametowidget(str(widget.cget("menu")))
            menu.configure(
                bg=WEB_FIELD_ACTIVE,
                fg=WEB_INK,
                activebackground=WEB_PANEL_HOVER,
                activeforeground=WEB_INK,
                bd=0,
                tearoff=False,
            )
        except tk.TclError:
            pass
    elif isinstance(widget, tk.Scrollbar):
        widget.configure(
            bg=WEB_PANEL_RAISED,
            activebackground=WEB_PANEL_HOVER,
            troughcolor=WEB_PANEL_INSET,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
    elif isinstance(widget, tk.Radiobutton):
        widget.configure(
            bg=WEB_PANEL,
            fg=WEB_INK,
            activebackground=WEB_PANEL,
            activeforeground=WEB_INK,
            selectcolor=WEB_PANEL_RAISED,
            highlightthickness=0,
            bd=0,
        )

    for child in widget.winfo_children():
        _style_dialog_widget_tree(child)


def _style_dialog_after_build(dialog: object) -> None:
    _style_dialog_widget_tree(dialog)


def _patched_center_dialog(
    dialog: tk.Toplevel,
    root: tk.Tk,
) -> None:
    assert _ORIGINAL_CENTER_DIALOG is not None
    _style_dialog_after_build(dialog)
    dialog.update_idletasks()
    title_width = max(260, (len(dialog.title()) * 10) + 88)
    width = max(1, dialog.winfo_reqwidth() + 36, title_width)
    height = max(1, dialog.winfo_reqheight() + 18)
    screen_width = max(1, root.winfo_screenwidth())
    screen_height = max(1, root.winfo_screenheight())
    left = max(0, round((screen_width - width) / 2))
    top = max(0, round((screen_height - height) / 2))
    dialog.geometry(f"{width}x{height}+{left}+{top}")


def _patched_center_toplevel(
    self: "base.MetroMapViewer",
    window: tk.Toplevel,
    *,
    width: int,
    height: int,
) -> None:
    assert _ORIGINAL_CENTER_TOPLEVEL is not None
    _style_dialog_after_build(window)
    self.root.update_idletasks()
    window.update_idletasks()
    title_width = max(280, (len(window.title()) * 10) + 96)
    fitted_width = min(
        width,
        max(window.winfo_reqwidth() + 36, title_width),
    )
    fitted_height = min(
        height,
        max(window.winfo_reqheight() + 18, 196),
    )
    screen_width = max(1, self.root.winfo_screenwidth())
    screen_height = max(1, self.root.winfo_screenheight())
    x = max(0, (screen_width - fitted_width) // 2)
    y = max(0, (screen_height - fitted_height) // 2)
    window.geometry(f"{fitted_width}x{fitted_height}+{x}+{y}")


def _styled_make_collapsible_sidebar_section(
    self: "base.MetroMapViewer",
    title: str,
    *,
    expanded: bool,
) -> tk.Frame:
    card = tk.Frame(
        self.sidebar,
        bg=MMCP_BORDER_DIM,
        highlightbackground=WEB_BORDER_LIGHT,
        highlightthickness=1,
        bd=0,
    )
    card.pack(fill="x", padx=14, pady=(12, 0))
    header = tk.Label(
        card,
        text=(
            f"[-] {title}"
            if expanded
            else f"[+] {title}"
        ),
        bg=WEB_PANEL_RAISED,
        fg=WEB_INK,
        font=(
            MMCP_MONO_FONT,
            15,
            "bold",
        ),
        anchor="w",
        cursor="hand2",
        padx=12,
        pady=10,
    )
    header.pack(fill="x")
    body = tk.Frame(
        card,
        bg=WEB_PANEL_INSET,
        highlightthickness=0,
        bd=0,
    )
    is_expanded = expanded

    def sync_state() -> None:
        header.configure(
            text=(
                f"[-] {title}"
                if is_expanded
                else f"[+] {title}"
            )
        )
        if is_expanded:
            if not body.winfo_manager():
                body.pack(fill="x", padx=1, pady=(0, 1))
        else:
            if body.winfo_manager():
                body.pack_forget()

    toggle_box = tk.Label(
        header,
        text="+",
        bg=WEB_PANEL_INSET,
        fg=WEB_DIAMOND,
        font=(MMCP_MONO_FONT, 13, "bold"),
        width=2,
        bd=1,
        relief="solid",
        highlightthickness=0,
        highlightbackground=WEB_BORDER_LIGHT,
    )
    toggle_box.place(relx=1.0, x=-12, rely=0.5, anchor="e")

    def sync_toggle_box() -> None:
        toggle_box.configure(text="-" if is_expanded else "+")

    def set_expanded(expanded_state: bool) -> None:
        nonlocal is_expanded
        is_expanded = expanded_state
        sync_state()
        sync_toggle_box()

    def toggle_with_box() -> None:
        set_expanded(not is_expanded)

    header.bind("<Button-1>", lambda _event: toggle_with_box())
    setattr(body, "_desktop_set_expanded", set_expanded)
    setattr(body, "_desktop_section_title", title)
    set_expanded(is_expanded)
    return body


def _styled_make_sidebar_caption(
    self: "base.MetroMapViewer",
    text: str,
    *,
    parent: tk.Misc | None = None,
) -> tk.Label:
    return tk.Label(
        parent or self.sidebar,
        text=text.upper(),
        bg=WEB_PANEL_INSET,
        fg=WEB_INK,
        font=(
            MMCP_MONO_FONT,
            12,
            "bold",
        ),
        anchor="w",
        justify="left",
    )


def _styled_make_sidebar_hint(
    self: "base.MetroMapViewer",
    text: str,
    *,
    parent: tk.Misc | None = None,
) -> tk.Label:
    return tk.Label(
        parent or self.sidebar,
        text=text,
        bg=WEB_PANEL_INSET,
        fg=WEB_MUTED,
        font=(
            "Helvetica",
            11,
        ),
        anchor="w",
        justify="left",
        wraplength=base.SIDEBAR_WIDTH - 56,
    )


def _styled_make_sidebar_entry(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
    variable: tk.StringVar,
) -> tk.Entry:
    return tk.Entry(
        parent,
        textvariable=variable,
        bg=WEB_FIELD,
        fg=WEB_INK,
        insertbackground=WEB_DIAMOND,
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground=WEB_BORDER_LIGHT,
        highlightcolor=WEB_DIAMOND,
        font=("Helvetica", base.SIDEBAR_TEXT_FONT_SIZE),
    )


def _styled_make_sidebar_option_menu(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
    variable: tk.StringVar,
) -> tk.Menubutton:
    option_menu = tk.Menubutton(
        parent,
        textvariable=variable,
        bg=WEB_FIELD,
        fg=WEB_INK,
        activebackground=WEB_FIELD_ACTIVE,
        activeforeground=WEB_INK,
        highlightthickness=1,
        highlightbackground=WEB_BORDER_LIGHT,
        highlightcolor=WEB_DIAMOND,
        bd=1,
        relief="solid",
        font=("Helvetica", base.SIDEBAR_TEXT_FONT_SIZE),
        anchor="w",
        direction="below",
        padx=12,
        pady=8,
        cursor="hand2",
    )
    menu = tk.Menu(
        option_menu,
        bg=WEB_FIELD_ACTIVE,
        fg=WEB_INK,
        activebackground=WEB_PANEL_HOVER,
        activeforeground=WEB_INK,
        font=("Helvetica", base.SIDEBAR_TEXT_FONT_SIZE),
        bd=0,
        tearoff=False,
    )
    option_menu.configure(menu=menu)
    return option_menu


def _styled_make_sidebar_button(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
    *,
    text: str,
    command: Callable[[], None],
) -> tk.Label:
    button = tk.Label(
        parent,
        cursor="hand2",
    )
    _style_mmcp_button(
        button,
        text=text,
    )
    palette = _mmcp_button_palette(text)
    button.bind(
        "<Enter>",
        lambda _event: button.configure(
            bg=palette.active_background
        ),
    )
    button.bind(
        "<Leave>",
        lambda _event: button.configure(
            bg=palette.background
        ),
    )
    button.bind("<Button-1>", lambda _event: command())
    return button


def _styled_configure_sidebar_button(
    self: "base.MetroMapViewer",
    button: tk.Label,
    *,
    text: str,
    command: Callable[[], None],
) -> None:
    _style_mmcp_button(
        button,
        text=text,
    )
    palette = _mmcp_button_palette(text)
    button.configure(cursor="hand2")
    button.unbind("<Enter>")
    button.unbind("<Leave>")
    button.unbind("<Button-1>")
    button.bind(
        "<Enter>",
        lambda _event: button.configure(
            bg=palette.active_background
        ),
    )
    button.bind(
        "<Leave>",
        lambda _event: button.configure(
            bg=palette.background
        ),
    )
    button.bind("<Button-1>", lambda _event: command())


def _styled_make_sidebar_checkbox(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
    *,
    text: str,
    variable: tk.BooleanVar,
    command: Callable[[], None],
) -> tk.Checkbutton:
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        command=command,
        bg=WEB_PANEL_INSET,
        fg=WEB_INK,
        activebackground=WEB_PANEL_INSET,
        activeforeground=WEB_INK,
        selectcolor=WEB_PANEL_RAISED,
        highlightthickness=0,
        bd=0,
        font=("Helvetica", base.SIDEBAR_TEXT_FONT_SIZE),
        anchor="w",
        justify="left",
    )


def _styled_make_info_button(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
    *,
    text: str,
    command: Callable[[], None],
) -> tk.Label:
    button = tk.Label(
        parent,
        cursor="hand2",
    )
    _style_mmcp_button(
        button,
        text=text,
    )
    palette = _mmcp_button_palette(text)
    self._bind_info_clickable(
        button,
        command=command,
        normal_background=palette.background,
        active_background=palette.active_background,
        normal_foreground=palette.foreground,
        active_foreground=palette.foreground,
    )
    return button


def _desktop_mode_by_key(key: str | None) -> DesktopMode:
    for mode in DESKTOP_MODES:
        if mode.key == key:
            return mode
    return DESKTOP_MODES[0]


def _desktop_mode_by_label(label: str | None) -> DesktopMode:
    normalized = str(label or "").strip().casefold()
    for mode in DESKTOP_MODES:
        if mode.label.casefold() == normalized:
            return mode
    return DESKTOP_MODES[0]


def _desktop_mode_labels() -> list[str]:
    return [mode.label for mode in DESKTOP_MODES]


def _ensure_desktop_mode_state(
    self: "base.MetroMapViewer",
) -> None:
    if not hasattr(self, "desktop_mode_var"):
        self.desktop_mode_var = tk.StringVar(
            master=self.root,
            value=_desktop_mode_by_key(
                DESKTOP_MODE_DEFAULT_KEY,
            ).label,
        )
    if not hasattr(self, "desktop_mode_status_var"):
        self.desktop_mode_status_var = tk.StringVar(
            master=self.root,
            value=_desktop_mode_by_label(
                self.desktop_mode_var.get(),
            ).description,
        )
    self.desktop_mode_key = _desktop_mode_by_label(
        self.desktop_mode_var.get(),
    ).key


def _set_desktop_mode_label(
    self: "base.MetroMapViewer",
    label: str,
) -> None:
    mode = _desktop_mode_by_label(label)
    self.desktop_mode_key = mode.key
    self.desktop_mode_var.set(mode.label)
    self.desktop_mode_status_var.set(mode.description)
    _apply_desktop_mode_visibility(self)


def _restore_packed_widget(
    record: PackedWidgetRecord,
) -> None:
    if record.widget.winfo_manager():
        return

    options = dict(record.pack_options)
    next_sibling = record.next_sibling
    try:
        if (
            next_sibling is not None
            and next_sibling.winfo_manager()
        ):
            record.widget.pack(
                before=next_sibling,
                **options,
            )
        else:
            record.widget.pack(**options)
    except tk.TclError:
        record.widget.pack(**options)


def _restore_packed_section(
    record: PackedSectionRecord,
) -> None:
    _restore_packed_widget(
        PackedWidgetRecord(
            widget=record.widget,
            pack_options=record.pack_options,
            next_sibling=record.next_sibling,
        )
    )


def _set_section_record_expanded(
    record: PackedSectionRecord,
    expanded: bool,
) -> None:
    body_widget = record.body_widget
    if body_widget is None:
        return
    set_expanded = getattr(
        body_widget,
        "_desktop_set_expanded",
        None,
    )
    if callable(set_expanded):
        set_expanded(expanded)


def _apply_desktop_mode_visibility(
    self: "base.MetroMapViewer",
) -> None:
    records = getattr(
        self,
        "_desktop_section_records",
        [],
    )
    if not records:
        return

    visible_titles = set(
        MODE_SECTION_TITLES.get(
            getattr(self, "desktop_mode_key", DESKTOP_MODE_DEFAULT_KEY),
            MODE_SECTION_TITLES[DESKTOP_MODE_DEFAULT_KEY],
        )
    )
    expanded_titles = set(
        MODE_SECTION_DEFAULT_EXPANDED.get(
            getattr(self, "desktop_mode_key", DESKTOP_MODE_DEFAULT_KEY),
            (),
        )
    )
    for record in records:
        if record.title in visible_titles:
            _restore_packed_section(record)
            _set_section_record_expanded(
                record,
                record.title in expanded_titles,
            )
        else:
            record.widget.pack_forget()

    sidebar_canvas = getattr(self, "sidebar_canvas", None)
    if isinstance(sidebar_canvas, tk.Canvas):
        sidebar_canvas.configure(
            scrollregion=sidebar_canvas.bbox("all")
        )
    _sync_desktop_workspace_shell(self)


def _append_desktop_mode_shell(
    self: "base.MetroMapViewer",
) -> None:
    _ensure_desktop_mode_state(self)
    workspace.install_mode_rail(
        self,
        modes=DESKTOP_MODES,
        on_mode_select=lambda selected: _set_desktop_mode_label(
            self,
            selected,
        ),
    )
    _sync_desktop_workspace_shell(self)


def _sync_desktop_workspace_shell(
    self: "base.MetroMapViewer",
) -> None:
    workspace.sync_workspace(
        self,
        modes=DESKTOP_MODES,
        active_mode_key=getattr(
            self,
            "desktop_mode_key",
            DESKTOP_MODE_DEFAULT_KEY,
        ),
    )


def _desktop_initial_section_expanded(
    _title: str,
    _requested_expanded: bool,
) -> bool:
    return False


def _route_plot_points(
    viewer: "base.MetroMapViewer",
) -> list[tuple[float, float]]:
    route = getattr(viewer, "current_route", None)
    if route is None:
        return []

    points: list[tuple[float, float]] = []
    route_request = getattr(viewer, "route_request", None)
    if route_request is not None:
        for endpoint_key in route_request:
            endpoint = base._path_endpoint_from_key(endpoint_key)
            if endpoint is not None:
                points.append(endpoint.plot_coordinates)

    for step in route.steps:
        points.extend(
            (float(point[0]), float(point[1]))
            for point in step.path_points
        )
    return points


def _route_fit_bounds_for_points(
    points: list[tuple[float, float]],
) -> tuple[float, float, float, float] | None:
    bounds = base._plot_bounds(points)
    if bounds is None:
        return None

    min_x, max_x, min_y, max_y = bounds
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    half_width = max(
        max_x - min_x,
        ROUTE_FIT_MIN_SPAN,
    ) / 2
    half_height = max(
        max_y - min_y,
        ROUTE_FIT_MIN_SPAN,
    ) / 2
    return (
        center_x - half_width,
        center_x + half_width,
        center_y - half_height,
        center_y + half_height,
    )


def _fit_current_route_view(
    self: "base.MetroMapViewer",
    *,
    show_message: bool = False,
) -> bool:
    points = _route_plot_points(self)
    bounds = _route_fit_bounds_for_points(points)
    if bounds is None:
        if show_message:
            messagebox.showinfo(
                "Fit Route",
                "Calculate a route before fitting the route view.",
                parent=self.root,
            )
        return False

    min_x, max_x, min_y, max_y = bounds
    self._set_view_to_plot_bounds(
        min_x,
        max_x,
        min_y,
        max_y,
        min_zoom=self._minimum_zoom(),
        margin_pixels=ROUTE_FIT_MARGIN_PIXELS,
    )
    return True


def _cancel_pending_route_fit(
    self: "base.MetroMapViewer",
) -> None:
    after_id = getattr(
        self,
        "_desktop_route_fit_after_id",
        None,
    )
    if after_id is None:
        return
    try:
        self.root.after_cancel(after_id)
    except tk.TclError:
        pass
    self._desktop_route_fit_after_id = None


def _schedule_route_fit(
    self: "base.MetroMapViewer",
) -> None:
    _cancel_pending_route_fit(self)
    expected_request = getattr(self, "route_request", None)

    def fit_after_redraw() -> None:
        self._desktop_route_fit_after_id = None
        if getattr(self, "route_request", None) != expected_request:
            return
        if getattr(self, "current_route", None) is None:
            return
        _fit_current_route_view(self)

    self._desktop_route_fit_after_id = self.root.after_idle(
        fit_after_redraw
    )


def _schedule_route_fit_if_ready(
    self: "base.MetroMapViewer",
) -> None:
    if getattr(self, "current_route", None) is None:
        _cancel_pending_route_fit(self)
        return
    if not _route_plot_points(self):
        _cancel_pending_route_fit(self)
        return
    _schedule_route_fit(self)


def _patched_refresh_current_route(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_REFRESH_CURRENT_ROUTE is not None
    _ORIGINAL_REFRESH_CURRENT_ROUTE(self)
    _sync_desktop_workspace_shell(self)


def _patched_plan_route(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_PLAN_ROUTE is not None
    _cancel_pending_route_fit(self)
    _ORIGINAL_PLAN_ROUTE(self)
    _sync_desktop_workspace_shell(self)
    _schedule_route_fit_if_ready(self)


def _patched_on_route_options_changed(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_ON_ROUTE_OPTIONS_CHANGED is not None
    _cancel_pending_route_fit(self)
    _ORIGINAL_ON_ROUTE_OPTIONS_CHANGED(self)
    _sync_desktop_workspace_shell(self)
    _schedule_route_fit_if_ready(self)


def _append_fit_route_controls(
    self: "base.MetroMapViewer",
    directions_section: tk.Misc | None,
) -> None:
    if directions_section is None:
        return

    fit_row = tk.Frame(
        directions_section,
        bg=MMCP_SURFACE,
    )
    fit_row.pack(fill="x", padx=16, pady=(0, 12))
    self.desktop_fit_route_button = (
        self._make_sidebar_button(
            fit_row,
            text="Fit Route",
            command=lambda: _fit_current_route_view(
                self,
                show_message=True,
            ),
        )
    )
    self.desktop_fit_route_button.pack(side="left")
    self._make_sidebar_hint(
        (
            "Recenter the calculated route after manually "
            "panning or zooming."
        ),
        parent=fit_row,
    ).pack(side="left", padx=(10, 0))


def _priority_entries_named_or_frontier(
    entries: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    filtered_entries: list[tuple[str, str]] = []
    for stop_var, text in entries:
        stop = base.STOPS_BY_VAR.get(stop_var)
        if stop is None:
            continue
        next_on_line = (
            "next frontier build on Line" in text
            or ": next on Line " in text
        )
        if base._priority_stop_is_named_or_frontier(
            stop,
            next_on_line=next_on_line,
        ):
            filtered_entries.append((stop_var, text))
    return filtered_entries


def _descendant_texts(widget: tk.Misc) -> list[str]:
    texts: list[str] = []
    try:
        text = str(widget.cget("text")).strip()
    except (tk.TclError, TypeError):
        text = ""
    if text:
        texts.append(text)

    for child in widget.winfo_children():
        texts.extend(_descendant_texts(child))
    return texts


def _hide_widget_when_worldgen_complete(
    texts: list[str],
    *,
    is_frame: bool,
) -> bool:
    combined = "\n".join(texts)
    return (
        "Auto Fill keeps advancing" in combined
        or "Start Auto Fill" in combined
        or "Circle internal voids" in combined
        or (
            is_frame
            and any(text == "Mode" for text in texts)
        )
    )


def _capture_generation_widgets(
    self: "base.MetroMapViewer",
    world_map_section: tk.Misc | None,
) -> None:
    if world_map_section is None:
        return

    children = list(world_map_section.winfo_children())
    target_widgets: list[tk.Widget] = []
    for child in children:
        texts = _descendant_texts(child)
        if _hide_widget_when_worldgen_complete(
            texts,
            is_frame=isinstance(child, tk.Frame),
        ):
            target_widgets.append(child)

    records: list[PackedWidgetRecord] = []
    for widget in target_widgets:
        try:
            pack_info = dict(widget.pack_info())
        except tk.TclError:
            continue
        pack_info.pop("in", None)
        pack_info.pop("before", None)
        pack_info.pop("after", None)
        index = children.index(widget)
        next_sibling = (
            children[index + 1]
            if index + 1 < len(children)
            else None
        )
        records.append(
            PackedWidgetRecord(
                widget=widget,
                pack_options=pack_info,
                next_sibling=next_sibling,
            )
        )

    self._worldgen_generation_widget_records = records
    self._worldgen_generation_controls_hidden = False
    self._worldgen_completion_banner = tk.Label(
        world_map_section,
        text=(
            "Map generation complete.\n"
            "Generation controls are hidden until "
            "completion becomes uncertain."
        ),
        bg=WEB_PANEL_RAISED,
        fg=WORLDGEN_COMPLETE_COLOR,
        font=(
            MMCP_MONO_FONT,
            base.SIDEBAR_TEXT_FONT_SIZE,
            "bold",
        ),
        anchor="w",
        justify="left",
        padx=12,
        pady=10,
        wraplength=base.SIDEBAR_WIDTH - 56,
        highlightbackground=WEB_EMERALD,
        highlightthickness=1,
    )
    self.root.after_idle(
        lambda: _refresh_worldgen_control_visibility(self)
    )


def _configured_target_render_bounds() -> (
    tuple[int, int, int, int] | None
):
    try:
        from worldgen.config import (
            default_config_path,
            load_config,
        )

        render = load_config(default_config_path()).render
    except Exception:
        return None

    return (
        int(render.min_x),
        int(render.max_x),
        int(render.min_z),
        int(render.max_z),
    )


def _payload_render_bounds(
    payload: dict[str, object],
) -> tuple[int, int, int, int] | None:
    try:
        return (
            base._render_cache_int(payload, "min_x"),
            base._render_cache_int(payload, "max_x"),
            base._render_cache_int(payload, "min_z"),
            base._render_cache_int(payload, "max_z"),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _worldgen_completion_payload_is_verified(
    payload: dict[str, object],
    target_bounds: tuple[int, int, int, int] | None,
) -> bool:
    colored_pixels = payload.get("colored_pixels")
    total_pixels = payload.get("total_pixels")
    if (
        not isinstance(colored_pixels, int)
        or not isinstance(total_pixels, int)
        or total_pixels <= 0
        or colored_pixels != total_pixels
    ):
        return False

    unfinished_point_count = payload.get(
        "unfinished_point_count"
    )
    if not isinstance(unfinished_point_count, int):
        return False
    if unfinished_point_count != 0:
        return False

    payload_bounds = _payload_render_bounds(payload)
    if target_bounds is None or payload_bounds is None:
        return False
    return target_bounds == payload_bounds


def _worldgen_completion_is_verified(
    viewer: "base.MetroMapViewer",
) -> bool:
    render_underlay = (
        viewer._current_world_map_render_underlay()
    )
    if render_underlay is None:
        return False
    payload, _image = render_underlay

    return _worldgen_completion_payload_is_verified(
        payload,
        _configured_target_render_bounds(),
    )


def _refresh_worldgen_control_visibility(
    self: "base.MetroMapViewer",
) -> None:
    records = getattr(
        self,
        "_worldgen_generation_widget_records",
        [],
    )
    banner = getattr(
        self,
        "_worldgen_completion_banner",
        None,
    )
    if not records or banner is None:
        return

    complete = _worldgen_completion_is_verified(self)
    currently_hidden = bool(
        getattr(
            self,
            "_worldgen_generation_controls_hidden",
            False,
        )
    )

    if complete and not currently_hidden:
        for record in records:
            record.widget.pack_forget()

        status_widget = getattr(
            self,
            "world_map_status_text",
            None,
        )
        if (
            isinstance(status_widget, tk.Widget)
            and status_widget.winfo_manager()
        ):
            banner.pack(
                before=status_widget,
                fill="x",
                padx=16,
                pady=(0, 8),
            )
        else:
            banner.pack(
                fill="x",
                padx=16,
                pady=(0, 8),
            )

        self._worldgen_generation_controls_hidden = True
        self.sidebar_canvas.configure(
            scrollregion=self.sidebar_canvas.bbox("all")
        )
        return

    if not complete and currently_hidden:
        banner.pack_forget()
        for record in reversed(records):
            _restore_packed_widget(record)
        self._worldgen_generation_controls_hidden = False
        self.sidebar_canvas.configure(
            scrollregion=self.sidebar_canvas.bbox("all")
        )


def _patched_set_world_map_status_text(
    self: "base.MetroMapViewer",
    text: str,
) -> None:
    assert _ORIGINAL_SET_WORLD_MAP_STATUS_TEXT is not None
    _ORIGINAL_SET_WORLD_MAP_STATUS_TEXT(self, text)
    _sync_desktop_workspace_shell(self)
    if hasattr(self, "root"):
        self.root.after_idle(
            lambda: _refresh_worldgen_control_visibility(
                self
            )
        )


def _patched_refresh_priority_list(
    self: "base.MetroMapViewer",
) -> None:
    origin_key = self._priority_origin_key()
    origin_label = base._display_label_for_endpoint_key(origin_key)
    self.priority_summary_var.set(
        f"From {origin_label}. Click a station below."
    )
    entries = base._priority_list_entries(
        origin_key,
        **self._route_graph_options(),
    )
    entries = _priority_entries_named_or_frontier(entries)
    base._write_priority_list_csv(entries)
    self._refresh_priority_filter_menu(entries)
    self._refresh_priority_line_filter_menu()
    self._populate_priority_list(
        self._priority_filter_entries(entries)
    )


def _draw_selected_stop_info_without_detection_button(
    self: "base.MetroMapViewer",
) -> None:
    if getattr(
        self,
        "_path_detection_hide_selected_popup",
        False,
    ):
        return
    if inspector.has_docked_inspector(self):
        self._clear_info_popup()
        return
    assert _NORMAL_DRAW_SELECTED_STOP_INFO is not None
    _NORMAL_DRAW_SELECTED_STOP_INFO(self)
    _decorate_selected_stop_popup(self)


def _draw_selected_metro_segment_info_without_docked_popup(
    self: "base.MetroMapViewer",
) -> None:
    if inspector.has_docked_inspector(self):
        self._clear_info_popup()
        return
    assert _ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO is not None
    _ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO(self)


def _draw_selected_path_node_info_without_docked_popup(
    self: "base.MetroMapViewer",
) -> None:
    if inspector.has_docked_inspector(self):
        self._clear_info_popup()
        return
    assert _ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO is not None
    _ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO(self)


def _popup_window_item_id(
    self: "base.MetroMapViewer",
    frame: tk.Widget,
) -> int | None:
    canvas = getattr(self, "canvas", None)
    if not isinstance(canvas, tk.Canvas):
        return None
    for item_id in canvas.find_all():
        try:
            window_name = str(canvas.itemcget(item_id, "window"))
        except tk.TclError:
            continue
        if window_name == str(frame):
            return int(item_id)
    return None


def _reposition_info_popup(
    self: "base.MetroMapViewer",
    frame: tk.Widget,
) -> None:
    canvas = getattr(self, "canvas", None)
    if not isinstance(canvas, tk.Canvas):
        return
    item_id = _popup_window_item_id(self, frame)
    if item_id is None:
        return
    frame.update_idletasks()
    margin = getattr(self, "padding", 20) // 2
    box_width = frame.winfo_reqwidth()
    box_height = frame.winfo_reqheight()
    max_width = max(margin, getattr(self, "width", box_width) - margin)
    x0 = min(margin, max_width - box_width)
    x0 = max(margin, x0)
    y0 = max(
        margin,
        getattr(self, "height", box_height) - margin - box_height,
    )
    canvas.coords(item_id, x0, y0)


def _wrap_popup_button_row(
    frame: tk.Misc,
    *,
    columns: int = 3,
) -> None:
    buttons = [
        child
        for child in frame.winfo_children()
        if isinstance(child, tk.Label)
        and str(child.cget("cursor")) == "hand2"
    ]
    if not buttons:
        return
    for child in buttons:
        child.pack_forget()
    for index, child in enumerate(buttons):
        row = index // columns
        column = index % columns
        frame.grid_columnconfigure(column, weight=1)
        child.grid(
            row=row,
            column=column,
            sticky="ew",
            padx=(0, 6 if column < columns - 1 else 0),
            pady=(0, 6),
        )


def _popup_action_section(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
    *,
    title: str,
    actions: list[tuple[str, Callable[[], None]]],
) -> None:
    if not actions:
        return
    row = tk.Frame(parent, bg=WEB_PANEL)
    row.pack(fill="x", padx=base.INFO_BOX_PAD_X, pady=(0, 6))
    tk.Label(
        row,
        text=title,
        bg=WEB_PANEL,
        fg=WEB_MUTED,
        font=(MMCP_MONO_FONT, 11, "bold"),
        width=8,
        anchor="w",
        justify="left",
    ).pack(side="left")
    button_strip = tk.Frame(row, bg=WEB_PANEL)
    button_strip.pack(side="left", fill="x", expand=True)
    for index, (text, command) in enumerate(actions):
        self._make_info_button(
            button_strip,
            text=text,
            command=command,
        ).pack(side="left", padx=(0, 6 if index < len(actions) - 1 else 0))


def _available_selected_stop_line_actions(
    stop_var: str,
    metro_ext: object | None,
) -> tuple[str, ...]:
    current_line_names = tuple(base.STOP_LINE_NAMES.get(stop_var, ()))
    actions: list[str] = []
    if metro_ext is not None and base.LINE_STOP_VARS:
        default_addable_line = getattr(
            metro_ext,
            "_default_addable_line",
            None,
        )
        if callable(default_addable_line) and default_addable_line(stop_var):
            actions.append("Add")
        switchable_target_lines = getattr(
            metro_ext,
            "_switchable_target_lines",
            None,
        )
        if (
            current_line_names
            and callable(switchable_target_lines)
            and switchable_target_lines(stop_var)
        ):
            actions.append("Switch")
    if current_line_names:
        actions.append("Remove")
    return tuple(actions)


def _show_popup_choice_dialog(
    self: "base.MetroMapViewer",
    *,
    title: str,
    message: str,
    choices: list[tuple[str, Callable[[], None]]],
) -> None:
    dialog = tk.Toplevel(self.root)
    dialog.title(title)
    dialog.transient(self.root)
    dialog.resizable(False, False)

    container = tk.Frame(
        dialog,
        bg=WEB_PANEL,
        padx=18,
        pady=16,
    )
    container.pack(fill="both", expand=True)
    tk.Label(
        container,
        text=message,
        bg=WEB_PANEL,
        fg=WEB_INK,
        font=("Helvetica", 12, "bold"),
        anchor="w",
        justify="left",
        wraplength=520,
    ).pack(anchor="w")

    button_row = tk.Frame(container, bg=WEB_PANEL)
    button_row.pack(anchor="w", fill="x", pady=(12, 0))

    def run_choice(callback: Callable[[], None]) -> None:
        try:
            dialog.grab_release()
        except tk.TclError:
            pass
        dialog.destroy()
        callback()

    for index, (label, callback) in enumerate(choices):
        self._make_info_button(
            button_row,
            text=label,
            command=lambda active_callback=callback: run_choice(
                active_callback
            ),
        ).pack(side="left", padx=(0, 6 if index < len(choices) else 0))
    self._make_info_button(
        button_row,
        text="Cancel",
        command=dialog.destroy,
    ).pack(side="left", padx=(6 if choices else 0, 0))

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.update_idletasks()
    base._center_dialog(dialog, self.root)
    dialog.grab_set()
    dialog.focus_force()


def _prompt_remove_selected_stop_from_line(
    self: "base.MetroMapViewer",
    stop_var: str,
) -> None:
    stop = base.STOPS_BY_VAR.get(stop_var)
    if stop is None:
        return
    line_names = tuple(base.STOP_LINE_NAMES.get(stop_var, ()))
    if not line_names:
        messagebox.showinfo(
            "Remove From Line",
            f"{base._display_label(stop.lbl)} is not on a metro line yet.",
            parent=self.root,
        )
        return
    _show_popup_choice_dialog(
        self,
        title="Remove From Line",
        message=(
            f"Remove {base._display_label(stop.lbl)} from which line?"
        ),
        choices=[
            (
                line_name,
                lambda active_line=line_name: self._remove_selected_station_from_line(
                    active_line
                ),
            )
            for line_name in line_names
        ],
    )


def _prompt_selected_stop_line_action(
    self: "base.MetroMapViewer",
    stop_var: str,
) -> None:
    stop = base.STOPS_BY_VAR.get(stop_var)
    if stop is None:
        return
    try:
        import metro_station_extensions as metro_ext
    except Exception:
        metro_ext = None

    action_names = _available_selected_stop_line_actions(
        stop_var,
        metro_ext,
    )
    if not action_names:
        messagebox.showinfo(
            "Lines",
            "There are no line actions available for this station.",
            parent=self.root,
        )
        return

    actions: list[tuple[str, Callable[[], None]]] = []
    if "Add" in action_names and metro_ext is not None:
        actions.append(
            (
                "Add",
                lambda active_stop_var=stop_var: metro_ext._show_add_selected_station_to_line_dialog(
                    self,
                    active_stop_var,
                ),
            )
        )
    if "Remove" in action_names:
        actions.append(
            (
                "Remove",
                lambda active_stop_var=stop_var: _prompt_remove_selected_stop_from_line(
                    self,
                    active_stop_var,
                ),
            )
        )
    if "Switch" in action_names and metro_ext is not None:
        actions.append(
            (
                "Switch",
                lambda active_stop_var=stop_var: metro_ext.show_switch_station_line_dialog(
                    self,
                    active_stop_var,
                ),
            )
        )
    _show_popup_choice_dialog(
        self,
        title="Station Lines",
        message=(
            f"What would you like to do with the lines for "
            f"{base._display_label(stop.lbl)}?"
        ),
        choices=actions,
    )


def _hide_existing_popup_action_rows(
    frame: tk.Misc,
) -> None:
    for child in frame.winfo_children():
        if not isinstance(child, tk.Frame):
            continue
        button_children = [
            grandchild
            for grandchild in child.winfo_children()
            if isinstance(grandchild, tk.Label)
            and str(grandchild.cget("cursor")) == "hand2"
        ]
        if button_children and len(button_children) == len(child.winfo_children()):
            child.pack_forget()


def _append_popup_action_sections(
    self: "base.MetroMapViewer",
    frame: tk.Misc,
    stop: base.MetroStop,
) -> None:
    try:
        import metro_station_extensions as metro_ext
    except Exception:
        metro_ext = None

    existing_sections = getattr(
        self,
        "_desktop_popup_action_sections",
        [],
    )
    for section in existing_sections:
        if isinstance(section, tk.Widget):
            section.destroy()

    _hide_existing_popup_action_rows(frame)

    section_container = tk.Frame(frame, bg=WEB_PANEL)
    section_container.pack(
        anchor="w",
        fill="x",
        padx=0,
        pady=(0, base.INFO_BOX_PAD_Y),
    )

    edit_actions = [
        ("Coordinates", self._edit_selected_coordinates),
        ("Name / Abbr", self._edit_selected_label),
        ("Station Entry", self._edit_selected_station_entry),
    ]
    manage_actions: list[tuple[str, Callable[[], None]]] = [
        ("Alignments", self._manage_selected_alignments),
        (
            "City Limits",
            self._toggle_selected_city_limits_edit,
        ),
    ]
    if _available_selected_stop_line_actions(stop.var, metro_ext):
        manage_actions.append(
            (
                "Lines",
                lambda active_stop_var=stop.var: _prompt_selected_stop_line_action(
                    self,
                    active_stop_var,
                ),
            )
        )
    if self.city_limits_edit_stop_var == stop.var:
        manage_actions.append(
            ("Clear", self._clear_selected_city_limits)
        )

    _popup_action_section(
        self,
        section_container,
        title="Edit",
        actions=edit_actions,
    )
    _popup_action_section(
        self,
        section_container,
        title="Manage",
        actions=manage_actions,
    )
    self._desktop_popup_action_sections = [section_container]


def _make_line_badge(
    parent: tk.Misc,
    *,
    line_name: str,
    line_color: str,
) -> tk.Canvas:
    size = 25
    badge = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=WEB_PANEL,
        highlightthickness=0,
        bd=0,
    )
    badge.create_oval(
        2,
        2,
        size - 2,
        size - 2,
        fill=line_color,
        outline=_line_badge_foreground(line_color),
        width=2,
    )
    badge.create_text(
        size / 2,
        size / 2,
        text=line_name,
        fill=_line_badge_foreground(line_color),
        font=(MMCP_MONO_FONT, 10, "bold"),
    )
    return badge


def _decorate_selected_stop_popup(
    self: "base.MetroMapViewer",
) -> None:
    frame = getattr(self, "info_popup_frame", None)
    stop_var = getattr(self, "selected_stop_var", None)
    if frame is None or stop_var not in base.STOPS_BY_VAR:
        return

    stop = base.STOPS_BY_VAR[stop_var]
    if isinstance(frame, tk.Misc):
        frame.configure(
            bg=WEB_PANEL,
            highlightbackground=WEB_BORDER_LIGHT,
            highlightthickness=1,
            bd=0,
        )
    children = list(frame.winfo_children())
    if not children:
        return
    original_title_label = children[0]
    if isinstance(original_title_label, tk.Label):
        original_title_label.pack_forget()

    existing_header_row = getattr(
        self,
        "_desktop_station_header_row",
        None,
    )
    if isinstance(existing_header_row, tk.Widget):
        existing_header_row.destroy()

    line_names = list(base.STOP_LINE_NAMES.get(stop.var, ()))
    header_row = tk.Frame(
        frame,
        bg=WEB_PANEL,
    )
    self._desktop_station_header_row = header_row
    pack_kwargs: dict[str, object] = {
        "fill": "x",
        "padx": base.INFO_BOX_PAD_X,
        "pady": (base.INFO_BOX_PAD_Y, max(2, base.INFO_BOX_SECTION_GAP // 2)),
    }
    if len(children) >= 2:
        pack_kwargs["before"] = children[1]
    header_row.pack(**pack_kwargs)
    title_row_label = tk.Label(
        header_row,
        text=f"{_station_marker_text(stop.var)} {base._station_display_name(stop)}",
        bg=WEB_PANEL,
        fg=WEB_INK,
        font=(
            "Helvetica",
            base.INFO_TITLE_FONT_SIZE - 2,
            "bold",
        ),
        anchor="w",
        justify="left",
    )
    title_row_label.pack(side="left", anchor="w")

    badge_row = tk.Frame(
        header_row,
        bg=WEB_PANEL,
    )
    badge_row.pack(side="right", anchor="e")
    for line_name in line_names:
        line_color = base.LINE_COLORS.get(
            line_name,
            WEB_PANEL_HOVER,
        )
        _make_line_badge(
            badge_row,
            line_name=line_name,
            line_color=line_color,
        ).pack(side="left", padx=(6, 0))

    _append_popup_action_sections(self, frame, stop)
    _reposition_info_popup(self, frame)


def _run_experimental_path_detection(
    self: "base.MetroMapViewer",
) -> None:
    stop_var = getattr(self, "selected_stop_var", None)
    if stop_var is None or stop_var not in base.STOPS_BY_VAR:
        messagebox.showinfo(
            "Experimental Path Detection",
            "Select a station first.",
            parent=self.root,
        )
        return

    proceed = messagebox.askyesno(
        "Experimental Path Detection",
        (
            "Path detection is an unsupported "
            "experimental tool.\n\n"
            "Existing saved paths and detection state "
            "will be preserved. Continue for the "
            "selected station?"
        ),
        parent=self.root,
    )
    if not proceed:
        return

    path_detection.detect_paths_for_stop(
        self,
        stop_var,
    )


def _append_advanced_section(
    self: "base.MetroMapViewer",
) -> None:
    section = self._make_collapsible_sidebar_section(
        "Advanced / Experimental",
        expanded=False,
    )
    self._make_sidebar_hint(
        (
            "Unsupported or rarely used tools live here. "
            "Path detection is intentionally hidden from "
            "normal station controls."
        ),
        parent=section,
    ).pack(anchor="w", padx=16, pady=(4, 8))
    self._make_sidebar_button(
        section,
        text="Detect Paths for Selected Station",
        command=lambda: _run_experimental_path_detection(
            self
        ),
    ).pack(anchor="w", padx=16, pady=(0, 12))
    return section


def _capture_section_records(
    self: "base.MetroMapViewer",
    captured_sections: dict[str, tk.Misc],
    *,
    advanced_section: tk.Misc | None,
) -> None:
    records: list[PackedSectionRecord] = []
    ordered_pairs = list(captured_sections.items())
    if advanced_section is not None:
        ordered_pairs.append(
            ("Advanced / Experimental", advanced_section)
        )
    for title, section_body in ordered_pairs:
        section_card = getattr(section_body, "master", None)
        if not isinstance(section_card, tk.Widget):
            continue
        try:
            pack_info = dict(section_card.pack_info())
        except tk.TclError:
            continue
        pack_info.pop("in", None)
        pack_info.pop("before", None)
        pack_info.pop("after", None)
        siblings = list(section_card.master.winfo_children())
        index = siblings.index(section_card)
        next_sibling = (
            siblings[index + 1]
            if index + 1 < len(siblings)
            else None
        )
        records.append(
            PackedSectionRecord(
                title=title,
                widget=section_card,
                pack_options=pack_info,
                next_sibling=next_sibling,
                body_widget=section_body,
            )
        )
    self._desktop_section_records = records


def _overlay_web_station_markers(
    self: "base.MetroMapViewer",
) -> None:
    canvas = getattr(self, "canvas", None)
    if not isinstance(canvas, tk.Canvas):
        return
    canvas.delete("desktop_station_marker")
    visible_line_names = self._visible_line_names()
    for stop in base.METRO_STOPS:
        position = self.station_canvas_positions.get(stop.var)
        if position is None:
            continue
        stop_visible_line_names = self._stop_visible_line_names(
            stop,
            visible_line_names,
        )
        if not stop_visible_line_names and base.STOP_LINE_NAMES[stop.var]:
            continue
        canvas_x, canvas_y = position
        radius = _station_marker_radius(stop.var)
        fill = self._stop_fill_for_visible_lines(
            stop_visible_line_names
        )
        selected = getattr(self, "selected_stop_var", None) == stop.var
        if selected:
            canvas.create_polygon(
                _diamond_marker_points(
                    canvas_x,
                    canvas_y,
                    radius + 4,
                ),
                fill="",
                outline=WEB_DIAMOND,
                width=3,
                tags=("desktop_station_marker",),
            )
        canvas.create_polygon(
            _diamond_marker_points(canvas_x, canvas_y, radius),
            fill=fill,
            outline=WEB_BORDER_DARK,
            width=2.5,
            tags=("desktop_station_marker",),
        )
        if len(base.STOP_LINE_NAMES.get(stop.var, ())) >= 2:
            canvas.create_polygon(
                _diamond_marker_points(
                    canvas_x,
                    canvas_y,
                    max(4, radius - 3),
                ),
                fill="",
                outline=WEB_INK,
                width=1.75,
                tags=("desktop_station_marker",),
            )


def _patched_redraw(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_REDRAW is not None
    _ORIGINAL_REDRAW(self)
    _overlay_web_station_markers(self)
    inspector.sync_inspector(self)


def _patched_build_route_panel(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_BUILD_ROUTE_PANEL is not None
    _apply_web_sidebar_shell_style(self)
    _append_desktop_mode_shell(self)

    captured_sections: dict[str, tk.Misc] = {}
    original_make_section = (
        self._make_collapsible_sidebar_section
    )

    def capture_section(
        title: str,
        *,
        expanded: bool,
    ) -> tk.Frame:
        body = original_make_section(
            title,
            expanded=_desktop_initial_section_expanded(
                title,
                expanded,
            ),
        )
        captured_sections[title] = body
        return body

    self._make_collapsible_sidebar_section = capture_section
    try:
        _ORIGINAL_BUILD_ROUTE_PANEL(self)
    finally:
        self._make_collapsible_sidebar_section = (
            original_make_section
        )

    _append_fit_route_controls(
        self,
        captured_sections.get("Directions"),
    )
    _capture_generation_widgets(
        self,
        captured_sections.get("World Map"),
    )
    advanced_section = _append_advanced_section(self)
    _capture_section_records(
        self,
        captured_sections,
        advanced_section=advanced_section,
    )
    _apply_desktop_mode_visibility(self)


def apply() -> None:
    global _APPLIED
    global _ORIGINAL_BUILD_ROUTE_PANEL
    global _ORIGINAL_REFRESH_CURRENT_ROUTE
    global _ORIGINAL_PLAN_ROUTE
    global _ORIGINAL_ON_ROUTE_OPTIONS_CHANGED
    global _ORIGINAL_SET_WORLD_MAP_STATUS_TEXT
    global _ORIGINAL_REFRESH_PRIORITY_LIST
    global _ORIGINAL_REDRAW
    global _ORIGINAL_CENTER_DIALOG
    global _ORIGINAL_CENTER_TOPLEVEL
    global _NORMAL_DRAW_SELECTED_STOP_INFO
    global _ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO
    global _ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO
    global _ORIGINAL_MAKE_COLLAPSIBLE_SIDEBAR_SECTION
    global _ORIGINAL_MAKE_SIDEBAR_CAPTION
    global _ORIGINAL_MAKE_SIDEBAR_HINT
    global _ORIGINAL_MAKE_SIDEBAR_ENTRY
    global _ORIGINAL_MAKE_SIDEBAR_OPTION_MENU
    global _ORIGINAL_MAKE_SIDEBAR_BUTTON
    global _ORIGINAL_CONFIGURE_SIDEBAR_BUTTON
    global _ORIGINAL_MAKE_SIDEBAR_CHECKBOX
    global _ORIGINAL_MAKE_INFO_BUTTON

    _apply_web_palette_to_base()

    if _APPLIED:
        return
    if getattr(base.MetroMapViewer, _APPLIED_ATTR, False):
        workspace.apply()
        _ORIGINAL_BUILD_ROUTE_PANEL = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_BUILD_ROUTE_PANEL"],
            None,
        )
        _ORIGINAL_REFRESH_CURRENT_ROUTE = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_REFRESH_CURRENT_ROUTE"],
            None,
        )
        _ORIGINAL_PLAN_ROUTE = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_PLAN_ROUTE"],
            None,
        )
        _ORIGINAL_ON_ROUTE_OPTIONS_CHANGED = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_ON_ROUTE_OPTIONS_CHANGED"
            ],
            None,
        )
        _ORIGINAL_SET_WORLD_MAP_STATUS_TEXT = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_SET_WORLD_MAP_STATUS_TEXT"],
            None,
        )
        _ORIGINAL_REFRESH_PRIORITY_LIST = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_REFRESH_PRIORITY_LIST"
            ],
            None,
        )
        _ORIGINAL_REDRAW = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_REDRAW"],
            None,
        )
        _ORIGINAL_CENTER_DIALOG = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_CENTER_DIALOG"],
            None,
        )
        _ORIGINAL_CENTER_TOPLEVEL = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_CENTER_TOPLEVEL"],
            None,
        )
        _NORMAL_DRAW_SELECTED_STOP_INFO = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_NORMAL_DRAW_SELECTED_STOP_INFO"],
            None,
        )
        _ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO"
            ],
            None,
        )
        _ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO"
            ],
            None,
        )
        _ORIGINAL_MAKE_COLLAPSIBLE_SIDEBAR_SECTION = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_MAKE_COLLAPSIBLE_SIDEBAR_SECTION"
            ],
            None,
        )
        _ORIGINAL_MAKE_SIDEBAR_CAPTION = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_MAKE_SIDEBAR_CAPTION"],
            None,
        )
        _ORIGINAL_MAKE_SIDEBAR_HINT = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_MAKE_SIDEBAR_HINT"],
            None,
        )
        _ORIGINAL_MAKE_SIDEBAR_ENTRY = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_MAKE_SIDEBAR_ENTRY"],
            None,
        )
        _ORIGINAL_MAKE_SIDEBAR_OPTION_MENU = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_MAKE_SIDEBAR_OPTION_MENU"
            ],
            None,
        )
        _ORIGINAL_MAKE_SIDEBAR_BUTTON = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_MAKE_SIDEBAR_BUTTON"],
            None,
        )
        _ORIGINAL_CONFIGURE_SIDEBAR_BUTTON = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_CONFIGURE_SIDEBAR_BUTTON"
            ],
            None,
        )
        _ORIGINAL_MAKE_SIDEBAR_CHECKBOX = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS[
                "_ORIGINAL_MAKE_SIDEBAR_CHECKBOX"
            ],
            None,
        )
        _ORIGINAL_MAKE_INFO_BUTTON = getattr(
            base.MetroMapViewer,
            _ORIGINAL_ATTRS["_ORIGINAL_MAKE_INFO_BUTTON"],
            None,
        )
        _APPLIED = True
        return

    workspace.apply()

    _ORIGINAL_BUILD_ROUTE_PANEL = (
        base.MetroMapViewer._build_route_panel
    )
    _ORIGINAL_REFRESH_CURRENT_ROUTE = (
        base.MetroMapViewer._refresh_current_route
    )
    _ORIGINAL_PLAN_ROUTE = base.MetroMapViewer._plan_route
    _ORIGINAL_ON_ROUTE_OPTIONS_CHANGED = (
        base.MetroMapViewer._on_route_options_changed
    )
    _ORIGINAL_SET_WORLD_MAP_STATUS_TEXT = (
        base.MetroMapViewer._set_world_map_status_text
    )
    _ORIGINAL_REFRESH_PRIORITY_LIST = (
        base.MetroMapViewer._refresh_priority_list
    )
    _ORIGINAL_REDRAW = base.MetroMapViewer.redraw
    _ORIGINAL_CENTER_DIALOG = base._center_dialog
    _ORIGINAL_CENTER_TOPLEVEL = (
        base.MetroMapViewer._center_toplevel
    )
    _NORMAL_DRAW_SELECTED_STOP_INFO = getattr(
        path_detection,
        "_ORIGINAL_DRAW_SELECTED_STOP_INFO",
        None,
    )
    if _NORMAL_DRAW_SELECTED_STOP_INFO is None:
        _NORMAL_DRAW_SELECTED_STOP_INFO = (
            base.MetroMapViewer._draw_selected_stop_info
        )
    _ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO = (
        base.MetroMapViewer._draw_selected_metro_segment_info
    )
    _ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO = (
        base.MetroMapViewer._draw_selected_path_node_info
    )
    _ORIGINAL_MAKE_COLLAPSIBLE_SIDEBAR_SECTION = (
        base.MetroMapViewer._make_collapsible_sidebar_section
    )
    _ORIGINAL_MAKE_SIDEBAR_CAPTION = (
        base.MetroMapViewer._make_sidebar_caption
    )
    _ORIGINAL_MAKE_SIDEBAR_HINT = (
        base.MetroMapViewer._make_sidebar_hint
    )
    _ORIGINAL_MAKE_SIDEBAR_ENTRY = (
        base.MetroMapViewer._make_sidebar_entry
    )
    _ORIGINAL_MAKE_SIDEBAR_OPTION_MENU = (
        base.MetroMapViewer._make_sidebar_option_menu
    )
    _ORIGINAL_MAKE_SIDEBAR_BUTTON = (
        base.MetroMapViewer._make_sidebar_button
    )
    _ORIGINAL_CONFIGURE_SIDEBAR_BUTTON = (
        base.MetroMapViewer._configure_sidebar_button
    )
    _ORIGINAL_MAKE_SIDEBAR_CHECKBOX = (
        base.MetroMapViewer._make_sidebar_checkbox
    )
    _ORIGINAL_MAKE_INFO_BUTTON = (
        base.MetroMapViewer._make_info_button
    )

    for global_name, attr_name in _ORIGINAL_ATTRS.items():
        setattr(
            base.MetroMapViewer,
            attr_name,
            globals()[global_name],
        )

    base.MetroMapViewer._build_route_panel = (
        _patched_build_route_panel
    )
    base.MetroMapViewer._refresh_current_route = (
        _patched_refresh_current_route
    )
    base.MetroMapViewer._plan_route = _patched_plan_route
    base.MetroMapViewer._on_route_options_changed = (
        _patched_on_route_options_changed
    )
    base.MetroMapViewer._set_world_map_status_text = (
        _patched_set_world_map_status_text
    )
    base.MetroMapViewer._refresh_priority_list = (
        _patched_refresh_priority_list
    )
    base.MetroMapViewer.redraw = _patched_redraw
    base._center_dialog = _patched_center_dialog
    base.MetroMapViewer._center_toplevel = (
        _patched_center_toplevel
    )
    try:
        import metro_station_extensions as metro_ext

        metro_ext._center_dialog = _patched_center_dialog
    except Exception:
        pass
    base.MetroMapViewer._make_collapsible_sidebar_section = (
        _styled_make_collapsible_sidebar_section
    )
    base.MetroMapViewer._make_sidebar_caption = (
        _styled_make_sidebar_caption
    )
    base.MetroMapViewer._make_sidebar_hint = (
        _styled_make_sidebar_hint
    )
    base.MetroMapViewer._make_sidebar_entry = (
        _styled_make_sidebar_entry
    )
    base.MetroMapViewer._make_sidebar_option_menu = (
        _styled_make_sidebar_option_menu
    )
    base.MetroMapViewer._make_sidebar_button = (
        _styled_make_sidebar_button
    )
    base.MetroMapViewer._configure_sidebar_button = (
        _styled_configure_sidebar_button
    )
    base.MetroMapViewer._make_sidebar_checkbox = (
        _styled_make_sidebar_checkbox
    )
    base.MetroMapViewer._make_info_button = (
        _styled_make_info_button
    )
    base.MetroMapViewer._draw_selected_stop_info = (
        _draw_selected_stop_info_without_detection_button
    )
    base.MetroMapViewer._draw_selected_metro_segment_info = (
        _draw_selected_metro_segment_info_without_docked_popup
    )
    base.MetroMapViewer._draw_selected_path_node_info = (
        _draw_selected_path_node_info_without_docked_popup
    )
    base.MetroMapViewer._fit_current_route_view = (
        _fit_current_route_view
    )
    base.MetroMapViewer._refresh_worldgen_control_visibility = (
        _refresh_worldgen_control_visibility
    )
    setattr(base.MetroMapViewer, _APPLIED_ATTR, True)
    _APPLIED = True
