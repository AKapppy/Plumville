from __future__ import annotations

import unittest
from unittest import mock

import legacy_core as base


class MapFramingTest(unittest.TestCase):
    def test_focus_station_view_uses_selected_station_radius(self) -> None:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer._set_view_to_plot_bounds = mock.Mock()
        viewer._minimum_zoom = mock.Mock(return_value=1.25)
        stop = base.MetroStop("P_A", "Alpha", 20, 30)

        base.MetroMapViewer._focus_station_view(viewer, stop)

        viewer._set_view_to_plot_bounds.assert_called_once_with(
            -130,
            170,
            -180,
            120,
            min_zoom=1.25,
            margin_pixels=0,
        )

    def test_focus_stop_selects_station_and_frames_view(self) -> None:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        stop = base.MetroStop("P_A", "Alpha", 20, 30)
        viewer.selected_stop_var = None
        viewer.selected_path_node_key = "coord:0,0"
        viewer._clear_metro_segment_selection = mock.Mock()
        viewer._focus_station_view = mock.Mock()

        with mock.patch.object(base, "STOPS_BY_VAR", {stop.var: stop}):
            base.MetroMapViewer._focus_stop(viewer, stop.var)

        self.assertEqual(viewer.selected_stop_var, stop.var)
        self.assertIsNone(viewer.selected_path_node_key)
        viewer._clear_metro_segment_selection.assert_called_once_with()
        viewer._focus_station_view.assert_called_once_with(stop)

    def test_option_letter_hotkey_fits_entire_line_geometry(self) -> None:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer._hotkeys_enabled = mock.Mock(return_value=True)
        viewer.show_line_view = mock.Mock()
        viewer.hover_canvas_point = (1.0, 2.0)
        viewer.cursor_readout_coordinates = (1, 2)
        viewer.show_cursor_guides = True
        event = mock.Mock(keysym="a")

        with mock.patch.object(base, "LINE_STOP_VARS", {"A": ("P_A1", "P_A2")}):
            result = base.MetroMapViewer._on_fit_line_hotkey(viewer, event)

        self.assertEqual(result, "break")
        viewer.show_line_view.assert_called_once_with("A")
        self.assertIsNone(viewer.hover_canvas_point)
        self.assertIsNone(viewer.cursor_readout_coordinates)
        self.assertFalse(viewer.show_cursor_guides)

    def test_show_line_view_uses_line_plot_bounds(self) -> None:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer._set_view_to_plot_bounds = mock.Mock()
        viewer._minimum_zoom = mock.Mock(return_value=1.25)

        with mock.patch.object(base, "METRO_LINE_PLOT_PATHS", {"A": ((0, 0), (100, -50))}):
            base.MetroMapViewer.show_line_view(viewer, "A")

        viewer._set_view_to_plot_bounds.assert_called_once_with(
            0,
            100,
            -50,
            0,
            min_zoom=1.25,
            margin_pixels=base.TARGET_MAP_VIEW_MARGIN_PIXELS,
        )

    def test_finish_startup_delays_reset_until_after_layout_settles(self) -> None:
        class FakeRoot:
            def __init__(self) -> None:
                self.after_calls: list[tuple[int, object]] = []

            def after(self, delay: int, callback: object) -> None:
                self.after_calls.append((delay, callback))

        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.root = FakeRoot()
        viewer._bring_to_front = mock.Mock()

        base.MetroMapViewer._finish_startup(viewer)

        viewer._bring_to_front.assert_called_once_with()
        self.assertEqual(viewer.root.after_calls, [(100, viewer._apply_startup_reset_view)])

    def test_startup_reset_view_uses_reset_after_idle_tasks(self) -> None:
        root = mock.Mock()
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.root = root
        viewer.reset_view = mock.Mock()

        base.MetroMapViewer._apply_startup_reset_view(viewer)

        root.update_idletasks.assert_called_once_with()
        viewer.reset_view.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
