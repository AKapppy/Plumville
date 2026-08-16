from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import legacy_core as base


class PathNodeSplittingTests(unittest.TestCase):
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

    def _payload_with_edge(
        self,
        *,
        kind: str = "walk",
        path_points: list[dict[str, int]] | None = None,
    ) -> dict[str, Any]:
        payload = json.loads(self.source_network_path.read_text(encoding="utf-8"))
        payload["path_nodes"] = [
            {"id": "node_a", "x": 999_000, "y": 999_000},
            {"id": "node_c", "x": 999_020, "y": 999_000},
        ]
        payload["extra_edges"] = [
            {
                "id": "edge_ac",
                "kind": kind,
                "from_endpoint": {"kind": "coord", "x": 999_000, "y": 999_000},
                "to_endpoint": {"kind": "coord", "x": 999_020, "y": 999_000},
                "bidirectional": True,
                "path_points": [] if path_points is None else path_points,
                "label": "Footpath",
            }
        ]
        return payload

    def test_add_path_node_splits_straight_walking_edge(self) -> None:
        self._write_payload(self._payload_with_edge())

        base.add_path_node("999010, 999000", label="Middle")

        payload = self._load_temp_payload()
        self.assertEqual(
            [(edge["from_endpoint"], edge["to_endpoint"]) for edge in payload["extra_edges"]],
            [
                (
                    {"kind": "coord", "x": 999_000, "y": 999_000},
                    {"kind": "coord", "x": 999_010, "y": 999_000},
                ),
                (
                    {"kind": "coord", "x": 999_010, "y": 999_000},
                    {"kind": "coord", "x": 999_020, "y": 999_000},
                ),
            ],
        )
        self.assertEqual([edge["id"] for edge in payload["extra_edges"]], ["edge_ac_a", "edge_ac_b"])
        self.assertEqual([edge["kind"] for edge in payload["extra_edges"]], ["walk", "walk"])
        self.assertEqual([edge["label"] for edge in payload["extra_edges"]], ["Footpath", "Footpath"])

    def test_add_path_node_splits_interior_segment_of_bent_walking_edge(self) -> None:
        payload = self._payload_with_edge(
            path_points=[
                {"x": 999_000, "y": 999_000},
                {"x": 999_010, "y": 999_000},
                {"x": 999_010, "y": 999_020},
                {"x": 999_020, "y": 999_000},
            ]
        )
        self._write_payload(payload)

        base.add_path_node("999010, 999010")

        payload = self._load_temp_payload()
        self.assertEqual(
            payload["extra_edges"][0]["path_points"],
            [
                {"x": 999_000, "y": 999_000},
                {"x": 999_010, "y": 999_000},
                {"x": 999_010, "y": 999_010},
            ],
        )
        self.assertEqual(
            payload["extra_edges"][1]["path_points"],
            [
                {"x": 999_010, "y": 999_010},
                {"x": 999_010, "y": 999_020},
                {"x": 999_020, "y": 999_000},
            ],
        )

    def test_add_path_node_does_not_split_connector_edge(self) -> None:
        self._write_payload(self._payload_with_edge(kind="connector"))

        base.add_path_node("999010, 999000")

        payload = self._load_temp_payload()
        self.assertEqual(len(payload["extra_edges"]), 1)
        self.assertEqual(payload["extra_edges"][0]["id"], "edge_ac")
        self.assertEqual(payload["extra_edges"][0]["kind"], "connector")


if __name__ == "__main__":
    unittest.main()
