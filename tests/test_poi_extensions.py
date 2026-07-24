from __future__ import annotations

import copy
import unittest
from unittest import mock

import legacy_core as base
import poi_extensions


def _payload() -> base.MetroNetworkPayload:
    return {
        "stops": [
            {"var": "P_A1", "lbl": "A_1", "x": 10, "y": 20},
        ],
        "line_colors": {},
        "wool_colors": {},
        "line_stop_vars": {},
        "line_path_specs": {},
        "path_nodes": [],
        "extra_edges": [],
        "alignment_reminders": [],
    }


class PoiExtensionConsolidationTests(unittest.TestCase):
    def test_add_custom_monument_point_of_interest_writes_normalized_node(self) -> None:
        payload = _payload()
        written_payload: base.MetroNetworkPayload | None = None

        with (
            mock.patch.object(base, "_load_network_payload", return_value=payload),
            mock.patch.object(base, "_write_network_payload") as write_network_payload,
            mock.patch.object(base, "_apply_network_payload") as apply_network_payload,
        ):
            added = base.add_custom_point_of_interest(
                (30, 40),
                kind="monument",
                label="  Ocean Monument  ",
                category="  Ocean  ",
            )
            written_payload = copy.deepcopy(write_network_payload.call_args.args[0])

        self.assertEqual(added.label, "Ocean Monument")
        self.assertEqual(added.coordinates, (30, 40))
        self.assertEqual(added.node_key, "coord:30,40")
        self.assertIsNotNone(written_payload)
        assert written_payload is not None
        self.assertEqual(
            written_payload["path_nodes"],
            [
                {
                    "id": "monument_1",
                    "x": 30,
                    "y": 40,
                    "label": "Ocean Monument",
                    "poi_kind": "monument",
                    "category": "Ocean",
                }
            ],
        )
        apply_network_payload.assert_called_once()

    def test_add_custom_poi_rejects_duplicate_station_or_node_coordinates(self) -> None:
        station_payload = _payload()
        with mock.patch.object(base, "_load_network_payload", return_value=station_payload):
            with self.assertRaisesRegex(ValueError, "station already exists"):
                base.add_custom_point_of_interest((10, 20), kind="pillager_tower")

        node_payload = _payload()
        node_payload["path_nodes"].append({"id": "node_1", "x": 30, "y": 40})
        with mock.patch.object(base, "_load_network_payload", return_value=node_payload):
            with self.assertRaisesRegex(ValueError, "node or PoI already exists"):
                base.add_custom_point_of_interest((30, 40), kind="pillager_tower")

    def test_poi_categories_are_sorted_unique_monument_categories(self) -> None:
        path_nodes = (
            base.PathNode(id="1", x=0, y=0, poi_kind="monument", category="Ocean"),
            base.PathNode(id="2", x=1, y=1, poi_kind="monument", category="Desert"),
            base.PathNode(id="3", x=2, y=2, poi_kind="monument", category="Ocean"),
            base.PathNode(id="4", x=3, y=3, poi_kind="pillager_tower", category="Tower"),
        )

        with mock.patch.object(base, "PATH_NODES", path_nodes):
            self.assertEqual(base._poi_categories(), ("Desert", "Ocean"))

    def test_poi_extensions_apply_is_compatibility_noop(self) -> None:
        before_dialog = base.MetroMapViewer._show_add_poi_dialog

        original_applied = poi_extensions._APPLIED
        applied_after_call = False
        try:
            poi_extensions._APPLIED = False
            poi_extensions.apply()
            applied_after_call = poi_extensions._APPLIED
        finally:
            poi_extensions._APPLIED = original_applied

        self.assertTrue(applied_after_call)
        self.assertIs(base.MetroMapViewer._show_add_poi_dialog, before_dialog)


if __name__ == "__main__":
    unittest.main()
