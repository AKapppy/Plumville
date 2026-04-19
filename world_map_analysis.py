from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import queue
import threading
from typing import Any

import numpy as np
from PIL import Image

import legacy_core as base


MAX_ANALYSIS_DIMENSION = 4096
MIN_HOLE_AREA = 1
HIGHLIGHT_OUTLINE = "#ffd84d"
HIGHLIGHT_WIDTH = 2
HIGHLIGHT_PADDING = 4


@dataclass(frozen=True, slots=True)
class VoidHighlight:
    image_left: int
    image_top: int
    image_right: int
    image_bottom: int


def _ensure_state(viewer: "base.MetroMapViewer") -> None:
    if hasattr(viewer, "_internal_void_state_ready"):
        return
    viewer._internal_void_state_ready = True
    viewer._internal_void_signature = None
    viewer._internal_void_highlights = []
    viewer._internal_void_queue = queue.Queue()
    viewer._internal_void_thread = None
    viewer._internal_void_stop = None
    viewer._internal_void_polling = False


def _analysis_signature(
    payload: dict[str, object],
    image: Image.Image,
    *,
    sealed_top: bool,
    sealed_bottom: bool,
    sealed_left: bool,
    sealed_right: bool,
) -> tuple[object, ...]:
    return (
        base._render_cache_int(payload, "min_x"),
        base._render_cache_int(payload, "max_x"),
        base._render_cache_int(payload, "min_z"),
        base._render_cache_int(payload, "max_z"),
        image.size[0],
        image.size[1],
        bool(sealed_top),
        bool(sealed_bottom),
        bool(sealed_left),
        bool(sealed_right),
        str(payload.get("generated_at", "")),
    )


def _downsample_render_mask(image: Image.Image) -> tuple[np.ndarray, int]:
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    rendered = alpha > 8
    height, width = rendered.shape
    max_dimension = max(height, width)
    if max_dimension <= MAX_ANALYSIS_DIMENSION:
        return rendered, 1

    scale = max(1, int(np.ceil(max_dimension / MAX_ANALYSIS_DIMENSION)))
    target_height = max(1, int(np.ceil(height / scale)))
    target_width = max(1, int(np.ceil(width / scale)))
    reduced = np.zeros((target_height, target_width), dtype=bool)
    for target_y in range(target_height):
        source_y0 = target_y * scale
        source_y1 = min(height, source_y0 + scale)
        for target_x in range(target_width):
            source_x0 = target_x * scale
            source_x1 = min(width, source_x0 + scale)
            if np.any(rendered[source_y0:source_y1, source_x0:source_x1]):
                reduced[target_y, target_x] = True
    return reduced, scale


def _find_internal_voids_worker(
    *,
    signature: tuple[object, ...],
    image: Image.Image,
    result_queue: "queue.Queue[tuple[tuple[object, ...], VoidHighlight | None]]",
    stop_event: threading.Event,
    sealed_top: bool,
    sealed_bottom: bool,
    sealed_left: bool,
    sealed_right: bool,
) -> None:
    reduced_mask, scale = _downsample_render_mask(image)
    blank_mask = ~reduced_mask
    height, width = blank_mask.shape
    visited = np.zeros((height, width), dtype=bool)

    for start_y in range(height):
        if stop_event.is_set():
            return
        for start_x in range(width):
            if stop_event.is_set():
                return
            if visited[start_y, start_x] or not blank_mask[start_y, start_x]:
                continue

            queue_local = deque([(start_x, start_y)])
            visited[start_y, start_x] = True
            component = []
            touches_unsealed_border = False

            while queue_local:
                current_x, current_y = queue_local.popleft()
                component.append((current_x, current_y))

                if current_y == 0 and not sealed_top:
                    touches_unsealed_border = True
                if current_y == height - 1 and not sealed_bottom:
                    touches_unsealed_border = True
                if current_x == 0 and not sealed_left:
                    touches_unsealed_border = True
                if current_x == width - 1 and not sealed_right:
                    touches_unsealed_border = True

                for neighbor_x, neighbor_y in (
                    (current_x + 1, current_y),
                    (current_x - 1, current_y),
                    (current_x, current_y + 1),
                    (current_x, current_y - 1),
                ):
                    if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                        continue
                    if visited[neighbor_y, neighbor_x] or not blank_mask[neighbor_y, neighbor_x]:
                        continue
                    visited[neighbor_y, neighbor_x] = True
                    queue_local.append((neighbor_x, neighbor_y))

            if touches_unsealed_border or len(component) < MIN_HOLE_AREA:
                continue

            xs = [point_x for point_x, _point_y in component]
            ys = [point_y for _point_x, point_y in component]
            highlight = VoidHighlight(
                image_left=max(0, (min(xs) * scale) - HIGHLIGHT_PADDING),
                image_top=max(0, (min(ys) * scale) - HIGHLIGHT_PADDING),
                image_right=((max(xs) + 1) * scale) + HIGHLIGHT_PADDING,
                image_bottom=((max(ys) + 1) * scale) + HIGHLIGHT_PADDING,
            )
            result_queue.put((signature, highlight))

    result_queue.put((signature, None))


def _sealed_edges_from_payload(payload: dict[str, object]) -> tuple[bool, bool, bool, bool]:
    try:
        render_min_x = base._render_cache_int(payload, "min_x")
        render_max_x = base._render_cache_int(payload, "max_x")
        render_min_z = base._render_cache_int(payload, "min_z")
        render_max_z = base._render_cache_int(payload, "max_z")
    except (KeyError, TypeError, ValueError):
        return (False, False, False, False)

    visible_bounds = None
    if hasattr(base, "_world_map_visible_render_bounds_from_payload"):
        visible_bounds = base._world_map_visible_render_bounds_from_payload(payload)
    if visible_bounds is None:
        return (False, False, False, False)

    colored_min_x, colored_max_x, colored_min_z, colored_max_z = visible_bounds
    sealed_top = colored_min_z == render_min_z
    sealed_bottom = colored_max_z == render_max_z
    sealed_left = colored_min_x == render_min_x
    sealed_right = colored_max_x == render_max_x
    return (sealed_top, sealed_bottom, sealed_left, sealed_right)


def _start_analysis(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
    image: Image.Image,
) -> None:
    _ensure_state(viewer)
    sealed_top, sealed_bottom, sealed_left, sealed_right = _sealed_edges_from_payload(payload)
    signature = _analysis_signature(
        payload,
        image,
        sealed_top=sealed_top,
        sealed_bottom=sealed_bottom,
        sealed_left=sealed_left,
        sealed_right=sealed_right,
    )
    if getattr(viewer, "_internal_void_signature", None) == signature:
        return

    viewer._internal_void_signature = signature
    viewer._internal_void_highlights = []

    stop_event = getattr(viewer, "_internal_void_stop", None)
    if stop_event is not None:
        stop_event.set()

    new_stop = threading.Event()
    viewer._internal_void_stop = new_stop
    viewer._internal_void_queue = queue.Queue()

    worker = threading.Thread(
        target=_find_internal_voids_worker,
        kwargs={
            "signature": signature,
            "image": image.copy(),
            "result_queue": viewer._internal_void_queue,
            "stop_event": new_stop,
            "sealed_top": sealed_top,
            "sealed_bottom": sealed_bottom,
            "sealed_left": sealed_left,
            "sealed_right": sealed_right,
        },
        daemon=True,
    )
    viewer._internal_void_thread = worker
    worker.start()

    if not getattr(viewer, "_internal_void_polling", False):
        viewer._internal_void_polling = True

        def poll() -> None:
            if not getattr(viewer, "_internal_void_polling", False):
                return
            updated = False
            queue_local = getattr(viewer, "_internal_void_queue", None)
            try:
                while queue_local is not None:
                    item_signature, payload_item = queue_local.get_nowait()
                    if item_signature != getattr(viewer, "_internal_void_signature", None):
                        continue
                    if payload_item is None:
                        continue
                    viewer._internal_void_highlights.append(payload_item)
                    updated = True
            except queue.Empty:
                pass
            if updated:
                viewer.redraw()
            viewer.root.after(120, poll)

        viewer.root.after(120, poll)


def update_background_analysis(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
    image: Image.Image,
) -> None:
    _ensure_state(viewer)
    if not getattr(viewer, "circle_internal_voids_var", None) or not viewer.circle_internal_voids_var.get():
        stop_event = getattr(viewer, "_internal_void_stop", None)
        if stop_event is not None:
            stop_event.set()
        viewer._internal_void_signature = None
        viewer._internal_void_highlights = []
        return

    _start_analysis(viewer, payload, image)


def _render_rect(
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


def draw_internal_voids(
    viewer: "base.MetroMapViewer",
    payload: dict[str, object],
    image: Image.Image,
) -> None:
    if not getattr(viewer, "circle_internal_voids_var", None) or not viewer.circle_internal_voids_var.get():
        return

    render_rect = _render_rect(viewer, payload)
    if render_rect is None:
        return
    left, top, right, bottom = render_rect
    image_width, image_height = image.size
    if image_width <= 0 or image_height <= 0 or right <= left or bottom <= top:
        return

    x_scale = (right - left) / image_width
    y_scale = (bottom - top) / image_height

    for highlight in getattr(viewer, "_internal_void_highlights", []):
        draw_left = left + (highlight.image_left * x_scale)
        draw_top = top + (highlight.image_top * y_scale)
        draw_right = left + (highlight.image_right * x_scale)
        draw_bottom = top + (highlight.image_bottom * y_scale)
        viewer.canvas.create_oval(
            draw_left,
            draw_top,
            draw_right,
            draw_bottom,
            outline=HIGHLIGHT_OUTLINE,
            width=HIGHLIGHT_WIDTH,
            dash=(4, 3),
        )
