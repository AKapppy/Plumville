from __future__ import annotations

import unittest

import legacy_core


class LegacyPathMetadataTests(unittest.TestCase):
    def test_station_entry_coordinates_anchor_stop_path_edges(self) -> None:
        payload = {
            "stops": [
                {
                    "var": "P_A",
                    "lbl": "A",
                    "x": 10,
                    "y": 20,
                    "station_entry_x": 12,
                    "station_entry_y": 22,
                    "has_connector": False,
                    "has_full_station": False,
                    "is_connected": False,
                    "has_finished_railway": False,
                    "has_signs": False,
                    "chime_directions": [],
                }
            ],
            "path_nodes": [],
            "extra_edges": [
                {
                    "id": "walk_a_node",
                    "kind": "walk",
                    "from_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "to_endpoint": {"kind": "coord", "x": 30, "y": 40},
                    "bidirectional": True,
                    "path_points": [{"x": 30, "y": 40}],
                }
            ],
            "alignment_reminders": [],
        }

        changed = legacy_core._normalize_extra_edges(payload)  # type: ignore[arg-type]

        self.assertTrue(changed)
        self.assertEqual(payload["extra_edges"][0]["path_points"], [])
        self.assertEqual(
            legacy_core._payload_endpoint_coordinates(
                payload,  # type: ignore[arg-type]
                {"kind": "stop", "stop_var": "P_A"},
            ),
            (12, 22),
        )

    def test_walking_paths_are_station_progress(self) -> None:
        incomplete = legacy_core.MetroStop(var="P_A", lbl="A", x=0, y=0)
        complete = legacy_core.MetroStop(var="P_A", lbl="A", x=0, y=0, has_walking_paths=True)

        self.assertIn("walking paths", legacy_core._missing_station_tasks(incomplete))
        self.assertEqual(complete.checkpoint_count, incomplete.checkpoint_count + 1)

    def test_adjacent_same_named_walk_edges_merge_into_one_step(self) -> None:
        steps: list[legacy_core.RouteStep] = []
        first_edge = legacy_core.RouteEdge(
            start=("coord:0,0", legacy_core.COORDINATE_NODE_CONTEXT),
            end=("coord:10,0", legacy_core.COORDINATE_NODE_CONTEXT),
            distance=10,
            transfer_count=0,
            kind="walk",
            label="Oak Road",
            path_points=((0, 0), (10, 0)),
        )
        second_edge = legacy_core.RouteEdge(
            start=("coord:10,0", legacy_core.COORDINATE_NODE_CONTEXT),
            end=("coord:20,0", legacy_core.COORDINATE_NODE_CONTEXT),
            distance=10,
            transfer_count=0,
            kind="walk",
            label="Oak Road",
            path_points=((10, 0), (20, 0)),
        )

        legacy_core._append_route_step(steps, first_edge)
        legacy_core._append_route_step(steps, second_edge)

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].label, "Oak Road")
        self.assertEqual(steps[0].distance, 20)
        self.assertEqual(steps[0].path_points, ((0, 0), (10, 0), (20, 0)))

    def test_city_limit_endpoint_uses_boundary_nodes(self) -> None:
        previous_stops_by_var = legacy_core.STOPS_BY_VAR
        previous_stops_by_lbl = legacy_core.STOPS_BY_LBL
        previous_path_nodes_by_key = legacy_core.PATH_NODES_BY_KEY
        previous_path_nodes = legacy_core.PATH_NODES
        try:
            stop = legacy_core.MetroStop(
                var="P_CITY",
                lbl="City",
                x=100,
                y=100,
                city_limit_node_keys=("coord:0,0", "coord:10,0", "coord:10,10"),
            )
            legacy_core.STOPS_BY_VAR = {stop.var: stop}
            legacy_core.STOPS_BY_LBL = {stop.lbl: stop}
            legacy_core.PATH_NODES = ()
            legacy_core.PATH_NODES_BY_KEY = {}

            endpoint = legacy_core._path_endpoint_from_runtime_identifier("City limits: City")
            graph = {
                ("coord:0,0", legacy_core.COORDINATE_NODE_CONTEXT): [],
                ("coord:10,0", legacy_core.COORDINATE_NODE_CONTEXT): [],
                ("coord:99,99", legacy_core.COORDINATE_NODE_CONTEXT): [],
            }

            self.assertIsNotNone(endpoint)
            assert endpoint is not None
            self.assertEqual(endpoint.kind, "city_limit")
            self.assertEqual(endpoint.coordinates, (7, 3))
            self.assertEqual(
                legacy_core._graph_nodes_for_endpoint(graph, endpoint.key),
                [
                    ("coord:0,0", legacy_core.COORDINATE_NODE_CONTEXT),
                    ("coord:10,0", legacy_core.COORDINATE_NODE_CONTEXT),
                ],
            )
        finally:
            legacy_core.STOPS_BY_VAR = previous_stops_by_var
            legacy_core.STOPS_BY_LBL = previous_stops_by_lbl
            legacy_core.PATH_NODES_BY_KEY = previous_path_nodes_by_key
            legacy_core.PATH_NODES = previous_path_nodes

    def test_station_endpoint_uses_closest_point_on_city_path_when_walks_done(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        previous_stops_by_var = legacy_core.STOPS_BY_VAR
        previous_stops_by_lbl = legacy_core.STOPS_BY_LBL
        previous_extra_edges = legacy_core.EXTRA_EDGES
        try:
            stop = legacy_core.MetroStop(
                var="P_CITY",
                lbl="City",
                x=5,
                y=2,
                has_walking_paths=True,
                city_limit_node_keys=("coord:0,0", "coord:10,0", "coord:10,10", "coord:0,10"),
            )
            legacy_core.METRO_STOPS = previous_metro_stops + (stop,)
            legacy_core.STOPS_BY_VAR = {**previous_stops_by_var, stop.var: stop}
            legacy_core.STOPS_BY_LBL = {**previous_stops_by_lbl, stop.lbl: stop}
            legacy_core.EXTRA_EDGES = (
                legacy_core.ExtraEdgeDefinition(
                    id="walk_inside_city",
                    kind="walk",
                    from_endpoint=legacy_core.PathEndpoint(kind="coord", key="coord:0,5", x=0, y=5),
                    to_endpoint=legacy_core.PathEndpoint(kind="coord", key="coord:10,5", x=10, y=5),
                    path_points=((0, 5), (10, 5)),
                ),
            )

            graph = legacy_core._build_route_graph(allow_connector=False, allow_walk=True)
            station_nodes = legacy_core._graph_nodes_for_endpoint(graph, "P_CITY")

            self.assertEqual(
                station_nodes,
                [("P_CITY", legacy_core.STATION_CITY_PATH_CONTEXT)],
            )
            outgoing_edges = graph[station_nodes[0]]
            self.assertEqual(
                sorted((edge.end, edge.distance, edge.path_points[0]) for edge in outgoing_edges),
                [
                    (("coord:0,5", legacy_core.COORDINATE_NODE_CONTEXT), 5, (5, -5)),
                    (("coord:10,5", legacy_core.COORDINATE_NODE_CONTEXT), 5, (5, -5)),
                ],
            )
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops
            legacy_core.STOPS_BY_VAR = previous_stops_by_var
            legacy_core.STOPS_BY_LBL = previous_stops_by_lbl
            legacy_core.EXTRA_EDGES = previous_extra_edges

    def test_normalize_city_limits_keeps_known_path_node_keys(self) -> None:
        payload = {
            "stops": [
                {
                    "var": "P_A",
                    "lbl": "A",
                    "x": 0,
                    "y": 0,
                    "city_limit_node_keys": ["coord:1,1", "1, 1", "coord:9,9"],
                }
            ],
            "path_nodes": [{"id": "node_1", "x": 1, "y": 1}],
            "extra_edges": [],
        }

        changed = legacy_core._normalize_city_limits(payload)  # type: ignore[arg-type]

        self.assertTrue(changed)
        self.assertEqual(payload["stops"][0]["city_limit_node_keys"], ["coord:1,1"])


if __name__ == "__main__":
    unittest.main()
