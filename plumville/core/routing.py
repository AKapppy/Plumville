from __future__ import annotations

from dataclasses import dataclass
import heapq
from itertools import combinations
from typing import Callable, Literal, Sequence

RouteNode = tuple[str, str]
RouteKind = Literal["ride", "transfer", "connector", "walk", "fly"]


@dataclass(frozen=True, slots=True)
class RouteEdge:
    start: RouteNode
    end: RouteNode
    distance: int
    transfer_count: int
    kind: RouteKind
    line_name: str | None = None
    label: str | None = None
    path_points: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class RouteStep:
    kind: RouteKind
    start_key: str
    end_key: str
    distance: int
    path_points: tuple[tuple[int, int], ...]
    line_name: str | None = None
    label: str | None = None
    stop_vars: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        if self.kind == "ride":
            return f"Line {self.line_name}"
        if self.label:
            return self.label
        return self.kind.title()

    @property
    def stop_count(self) -> int:
        if len(self.stop_vars) < 2:
            return 0
        return max(0, len(self.stop_vars) - 1)


@dataclass(frozen=True, slots=True)
class RouteResult:
    start_key: str
    end_key: str
    total_distance: int
    total_interchanges: int
    steps: tuple[RouteStep, ...]


@dataclass(frozen=True, slots=True)
class RouteSearchResult:
    total_distance: int
    total_interchanges: int
    edges: tuple[RouteEdge, ...]


@dataclass(frozen=True, slots=True)
class RouteGraphStop:
    stop_key: str
    line_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RouteGraphLineSegment:
    line_name: str
    start_key: str
    end_key: str
    distance: int
    forward_path_points: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class RouteGraphEndpointEdge:
    from_endpoint_key: str
    to_endpoint_key: str
    from_is_coordinate: bool
    to_is_coordinate: bool
    distance: int
    kind: RouteKind
    label: str | None = None
    path_points: tuple[tuple[int, int], ...] = ()
    reverse_path_points: tuple[tuple[int, int], ...] = ()
    bidirectional: bool = False


def append_route_step(steps: list[RouteStep], edge: RouteEdge) -> None:
    start_key = edge.start[0]
    end_key = edge.end[0]

    if edge.kind == "transfer":
        steps.append(
            RouteStep(
                kind="transfer",
                start_key=start_key,
                end_key=end_key,
                distance=0,
                line_name=edge.line_name,
                label=edge.label,
                stop_vars=(start_key,),
                path_points=(),
            )
        )
        return

    if (
        steps
        and edge.kind == "ride"
        and steps[-1].kind == "ride"
        and steps[-1].line_name == edge.line_name
    ):
        previous_step = steps[-1]
        combined_stop_vars = previous_step.stop_vars
        if combined_stop_vars[-1] != end_key:
            combined_stop_vars = combined_stop_vars + (end_key,)
        combined_path_points = previous_step.path_points
        if combined_path_points and edge.path_points and combined_path_points[-1] == edge.path_points[0]:
            combined_path_points = combined_path_points + edge.path_points[1:]
        else:
            combined_path_points = combined_path_points + edge.path_points
        steps[-1] = RouteStep(
            kind="ride",
            start_key=previous_step.start_key,
            end_key=end_key,
            distance=previous_step.distance + edge.distance,
            line_name=previous_step.line_name,
            label=previous_step.label,
            stop_vars=combined_stop_vars,
            path_points=combined_path_points,
        )
        return

    if (
        steps
        and edge.kind == "walk"
        and steps[-1].kind == "walk"
        and (steps[-1].label or "") == (edge.label or "")
    ):
        previous_step = steps[-1]
        combined_path_points = previous_step.path_points
        if combined_path_points and edge.path_points and combined_path_points[-1] == edge.path_points[0]:
            combined_path_points = combined_path_points + edge.path_points[1:]
        else:
            combined_path_points = combined_path_points + edge.path_points
        steps[-1] = RouteStep(
            kind="walk",
            start_key=previous_step.start_key,
            end_key=end_key,
            distance=previous_step.distance + edge.distance,
            line_name=previous_step.line_name,
            label=previous_step.label,
            stop_vars=previous_step.stop_vars + (end_key,),
            path_points=combined_path_points,
        )
        return

    steps.append(
        RouteStep(
            kind=edge.kind,
            start_key=start_key,
            end_key=end_key,
            distance=edge.distance,
            line_name=edge.line_name,
            label=edge.label,
            stop_vars=(start_key, end_key),
            path_points=edge.path_points,
        )
    )


def unfinished_route_line_names(
    route: RouteResult,
    connected_stop_keys: frozenset[str],
) -> tuple[str, ...]:
    line_names: set[str] = set()
    for step in route.steps:
        if step.kind != "ride" or step.line_name is None or len(step.stop_vars) < 2:
            continue
        for start_key, end_key in zip(step.stop_vars, step.stop_vars[1:]):
            if start_key not in connected_stop_keys or end_key not in connected_stop_keys:
                line_names.add(step.line_name)
    return tuple(sorted(line_names))


def format_line_name_list(line_names: Sequence[str]) -> str:
    if not line_names:
        return ""
    if len(line_names) == 1:
        return line_names[0]
    if len(line_names) == 2:
        return f"{line_names[0]} and {line_names[1]}"
    return f"{', '.join(line_names[:-1])}, and {line_names[-1]}"


def format_route_instructions(
    route: RouteResult,
    *,
    endpoint_labeler: Callable[[str], str],
    format_track_distance: Callable[[int], str],
    format_distance_and_time: Callable[[int], str],
    format_travel_time_for_distance: Callable[[int], str],
    unfinished_line_names: tuple[str, ...] = (),
) -> str:
    start_label = endpoint_labeler(route.start_key)
    end_label = endpoint_labeler(route.end_key)
    if not route.steps:
        return (
            f"You are already at {start_label}.\n"
            f"Track distance: {format_track_distance(0)}."
        )

    rail_distance = sum(
        step.distance
        for step in route.steps
        if step.kind in {"ride", "connector"}
    )
    lines = [
        f"Track distance: {format_track_distance(route.total_distance)}",
        f"Rail time estimate: {format_travel_time_for_distance(rail_distance)}",
        f"Interchanges: {route.total_interchanges}",
        "",
    ]
    step_number = 1
    for step in route.steps:
        start_step_label = endpoint_labeler(step.start_key)
        end_step_label = endpoint_labeler(step.end_key)

        if step.kind == "ride":
            stop_word = "stop" if step.stop_count == 1 else "stops"
            lines.append(
                f"{step_number}. Take Line {step.line_name} from {start_step_label} "
                f"to {end_step_label} for {format_distance_and_time(step.distance)} "
                f"({step.stop_count} {stop_word})."
            )
        elif step.kind == "transfer":
            lines.append(
                f"{step_number}. Transfer at {start_step_label} to Line {step.line_name}."
            )
        elif step.kind == "connector":
            lines.append(
                f"{step_number}. Take {step.display_name.lower()} from {start_step_label} "
                f"to {end_step_label} for {format_distance_and_time(step.distance)}."
            )
        elif step.kind == "fly":
            lines.append(
                f"{step_number}. Fly directly from {start_step_label} to {end_step_label} "
                f"for {format_track_distance(step.distance)}."
            )
        else:
            if step.label and step.label != "Walk":
                lines.append(
                    f"{step_number}. Walk on {step.label} from {start_step_label} "
                    f"to {end_step_label} for {format_track_distance(step.distance)}."
                )
            else:
                lines.append(
                    f"{step_number}. Walk from {start_step_label} to {end_step_label} "
                    f"for {format_track_distance(step.distance)}."
                )
        step_number += 1

    lines.append("")
    if unfinished_line_names:
        line_word = "line is" if len(unfinished_line_names) == 1 else "lines are"
        lines.append(
            f"Warning: the {format_line_name_list(unfinished_line_names)} {line_word} "
            "not fully constructed for this route. Consider direct flying instead."
        )
        lines.append("")
    lines.append(f"Route from {start_label} to {end_label}.")
    return "\n".join(lines)


def append_graph_edge(
    graph: dict[RouteNode, list[RouteEdge]],
    edge: RouteEdge,
) -> None:
    graph.setdefault(edge.start, []).append(edge)


def ensure_graph_nodes(
    graph: dict[RouteNode, list[RouteEdge]],
    nodes: tuple[RouteNode, ...],
) -> None:
    for node in nodes:
        graph.setdefault(node, [])


def add_transfer_edges(
    graph: dict[RouteNode, list[RouteEdge]],
    stop_key: str,
    line_names: tuple[str, ...],
) -> None:
    ensure_graph_nodes(graph, tuple((stop_key, line_name) for line_name in line_names))

    for first_line, second_line in combinations(line_names, 2):
        first_node = (stop_key, first_line)
        second_node = (stop_key, second_line)
        append_graph_edge(
            graph,
            RouteEdge(
                start=first_node,
                end=second_node,
                distance=0,
                transfer_count=1,
                kind="transfer",
                line_name=second_line,
            ),
        )
        append_graph_edge(
            graph,
            RouteEdge(
                start=second_node,
                end=first_node,
                distance=0,
                transfer_count=1,
                kind="transfer",
                line_name=first_line,
            ),
        )


def add_bidirectional_ride_edges(
    graph: dict[RouteNode, list[RouteEdge]],
    *,
    line_name: str,
    start_key: str,
    end_key: str,
    distance: int,
    forward_path_points: tuple[tuple[int, int], ...],
) -> None:
    start_node = (start_key, line_name)
    end_node = (end_key, line_name)
    append_graph_edge(
        graph,
        RouteEdge(
            start=start_node,
            end=end_node,
            distance=distance,
            transfer_count=0,
            kind="ride",
            line_name=line_name,
            path_points=forward_path_points,
        ),
    )
    append_graph_edge(
        graph,
        RouteEdge(
            start=end_node,
            end=start_node,
            distance=distance,
            transfer_count=0,
            kind="ride",
            line_name=line_name,
            path_points=tuple(reversed(forward_path_points)),
        ),
    )


def add_endpoint_edges(
    graph: dict[RouteNode, list[RouteEdge]],
    *,
    start_nodes: tuple[RouteNode, ...],
    end_nodes: tuple[RouteNode, ...],
    distance: int,
    kind: RouteKind,
    label: str | None = None,
    path_points: tuple[tuple[int, int], ...] = (),
    reverse_path_points: tuple[tuple[int, int], ...] = (),
    bidirectional: bool = False,
) -> None:
    for start_node in start_nodes:
        for end_node in end_nodes:
            append_graph_edge(
                graph,
                RouteEdge(
                    start=start_node,
                    end=end_node,
                    distance=distance,
                    transfer_count=0,
                    kind=kind,
                    label=label,
                    path_points=path_points,
                ),
            )
            if bidirectional:
                append_graph_edge(
                    graph,
                    RouteEdge(
                        start=end_node,
                        end=start_node,
                        distance=distance,
                        transfer_count=0,
                        kind=kind,
                        label=label,
                        path_points=reverse_path_points,
                    ),
                )


def build_route_graph(
    *,
    stops: tuple[RouteGraphStop, ...],
    line_segments: tuple[RouteGraphLineSegment, ...],
    endpoint_edges: tuple[RouteGraphEndpointEdge, ...],
    coordinate_context: str,
    endpoint_node_resolver: Callable[
        [dict[RouteNode, list[RouteEdge]], str],
        list[RouteNode],
    ],
) -> dict[RouteNode, list[RouteEdge]]:
    graph: dict[RouteNode, list[RouteEdge]] = {}

    for stop in stops:
        add_transfer_edges(graph, stop.stop_key, stop.line_names)

    for segment in line_segments:
        add_bidirectional_ride_edges(
            graph,
            line_name=segment.line_name,
            start_key=segment.start_key,
            end_key=segment.end_key,
            distance=segment.distance,
            forward_path_points=segment.forward_path_points,
        )

    for endpoint_edge in endpoint_edges:
        if endpoint_edge.from_is_coordinate:
            ensure_graph_nodes(graph, ((endpoint_edge.from_endpoint_key, coordinate_context),))
        if endpoint_edge.to_is_coordinate:
            ensure_graph_nodes(graph, ((endpoint_edge.to_endpoint_key, coordinate_context),))

        start_nodes = endpoint_node_resolver(graph, endpoint_edge.from_endpoint_key)
        end_nodes = endpoint_node_resolver(graph, endpoint_edge.to_endpoint_key)
        if not start_nodes or not end_nodes:
            continue

        add_endpoint_edges(
            graph,
            start_nodes=tuple(start_nodes),
            end_nodes=tuple(end_nodes),
            distance=endpoint_edge.distance,
            kind=endpoint_edge.kind,
            label=endpoint_edge.label,
            path_points=endpoint_edge.path_points,
            reverse_path_points=endpoint_edge.reverse_path_points,
            bidirectional=endpoint_edge.bidirectional,
        )

    return graph


def standard_graph_nodes_for_endpoint(
    graph: dict[RouteNode, list[RouteEdge]],
    endpoint_key: str,
    *,
    excluded_contexts: tuple[str, ...] = (),
) -> list[RouteNode]:
    excluded_context_set = set(excluded_contexts)
    return sorted(
        node
        for node in graph
        if node[0] == endpoint_key and node[1] not in excluded_context_set
    )


def graph_nodes_for_endpoint(
    graph: dict[RouteNode, list[RouteEdge]],
    endpoint_key: str,
    *,
    expanded_endpoint_keys: tuple[str, ...] = (),
    preferred_context: str | None = None,
    excluded_contexts: tuple[str, ...] = (),
) -> list[RouteNode]:
    if expanded_endpoint_keys:
        expanded_nodes: list[RouteNode] = []
        for expanded_endpoint_key in expanded_endpoint_keys:
            expanded_nodes.extend(
                standard_graph_nodes_for_endpoint(
                    graph,
                    expanded_endpoint_key,
                    excluded_contexts=excluded_contexts,
                )
            )
        return sorted(dict.fromkeys(expanded_nodes))

    if preferred_context is not None:
        preferred_node = (endpoint_key, preferred_context)
        if preferred_node in graph:
            return [preferred_node]

    return standard_graph_nodes_for_endpoint(
        graph,
        endpoint_key,
        excluded_contexts=excluded_contexts,
    )


def shortest_route_edges(
    graph: dict[RouteNode, list[RouteEdge]],
    start_nodes: list[RouteNode] | tuple[RouteNode, ...],
    end_nodes: set[RouteNode] | frozenset[RouteNode] | list[RouteNode] | tuple[RouteNode, ...],
) -> RouteSearchResult | None:
    end_node_set = set(end_nodes)
    if not start_nodes or not end_node_set:
        return None

    best_costs: dict[RouteNode, tuple[int, int]] = {}
    predecessors: dict[RouteNode, tuple[RouteNode | None, RouteEdge | None]] = {}
    heap: list[tuple[int, int, RouteNode]] = []

    for start_node in start_nodes:
        best_costs[start_node] = (0, 0)
        predecessors[start_node] = (None, None)
        heapq.heappush(heap, (0, 0, start_node))

    best_end_node: RouteNode | None = None
    while heap:
        track_distance, transfer_count, node = heapq.heappop(heap)
        if (track_distance, transfer_count) != best_costs.get(node):
            continue
        if node in end_node_set:
            best_end_node = node
            break

        for edge in graph.get(node, []):
            next_node = edge.end
            next_cost = (
                track_distance + edge.distance,
                transfer_count + edge.transfer_count,
            )
            if next_cost < best_costs.get(next_node, (10**12, 10**12)):
                best_costs[next_node] = next_cost
                predecessors[next_node] = (node, edge)
                heapq.heappush(heap, (next_cost[0], next_cost[1], next_node))

    if best_end_node is None:
        return None

    route_edges: list[RouteEdge] = []
    cursor = best_end_node
    while True:
        previous_node, edge = predecessors[cursor]
        if edge is None or previous_node is None:
            break
        route_edges.append(edge)
        cursor = previous_node
    route_edges.reverse()

    total_distance, total_interchanges = best_costs[best_end_node]
    return RouteSearchResult(
        total_distance=total_distance,
        total_interchanges=total_interchanges,
        edges=tuple(route_edges),
    )


def route_costs_from_nodes(
    graph: dict[RouteNode, list[RouteEdge]],
    start_nodes: list[RouteNode] | tuple[RouteNode, ...],
) -> dict[RouteNode, tuple[int, int]]:
    best_costs: dict[RouteNode, tuple[int, int]] = {}
    heap: list[tuple[int, int, RouteNode]] = []
    for start_node in start_nodes:
        best_costs[start_node] = (0, 0)
        heapq.heappush(heap, (0, 0, start_node))

    while heap:
        track_distance, transfer_count, node = heapq.heappop(heap)
        if (track_distance, transfer_count) != best_costs.get(node):
            continue

        for edge in graph.get(node, []):
            next_node = edge.end
            next_cost = (
                track_distance + edge.distance,
                transfer_count + edge.transfer_count,
            )
            if next_cost < best_costs.get(next_node, (10**12, 10**12)):
                best_costs[next_node] = next_cost
                heapq.heappush(heap, (next_cost[0], next_cost[1], next_node))

    return best_costs
