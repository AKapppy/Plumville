from __future__ import annotations

from math import ceil, floor
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageTk
import numpy as np

import legacy_core as base
import world_map_analysis


UNDERLAY_SEAM_OVERSCAN_PIXELS = 1
SHARP_UNDERLAY_UPSCALE_THRESHOLD = 1.5
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


def _underlay_resampling_filter(
    target_width: int,
    target_height: int,
    source_box: tuple[int, int, int, int],
) -> int:
    source_left, source_top, source_right, source_bottom = source_box
    source_width = max(1, source_right - source_left)
    source_height = max(1, source_bottom - source_top)
    upscale = max(target_width / source_width, target_height / source_height)
    if upscale >= SHARP_UNDERLAY_UPSCALE_THRESHOLD:
        try:
            return Image.Resampling.NEAREST
        except AttributeError:
            return cast(Any, Image).NEAREST
    try:
        return Image.Resampling.BILINEAR
    except AttributeError:
        return cast(Any, Image).BILINEAR


def _native_block_image_size(payload: dict[str, object]) -> tuple[int, int] | None:
    try:
        render_min_x = base._render_cache_int(payload, "min_x")
        render_max_x = base._render_cache_int(payload, "max_x")
        render_min_z = base._render_cache_int(payload, "min_z")
        render_max_z = base._render_cache_int(payload, "max_z")
    except (KeyError, TypeError, ValueError):
        return None
    return (render_max_x - render_min_x + 1, render_max_z - render_min_z + 1)


def _image_is_native_block_resolution(payload: dict[str, object], image: Image.Image) -> bool:
    native_size = _native_block_image_size(payload)
    return native_size is not None and image.size == native_size


def _full_resolution_image_candidates(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
) -> list[Path]:
    candidates: list[Path] = []
    payload_image_path = payload.get("image_path")
    if isinstance(payload_image_path, str) and payload_image_path:
        candidates.append(Path(payload_image_path))

    try:
        from worldgen.config import load_config
        from worldgen.generator import BedrockWorldGenerator

        config = load_config()
        mode_paths = BedrockWorldGenerator(config).paths_for_mode(viewer._selected_world_map_mode_key())
        candidates.extend(
            [
                mode_paths.render_image_path,
                mode_paths.docs_render_image_path,
                config.repo_root / "worldgen_output" / mode_paths.render_image_path.name,
                config.repo_root / "docs" / "assets" / mode_paths.render_image_path.name,
            ]
        )
    except Exception:
        pass

    return candidates


def _full_resolution_render_source(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
    source_image: Image.Image,
) -> Image.Image:
    if _image_is_native_block_resolution(payload, source_image):
        return source_image

    native_size = _native_block_image_size(payload)
    if native_size is None:
        return source_image

    candidates = _full_resolution_image_candidates(viewer, payload)
    resolved_candidates: set[Path] = set()
    for candidate in candidates:
        try:
            resolved_candidates.add(candidate.resolve())
        except OSError:
            resolved_candidates.add(candidate)

    cached_path = getattr(viewer, "_world_map_full_render_image_path", None)
    cached_stat = getattr(viewer, "_world_map_full_render_image_stat", None)
    cached_image = getattr(viewer, "_world_map_full_render_source_image", None)
    if isinstance(cached_path, Path) and isinstance(cached_image, Image.Image):
        try:
            resolved_cached_path = cached_path.resolve()
        except OSError:
            resolved_cached_path = cached_path
        image_stat = base._file_stat_key(cached_path)
        if (
            resolved_cached_path in resolved_candidates
            and image_stat is not None
            and image_stat == cached_stat
            and cached_image.size == native_size
        ):
            return cached_image

    seen_paths: set[Path] = set()
    for candidate in candidates:
        try:
            resolved_candidate = candidate.resolve()
        except OSError:
            resolved_candidate = candidate
        if resolved_candidate in seen_paths:
            continue
        seen_paths.add(resolved_candidate)

        image_stat = base._file_stat_key(candidate)
        if image_stat is None:
            continue
        try:
            with Image.open(candidate) as candidate_image:
                if candidate_image.size != native_size:
                    continue
                full_source = candidate_image.convert("RGBA")
        except OSError:
            continue

        viewer._world_map_full_render_image_path = candidate
        viewer._world_map_full_render_image_stat = image_stat
        viewer._world_map_full_render_source_image = full_source
        return full_source

    return source_image


def _draw_plan_is_upscaled(
    target_width: int,
    target_height: int,
    source_box: tuple[int, int, int, int],
) -> bool:
    source_left, source_top, source_right, source_bottom = source_box
    source_width = max(1, source_right - source_left)
    source_height = max(1, source_bottom - source_top)
    return max(target_width / source_width, target_height / source_height) >= SHARP_UNDERLAY_UPSCALE_THRESHOLD


def _alpha_limited_copy(image: Image.Image) -> Image.Image:
    underlay = image.convert("RGBA")
    alpha = underlay.getchannel("A").point(base._limit_world_map_alpha)
    underlay.putalpha(alpha)
    return underlay


def _underlay_cache_key(
    source_image: Image.Image,
    target_width: int,
    target_height: int,
    source_box: tuple[int, int, int, int],
    fast_resample: bool,
) -> tuple[int, int, int, tuple[int, int, int, int], bool]:
    return (id(source_image), target_width, target_height, source_box, fast_resample)


def _cached_underlay_photo(
    viewer: "base.MetroMapViewer",
    source_image: Image.Image,
    target_width: int,
    target_height: int,
    source_box: tuple[int, int, int, int],
    *,
    fast_resample: bool,
) -> ImageTk.PhotoImage:
    cache_key = _underlay_cache_key(source_image, target_width, target_height, source_box, fast_resample)
    cached = getattr(viewer, "_world_map_underlay_photo_cache", None)
    if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == cache_key:
        cached_photo = cached[1]
        if isinstance(cached_photo, ImageTk.PhotoImage):
            return cached_photo

    underlay = source_image.crop(source_box)
    if fast_resample:
        try:
            resampling_filter = Image.Resampling.NEAREST
        except AttributeError:
            resampling_filter = cast(Any, Image).NEAREST
    else:
        resampling_filter = _underlay_resampling_filter(target_width, target_height, source_box)
    underlay = underlay.resize((target_width, target_height), resampling_filter)
    underlay = _alpha_limited_copy(underlay)
    underlay_image = ImageTk.PhotoImage(underlay)
    viewer._world_map_underlay_photo_cache = (cache_key, underlay_image)
    return underlay_image


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


def _patched_draw_world_map_render_underlay(
    self: "base.MetroMapViewer",
    *,
    fast_resample: bool = False,
) -> None:
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
    if _draw_plan_is_upscaled(target_width, target_height, source_box):
        full_source_image = _full_resolution_render_source(self, payload, source_image)
        if full_source_image is not source_image:
            full_draw_plan = _compute_underlay_draw_plan(self, payload, full_source_image)
            if full_draw_plan is not None:
                source_image = full_source_image
                draw_left, draw_top, target_width, target_height, source_box = full_draw_plan

    underlay_image = _cached_underlay_photo(
        self,
        source_image,
        target_width,
        target_height,
        source_box,
        fast_resample=fast_resample,
    )
    self.overlay_image_refs.append(underlay_image)
    image_id = self.canvas.create_image(draw_left, draw_top, anchor="nw", image=underlay_image)
    self.canvas.tag_lower(image_id)

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

    source_image = _full_resolution_render_source(self, payload, source_image)
    draw_plan = _compute_underlay_draw_plan(self, payload, source_image)
    if draw_plan is None:
        return None

    draw_left, draw_top, target_width, target_height, source_box = draw_plan
    underlay = _alpha_limited_copy(source_image.crop(source_box))

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


def _export_visible_block_png(self: "base.MetroMapViewer") -> None:
    from datetime import datetime
    from tkinter import messagebox

    self.root.update_idletasks()
    self.width = self.canvas.winfo_width()
    self.height = self.canvas.winfo_height()

    render_underlay = self._current_world_map_render_underlay()
    if render_underlay is None:
        messagebox.showerror(
            "Export Failed",
            "Render the world map first, then export the visible block-level PNG.",
            parent=self.root,
        )
        return

    payload, source_image = render_underlay
    source_image = _full_resolution_render_source(self, payload, source_image)
    draw_plan = _compute_underlay_draw_plan(self, payload, source_image)
    if draw_plan is None:
        messagebox.showerror(
            "Export Failed",
            "No rendered world-map blocks are visible in the current view.",
            parent=self.root,
        )
        return

    _draw_left, _draw_top, _target_width, _target_height, source_box = draw_plan
    try:
        block_image = _alpha_limited_copy(source_image.crop(source_box))
        base.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        export_path = base.EXPORTS_DIR / f"world-map-blocks-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        block_image.save(export_path, format="PNG")
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror("Export Failed", f"Could not write the block PNG export.\n\n{exc}", parent=self.root)
        return

    messagebox.showinfo("Map Exported", f"Saved block-level PNG to:\n{export_path}", parent=self.root)


def apply() -> None:
    base.MetroMapViewer._draw_world_map_render_underlay = _patched_draw_world_map_render_underlay
    base.MetroMapViewer._current_world_map_svg_image = _patched_current_world_map_svg_image
    base.MetroMapViewer._export_visible_block_png = _export_visible_block_png
