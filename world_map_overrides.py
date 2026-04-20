from __future__ import annotations

from math import ceil, floor
from typing import Any, cast

from PIL import Image, ImageTk
import numpy as np

import legacy_core as base
import world_map_analysis


UNDERLAY_SEAM_OVERSCAN_PIXELS = 1
BOUNDARY_EDGE_COLOR = "#e5e7eb"
BOUNDARY_EDGE_WIDTH = 1
EDGE_TOUCH_BAND = 2


def _render_canvas_rect(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
) -> tuple[float, float, float, float] | None:
    try:
        render_min_x = base._render_cache_int(payload, "min_x")
        render_max_x = base._render_cache_int(payload, "max_x")
        render_min_z = base._render_cache_int(payload, "min_z")
        render_max_z = base._render_cache_int(payload, "max_z")
    except (KeyError, TypeError, ValueError):
        return None

    top_left_x, top_left_y = viewer.world_to_canvas((render_min_x, -render_min_z))
    bottom_right_x, bottom_right_y = viewer.world_to_canvas((render_max_x, -render_max_z))
    return (
        min(top_left_x, bottom_right_x),
        min(top_left_y, bottom_right_y),
        max(top_left_x, bottom_right_x),
        max(top_left_y, bottom_right_y),
    )


def _compute_underlay_draw_plan(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
    source_image: Image.Image,
) -> tuple[float, float, int, int, tuple[int, int, int, int]] | None:
    render_rect = _render_canvas_rect(viewer, payload)
    if render_rect is None:
        return None
    left, top, right, bottom = render_rect
    if right <= left or bottom <= top:
        return None

    visible_left = max(0.0, left)
    visible_top = max(0.0, top)
    visible_right = min(float(viewer.width), right)
    visible_bottom = min(float(viewer.height), bottom)
    if visible_right <= visible_left or visible_bottom <= visible_top:
        return None

    image_width, image_height = source_image.size
    source_left = floor(max(0, min(image_width, ((visible_left - left) / (right - left)) * image_width)))
    source_right = ceil(max(0, min(image_width, ((visible_right - left) / (right - left)) * image_width)))
    source_top = floor(max(0, min(image_height, ((visible_top - top) / (bottom - top)) * image_height)))
    source_bottom = ceil(max(0, min(image_height, ((visible_bottom - top) / (bottom - top)) * image_height)))
    if source_right <= source_left or source_bottom <= source_top:
        return None

    overscan = UNDERLAY_SEAM_OVERSCAN_PIXELS
    padded_source_left = max(0, source_left - overscan)
    padded_source_top = max(0, source_top - overscan)
    padded_source_right = min(image_width, source_right + overscan)
    padded_source_bottom = min(image_height, source_bottom + overscan)

    x_scale = (right - left) / max(1, image_width)
    y_scale = (bottom - top) / max(1, image_height)
    draw_left = left + (padded_source_left * x_scale)
    draw_top = top + (padded_source_top * y_scale)
    draw_right = left + (padded_source_right * x_scale)
    draw_bottom = top + (padded_source_bottom * y_scale)

    target_width = max(1, round(draw_right - draw_left))
    target_height = max(1, round(draw_bottom - draw_top))
    source_box = (
        padded_source_left,
        padded_source_top,
        padded_source_right,
        padded_source_bottom,
    )
    return (draw_left, draw_top, target_width, target_height, source_box)


def _edge_runs(edge_mask: np.ndarray) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    run_start = None
    for index, value in enumerate(edge_mask.tolist()):
        if value and run_start is None:
            run_start = index
        elif not value and run_start is not None:
            runs.append((run_start, index - 1))
            run_start = None
    if run_start is not None:
        runs.append((run_start, len(edge_mask) - 1))
    return runs


def _draw_world_boundary_completion_edges(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
    source_image: Image.Image,
) -> None:
    if not viewer.show_world_map_render_var.get():
        return

    render_rect = _render_canvas_rect(viewer, payload)
    if render_rect is None:
        return
    render_left, render_top, render_right, render_bottom = render_rect

    visible_bounds = None
    if hasattr(base, "_world_map_visible_render_bounds_from_payload"):
        visible_bounds = base._world_map_visible_render_bounds_from_payload(payload)
    if visible_bounds is None:
        return

    try:
        render_min_x = base._render_cache_int(payload, "min_x")
        render_max_x = base._render_cache_int(payload, "max_x")
        render_min_z = base._render_cache_int(payload, "min_z")
        render_max_z = base._render_cache_int(payload, "max_z")
    except (KeyError, TypeError, ValueError):
        return

    colored_min_x, colored_max_x, colored_min_z, colored_max_z = visible_bounds

    alpha = np.asarray(source_image.getchannel("A"), dtype=np.uint8)
    rendered = alpha > 8
    if rendered.size == 0:
        return
    image_height, image_width = rendered.shape

    x_scale = (render_right - render_left) / max(1, image_width)
    y_scale = (render_bottom - render_top) / max(1, image_height)

    if colored_min_z == render_min_z:
        top_mask = np.any(rendered[:EDGE_TOUCH_BAND, :], axis=0)
        for run_start, run_end in _edge_runs(top_mask):
            x0 = render_left + (run_start * x_scale)
            x1 = render_left + ((run_end + 1) * x_scale)
            viewer.canvas.create_line(
                x0,
                render_top,
                x1,
                render_top,
                fill=BOUNDARY_EDGE_COLOR,
                width=BOUNDARY_EDGE_WIDTH,
            )

    if colored_max_z == render_max_z:
        bottom_mask = np.any(rendered[max(0, image_height - EDGE_TOUCH_BAND):, :], axis=0)
        for run_start, run_end in _edge_runs(bottom_mask):
            x0 = render_left + (run_start * x_scale)
            x1 = render_left + ((run_end + 1) * x_scale)
            viewer.canvas.create_line(
                x0,
                render_bottom,
                x1,
                render_bottom,
                fill=BOUNDARY_EDGE_COLOR,
                width=BOUNDARY_EDGE_WIDTH,
            )

    if colored_min_x == render_min_x:
        left_mask = np.any(rendered[:, :EDGE_TOUCH_BAND], axis=1)
        for run_start, run_end in _edge_runs(left_mask):
            y0 = render_top + (run_start * y_scale)
            y1 = render_top + ((run_end + 1) * y_scale)
            viewer.canvas.create_line(
                render_left,
                y0,
                render_left,
                y1,
                fill=BOUNDARY_EDGE_COLOR,
                width=BOUNDARY_EDGE_WIDTH,
            )

    if colored_max_x == render_max_x:
        right_mask = np.any(rendered[:, max(0, image_width - EDGE_TOUCH_BAND):], axis=1)
        for run_start, run_end in _edge_runs(right_mask):
            y0 = render_top + (run_start * y_scale)
            y1 = render_top + ((run_end + 1) * y_scale)
            viewer.canvas.create_line(
                render_right,
                y0,
                render_right,
                y1,
                fill=BOUNDARY_EDGE_COLOR,
                width=BOUNDARY_EDGE_WIDTH,
            )


def _patched_draw_world_map_render_underlay(self: "base.MetroMapViewer") -> None:
    if not self.show_world_map_render_var.get():
        return

    render_underlay = self._current_world_map_render_underlay()
    if render_underlay is None:
        return
    payload, source_image = render_underlay

    world_map_analysis.update_background_analysis(self, payload, source_image)

    draw_plan = _compute_underlay_draw_plan(self, payload, source_image)
    if draw_plan is None:
        return

    draw_left, draw_top, target_width, target_height, source_box = draw_plan
    underlay = source_image.crop(source_box)
    try:
        resampling_filter = Image.Resampling.BILINEAR
    except AttributeError:
        resampling_filter = cast(Any, Image).BILINEAR
    underlay = underlay.resize((target_width, target_height), resampling_filter)
    alpha = underlay.getchannel("A").point(base._limit_world_map_alpha)
    underlay.putalpha(alpha)
    underlay_image = ImageTk.PhotoImage(underlay)
    self.overlay_image_refs.append(underlay_image)
    self.canvas.create_image(draw_left, draw_top, anchor="nw", image=underlay_image)

    world_map_analysis.draw_internal_voids(self, payload, source_image)
    _draw_world_boundary_completion_edges(self, payload, source_image)


def _patched_current_world_map_svg_image(self: "base.MetroMapViewer") -> base.SvgRasterImage | None:
    render_underlay = self._current_world_map_render_underlay()
    if render_underlay is None:
        return None
    payload, source_image = render_underlay
    draw_plan = _compute_underlay_draw_plan(self, payload, source_image)
    if draw_plan is None:
        return None

    draw_left, draw_top, target_width, target_height, source_box = draw_plan
    underlay = source_image.crop(source_box)
    try:
        resampling_filter = Image.Resampling.BILINEAR
    except AttributeError:
        resampling_filter = cast(Any, Image).BILINEAR
    underlay = underlay.resize((target_width, target_height), resampling_filter)
    alpha = underlay.getchannel("A").point(base._limit_world_map_alpha)
    underlay.putalpha(alpha)

    import base64
    import io

    buffer = io.BytesIO()
    underlay.save(buffer, format="PNG")
    encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")
    return base.SvgRasterImage(
        data_uri=f"data:image/png;base64,{encoded_image}",
        left=draw_left,
        top=draw_top,
        width=target_width,
        height=target_height,
    )


def apply() -> None:
    base.MetroMapViewer._draw_world_map_render_underlay = _patched_draw_world_map_render_underlay
    base.MetroMapViewer._current_world_map_svg_image = _patched_current_world_map_svg_image
