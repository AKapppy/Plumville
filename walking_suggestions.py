from __future__ import annotations

from dataclasses import dataclass
from math import dist
from typing import Iterable


ANCHOR_NODE_MAX_DISTANCE = 96.0


@dataclass(frozen=True, slots=True)
class SuggestedSegment:
    start_coordinates: tuple[int, int]
    end_coordinates: tuple[int, int]
    start_key: str
    end_key: str
    start_label: str
    end_label: str
    length: float


def _is_explicit_node(node: object) -> bool:
    return bool(getattr(node, "is_explicit", False))


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
        if not _is_explicit_node(node):
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


def build_suggested_segments(base: object) -> tuple[SuggestedSegment, ...]:
    anchors_by_stop = village_anchor_keys(base)
    anchor_keys = tuple(dict.fromkeys(anchors_by_stop.values()))
    if len(anchor_keys) < 2:
        return ()

    component_by_key = _walk_component_index(base, anchor_keys)
    grouped_keys: dict[int, list[str]] = {}
    for endpoint_key in anchor_keys:
        grouped_keys.setdefault(component_by_key[endpoint_key], []).append(endpoint_key)

    component_ids = sorted(grouped_keys)
    if len(component_ids) < 2:
        return ()

    candidate_edges: list[tuple[float, str, str, int, int]] = []
    for first_index, first_component in enumerate(component_ids):
        for second_component in component_ids[first_index + 1:]:
            best_pair = None
            for first_key in grouped_keys[first_component]:
                first_coordinates = _endpoint_coordinates(base, first_key)
                for second_key in grouped_keys[second_component]:
                    second_coordinates = _endpoint_coordinates(base, second_key)
                    edge_length = dist(first_coordinates, second_coordinates)
                    edge_candidate = (
                        edge_length,
                        first_key,
                        second_key,
                        first_component,
                        second_component,
                    )
                    if best_pair is None or edge_candidate < best_pair:
                        best_pair = edge_candidate
            if best_pair is not None:
                candidate_edges.append(best_pair)

    candidate_edges.sort()

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

    segments: list[SuggestedSegment] = []
    for edge_length, first_key, second_key, first_component, second_component in candidate_edges:
        if not union(first_component, second_component):
            continue
        first_coordinates = _endpoint_coordinates(base, first_key)
        second_coordinates = _endpoint_coordinates(base, second_key)
        segments.append(
            SuggestedSegment(
                start_coordinates=first_coordinates,
                end_coordinates=second_coordinates,
                start_key=first_key,
                end_key=second_key,
                start_label=_display_label_for(base, first_key),
                end_label=_display_label_for(base, second_key),
                length=edge_length,
            )
        )

    return tuple(segments)
