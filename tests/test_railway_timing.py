from __future__ import annotations

import unittest
from unittest import mock

import legacy_core as base


class RailwayTimingTests(unittest.TestCase):
    def test_travel_time_uses_minecart_speed(self) -> None:
        self.assertEqual(base._travel_time_seconds(80), 10)
        self.assertEqual(base._format_travel_time_for_distance(480), "1m")
        self.assertEqual(base._format_distance_and_time(960), "960 m / 2m")

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


if __name__ == "__main__":
    unittest.main()
