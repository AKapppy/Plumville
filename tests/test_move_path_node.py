from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import legacy_core as base


class MovePathNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        temp_root = Path(self.tempdir.name)
        self.source_network_path = Path(base.__file__).with_name("metro_network.json")
        self.network_path = temp_root / "metro_network.json"
        self.backup_path = temp_root / "metro_network.last.json"
        self.history_dir = temp_root / "metro_network.history"

        self.patchers = [
            mock.patch.object(base, "METRO_NETWORK_PATH", self.network_path),
            mock.patch.object(base, "METRO_NETWORK_BACKUP_PATH", self.backup_path),
            mock.patch.object(base, "METRO_NETWORK_HISTORY_DIR", self.history_dir),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(self._restore_real_network)

    def _restore_real_network(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()
        base._reload_network_data()

    def _write_payload(self, payload: dict[str, Any]) -> None:
        self.network_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        base._reload_network_data()

    def _load_temp_payload(self) -> dict[str, Any]:
        return json.loads(self.network_path.read_text(encoding="utf-8"))

    def test_move_path_node_updates_edges_and_city_limits(self) -> None:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        first_stop = payload["stops"][0]
        stop_x = int(first_stop["station_entry_x"]) if "station_entry_x" in first_stop else int(first_stop["x"])
        stop_y = int(first_stop["station_entry_y"]) if "station_entry_y" in first_stop else int(first_stop["y"])

        old_coordinates = (999_991, 999_992)
        new_coordinates = (999_995, 999_996)
        old_key = base._coordinate_endpoint_key(*old_coordinates)

        payload["path_nodes"] = [
            {
                "id": "test_node",
                "x": old_coordinates[0],
                "y": old_coordinates[1],
                "label": "Test Node",
            }
        ]
        payload["extra_edges"] = [
            {
                "id": "test_edge",
                "kind": "walk",
                "from_endpoint": {
                    "kind": "coord",
                    "x": old_coordinates[0],
                    "y": old_coordinates[1],
                },
                "to_endpoint": {
                    "kind": "stop",
                    "stop_var": str(first_stop["var"]),
                },
                "bidirectional": True,
                "path_points": [
                    {"x": old_coordinates[0], "y": old_coordinates[1]},
                    {"x": old_coordinates[0] - 1, "y": old_coordinates[1]},
                    {"x": stop_x, "y": stop_y},
                ],
            }
        ]
        first_stop["city_limit_node_keys"] = [old_key]
        self._write_payload(payload)

        base.move_path_node("test_node", new_coordinates)

        updated_payload = self._load_temp_payload()
        moved_node = updated_payload["path_nodes"][0]
        self.assertEqual((moved_node["x"], moved_node["y"]), new_coordinates)

        moved_edge = updated_payload["extra_edges"][0]
        self.assertEqual(
            (moved_edge["from_endpoint"]["x"], moved_edge["from_endpoint"]["y"]),
            new_coordinates,
        )
        self.assertEqual(
            (moved_edge["path_points"][0]["x"], moved_edge["path_points"][0]["y"]),
            new_coordinates,
        )
        self.assertEqual(
            updated_payload["stops"][0]["city_limit_node_keys"],
            [base._coordinate_endpoint_key(*new_coordinates)],
        )

    def test_move_path_node_supports_derived_endpoint_nodes(self) -> None:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        first_stop = payload["stops"][0]
        stop_x = int(first_stop["station_entry_x"]) if "station_entry_x" in first_stop else int(first_stop["x"])
        stop_y = int(first_stop["station_entry_y"]) if "station_entry_y" in first_stop else int(first_stop["y"])

        old_coordinates = (999_881, 999_882)
        new_coordinates = (999_885, 999_886)
        old_key = base._coordinate_endpoint_key(*old_coordinates)

        payload["path_nodes"] = []
        payload["extra_edges"] = [
            {
                "id": "derived_edge",
                "kind": "connector",
                "from_endpoint": {
                    "kind": "coord",
                    "x": old_coordinates[0],
                    "y": old_coordinates[1],
                },
                "to_endpoint": {
                    "kind": "stop",
                    "stop_var": str(first_stop["var"]),
                },
                "bidirectional": True,
                "path_points": [
                    {"x": old_coordinates[0], "y": old_coordinates[1]},
                    {"x": old_coordinates[0] + 1, "y": old_coordinates[1]},
                    {"x": stop_x, "y": stop_y},
                ],
            }
        ]
        first_stop["city_limit_node_keys"] = [old_key]
        self._write_payload(payload)

        base.move_path_node(f"{old_coordinates[0]}, {old_coordinates[1]}", new_coordinates)

        updated_payload = self._load_temp_payload()
        moved_edge = updated_payload["extra_edges"][0]
        self.assertEqual(
            (moved_edge["from_endpoint"]["x"], moved_edge["from_endpoint"]["y"]),
            new_coordinates,
        )
        self.assertEqual(
            (moved_edge["path_points"][0]["x"], moved_edge["path_points"][0]["y"]),
            new_coordinates,
        )
        self.assertEqual(updated_payload["path_nodes"], [])
        self.assertEqual(
            updated_payload["stops"][0]["city_limit_node_keys"],
            [base._coordinate_endpoint_key(*new_coordinates)],
        )


if __name__ == "__main__":
    unittest.main()
