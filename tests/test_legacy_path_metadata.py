from __future__ import annotations

import unittest
from unittest import mock

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

        self.assertIn("paths", legacy_core._missing_station_tasks(incomplete))
        self.assertEqual(complete.checkpoint_count, incomplete.checkpoint_count + 1)

    def test_station_entry_appears_in_checklist_summary(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        try:
            legacy_core.METRO_STOPS = (
                legacy_core.MetroStop(var="P_A", lbl="A", x=0, y=0, station_entry_x=1, station_entry_y=2),
                legacy_core.MetroStop(var="P_B", lbl="B", x=10, y=10),
            )
            with mock.patch.object(
                legacy_core,
                "_world_map_checklist_completion_line",
                return_value=None,
            ):
                summary = legacy_core._station_progress_summary_text()

            self.assertIn("Station Entrances: 1/2", summary)
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops

    def test_completed_checklist_items_disappear(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        previous_stop_line_names = legacy_core.STOP_LINE_NAMES
        try:
            stop = legacy_core.MetroStop(
                var="P_A",
                lbl="Alpha",
                x=0,
                y=0,
                has_connector=True,
                has_full_station=True,
                has_walking_paths=True,
                is_connected=True,
                has_finished_railway=True,
                has_signs=True,
                station_entry_x=1,
                station_entry_y=2,
                city_limit_node_keys=("coord:1,1", "coord:2,2", "coord:3,3"),
            )
            legacy_core.METRO_STOPS = (stop,)
            legacy_core.STOP_LINE_NAMES = {stop.var: ()}
            with mock.patch.object(
                legacy_core,
                "_world_map_checklist_completion_line",
                return_value=None,
            ):
                summary = legacy_core._station_progress_summary_text()

            self.assertEqual(summary, "")
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops
            legacy_core.STOP_LINE_NAMES = previous_stop_line_names

    def test_waiting_for_connections_checklist_items_hide_until_needed(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        try:
            legacy_core.METRO_STOPS = (
                legacy_core.MetroStop(var="P_A", lbl="A", x=0, y=0),
            )
            with mock.patch.object(
                legacy_core,
                "_world_map_checklist_completion_line",
                return_value=None,
            ):
                summary = legacy_core._station_progress_summary_text()

            self.assertNotIn("Finished Railway:", summary)
            self.assertNotIn("Signs:", summary)
            self.assertNotIn("Chimes:", summary)
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops

    def test_signs_are_available_after_station_is_built(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        try:
            needs_signs = legacy_core.MetroStop(
                var="P_A",
                lbl="Alpha",
                x=0,
                y=0,
                has_full_station=True,
            )
            has_signs = legacy_core.MetroStop(
                var="P_A",
                lbl="Alpha",
                x=0,
                y=0,
                has_full_station=True,
                has_signs=True,
            )

            self.assertFalse(needs_signs.is_connected)
            self.assertIn("signs", legacy_core._missing_station_tasks(needs_signs))
            self.assertEqual(has_signs.checkpoint_count, needs_signs.checkpoint_count + 1)

            legacy_core.METRO_STOPS = (needs_signs,)
            with mock.patch.object(
                legacy_core,
                "_world_map_checklist_completion_line",
                return_value=None,
            ):
                summary = legacy_core._station_progress_summary_text()

            self.assertIn("Signs: 0/1", summary)
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops

    def test_station_priority_entry_includes_station_village_tasks(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        previous_stops_by_var = legacy_core.STOPS_BY_VAR
        previous_stop_line_names = legacy_core.STOP_LINE_NAMES
        previous_line_stop_vars = legacy_core.LINE_STOP_VARS
        try:
            stop = legacy_core.MetroStop(
                var="P_V",
                lbl="Village",
                x=0,
                y=0,
                is_connected=True,
                has_connector=True,
                has_full_station=True,
                has_finished_railway=True,
                has_signs=True,
            )
            legacy_core.METRO_STOPS = (stop,)
            legacy_core.STOPS_BY_VAR = {stop.var: stop}
            legacy_core.STOP_LINE_NAMES = {stop.var: ("A",)}
            legacy_core.LINE_STOP_VARS = {"A": (stop.var,)}

            with mock.patch.object(
                legacy_core,
                "_route_costs_from_endpoint_key",
                return_value={stop.var: (0, 0)},
            ):
                entries = legacy_core._priority_list_entries(stop.var)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0][0], stop.var)
            self.assertIn("needs station entrance, paths, and city limits", entries[0][1])
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops
            legacy_core.STOPS_BY_VAR = previous_stops_by_var
            legacy_core.STOP_LINE_NAMES = previous_stop_line_names
            legacy_core.LINE_STOP_VARS = previous_line_stop_vars

    def test_alignment_reminder_adds_priority_need_until_station_connected(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        previous_stops_by_var = legacy_core.STOPS_BY_VAR
        previous_stop_line_names = legacy_core.STOP_LINE_NAMES
        previous_line_stop_vars = legacy_core.LINE_STOP_VARS
        previous_alignment_reminders = legacy_core.ALIGNMENT_REMINDERS
        try:
            connected_stop = legacy_core.MetroStop(
                var="P_A",
                lbl="Anchor",
                x=0,
                y=0,
                is_connected=True,
                has_connector=True,
                has_full_station=True,
                has_walking_paths=True,
                station_entry_x=0,
                station_entry_y=0,
                city_limit_node_keys=("coord:0,0", "coord:1,0", "coord:1,1"),
                has_finished_railway=True,
                has_signs=True,
            )
            aligned_target = legacy_core.MetroStop(
                var="P_B",
                lbl="Aligned",
                x=100,
                y=50,
                is_connected=False,
                has_connector=True,
                has_full_station=True,
                has_walking_paths=True,
                station_entry_x=100,
                station_entry_y=50,
                city_limit_node_keys=("coord:0,0", "coord:1,0", "coord:1,1"),
            )
            legacy_core.METRO_STOPS = (connected_stop, aligned_target)
            legacy_core.STOPS_BY_VAR = {
                connected_stop.var: connected_stop,
                aligned_target.var: aligned_target,
            }
            legacy_core.STOP_LINE_NAMES = {
                connected_stop.var: ("B",),
                aligned_target.var: ("B",),
            }
            legacy_core.LINE_STOP_VARS = {"B": (connected_stop.var, aligned_target.var)}
            legacy_core.ALIGNMENT_REMINDERS = (
                legacy_core.AlignmentReminder(connected_stop.var, aligned_target.var, "y"),
            )

            with mock.patch.object(legacy_core, "_station_max_chime_count", return_value=0):
                self.assertIn("alignment", legacy_core._missing_station_tasks(aligned_target))
                self.assertNotIn("alignment", legacy_core._missing_station_tasks(connected_stop))

                with (
                    mock.patch.object(
                        legacy_core,
                        "_route_costs_from_endpoint_key",
                        return_value={connected_stop.var: (0, 0)},
                    ),
                    mock.patch.object(legacy_core, "_line_distance_between_stops", return_value=100),
                ):
                    entries = legacy_core._priority_list_entries(connected_stop.var)

                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0][0], aligned_target.var)
                self.assertIn("align to other station(s)", entries[0][1])

                connected_target = legacy_core.MetroStop(
                    var=aligned_target.var,
                    lbl=aligned_target.lbl,
                    x=aligned_target.x,
                    y=aligned_target.y,
                    is_connected=True,
                    has_connector=aligned_target.has_connector,
                    has_full_station=aligned_target.has_full_station,
                    has_walking_paths=aligned_target.has_walking_paths,
                    station_entry_x=aligned_target.station_entry_x,
                    station_entry_y=aligned_target.station_entry_y,
                    city_limit_node_keys=aligned_target.city_limit_node_keys,
                    has_finished_railway=True,
                    has_signs=True,
                )
                legacy_core.METRO_STOPS = (connected_stop, connected_target)
                legacy_core.STOPS_BY_VAR = {
                    connected_stop.var: connected_stop,
                    connected_target.var: connected_target,
                }
                self.assertNotIn("alignment", legacy_core._missing_station_tasks(connected_target))
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops
            legacy_core.STOPS_BY_VAR = previous_stops_by_var
            legacy_core.STOP_LINE_NAMES = previous_stop_line_names
            legacy_core.LINE_STOP_VARS = previous_line_stop_vars
            legacy_core.ALIGNMENT_REMINDERS = previous_alignment_reminders

    def test_checklist_uses_paths_and_city_limits_labels(self) -> None:
        previous_metro_stops = legacy_core.METRO_STOPS
        try:
            legacy_core.METRO_STOPS = (
                legacy_core.MetroStop(var="P_A", lbl="Alpha", x=0, y=0),
                legacy_core.MetroStop(
                    var="P_B",
                    lbl="Bravo",
                    x=10,
                    y=10,
                    has_walking_paths=True,
                    city_limit_node_keys=("coord:1,1", "coord:2,2", "coord:3,3"),
                ),
            )
            with mock.patch.object(
                legacy_core,
                "_world_map_checklist_completion_line",
                return_value=None,
            ):
                summary = legacy_core._station_progress_summary_text()

            self.assertIn("Paths: 1/2", summary)
            self.assertIn("City Limits: 1/2", summary)
        finally:
            legacy_core.METRO_STOPS = previous_metro_stops

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
