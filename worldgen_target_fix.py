from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Callable

_APPLIED = False

_ORIGINAL_NEXT_UNDERCOVERED = None
_ORIGINAL_RENDER_AREA_TELEPORT_POINTS = None
_ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH = None


@dataclass(frozen=True, slots=True)
class _BlankChunkComponent:
    chunk_counts: dict[tuple[int, int], int]
    total_blank_pixels: int
    min_chunk_x: int
    max_chunk_x: int
    min_chunk_z: int
    max_chunk_z: int
    centroid_chunk_x: float
    centroid_chunk_z: float
    is_internal: bool


_COMPONENT_CACHE: dict[tuple[object, ...], tuple[_BlankChunkComponent, ...]] = {}


def _file_signature(path: Path) -> tuple[str, int, int] | None:
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return (str(path.resolve()), stat_result.st_mtime_ns, stat_result.st_size)


def _load_render_metadata(config) -> dict[str, object]:
    try:
        metadata_text = config.paths.render_cache_path.read_text(encoding='utf-8')
    except OSError:
        return {}
    try:
        payload = json.loads(metadata_text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _render_chunk_bounds(config) -> tuple[int, int, int, int]:
    render = config.render
    return (
        render.min_x // 16,
        render.max_x // 16,
        render.min_z // 16,
        render.max_z // 16,
    )


def _colored_chunk_bounds(metadata: dict[str, object]) -> tuple[int, int, int, int] | None:
    try:
        colored_min_x = int(metadata['colored_min_x']) // 16
        colored_max_x = int(metadata['colored_max_x']) // 16
        colored_min_z = int(metadata['colored_min_z']) // 16
        colored_max_z = int(metadata['colored_max_z']) // 16
    except (KeyError, TypeError, ValueError):
        return None
    return (colored_min_x, colored_max_x, colored_min_z, colored_max_z)


def _component_is_internal(
    component_chunk_counts: dict[tuple[int, int], int],
    *,
    config,
    metadata: dict[str, object],
) -> bool:
    colored_bounds = _colored_chunk_bounds(metadata)
    if colored_bounds is None:
        return False

    render_min_chunk_x, render_max_chunk_x, render_min_chunk_z, render_max_chunk_z = _render_chunk_bounds(config)
    colored_min_chunk_x, colored_max_chunk_x, colored_min_chunk_z, colored_max_chunk_z = colored_bounds

    min_chunk_x = min(chunk_x for chunk_x, _chunk_z in component_chunk_counts)
    max_chunk_x = max(chunk_x for chunk_x, _chunk_z in component_chunk_counts)
    min_chunk_z = min(chunk_z for _chunk_x, chunk_z in component_chunk_counts)
    max_chunk_z = max(chunk_z for _chunk_x, chunk_z in component_chunk_counts)

    top_ok = (
        min_chunk_z >= colored_min_chunk_z
        or (min_chunk_z == render_min_chunk_z and colored_min_chunk_z == render_min_chunk_z)
    )
    bottom_ok = (
        max_chunk_z <= colored_max_chunk_z
        or (max_chunk_z == render_max_chunk_z and colored_max_chunk_z == render_max_chunk_z)
    )
    left_ok = (
        min_chunk_x >= colored_min_chunk_x
        or (min_chunk_x == render_min_chunk_x and colored_min_chunk_x == render_min_chunk_x)
    )
    right_ok = (
        max_chunk_x <= colored_max_chunk_x
        or (max_chunk_x == render_max_chunk_x and colored_max_chunk_x == render_max_chunk_x)
    )
    return top_ok and bottom_ok and left_ok and right_ok


def _blank_chunk_components(config, blank_coverage) -> tuple[_BlankChunkComponent, ...]:
    if blank_coverage is None or not blank_coverage.blank_pixels_by_chunk:
        return ()

    metadata_path_sig = _file_signature(config.paths.render_cache_path)
    cache_key = (
        blank_coverage.image_stat,
        metadata_path_sig,
        config.render.min_x,
        config.render.max_x,
        config.render.min_z,
        config.render.max_z,
    )
    cached = _COMPONENT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    metadata = _load_render_metadata(config)
    remaining = set(blank_coverage.blank_pixels_by_chunk)
    components: list[_BlankChunkComponent] = []

    while remaining:
        seed = remaining.pop()
        queue = deque([seed])
        component_chunk_counts: dict[tuple[int, int], int] = {
            seed: blank_coverage.blank_pixels_by_chunk[seed]
        }

        while queue:
            current_x, current_z = queue.popleft()
            for neighbor in (
                (current_x + 1, current_z),
                (current_x - 1, current_z),
                (current_x, current_z + 1),
                (current_x, current_z - 1),
            ):
                if neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                component_chunk_counts[neighbor] = blank_coverage.blank_pixels_by_chunk[neighbor]
                queue.append(neighbor)

        total_blank_pixels = sum(component_chunk_counts.values())
        weighted_x = sum(chunk_x * count for (chunk_x, _chunk_z), count in component_chunk_counts.items())
        weighted_z = sum(chunk_z * count for (_chunk_x, chunk_z), count in component_chunk_counts.items())
        centroid_chunk_x = weighted_x / max(1, total_blank_pixels)
        centroid_chunk_z = weighted_z / max(1, total_blank_pixels)
        components.append(
            _BlankChunkComponent(
                chunk_counts=component_chunk_counts,
                total_blank_pixels=total_blank_pixels,
                min_chunk_x=min(chunk_x for chunk_x, _chunk_z in component_chunk_counts),
                max_chunk_x=max(chunk_x for chunk_x, _chunk_z in component_chunk_counts),
                min_chunk_z=min(chunk_z for _chunk_x, chunk_z in component_chunk_counts),
                max_chunk_z=max(chunk_z for _chunk_x, chunk_z in component_chunk_counts),
                centroid_chunk_x=centroid_chunk_x,
                centroid_chunk_z=centroid_chunk_z,
                is_internal=_component_is_internal(
                    component_chunk_counts,
                    config=config,
                    metadata=metadata,
                ),
            )
        )

    center_chunk_x = config.render.center_x // 16
    center_chunk_z = config.render.center_z // 16
    components.sort(
        key=lambda component: (
            0 if component.is_internal else 1,
            -component.total_blank_pixels,
            math.hypot(component.centroid_chunk_x - center_chunk_x, component.centroid_chunk_z - center_chunk_z),
        )
    )
    result = tuple(components)
    _COMPONENT_CACHE[cache_key] = result
    return result


def _clamp_chunk_center(config, center_chunk: tuple[int, int]) -> tuple[int, int]:
    import worldgen.generator as generator

    min_chunk_x, max_chunk_x, min_chunk_z, max_chunk_z = generator._target_load_chunk_bounds()
    chunk_x = max(min_chunk_x, min(max_chunk_x, center_chunk[0]))
    chunk_z = max(min_chunk_z, min(max_chunk_z, center_chunk[1]))
    return (chunk_x, chunk_z)


def _covered_blank_pixels(component: _BlankChunkComponent, center_chunk: tuple[int, int], *, radius: int) -> int:
    center_x, center_z = center_chunk
    return sum(
        blank_count
        for (chunk_x, chunk_z), blank_count in component.chunk_counts.items()
        if abs(chunk_x - center_x) <= radius and abs(chunk_z - center_z) <= radius
    )


def _component_targets(config, component: _BlankChunkComponent) -> list[tuple[int, int]]:
    import worldgen.generator as generator

    radius = config.headless_loader.chunk_radius
    remaining = dict(component.chunk_counts)
    targets: list[tuple[int, int]] = []

    while remaining:
        candidate_centers: set[tuple[int, int]] = set(remaining)
        centroid_chunk = (
            round(component.centroid_chunk_x),
            round(component.centroid_chunk_z),
        )
        candidate_centers.add(centroid_chunk)
        candidate_centers.add((component.min_chunk_x, component.min_chunk_z))
        candidate_centers.add((component.max_chunk_x, component.max_chunk_z))
        candidate_centers.add((component.min_chunk_x, component.max_chunk_z))
        candidate_centers.add((component.max_chunk_x, component.min_chunk_z))

        best_center = None
        best_score = None
        for candidate_center in candidate_centers:
            clamped_center = _clamp_chunk_center(config, candidate_center)
            coverage = sum(
                blank_count
                for (chunk_x, chunk_z), blank_count in remaining.items()
                if abs(chunk_x - clamped_center[0]) <= radius and abs(chunk_z - clamped_center[1]) <= radius
            )
            if coverage <= 0:
                continue
            score = (
                coverage,
                -math.hypot(
                    clamped_center[0] - component.centroid_chunk_x,
                    clamped_center[1] - component.centroid_chunk_z,
                ),
            )
            if best_score is None or score > best_score:
                best_score = score
                best_center = clamped_center

        if best_center is None:
            break

        targets.append(generator._chunk_center_world_pair(best_center))
        covered = [
            chunk
            for chunk in remaining
            if abs(chunk[0] - best_center[0]) <= radius and abs(chunk[1] - best_center[1]) <= radius
        ]
        for chunk in covered:
            del remaining[chunk]

    return targets


def _component_priority_teleport_points(config, blank_coverage) -> tuple[tuple[int, int], ...]:
    components = _blank_chunk_components(config, blank_coverage)
    if not components:
        return ()

    ordered_targets: list[tuple[int, int]] = []
    seen_targets: set[tuple[int, int]] = set()
    for component in components:
        for target in _component_targets(config, component):
            if target in seen_targets:
                continue
            seen_targets.add(target)
            ordered_targets.append(target)
    return tuple(ordered_targets)


def _prioritized_render_area_teleport_points(
    config,
    *,
    world_path=None,
    blank_coverage=None,
):
    if blank_coverage is not None:
        prioritized_points = _component_priority_teleport_points(config, blank_coverage)
        if prioritized_points:
            return prioritized_points
    return _ORIGINAL_RENDER_AREA_TELEPORT_POINTS(
        config,
        world_path=world_path,
        blank_coverage=blank_coverage,
    )


def _prioritized_next_undercovered_teleport_index(
    config,
    teleport_points,
    *,
    start_index,
    world_path,
    blank_coverage=None,
):
    import worldgen.generator as generator

    if not teleport_points:
        return 0

    normalized_start_index = start_index % len(teleport_points)

    if blank_coverage is not None:
        fallback_index = None
        for offset in range(len(teleport_points)):
            index = (normalized_start_index + offset) % len(teleport_points)
            point = teleport_points[index]
            missing_pixels = generator._teleport_point_missing_pixel_count(
                config,
                point,
                blank_coverage,
            )
            if missing_pixels > max(64, generator.TELEPORT_TARGET_MIN_ACTIONABLE_BLANK_PIXELS // 8):
                return index
            if missing_pixels > 0 and fallback_index is None:
                fallback_index = index
        return normalized_start_index if fallback_index is None else fallback_index

    return _ORIGINAL_NEXT_UNDERCOVERED(
        config,
        teleport_points,
        start_index=start_index,
        world_path=world_path,
        blank_coverage=blank_coverage,
    )


def _pixel_bounds_for_chunk(config, chunk_x: int, chunk_z: int) -> tuple[int, int, int, int] | None:
    render = config.render
    sample_step = render.sample_step

    min_world_x = chunk_x * 16
    max_world_x = (chunk_x * 16) + 15
    min_world_z = chunk_z * 16
    max_world_z = (chunk_z * 16) + 15

    if max_world_x < render.min_x or min_world_x > render.max_x or max_world_z < render.min_z or min_world_z > render.max_z:
        return None

    width = generator_width = ((render.max_x - render.min_x) // sample_step) + 1
    height = ((render.max_z - render.min_z) // sample_step) + 1
    min_pixel_x = max(0, math.ceil((max(min_world_x, render.min_x) - render.min_x) / sample_step))
    max_pixel_x = min(width - 1, math.floor((min(max_world_x, render.max_x) - render.min_x) / sample_step))
    min_pixel_z = max(0, math.ceil((max(min_world_z, render.min_z) - render.min_z) / sample_step))
    max_pixel_z = min(height - 1, math.floor((min(max_world_z, render.max_z) - render.min_z) / sample_step))
    if min_pixel_x > max_pixel_x or min_pixel_z > max_pixel_z:
        return None
    return (min_pixel_x, max_pixel_x, min_pixel_z, max_pixel_z)


def _component_blank_pixel_batch(
    config,
    image_path,
    *,
    batch_size,
    max_scan_pixels,
):
    import worldgen.generator as generator
    from PIL import Image

    if batch_size <= 0 or max_scan_pixels <= 0:
        return _ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH(
            config,
            image_path,
            batch_size=batch_size,
            max_scan_pixels=max_scan_pixels,
        )

    blank_coverage = generator._load_blank_render_coverage(config, image_path)
    if blank_coverage is None or blank_coverage.blank_pixel_count == 0:
        return _ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH(
            config,
            image_path,
            batch_size=batch_size,
            max_scan_pixels=max_scan_pixels,
        )

    components = _blank_chunk_components(config, blank_coverage)
    if not components:
        return _ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH(
            config,
            image_path,
            batch_size=batch_size,
            max_scan_pixels=max_scan_pixels,
        )

    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(image_path) as source_image:
            alpha = source_image.convert('RGBA').getchannel('A')
    except OSError:
        return _ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH(
            config,
            image_path,
            batch_size=batch_size,
            max_scan_pixels=max_scan_pixels,
        )

    pixels = alpha.load()
    if pixels is None:
        return _ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH(
            config,
            image_path,
            batch_size=batch_size,
            max_scan_pixels=max_scan_pixels,
        )

    render = config.render
    center_pixel_x = max(0, round((render.center_x - render.min_x) / render.sample_step))
    center_pixel_z = max(0, round((render.center_z - render.min_z) / render.sample_step))

    selected_pixels: set[tuple[int, int]] = set()
    scanned_pixels = 0
    last_pixel_x = center_pixel_x
    last_pixel_z = center_pixel_z

    for component in components:
        chunk_items = sorted(
            component.chunk_counts.items(),
            key=lambda item: (
                -item[1],
                math.hypot(item[0][0] - component.centroid_chunk_x, item[0][1] - component.centroid_chunk_z),
            ),
        )
        for (chunk_x, chunk_z), _blank_count in chunk_items:
            bounds = _pixel_bounds_for_chunk(config, chunk_x, chunk_z)
            if bounds is None:
                continue
            min_pixel_x, max_pixel_x, min_pixel_z, max_pixel_z = bounds
            for pixel_z in range(min_pixel_z, max_pixel_z + 1):
                for pixel_x in range(min_pixel_x, max_pixel_x + 1):
                    scanned_pixels += 1
                    if scanned_pixels > max_scan_pixels:
                        return generator._BlankPixelSpiralBatch(
                            pixel_keys=selected_pixels,
                            scanned_pixels=scanned_pixels,
                            center_pixel_x=center_pixel_x,
                            center_pixel_z=center_pixel_z,
                            last_pixel_x=last_pixel_x,
                            last_pixel_z=last_pixel_z,
                        )
                    if pixels[pixel_x, pixel_z] != 0:
                        continue
                    selected_pixels.add((pixel_x, pixel_z))
                    last_pixel_x = pixel_x
                    last_pixel_z = pixel_z
                    if len(selected_pixels) >= batch_size:
                        return generator._BlankPixelSpiralBatch(
                            pixel_keys=selected_pixels,
                            scanned_pixels=scanned_pixels,
                            center_pixel_x=center_pixel_x,
                            center_pixel_z=center_pixel_z,
                            last_pixel_x=last_pixel_x,
                            last_pixel_z=last_pixel_z,
                        )

    return generator._BlankPixelSpiralBatch(
        pixel_keys=selected_pixels,
        scanned_pixels=scanned_pixels,
        center_pixel_x=center_pixel_x,
        center_pixel_z=center_pixel_z,
        last_pixel_x=last_pixel_x,
        last_pixel_z=last_pixel_z,
    )


def apply() -> None:
    global _APPLIED
    global _ORIGINAL_NEXT_UNDERCOVERED
    global _ORIGINAL_RENDER_AREA_TELEPORT_POINTS
    global _ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH

    if _APPLIED:
        return

    import worldgen.generator as generator

    _ORIGINAL_NEXT_UNDERCOVERED = generator._next_undercovered_teleport_index
    _ORIGINAL_RENDER_AREA_TELEPORT_POINTS = generator._render_area_teleport_points
    _ORIGINAL_BLANK_PIXEL_SPIRAL_BATCH = generator._blank_pixel_spiral_batch

    generator._render_area_teleport_points = _prioritized_render_area_teleport_points
    generator._next_undercovered_teleport_index = _prioritized_next_undercovered_teleport_index
    generator._blank_pixel_spiral_batch = _component_blank_pixel_batch

    generator.INCREMENTAL_RENDER_BATCH_PIXELS = max(
        generator.INCREMENTAL_RENDER_BATCH_PIXELS,
        100_000,
    )
    generator.INCREMENTAL_RENDER_MAX_SCAN_PIXELS = max(
        generator.INCREMENTAL_RENDER_MAX_SCAN_PIXELS,
        25_000_000,
    )
    generator.TELEPORT_TARGET_MIN_ACTIONABLE_BLANK_PIXELS = min(
        generator.TELEPORT_TARGET_MIN_ACTIONABLE_BLANK_PIXELS,
        512,
    )

    _APPLIED = True
