from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
