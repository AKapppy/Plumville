from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import legacy_core as base
from plumville.core import network


class CoreNetworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.network_path = self.root / "metro_network.json"
        self.backup_path = self.root / "metro_network.last.json"
        self.history_dir = self.root / "metro_network.history"

    def test_serialize_network_payload_uses_stable_pretty_json_with_trailing_newline(self) -> None:
        self.assertEqual(
            network.serialize_network_payload({"stops": []}),
            json.dumps({"stops": []}, indent=2) + "\n",
        )

    def test_coerce_int_accepts_legacy_int_inputs(self) -> None:
        self.assertEqual(network.coerce_int(True), 1)
        self.assertEqual(network.coerce_int(12), 12)
        self.assertEqual(network.coerce_int(12.9), 12)
        self.assertEqual(network.coerce_int("12"), 12)
        self.assertEqual(network.coerce_int(b"12"), 12)
        self.assertIsNone(network.coerce_int("twelve"))

    def test_normalized_ordered_values_filters_dedupes_and_preserves_valid_order(self) -> None:
        self.assertEqual(
            network.normalized_ordered_values(
                ["WEST", "north", "north", "bad", "east"],
                ("north", "east", "south", "west"),
            ),
            ("north", "east", "west"),
        )
        self.assertEqual(network.normalized_ordered_values("north", ("north",)), ())

    def test_normalize_stop_metadata_normalizes_checkpoints_entry_and_chimes(self) -> None:
        payload = {
            "stops": [
                {
                    "var": "P_A",
                    "has_connector": 1,
                    "abbr": " BKP ",
                    "station_entry_x": "10",
                    "station_entry_y": 20.5,
                    "chime_directions": ["west", "north", "west", "bad"],
                },
                {
                    "var": "P_B",
                    "abbr": "   ",
                    "station_entry_x": "bad",
                    "station_entry_y": 30,
                    "chime_directions": "north",
                },
            ]
        }

        changed = network.normalize_stop_metadata(
            payload,
            checkpoint_fields=("has_connector", "is_connected"),
            chime_directions=("north", "east", "south", "west"),
        )

        self.assertTrue(changed)
        self.assertEqual(
            payload["stops"][0],
            {
                "var": "P_A",
                "has_connector": True,
                "is_connected": False,
                "abbr": "BKP",
                "station_entry_x": 10,
                "station_entry_y": 20,
                "chime_directions": ["north", "west"],
            },
        )
        self.assertEqual(
            payload["stops"][1],
            {
                "var": "P_B",
                "has_connector": False,
                "is_connected": False,
                "chime_directions": [],
            },
        )

    def test_line_finish_origin_options_uses_first_and_last_connected_line_stops(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "is_connected": True},
                {"var": "P_B", "is_connected": False},
                {"var": "P_C", "is_connected": True},
                {"var": "P_D", "is_connected": True},
            ],
            "line_stop_vars": {"A": ["P_A", "P_B", "P_C", "P_D"]},
        }

        self.assertEqual(network.line_finish_origin_options(payload, "A"), ("P_A", "P_D"))
        self.assertEqual(base._payload_line_finish_origin_options(payload, "A"), ("P_A", "P_D"))  # type: ignore[arg-type]

    def test_normalize_railway_finish_progress_keeps_valid_line_points(self) -> None:
        payload = {
            "line_stop_vars": {"A": ["P_A"]},
            "railway_finish_progress": {
                "A": {"x": "10", "y": 20.5},
                "Z": {"x": 1, "y": 2},
                "B": {"x": "bad", "y": 3},
            },
        }

        changed = network.normalize_railway_finish_progress(payload)

        self.assertTrue(changed)
        self.assertEqual(payload["railway_finish_progress"], {"A": {"x": 10, "y": 20}})
        self.assertFalse(base._normalize_railway_finish_progress(payload))  # type: ignore[arg-type]

    def test_normalize_railway_finish_origins_keeps_only_valid_connected_origins(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "is_connected": True},
                {"var": "P_B", "is_connected": False},
                {"var": "P_C", "is_connected": True},
            ],
            "line_stop_vars": {"A": ["P_A", "P_B", "P_C"], "B": ["P_B"]},
            "railway_finish_origins": {
                "A": "P_C",
                "B": "P_B",
                "Z": "P_A",
            },
        }

        changed = network.normalize_railway_finish_origins(payload)

        self.assertTrue(changed)
        self.assertEqual(payload["railway_finish_origins"], {"A": "P_C"})
        self.assertFalse(base._normalize_railway_finish_origins(payload))  # type: ignore[arg-type]

    def test_normalize_path_nodes_removes_invalid_duplicates_and_station_collisions(self) -> None:
        payload = {
            "stops": [{"var": "P_A", "x": 0, "y": 0}],
            "path_nodes": [
                {"id": "keep", "x": "10", "y": 20, "label": "  Oak  "},
                {"id": "keep", "x": 30.2, "y": b"40", "poi_kind": "MONUMENT", "category": "Ocean"},
                {"id": "", "x": 0, "y": 0},
                {"id": "bad", "x": "nope", "y": 5},
                {"id": "dup_coord", "x": 10, "y": 20},
                "not a node",
            ],
        }

        changed = network.normalize_path_nodes(payload)

        self.assertTrue(changed)
        self.assertEqual(
            payload["path_nodes"],
            [
                {"id": "keep", "x": 10, "y": 20, "label": "Oak"},
                {
                    "id": "keep_2",
                    "x": 30,
                    "y": 40,
                    "poi_kind": "monument",
                    "category": "Ocean",
                },
            ],
        )
        self.assertFalse(base._normalize_path_nodes(payload))  # type: ignore[arg-type]

    def test_endpoint_resolution_supports_stop_labels_path_nodes_and_coordinates(self) -> None:
        payload = {
            "stops": [{"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0}],
            "path_nodes": [{"id": "oak", "x": 10, "y": 20, "label": "Oak"}],
        }

        self.assertEqual(network.resolve_stop_key(payload, "Alpha"), "P_A")
        self.assertEqual(network.resolve_path_node(payload, "Oak"), payload["path_nodes"][0])
        self.assertEqual(
            network.path_endpoint_record_from_identifier(payload, "oak"),
            {"kind": "coord", "x": 10, "y": 20},
        )
        self.assertEqual(
            network.path_endpoint_record_from_identifier(payload, "(30, -40)"),
            {"kind": "coord", "x": 30, "y": -40},
        )
        self.assertEqual(base._coordinate_endpoint_key(30, -40), "coord:30,-40")
        self.assertEqual(base._parse_coordinate_text("(30, -40)"), (30, -40))

    def test_normalize_extra_edges_supports_legacy_fields_and_path_specs(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0, "station_entry_x": 1, "station_entry_y": 2},
                {"var": "P_B", "lbl": "Beta", "x": 100, "y": 0},
            ],
            "path_nodes": [{"id": "oak", "x": 30, "y": 40, "label": "Oak"}],
            "extra_edges": [
                {
                    "id": " edge ",
                    "kind": "WALK",
                    "from_var": "Alpha",
                    "to_endpoint": {"kind": "coordinate", "x": "30", "y": "40"},
                    "path_points": [{"x": 10, "y": 20}],
                    "label": "  Lane  ",
                    "distance": "50",
                },
                {
                    "id": "edge",
                    "kind": "bad",
                    "from_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "to_endpoint": {"kind": "stop", "stop_var": "P_B"},
                    "path_specs": [{"x_var": "P_A", "y_var": "P_B", "dx": 5, "dy": 3}],
                    "bidirectional": 0,
                },
                {
                    "id": "same",
                    "from_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "to_endpoint": {"kind": "stop", "stop_var": "P_A"},
                },
            ],
        }

        changed = network.normalize_extra_edges(payload)

        self.assertTrue(changed)
        self.assertEqual(
            payload["extra_edges"],
            [
                {
                    "id": "edge",
                    "kind": "walk",
                    "from_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "to_endpoint": {"kind": "coord", "x": 30, "y": 40},
                    "bidirectional": True,
                    "path_points": [
                        {"x": 1, "y": 2},
                        {"x": 10, "y": 20},
                        {"x": 30, "y": 40},
                    ],
                    "label": "Lane",
                    "distance": 50,
                },
                {
                    "id": "edge_2",
                    "kind": "connector",
                    "from_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "to_endpoint": {"kind": "stop", "stop_var": "P_B"},
                    "bidirectional": False,
                    "path_points": [
                        {"x": 1, "y": 2},
                        {"x": 5, "y": -3},
                        {"x": 100, "y": 0},
                    ],
                },
            ],
        )
        self.assertFalse(base._normalize_extra_edges(payload))  # type: ignore[arg-type]

    def test_normalize_city_limits_keeps_known_path_node_keys_and_coordinate_text(self) -> None:
        payload = {
            "stops": [
                {
                    "var": "P_A",
                    "x": 0,
                    "y": 0,
                    "city_limit_node_keys": ["10,20", "coord:30,40", "missing", "10,20"],
                }
            ],
            "path_nodes": [{"id": "oak", "x": 10, "y": 20}],
            "extra_edges": [
                {
                    "id": "walk",
                    "kind": "walk",
                    "from_endpoint": {"kind": "coord", "x": 30, "y": 40},
                    "to_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "path_points": [],
                }
            ],
        }

        changed = network.normalize_city_limits(payload)

        self.assertTrue(changed)
        self.assertEqual(payload["stops"][0]["city_limit_node_keys"], ["coord:10,20", "coord:30,40"])
        self.assertFalse(base._normalize_city_limits(payload))  # type: ignore[arg-type]

    def test_normalize_alignment_reminders_dedupes_sorts_and_drops_aligned_pairs(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0},
                {"var": "P_B", "lbl": "Beta", "x": 10, "y": 50},
                {"var": "P_C", "lbl": "Gamma", "x": 0, "y": 70},
            ],
            "alignment_reminders": [
                {"first_var": "Beta", "second_var": "Alpha", "axis": "auto"},
                {"first_var": "P_A", "second_var": "P_B", "axis": "x"},
                {"first_var": "P_A", "second_var": "P_C", "axis": "x"},
                {"first_var": "P_A", "second_var": "P_A", "axis": "y"},
                {"first_var": "missing", "second_var": "P_B", "axis": "y"},
                "not a reminder",
            ],
        }

        self.assertEqual(network.infer_alignment_axis(0, 0, 10, 50), "x")
        self.assertEqual(base._infer_alignment_axis_from_coordinates(0, 0, 50, 10), "y")

        changed = network.normalize_alignment_reminders(payload)

        self.assertTrue(changed)
        self.assertEqual(
            payload["alignment_reminders"],
            [{"first_var": "P_A", "second_var": "P_B", "axis": "x"}],
        )
        self.assertFalse(base._normalize_alignment_reminders(payload))  # type: ignore[arg-type]

    def test_alignment_editor_preview_describes_included_stations(self) -> None:
        previous_stops_by_var = base.STOPS_BY_VAR
        previous_line_stop_vars = base.LINE_STOP_VARS
        previous_stops = base.METRO_STOPS
        try:
            alpha = base.MetroStop("P_A", "Alpha", 0, 0)
            beta = base.MetroStop("P_B", "Beta", 10, 50)
            gamma = base.MetroStop("P_C", "Gamma", 20, 50)
            base.STOPS_BY_VAR = {
                alpha.var: alpha,
                beta.var: beta,
                gamma.var: gamma,
            }
            base.LINE_STOP_VARS = {"A": (alpha.var, beta.var, gamma.var)}
            base.METRO_STOPS = (alpha, beta, gamma)

            preview = base._alignment_editor_preview_text(alpha.var, gamma.var, "y")

            self.assertIn("Match Y (horizontal)", preview)
            self.assertIn("Alpha, Beta, Gamma", preview)
            self.assertIn("Needs an alignment ellipse.", preview)
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var
            base.LINE_STOP_VARS = previous_line_stop_vars
            base.METRO_STOPS = previous_stops

    def test_default_turn_direction_label_uses_compass_directions(self) -> None:
        self.assertEqual(
            base._default_turn_direction_label((0, 0), (10, -10), ((10, 0),)),
            "East-South",
        )
        self.assertEqual(
            base._default_turn_direction_label((0, 0), (-10, 10), ((0, 10),)),
            "North-West",
        )

    def test_set_alignment_reminder_replaces_existing_record_atomically(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0},
                {"var": "P_B", "lbl": "Beta", "x": 10, "y": 50},
                {"var": "P_C", "lbl": "Gamma", "x": 30, "y": 50},
            ],
            "alignment_reminders": [
                {"first_var": "P_A", "second_var": "P_B", "axis": "x"},
            ],
        }

        with (
            mock.patch.object(base, "_load_network_payload", return_value=payload),
            mock.patch.object(base, "_write_network_payload") as write_payload,
            mock.patch.object(base, "_apply_network_payload") as apply_payload,
        ):
            base.set_alignment_reminder(
                "P_A",
                "P_C",
                "y",
                previous_first_station="P_A",
                previous_second_station="P_B",
                previous_axis="x",
            )

        self.assertEqual(
            payload["alignment_reminders"],
            [{"first_var": "P_A", "second_var": "P_C", "axis": "y"}],
        )
        write_payload.assert_called_once_with(payload)
        apply_payload.assert_called_once_with(payload)

    def test_set_alignment_reminder_drops_matching_record_when_pair_is_already_aligned(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0},
                {"var": "P_B", "lbl": "Beta", "x": 0, "y": 50},
            ],
            "alignment_reminders": [
                {"first_var": "P_A", "second_var": "P_B", "axis": "x"},
            ],
        }

        with (
            mock.patch.object(base, "_load_network_payload", return_value=payload),
            mock.patch.object(base, "_write_network_payload"),
            mock.patch.object(base, "_apply_network_payload"),
        ):
            base.set_alignment_reminder(
                "P_A",
                "P_B",
                "x",
                previous_first_station="P_A",
                previous_second_station="P_B",
                previous_axis="x",
            )

        self.assertEqual(payload["alignment_reminders"], [])

    def test_set_metro_line_segment_custom_points_replaces_segment_specs(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0},
                {"var": "P_B", "lbl": "Beta", "x": 10, "y": 10},
            ],
            "line_stop_vars": {"A": ["P_A", "P_B"]},
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A", "y_var": "P_A", "dx": 0, "dy": 0},
                    {"x_var": "P_B", "y_var": "P_B", "dx": 0, "dy": 0},
                ]
            },
            "alignment_reminders": [{"first_var": "P_A", "second_var": "P_B", "axis": "x"}],
        }
        previous_stops_by_var = base.STOPS_BY_VAR
        try:
            alpha = base.MetroStop("P_A", "Alpha", 0, 0)
            beta = base.MetroStop("P_B", "Beta", 10, 10)
            base.STOPS_BY_VAR = {alpha.var: alpha, beta.var: beta}
            with (
                mock.patch.object(base, "_load_network_payload", return_value=payload),
                mock.patch.object(base, "_write_network_payload"),
                mock.patch.object(base, "_apply_network_payload"),
            ):
                base.set_metro_line_segment_custom_points("A", "P_A", "P_B", [(0, 5), (10, 5)])
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var

        self.assertEqual(
            payload["line_path_specs"]["A"],
            [
                {"x_var": "P_A", "y_var": "P_A", "dx": 0, "dy": 0},
                {"x_var": "P_A", "y_var": "P_A", "dx": 0, "dy": -5},
                {"x_var": "P_A", "y_var": "P_A", "dx": 10, "dy": -5},
                {"x_var": "P_B", "y_var": "P_B", "dx": 0, "dy": 0},
            ],
        )
        self.assertEqual(payload["alignment_reminders"], [])

    def test_reset_all_metro_line_segments_direct_collapses_extra_specs(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0},
                {"var": "P_B", "lbl": "Beta", "x": 10, "y": 10},
                {"var": "P_C", "lbl": "Gamma", "x": 20, "y": 10},
            ],
            "line_stop_vars": {"A": ["P_A", "P_B", "P_C"]},
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A", "y_var": "P_A", "dx": 0, "dy": 0},
                    {"x_var": "P_A", "y_var": "P_B", "dx": 0, "dy": 0},
                    {"x_var": "P_B", "y_var": "P_B", "dx": 0, "dy": 0},
                    {"x_var": "P_C", "y_var": "P_B", "dx": 0, "dy": 0},
                    {"x_var": "P_C", "y_var": "P_C", "dx": 0, "dy": 0},
                ]
            },
            "alignment_reminders": [],
        }
        previous_stops_by_var = base.STOPS_BY_VAR
        try:
            alpha = base.MetroStop("P_A", "Alpha", 0, 0)
            beta = base.MetroStop("P_B", "Beta", 10, 10)
            gamma = base.MetroStop("P_C", "Gamma", 20, 10)
            base.STOPS_BY_VAR = {alpha.var: alpha, beta.var: beta, gamma.var: gamma}
            with (
                mock.patch.object(base, "_load_network_payload", return_value=payload),
                mock.patch.object(base, "_write_network_payload"),
                mock.patch.object(base, "_apply_network_payload"),
            ):
                base.reset_all_metro_line_segments_direct()
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var

        self.assertEqual(
            payload["line_path_specs"]["A"],
            [
                {"x_var": "P_A", "y_var": "P_A", "dx": 0, "dy": 0},
                {"x_var": "P_B", "y_var": "P_B", "dx": 0, "dy": 0},
                {"x_var": "P_C", "y_var": "P_C", "dx": 0, "dy": 0},
            ],
        )
        self.assertEqual(
            payload["alignment_reminders"],
            [{"first_var": "P_A", "second_var": "P_B", "axis": "x"}],
        )

    def test_set_metro_line_segment_endpoint_coordinates_updates_anchors_only(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A", "lbl": "Alpha", "x": 0, "y": 0},
                {"var": "P_B", "lbl": "Beta", "x": 10, "y": 10},
            ],
            "line_stop_vars": {"A": ["P_A", "P_B"]},
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A", "y_var": "P_A", "dx": 0, "dy": 0},
                    {"x_var": "P_A", "y_var": "P_A", "dx": 4, "dy": -2},
                    {"x_var": "P_B", "y_var": "P_B", "dx": 0, "dy": 0},
                ]
            },
            "alignment_reminders": [],
        }
        previous_stops_by_var = base.STOPS_BY_VAR
        try:
            alpha = base.MetroStop("P_A", "Alpha", 0, 0)
            beta = base.MetroStop("P_B", "Beta", 10, 10)
            base.STOPS_BY_VAR = {alpha.var: alpha, beta.var: beta}
            with (
                mock.patch.object(base, "_load_network_payload", return_value=payload),
                mock.patch.object(base, "_write_network_payload"),
                mock.patch.object(base, "_apply_network_payload"),
            ):
                base.set_metro_line_segment_endpoint_coordinates(
                    "A",
                    "P_A",
                    "P_B",
                    start_coordinates=(1, 2),
                    end_coordinates=(9, 8),
                )
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var

        self.assertEqual(
            payload["line_path_specs"]["A"],
            [
                {"x_var": "P_A", "y_var": "P_A", "dx": 1, "dy": -2},
                {"x_var": "P_A", "y_var": "P_A", "dx": 4, "dy": -2},
                {"x_var": "P_B", "y_var": "P_B", "dx": -1, "dy": 2},
            ],
        )

    def test_metro_segment_coordinate_list_formatter_is_shared_by_editors(self) -> None:
        self.assertEqual(base._format_coordinate_list(()), "No intermediate coordinates.")
        self.assertEqual(base._format_coordinate_list(((1, 2), (3, 4))), "(1, 2) -> (3, 4)")

    def test_metro_segment_endpoint_editor_reaches_save_button_without_display(self) -> None:
        class FakeWidget:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def pack(self, *_args: object, **_kwargs: object) -> None:
                pass

            def title(self, _value: str) -> None:
                pass

            def configure(self, **_kwargs: object) -> None:
                pass

            def transient(self, _root: object) -> None:
                pass

            def grab_set(self) -> None:
                pass

            def protocol(self, _name: str, _callback: object) -> None:
                pass

            def winfo_exists(self) -> bool:
                return True

            def destroy(self) -> None:
                pass

        class FakeStringVar:
            def __init__(self, *_args: object, value: str = "", **_kwargs: object) -> None:
                self.value = value

            def get(self) -> str:
                return self.value

            def set(self, value: str) -> None:
                self.value = value

            def trace_add(self, _mode: str, _callback: object) -> str:
                return "trace"

        class FakeButton(FakeWidget):
            def __init__(self, text: str, command: object) -> None:
                super().__init__()
                self.text = text
                self.command = command

        class FakeViewer:
            def __init__(self) -> None:
                self.root = object()
                self.buttons: list[FakeButton] = []
                self.preview_points: tuple[tuple[int, int], ...] | None = None

            def _center_toplevel(self, _dialog: object, *, width: int, height: int) -> None:
                self.center_size = (width, height)

            def _clear_metro_segment_preview(self) -> None:
                self.preview_points = None

            def _set_metro_segment_preview(self, points: tuple[tuple[int, int], ...]) -> None:
                self.preview_points = points

            def _make_sidebar_button(
                self,
                _parent: object,
                *,
                text: str,
                command: object,
            ) -> FakeButton:
                button = FakeButton(text, command)
                self.buttons.append(button)
                return button

        previous_tk = base.tk
        previous_stops_by_var = base.STOPS_BY_VAR
        viewer = FakeViewer()
        try:
            base.tk = SimpleNamespace(
                Toplevel=FakeWidget,
                Frame=FakeWidget,
                Label=FakeWidget,
                Entry=FakeWidget,
                StringVar=FakeStringVar,
            )
            alpha = base.MetroStop("P_A", "Alpha", 0, 0)
            beta = base.MetroStop("P_B", "Beta", 10, 10)
            base.STOPS_BY_VAR = {alpha.var: alpha, beta.var: beta}
            segment = base.MetroLineSegment(
                "A",
                "P_A",
                "P_B",
                (
                    base.LinePathPointSpec("P_A", "P_A"),
                    base.LinePathPointSpec("P_A", "P_A", 4, -2),
                    base.LinePathPointSpec("P_B", "P_B"),
                ),
            )

            base.MetroMapViewer._edit_metro_segment_endpoints(viewer, segment)  # type: ignore[arg-type]
        finally:
            base.tk = previous_tk
            base.STOPS_BY_VAR = previous_stops_by_var

        self.assertIn("Save Endpoints", [button.text for button in viewer.buttons])
        self.assertEqual(viewer.preview_points, ((0, 0), (4, -2), (10, -10)))

    def test_payload_projection_helpers_build_runtime_mappings(self) -> None:
        payload = {
            "line_colors": {"A": "#fff", 2: "#000"},
            "wool_colors": {"A": "White"},
            "line_stop_vars": {"A": ["P_A", "P_B"], "B": ("P_B",)},
            "railway_finish_progress": {
                "A": {"x": "10", "y": 20},
                "Z": {"x": 1, "y": 2},
            },
            "railway_finish_origins": {
                "A": "P_B",
                "B": "P_Z",
                "Z": "P_A",
            },
        }

        line_stop_vars = network.line_stop_vars_from_payload(payload)

        self.assertEqual(network.line_colors_from_payload(payload), {"A": "#fff", "2": "#000"})
        self.assertEqual(network.wool_colors_from_payload(payload), {"A": "White"})
        self.assertEqual(line_stop_vars, {"A": ("P_A", "P_B"), "B": ("P_B",)})
        self.assertEqual(
            network.stop_line_names(("P_A", "P_B", "P_C"), line_stop_vars),
            {"P_A": ("A",), "P_B": ("A", "B"), "P_C": ()},
        )
        self.assertEqual(
            network.railway_finish_progress_from_payload(payload, line_stop_vars),
            {"A": {"x": 10, "y": 20}},
        )
        self.assertEqual(
            network.railway_finish_origins_from_payload(payload, line_stop_vars),
            {"A": "P_B"},
        )

    def test_line_path_projection_helpers_build_plot_and_coordinate_paths(self) -> None:
        payload = {
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A", "y_var": "P_A"},
                    {"x_var": "P_B", "y_var": "P_A", "dx": "5", "dy": "-2"},
                ]
            }
        }
        stop_coordinates = {"P_A": (10, 20), "P_B": (30, 40)}

        spec_records = network.line_path_spec_records_from_payload(payload)
        plot_paths = network.line_path_plot_paths_from_specs(spec_records, stop_coordinates)
        coordinate_paths = network.line_path_coordinate_paths_from_plot_paths(plot_paths)

        self.assertEqual(
            spec_records,
            {"A": ({"x_var": "P_A", "y_var": "P_A", "dx": 0, "dy": 0}, {"x_var": "P_B", "y_var": "P_A", "dx": 5, "dy": -2})},
        )
        self.assertEqual(plot_paths, {"A": ((10, -20), (35, -22))})
        self.assertEqual(coordinate_paths, {"A": ((10, 20), (35, 22))})

    def test_runtime_record_projection_helpers_coerce_payload_records(self) -> None:
        payload = {
            "path_nodes": [
                {"id": 1, "x": "10", "y": 20.5, "label": "Oak", "poi_kind": "MONUMENT", "category": "Ocean"},
            ],
            "extra_edges": [
                {
                    "id": 2,
                    "kind": "walk",
                    "from_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "to_endpoint": {"kind": "coord", "x": 10, "y": 20},
                    "bidirectional": 0,
                    "label": "Lane",
                    "distance": "30",
                    "path_points": [{"x": "1", "y": 2.5}],
                }
            ],
            "alignment_reminders": [{"first_var": "P_B", "second_var": "P_A", "axis": "x"}],
        }

        self.assertEqual(
            network.path_node_records_from_payload(payload),
            ({"id": "1", "x": 10, "y": 20, "label": "Oak", "poi_kind": "MONUMENT", "category": "Ocean"},),
        )
        self.assertEqual(
            network.extra_edge_records_from_payload(payload),
            (
                {
                    "id": "2",
                    "kind": "walk",
                    "from_endpoint": {"kind": "stop", "stop_var": "P_A"},
                    "to_endpoint": {"kind": "coord", "x": 10, "y": 20},
                    "bidirectional": False,
                    "label": "Lane",
                    "distance": 30,
                    "path_points": [{"x": 1, "y": 2}],
                },
            ),
        )
        self.assertEqual(
            network.alignment_reminder_records_from_payload(payload),
            ({"first_var": "P_B", "second_var": "P_A", "axis": "x"},),
        )

    def test_validation_helpers_accept_valid_network_shapes(self) -> None:
        line_stop_vars = {"A": ("P_A1", "P_A2")}
        line_path_specs = {
            "A": (
                {"x_var": "P_A1", "y_var": "P_A1"},
                {"x_var": "P_A2", "y_var": "P_A2"},
            )
        }

        network.validate_stop_records(
            ({"var": "P_A1", "lbl": "A_1"}, {"var": "P_A2", "lbl": "A_2"}),
            unassociated_station_label=base.UNASSOCIATED_STATION_LABEL,
        )
        network.validate_line_sequences(("P_A1", "P_A2"), line_stop_vars)
        network.validate_line_path_specs(line_path_specs, line_stop_vars, {"P_A1", "P_A2"})
        network.validate_line_colors({"A": "#fff"}, line_stop_vars)
        network.validate_stop_line_names(("P_A1", "P_A2"), {"P_A1": ("A",), "P_A2": ("A",)})
        network.validate_path_nodes(({"id": "oak", "x": 10, "y": 20},), {(0, 0)})
        network.validate_extra_edges(
            (
                {
                    "id": "walk",
                    "from_endpoint": {"kind": "stop", "key": "P_A1", "coordinates": (0, 0)},
                    "to_endpoint": {"kind": "coord", "key": "coord:1,1", "coordinates": (1, 1)},
                    "path_points": ((0, 0), (1, 1)),
                },
            ),
            {"P_A1", "P_A2"},
        )

    def test_validation_helpers_raise_matching_errors_for_invalid_shapes(self) -> None:
        with self.assertRaisesRegex(ValueError, "Stop variables must be unique"):
            network.validate_stop_records(
                ({"var": "P_A", "lbl": "A"}, {"var": "P_A", "lbl": "B"}),
                unassociated_station_label=base.UNASSOCIATED_STATION_LABEL,
            )
        with self.assertRaisesRegex(ValueError, "duplicate stop entries"):
            network.validate_line_sequences(("P_A1",), {"A": ("P_A1", "P_A1")})
        with self.assertRaisesRegex(ValueError, "path is missing stops"):
            network.validate_line_path_specs(
                {"A": ({"x_var": "P_A1", "y_var": "P_A1"}, {"x_var": "P_A1", "y_var": "P_A1"})},
                {"A": ("P_A1", "P_A2")},
                {"P_A1", "P_A2"},
            )
        with self.assertRaisesRegex(ValueError, "LINE_COLORS"):
            network.validate_line_colors({}, {"A": ("P_A1",)})
        with self.assertRaisesRegex(ValueError, "overlaps a station coordinate"):
            network.validate_path_nodes(({"id": "oak", "x": 0, "y": 0},), {(0, 0)})
        with self.assertRaisesRegex(ValueError, "unknown start stop"):
            network.validate_extra_edges(
                (
                    {
                        "id": "walk",
                        "from_endpoint": {"kind": "stop", "key": "P_Z", "coordinates": (0, 0)},
                        "to_endpoint": {"kind": "coord", "key": "coord:1,1", "coordinates": (1, 1)},
                        "path_points": (),
                    },
                ),
                {"P_A"},
            )
        with self.assertRaisesRegex(ValueError, "missing line membership"):
            network.validate_stop_line_names(("P_A",), {})

    def test_write_network_payload_creates_file_without_backup_for_first_write(self) -> None:
        network.write_network_payload(
            {"stops": []},
            network_path=self.network_path,
            backup_path=self.backup_path,
            history_dir=self.history_dir,
            max_history_snapshots=10,
        )

        self.assertEqual(self.network_path.read_text(encoding="utf-8"), '{\n  "stops": []\n}\n')
        self.assertFalse(self.backup_path.exists())
        self.assertEqual(network.history_snapshot_paths(self.history_dir), [])

    def test_write_network_payload_records_backup_and_history_when_existing_payload_changes(self) -> None:
        current_text = '{\n  "stops": []\n}\n'
        self.network_path.write_text(current_text, encoding="utf-8")

        network.write_network_payload(
            {"stops": [{"var": "P_A"}]},
            network_path=self.network_path,
            backup_path=self.backup_path,
            history_dir=self.history_dir,
            max_history_snapshots=10,
            now=lambda: datetime(2026, 7, 24, 12, 0, 0),
        )

        self.assertEqual(self.backup_path.read_text(encoding="utf-8"), current_text)
        self.assertEqual(
            [path.name for path in network.history_snapshot_paths(self.history_dir)],
            ["20260724-120000-000000.json"],
        )
        self.assertEqual(
            json.loads(self.network_path.read_text(encoding="utf-8")),
            {"stops": [{"var": "P_A"}]},
        )

    def test_record_history_snapshot_skips_duplicate_latest_snapshot(self) -> None:
        times = iter((
            datetime(2026, 7, 24, 12, 0, 0),
            datetime(2026, 7, 24, 12, 1, 0),
        ))

        network.record_history_snapshot(
            "same\n",
            history_dir=self.history_dir,
            max_history_snapshots=10,
            now=lambda: next(times),
        )
        network.record_history_snapshot(
            "same\n",
            history_dir=self.history_dir,
            max_history_snapshots=10,
            now=lambda: next(times),
        )

        self.assertEqual(len(network.history_snapshot_paths(self.history_dir)), 1)

    def test_record_history_snapshot_trims_oldest_snapshots(self) -> None:
        times = iter((
            datetime(2026, 7, 24, 12, 0, 0),
            datetime(2026, 7, 24, 12, 1, 0),
            datetime(2026, 7, 24, 12, 2, 0),
        ))
        for index in range(3):
            network.record_history_snapshot(
                f"payload {index}\n",
                history_dir=self.history_dir,
                max_history_snapshots=2,
                now=lambda: next(times),
            )

        self.assertEqual(
            [path.name for path in network.history_snapshot_paths(self.history_dir)],
            ["20260724-120100-000000.json", "20260724-120200-000000.json"],
        )

    def test_restore_last_network_snapshot_prefers_latest_history_snapshot(self) -> None:
        self.network_path.write_text("current\n", encoding="utf-8")
        self.backup_path.write_text("backup\n", encoding="utf-8")
        self.history_dir.mkdir()
        (self.history_dir / "20260724-120000-000000.json").write_text("old\n", encoding="utf-8")
        latest_path = self.history_dir / "20260724-120100-000000.json"
        latest_path.write_text("latest\n", encoding="utf-8")

        network.restore_last_network_snapshot(
            network_path=self.network_path,
            backup_path=self.backup_path,
            history_dir=self.history_dir,
        )

        self.assertEqual(self.network_path.read_text(encoding="utf-8"), "latest\n")
        self.assertEqual(self.backup_path.read_text(encoding="utf-8"), "current\n")
        self.assertFalse(latest_path.exists())

    def test_restore_last_network_snapshot_falls_back_to_backup(self) -> None:
        self.network_path.write_text("current\n", encoding="utf-8")
        self.backup_path.write_text("backup\n", encoding="utf-8")

        network.restore_last_network_snapshot(
            network_path=self.network_path,
            backup_path=self.backup_path,
            history_dir=self.history_dir,
        )

        self.assertEqual(self.network_path.read_text(encoding="utf-8"), "backup\n")
        self.assertEqual(self.backup_path.read_text(encoding="utf-8"), "current\n")


if __name__ == "__main__":
    unittest.main()
