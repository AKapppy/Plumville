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
        self.source_network_path = base.METRO_NETWORK_PATH
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

    def _clear_existing_path_refs(self, payload: dict[str, Any]) -> None:
        payload["extra_edges"] = []
        for stop_record in payload.get("stops", []):
            if isinstance(stop_record, dict):
                stop_record.pop("city_limit_node_keys", None)

    def test_move_path_node_updates_edges_and_city_limits(self) -> None:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        self._clear_existing_path_refs(payload)
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

        base.move_path_node("Test Node", new_coordinates)

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
        self._clear_existing_path_refs(payload)
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
        self.assertEqual(
            updated_payload["path_nodes"],
            [{"id": "node_1", "x": new_coordinates[0], "y": new_coordinates[1]}],
        )
        self.assertEqual(
            updated_payload["stops"][0]["city_limit_node_keys"],
            [base._coordinate_endpoint_key(*new_coordinates)],
        )

    def test_move_path_node_merges_with_existing_node_and_keeps_existing_label(self) -> None:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        self._clear_existing_path_refs(payload)
        first_stop = payload["stops"][0]
        stop_x = int(first_stop["station_entry_x"]) if "station_entry_x" in first_stop else int(first_stop["x"])
        stop_y = int(first_stop["station_entry_y"]) if "station_entry_y" in first_stop else int(first_stop["y"])

        old_coordinates = (999_771, 999_772)
        target_coordinates = (999_775, 999_776)
        old_key = base._coordinate_endpoint_key(*old_coordinates)

        payload["path_nodes"] = [
            {
                "id": "existing_node",
                "x": target_coordinates[0],
                "y": target_coordinates[1],
                "label": "Existing Name",
            },
            {
                "id": "moved_node",
                "x": old_coordinates[0],
                "y": old_coordinates[1],
                "label": "Moved Name",
            },
        ]
        payload["extra_edges"] = [
            {
                "id": "moved_edge",
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
                    {"x": old_coordinates[0] + 1, "y": old_coordinates[1]},
                    {"x": stop_x, "y": stop_y},
                ],
            }
        ]
        first_stop["city_limit_node_keys"] = [old_key]
        self._write_payload(payload)

        base.move_path_node("Moved Name", target_coordinates)

        updated_payload = self._load_temp_payload()
        self.assertEqual(
            updated_payload["path_nodes"],
            [
                {
                    "id": "node_1",
                    "x": target_coordinates[0],
                    "y": target_coordinates[1],
                    "label": "Existing Name",
                }
            ],
        )
        moved_edge = updated_payload["extra_edges"][0]
        self.assertEqual(
            (moved_edge["from_endpoint"]["x"], moved_edge["from_endpoint"]["y"]),
            target_coordinates,
        )
        self.assertEqual(
            (moved_edge["path_points"][0]["x"], moved_edge["path_points"][0]["y"]),
            target_coordinates,
        )
        self.assertEqual(
            updated_payload["stops"][0]["city_limit_node_keys"],
            [base._coordinate_endpoint_key(*target_coordinates)],
        )

    def test_add_path_node_reuses_lowest_open_numeric_id(self) -> None:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        self._clear_existing_path_refs(payload)
        payload["path_nodes"] = [
            {"id": "node_1", "x": 999_111, "y": 999_112},
            {"id": "node_3", "x": 999_131, "y": 999_132},
        ]
        self._write_payload(payload)

        base.add_path_node("999121, 999122", label="Middle")

        updated_payload = self._load_temp_payload()
        self.assertIn(
            {"id": "node_2", "x": 999_121, "y": 999_122, "label": "Middle"},
            updated_payload["path_nodes"],
        )

    def test_remove_path_node_supports_derived_coordinate_nodes(self) -> None:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        self._clear_existing_path_refs(payload)
        first_stop = payload["stops"][0]
        coordinates = (999_551, 999_552)
        old_key = base._coordinate_endpoint_key(*coordinates)
        payload["path_nodes"] = []
        payload["extra_edges"] = [
            {
                "id": "derived_edge",
                "kind": "walk",
                "from_endpoint": {"kind": "coord", "x": coordinates[0], "y": coordinates[1]},
                "to_endpoint": {"kind": "stop", "stop_var": str(first_stop["var"])},
                "bidirectional": True,
                "path_points": [],
            }
        ]
        first_stop["city_limit_node_keys"] = [old_key]
        self._write_payload(payload)

        base.remove_path_node(f"{coordinates[0]}, {coordinates[1]}")

        updated_payload = self._load_temp_payload()
        self.assertEqual(updated_payload["extra_edges"], [])
        self.assertNotIn(old_key, updated_payload["stops"][0].get("city_limit_node_keys", []))
        self.assertNotIn(
            coordinates,
            {
                (int(node["x"]), int(node["y"]))
                for node in updated_payload.get("path_nodes", [])
            },
        )

    def test_remove_extra_edge_deletes_one_connection_between_nodes(self) -> None:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        self._clear_existing_path_refs(payload)
        payload["path_nodes"] = [
            {"id": "node_1", "x": 999_611, "y": 999_612},
            {"id": "node_2", "x": 999_621, "y": 999_622},
            {"id": "node_3", "x": 999_631, "y": 999_632},
        ]
        payload["extra_edges"] = [
            {
                "id": "edge_remove",
                "kind": "walk",
                "from_endpoint": {"kind": "coord", "x": 999_611, "y": 999_612},
                "to_endpoint": {"kind": "coord", "x": 999_621, "y": 999_622},
                "bidirectional": True,
                "path_points": [],
            },
            {
                "id": "edge_keep",
                "kind": "walk",
                "from_endpoint": {"kind": "coord", "x": 999_621, "y": 999_622},
                "to_endpoint": {"kind": "coord", "x": 999_631, "y": 999_632},
                "bidirectional": True,
                "path_points": [],
            },
        ]
        self._write_payload(payload)

        base.remove_extra_edge("edge_remove")

        updated_payload = self._load_temp_payload()
        self.assertEqual([edge["id"] for edge in updated_payload["extra_edges"]], ["edge_keep"])


if __name__ == "__main__":
    unittest.main()
