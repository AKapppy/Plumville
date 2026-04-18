from __future__ import annotations

from math import ceil, floor
from typing import Any, cast

from PIL import Image, ImageTk
import legacy_core as base


UNDERLAY_SEAM_OVERSCAN_PIXELS = 1


def _compute_underlay_draw_plan(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
    source_image: Image.Image,
) -> tuple[float, float, int, int, tuple[int, int, int, int]] | None:
    try:
        render_min_x = base._render_cache_int(payload, "min_x")
        render_max_x = base._render_cache_int(payload, "max_x")
        render_min_z = base._render_cache_int(payload, "min_z")
        render_max_z = base._render_cache_int(payload, "max_z")
    except (KeyError, TypeError, ValueError):
        return None

    top_left_x, top_left_y = viewer.world_to_canvas((render_min_x, -render_min_z))
    bottom_right_x, bottom_right_y = viewer.world_to_canvas((render_max_x, -render_max_z))
    left = min(top_left_x, bottom_right_x)
    right = max(top_left_x, bottom_right_x)
    top = min(top_left_y, bottom_right_y)
    bottom = max(top_left_y, bottom_right_y)
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


def _patched_draw_world_map_target_preview_rectangle(
    self: "base.MetroMapViewer",
    preview: Any,
    *,
    outline: str,
    width: int,
    dash: tuple[int, int] | None,
) -> None:
    canvas_bounds = self._world_map_target_canvas_bounds(preview)
    if canvas_bounds is None:
        return
    left, top, right, bottom = canvas_bounds

    if dash is None:
        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=outline,
            width=width,
        )
    else:
        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=outline,
            width=width,
            dash=dash,
        )


def _patched_draw_world_map_render_underlay(self: "base.MetroMapViewer") -> None:
    if not self.show_world_map_render_var.get():
        return

    render_underlay = self._current_world_map_render_underlay()
    if render_underlay is None:
        return
    payload, source_image = render_underlay
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
    if not self.show_world_map_bounds_var.get():
        return
    self._draw_world_map_next_target_bounds()


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
    base.MetroMapViewer._draw_world_map_target_preview_rectangle = _patched_draw_world_map_target_preview_rectangle
    base.MetroMapViewer._draw_world_map_render_underlay = _patched_draw_world_map_render_underlay
    base.MetroMapViewer._current_world_map_svg_image = _patched_current_world_map_svg_image
