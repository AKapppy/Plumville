from __future__ import annotations

from dataclasses import dataclass
import heapq
from math import dist, hypot
from typing import Any, Iterable, cast

from PIL import Image


ANCHOR_NODE_MAX_DISTANCE = 96.0
MAX_GRID_DIMENSION = 180
WATER_COST_MULTIPLIER = 10.0
NEAR_WATER_COST_MULTIPLIER = 1.75
OUTSIDE_RENDER_SEARCH_RADIUS = 4
COMPONENT_PAIR_CANDIDATES = 8
FRONTIER_COMPONENT_PAIR_CANDIDATES = 64
TREE_COMPONENT_PAIR_CANDIDATES = 12
TREE_ATTACHABLE_SOURCE_CANDIDATES = 3
CLOSE_VIRTUAL_ENDPOINT_DISTANCE = 16.0
LOOP_ROUTE_COST_MULTIPLIER = 1.25
LOOP_CANDIDATES_PER_FRONTIER = 1


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


@dataclass(frozen=True, slots=True)
class _VillageAnchor:
    stop_var: str
    key: str
    coordinates: tuple[int, int]
    label: str
    component_keys: tuple[str, ...] = ()


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
                        red, green, blue, alpha = cast(tuple[int, int, int, int], pixels[px, py])
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


def _display_label_for(base: Any, endpoint_key: str) -> str:
    if not hasattr(base, "_path_endpoint_from_key"):
        return endpoint_key
    endpoint = base._path_endpoint_from_key(endpoint_key)
    if endpoint is None:
        return endpoint_key
    return endpoint.display_label


def _city_path_anchor_for_stop(base: Any, stop: object) -> _VillageAnchor | None:
    if not bool(getattr(stop, "has_walking_paths", False)):
        return None
    if not tuple(getattr(stop, "city_limit_node_keys", ()) or ()):
        return None
    if not all(
        hasattr(base, helper_name)
        for helper_name in (
            "_city_limit_world_points",
            "_city_path_anchor_candidate_for_edge",
            "_coordinate_endpoint_key",
            "_display_label",
        )
    ):
        return None

    city_limit_points = base._city_limit_world_points(stop)
    if len(city_limit_points) < 3:
        return None

    best_candidate = None
    best_edge = None
    for edge in base.EXTRA_EDGES:
        if getattr(edge, "kind", None) != "walk":
            continue
        candidate = base._city_path_anchor_candidate_for_edge(stop, city_limit_points, edge)
        if candidate is None:
            continue
        if best_candidate is None or candidate < best_candidate:
            best_candidate = candidate
            best_edge = edge

    if best_candidate is None or best_edge is None:
        return None

    _anchor_distance, _anchor_along_distance, anchor_point = best_candidate
    anchor_key = base._coordinate_endpoint_key(anchor_point[0], anchor_point[1])
    component_keys = (
        str(getattr(getattr(best_edge, "from_endpoint"), "key")),
        str(getattr(getattr(best_edge, "to_endpoint"), "key")),
    )
    return _VillageAnchor(
        stop_var=str(getattr(stop, "var")),
        key=anchor_key,
        coordinates=anchor_point,
        label=base._display_label(str(getattr(stop, "lbl", getattr(stop, "var")))),
        component_keys=tuple(dict.fromkeys(component_keys)),
    )


def _choose_anchor_for_stop(base: Any, stop: object) -> _VillageAnchor:
    city_anchor = _city_path_anchor_for_stop(base, stop)
    if city_anchor is not None:
        return city_anchor

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
        stop_var = str(getattr(stop, "var"))
        endpoint = base._path_endpoint_from_key(stop_var) if hasattr(base, "_path_endpoint_from_key") else None
        coordinates = tuple(endpoint.coordinates) if endpoint is not None else cast(tuple[int, int], stop_coordinates)
        return _VillageAnchor(
            stop_var=stop_var,
            key=stop_var,
            coordinates=coordinates,
            label=_display_label_for(base, stop_var),
        )

    node_key = str(getattr(best_node, "key"))
    return _VillageAnchor(
        stop_var=str(getattr(stop, "var")),
        key=node_key,
        coordinates=tuple(getattr(best_node, "coordinates")),
        label=_display_label_for(base, node_key),
    )


def _eligible_suggestion_stop_vars(base: Any) -> frozenset[str]:
    connected_stop_vars = {
        str(getattr(stop, "var"))
        for stop in base.METRO_STOPS
        if bool(getattr(stop, "is_connected", False))
    }
    frontier_stop_vars: set[str] = set()
    frontier_highlight_stop_vars = getattr(base, "_frontier_highlight_stop_vars", None)
    if callable(frontier_highlight_stop_vars):
        frontier_values = cast(Iterable[object], frontier_highlight_stop_vars())
        frontier_stop_vars.update(str(stop_var) for stop_var in frontier_values)
    return frozenset(connected_stop_vars | frontier_stop_vars)


def village_anchor_keys(base: Any) -> dict[str, str]:
    return {
        stop_var: anchor.key
        for stop_var, anchor in village_anchors(base).items()
    }


def village_anchors(base: Any) -> dict[str, _VillageAnchor]:
    eligible_stop_vars = _eligible_suggestion_stop_vars(base)
    return {
        str(getattr(stop, "var")): _choose_anchor_for_stop(base, stop)
        for stop in base.METRO_STOPS
        if str(getattr(stop, "var")) in eligible_stop_vars
    }


def _walk_component_index(base: Any, anchors: Iterable[_VillageAnchor]) -> dict[str, int]:
    anchor_tuple = tuple(anchors)
    adjacency: dict[str, set[str]] = {}

    def ensure_key(endpoint_key: str) -> None:
        adjacency.setdefault(endpoint_key, set())

    def connect(first_key: str, second_key: str) -> None:
        ensure_key(first_key)
        ensure_key(second_key)
        adjacency[first_key].add(second_key)
        adjacency[second_key].add(first_key)

    for edge in base.EXTRA_EDGES:
        if getattr(edge, "kind", None) != "walk":
            continue
        from_key = str(getattr(getattr(edge, "from_endpoint"), "key"))
        to_key = str(getattr(getattr(edge, "to_endpoint"), "key"))
        path_keys = [from_key]
        for point_x, point_y in _edge_path_coordinates(edge):
            path_keys.append(_coordinate_key(base, point_x, point_y))
        path_keys.append(to_key)
        deduped_path_keys = _dedupe_consecutive_keys(path_keys)
        for first_key, second_key in zip(deduped_path_keys, deduped_path_keys[1:]):
            connect(first_key, second_key)
    for anchor in anchor_tuple:
        ensure_key(anchor.key)
        for component_key in anchor.component_keys:
            connect(anchor.key, component_key)

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


def _coordinate_key(base: Any, point_x: int, point_y: int) -> str:
    coordinate_key = getattr(base, "_coordinate_endpoint_key", None)
    if callable(coordinate_key):
        return str(coordinate_key(point_x, point_y))
    return f"coord:{point_x},{point_y}"


def _edge_path_coordinates(edge: object) -> tuple[tuple[int, int], ...]:
    path_points = tuple(getattr(edge, "path_points", ()) or ())
    if not path_points:
        return ()
    from_coordinates = tuple(getattr(getattr(edge, "from_endpoint"), "coordinates"))
    to_coordinates = tuple(getattr(getattr(edge, "to_endpoint"), "coordinates"))
    points = [tuple(point) for point in path_points]
    if points and points[0] == from_coordinates:
        points = points[1:]
    if points and points[-1] == to_coordinates:
        points = points[:-1]
    return tuple(cast(tuple[int, int], point) for point in points)


def _dedupe_consecutive_keys(keys: list[str]) -> list[str]:
    deduped: list[str] = []
    for key in keys:
        if deduped and deduped[-1] == key:
            continue
        deduped.append(key)
    return deduped


def _endpoint_coordinates(base: Any, endpoint_key: str) -> tuple[int, int]:
    endpoint = base._path_endpoint_from_key(endpoint_key)
    if endpoint is None:
        raise KeyError(endpoint_key)
    return tuple(endpoint.coordinates)


def _endpoint_coordinates_or_none(base: Any, endpoint_key: str) -> tuple[int, int] | None:
    try:
        return _endpoint_coordinates(base, endpoint_key)
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    if not endpoint_key.startswith("coord:"):
        return None
    coordinate_text = endpoint_key.removeprefix("coord:")
    try:
        point_x_text, point_y_text = coordinate_text.split(",", 1)
        return (int(point_x_text), int(point_y_text))
    except ValueError:
        return None


def _terrain_from_viewer(viewer: Any) -> TerrainGrid | None:
    metadata = _terrain_metadata_from_viewer(viewer)
    if metadata is None:
        return None
    min_x, max_x, min_z, max_z, source_image = metadata
    return TerrainGrid(
        min_x=min_x,
        max_x=max_x,
        min_z=min_z,
        max_z=max_z,
        image=source_image,
    )


def _terrain_metadata_from_viewer(
    viewer: Any,
) -> tuple[int, int, int, int, Image.Image] | None:
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
    return (min_x, max_x, min_z, max_z, source_image)


def _terrain_signature_from_metadata(
    metadata: tuple[int, int, int, int, Image.Image],
) -> tuple[object, ...]:
    min_x, max_x, min_z, max_z, source_image = metadata
    image_width, image_height = source_image.size
    step_px = max(1, round(max(image_width, image_height) / MAX_GRID_DIMENSION))
    return (
        min_x,
        max_x,
        min_z,
        max_z,
        image_width,
        image_height,
        step_px,
    )


def _network_signature(base: Any) -> tuple[object, ...]:
    stop_signature = tuple(
        (
            str(stop.var),
            int(stop.x),
            int(stop.y),
            tuple(getattr(stop, "station_entry_coordinates", None) or ()),
            bool(getattr(stop, "is_connected", False)),
            bool(getattr(stop, "has_walking_paths", False)),
            tuple(getattr(stop, "city_limit_node_keys", ()) or ()),
        )
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
    base: Any,
    grouped_keys: dict[int, list[str]],
    first_component: int,
    second_component: int,
    *,
    limit: int = COMPONENT_PAIR_CANDIDATES,
) -> list[tuple[float, str, str]]:
    candidates: list[tuple[float, str, str]] = []
    for first_key in grouped_keys[first_component]:
        first_coordinates = _endpoint_coordinates(base, first_key)
        for second_key in grouped_keys[second_component]:
            second_coordinates = _endpoint_coordinates(base, second_key)
            candidates.append((dist(first_coordinates, second_coordinates), first_key, second_key))
    candidates.sort()
    return candidates[:limit]


def _route_candidate_for_key_pair(
    base: Any,
    terrain: TerrainGrid,
    first_key: str,
    second_key: str,
    first_component: int,
    second_component: int,
) -> _RouteCandidate | None:
    first_coordinates = _endpoint_coordinates(base, first_key)
    second_coordinates = _endpoint_coordinates(base, second_key)
    route = terrain.find_path(first_coordinates, second_coordinates)
    if route is None:
        return None
    route_cost, path_coordinates = route
    path_coordinates = _minecraft_buildable_path(path_coordinates)
    return _RouteCandidate(
        cost=route_cost,
        first_key=first_key,
        second_key=second_key,
        first_component=first_component,
        second_component=second_component,
        path_coordinates=path_coordinates,
    )


def _best_route_between_components(
    base: Any,
    terrain: TerrainGrid,
    grouped_keys: dict[int, list[str]],
    first_component: int,
    second_component: int,
    *,
    limit: int = COMPONENT_PAIR_CANDIDATES,
) -> _RouteCandidate | None:
    best_route = None
    for _straight_distance, first_key, second_key in _component_pair_candidates(
        base,
        grouped_keys,
        first_component,
        second_component,
        limit=limit,
    ):
        candidate = _route_candidate_for_key_pair(
            base,
            terrain,
            first_key,
            second_key,
            first_component,
            second_component,
        )
        if candidate is None:
            continue
        if best_route is None or candidate.cost < best_route.cost:
            best_route = candidate
    return best_route


def _candidate_routes(
    base: Any,
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
                candidate = _route_candidate_for_key_pair(
                    base,
                    terrain,
                    first_key,
                    second_key,
                    first_component,
                    second_component,
                )
                if candidate is None:
                    continue
                if best_route is None or candidate.cost < best_route.cost:
                    best_route = candidate
            if best_route is not None:
                candidates.append(best_route)
    candidates.sort(key=lambda candidate: (candidate.cost, candidate.first_key, candidate.second_key))
    return candidates


def _primary_walk_component_id(
    component_by_key: dict[str, int],
    anchors_by_stop: dict[str, _VillageAnchor],
) -> int | None:
    component_counts: dict[int, int] = {}
    for anchor in anchors_by_stop.values():
        component_id = component_by_key.get(anchor.key)
        if component_id is None:
            continue
        component_counts[component_id] = component_counts.get(component_id, 0) + 1
    if not component_counts:
        return None
    endpoint_counts: dict[int, int] = {}
    for component_id in component_by_key.values():
        endpoint_counts[component_id] = endpoint_counts.get(component_id, 0) + 1
    return max(
        component_counts,
        key=lambda component_id: (
            component_counts[component_id],
            endpoint_counts.get(component_id, 0),
            -component_id,
        ),
    )


def _minimum_spanning_candidates(
    candidates: Iterable[_RouteCandidate],
    component_ids: Iterable[int],
) -> list[_RouteCandidate]:
    parent = {component_id: component_id for component_id in component_ids}

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

    selected_candidates: list[_RouteCandidate] = []
    for candidate in candidates:
        if not union(candidate.first_component, candidate.second_component):
            continue
        selected_candidates.append(candidate)
    return selected_candidates


def _direct_frontier_candidates(
    base: Any,
    terrain: TerrainGrid,
    grouped_keys: dict[int, list[str]],
    candidates: Iterable[_RouteCandidate],
    primary_component: int,
) -> list[_RouteCandidate]:
    direct_candidates: list[_RouteCandidate] = []
    seen_pairs: set[tuple[int, int]] = set()
    for candidate in candidates:
        if primary_component not in (candidate.first_component, candidate.second_component):
            continue
        component_pair = tuple(sorted((candidate.first_component, candidate.second_component)))
        if component_pair in seen_pairs:
            continue
        seen_pairs.add(component_pair)
        refined_candidate = _best_route_between_components(
            base,
            terrain,
            grouped_keys,
            candidate.first_component,
            candidate.second_component,
            limit=FRONTIER_COMPONENT_PAIR_CANDIDATES,
        )
        direct_candidates.append(refined_candidate or candidate)
    direct_candidates.sort(key=lambda candidate: (candidate.cost, candidate.first_key, candidate.second_key))
    return direct_candidates


def _anchor_route_candidates_between_components(
    base: Any,
    terrain: TerrainGrid,
    anchors_by_stop: dict[str, _VillageAnchor],
    component_by_key: dict[str, int],
    first_component: int,
    second_component: int,
) -> list[_RouteCandidate]:
    first_anchors = tuple(
        anchor
        for anchor in anchors_by_stop.values()
        if component_by_key.get(anchor.key) == first_component
    )
    second_anchors = tuple(
        anchor
        for anchor in anchors_by_stop.values()
        if component_by_key.get(anchor.key) == second_component
    )
    candidates: list[_RouteCandidate] = []
    for first_anchor in first_anchors:
        for second_anchor in second_anchors:
            candidate = _route_candidate_for_key_pair(
                base,
                terrain,
                first_anchor.key,
                second_anchor.key,
                first_component,
                second_component,
            )
            if candidate is not None:
                candidates.append(candidate)
    candidates.sort(key=lambda candidate: (candidate.cost, candidate.first_key, candidate.second_key))
    return candidates


def _loop_candidates_for_direct_routes(
    base: Any,
    terrain: TerrainGrid,
    anchors_by_stop: dict[str, _VillageAnchor],
    component_by_key: dict[str, int],
    direct_candidates: Iterable[_RouteCandidate],
) -> list[_RouteCandidate]:
    loop_candidates: list[_RouteCandidate] = []
    selected_pairs = {
        frozenset((candidate.first_key, candidate.second_key))
        for candidate in direct_candidates
    }
    for direct_candidate in direct_candidates:
        added_for_frontier = 0
        for candidate in _anchor_route_candidates_between_components(
            base,
            terrain,
            anchors_by_stop,
            component_by_key,
            direct_candidate.first_component,
            direct_candidate.second_component,
        ):
            candidate_pair = frozenset((candidate.first_key, candidate.second_key))
            if candidate_pair in selected_pairs:
                continue
            if candidate.cost > direct_candidate.cost * LOOP_ROUTE_COST_MULTIPLIER:
                break
            selected_pairs.add(candidate_pair)
            loop_candidates.append(candidate)
            added_for_frontier += 1
            if added_for_frontier >= LOOP_CANDIDATES_PER_FRONTIER:
                break
    loop_candidates.sort(key=lambda candidate: (candidate.cost, candidate.first_key, candidate.second_key))
    return loop_candidates


def _anchor_component_ids(
    anchors_by_stop: dict[str, _VillageAnchor],
    component_by_key: dict[str, int],
) -> set[int]:
    return {
        component_id
        for anchor in anchors_by_stop.values()
        for component_id in (component_by_key.get(anchor.key),)
        if component_id is not None
    }


def _pass_through_component_ids(
    base: Any,
    anchors_by_stop: dict[str, _VillageAnchor],
    component_by_key: dict[str, int],
) -> set[int]:
    stop_by_var = {
        str(getattr(stop, "var")): stop
        for stop in base.METRO_STOPS
    }
    pass_through_components: set[int] = set()
    for stop_var, anchor in anchors_by_stop.items():
        stop = stop_by_var.get(stop_var)
        if stop is None or not bool(getattr(stop, "has_walking_paths", False)):
            continue
        component_id = component_by_key.get(anchor.key)
        if component_id is not None:
            pass_through_components.add(component_id)
    return pass_through_components


def _best_route_chain_between_components(
    base: Any,
    terrain: TerrainGrid,
    grouped_keys: dict[int, list[str]],
    first_component: int,
    second_component: int,
    anchored_components: set[int],
    *,
    limit: int = FRONTIER_COMPONENT_PAIR_CANDIDATES,
) -> list[_RouteCandidate]:
    direct_route = _best_route_between_components(
        base,
        terrain,
        grouped_keys,
        first_component,
        second_component,
        limit=limit,
    )
    best_cost = direct_route.cost if direct_route is not None else float("inf")
    best_chain = [direct_route] if direct_route is not None else []

    for intermediate_component in sorted(grouped_keys):
        if intermediate_component in {first_component, second_component}:
            continue
        if intermediate_component in anchored_components:
            continue

        first_route = _best_route_between_components(
            base,
            terrain,
            grouped_keys,
            first_component,
            intermediate_component,
            limit=limit,
        )
        if first_route is None:
            continue
        second_route = _best_route_between_components(
            base,
            terrain,
            grouped_keys,
            intermediate_component,
            second_component,
            limit=limit,
        )
        if second_route is None:
            continue

        chain_cost = first_route.cost + second_route.cost
        if chain_cost < best_cost:
            best_cost = chain_cost
            best_chain = [first_route, second_route]

    return best_chain


def _chain_cost(chain: Iterable[_RouteCandidate]) -> float:
    return sum(candidate.cost for candidate in chain)


def _component_straight_distance(
    base: Any,
    grouped_keys: dict[int, list[str]],
    first_component: int,
    second_component: int,
) -> float:
    candidates = _component_pair_candidates(
        base,
        grouped_keys,
        first_component,
        second_component,
        limit=1,
    )
    if not candidates:
        return float("inf")
    return candidates[0][0]


def _route_shared_key(first_candidate: _RouteCandidate, second_candidate: _RouteCandidate) -> str | None:
    shared_keys = {
        first_candidate.first_key,
        first_candidate.second_key,
    } & {
        second_candidate.first_key,
        second_candidate.second_key,
    }
    if len(shared_keys) != 1:
        return None
    return next(iter(shared_keys))


def _oriented_path_to_key(
    candidate: _RouteCandidate,
    end_key: str,
) -> tuple[str, tuple[tuple[int, int], ...]] | None:
    if candidate.second_key == end_key:
        return (candidate.first_key, candidate.path_coordinates)
    if candidate.first_key == end_key:
        return (candidate.second_key, tuple(reversed(candidate.path_coordinates)))
    return None


def _route_merge_point(
    first_path: tuple[tuple[int, int], ...],
    second_path: tuple[tuple[int, int], ...],
) -> tuple[int, int] | None:
    first_unique = first_path[0]
    second_unique = second_path[0]
    shared_endpoint = first_path[-1]
    best_point = None
    best_distance = None

    for first_start, first_end in zip(first_path, first_path[1:]):
        for second_start, second_end in zip(second_path, second_path[1:]):
            intersection = _segment_intersection(first_start, first_end, second_start, second_end)
            if intersection is None:
                continue
            if intersection in {first_unique, second_unique, shared_endpoint}:
                continue
            intersection_distance = dist(intersection, shared_endpoint)
            if best_distance is None or intersection_distance > best_distance:
                best_distance = intersection_distance
                best_point = intersection
    return best_point


def _segment_intersection(
    first_start: tuple[int, int],
    first_end: tuple[int, int],
    second_start: tuple[int, int],
    second_end: tuple[int, int],
) -> tuple[int, int] | None:
    first_x, first_y = first_start
    first_dx = first_end[0] - first_x
    first_dy = first_end[1] - first_y
    second_x, second_y = second_start
    second_dx = second_end[0] - second_x
    second_dy = second_end[1] - second_y
    denominator = (first_dx * second_dy) - (first_dy * second_dx)

    if denominator == 0:
        for point in (first_start, first_end, second_start, second_end):
            if _point_on_segment(point, first_start, first_end) and _point_on_segment(point, second_start, second_end):
                return point
        return None

    delta_x = second_x - first_x
    delta_y = second_y - first_y
    first_fraction = ((delta_x * second_dy) - (delta_y * second_dx)) / denominator
    second_fraction = ((delta_x * first_dy) - (delta_y * first_dx)) / denominator
    if not (0.0 <= first_fraction <= 1.0 and 0.0 <= second_fraction <= 1.0):
        return None
    return (
        round(first_x + (first_fraction * first_dx)),
        round(first_y + (first_fraction * first_dy)),
    )


def _point_on_segment(
    point: tuple[int, int],
    segment_start: tuple[int, int],
    segment_end: tuple[int, int],
) -> bool:
    cross_product = (
        (point[1] - segment_start[1]) * (segment_end[0] - segment_start[0])
        - (point[0] - segment_start[0]) * (segment_end[1] - segment_start[1])
    )
    if cross_product != 0:
        return False
    return (
        min(segment_start[0], segment_end[0]) <= point[0] <= max(segment_start[0], segment_end[0])
        and min(segment_start[1], segment_end[1]) <= point[1] <= max(segment_start[1], segment_end[1])
    )


def _split_path_at_point(
    path: tuple[tuple[int, int], ...],
    split_point: tuple[int, int],
) -> tuple[
    tuple[tuple[int, int], ...],
    tuple[tuple[int, int], ...],
] | None:
    if split_point == path[0]:
        return ((path[0],), path)
    if split_point == path[-1]:
        return (path, (path[-1],))

    for index, (segment_start, segment_end) in enumerate(zip(path, path[1:])):
        if not _point_on_segment(split_point, segment_start, segment_end):
            continue
        prefix = [*path[: index + 1]]
        suffix = [*path[index + 1 :]]
        if prefix[-1] != split_point:
            prefix.append(split_point)
        if suffix[0] != split_point:
            suffix.insert(0, split_point)
        return (tuple(_dedupe_consecutive_points(prefix)), tuple(_dedupe_consecutive_points(suffix)))
    return None


def _candidate_from_path(
    *,
    first_key: str,
    second_key: str,
    first_component: int,
    second_component: int,
    path_coordinates: tuple[tuple[int, int], ...],
) -> _RouteCandidate | None:
    if len(path_coordinates) < 2:
        return None
    path_coordinates = _minecraft_buildable_path(path_coordinates)
    return _RouteCandidate(
        cost=_polyline_length(path_coordinates),
        first_key=first_key,
        second_key=second_key,
        first_component=first_component,
        second_component=second_component,
        path_coordinates=path_coordinates,
    )


def _merged_shared_trunk_candidates(
    base: Any,
    first_candidate: _RouteCandidate,
    second_candidate: _RouteCandidate,
) -> tuple[_RouteCandidate, ...]:
    shared_key = _route_shared_key(first_candidate, second_candidate)
    if shared_key is None:
        return ()

    first_oriented = _oriented_path_to_key(first_candidate, shared_key)
    second_oriented = _oriented_path_to_key(second_candidate, shared_key)
    if first_oriented is None or second_oriented is None:
        return ()

    first_unique_key, first_path = first_oriented
    second_unique_key, second_path = second_oriented
    merge_point = _route_merge_point(first_path, second_path)
    if merge_point is None:
        return ()

    first_split = _split_path_at_point(first_path, merge_point)
    second_split = _split_path_at_point(second_path, merge_point)
    if first_split is None or second_split is None:
        return ()

    merge_key = _coordinate_key(base, merge_point[0], merge_point[1])
    first_branch, first_trunk = first_split
    second_branch, second_trunk = second_split
    trunk_path = first_trunk if _polyline_length(first_trunk) <= _polyline_length(second_trunk) else second_trunk

    candidates = tuple(
        candidate
        for candidate in (
            _candidate_from_path(
                first_key=first_unique_key,
                second_key=merge_key,
                first_component=first_candidate.first_component,
                second_component=first_candidate.first_component,
                path_coordinates=first_branch,
            ),
            _candidate_from_path(
                first_key=second_unique_key,
                second_key=merge_key,
                first_component=second_candidate.first_component,
                second_component=second_candidate.first_component,
                path_coordinates=second_branch,
            ),
            _candidate_from_path(
                first_key=merge_key,
                second_key=shared_key,
                first_component=first_candidate.first_component,
                second_component=first_candidate.second_component,
                path_coordinates=trunk_path,
            ),
        )
        if candidate is not None
    )
    return candidates


def _consolidated_candidates(
    base: Any,
    direct_candidates: list[_RouteCandidate],
    loop_candidates: Iterable[_RouteCandidate],
) -> list[_RouteCandidate]:
    consolidated = direct_candidates[:]
    replaced_indexes: set[int] = set()
    additions: list[_RouteCandidate] = []

    for loop_candidate in loop_candidates:
        for index, direct_candidate in enumerate(consolidated):
            if index in replaced_indexes:
                continue
            if {
                direct_candidate.first_component,
                direct_candidate.second_component,
            } != {
                loop_candidate.first_component,
                loop_candidate.second_component,
            }:
                continue
            merged_candidates = _merged_shared_trunk_candidates(base, direct_candidate, loop_candidate)
            if not merged_candidates:
                continue
            replaced_indexes.add(index)
            additions.extend(merged_candidates)
            break

    if not replaced_indexes:
        return consolidated
    return [
        candidate
        for index, candidate in enumerate(consolidated)
        if index not in replaced_indexes
    ] + additions


def _route_branch_point(
    first_path: tuple[tuple[int, int], ...],
    second_path: tuple[tuple[int, int], ...],
) -> tuple[int, int] | None:
    shared_start = first_path[0]
    first_target = first_path[-1]
    second_target = second_path[-1]
    best_point = None
    best_distance = None

    for first_start, first_end in zip(first_path, first_path[1:]):
        for second_start, second_end in zip(second_path, second_path[1:]):
            intersection = _segment_intersection(first_start, first_end, second_start, second_end)
            if intersection is None:
                continue
            if intersection in {shared_start, first_target, second_target}:
                continue
            intersection_distance = dist(shared_start, intersection)
            if best_distance is None or intersection_distance > best_distance:
                best_distance = intersection_distance
                best_point = intersection
    return best_point


def _oriented_path_from_key(
    candidate: _RouteCandidate,
    start_key: str,
) -> tuple[str, tuple[tuple[int, int], ...]] | None:
    if candidate.first_key == start_key:
        return (candidate.second_key, candidate.path_coordinates)
    if candidate.second_key == start_key:
        return (candidate.first_key, tuple(reversed(candidate.path_coordinates)))
    return None


def _merged_shared_stem_candidates(
    base: Any,
    first_candidate: _RouteCandidate,
    second_candidate: _RouteCandidate,
) -> tuple[_RouteCandidate, ...]:
    shared_key = _route_shared_key(first_candidate, second_candidate)
    if shared_key is None:
        return ()

    first_oriented = _oriented_path_from_key(first_candidate, shared_key)
    second_oriented = _oriented_path_from_key(second_candidate, shared_key)
    if first_oriented is None or second_oriented is None:
        return ()

    first_target_key, first_path = first_oriented
    second_target_key, second_path = second_oriented
    branch_point = _route_branch_point(first_path, second_path)
    if branch_point is None:
        return ()

    first_split = _split_path_at_point(first_path, branch_point)
    second_split = _split_path_at_point(second_path, branch_point)
    if first_split is None or second_split is None:
        return ()

    branch_key = _coordinate_key(base, branch_point[0], branch_point[1])
    first_stem, first_branch = first_split
    _second_stem, second_branch = second_split
    return tuple(
        candidate
        for candidate in (
            _candidate_from_path(
                first_key=shared_key,
                second_key=branch_key,
                first_component=first_candidate.first_component,
                second_component=first_candidate.first_component,
                path_coordinates=first_stem,
            ),
            _candidate_from_path(
                first_key=branch_key,
                second_key=first_target_key,
                first_component=first_candidate.first_component,
                second_component=first_candidate.second_component,
                path_coordinates=first_branch,
            ),
            _candidate_from_path(
                first_key=branch_key,
                second_key=second_target_key,
                first_component=second_candidate.first_component,
                second_component=second_candidate.second_component,
                path_coordinates=second_branch,
            ),
        )
        if candidate is not None
    )


def _consolidate_shared_stems(
    base: Any,
    candidates: Iterable[_RouteCandidate],
) -> list[_RouteCandidate]:
    consolidated = _dedupe_route_candidates(candidates)
    for _attempt in range(len(consolidated)):
        for first_index, first_candidate in enumerate(consolidated):
            for second_index in range(first_index + 1, len(consolidated)):
                second_candidate = consolidated[second_index]
                merged_candidates = _merged_shared_stem_candidates(
                    base,
                    first_candidate,
                    second_candidate,
                )
                if not merged_candidates:
                    continue
                consolidated = _dedupe_route_candidates(
                    [
                        candidate
                        for index, candidate in enumerate(consolidated)
                        if index not in {first_index, second_index}
                    ]
                    + list(merged_candidates)
                )
                break
            else:
                continue
            break
        else:
            break
    return consolidated


def _canonicalize_close_virtual_endpoints(
    base: Any,
    candidates: Iterable[_RouteCandidate],
    fixed_endpoint_keys: set[str],
) -> list[_RouteCandidate]:
    canonical_coordinate_points: list[tuple[str, tuple[int, int]]] = []
    canonical_by_key: dict[str, str] = {}

    def canonical_key(endpoint_key: str) -> str:
        cached_key = canonical_by_key.get(endpoint_key)
        if cached_key is not None:
            return cached_key
        if endpoint_key in fixed_endpoint_keys and not endpoint_key.startswith("coord:"):
            canonical_by_key[endpoint_key] = endpoint_key
            return endpoint_key

        coordinates = _endpoint_coordinates_or_none(base, endpoint_key)
        if coordinates is None:
            canonical_by_key[endpoint_key] = endpoint_key
            return endpoint_key

        nearest_coordinate = min(
            (
                (dist(coordinates, known_coordinates), known_key)
                for known_key, known_coordinates in canonical_coordinate_points
                if dist(coordinates, known_coordinates) <= CLOSE_VIRTUAL_ENDPOINT_DISTANCE
            ),
            default=None,
            key=lambda item: (item[0], item[1]),
        )
        if nearest_coordinate is not None:
            canonical_by_key[endpoint_key] = nearest_coordinate[1]
            return nearest_coordinate[1]

        canonical_coordinate_points.append((endpoint_key, coordinates))
        canonical_by_key[endpoint_key] = endpoint_key
        return endpoint_key

    rewritten_candidates: list[_RouteCandidate] = []
    for candidate in _dedupe_route_candidates(candidates):
        first_key = canonical_key(candidate.first_key)
        second_key = canonical_key(candidate.second_key)
        if first_key == second_key:
            continue

        path_coordinates = list(candidate.path_coordinates)
        first_coordinates = _endpoint_coordinates_or_none(base, first_key)
        second_coordinates = _endpoint_coordinates_or_none(base, second_key)
        if first_coordinates is not None:
            path_coordinates[0] = first_coordinates
        if second_coordinates is not None:
            path_coordinates[-1] = second_coordinates

        rewritten_candidate = _candidate_from_path(
            first_key=first_key,
            second_key=second_key,
            first_component=candidate.first_component,
            second_component=candidate.second_component,
            path_coordinates=tuple(path_coordinates),
        )
        if rewritten_candidate is not None:
            rewritten_candidates.append(rewritten_candidate)

    return _dedupe_route_candidates(rewritten_candidates)


def _tree_route_candidates(
    base: Any,
    terrain: TerrainGrid,
    grouped_keys: dict[int, list[str]],
    anchors_by_stop: dict[str, _VillageAnchor],
    component_by_key: dict[str, int],
    primary_component: int,
) -> list[_RouteCandidate]:
    anchored_components = _anchor_component_ids(anchors_by_stop, component_by_key)
    pass_through_components = _pass_through_component_ids(base, anchors_by_stop, component_by_key)
    attached_components = {primary_component}
    attachable_components = {primary_component}
    remaining_components = anchored_components - attached_components
    selected_candidates: list[_RouteCandidate] = []
    route_chain_cache: dict[tuple[int, int], list[_RouteCandidate]] = {}

    def route_chain_between(
        source_component: int,
        target_component: int,
    ) -> list[_RouteCandidate]:
        cache_key = (source_component, target_component)
        cached_chain = route_chain_cache.get(cache_key)
        if cached_chain is not None:
            return cached_chain
        route_chain = _best_route_chain_between_components(
            base,
            terrain,
            grouped_keys,
            source_component,
            target_component,
            anchored_components,
            limit=TREE_COMPONENT_PAIR_CANDIDATES,
        )
        route_chain_cache[cache_key] = route_chain
        return route_chain

    while remaining_components and attachable_components:
        best_source = None
        best_target = None
        best_chain: list[_RouteCandidate] = []
        best_cost = float("inf")
        pairs_to_try: set[tuple[int, int]] = set()
        for target_component in sorted(remaining_components):
            closest_sources = sorted(
                (
                    (
                        _component_straight_distance(
                            base,
                            grouped_keys,
                            source_component,
                            target_component,
                        ),
                        source_component,
                    )
                    for source_component in attachable_components
                ),
                key=lambda item: (item[0], item[1]),
            )[:TREE_ATTACHABLE_SOURCE_CANDIDATES]
            pairs_to_try.update(
                (source_component, target_component)
                for _straight_distance, source_component in closest_sources
            )

        for source_component, target_component in sorted(
            pairs_to_try,
            key=lambda pair: (
                _component_straight_distance(base, grouped_keys, pair[0], pair[1]),
                pair[0],
                pair[1],
            ),
        ):
            route_chain = route_chain_between(source_component, target_component)
            if not route_chain:
                continue
            route_cost = _chain_cost(route_chain)
            if route_cost < best_cost:
                best_cost = route_cost
                best_source = source_component
                best_target = target_component
                best_chain = route_chain

        if best_source is None or best_target is None:
            break

        selected_candidates.extend(best_chain)
        attached_components.add(best_target)
        remaining_components.remove(best_target)
        if best_target in pass_through_components:
            attachable_components.add(best_target)

    return selected_candidates


def _dedupe_route_candidates(candidates: Iterable[_RouteCandidate]) -> list[_RouteCandidate]:
    deduped: list[_RouteCandidate] = []
    seen_pairs: set[frozenset[str]] = set()
    for candidate in sorted(candidates, key=lambda item: (item.cost, item.first_key, item.second_key)):
        candidate_pair = frozenset((candidate.first_key, candidate.second_key))
        if candidate_pair in seen_pairs:
            continue
        seen_pairs.add(candidate_pair)
        deduped.append(candidate)
    return deduped


def _suggestion_candidates(
    base: Any,
    terrain: TerrainGrid,
    grouped_keys: dict[int, list[str]],
    anchors_by_stop: dict[str, _VillageAnchor],
    component_by_key: dict[str, int],
) -> list[_RouteCandidate]:
    primary_component = _primary_walk_component_id(component_by_key, anchors_by_stop)
    if primary_component is None:
        return []

    direct_candidates = _tree_route_candidates(
        base,
        terrain,
        grouped_keys,
        anchors_by_stop,
        component_by_key,
        primary_component,
    )

    loop_candidates = _loop_candidates_for_direct_routes(
        base,
        terrain,
        anchors_by_stop,
        component_by_key,
        direct_candidates,
    )
    consolidated_candidates = _consolidated_candidates(base, direct_candidates, loop_candidates)
    stem_candidates = _consolidate_shared_stems(base, consolidated_candidates)
    fixed_endpoint_keys = {
        endpoint_key
        for endpoint_keys in grouped_keys.values()
        for endpoint_key in endpoint_keys
    }
    return _canonicalize_close_virtual_endpoints(base, stem_candidates, fixed_endpoint_keys)


def build_suggested_segments(base: Any, viewer: Any | None = None) -> tuple[SuggestedSegment, ...]:
    global _CACHE_KEY
    global _CACHE_VALUE

    anchors_by_stop = village_anchors(base)
    anchor_keys = tuple(dict.fromkeys(anchor.key for anchor in anchors_by_stop.values()))
    if len(anchor_keys) < 2:
        return ()

    component_by_key = _walk_component_index(base, anchors_by_stop.values())
    grouped_keys: dict[int, list[str]] = {}
    for endpoint_key, component_id in component_by_key.items():
        grouped_keys.setdefault(component_id, []).append(endpoint_key)
    for component_id in grouped_keys:
        grouped_keys[component_id].sort()

    if len(grouped_keys) < 2:
        return ()

    terrain = None
    terrain_metadata = (
        _terrain_metadata_from_viewer(viewer)
        if viewer is not None
        else None
    )
    if terrain_metadata is None and viewer is not None:
        terrain = _terrain_from_viewer(viewer)
        if terrain is not None:
            terrain_signature = terrain.signature
        else:
            terrain_signature = None
    else:
        terrain_signature = (
            _terrain_signature_from_metadata(terrain_metadata)
            if terrain_metadata is not None
            else None
        )
    if terrain_signature is None:
        return ()

    cache_key = (_network_signature(base), terrain_signature)
    if cache_key == _CACHE_KEY:
        return _CACHE_VALUE

    if terrain is None:
        assert terrain_metadata is not None
        min_x, max_x, min_z, max_z, source_image = terrain_metadata
        terrain = TerrainGrid(
            min_x=min_x,
            max_x=max_x,
            min_z=min_z,
            max_z=max_z,
            image=source_image,
        )

    candidates = _suggestion_candidates(
        base,
        terrain,
        grouped_keys,
        anchors_by_stop,
        component_by_key,
    )
    if not candidates:
        _CACHE_KEY = cache_key
        _CACHE_VALUE = ()
        return ()

    segments: list[SuggestedSegment] = []
    for candidate in candidates:
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


def _minecraft_buildable_path(
    points: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    if len(points) <= 1:
        return points

    buildable_points = [points[0]]
    for start_point, end_point in zip(points, points[1:]):
        for point in _minecraft_buildable_segment_points(start_point, end_point):
            if buildable_points[-1] != point:
                buildable_points.append(point)
    return tuple(buildable_points)


def _minecraft_buildable_segment_points(
    start_point: tuple[int, int],
    end_point: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    if _has_minecraft_buildable_slope(start_point, end_point):
        return (end_point,)

    delta_x = end_point[0] - start_point[0]
    delta_y = end_point[1] - start_point[1]
    abs_delta_x = abs(delta_x)
    abs_delta_y = abs(delta_y)
    sign_x = _sign(delta_x)
    sign_y = _sign(delta_y)

    if abs_delta_x > abs_delta_y:
        slope_denominator = max(1, abs_delta_x // abs_delta_y)
        sloped_delta_x = slope_denominator * abs_delta_y
        bend_point = (start_point[0] + (sign_x * sloped_delta_x), end_point[1])
    else:
        slope_numerator = max(1, abs_delta_y // abs_delta_x)
        sloped_delta_y = slope_numerator * abs_delta_x
        bend_point = (end_point[0], start_point[1] + (sign_y * sloped_delta_y))

    if bend_point in {start_point, end_point}:
        return (end_point,)
    return (bend_point, end_point)


def _has_minecraft_buildable_slope(
    first_point: tuple[int, int],
    second_point: tuple[int, int],
) -> bool:
    delta_x = abs(second_point[0] - first_point[0])
    delta_y = abs(second_point[1] - first_point[1])
    if delta_x == 0 or delta_y == 0:
        return True
    return delta_y % delta_x == 0 or delta_x % delta_y == 0
