from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import queue
import threading

import numpy as np
from PIL import Image

import legacy_core as base


MAX_ANALYSIS_DIMENSION = 4096
MIN_HOLE_AREA = 1
OUTLINE_COLOR = "#ffd84d"
LARGEST_OUTLINE_COLOR = "#ff7a59"
OUTLINE_WIDTH = 2
COUNT_TEXT_COLOR = "#f5f7fa"
COUNT_TEXT_PADDING_X = 8
COUNT_TEXT_PADDING_Y = 6


@dataclass(frozen=True, slots=True)
class VoidOutline:
    horizontal_segments: tuple[tuple[int, int, int], ...]
    vertical_segments: tuple[tuple[int, int, int], ...]
    image_left: int
    image_top: int
    image_right: int
    image_bottom: int
    area_pixels: int


def _ensure_state(viewer: "base.MetroMapViewer") -> None:
    if hasattr(viewer, "_internal_void_state_ready"):
        return
    viewer._internal_void_state_ready = True
    viewer._internal_void_signature = None
    viewer._internal_void_outlines = []
    viewer._internal_void_queue = queue.Queue()
    viewer._internal_void_thread = None
    viewer._internal_void_stop = None
    viewer._internal_void_polling = False
    viewer._internal_void_analysis_complete = False


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


def _merge_intervals(values: list[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    values.sort()
    runs: list[tuple[int, int]] = []
    run_start = values[0]
    run_end = values[0]
    for value in values[1:]:
        if value == run_end + 1:
            run_end = value
            continue
        runs.append((run_start, run_end))
        run_start = value
        run_end = value
    runs.append((run_start, run_end))
    return runs


def _build_outline(component: list[tuple[int, int]], *, scale: int) -> VoidOutline:
    cells = set(component)
    top_edges: dict[int, list[int]] = defaultdict(list)
    bottom_edges: dict[int, list[int]] = defaultdict(list)
    left_edges: dict[int, list[int]] = defaultdict(list)
    right_edges: dict[int, list[int]] = defaultdict(list)

    xs = [cell_x for cell_x, _cell_y in component]
    ys = [cell_y for _cell_x, cell_y in component]

    for cell_x, cell_y in component:
        if (cell_x, cell_y - 1) not in cells:
            top_edges[cell_y].append(cell_x)
        if (cell_x, cell_y + 1) not in cells:
            bottom_edges[cell_y + 1].append(cell_x)
        if (cell_x - 1, cell_y) not in cells:
            left_edges[cell_x].append(cell_y)
        if (cell_x + 1, cell_y) not in cells:
            right_edges[cell_x + 1].append(cell_y)

    horizontal_segments: list[tuple[int, int, int]] = []
    vertical_segments: list[tuple[int, int, int]] = []

    for edge_y, x_values in top_edges.items():
        for run_start, run_end in _merge_intervals(x_values):
            horizontal_segments.append((edge_y, run_start, run_end + 1))
    for edge_y, x_values in bottom_edges.items():
        for run_start, run_end in _merge_intervals(x_values):
            horizontal_segments.append((edge_y, run_start, run_end + 1))
    for edge_x, y_values in left_edges.items():
        for run_start, run_end in _merge_intervals(y_values):
            vertical_segments.append((edge_x, run_start, run_end + 1))
    for edge_x, y_values in right_edges.items():
        for run_start, run_end in _merge_intervals(y_values):
            vertical_segments.append((edge_x, run_start, run_end + 1))

    return VoidOutline(
        horizontal_segments=tuple(horizontal_segments),
        vertical_segments=tuple(vertical_segments),
        image_left=min(xs) * scale,
        image_top=min(ys) * scale,
        image_right=(max(xs) + 1) * scale,
        image_bottom=(max(ys) + 1) * scale,
        area_pixels=len(component) * (scale * scale),
    )


def _find_internal_voids_worker(
    *,
    signature: tuple[object, ...],
    image: Image.Image,
    result_queue: "queue.Queue[tuple[tuple[object, ...], VoidOutline | None]]",
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
            component: list[tuple[int, int]] = []
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

            result_queue.put((signature, _build_outline(component, scale=scale)))

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
    viewer._internal_void_outlines = []
    viewer._internal_void_analysis_complete = False

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
                        viewer._internal_void_analysis_complete = True
                        continue
                    viewer._internal_void_outlines.append(payload_item)
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
        viewer._internal_void_outlines = []
        viewer._internal_void_analysis_complete = False
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

    outlines = getattr(viewer, "_internal_void_outlines", [])
    if not outlines:
        return

    largest_outline = max(outlines, key=lambda outline: outline.area_pixels)

    for outline in outlines:
        outline_color = LARGEST_OUTLINE_COLOR if outline is largest_outline else OUTLINE_COLOR

        for edge_y, start_x, end_x in outline.horizontal_segments:
            viewer.canvas.create_line(
                left + (start_x * x_scale),
                top + (edge_y * y_scale),
                left + (end_x * x_scale),
                top + (edge_y * y_scale),
                fill=outline_color,
                width=OUTLINE_WIDTH,
            )

        for edge_x, start_y, end_y in outline.vertical_segments:
            viewer.canvas.create_line(
                left + (edge_x * x_scale),
                top + (start_y * y_scale),
                left + (edge_x * x_scale),
                top + (end_y * y_scale),
                fill=outline_color,
                width=OUTLINE_WIDTH,
            )

    count_text = f"Internal voids: {len(outlines)}"
    if not getattr(viewer, "_internal_void_analysis_complete", False):
        count_text += "+"
    viewer.canvas.create_text(
        left + COUNT_TEXT_PADDING_X,
        top + COUNT_TEXT_PADDING_Y,
        anchor="nw",
        text=count_text,
        fill=COUNT_TEXT_COLOR,
        font=("Helvetica", 10, "bold"),
    )
