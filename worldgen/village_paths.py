from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from math import dist, inf
from typing import Any, Iterable

import numpy as np

from .bedrock_chunks import ChunkDecodeError, decode_subchunk, iter_subchunk_records
from .config import WorldgenConfig, load_config
from .generator import BedrockWorldGenerator
from .modes import LAN_Y40, worldgen_mode
from . import render as render_mod


PATH_BLOCK_NAMES = frozenset((
    "dirt_path",
    "grass_path",
))
WATERLIKE_BLOCK_NAMES = frozenset((
    "water",
    "minecraft:water",
    "bubble_column",
    "minecraft:bubble_column",
    "kelp",
    "minecraft:kelp",
    "seagrass",
    "minecraft:seagrass",
    "tall_seagrass",
    "minecraft:tall_seagrass",
))
SEED_SNAP_RADIUS = 40
DEFAULT_SCAN_RADIUS = 224
SMALL_LOOP_WORLD_LENGTH = 18.0
RDP_WORLD_EPSILON = 4.0
MAX_SKELETON_DIMENSION = 160
PRUNE_BRANCH_PIXELS = 3
NODE_CLUSTER_RADIUS = 1

_SCAN_CACHE: dict[tuple[str, int, int, int], "SurfaceScan"] = {}


@dataclass(frozen=True, slots=True)
class DetectedVillageEdge:
    endpoint_a: tuple[int, int]
    endpoint_b: tuple[int, int]
    path_points: tuple[tuple[int, int], ...]
    is_pier: bool


@dataclass(frozen=True, slots=True)
class DetectedVillagePreview:
    stop_var: str
    node_coordinates: tuple[tuple[int, int], ...]
    edges: tuple[DetectedVillageEdge, ...]
    bounds: tuple[int, int, int, int]
    pier_node_coordinates: frozenset[tuple[int, int]]
    snapped_seed_points: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class SurfacePoint:
    x: int
    z: int
    y: int
    block_name: str


@dataclass(frozen=True, slots=True)
class SurfaceScan:
    mode_key: str
    center: tuple[int, int]
    radius: int
    surface_points: dict[tuple[int, int], SurfacePoint]


@dataclass(frozen=True, slots=True)
class UnknownRuntimeBlockGroup:
    block_name: str
    count: int
    coordinates: tuple[tuple[int, int], ...]


class PathDetectionError(RuntimeError):
    def __init__(self, message: str, *, scan: SurfaceScan, seed_points: list[tuple[int, int]]) -> None:
        super().__init__(message)
        self.scan = scan
        self.seed_points = seed_points


def infer_mode_key_from_render_payload(payload: dict[str, object]) -> str:
    render_style = str(payload.get("render_style", "surface") or "surface")
    fixed_y = payload.get("fixed_y")
    image_name = str(payload.get("image_path", "") or "").lower()
    if render_style == "fixed_y" or fixed_y is not None or "y40" in image_name:
        return LAN_Y40
    if "lan_surface" in image_name:
        return "lan_surface"
    return "local_seed_surface"


def build_preview_from_seeds(
    *,
    stop_var: str,
    stop_coordinates: tuple[int, int],
    seed_points: list[tuple[int, int]],
    render_payload: dict[str, object],
    config: WorldgenConfig | None = None,
    extra_path_block_names: Iterable[str] = (),
) -> DetectedVillagePreview:
    mode_key = infer_mode_key_from_render_payload(render_payload)
    if mode_key == LAN_Y40:
        raise RuntimeError("Village path detection only works from a surface render, not LAN Y=40.")

    if not seed_points:
        raise RuntimeError("Add a seed first.")

    scan_center = seed_points[0]
    active_config = config or load_config()
    scan = load_surface_scan(
        config=active_config,
        mode_key=mode_key,
        center=scan_center,
        radius=DEFAULT_SCAN_RADIUS,
    )
    path_points = _path_points_from_scan(scan, extra_path_block_names=extra_path_block_names)
    if not path_points:
        raise PathDetectionError(_no_path_blocks_message(scan, seed_points), scan=scan, seed_points=seed_points)

    union_component: set[tuple[int, int]] = set()
    snapped_seeds: list[tuple[int, int]] = []
    for seed_point in seed_points:
        snapped_seed = _nearest_seed_path(path_points, seed_point, max_distance=SEED_SNAP_RADIUS)
        if snapped_seed is None:
            continue
        snapped_seeds.append(snapped_seed)
        union_component.update(_connected_path_component(path_points, snapped_seed))

    if not union_component:
        raise RuntimeError("None of the provided seeds landed near a real village path block.")

    preview = _build_preview_from_component(
        stop_var=stop_var,
        stop_coordinates=stop_coordinates,
        component_points=union_component,
        surface_points=scan.surface_points,
        snapped_seed_points=tuple(dict.fromkeys(snapped_seeds)),
    )
    if preview is None:
        raise RuntimeError("Could not reduce the connected path network into usable centerlines.")
    return preview


def load_surface_scan(
    *,
    config: WorldgenConfig,
    mode_key: str,
    center: tuple[int, int],
    radius: int,
) -> SurfaceScan:
    cache_key = (mode_key, center[0], center[1], radius)
    cached = _SCAN_CACHE.get(cache_key)
    if cached is not None:
        return cached

    min_x = center[0] - radius
    max_x = center[0] + radius
    min_z = center[1] - radius
    max_z = center[1] + radius

    mode = worldgen_mode(mode_key)
    generator = BedrockWorldGenerator(config)
    mode_paths = generator.paths_for_mode(mode.key)

    min_chunk_x = min_x // 16
    max_chunk_x = max_x // 16
    min_chunk_z = min_z // 16
    max_chunk_z = max_z // 16

    persistent_records = ()
    if not mode.is_lan:
        world_path = generator._world_folder_for_coverage_scan()  # type: ignore[attr-defined]
        if world_path is not None and world_path.exists():
            persistent_records = tuple(
                iter_subchunk_records(
                    world_path,
                    min_chunk_x=min_chunk_x,
                    max_chunk_x=max_chunk_x,
                    min_chunk_z=min_chunk_z,
                    max_chunk_z=max_chunk_z,
                )
            )

    packet_records = render_mod._iter_cached_packet_subchunk_records(  # type: ignore[attr-defined]
        mode_paths.headless_chunk_packet_path,
        min_chunk_x=min_chunk_x,
        max_chunk_x=max_chunk_x,
        min_chunk_z=min_chunk_z,
        max_chunk_z=max_chunk_z,
    )

    if persistent_records and packet_records:
        packet_records = render_mod._filter_packet_records_against_persistent_columns(  # type: ignore[attr-defined]
            packet_records,
            persistent_records=persistent_records,
        )

    records = sorted(
        (*persistent_records, *packet_records),
        key=lambda record: (
            record.subchunk_y,
            1 if not record.uses_runtime_palette else 0,
            record.chunk_z,
            record.chunk_x,
        ),
        reverse=True,
    )
    if not records:
        raise RuntimeError("No chunk data is available for this area yet. Load/render that village area first.")

    surface_points: dict[tuple[int, int], SurfacePoint] = {}
    for record in records:
        try:
            subchunk = decode_subchunk(record)
        except ChunkDecodeError:
            continue
        _collect_surface_points(
            surface_points,
            subchunk,
            min_x=min_x,
            max_x=max_x,
            min_z=min_z,
            max_z=max_z,
        )

    if not surface_points:
        raise RuntimeError("Chunk data was found, but no visible surface blocks were resolved in this area.")

    scan = SurfaceScan(
        mode_key=mode.key,
        center=center,
        radius=radius,
        surface_points=surface_points,
    )
    _SCAN_CACHE[cache_key] = scan
    return scan


def _collect_surface_points(
    surface_points: dict[tuple[int, int], SurfacePoint],
    subchunk: Any,
    *,
    min_x: int,
    max_x: int,
    min_z: int,
    max_z: int,
) -> None:
    for local_z in range(16):
        world_z = (subchunk.chunk_z * 16) + local_z
        if world_z < min_z or world_z > max_z:
            continue
        for local_x in range(16):
            world_x = (subchunk.chunk_x * 16) + local_x
            if world_x < min_x or world_x > max_x:
                continue
            world_key = (world_x, world_z)
            if world_key in surface_points:
                continue
            for local_y in range(15, -1, -1):
                block_info = subchunk.visible_block_info(local_x, local_y, local_z)
                if block_info is None:
                    continue
                render_block_name = render_mod._resolve_block_name_for_render(block_info.name)  # type: ignore[attr-defined]
                block_y = subchunk.min_y + local_y
                if render_mod._is_chunk_touch_marker(render_block_name, block_y):  # type: ignore[attr-defined]
                    continue
                if render_mod._is_non_rendering_block(render_block_name):  # type: ignore[attr-defined]
                    continue
                surface_points[world_key] = SurfacePoint(
                    x=world_x,
                    z=world_z,
                    y=block_y,
                    block_name=block_info.name,
                )
                break


def _normalized_block_name(block_name: str) -> str:
    return block_name.strip().lower().removeprefix("minecraft:")


def _is_path_block(block_name: str, *, extra_path_block_names: Iterable[str] = ()) -> bool:
    normalized = _normalized_block_name(block_name)
    extra_names = {_normalized_block_name(name) for name in extra_path_block_names}
    if normalized in extra_names:
        return True
    if _normalized_block_name(block_name) in PATH_BLOCK_NAMES:
        return True
    render_block_name = render_mod._resolve_block_name_for_render(block_name)  # type: ignore[attr-defined]
    return _normalized_block_name(render_block_name) in PATH_BLOCK_NAMES or _normalized_block_name(render_block_name) in extra_names


def _path_points_from_scan(
    scan: SurfaceScan,
    *,
    extra_path_block_names: Iterable[str] = (),
) -> set[tuple[int, int]]:
    return {
        coordinates
        for coordinates, surface_point in scan.surface_points.items()
        if _is_path_block(surface_point.block_name, extra_path_block_names=extra_path_block_names)
    }


def unknown_runtime_block_groups(
    scan: SurfaceScan,
    *,
    focus_points: Iterable[tuple[int, int]] = (),
    focus_radius: int | None = None,
) -> tuple[UnknownRuntimeBlockGroup, ...]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    focus_point_tuple = tuple(focus_points)
    focused_grouped: dict[str, list[tuple[int, int]]] = {}
    for coordinates, surface_point in scan.surface_points.items():
        normalized = _normalized_block_name(surface_point.block_name)
        if not normalized.startswith("unknown_runtime_"):
            continue
        grouped.setdefault(surface_point.block_name, []).append(coordinates)
        if focus_point_tuple and focus_radius is not None:
            nearest_distance = min(dist(coordinates, focus_point) for focus_point in focus_point_tuple)
            if nearest_distance <= focus_radius:
                focused_grouped.setdefault(surface_point.block_name, []).append(coordinates)

    active_grouped = focused_grouped or grouped

    def nearest_focus_distance(coordinates: list[tuple[int, int]]) -> float:
        if not focus_point_tuple:
            return inf
        return min(dist(coordinate, focus_point) for coordinate in coordinates for focus_point in focus_point_tuple)

    return tuple(
        UnknownRuntimeBlockGroup(
            block_name=block_name,
            count=len(coordinates),
            coordinates=tuple(sorted(coordinates)),
        )
        for block_name, coordinates in sorted(
            active_grouped.items(),
            key=lambda item: (
                nearest_focus_distance(item[1]),
                -len(item[1]),
                item[0],
            ),
        )
    )


def _block_name_summary(scan: SurfaceScan, *, limit: int = 8) -> str:
    counts = Counter(_normalized_block_name(point.block_name) for point in scan.surface_points.values())
    if not counts:
        return "none"
    return ", ".join(f"{name} ({count})" for name, count in counts.most_common(limit))


def _seed_block_summary(scan: SurfaceScan, seed_points: list[tuple[int, int]]) -> str:
    summaries = []
    for seed_x, seed_z in seed_points[:4]:
        surface_point = scan.surface_points.get((seed_x, seed_z))
        if surface_point is None:
            block_name = f"not loaded; chunk {seed_x // 16},{seed_z // 16} is missing from the scan cache"
        else:
            block_name = surface_point.block_name
        summaries.append(f"({seed_x}, {seed_z})={block_name}")
    if not summaries:
        return "no seeds"
    return ", ".join(summaries)


def _loaded_bounds_summary(scan: SurfaceScan) -> str:
    if not scan.surface_points:
        return "no loaded surface columns"
    xs = [point[0] for point in scan.surface_points]
    zs = [point[1] for point in scan.surface_points]
    return f"x {min(xs)}..{max(xs)}, z {min(zs)}..{max(zs)}"


def _no_path_blocks_message(scan: SurfaceScan, seed_points: list[tuple[int, int]]) -> str:
    return (
        "No Dirt Path blocks were found in the scanned village area. "
        "Bedrock may report the Dirt Path block as minecraft:grass_path; that name is accepted. "
        f"Scanned center {scan.center} with radius {scan.radius}. "
        f"Loaded surface columns: {_loaded_bounds_summary(scan)}. "
        f"Seed blocks: {_seed_block_summary(scan, seed_points)}. "
        f"Most common scanned blocks: {_block_name_summary(scan)}."
    )


def _is_waterlike(block_name: str) -> bool:
    normalized = block_name.lower()
    if normalized in WATERLIKE_BLOCK_NAMES:
        return True
    return (
        "water" in normalized
        or "kelp" in normalized
        or "seagrass" in normalized
        or normalized == "bubble_column"
    )


def _nearest_seed_path(
    path_points: set[tuple[int, int]],
    seed_coordinates: tuple[int, int],
    *,
    max_distance: int,
) -> tuple[int, int] | None:
    best_point = None
    best_distance = None
    for point in path_points:
        point_distance = dist(point, seed_coordinates)
        if point_distance > max_distance:
            continue
        if best_distance is None or point_distance < best_distance:
            best_distance = point_distance
            best_point = point
    return best_point


def _path_neighbors(point: tuple[int, int], path_points: set[tuple[int, int]]) -> list[tuple[int, int]]:
    world_x, world_z = point
    neighbors = []
    for neighbor in (
        (world_x + 1, world_z),
        (world_x - 1, world_z),
        (world_x, world_z + 1),
        (world_x, world_z - 1),
    ):
        if neighbor in path_points:
            neighbors.append(neighbor)
    return neighbors


def _connected_path_component(
    path_points: set[tuple[int, int]],
    seed: tuple[int, int],
) -> set[tuple[int, int]]:
    queue = deque([seed])
    seen = {seed}
    component: set[tuple[int, int]] = set()
    while queue:
        point = queue.popleft()
        component.add(point)
        for neighbor in _path_neighbors(point, path_points):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append(neighbor)
    return component


def _downsample_mask(mask: np.ndarray) -> tuple[np.ndarray, int]:
    height, width = mask.shape
    max_dimension = max(height, width)
    if max_dimension <= MAX_SKELETON_DIMENSION:
        return mask.astype(bool), 1

    scale = max(1, int(np.ceil(max_dimension / MAX_SKELETON_DIMENSION)))
    target_height = max(1, int(np.ceil(height / scale)))
    target_width = max(1, int(np.ceil(width / scale)))
    reduced = np.zeros((target_height, target_width), dtype=bool)
    for target_y in range(target_height):
        source_y0 = target_y * scale
        source_y1 = min(height, source_y0 + scale)
        for target_x in range(target_width):
            source_x0 = target_x * scale
            source_x1 = min(width, source_x0 + scale)
            if np.any(mask[source_y0:source_y1, source_x0:source_x1]):
                reduced[target_y, target_x] = True
    return reduced, scale


def _zhang_suen_thinning(mask: np.ndarray) -> np.ndarray:
    image = mask.astype(np.uint8).copy()
    if image.size == 0:
        return image.astype(bool)

    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            points_to_remove: list[tuple[int, int]] = []
            height, width = image.shape
            for pixel_y in range(1, height - 1):
                row_above = image[pixel_y - 1]
                row_here = image[pixel_y]
                row_below = image[pixel_y + 1]
                for pixel_x in range(1, width - 1):
                    if row_here[pixel_x] != 1:
                        continue
                    p2 = row_above[pixel_x]
                    p3 = row_above[pixel_x + 1]
                    p4 = row_here[pixel_x + 1]
                    p5 = row_below[pixel_x + 1]
                    p6 = row_below[pixel_x]
                    p7 = row_below[pixel_x - 1]
                    p8 = row_here[pixel_x - 1]
                    p9 = row_above[pixel_x - 1]
                    neighbors = [p2, p3, p4, p5, p6, p7, p8, p9]
                    transitions = sum(
                        1
                        for first_value, second_value in zip(neighbors, neighbors[1:] + neighbors[:1])
                        if first_value == 0 and second_value == 1
                    )
                    neighbor_count = int(sum(neighbors))
                    if neighbor_count < 2 or neighbor_count > 6:
                        continue
                    if transitions != 1:
                        continue
                    if step == 0:
                        if p2 * p4 * p6 != 0:
                            continue
                        if p4 * p6 * p8 != 0:
                            continue
                    else:
                        if p2 * p4 * p8 != 0:
                            continue
                        if p2 * p6 * p8 != 0:
                            continue
                    points_to_remove.append((pixel_y, pixel_x))
            if points_to_remove:
                changed = True
                for pixel_y, pixel_x in points_to_remove:
                    image[pixel_y, pixel_x] = 0
    return image.astype(bool)


def _local_neighbors(mask: np.ndarray, pixel: tuple[int, int]) -> list[tuple[int, int]]:
    pixel_x, pixel_y = pixel
    neighbors = []
    height, width = mask.shape
    for neighbor_x, neighbor_y in (
        (pixel_x + 1, pixel_y),
        (pixel_x - 1, pixel_y),
        (pixel_x, pixel_y + 1),
        (pixel_x, pixel_y - 1),
    ):
        if 0 <= neighbor_x < width and 0 <= neighbor_y < height and mask[neighbor_y, neighbor_x]:
            neighbors.append((neighbor_x, neighbor_y))
    return neighbors


def _global_neighbors(skeleton_points: set[tuple[int, int]], pixel: tuple[int, int]) -> list[tuple[int, int]]:
    pixel_x, pixel_y = pixel
    neighbors = []
    for neighbor in (
        (pixel_x + 1, pixel_y),
        (pixel_x - 1, pixel_y),
        (pixel_x, pixel_y + 1),
        (pixel_x, pixel_y - 1),
    ):
        if neighbor in skeleton_points:
            neighbors.append(neighbor)
    return neighbors


def _prune_skeleton(mask: np.ndarray, *, anchor: tuple[int, int]) -> np.ndarray:
    pruned = mask.copy()
    changed = True
    while changed:
        changed = False
        endpoints: list[tuple[int, int]] = []
        height, width = pruned.shape
        for pixel_y in range(height):
            for pixel_x in range(width):
                if not pruned[pixel_y, pixel_x]:
                    continue
                pixel = (pixel_x, pixel_y)
                if pixel == anchor:
                    continue
                if len(_local_neighbors(pruned, pixel)) <= 1:
                    endpoints.append(pixel)
        for endpoint in endpoints:
            chain = [endpoint]
            previous = None
            current = endpoint
            while True:
                neighbors = [neighbor for neighbor in _local_neighbors(pruned, current) if neighbor != previous]
                if not neighbors:
                    break
                next_pixel = neighbors[0]
                previous, current = current, next_pixel
                chain.append(current)
                if current == anchor:
                    break
                if len(_local_neighbors(pruned, current)) != 2:
                    break
            if len(chain) - 1 > PRUNE_BRANCH_PIXELS or chain[-1] == anchor:
                continue
            for pixel_x, pixel_y in chain[:-1]:
                if (pixel_x, pixel_y) != anchor and pruned[pixel_y, pixel_x]:
                    pruned[pixel_y, pixel_x] = False
                    changed = True
    return pruned


def _cluster_node_pixels(node_pixels: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    remaining = set(node_pixels)
    clusters: list[set[tuple[int, int]]] = []
    while remaining:
        seed = remaining.pop()
        cluster = {seed}
        stack = [seed]
        while stack:
            current_x, current_y = stack.pop()
            matches = [
                candidate
                for candidate in list(remaining)
                if max(abs(candidate[0] - current_x), abs(candidate[1] - current_y)) <= NODE_CLUSTER_RADIUS
            ]
            for candidate in matches:
                remaining.remove(candidate)
                cluster.add(candidate)
                stack.append(candidate)
        clusters.append(cluster)
    return clusters


def _representative_pixel(cluster: set[tuple[int, int]]) -> tuple[int, int]:
    avg_x = sum(pixel_x for pixel_x, _pixel_y in cluster) / len(cluster)
    avg_y = sum(pixel_y for _pixel_x, pixel_y in cluster) / len(cluster)
    return min(cluster, key=lambda pixel: abs(pixel[0] - avg_x) + abs(pixel[1] - avg_y))


def _point_line_distance(point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]) -> float:
    if start == end:
        return dist(point, start)
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    t = ((px - sx) * dx + (py - sy) * dy) / float((dx * dx) + (dy * dy))
    t = max(0.0, min(1.0, t))
    projection = (sx + (t * dx), sy + (t * dy))
    return ((px - projection[0]) ** 2 + (py - projection[1]) ** 2) ** 0.5


def _rdp(points: list[tuple[int, int]], epsilon: float) -> list[tuple[int, int]]:
    if len(points) <= 2:
        return points[:]
    start = points[0]
    end = points[-1]
    max_distance = -1.0
    max_index = -1
    for index in range(1, len(points) - 1):
        distance = _point_line_distance(points[index], start, end)
        if distance > max_distance:
            max_distance = distance
            max_index = index
    if max_distance <= epsilon:
        return [start, end]
    left = _rdp(points[: max_index + 1], epsilon)
    right = _rdp(points[max_index:], epsilon)
    return left[:-1] + right


def _reduced_to_world_point(
    reduced_pixel: tuple[int, int],
    *,
    min_x: int,
    min_z: int,
    scale: int,
) -> tuple[int, int]:
    return (
        min_x + (reduced_pixel[0] * scale),
        min_z + (reduced_pixel[1] * scale),
    )


def _point_is_over_water(
    point: tuple[int, int],
    surface_points: dict[tuple[int, int], SurfacePoint],
) -> bool:
    water_neighbors = 0
    land_neighbors = 0
    point_x, point_z = point
    for neighbor in (
        (point_x + 1, point_z),
        (point_x - 1, point_z),
        (point_x, point_z + 1),
        (point_x, point_z - 1),
    ):
        surface_point = surface_points.get(neighbor)
        if surface_point is None:
            continue
        if _is_path_block(surface_point.block_name):
            continue
        if _is_waterlike(surface_point.block_name):
            water_neighbors += 1
        else:
            land_neighbors += 1
    return water_neighbors >= 2 and land_neighbors == 0


def _edge_is_pier(
    world_points: list[tuple[int, int]],
    surface_points: dict[tuple[int, int], SurfacePoint],
    endpoint_a: tuple[int, int],
    endpoint_b: tuple[int, int],
) -> tuple[bool, set[tuple[int, int]]]:
    if len(world_points) < 2:
        return (False, set())

    over_water_flags = [_point_is_over_water(point, surface_points) for point in world_points]

    def tail_over_water(from_start: bool) -> bool:
        sequence = over_water_flags if from_start else list(reversed(over_water_flags))
        tail_length = max(2, min(6, len(sequence) // 3 or 2))
        tail = sequence[:tail_length]
        return sum(1 for value in tail if value) >= max(2, len(tail) - 1)

    start_pier = tail_over_water(True)
    end_pier = tail_over_water(False)
    if not start_pier and not end_pier:
        return (False, set())

    pier_nodes: set[tuple[int, int]] = set()
    if start_pier:
        pier_nodes.add(endpoint_a)
    if end_pier:
        pier_nodes.add(endpoint_b)
    return (True, pier_nodes)


def _build_preview_from_component(
    *,
    stop_var: str,
    stop_coordinates: tuple[int, int],
    component_points: set[tuple[int, int]],
    surface_points: dict[tuple[int, int], SurfacePoint],
    snapped_seed_points: tuple[tuple[int, int], ...],
) -> DetectedVillagePreview | None:
    xs = [world_x for world_x, _world_z in component_points]
    zs = [world_z for _world_x, world_z in component_points]
    min_x = min(xs)
    max_x = max(xs)
    min_z = min(zs)
    max_z = max(zs)

    width = max_x - min_x + 1
    height = max_z - min_z + 1
    mask = np.zeros((height, width), dtype=bool)
    for world_x, world_z in component_points:
        mask[world_z - min_z, world_x - min_x] = True

    reduced_mask, scale = _downsample_mask(mask)
    if not reduced_mask.any():
        return None

    skeleton = _zhang_suen_thinning(reduced_mask)
    if not skeleton.any():
        return None

    stop_reduced = (
        int(np.clip(round((stop_coordinates[0] - min_x) / scale), 0, skeleton.shape[1] - 1)),
        int(np.clip(round((stop_coordinates[1] - min_z) / scale), 0, skeleton.shape[0] - 1)),
    )
    reduced_skeleton_points = [
        (pixel_x, pixel_y)
        for pixel_y, pixel_x in np.argwhere(skeleton)
    ]
    anchor = min(
        reduced_skeleton_points,
        key=lambda pixel: ((pixel[0] - stop_reduced[0]) ** 2) + ((pixel[1] - stop_reduced[1]) ** 2),
    )
    skeleton = _prune_skeleton(skeleton, anchor=anchor)
    reduced_skeleton_points = [
        (pixel_x, pixel_y)
        for pixel_y, pixel_x in np.argwhere(skeleton)
    ]
    if not reduced_skeleton_points:
        return None

    skeleton_set = set(reduced_skeleton_points)
    node_pixels = {
        pixel
        for pixel in skeleton_set
        if len(_global_neighbors(skeleton_set, pixel)) != 2
    }
    node_pixels.add(anchor)

    clusters = _cluster_node_pixels(node_pixels)
    representative_by_pixel = {}
    representative_nodes = []
    for cluster in clusters:
        representative = _representative_pixel(cluster)
        representative_nodes.append(representative)
        for pixel in cluster:
            representative_by_pixel[pixel] = representative

    node_set = set(representative_nodes)
    edge_map: dict[tuple[tuple[int, int], tuple[int, int]], list[tuple[int, int]]] = {}
    visited_segments: set[tuple[tuple[int, int], tuple[int, int]]] = set()

    for node_pixel in sorted(node_set):
        for neighbor_pixel in _global_neighbors(skeleton_set, node_pixel):
            segment_endpoints = sorted((node_pixel, neighbor_pixel))
            segment_key = (segment_endpoints[0], segment_endpoints[1])
            if segment_key in visited_segments:
                continue
            visited_segments.add(segment_key)
            path = [node_pixel, neighbor_pixel]
            previous = node_pixel
            current = neighbor_pixel
            while current not in node_set:
                neighbors = [neighbor for neighbor in _global_neighbors(skeleton_set, current) if neighbor != previous]
                if not neighbors:
                    break
                next_pixel = neighbors[0]
                next_segment_endpoints = sorted((current, next_pixel))
                visited_segments.add((next_segment_endpoints[0], next_segment_endpoints[1]))
                path.append(next_pixel)
                previous, current = current, next_pixel

            endpoint_a = representative_by_pixel.get(path[0], path[0])
            endpoint_b = representative_by_pixel.get(path[-1], path[-1])
            if endpoint_a == endpoint_b:
                continue

            normalized_endpoints = sorted((endpoint_a, endpoint_b))
            normalized_key = (normalized_endpoints[0], normalized_endpoints[1])
            if normalized_key in edge_map:
                if len(path) < len(edge_map[normalized_key]):
                    edge_map[normalized_key] = path
            else:
                edge_map[normalized_key] = path

    if not edge_map:
        return None

    node_degree: dict[tuple[int, int], int] = {}
    for endpoint_a, endpoint_b in edge_map:
        node_degree[endpoint_a] = node_degree.get(endpoint_a, 0) + 1
        node_degree[endpoint_b] = node_degree.get(endpoint_b, 0) + 1

    edges: list[DetectedVillageEdge] = []
    node_coordinates: set[tuple[int, int]] = set()
    pier_nodes: set[tuple[int, int]] = set()
    point_xs: list[int] = []
    point_zs: list[int] = []

    for endpoint_a, endpoint_b in sorted(edge_map):
        reduced_path = edge_map[(endpoint_a, endpoint_b)]
        world_points = [
            _reduced_to_world_point(
                reduced_pixel,
                min_x=min_x,
                min_z=min_z,
                scale=scale,
            )
            for reduced_pixel in reduced_path
        ]
        simplified_points = _rdp(world_points, RDP_WORLD_EPSILON)
        simplified_points = [world_points[0], *simplified_points[1:-1], world_points[-1]] if len(simplified_points) >= 2 else world_points
        deduped_points = []
        for point in simplified_points:
            if deduped_points and deduped_points[-1] == point:
                continue
            deduped_points.append(point)
        if len(deduped_points) < 2:
            continue

        endpoint_a_world = deduped_points[0]
        endpoint_b_world = deduped_points[-1]
        length = sum(dist(first_point, second_point) for first_point, second_point in zip(deduped_points, deduped_points[1:]))
        if length < SMALL_LOOP_WORLD_LENGTH and node_degree.get(endpoint_a, 0) >= 2 and node_degree.get(endpoint_b, 0) >= 2:
            continue

        is_pier, edge_pier_nodes = _edge_is_pier(
            deduped_points,
            surface_points,
            endpoint_a_world,
            endpoint_b_world,
        )

        node_coordinates.add(endpoint_a_world)
        node_coordinates.add(endpoint_b_world)
        pier_nodes.update(edge_pier_nodes)
        for point_x, point_z in deduped_points:
            point_xs.append(point_x)
            point_zs.append(point_z)

        edges.append(
            DetectedVillageEdge(
                endpoint_a=endpoint_a_world,
                endpoint_b=endpoint_b_world,
                path_points=tuple(deduped_points),
                is_pier=is_pier,
            )
        )

    if not edges:
        return None

    padding = 16
    bounds = (
        min(point_xs) - padding,
        max(point_xs) + padding,
        min(point_zs) - padding,
        max(point_zs) + padding,
    )
    return DetectedVillagePreview(
        stop_var=stop_var,
        node_coordinates=tuple(sorted(node_coordinates)),
        edges=tuple(edges),
        bounds=bounds,
        pier_node_coordinates=frozenset(pier_nodes),
        snapped_seed_points=snapped_seed_points,
    )
