from __future__ import annotations

import unittest
from unittest import mock

import legacy_core as base
from plumville.core import travel_time


class RailwayTimingTests(unittest.TestCase):
    def test_core_travel_time_formatting(self) -> None:
        self.assertEqual(travel_time.MINECART_SPEED_MPS, 8.0)
        self.assertEqual(travel_time.travel_time_seconds(80), 10)
        self.assertEqual(travel_time.format_track_distance(999), "999 m")
        self.assertEqual(travel_time.format_track_distance(1800), "1.8 km")
        self.assertEqual(travel_time.format_travel_time(59), "59s")
        self.assertEqual(travel_time.format_travel_time(60), "1m")
        self.assertEqual(travel_time.format_travel_time(125), "2m 5s")
        self.assertEqual(travel_time.format_travel_time(3600), "1h")
        self.assertEqual(travel_time.format_distance_and_time(960), "960 m / 2m")

    def test_travel_time_uses_minecart_speed(self) -> None:
        self.assertEqual(base._travel_time_seconds(80), 10)
        self.assertEqual(base._format_travel_time_for_distance(480), "1m")
        self.assertEqual(base._format_distance_and_time(960), "960 m / 2m")
        self.assertEqual(base.MINECART_SPEED_MPS, travel_time.MINECART_SPEED_MPS)

    def test_extra_edge_summaries_include_minecart_time(self) -> None:
        edge = base.ExtraEdgeDefinition(
            id="walk_a",
            kind="walk",
            from_endpoint=base.PathEndpoint(kind="coord", key="coord:0,0", x=0, y=0),
            to_endpoint=base.PathEndpoint(kind="coord", key="coord:80,0", x=80, y=0),
        )

        self.assertIn("80 m / 10s", base._extra_edge_full_summary(edge))

    def test_line_summary_includes_total_connected_and_leg_times(self) -> None:
        first_stop = base.MetroStop(
            var="P_A1",
            lbl="A_1",
            x=0,
            y=0,
            is_connected=True,
            station_entry_x=1,
            station_entry_y=2,
        )
        second_stop = base.MetroStop(
            var="P_A2",
            lbl="A_2",
            x=80,
            y=0,
            is_connected=True,
        )
        with (
            mock.patch.object(base, "LINE_STOP_VARS", {"A": ("P_A1", "P_A2")}),
            mock.patch.object(base, "LINE_TUNNELED_STOP_VARS", {"A": frozenset(("P_A1", "P_A2"))}),
            mock.patch.object(base, "STOPS_BY_VAR", {"P_A1": first_stop, "P_A2": second_stop}),
            mock.patch.object(base, "LINE_COLORS", {"A": "#ff0000"}),
            mock.patch.object(base, "METRO_LINE_PLOT_PATHS", {"A": ((0, 0), (80, 0))}),
            mock.patch.object(
                base,
                "LINE_PATH_SPECS",
                {
                    "A": (
                        base.LinePathPointSpec("P_A1", "P_A1", 0, 0),
                        base.LinePathPointSpec("P_A2", "P_A2", 0, 0),
                    )
                },
            ),
        ):
            summary = base._line_summary_text("A")

        self.assertIn("Total: 80 m / 10s", summary)
        self.assertIn("Tunneled: 80 m / 10s", summary)
        self.assertIn("Connected: 80 m / 10s", summary)
        self.assertIn("entry (1, 2)", summary)
        self.assertIn("-> 80 m / 10s [connected]", summary)

    def test_railway_progress_summary_uses_tunneled_connected_and_planned_track(self) -> None:
        first_stop = base.MetroStop("P_A1", "Alpha", 0, 0, is_tunneled=True, is_connected=True)
        second_stop = base.MetroStop("P_A2", "Beta", 80, 0, is_tunneled=True, is_connected=True)
        third_stop = base.MetroStop("P_A3", "Gamma", 160, 0, is_connected=False)

        with (
            mock.patch.object(base, "LINE_STOP_VARS", {"A": ("P_A1", "P_A2", "P_A3")}),
            mock.patch.object(base, "LINE_TUNNELED_STOP_VARS", {"A": frozenset(("P_A1", "P_A2"))}),
            mock.patch.object(
                base,
                "STOPS_BY_VAR",
                {
                    "P_A1": first_stop,
                    "P_A2": second_stop,
                    "P_A3": third_stop,
                },
            ),
            mock.patch.object(base, "METRO_LINE_PLOT_PATHS", {"A": ((0, 0), (80, 0), (160, 0))}),
            mock.patch.object(
                base,
                "LINE_PATH_SPECS",
                {
                    "A": (
                        base.LinePathPointSpec("P_A1", "P_A1", 0, 0),
                        base.LinePathPointSpec("P_A2", "P_A2", 0, 0),
                        base.LinePathPointSpec("P_A3", "P_A3", 0, 0),
                    )
                },
            ),
            mock.patch.object(base, "RAILWAY_FINISH_PROGRESS", {"A": {"x": 160, "y": 0}}),
            mock.patch.object(base, "_frontier_highlight_segments", return_value=()),
        ):
            summary = base._railway_finish_progress_summary_text()

        self.assertEqual(
            summary,
            "A  T: 50% (80 / 160 m)\n     C: 50% (80 / 160 m)",
        )

    def test_railway_progress_summary_sorts_completed_lines_to_bottom(self) -> None:
        stops = {
            "P_A1": base.MetroStop("P_A1", "Alpha", 0, 0, is_tunneled=True),
            "P_A2": base.MetroStop("P_A2", "Beta", 100, 0, is_tunneled=True),
            "P_B1": base.MetroStop("P_B1", "Alpha", 0, 10, is_tunneled=True, is_connected=True),
            "P_B2": base.MetroStop("P_B2", "Beta", 100, 10, is_tunneled=True, is_connected=True),
            "P_C1": base.MetroStop("P_C1", "Alpha", 0, 20),
            "P_C2": base.MetroStop("P_C2", "Beta", 100, 20),
        }

        with (
            mock.patch.object(
                base,
                "LINE_STOP_VARS",
                {
                    "B": ("P_B1", "P_B2"),
                    "C": ("P_C1", "P_C2"),
                    "A": ("P_A1", "P_A2"),
                },
            ),
            mock.patch.object(base, "STOPS_BY_VAR", stops),
            mock.patch.object(
                base,
                "LINE_TUNNELED_STOP_VARS",
                {
                    "A": frozenset(("P_A1", "P_A2")),
                    "B": frozenset(("P_B1", "P_B2")),
                    "C": frozenset(),
                },
            ),
            mock.patch.object(
                base,
                "METRO_LINE_PLOT_PATHS",
                {
                    "A": ((0, 0), (100, 0)),
                    "B": ((0, -10), (100, -10)),
                    "C": ((0, -20), (100, -20)),
                },
            ),
            mock.patch.object(
                base,
                "LINE_PATH_SPECS",
                {
                    "A": (
                        base.LinePathPointSpec("P_A1", "P_A1", 0, 0),
                        base.LinePathPointSpec("P_A2", "P_A2", 0, 0),
                    ),
                    "B": (
                        base.LinePathPointSpec("P_B1", "P_B1", 0, 0),
                        base.LinePathPointSpec("P_B2", "P_B2", 0, 0),
                    ),
                    "C": (
                        base.LinePathPointSpec("P_C1", "P_C1", 0, 0),
                        base.LinePathPointSpec("P_C2", "P_C2", 0, 0),
                    ),
                },
            ),
            mock.patch.object(base, "_frontier_highlight_segments", return_value=(("C", "P_C1", "P_C2"),)),
        ):
            line_names = base._railway_sidebar_line_names()
            summary = base._railway_finish_progress_summary_text()

        self.assertEqual(line_names, ("A", "C", "B"))
        self.assertNotIn("B  T:", summary)
        self.assertTrue(summary.rstrip().endswith("B  C: 100% (100 m)"))

    def test_railway_sidebar_includes_tunneling_frontier_without_connected_frontier(self) -> None:
        stops = {
            "P_D1": base.MetroStop("P_D1", "Alpha", 0, 0, is_tunneled=True),
            "P_D2": base.MetroStop("P_D2", "Beta", 100, 0),
        }

        with (
            mock.patch.object(base, "LINE_STOP_VARS", {"D": ("P_D1", "P_D2")}),
            mock.patch.object(base, "STOPS_BY_VAR", stops),
            mock.patch.object(base, "LINE_TUNNELED_STOP_VARS", {"D": frozenset(("P_D1",))}),
            mock.patch.object(base, "METRO_LINE_PLOT_PATHS", {"D": ((0, 0), (100, 0))}),
            mock.patch.object(
                base,
                "LINE_PATH_SPECS",
                {
                    "D": (
                        base.LinePathPointSpec("P_D1", "P_D1", 0, 0),
                        base.LinePathPointSpec("P_D2", "P_D2", 0, 0),
                    )
                },
            ),
            mock.patch.object(base, "_frontier_highlight_segments", return_value=()),
        ):
            line_names = base._railway_sidebar_line_names()
            summary = base._railway_finish_progress_summary_text()

        self.assertEqual(line_names, ("D",))
        self.assertIn("D  T: 0% (0 / 100 m)", summary)

    def test_line_tunneled_stop_payload_can_target_one_shared_line(self) -> None:
        payload = {
            "stops": [
                {"var": "P_AB1", "lbl": "AB1", "x": 0, "y": 0},
                {"var": "P_AB2", "lbl": "AB2", "x": 10, "y": 0},
            ],
            "line_stop_vars": {
                "A": ["P_AB1", "P_AB2"],
                "B": ["P_AB1", "P_AB2"],
            },
            "line_tunneled_stop_vars": {},
        }

        base._update_line_tunneled_stop_vars_in_payload(
            payload,  # type: ignore[arg-type]
            "P_AB1",
            ("A",),
            True,
        )
        base._update_line_tunneled_stop_vars_in_payload(
            payload,  # type: ignore[arg-type]
            "P_AB2",
            ("A",),
            True,
        )

        self.assertEqual(
            payload["line_tunneled_stop_vars"],
            {"A": ["P_AB1", "P_AB2"]},
        )

    def test_existing_line_tunneled_payload_prevents_legacy_smearing_to_all_lines(self) -> None:
        payload = {
            "stops": [
                {"var": "P_AB1", "lbl": "AB1", "x": 0, "y": 0, "is_tunneled": True},
            ],
            "line_stop_vars": {
                "A": ["P_AB1"],
                "B": ["P_AB1"],
            },
            "line_tunneled_stop_vars": {"A": ["P_AB1"]},
        }

        self.assertEqual(
            base._line_tunneled_stop_vars_from_payload(payload),  # type: ignore[arg-type]
            {"A": frozenset(("P_AB1",)), "B": frozenset()},
        )

    def test_tunneled_checkpoint_marks_railway_summary_dirty(self) -> None:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.selected_stop_var = "P_A1"
        viewer.route_controls_dirty = False
        viewer.route_dirty = False
        viewer.priority_dirty = False
        viewer.stats_dirty = False
        viewer.railway_finish_dirty = False
        viewer.redraw = mock.Mock()

        with mock.patch.object(base, "_update_stop_record") as update_stop_record:
            base.MetroMapViewer._update_selected_checkpoint(viewer, "is_tunneled", False)

        update_stop_record.assert_called_once_with(
            "P_A1",
            is_tunneled=False,
            tunneled_line_names=None,
        )
        self.assertTrue(viewer.railway_finish_dirty)
        viewer.redraw.assert_called_once_with()

    def test_segment_construction_status_keeps_station_checklist_separate(self) -> None:
        first_stop = base.MetroStop(
            var="P_A1",
            lbl="A_1",
            x=0,
            y=0,
            is_connected=True,
            has_finished_railway=True,
        )
        second_stop = base.MetroStop(
            var="P_A2",
            lbl="A_2",
            x=80,
            y=0,
            is_connected=True,
            has_finished_railway=False,
        )
        with (
            mock.patch.object(base, "LINE_STOP_VARS", {"A": ("P_A1", "P_A2")}),
            mock.patch.object(base, "LINE_TUNNELED_STOP_VARS", {"A": frozenset(("P_A1", "P_A2"))}),
            mock.patch.object(base, "STOPS_BY_VAR", {"P_A1": first_stop, "P_A2": second_stop}),
            mock.patch.object(base, "METRO_LINE_PLOT_PATHS", {"A": ((0, 0), (80, 0))}),
            mock.patch.object(
                base,
                "LINE_PATH_SPECS",
                {
                    "A": (
                        base.LinePathPointSpec("P_A1", "P_A1", 0, 0),
                        base.LinePathPointSpec("P_A2", "P_A2", 0, 0),
                    )
                },
            ),
        ):
            statuses = base._railway_segment_construction_statuses("A")
            summary = base._line_summary_text("A")

        self.assertEqual(len(statuses), 1)
        status = statuses[0]
        self.assertTrue(status.routing_open)
        self.assertFalse(status.station_checklist_complete)
        self.assertEqual(status.construction_label, "open; station checklist incomplete")
        self.assertIn("-> 80 m / 10s [connected] open; station checklist incomplete", summary)


if __name__ == "__main__":
    unittest.main()
