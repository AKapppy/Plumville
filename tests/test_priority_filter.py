from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import legacy_core as base


class _FakeVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class PriorityFilterTest(unittest.TestCase):
    def test_selected_need_filters_entries_and_highlights_same_stations(self) -> None:
        entries = [(stop.var, stop.lbl) for stop in base.METRO_STOPS]
        counts = {}
        for stop_var, _text in entries:
            for task_name in base._missing_station_tasks(base.STOPS_BY_VAR[stop_var]):
                counts[task_name] = counts.get(task_name, 0) + 1
        self.assertTrue(counts)

        selected_task = max(counts, key=counts.get)
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.priority_filter_options = {"Selected": selected_task}
        viewer.priority_filter_var = _FakeVar("Selected")
        viewer.priority_highlight_stop_vars = set()

        filtered_entries = base.MetroMapViewer._priority_filter_entries(viewer, entries)
        expected_stop_vars = {
            stop_var
            for stop_var, _text in entries
            if selected_task in base._missing_station_tasks(base.STOPS_BY_VAR[stop_var])
        }

        self.assertEqual({stop_var for stop_var, _text in filtered_entries}, expected_stop_vars)
        self.assertEqual(viewer.priority_highlight_stop_vars, expected_stop_vars)

    def test_all_needs_filter_clears_map_highlights(self) -> None:
        entries = [(stop.var, stop.lbl) for stop in base.METRO_STOPS]
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.priority_filter_options = {base.PRIORITY_FILTER_ALL_LABEL: None}
        viewer.priority_filter_var = _FakeVar(base.PRIORITY_FILTER_ALL_LABEL)
        viewer.priority_highlight_stop_vars = {"P_ABCDE"}

        self.assertEqual(base.MetroMapViewer._priority_filter_entries(viewer, entries), entries)
        self.assertEqual(viewer.priority_highlight_stop_vars, set())

    def test_priority_list_includes_started_unconnected_station_work(self) -> None:
        stop = base.MetroStop("P_TEST", "Started", 0, 0, has_full_station=True)

        with (
            mock.patch.object(base, "METRO_STOPS", (stop,)),
            mock.patch.object(base, "STOPS_BY_VAR", {stop.var: stop}),
            mock.patch.object(base, "STOP_LINE_NAMES", {stop.var: ()}),
            mock.patch.object(base, "LINE_STOP_VARS", {}),
            mock.patch.object(base, "_route_costs_from_endpoint_key", return_value={}),
        ):
            entries = base._priority_list_entries("P_ABCDE")

        self.assertEqual([stop_var for stop_var, _text in entries], [stop.var])
        self.assertIn("needs", entries[0][1])

    def test_priority_list_includes_next_station_on_started_line(self) -> None:
        frontier = base.MetroStop("P_FRONTIER", "Frontier", 0, 0, is_connected=True)
        next_stop = base.MetroStop("P_NEXT", "Next", 10, 0)

        with (
            mock.patch.object(base, "METRO_STOPS", (frontier, next_stop)),
            mock.patch.object(base, "STOPS_BY_VAR", {frontier.var: frontier, next_stop.var: next_stop}),
            mock.patch.object(base, "STOP_LINE_NAMES", {frontier.var: ("A",), next_stop.var: ("A",)}),
            mock.patch.object(base, "LINE_STOP_VARS", {"A": (frontier.var, next_stop.var)}),
            mock.patch.object(
                base,
                "_missing_station_tasks",
                side_effect=lambda stop: [] if stop.var == frontier.var else ["station"],
            ),
            mock.patch.object(base, "_route_costs_from_endpoint_key", return_value={frontier.var: (12, 0)}),
            mock.patch.object(base, "_line_distance_between_stops", return_value=10),
        ):
            entries = base._priority_list_entries("P_ABCDE")

        self.assertEqual([stop_var for stop_var, _text in entries], [next_stop.var])
        self.assertIn("12 m", entries[0][1])

    def test_priority_csv_includes_lines_and_checklist_columns(self) -> None:
        stop = base.MetroStop(
            "P_TEST",
            "Village",
            0,
            0,
            has_connector=True,
            has_full_station=True,
            has_walking_paths=False,
            is_connected=True,
            has_signs=False,
            station_entry_x=3,
            station_entry_y=4,
            city_limit_node_keys=("coord:0,0", "coord:1,0", "coord:1,1"),
        )
        entries = [(stop.var, "Village: needs walking paths and signs")]

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "priority_list.csv"
            with (
                mock.patch.object(base, "STOPS_BY_VAR", {stop.var: stop}),
                mock.patch.object(base, "STOP_LINE_NAMES", {stop.var: ("A", "B")}),
                mock.patch.object(base, "PRIORITY_LIST_CSV_PATH", csv_path),
                mock.patch.object(base, "_station_max_chime_count", return_value=0),
            ):
                base._write_priority_list_csv(entries)

            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Station ID"], stop.var)
        self.assertEqual(rows[0]["Station Name"], "Village")
        self.assertEqual(rows[0]["Lines"], "A, B")
        self.assertEqual(rows[0]["Named"], "TRUE")
        self.assertEqual(rows[0]["Facade"], "TRUE")
        self.assertEqual(rows[0]["Station"], "TRUE")
        self.assertEqual(rows[0]["Walking Paths"], "FALSE")
        self.assertEqual(rows[0]["Signs"], "FALSE")
        self.assertEqual(rows[0]["Finished Railway"], "")
        self.assertEqual(rows[0]["Chimes"], "")


if __name__ == "__main__":
    unittest.main()
