from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import legacy_core as base
import path_detection


ROUTE_FIT_MIN_SPAN = 900.0
ROUTE_FIT_MARGIN_PIXELS = 72.0
WORLDGEN_COMPLETE_COLOR = "#55b86a"

_ORIGINAL_BUILD_ROUTE_PANEL: Callable[..., None] | None = None
_ORIGINAL_REFRESH_CURRENT_ROUTE: Callable[..., None] | None = None
_ORIGINAL_SET_WORLD_MAP_STATUS_TEXT: Callable[..., None] | None = None
_NORMAL_DRAW_SELECTED_STOP_INFO: Callable[..., None] | None = None
_APPLIED = False


@dataclass(slots=True)
class PackedWidgetRecord:
    widget: tk.Widget
    pack_options: dict[str, object]
    next_sibling: tk.Widget | None


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


def _fit_current_route_view(
    self: "base.MetroMapViewer",
    *,
    show_message: bool = False,
) -> bool:
    points = _route_plot_points(self)
    bounds = base._plot_bounds(points)
    if bounds is None:
        if show_message:
            messagebox.showinfo(
                "Fit Route",
                "Calculate a route before fitting the route view.",
                parent=self.root,
            )
        return False

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

    self._set_view_to_plot_bounds(
        center_x - half_width,
        center_x + half_width,
        center_y - half_height,
        center_y + half_height,
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


def _patched_refresh_current_route(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_REFRESH_CURRENT_ROUTE is not None
    _ORIGINAL_REFRESH_CURRENT_ROUTE(self)
    if getattr(self, "current_route", None) is not None:
        _schedule_route_fit(self)


def _append_fit_route_controls(
    self: "base.MetroMapViewer",
    directions_section: tk.Misc | None,
) -> None:
    if directions_section is None:
        return

    fit_row = tk.Frame(
        directions_section,
        bg=base.BACKGROUND_COLOR,
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
        combined = "\n".join(texts)
        if (
            "Auto Fill keeps advancing" in combined
            or "Start Auto Fill" in combined
            or (
                isinstance(child, tk.Frame)
                and any(text == "Mode" for text in texts)
            )
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
        bg=base.INFO_BOX_BACKGROUND,
        fg=WORLDGEN_COMPLETE_COLOR,
        font=(
            "Helvetica",
            base.SIDEBAR_TEXT_FONT_SIZE,
            "bold",
        ),
        anchor="w",
        justify="left",
        padx=12,
        pady=10,
        wraplength=base.SIDEBAR_WIDTH - 56,
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


def _worldgen_completion_is_verified(
    viewer: "base.MetroMapViewer",
) -> bool:
    render_underlay = (
        viewer._current_world_map_render_underlay()
    )
    if render_underlay is None:
        return False
    payload, _image = render_underlay

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
    if (
        isinstance(unfinished_point_count, int)
        and unfinished_point_count > 0
    ):
        return False

    target_bounds = _configured_target_render_bounds()
    payload_bounds = _payload_render_bounds(payload)
    if target_bounds is None or payload_bounds is None:
        return False
    return target_bounds == payload_bounds


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
    if hasattr(self, "root"):
        self.root.after_idle(
            lambda: _refresh_worldgen_control_visibility(
                self
            )
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
    assert _NORMAL_DRAW_SELECTED_STOP_INFO is not None
    _NORMAL_DRAW_SELECTED_STOP_INFO(self)


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


def _patched_build_route_panel(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_BUILD_ROUTE_PANEL is not None

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
            expanded=expanded,
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
    _append_advanced_section(self)


def apply() -> None:
    global _APPLIED
    global _ORIGINAL_BUILD_ROUTE_PANEL
    global _ORIGINAL_REFRESH_CURRENT_ROUTE
    global _ORIGINAL_SET_WORLD_MAP_STATUS_TEXT
    global _NORMAL_DRAW_SELECTED_STOP_INFO

    if _APPLIED:
        return

    _ORIGINAL_BUILD_ROUTE_PANEL = (
        base.MetroMapViewer._build_route_panel
    )
    _ORIGINAL_REFRESH_CURRENT_ROUTE = (
        base.MetroMapViewer._refresh_current_route
    )
    _ORIGINAL_SET_WORLD_MAP_STATUS_TEXT = (
        base.MetroMapViewer._set_world_map_status_text
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

    base.MetroMapViewer._build_route_panel = (
        _patched_build_route_panel
    )
    base.MetroMapViewer._refresh_current_route = (
        _patched_refresh_current_route
    )
    base.MetroMapViewer._set_world_map_status_text = (
        _patched_set_world_map_status_text
    )
    base.MetroMapViewer._draw_selected_stop_info = (
        _draw_selected_stop_info_without_detection_button
    )
    base.MetroMapViewer._fit_current_route_view = (
        _fit_current_route_view
    )
    base.MetroMapViewer._refresh_worldgen_control_visibility = (
        _refresh_worldgen_control_visibility
    )
    _APPLIED = True
