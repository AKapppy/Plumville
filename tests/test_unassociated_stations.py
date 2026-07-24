from __future__ import annotations

import copy
import unittest
from unittest import mock

import legacy_core as base


class UnassociatedStationTests(unittest.TestCase):
    def test_removing_last_line_turns_station_into_unassociated_marker(self) -> None:
        payload = {
            "stops": [
                {
                    "var": "P_V6",
                    "lbl": "V_6",
                    "x": 20,
                    "y": 0,
                    "has_connector": True,
                    "has_full_station": True,
                    "has_walking_paths": True,
                    "is_connected": True,
                    "has_finished_railway": True,
                    "has_signs": True,
                    "chime_directions": ["north"],
                },
            ],
            "line_colors": {"V": "#f0932d"},
            "wool_colors": {"V": "Orange"},
            "line_stop_vars": {"V": ["P_V6"]},
            "line_path_specs": {
                "V": [
                    {"x_var": "P_V6", "y_var": "P_V6", "dx": 0, "dy": 0},
                    {"x_var": "P_V6", "y_var": "P_V6", "dx": 0, "dy": 0},
                ]
            },
            "path_nodes": [],
            "extra_edges": [],
            "alignment_reminders": [],
            "railway_finish_progress": {"V": {"x": 20, "y": 0}},
            "railway_finish_origins": {"V": "P_V6"},
        }
        written_payload = {}

        with (
            mock.patch.object(base, "_load_network_payload", return_value=payload),
            mock.patch.object(base, "_write_network_payload", side_effect=lambda value: written_payload.update(copy.deepcopy(value))),
            mock.patch.object(base, "_apply_network_payload"),
        ):
            new_var = base.remove_station_from_line("P_V6", "V")

        self.assertEqual(new_var, "P_6")
        self.assertEqual(written_payload["stops"][0]["var"], "P_6")
        self.assertEqual(written_payload["stops"][0]["lbl"], base.UNASSOCIATED_STATION_LABEL)
        self.assertFalse(written_payload["stops"][0]["has_connector"])
        self.assertFalse(written_payload["stops"][0]["is_connected"])
        self.assertEqual(written_payload["line_stop_vars"], {})
        self.assertEqual(written_payload["line_path_specs"], {})
        self.assertEqual(written_payload["line_colors"], {})
        self.assertEqual(written_payload["wool_colors"], {})
        self.assertEqual(written_payload["railway_finish_progress"], {})
        self.assertEqual(written_payload["railway_finish_origins"], {})

    def test_removing_one_line_from_junction_keeps_remaining_membership(self) -> None:
        payload = {
            "stops": [
                {"var": "P_A1", "lbl": "A_1", "x": 0, "y": 0},
                {"var": "P_AB", "lbl": "AB", "x": 10, "y": 0},
                {"var": "P_B2", "lbl": "B_2", "x": 20, "y": 0},
            ],
            "line_colors": {"A": "#e0d21a", "B": "#008c1a"},
            "wool_colors": {"A": "Yellow", "B": "Green"},
            "line_stop_vars": {
                "A": ["P_A1", "P_AB"],
                "B": ["P_AB", "P_B2"],
            },
            "line_path_specs": {
                "A": [
                    {"x_var": "P_A1", "y_var": "P_A1", "dx": 0, "dy": 0},
                    {"x_var": "P_AB", "y_var": "P_AB", "dx": 0, "dy": 0},
                ],
                "B": [
                    {"x_var": "P_AB", "y_var": "P_AB", "dx": 0, "dy": 0},
                    {"x_var": "P_B2", "y_var": "P_B2", "dx": 0, "dy": 0},
                ],
            },
            "path_nodes": [],
            "extra_edges": [],
            "alignment_reminders": [],
            "railway_finish_progress": {},
            "railway_finish_origins": {},
        }
        written_payload = {}

        with (
            mock.patch.object(base, "_load_network_payload", return_value=payload),
            mock.patch.object(base, "_write_network_payload", side_effect=lambda value: written_payload.update(copy.deepcopy(value))),
            mock.patch.object(base, "_apply_network_payload"),
        ):
            new_var = base.remove_station_from_line("P_AB", "A")

        self.assertEqual(new_var, "P_B")
        self.assertEqual(written_payload["stops"][1]["var"], "P_B")
        self.assertEqual(written_payload["stops"][1]["lbl"], "B_1")
        self.assertEqual(written_payload["line_stop_vars"]["A"], ["P_A1"])
        self.assertEqual(written_payload["line_stop_vars"]["B"], ["P_B", "P_B2"])
        self.assertEqual(
            [spec["x_var"] for spec in written_payload["line_path_specs"]["B"]],
            ["P_B", "P_B2"],
        )


if __name__ == "__main__":
    unittest.main()
