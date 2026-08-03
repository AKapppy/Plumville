from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from typing import Callable, Sequence

import legacy_core as base


APP_BG = "#0b0f12"
APP_BAR_BG = "#111417"
PANEL_BG = "#161b1f"
PANEL_ALT_BG = "#101417"
PANEL_RAISED = "#1a2025"
BORDER = "#3d474f"
TEXT = "#f4f6f2"
MUTED = "#9aa59f"
ACCENT = "#72c9ec"
SUCCESS = "#55b86a"
MODE_RAIL_WIDTH = 86
SECONDARY_WIDTH = 320
INSPECTOR_WIDTH = 360

_APPLIED = False


@dataclass(slots=True)
class WorkspaceShell:
    root_frame: tk.Frame
    app_bar: tk.Frame
    topbar_mode_label: tk.Label
    topbar_status_label: tk.Label
    inspector_toggle_button: tk.Label
    content_frame: tk.Frame
    mode_rail: tk.Frame
    secondary_shell: tk.Frame
    secondary_title_label: tk.Label
    secondary_description_label: tk.Label
    secondary_body: tk.Frame
    map_shell: tk.Frame
    inspector_shell: tk.Frame
    inspector_canvas: tk.Canvas
    inspector_scrollbar: tk.Scrollbar
    inspector_body: tk.Frame
    inspector_body_window_id: int
    inspector_header_label: tk.Label
    inspector_header_button: tk.Label
    status_strip: tk.Frame
    status_label: tk.Label
    mode_buttons: dict[str, tk.Label]


def _mode_key(mode: object) -> str:
    return str(getattr(mode, "key"))


def _mode_label(mode: object) -> str:
    return str(getattr(mode, "label"))


def _mode_description(mode: object) -> str:
    return str(getattr(mode, "description"))


def _style_action_label(
    label: tk.Label,
    *,
    active: bool,
) -> None:
    label.configure(
        bg="#1e2730" if active else PANEL_RAISED,
        fg=ACCENT if active else TEXT,
        highlightbackground=ACCENT if active else BORDER,
        highlightthickness=1,
        bd=0,
    )


def _mode_rail_text(label: str) -> str:
    if label == "Construction":
        return "Const"
    if label == "Advanced":
        return "Adv"
    return label


def _topbar_status_text(viewer: "base.MetroMapViewer") -> str:
    mode_key = str(getattr(viewer, "desktop_mode_key", ""))
    if mode_key == "world":
        status_var = getattr(viewer, "world_map_status_var", None)
        if status_var is not None:
            text = str(status_var.get()).strip()
            if text:
                return text
    return ""


def _status_strip_text(viewer: "base.MetroMapViewer") -> str:
    mode_key = str(getattr(viewer, "desktop_mode_key", ""))
    if mode_key == "directions":
        route_summary_var = getattr(viewer, "route_summary_var", None)
        if route_summary_var is not None:
            summary = str(route_summary_var.get()).strip()
            if summary and summary != "Choose two stations or coordinates.":
                return summary.splitlines()[0]
    if mode_key == "edit":
        path_click_mode_var = getattr(viewer, "path_click_mode_var", None)
        if path_click_mode_var is not None and bool(path_click_mode_var.get()):
            status_var = getattr(viewer, "path_click_status_var", None)
            if status_var is not None:
                text = str(status_var.get()).strip()
                if text:
                    return text
    return ""


def _inspector_empty_state_text() -> str:
    return (
        "Select a station\n"
        "Use the docked inspector for station details and actions."
    )


def _workspace_shell(viewer: "base.MetroMapViewer") -> WorkspaceShell | None:
    shell = getattr(viewer, "_desktop_workspace_shell", None)
    if isinstance(shell, WorkspaceShell):
        return shell
    return None


def _toggle_inspector(viewer: "base.MetroMapViewer") -> None:
    set_inspector_visible(
        viewer,
        not bool(getattr(viewer, "_desktop_inspector_visible", True)),
    )


def _make_topbar_button(
    parent: tk.Misc,
    *,
    text: str,
    command: Callable[[], None],
) -> tk.Label:
    button = tk.Label(
        parent,
        text=text,
        bg=PANEL_RAISED,
        fg=TEXT,
        font=("Helvetica", 11, "bold"),
        padx=10,
        pady=7,
        cursor="hand2",
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
    )
    button.bind("<Button-1>", lambda _event: command())
    button.bind("<Enter>", lambda _event: button.configure(bg="#20272d"))
    button.bind("<Leave>", lambda _event: button.configure(bg=PANEL_RAISED))
    return button


def _configure_workspace_hosts(
    self: "base.MetroMapViewer",
) -> None:
    if _workspace_shell(self) is not None:
        self.workspace_secondary_parent = _workspace_shell(self).secondary_body
        self.workspace_map_parent = _workspace_shell(self).map_shell
        return

    self.root.grid_rowconfigure(0, weight=1)
    self.root.grid_columnconfigure(0, weight=1)
    root_frame = tk.Frame(self.root, bg=APP_BG)
    root_frame.grid(row=0, column=0, sticky="nsew")
    root_frame.grid_rowconfigure(1, weight=1)
    root_frame.grid_columnconfigure(0, weight=1)

    app_bar = tk.Frame(
        root_frame,
        bg=APP_BAR_BG,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
        padx=16,
        pady=10,
    )
    app_bar.grid(row=0, column=0, sticky="ew")
    app_bar.grid_columnconfigure(1, weight=1)
    tk.Label(
        app_bar,
        text="PLUMVILLE METRO",
        bg=APP_BAR_BG,
        fg=TEXT,
        font=("Courier", 16, "bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="w")
    mode_label = tk.Label(
        app_bar,
        text="All",
        bg=APP_BAR_BG,
        fg=ACCENT,
        font=("Helvetica", 12, "bold"),
        anchor="w",
        padx=12,
    )
    mode_label.grid(row=0, column=1, sticky="w")
    status_label = tk.Label(
        app_bar,
        text="Workspace shell active",
        bg=APP_BAR_BG,
        fg=MUTED,
        font=("Helvetica", 11),
        anchor="w",
    )
    status_label.grid(row=0, column=2, sticky="w", padx=(12, 0))
    inspector_toggle_button = _make_topbar_button(
        app_bar,
        text="Hide Inspector",
        command=lambda active_self=self: _toggle_inspector(active_self),
    )
    inspector_toggle_button.grid(row=0, column=3, sticky="e", padx=(12, 0))

    content_frame = tk.Frame(root_frame, bg=APP_BG)
    content_frame.grid(row=1, column=0, sticky="nsew")
    content_frame.grid_rowconfigure(0, weight=1)
    content_frame.grid_columnconfigure(2, weight=1)

    mode_rail = tk.Frame(
        content_frame,
        bg=PANEL_ALT_BG,
        width=MODE_RAIL_WIDTH,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
        padx=8,
        pady=10,
    )
    mode_rail.grid(row=0, column=0, sticky="ns")
    mode_rail.grid_propagate(False)

    secondary_shell = tk.Frame(
        content_frame,
        bg=PANEL_BG,
        width=SECONDARY_WIDTH,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
    )
    secondary_shell.grid(row=0, column=1, sticky="nsw", padx=(8, 10), pady=8)
    secondary_shell.grid_propagate(False)
    secondary_shell.grid_rowconfigure(1, weight=1)
    secondary_shell.grid_columnconfigure(0, weight=1)
    secondary_header = tk.Frame(
        secondary_shell,
        bg=PANEL_BG,
        padx=14,
        pady=12,
    )
    secondary_header.grid(row=0, column=0, sticky="ew")
    secondary_title_label = tk.Label(
        secondary_header,
        text="All",
        bg=PANEL_BG,
        fg=TEXT,
        font=("Helvetica", 16, "bold"),
        anchor="w",
        justify="left",
    )
    secondary_title_label.pack(anchor="w")
    secondary_description_label = tk.Label(
        secondary_header,
        text="Show all major desktop sections at once.",
        bg=PANEL_BG,
        fg=MUTED,
        font=("Helvetica", 10),
        anchor="w",
        justify="left",
        wraplength=SECONDARY_WIDTH - 36,
    )
    secondary_description_label.pack(anchor="w", pady=(4, 0))
    secondary_body = tk.Frame(secondary_shell, bg=PANEL_BG)
    secondary_body.grid(row=1, column=0, sticky="nsew")

    map_shell = tk.Frame(
        content_frame,
        bg=PANEL_ALT_BG,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
    )
    map_shell.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=8)
    map_shell.grid_rowconfigure(0, weight=1)
    map_shell.grid_columnconfigure(0, weight=1)

    inspector_shell = tk.Frame(
        content_frame,
        bg=PANEL_BG,
        width=INSPECTOR_WIDTH,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
    )
    inspector_shell.grid(row=0, column=3, sticky="nse", pady=8)
    inspector_shell.grid_propagate(False)
    inspector_shell.grid_rowconfigure(1, weight=1)
    inspector_shell.grid_columnconfigure(0, weight=1)
    inspector_header = tk.Frame(
        inspector_shell,
        bg=PANEL_BG,
        padx=14,
        pady=12,
    )
    inspector_header.grid(row=0, column=0, sticky="ew")
    inspector_header.grid_columnconfigure(0, weight=1)
    inspector_header_label = tk.Label(
        inspector_header,
        text="Inspector",
        bg=PANEL_BG,
        fg=TEXT,
        font=("Helvetica", 16, "bold"),
        anchor="w",
    )
    inspector_header_label.grid(row=0, column=0, sticky="w")
    inspector_header_button = _make_topbar_button(
        inspector_header,
        text="Hide",
        command=lambda active_self=self: _toggle_inspector(active_self),
    )
    inspector_header_button.grid(row=0, column=1, sticky="e")

    inspector_viewport = tk.Frame(inspector_shell, bg=PANEL_BG)
    inspector_viewport.grid(row=1, column=0, sticky="nsew")
    inspector_viewport.grid_rowconfigure(0, weight=1)
    inspector_viewport.grid_columnconfigure(0, weight=1)
    inspector_canvas = tk.Canvas(
        inspector_viewport,
        bg=PANEL_BG,
        highlightthickness=0,
        bd=0,
    )
    inspector_canvas.grid(row=0, column=0, sticky="nsew")
    inspector_scrollbar = tk.Scrollbar(
        inspector_viewport,
        orient="vertical",
        command=inspector_canvas.yview,
    )
    inspector_scrollbar.grid(row=0, column=1, sticky="ns")
    inspector_canvas.configure(yscrollcommand=inspector_scrollbar.set)
    inspector_body = tk.Frame(
        inspector_canvas,
        bg=PANEL_BG,
        padx=18,
        pady=18,
    )
    inspector_body_window_id = inspector_canvas.create_window(
        (0, 0),
        anchor="nw",
        window=inspector_body,
    )

    def refresh_inspector_scroll_region(_event: object | None = None) -> None:
        try:
            inspector_canvas.configure(scrollregion=inspector_canvas.bbox("all"))
        except tk.TclError:
            return

    def resize_inspector_body(event: object) -> None:
        try:
            inspector_canvas.itemconfigure(
                inspector_body_window_id,
                width=int(getattr(event, "width", INSPECTOR_WIDTH)),
            )
            inspector_canvas.configure(scrollregion=inspector_canvas.bbox("all"))
        except tk.TclError:
            return

    def scroll_inspector(event: object) -> None:
        delta = int(getattr(event, "delta", 0))
        if delta:
            inspector_canvas.yview_scroll(int(-1 * (delta / 120)), "units")

    inspector_body.bind("<Configure>", refresh_inspector_scroll_region)
    inspector_canvas.bind("<Configure>", resize_inspector_body)
    inspector_canvas.bind("<MouseWheel>", scroll_inspector)
    inspector_body.bind("<MouseWheel>", scroll_inspector)
    tk.Label(
        inspector_body,
        text="◆",
        bg=PANEL_BG,
        fg=ACCENT,
        font=("Courier", 36, "bold"),
        anchor="center",
        justify="center",
    ).pack(pady=(18, 10))
    tk.Label(
        inspector_body,
        text=_inspector_empty_state_text(),
        bg=PANEL_BG,
        fg=MUTED,
        font=("Helvetica", 12),
        anchor="center",
        justify="center",
        wraplength=INSPECTOR_WIDTH - 54,
    ).pack()

    status_strip = tk.Frame(
        root_frame,
        bg=APP_BAR_BG,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
        padx=12,
        pady=6,
    )
    status_strip.grid(row=2, column=0, sticky="ew")
    status_label_widget = tk.Label(
        status_strip,
        text="",
        bg=APP_BAR_BG,
        fg=MUTED,
        font=("Helvetica", 10),
        anchor="w",
        justify="left",
    )
    status_label_widget.pack(anchor="w")
    status_strip.grid_remove()

    shell = WorkspaceShell(
        root_frame=root_frame,
        app_bar=app_bar,
        topbar_mode_label=mode_label,
        topbar_status_label=status_label,
        inspector_toggle_button=inspector_toggle_button,
        content_frame=content_frame,
        mode_rail=mode_rail,
        secondary_shell=secondary_shell,
        secondary_title_label=secondary_title_label,
        secondary_description_label=secondary_description_label,
        secondary_body=secondary_body,
        map_shell=map_shell,
        inspector_shell=inspector_shell,
        inspector_canvas=inspector_canvas,
        inspector_scrollbar=inspector_scrollbar,
        inspector_body=inspector_body,
        inspector_body_window_id=inspector_body_window_id,
        inspector_header_label=inspector_header_label,
        inspector_header_button=inspector_header_button,
        status_strip=status_strip,
        status_label=status_label_widget,
        mode_buttons={},
    )
    self._desktop_workspace_shell = shell
    self._desktop_inspector_visible = False
    self._desktop_inspector_task_key = None
    self._desktop_inspector_hidden_task_key = None
    inspector_shell.grid_remove()
    inspector_toggle_button.configure(text="Show Inspector")
    inspector_header_button.configure(text="Show")
    self.workspace_secondary_parent = secondary_body
    self.workspace_map_parent = map_shell


def _finalize_workspace_hosts(
    self: "base.MetroMapViewer",
) -> None:
    shell = _workspace_shell(self)
    if shell is None:
        return
    shell.map_shell.grid_rowconfigure(0, weight=1)
    shell.map_shell.grid_columnconfigure(0, weight=1)


def install_mode_rail(
    viewer: "base.MetroMapViewer",
    *,
    modes: Sequence[object],
    on_mode_select: Callable[[str], None],
) -> None:
    shell = _workspace_shell(viewer)
    if shell is None or shell.mode_buttons:
        return

    for index, mode in enumerate(modes):
        label = tk.Label(
            shell.mode_rail,
            text=_mode_rail_text(_mode_label(mode)),
            bg=PANEL_RAISED,
            fg=TEXT,
            font=("Helvetica", 10, "bold"),
            anchor="center",
            justify="center",
            wraplength=MODE_RAIL_WIDTH - 24,
            padx=8,
            pady=12,
            cursor="hand2",
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        label.pack(fill="x", pady=(0, 8 if index < len(modes) - 1 else 0))
        label.bind(
            "<Button-1>",
            lambda _event, active_label=_mode_label(mode): on_mode_select(
                active_label
            ),
        )
        shell.mode_buttons[_mode_key(mode)] = label


def _current_view_center(
    viewer: "base.MetroMapViewer",
) -> tuple[float, float] | None:
    width = float(getattr(viewer, "width", 0))
    height = float(getattr(viewer, "height", 0))
    canvas_to_world = getattr(viewer, "canvas_to_world", None)
    if width <= 0 or height <= 0 or not callable(canvas_to_world):
        return None

    try:
        world_x, world_z = canvas_to_world((width / 2, height / 2))
    except (TypeError, ValueError):
        return None
    return (float(world_x), -float(world_z))


def _restore_map_after_inspector_layout(
    viewer: "base.MetroMapViewer",
    previous_center: tuple[float, float] | None,
) -> None:
    center_on_world_point = getattr(viewer, "_center_on_world_point", None)
    if previous_center is None or not callable(center_on_world_point):
        redraw = getattr(viewer, "redraw", None)
        if callable(redraw):
            redraw()
        return

    center_on_world_point(previous_center)
    redraw = getattr(viewer, "redraw", None)
    if callable(redraw):
        redraw()


def _schedule_map_refit_after_inspector_toggle(
    viewer: "base.MetroMapViewer",
    previous_center: tuple[float, float] | None,
) -> None:
    root = getattr(viewer, "root", None)
    after_idle = getattr(root, "after_idle", None)
    callback = lambda: _restore_map_after_inspector_layout(
        viewer,
        previous_center,
    )
    if callable(after_idle):
        after_idle(callback)
    else:
        callback()


def set_inspector_visible(
    viewer: "base.MetroMapViewer",
    visible: bool,
    *,
    remember_hidden_task: bool = True,
) -> None:
    shell = _workspace_shell(viewer)
    if shell is None:
        return
    was_visible = bool(getattr(viewer, "_desktop_inspector_visible", True))
    previous_center = None
    if was_visible != visible:
        previous_center = _current_view_center(viewer)

    viewer._desktop_inspector_visible = visible
    if visible:
        viewer._desktop_inspector_hidden_task_key = None
        shell.inspector_shell.grid()
    else:
        if remember_hidden_task:
            viewer._desktop_inspector_hidden_task_key = getattr(
                viewer,
                "_desktop_inspector_task_key",
                None,
            )
        shell.inspector_shell.grid_remove()
    button_text = "Hide Inspector" if visible else "Show Inspector"
    shell.inspector_toggle_button.configure(text=button_text)
    shell.inspector_header_button.configure(
        text="Hide" if visible else "Show"
    )
    if was_visible != visible:
        _schedule_map_refit_after_inspector_toggle(viewer, previous_center)


def show_inspector_for_task(
    viewer: "base.MetroMapViewer",
    task_key: object | None,
) -> None:
    viewer._desktop_inspector_task_key = task_key
    if task_key is None:
        return
    if task_key == getattr(viewer, "_desktop_inspector_hidden_task_key", None):
        return
    if not bool(getattr(viewer, "_desktop_inspector_visible", False)):
        set_inspector_visible(
            viewer,
            True,
            remember_hidden_task=False,
        )


def sync_workspace(
    viewer: "base.MetroMapViewer",
    *,
    modes: Sequence[object],
    active_mode_key: str,
) -> None:
    shell = _workspace_shell(viewer)
    if shell is None:
        return

    active_mode = next(
        (mode for mode in modes if _mode_key(mode) == active_mode_key),
        modes[0],
    )
    shell.topbar_mode_label.configure(text=_mode_label(active_mode))
    shell.topbar_status_label.configure(text=_topbar_status_text(viewer))
    shell.secondary_title_label.configure(text=f"{_mode_label(active_mode)} Mode")
    shell.secondary_description_label.configure(
        text=_mode_description(active_mode)
    )

    status_text = _status_strip_text(viewer)
    if status_text:
        shell.status_label.configure(text=status_text)
        shell.status_strip.grid()
    else:
        shell.status_label.configure(text="")
        shell.status_strip.grid_remove()

    for mode in modes:
        button = shell.mode_buttons.get(_mode_key(mode))
        if button is None:
            continue
        _style_action_label(
            button,
            active=_mode_key(mode) == active_mode_key,
        )


def apply() -> None:
    global _APPLIED
    if _APPLIED:
        return

    base.MetroMapViewer._configure_desktop_workspace_hosts = (
        _configure_workspace_hosts
    )
    base.MetroMapViewer._finalize_desktop_workspace_hosts = (
        _finalize_workspace_hosts
    )
    _APPLIED = True
