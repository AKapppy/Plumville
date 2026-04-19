from __future__ import annotations

from dataclasses import dataclass
import heapq
from math import dist, hypot
from typing import Iterable

from PIL import Image


ANCHOR_NODE_MAX_DISTANCE = 96.0
MAX_GRID_DIMENSION = 180
WATER_COST_MULTIPLIER = 10.0
NEAR_WATER_COST_MULTIPLIER = 1.75
OUTSIDE_RENDER_SEARCH_RADIUS = 4
COMPONENT_PAIR_CANDIDATES = 8


@dataclass(frozen=True, slots=True)
class SuggestedSegment:
    start_coordinates: tuple[int, int]
    end_coordinates: tuple[int, int]
    start_key: str
    end_key: str
    start_label: str
    end_label: str
    length: float
    cost: float
    path_coordinates: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class _RouteCandidate:
    cost: float
    first_key: str
    second_key: str
    first_component: int
    second_component: int
    path_coordinates: tuple[tuple[int, int], ...]


_CACHE_KEY: tuple[object, ...] | None = None
_CACHE_VALUE: tuple[SuggestedSegment, ...] = ()


class TerrainGrid:
    def __init__(
        self,
        *,
        min_x: int,
        max_x: int,
        min_z: int,
        max_z: int,
        image: Image.Image,
    ) -> None:
        self.min_x = min_x
        self.max_x = max_x
        self.min_z = min_z
        self.max_z = max_z
        self.image = image.convert("RGBA")
        self.image_width, self.image_height = self.image.size
        self.step_px = max(1, round(max(self.image_width, self.image_height) / MAX_GRID_DIMENSION))
        self.grid_width = max(1, (self.image_width + self.step_px - 1) // self.step_px)
        self.grid_height = max(1, (self.image_height + self.step_px - 1) // self.step_px)
        self.rendered: list[list[bool]] = [[False] * self.grid_width for _ in range(self.grid_height)]
        self.water: list[list[bool]] = [[False] * self.grid_width for _ in range(self.grid_height)]
        self.land_component: list[list[int]] = [[-1] * self.grid_width for _ in range(self.grid_height)]
        self._populate_grid()
        self._label_land_components()

    @property
    def signature(self) -> tuple[object, ...]:
        return (
            self.min_x,
            self.max_x,
            self.min_z,
            self.max_z,
            self.image_width,
            self.image_height,
            self.step_px,
        )

    def _populate_grid(self) -> None:
        pixels = self.image.load()
        if pixels is None:
            return

        for grid_y in range(self.grid_height):
            px_top = grid_y * self.step_px
            px_bottom = min(self.image_height, px_top + self.step_px)
            for grid_x in range(self.grid_width):
                px_left = grid_x * self.step_px
                px_right = min(self.image_width, px_left + self.step_px)

                total_alpha = 0
                total_red = 0
                total_green = 0
                total_blue = 0
                sample_count = 0

                for py in range(px_top, px_bottom):
                    for px in range(px_left, px_right):
                        red, green, blue, alpha = pixels[px, py]
                        total_alpha += alpha
                        total_red += red
                        total_green += green
                        total_blue += blue
                        sample_count += 1

                if sample_count <= 0:
                    continue

                avg_alpha = total_alpha / sample_count
                if avg_alpha <= 8:
                    continue

                avg_red = total_red / sample_count
                avg_green = total_green / sample_count
                avg_blue = total_blue / sample_count
                self.rendered[grid_y][grid_x] = True
                self.water[grid_y][grid_x] = _looks_like_water(avg_red, avg_green, avg_blue)

    def _label_land_components(self) -> None:
        next_component = 0
        for grid_y in range(self.grid_height):
            for grid_x in range(self.grid_width):
                if not self.rendered[grid_y][grid_x] or self.water[grid_y][grid_x]:
                    continue
                if self.land_component[grid_y][grid_x] >= 0:
                    continue
                stack = [(grid_x, grid_y)]
                self.land_component[grid_y][grid_x] = next_component
                while stack:
                    current_x, current_y = stack.pop()
                    for neighbor_x, neighbor_y in _neighbors8(current_x, current_y):
                        if not self._in_bounds((neighbor_x, neighbor_y)):
                            continue
                        if not self.rendered[neighbor_y][neighbor_x] or self.water[neighbor_y][neighbor_x]:
                            continue
                        if self.land_component[neighbor_y][neighbor_x] >= 0:
                            continue
                        self.land_component[neighbor_y][neighbor_x] = next_component
                        stack.append((neighbor_x, neighbor_y))
                next_component += 1

    def _world_to_grid(self, coordinates: tuple[int, int]) -> tuple[int, int]:
        world_x, world_z = coordinates
        x_ratio = 0.0 if self.max_x == self.min_x else (world_x - self.min_x) / (self.max_x - self.min_x)
        z_ratio = 0.0 if self.max_z == self.min_z else (world_z - self.min_z) / (self.max_z - self.min_z)
        grid_x = round(_clamp(x_ratio, 0.0, 1.0) * max(0, self.grid_width - 1))
        grid_y = round(_clamp(z_ratio, 0.0, 1.0) * max(0, self.grid_height - 1))
        return (grid_x, grid_y)

    def _grid_to_world(self, grid_point: tuple[int, int]) -> tuple[int, int]:
        grid_x, grid_y = grid_point
        x_ratio = 0.0 if self.grid_width <= 1 else grid_x / (self.grid_width - 1)
        z_ratio = 0.0 if self.grid_height <= 1 else grid_y / (self.grid_height - 1)
        world_x = round(self.min_x + ((self.max_x - self.min_x) * x_ratio))
        world_z = round(self.min_z + ((self.max_z - self.min_z) * z_ratio))
        return (world_x, world_z)

    def _in_bounds(self, grid_point: tuple[int, int]) -> bool:
        grid_x, grid_y = grid_point
        return 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height

    def _is_rendered(self, grid_point: tuple[int, int]) -> bool:
        grid_x, grid_y = grid_point
        return self.rendered[grid_y][grid_x]

    def _is_water(self, grid_point: tuple[int, int]) -> bool:
        grid_x, grid_y = grid_point
        return self.water[grid_y][grid_x]

    def _land_component_id(self, grid_point: tuple[int, int]) -> int | None:
        grid_x, grid_y = grid_point
        value = self.land_component[grid_y][grid_x]
        return None if value < 0 else value

    def _is_near_water(self, grid_point: tuple[int, int]) -> bool:
        grid_x, grid_y = grid_point
        for delta_y in (-1, 0, 1):
            for delta_x in (-1, 0, 1):
                if delta_x == 0 and delta_y == 0:
                    continue
                neighbor = (grid_x + delta_x, grid_y + delta_y)
                if not self._in_bounds(neighbor):
                    continue
                if self._is_water(neighbor):
                    return True
        return False

    def snap_world_point(self, coordinates: tuple[int, int]) -> tuple[int, int] | None:
        start_point = self._world_to_grid(coordinates)
        best_land_point = None
        best_land_score = None
        best_water_point = None
        best_water_score = None

        for radius in range(OUTSIDE_RENDER_SEARCH_RADIUS + 1):
            for grid_y in range(start_point[1] - radius, start_point[1] + radius + 1):
                for grid_x in range(start_point[0] - radius, start_point[0] + radius + 1):
                    candidate = (grid_x, grid_y)
                    if not self._in_bounds(candidate):
                        continue
                    if not self._is_rendered(candidate):
                        continue
                    world_candidate = self._grid_to_world(candidate)
                    candidate_distance = hypot(
                        world_candidate[0] - coordinates[0],
                        world_candidate[1] - coordinates[1],
                    )
                    score = (radius, candidate_distance)
                    if self._is_water(candidate):
                        if best_water_score is None or score < best_water_score:
                            best_water_score = score
                            best_water_point = candidate
                        continue
                    if best_land_score is None or score < best_land_score:
                        best_land_score = score
                        best_land_point = candidate
            if best_land_point is not None:
                return best_land_point
        return best_water_point

    def _neighbors(
        self,
        grid_point: tuple[int, int],
        *,
        required_land_component: int | None,
        forbid_water: bool,
    ) -> Iterable[tuple[tuple[int, int], float]]:
        grid_x, grid_y = grid_point
        for delta_y in (-1, 0, 1):
            for delta_x in (-1, 0, 1):
                if delta_x == 0 and delta_y == 0:
                    continue
                neighbor = (grid_x + delta_x, grid_y + delta_y)
                if not self._in_bounds(neighbor) or not self._is_rendered(neighbor):
                    continue
                if required_land_component is not None:
                    if self._land_component_id(neighbor) != required_land_component:
                        continue
                base_cost = 1.41421356237 if delta_x != 0 and delta_y != 0 else 1.0
                if self._is_water(neighbor):
                    if forbid_water:
                        continue
                    yield (neighbor, base_cost * WATER_COST_MULTIPLIER)
                    continue
                if self._is_near_water(neighbor):
                    yield (neighbor, base_cost * NEAR_WATER_COST_MULTIPLIER)
                    continue
                yield (neighbor, base_cost)

    def _heuristic(self, first_point: tuple[int, int], second_point: tuple[int, int]) -> float:
        delta_x = abs(first_point[0] - second_point[0])
        delta_y = abs(first_point[1] - second_point[1])
        diagonal = min(delta_x, delta_y)
        straight = max(delta_x, delta_y) - diagonal
        return (diagonal * 1.41421356237) + straight

    def find_path(
        self,
        start_coordinates: tuple[int, int],
        end_coordinates: tuple[int, int],
    ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
        start_grid = self.snap_world_point(start_coordinates)
        end_grid = self.snap_world_point(end_coordinates)
        if start_grid is None or end_grid is None:
            return None

        start_component = self._land_component_id(start_grid)
        end_component = self._land_component_id(end_grid)
        same_land_component = (
            start_component is not None
            and end_component is not None
            and start_component == end_component
        )

        frontier: list[tuple[float, float, tuple[int, int]]] = []
        heapq.heappush(frontier, (self._heuristic(start_grid, end_grid), 0.0, start_grid))
        best_costs: dict[tuple[int, int], float] = {start_grid: 0.0}
        previous: dict[tuple[int, int], tuple[int, int] | None] = {start_grid: None}

        while frontier:
            _priority, current_cost, current_point = heapq.heappop(frontier)
            if current_cost != best_costs.get(current_point):
                continue
            if current_point == end_grid:
                break

            for next_point, edge_cost in self._neighbors(
                current_point,
                required_land_component=start_component if same_land_component else None,
                forbid_water=same_land_component,
            ):
                next_cost = current_cost + edge_cost
                if next_cost >= best_costs.get(next_point, float("inf")):
                    continue
                best_costs[next_point] = next_cost
                previous[next_point] = current_point
                heapq.heappush(
                    frontier,
                    (next_cost + self._heuristic(next_point, end_grid), next_cost, next_point),
                )

        if end_grid not in best_costs:
            return None

        grid_path = [end_grid]
        while grid_path[-1] != start_grid:
            parent = previous.get(grid_path[-1])
            if parent is None:
                return None
            grid_path.append(parent)
        grid_path.reverse()

        compressed_grid_path = _compress_grid_path(grid_path)
        world_points = [start_coordinates]
        for grid_point in compressed_grid_path[1:-1]:
            world_points.append(self._grid_to_world(grid_point))
        world_points.append(end_coordinates)
        return (best_costs[end_grid], tuple(_dedupe_consecutive_points(world_points)))


def _neighbors8(grid_x: int, grid_y: int):
    for delta_y in (-1, 0, 1):
        for delta_x in (-1, 0, 1):
            if delta_x == 0 and delta_y == 0:
                continue
            yield (grid_x + delta_x, grid_y + delta_y)


def _looks_like_water(red: float, green: float, blue: float) -> bool:
    if blue >= red + 24 and blue >= green + 18 and green <= 170:
        return True
    water_distance = ((red - 48) ** 2) + ((green - 112) ** 2) + ((blue - 186) ** 2)
    return water_distance <= (52 ** 2)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _dedupe_consecutive_points(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    deduped: list[tuple[int, int]] = []
    for point in points:
        if deduped and deduped[-1] == point:
            continue
        deduped.append(point)
    return deduped


def _compress_grid_path(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if len(points) <= 2:
        return points[:]

    compressed = [points[0]]
    previous_direction: tuple[int, int] | None = None
    for index in range(1, len(points)):
        previous_point = points[index - 1]
        current_point = points[index]
        direction = (
            _sign(current_point[0] - previous_point[0]),
            _sign(current_point[1] - previous_point[1]),
        )
        if previous_direction is None:
            previous_direction = direction
            continue
        if direction != previous_direction:
            compressed.append(previous_point)
            previous_direction = direction
    compressed.append(points[-1])
    return compressed


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _is_pier_node(node: object) -> bool:
    node_key = str(getattr(node, "key", "")).lower()
    node_label = str(getattr(node, "label", "") or "").lower()
    return "_pier_" in node_key or "pier" in node_label


def _display_label_for(base: object, endpoint_key: str) -> str:
    endpoint = base._path_endpoint_from_key(endpoint_key)
    if endpoint is None:
        return endpoint_key
    return endpoint.display_label


def _choose_anchor_key_for_stop(base: object, stop: object) -> str:
    stop_coordinates = tuple(getattr(stop, "coordinates"))
    best_node = None
    best_distance = None

    for node in base.PATH_NODES:
        if _is_pier_node(node):
            continue
        node_distance = dist(stop_coordinates, tuple(getattr(node, "coordinates")))
        if node_distance > ANCHOR_NODE_MAX_DISTANCE:
            continue
        if best_distance is None or node_distance < best_distance:
            best_distance = node_distance
            best_node = node

    if best_node is None:
        return str(getattr(stop, "var"))
    return str(getattr(best_node, "key"))


def village_anchor_keys(base: object) -> dict[str, str]:
    return {
        str(getattr(stop, "var")): _choose_anchor_key_for_stop(base, stop)
        for stop in base.METRO_STOPS
    }


def _walk_component_index(base: object, anchor_keys: Iterable[str]) -> dict[str, int]:
    relevant_keys = set(anchor_keys)
    adjacency: dict[str, set[str]] = {key: set() for key in relevant_keys}

    for edge in base.EXTRA_EDGES:
        if getattr(edge, "kind", None) != "walk":
            continue
        from_key = str(getattr(getattr(edge, "from_endpoint"), "key"))
        to_key = str(getattr(getattr(edge, "to_endpoint"), "key"))
        if from_key in adjacency and to_key in adjacency:
            adjacency[from_key].add(to_key)
            adjacency[to_key].add(from_key)

    component_by_key: dict[str, int] = {}
    next_component = 0
    for start_key in sorted(adjacency):
        if start_key in component_by_key:
            continue
        stack = [start_key]
        component_by_key[start_key] = next_component
        while stack:
            current_key = stack.pop()
            for neighbor_key in adjacency[current_key]:
                if neighbor_key in component_by_key:
                    continue
                component_by_key[neighbor_key] = next_component
                stack.append(neighbor_key)
        next_component += 1
    return component_by_key


def _endpoint_coordinates(base: object, endpoint_key: str) -> tuple[int, int]:
    endpoint = base._path_endpoint_from_key(endpoint_key)
    if endpoint is None:
        raise KeyError(endpoint_key)
    return tuple(endpoint.coordinates)


def _terrain_from_viewer(viewer: object) -> TerrainGrid | None:
    if not hasattr(viewer, "_current_world_map_render_underlay"):
        return None
    render_underlay = viewer._current_world_map_render_underlay()
    if render_underlay is None:
        return None

    payload, source_image = render_underlay
    try:
        min_x = int(payload["min_x"])
        max_x = int(payload["max_x"])
        min_z = int(payload["min_z"])
        max_z = int(payload["max_z"])
    except (KeyError, TypeError, ValueError):
        return None

    if min_x >= max_x or min_z >= max_z:
        return None
    return TerrainGrid(
        min_x=min_x,
        max_x=max_x,
        min_z=min_z,
        max_z=max_z,
        image=source_image,
    )


def _network_signature(base: object) -> tuple[object, ...]:
    stop_signature = tuple(
        (str(stop.var), int(stop.x), int(stop.y))
        for stop in sorted(base.METRO_STOPS, key=lambda stop: str(stop.var))
    )
    node_signature = tuple(
        (
            str(node.key),
            int(node.x),
            int(node.y),
            str(getattr(node, "label", "") or ""),
        )
        for node in sorted(base.PATH_NODES, key=lambda node: str(node.key))
    )
    walk_edge_signature = tuple(
        (
            str(edge.id),
            str(edge.from_endpoint.key),
            str(edge.to_endpoint.key),
            tuple(tuple(point) for point in getattr(edge, "path_points", ()) or ()),
            str(getattr(edge, "label", "") or ""),
        )
        for edge in sorted(
            (edge for edge in base.EXTRA_EDGES if getattr(edge, "kind", None) == "walk"),
            key=lambda edge: str(edge.id),
        )
    )
    return (stop_signature, node_signature, walk_edge_signature)


def _component_pair_candidates(
    base: object,
    grouped_keys: dict[int, list[str]],
    first_component: int,
    second_component: int,
) -> list[tuple[float, str, str]]:
    candidates: list[tuple[float, str, str]] = []
    for first_key in grouped_keys[first_component]:
        first_coordinates = _endpoint_coordinates(base, first_key)
        for second_key in grouped_keys[second_component]:
            second_coordinates = _endpoint_coordinates(base, second_key)
            candidates.append((dist(first_coordinates, second_coordinates), first_key, second_key))
    candidates.sort()
    return candidates[:COMPONENT_PAIR_CANDIDATES]


def _candidate_routes(
    base: object,
    terrain: TerrainGrid,
    grouped_keys: dict[int, list[str]],
) -> list[_RouteCandidate]:
    component_ids = sorted(grouped_keys)
    candidates: list[_RouteCandidate] = []

    for first_index, first_component in enumerate(component_ids):
        for second_component in component_ids[first_index + 1:]:
            best_route = None
            for _straight_distance, first_key, second_key in _component_pair_candidates(
                base,
                grouped_keys,
                first_component,
                second_component,
            ):
                first_coordinates = _endpoint_coordinates(base, first_key)
                second_coordinates = _endpoint_coordinates(base, second_key)
                route = terrain.find_path(first_coordinates, second_coordinates)
                if route is None:
                    continue
                route_cost, path_coordinates = route
                candidate = _RouteCandidate(
                    cost=route_cost,
                    first_key=first_key,
                    second_key=second_key,
                    first_component=first_component,
                    second_component=second_component,
                    path_coordinates=path_coordinates,
                )
                if best_route is None or candidate.cost < best_route.cost:
                    best_route = candidate
            if best_route is not None:
                candidates.append(best_route)
    candidates.sort(key=lambda candidate: (candidate.cost, candidate.first_key, candidate.second_key))
    return candidates


def build_suggested_segments(base: object, viewer: object | None = None) -> tuple[SuggestedSegment, ...]:
    global _CACHE_KEY
    global _CACHE_VALUE

    anchors_by_stop = village_anchor_keys(base)
    anchor_keys = tuple(dict.fromkeys(anchors_by_stop.values()))
    if len(anchor_keys) < 2:
        return ()

    component_by_key = _walk_component_index(base, anchor_keys)
    grouped_keys: dict[int, list[str]] = {}
    for endpoint_key in anchor_keys:
        grouped_keys.setdefault(component_by_key[endpoint_key], []).append(endpoint_key)

    if len(grouped_keys) < 2:
        return ()

    terrain = _terrain_from_viewer(viewer) if viewer is not None else None
    if terrain is None:
        return ()

    cache_key = (_network_signature(base), terrain.signature)
    if cache_key == _CACHE_KEY:
        return _CACHE_VALUE

    candidates = _candidate_routes(base, terrain, grouped_keys)
    if not candidates:
        _CACHE_KEY = cache_key
        _CACHE_VALUE = ()
        return ()

    parent = {component_id: component_id for component_id in grouped_keys}

    def find(component_id: int) -> int:
        while parent[component_id] != component_id:
            parent[component_id] = parent[parent[component_id]]
            component_id = parent[component_id]
        return component_id

    def union(first_component: int, second_component: int) -> bool:
        first_root = find(first_component)
        second_root = find(second_component)
        if first_root == second_root:
            return False
        parent[second_root] = first_root
        return True

    segments: list[SuggestedSegment] = []
    for candidate in candidates:
        if not union(candidate.first_component, candidate.second_component):
            continue
        start_coordinates = _endpoint_coordinates(base, candidate.first_key)
        end_coordinates = _endpoint_coordinates(base, candidate.second_key)
        segments.append(
            SuggestedSegment(
                start_coordinates=start_coordinates,
                end_coordinates=end_coordinates,
                start_key=candidate.first_key,
                end_key=candidate.second_key,
                start_label=_display_label_for(base, candidate.first_key),
                end_label=_display_label_for(base, candidate.second_key),
                length=_polyline_length(candidate.path_coordinates),
                cost=candidate.cost,
                path_coordinates=candidate.path_coordinates,
            )
        )

    _CACHE_KEY = cache_key
    _CACHE_VALUE = tuple(segments)
    return _CACHE_VALUE


def _polyline_length(points: tuple[tuple[int, int], ...]) -> float:
    return sum(dist(first_point, second_point) for first_point, second_point in zip(points, points[1:]))
