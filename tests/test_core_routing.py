from __future__ import annotations

import unittest
from unittest import mock

import legacy_core as base
from plumville.core import routing


class CoreRoutingTests(unittest.TestCase):
    def test_legacy_route_models_alias_core_models(self) -> None:
        self.assertIs(base.RouteEdge, routing.RouteEdge)
        self.assertIs(base.RouteStep, routing.RouteStep)
        self.assertIs(base.RouteResult, routing.RouteResult)

    def test_route_step_display_name_and_stop_count(self) -> None:
        ride_step = routing.RouteStep(
            kind="ride",
            start_key="P_A",
            end_key="P_B",
            distance=80,
            line_name="A",
            stop_vars=("P_A", "P_B", "P_C"),
            path_points=((0, 0), (80, 0)),
        )
        walk_step = routing.RouteStep(
            kind="walk",
            start_key="coord:0,0",
            end_key="coord:5,0",
            distance=5,
            label="Oak Road",
            path_points=((0, 0), (5, 0)),
        )
        transfer_step = routing.RouteStep(
            kind="transfer",
            start_key="P_A",
            end_key="P_A",
            distance=0,
            path_points=(),
        )

        self.assertEqual(ride_step.display_name, "Line A")
        self.assertEqual(ride_step.stop_count, 2)
        self.assertEqual(walk_step.display_name, "Oak Road")
        self.assertEqual(transfer_step.display_name, "Transfer")
        self.assertEqual(transfer_step.stop_count, 0)

    def test_unfinished_route_line_names_flags_lines_with_unconnected_ride_stops(self) -> None:
        route = routing.RouteResult(
            start_key="P_A",
            end_key="P_D",
            total_distance=150,
            total_interchanges=0,
            steps=(
                routing.RouteStep(
                    kind="ride",
                    start_key="P_A",
                    end_key="P_C",
                    distance=100,
                    line_name="A",
                    stop_vars=("P_A", "P_B", "P_C"),
                    path_points=((0, 0), (100, 0)),
                ),
                routing.RouteStep(
                    kind="walk",
                    start_key="P_C",
                    end_key="P_D",
                    distance=50,
                    label="Oak Road",
                    stop_vars=("P_C", "P_D"),
                    path_points=((100, 0), (150, 0)),
                ),
            ),
        )

        self.assertEqual(
            routing.unfinished_route_line_names(route, frozenset({"P_A", "P_B"})),
            ("A",),
        )
        self.assertEqual(
            routing.unfinished_route_line_names(route, frozenset({"P_A", "P_B", "P_C"})),
            (),
        )

    def test_format_line_name_list_uses_readable_joining(self) -> None:
        self.assertEqual(routing.format_line_name_list(()), "")
        self.assertEqual(routing.format_line_name_list(("A",)), "A")
        self.assertEqual(routing.format_line_name_list(("A", "B")), "A and B")
        self.assertEqual(routing.format_line_name_list(("A", "B", "C")), "A, B, and C")
        self.assertEqual(base._format_line_name_list(("A", "B", "C")), "A, B, and C")

    def test_format_route_instructions_builds_steps_and_unfinished_warning(self) -> None:
        labels = {
            "P_A": "Alpha",
            "P_B": "Beta",
            "P_C": "Gamma",
            "coord:1,1": "1, 1",
        }
        route = routing.RouteResult(
            start_key="P_A",
            end_key="coord:1,1",
            total_distance=150,
            total_interchanges=1,
            steps=(
                routing.RouteStep(
                    kind="ride",
                    start_key="P_A",
                    end_key="P_B",
                    distance=80,
                    line_name="A",
                    stop_vars=("P_A", "P_B"),
                    path_points=((0, 0), (80, 0)),
                ),
                routing.RouteStep(
                    kind="transfer",
                    start_key="P_B",
                    end_key="P_B",
                    distance=0,
                    line_name="B",
                    stop_vars=("P_B",),
                    path_points=(),
                ),
                routing.RouteStep(
                    kind="connector",
                    start_key="P_B",
                    end_key="P_C",
                    distance=40,
                    label="Metro Connector",
                    stop_vars=("P_B", "P_C"),
                    path_points=((80, 0), (120, 0)),
                ),
                routing.RouteStep(
                    kind="walk",
                    start_key="P_C",
                    end_key="coord:1,1",
                    distance=30,
                    label="Oak Road",
                    stop_vars=("P_C", "coord:1,1"),
                    path_points=((120, 0), (150, 0)),
                ),
            ),
        )

        instructions = routing.format_route_instructions(
            route,
            endpoint_labeler=lambda key: labels[key],
            format_track_distance=lambda distance: f"{distance} m",
            format_distance_and_time=lambda distance: f"{distance} m / {distance // 8}s",
            format_travel_time_for_distance=lambda distance: f"{distance // 8}s",
            unfinished_line_names=("A", "B"),
        )

        self.assertIn("Track distance: 150 m", instructions)
        self.assertIn("Rail time estimate: 15s", instructions)
        self.assertIn("1. Take Line A from Alpha to Beta for 80 m / 10s (1 stop).", instructions)
        self.assertIn("2. Transfer at Beta to Line B.", instructions)
        self.assertIn("3. Take metro connector from Beta to Gamma for 40 m / 5s.", instructions)
        self.assertIn("4. Walk on Oak Road from Gamma to 1, 1 for 30 m.", instructions)
        self.assertIn("Warning: the A and B lines are not fully constructed", instructions)
        self.assertTrue(instructions.endswith("Route from Alpha to 1, 1."))

    def test_format_route_instructions_handles_zero_step_route(self) -> None:
        route = routing.RouteResult(
            start_key="P_A",
            end_key="P_A",
            total_distance=0,
            total_interchanges=0,
            steps=(),
        )

        instructions = routing.format_route_instructions(
            route,
            endpoint_labeler=lambda _key: "Alpha",
            format_track_distance=lambda distance: f"{distance} m",
            format_distance_and_time=lambda distance: f"{distance} m",
            format_travel_time_for_distance=lambda _distance: "0s",
        )

        self.assertEqual(instructions, "You are already at Alpha.\nTrack distance: 0 m.")

    def test_adjacent_same_line_ride_edges_merge_into_one_step(self) -> None:
        steps: list[routing.RouteStep] = []
        first_edge = routing.RouteEdge(
            start=("P_A", "A"),
            end=("P_B", "A"),
            distance=80,
            transfer_count=0,
            kind="ride",
            line_name="A",
            path_points=((0, 0), (80, 0)),
        )
        second_edge = routing.RouteEdge(
            start=("P_B", "A"),
            end=("P_C", "A"),
            distance=120,
            transfer_count=0,
            kind="ride",
            line_name="A",
            path_points=((80, 0), (200, 0)),
        )

        routing.append_route_step(steps, first_edge)
        routing.append_route_step(steps, second_edge)

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].distance, 200)
        self.assertEqual(steps[0].stop_vars, ("P_A", "P_B", "P_C"))
        self.assertEqual(steps[0].path_points, ((0, 0), (80, 0), (200, 0)))

    def test_adjacent_same_named_walk_edges_merge_into_one_step(self) -> None:
        steps: list[routing.RouteStep] = []
        first_edge = routing.RouteEdge(
            start=("coord:0,0", "__coord__"),
            end=("coord:10,0", "__coord__"),
            distance=10,
            transfer_count=0,
            kind="walk",
            label="Oak Road",
            path_points=((0, 0), (10, 0)),
        )
        second_edge = routing.RouteEdge(
            start=("coord:10,0", "__coord__"),
            end=("coord:20,0", "__coord__"),
            distance=10,
            transfer_count=0,
            kind="walk",
            label="Oak Road",
            path_points=((10, 0), (20, 0)),
        )

        routing.append_route_step(steps, first_edge)
        routing.append_route_step(steps, second_edge)

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].label, "Oak Road")
        self.assertEqual(steps[0].distance, 20)
        self.assertEqual(steps[0].path_points, ((0, 0), (10, 0), (20, 0)))

    def test_legacy_append_route_step_wrapper_uses_core_behavior(self) -> None:
        steps: list[base.RouteStep] = []
        edge = base.RouteEdge(
            start=("P_A", "A"),
            end=("P_B", "A"),
            distance=80,
            transfer_count=0,
            kind="ride",
            line_name="A",
            path_points=((0, 0), (80, 0)),
        )

        base._append_route_step(steps, edge)

        self.assertEqual(steps, [
            routing.RouteStep(
                kind="ride",
                start_key="P_A",
                end_key="P_B",
                distance=80,
                line_name="A",
                stop_vars=("P_A", "P_B"),
                path_points=((0, 0), (80, 0)),
            )
        ])

    def test_legacy_unfinished_route_line_names_wrapper_uses_core_behavior(self) -> None:
        connected_stop = base.MetroStop(var="P_A", lbl="A", x=0, y=0, is_connected=True)
        unfinished_stop = base.MetroStop(var="P_B", lbl="B", x=100, y=0, is_connected=False)
        route = base.RouteResult(
            start_key="P_A",
            end_key="P_B",
            total_distance=100,
            total_interchanges=0,
            steps=(
                base.RouteStep(
                    kind="ride",
                    start_key="P_A",
                    end_key="P_B",
                    distance=100,
                    line_name="A",
                    stop_vars=("P_A", "P_B"),
                    path_points=((0, 0), (100, 0)),
                ),
            ),
        )

        with mock.patch.object(
            base,
            "STOPS_BY_VAR",
            {"P_A": connected_stop, "P_B": unfinished_stop},
        ):
            self.assertEqual(base._unfinished_route_line_names(route), ("A",))

    def test_append_graph_edge_adds_edge_to_start_node(self) -> None:
        edge = routing.RouteEdge(
            start=("P_A", "A"),
            end=("P_B", "A"),
            distance=30,
            transfer_count=0,
            kind="ride",
            line_name="A",
        )
        graph: dict[routing.RouteNode, list[routing.RouteEdge]] = {}

        routing.append_graph_edge(graph, edge)

        self.assertEqual(graph, {("P_A", "A"): [edge]})

    def test_ensure_graph_nodes_initializes_empty_adjacency_lists(self) -> None:
        graph: dict[routing.RouteNode, list[routing.RouteEdge]] = {}

        routing.ensure_graph_nodes(graph, (("P_A", "A"), ("P_A", "B")))

        self.assertEqual(graph, {("P_A", "A"): [], ("P_A", "B"): []})

    def test_add_transfer_edges_adds_all_line_interchanges(self) -> None:
        graph: dict[routing.RouteNode, list[routing.RouteEdge]] = {}

        routing.add_transfer_edges(graph, "P_A", ("A", "B", "C"))

        self.assertEqual(set(graph), {("P_A", "A"), ("P_A", "B"), ("P_A", "C")})
        self.assertEqual(len(graph[("P_A", "A")]), 2)
        self.assertIn(
            routing.RouteEdge(
                start=("P_A", "A"),
                end=("P_A", "B"),
                distance=0,
                transfer_count=1,
                kind="transfer",
                line_name="B",
            ),
            graph[("P_A", "A")],
        )
        self.assertIn(
            routing.RouteEdge(
                start=("P_A", "C"),
                end=("P_A", "A"),
                distance=0,
                transfer_count=1,
                kind="transfer",
                line_name="A",
            ),
            graph[("P_A", "C")],
        )

    def test_add_bidirectional_ride_edges_adds_forward_and_reverse_paths(self) -> None:
        graph: dict[routing.RouteNode, list[routing.RouteEdge]] = {}

        routing.add_bidirectional_ride_edges(
            graph,
            line_name="A",
            start_key="P_A",
            end_key="P_B",
            distance=100,
            forward_path_points=((0, 0), (50, 0), (100, 0)),
        )

        self.assertEqual(
            graph[("P_A", "A")],
            [
                routing.RouteEdge(
                    start=("P_A", "A"),
                    end=("P_B", "A"),
                    distance=100,
                    transfer_count=0,
                    kind="ride",
                    line_name="A",
                    path_points=((0, 0), (50, 0), (100, 0)),
                )
            ],
        )
        self.assertEqual(
            graph[("P_B", "A")],
            [
                routing.RouteEdge(
                    start=("P_B", "A"),
                    end=("P_A", "A"),
                    distance=100,
                    transfer_count=0,
                    kind="ride",
                    line_name="A",
                    path_points=((100, 0), (50, 0), (0, 0)),
                )
            ],
        )

    def test_add_endpoint_edges_adds_cartesian_bidirectional_edges(self) -> None:
        graph: dict[routing.RouteNode, list[routing.RouteEdge]] = {}

        routing.add_endpoint_edges(
            graph,
            start_nodes=(("P_A", "A"), ("P_A", "B")),
            end_nodes=(("coord:1,1", "__coord__"),),
            distance=12,
            kind="walk",
            label="Oak Road",
            path_points=((0, 0), (1, -1)),
            reverse_path_points=((1, -1), (0, 0)),
            bidirectional=True,
        )

        self.assertEqual(len(graph[("P_A", "A")]), 1)
        self.assertEqual(len(graph[("P_A", "B")]), 1)
        self.assertEqual(
            graph[("coord:1,1", "__coord__")],
            [
                routing.RouteEdge(
                    start=("coord:1,1", "__coord__"),
                    end=("P_A", "A"),
                    distance=12,
                    transfer_count=0,
                    kind="walk",
                    label="Oak Road",
                    path_points=((1, -1), (0, 0)),
                ),
                routing.RouteEdge(
                    start=("coord:1,1", "__coord__"),
                    end=("P_A", "B"),
                    distance=12,
                    transfer_count=0,
                    kind="walk",
                    label="Oak Road",
                    path_points=((1, -1), (0, 0)),
                ),
            ],
        )

    def test_build_route_graph_adds_stops_segments_and_endpoint_edges(self) -> None:
        def endpoint_node_resolver(
            graph: dict[routing.RouteNode, list[routing.RouteEdge]],
            endpoint_key: str,
        ) -> list[routing.RouteNode]:
            return routing.graph_nodes_for_endpoint(graph, endpoint_key)

        graph = routing.build_route_graph(
            stops=(
                routing.RouteGraphStop("P_A", ("A",)),
                routing.RouteGraphStop("P_B", ("A",)),
            ),
            line_segments=(
                routing.RouteGraphLineSegment(
                    line_name="A",
                    start_key="P_A",
                    end_key="P_B",
                    distance=100,
                    forward_path_points=((0, 0), (100, 0)),
                ),
            ),
            endpoint_edges=(
                routing.RouteGraphEndpointEdge(
                    from_endpoint_key="P_B",
                    to_endpoint_key="coord:1,1",
                    from_is_coordinate=False,
                    to_is_coordinate=True,
                    distance=12,
                    kind="walk",
                    label="Oak Road",
                    path_points=((100, 0), (101, -1)),
                    reverse_path_points=((101, -1), (100, 0)),
                    bidirectional=True,
                ),
            ),
            coordinate_context="__coord__",
            endpoint_node_resolver=endpoint_node_resolver,
        )

        self.assertEqual(set(graph), {("P_A", "A"), ("P_B", "A"), ("coord:1,1", "__coord__")})
        self.assertIn(
            routing.RouteEdge(
                start=("P_A", "A"),
                end=("P_B", "A"),
                distance=100,
                transfer_count=0,
                kind="ride",
                line_name="A",
                path_points=((0, 0), (100, 0)),
            ),
            graph[("P_A", "A")],
        )
        self.assertIn(
            routing.RouteEdge(
                start=("P_B", "A"),
                end=("coord:1,1", "__coord__"),
                distance=12,
                transfer_count=0,
                kind="walk",
                label="Oak Road",
                path_points=((100, 0), (101, -1)),
            ),
            graph[("P_B", "A")],
        )
        self.assertEqual(
            graph[("coord:1,1", "__coord__")],
            [
                routing.RouteEdge(
                    start=("coord:1,1", "__coord__"),
                    end=("P_B", "A"),
                    distance=12,
                    transfer_count=0,
                    kind="walk",
                    label="Oak Road",
                    path_points=((101, -1), (100, 0)),
                )
            ],
        )

    def test_standard_graph_nodes_for_endpoint_excludes_contexts(self) -> None:
        graph: dict[routing.RouteNode, list[routing.RouteEdge]] = {
            ("P_A", "A"): [],
            ("P_A", "station_city_path"): [],
            ("P_A", "B"): [],
            ("P_B", "A"): [],
        }

        nodes = routing.standard_graph_nodes_for_endpoint(
            graph,
            "P_A",
            excluded_contexts=("station_city_path",),
        )

        self.assertEqual(nodes, [("P_A", "A"), ("P_A", "B")])

    def test_graph_nodes_for_endpoint_prefers_context_or_expands_keys(self) -> None:
        graph: dict[routing.RouteNode, list[routing.RouteEdge]] = {
            ("P_CITY", "A"): [],
            ("P_CITY", "station_city_path"): [],
            ("coord:1,1", "__coord__"): [],
            ("coord:2,2", "__coord__"): [],
            ("coord:2,2", "station_city_path"): [],
        }

        self.assertEqual(
            routing.graph_nodes_for_endpoint(
                graph,
                "P_CITY",
                preferred_context="station_city_path",
                excluded_contexts=("station_city_path",),
            ),
            [("P_CITY", "station_city_path")],
        )
        self.assertEqual(
            routing.graph_nodes_for_endpoint(
                graph,
                "city-limit:P_CITY",
                expanded_endpoint_keys=("coord:2,2", "coord:1,1"),
                excluded_contexts=("station_city_path",),
            ),
            [("coord:1,1", "__coord__"), ("coord:2,2", "__coord__")],
        )

    def test_shortest_route_edges_prefers_distance_then_transfer_count(self) -> None:
        direct_edge = routing.RouteEdge(
            start=("P_A", "A"),
            end=("P_D", "A"),
            distance=100,
            transfer_count=0,
            kind="ride",
            line_name="A",
        )
        transfer_edge = routing.RouteEdge(
            start=("P_A", "A"),
            end=("P_D", "B"),
            distance=80,
            transfer_count=1,
            kind="transfer",
            line_name="B",
        )
        first_ride_edge = routing.RouteEdge(
            start=("P_A", "A"),
            end=("P_B", "A"),
            distance=40,
            transfer_count=0,
            kind="ride",
            line_name="A",
        )
        second_ride_edge = routing.RouteEdge(
            start=("P_B", "A"),
            end=("P_D", "A"),
            distance=40,
            transfer_count=0,
            kind="ride",
            line_name="A",
        )
        graph = {
            ("P_A", "A"): [direct_edge, transfer_edge, first_ride_edge],
            ("P_B", "A"): [second_ride_edge],
        }

        result = routing.shortest_route_edges(graph, [("P_A", "A")], {("P_D", "A"), ("P_D", "B")})

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.total_distance, 80)
        self.assertEqual(result.total_interchanges, 0)
        self.assertEqual(result.edges, (first_ride_edge, second_ride_edge))

    def test_shortest_route_edges_returns_none_without_reachable_end(self) -> None:
        graph = {
            ("P_A", "A"): [
                routing.RouteEdge(
                    start=("P_A", "A"),
                    end=("P_B", "A"),
                    distance=40,
                    transfer_count=0,
                    kind="ride",
                    line_name="A",
                )
            ]
        }

        result = routing.shortest_route_edges(graph, [("P_A", "A")], {("P_Z", "Z")})

        self.assertIsNone(result)

    def test_route_costs_from_nodes_returns_best_costs(self) -> None:
        slower_edge = routing.RouteEdge(
            start=("P_A", "A"),
            end=("P_C", "A"),
            distance=70,
            transfer_count=0,
            kind="ride",
            line_name="A",
        )
        first_fast_edge = routing.RouteEdge(
            start=("P_A", "A"),
            end=("P_B", "A"),
            distance=30,
            transfer_count=0,
            kind="ride",
            line_name="A",
        )
        second_fast_edge = routing.RouteEdge(
            start=("P_B", "A"),
            end=("P_C", "A"),
            distance=30,
            transfer_count=0,
            kind="ride",
            line_name="A",
        )
        graph = {
            ("P_A", "A"): [slower_edge, first_fast_edge],
            ("P_B", "A"): [second_fast_edge],
        }

        costs = routing.route_costs_from_nodes(graph, [("P_A", "A")])

        self.assertEqual(costs[("P_A", "A")], (0, 0))
        self.assertEqual(costs[("P_B", "A")], (30, 0))
        self.assertEqual(costs[("P_C", "A")], (60, 0))


if __name__ == "__main__":
    unittest.main()
