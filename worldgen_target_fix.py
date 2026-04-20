from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path
import random

_APPLIED = False

_ORIGINAL_NEXT_UNDERCOVERED = None
_ORIGINAL_RENDER_AREA_TELEPORT_POINTS = None


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
        components.append(
            _BlankChunkComponent(
                chunk_counts=component_chunk_counts,
                total_blank_pixels=total_blank_pixels,
                min_chunk_x=min(chunk_x for chunk_x, _chunk_z in component_chunk_counts),
                max_chunk_x=max(chunk_x for chunk_x, _chunk_z in component_chunk_counts),
                min_chunk_z=min(chunk_z for _chunk_x, chunk_z in component_chunk_counts),
                max_chunk_z=max(chunk_z for _chunk_x, chunk_z in component_chunk_counts),
                centroid_chunk_x=weighted_x / max(1, total_blank_pixels),
                centroid_chunk_z=weighted_z / max(1, total_blank_pixels),
                is_internal=_component_is_internal(
                    component_chunk_counts,
                    config=config,
                    metadata=metadata,
                ),
            )
        )

    components.sort(
        key=lambda component: (
            0 if component.is_internal else 1,
            -component.total_blank_pixels,
            component.min_chunk_z,
            component.min_chunk_x,
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


def _coast_candidate_centers(config, component: _BlankChunkComponent) -> list[tuple[int, int]]:
    radius = config.headless_loader.chunk_radius
    component_chunks = set(component.chunk_counts)
    candidates: list[tuple[int, int]] = []

    for chunk_x, chunk_z in component_chunks:
        if (chunk_x - 1, chunk_z) not in component_chunks:
            candidates.append((chunk_x - 1 + radius, chunk_z))
        if (chunk_x + 1, chunk_z) not in component_chunks:
            candidates.append((chunk_x + 1 - radius, chunk_z))
        if (chunk_x, chunk_z - 1) not in component_chunks:
            candidates.append((chunk_x, chunk_z - 1 + radius))
        if (chunk_x, chunk_z + 1) not in component_chunks:
            candidates.append((chunk_x, chunk_z + 1 - radius))

    deduped: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for candidate in candidates:
        clamped = _clamp_chunk_center(config, candidate)
        if clamped in seen:
            continue
        seen.add(clamped)
        deduped.append(clamped)
    return deduped


def _component_target(config, component: _BlankChunkComponent) -> tuple[int, int]:
    coast_candidates = _coast_candidate_centers(config, component)
    if coast_candidates:
        seed_value = hash((
            config.render.min_x,
            config.render.max_x,
            config.render.min_z,
            config.render.max_z,
            round(component.centroid_chunk_x, 3),
            round(component.centroid_chunk_z, 3),
            component.total_blank_pixels,
        ))
        rng = random.Random(seed_value)
        return coast_candidates[rng.randrange(len(coast_candidates))]

    dense_chunk = max(
        component.chunk_counts.items(),
        key=lambda item: (
            item[1],
            -((item[0][0] - component.centroid_chunk_x) ** 2 + (item[0][1] - component.centroid_chunk_z) ** 2),
        ),
    )[0]
    return _clamp_chunk_center(config, dense_chunk)


def _promoted_largest_targets(config, blank_coverage) -> tuple[tuple[int, int], ...]:
    if blank_coverage is None:
        return ()

    import worldgen.generator as generator

    targets: list[tuple[int, int]] = []
    seen_targets: set[tuple[int, int]] = set()
    for component in _blank_chunk_components(config, blank_coverage):
        target = generator._chunk_center_world_pair(_component_target(config, component))
        if target in seen_targets:
            continue
        seen_targets.add(target)
        targets.append(target)
    return tuple(targets)


def _largest_first_render_area_teleport_points(
    config,
    *,
    world_path=None,
    blank_coverage=None,
):
    original_points = _ORIGINAL_RENDER_AREA_TELEPORT_POINTS(
        config,
        world_path=world_path,
        blank_coverage=blank_coverage,
    )
    if blank_coverage is None:
        return original_points

    promoted_points = _promoted_largest_targets(config, blank_coverage)
    if not promoted_points:
        return original_points

    result: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for point in promoted_points + original_points:
        if point in seen:
            continue
        seen.add(point)
        result.append(point)
    return tuple(result)


def _largest_first_next_undercovered_teleport_index(
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
        promoted_points = _promoted_largest_targets(config, blank_coverage)

        for promoted_point in promoted_points:
            if promoted_point not in teleport_points:
                continue
            missing_pixels = generator._teleport_point_missing_pixel_count(
                config,
                promoted_point,
                blank_coverage,
            )
            if missing_pixels > 0:
                return teleport_points.index(promoted_point)

        first_actionable = None
        first_positive = None
        for offset in range(len(teleport_points)):
            index = (normalized_start_index + offset) % len(teleport_points)
            point = teleport_points[index]
            missing_pixels = generator._teleport_point_missing_pixel_count(
                config,
                point,
                blank_coverage,
            )
            if missing_pixels > generator.TELEPORT_TARGET_MIN_ACTIONABLE_BLANK_PIXELS:
                first_actionable = index
                break
            if missing_pixels > 0 and first_positive is None:
                first_positive = index

        if first_actionable is not None:
            return first_actionable
        if first_positive is not None:
            return first_positive
        return normalized_start_index

    return _ORIGINAL_NEXT_UNDERCOVERED(
        config,
        teleport_points,
        start_index=start_index,
        world_path=world_path,
        blank_coverage=blank_coverage,
    )


def apply() -> None:
    global _APPLIED
    global _ORIGINAL_NEXT_UNDERCOVERED
    global _ORIGINAL_RENDER_AREA_TELEPORT_POINTS

    if _APPLIED:
        return

    import worldgen.generator as generator

    _ORIGINAL_NEXT_UNDERCOVERED = generator._next_undercovered_teleport_index
    _ORIGINAL_RENDER_AREA_TELEPORT_POINTS = generator._render_area_teleport_points

    generator._render_area_teleport_points = _largest_first_render_area_teleport_points
    generator._next_undercovered_teleport_index = _largest_first_next_undercovered_teleport_index

    _APPLIED = True
