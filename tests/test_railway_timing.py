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
        self.assertIn("Connected: 80 m / 10s", summary)
        self.assertIn("entry (1, 2)", summary)
        self.assertIn("-> 80 m / 10s [connected]", summary)

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
