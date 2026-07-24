from __future__ import annotations

import copy
import unittest
from unittest import mock

import metro_station_extensions as metro_ext


class MetroStationExtensionTests(unittest.TestCase):
    def test_existing_station_move_removes_old_anchor_before_reinserting(self) -> None:
        payload = {
            "stops": [
                {"var": "P_V4", "lbl": "V_4", "x": 0, "y": 0},
                {"var": "P_V5", "lbl": "V_5", "x": 10, "y": 0},
                {"var": "P_V6", "lbl": "V_6", "x": 20, "y": 0},
            ],
            "line_colors": {"V": "#f0932d"},
            "wool_colors": {"V": "Orange"},
            "line_stop_vars": {"V": ["P_V4", "P_V6", "P_V5"]},
            "line_path_specs": {
                "V": [
                    {"x_var": "P_V4", "y_var": "P_V4", "dx": 0, "dy": 0},
                    {"x_var": "P_V6", "y_var": "P_V6", "dx": 0, "dy": 0},
                    {"x_var": "P_V5", "y_var": "P_V5", "dx": 0, "dy": 0},
                ]
            },
            "path_nodes": [],
            "extra_edges": [],
            "alignment_reminders": [],
        }

        metro_ext._insert_station_after(payload, "V", "P_V6", "P_V5")

        self.assertEqual(payload["line_stop_vars"]["V"], ["P_V4", "P_V5", "P_V6"])
        self.assertEqual(
            [spec["x_var"] for spec in payload["line_path_specs"]["V"] if spec["x_var"] == spec["y_var"]],
            ["P_V4", "P_V5", "P_V6"],
        )

    def test_station_can_be_inserted_before_first_stop(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A1", "lbl": "A_1", "x": 0, "y": 0},
                {"var": "P_A2", "lbl": "A_2", "x": 10, "y": 0},
                {"var": "P_A3", "lbl": "A_3", "x": -10, "y": 0},
            ],
            "line_colors": {"A": "#e0d21a"},
            "wool_colors": {"A": "Yellow"},
            "line_stop_vars": {"A": ["P_A1", "P_A2"]},
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A1", "y_var": "P_A1", "dx": 0, "dy": 0},
                    {"x_var": "P_A2", "y_var": "P_A2", "dx": 0, "dy": 0},
                ]
            },
            "path_nodes": [],
            "extra_edges": [],
            "alignment_reminders": [],
        }

        metro_ext._insert_station_at_index(payload, "A", "P_A3", 0)

        self.assertEqual(payload["line_stop_vars"]["A"], ["P_A3", "P_A1", "P_A2"])
        self.assertEqual(
            [spec["x_var"] for spec in payload["line_path_specs"]["A"] if spec["x_var"] == spec["y_var"]],
            ["P_A3", "P_A1", "P_A2"],
        )

    def test_order_list_index_places_new_station(self) -> None:
        payload = {
            "line_stop_vars": {"A": ["P_A1", "P_A2"]},
        }

        ordered_stop_vars = ["P_A1", "[new]", "P_A2"]
        insert_index = ordered_stop_vars.index("[new]")
        existing_stop_vars = [stop_var for stop_var in ordered_stop_vars if stop_var != "[new]"]

        self.assertEqual(existing_stop_vars, payload["line_stop_vars"]["A"])
        self.assertEqual(insert_index, 1)

    def test_default_addable_line_skips_current_memberships(self) -> None:
        original_line_stop_vars = metro_ext.base.LINE_STOP_VARS
        original_stop_line_names = metro_ext.base.STOP_LINE_NAMES
        metro_ext.base.LINE_STOP_VARS = {
            "A": ("P_A1",),
            "B": ("P_B1",),
            "C": ("P_C1",),
        }
        metro_ext.base.STOP_LINE_NAMES = {"P_A1": ("A",)}
        try:
            self.assertEqual(metro_ext._default_addable_line("P_A1"), "B")
        finally:
            metro_ext.base.LINE_STOP_VARS = original_line_stop_vars
            metro_ext.base.STOP_LINE_NAMES = original_stop_line_names

    def test_reordered_line_preserves_reversed_adjacent_path_specs(self) -> None:
        payload = {
            "line_stop_vars": {"A": ["P_A1", "P_A2", "P_A3"]},
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A1", "y_var": "P_A1", "dx": 0, "dy": 0},
                    {"x_var": "P_A1", "y_var": "P_A2", "dx": 4, "dy": 5},
                    {"x_var": "P_A2", "y_var": "P_A2", "dx": 0, "dy": 0},
                    {"x_var": "P_A3", "y_var": "P_A3", "dx": 0, "dy": 0},
                ],
            },
        }

        specs = metro_ext._line_specs_for_reordered_sequence(
            payload,
            "A",
            ["P_A2", "P_A1", "P_A3"],
        )

        self.assertEqual(
            specs,
            [
                {"x_var": "P_A2", "y_var": "P_A2", "dx": 0, "dy": 0},
                {"x_var": "P_A1", "y_var": "P_A2", "dx": 4, "dy": 5},
                {"x_var": "P_A1", "y_var": "P_A1", "dx": 0, "dy": 0},
                {"x_var": "P_A3", "y_var": "P_A3", "dx": 0, "dy": 0},
            ],
        )

    def test_switch_station_line_moves_membership_in_one_save(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A1", "lbl": "A_1", "x": 0, "y": 0},
                {"var": "P_A2", "lbl": "A_2", "x": 10, "y": 0},
                {"var": "P_B1", "lbl": "B_1", "x": 0, "y": 10},
                {"var": "P_B3", "lbl": "B_3", "x": 20, "y": 10},
            ],
            "line_colors": {"A": "#e0d21a", "B": "#008c1a"},
            "wool_colors": {"A": "Yellow", "B": "Green"},
            "line_stop_vars": {
                "A": ["P_A1", "P_A2"],
                "B": ["P_B1", "P_B3"],
            },
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A1", "y_var": "P_A1", "dx": 0, "dy": 0},
                    {"x_var": "P_A2", "y_var": "P_A2", "dx": 0, "dy": 0},
                ],
                "B": [
                    {"x_var": "P_B1", "y_var": "P_B1", "dx": 0, "dy": 0},
                    {"x_var": "P_B3", "y_var": "P_B3", "dx": 0, "dy": 0},
                ],
            },
            "path_nodes": [],
            "extra_edges": [],
            "alignment_reminders": [],
        }
        written_payload = {}
        original_payload = metro_ext.base._load_network_payload()

        try:
            with (
                mock.patch.object(metro_ext.base, "_load_network_payload", return_value=copy.deepcopy(payload)),
                mock.patch.object(
                    metro_ext.base,
                    "_write_network_payload",
                    side_effect=lambda value: written_payload.update(copy.deepcopy(value)),
                ),
            ):
                added = metro_ext.switch_station_line(
                    "P_A2",
                    from_line_name="A",
                    to_line_name="B",
                    ordered_target_stop_vars=["P_B1", "[new]", "P_B3"],
                )
        finally:
            metro_ext.base._apply_network_payload(original_payload)

        self.assertEqual(added.stop_var, "P_B2")
        self.assertEqual(written_payload["stops"][1]["var"], "P_B2")
        self.assertEqual(written_payload["stops"][1]["lbl"], "B_2")
        self.assertEqual(written_payload["line_stop_vars"]["A"], ["P_A1"])
        self.assertEqual(written_payload["line_stop_vars"]["B"], ["P_B1", "P_B2", "P_B3"])

    def test_placeholder_names_follow_line_order_and_junction_letters(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A1", "lbl": "Custom Name", "x": 0, "y": 0},
                {"var": "P_A2", "lbl": "A_9", "x": 10, "y": 0},
                {"var": "P_AB", "lbl": "A_3", "x": 20, "y": 0},
            ],
            "line_colors": {"A": "#e0d21a", "B": "#008c1a"},
            "wool_colors": {"A": "Yellow", "B": "Green"},
            "line_stop_vars": {
                "A": ["P_A1", "P_A2", "P_AB"],
                "B": ["P_AB"],
            },
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A1", "y_var": "P_A1", "dx": 0, "dy": 0},
                    {"x_var": "P_A2", "y_var": "P_A2", "dx": 0, "dy": 0},
                    {"x_var": "P_AB", "y_var": "P_AB", "dx": 0, "dy": 0},
                ],
                "B": [
                    {"x_var": "P_AB", "y_var": "P_AB", "dx": 0, "dy": 0},
                    {"x_var": "P_AB", "y_var": "P_AB", "dx": 0, "dy": 0},
                ],
            },
            "path_nodes": [],
            "extra_edges": [],
            "alignment_reminders": [],
        }

        metro_ext._renumber_placeholder_station_labels(payload)

        labels = {stop["var"]: stop["lbl"] for stop in payload["stops"]}
        self.assertEqual(labels["P_A1"], "Custom Name")
        self.assertEqual(labels["P_A2"], "A_2")
        self.assertEqual(labels["P_AB"], "AB")


if __name__ == "__main__":
    unittest.main()
