from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest import mock

import legacy_core as base


class _Var:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def set(self, value: object) -> None:
        self.value = value


class CityLimitPathingTest(unittest.TestCase):
    def _viewer(self) -> base.MetroMapViewer:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.width = 400
        viewer.height = 300
        viewer.selected_stop_var = None
        viewer.selected_path_node_key = None
        viewer.city_limits_edit_stop_var = None
        viewer.city_limits_pending_node_keys = ()
        viewer.pathing_town_stop_var = None
        viewer.path_click_mode_var = _Var(False)
        viewer.show_city_limits_var = _Var(False)
        viewer.show_path_nodes_var = _Var(False)
        viewer.path_click_status_var = _Var("")
        viewer.route_controls_dirty = False
        viewer.route_dirty = False
        viewer.priority_dirty = False
        viewer.stats_dirty = False
        viewer.root = object()
        viewer._clear_metro_segment_selection = mock.Mock()
        viewer.redraw = mock.Mock()
        viewer.canvas_to_world = lambda point: (round(point[0]), round(point[1]))
        return viewer

    def test_pathing_context_infers_nearest_station_when_zoomed_in(self) -> None:
        viewer = self._viewer()
        viewer.canvas_to_world = lambda point: (round(point[0] / 4), round(point[1] / 4))
        alpha = base.MetroStop("P_A", "Alpha", 40, 35)
        beta = base.MetroStop("P_B", "Beta", 600, 600)

        with mock.patch.object(base, "METRO_STOPS", (alpha, beta)):
            context = base.MetroMapViewer._pathing_context_stop(viewer)

        self.assertEqual(context, alpha)
        self.assertEqual(viewer.pathing_town_stop_var, alpha.var)

    def test_pathing_context_requires_zoom_or_selected_station(self) -> None:
        viewer = self._viewer()
        viewer.canvas_to_world = lambda point: (round(point[0] * 10), round(point[1] * 10))
        alpha = base.MetroStop("P_A", "Alpha", 0, 0)

        with mock.patch.object(base, "METRO_STOPS", (alpha,)):
            context = base.MetroMapViewer._pathing_context_stop(viewer)

        self.assertIsNone(context)

    def test_city_limit_suggestion_uses_nodes_owned_by_nearest_town(self) -> None:
        viewer = self._viewer()
        alpha = base.MetroStop("P_A", "Alpha", 0, 0)
        beta = base.MetroStop("P_B", "Beta", 1000, 0)
        alpha_nodes = (
            base.PathNode("n1", 10, 0),
            base.PathNode("n2", 0, 10),
            base.PathNode("n3", -10, 0),
        )
        beta_node = base.PathNode("n4", 990, 0)

        with (
            mock.patch.object(base, "METRO_STOPS", (alpha, beta)),
            mock.patch.object(base, "_all_path_nodes", return_value=(*alpha_nodes, beta_node)),
            mock.patch.object(
                base,
                "_all_path_nodes_by_key",
                return_value={node.key: node for node in (*alpha_nodes, beta_node)},
            ),
        ):
            node_keys = base.MetroMapViewer._suggested_city_limit_node_keys_for_stop(viewer, alpha.var)

        self.assertEqual(set(node_keys), {node.key for node in alpha_nodes})
        self.assertNotIn(beta_node.key, node_keys)

    def test_ordered_city_limit_node_keys_uses_outer_hull(self) -> None:
        viewer = self._viewer()
        nodes = (
            base.PathNode("west", -10, 0),
            base.PathNode("south", 0, -10),
            base.PathNode("east", 10, 0),
            base.PathNode("north", 0, 10),
            base.PathNode("center", 0, 0),
        )

        with mock.patch.object(
            base,
            "_all_path_nodes_by_key",
            return_value={node.key: node for node in nodes},
        ):
            node_keys = base.MetroMapViewer._ordered_city_limit_node_keys(
                viewer,
                tuple(node.key for node in nodes),
            )

        self.assertEqual(
            set(node_keys),
            {"coord:-10,0", "coord:0,-10", "coord:10,0", "coord:0,10"},
        )
        self.assertNotIn("coord:0,0", node_keys)

    def test_start_city_limits_edit_uses_suggestion_without_saving(self) -> None:
        viewer = self._viewer()
        alpha = base.MetroStop("P_A", "Alpha", 0, 0)

        with (
            mock.patch.object(base, "STOPS_BY_VAR", {alpha.var: alpha}),
            mock.patch.object(
                base.MetroMapViewer,
                "_suggested_city_limit_node_keys_for_stop",
                return_value=("coord:0,0", "coord:1,0", "coord:0,1"),
            ),
        ):
            base.MetroMapViewer._start_city_limits_edit(viewer, alpha.var)

        self.assertEqual(viewer.city_limits_edit_stop_var, alpha.var)
        self.assertEqual(viewer.city_limits_pending_node_keys, ("coord:0,0", "coord:1,0", "coord:0,1"))
        self.assertTrue(viewer.path_click_mode_var.get())
        self.assertTrue(viewer.show_city_limits_var.get())

    def test_confirm_city_limits_edit_saves_pending_polygon(self) -> None:
        viewer = self._viewer()
        viewer.city_limits_edit_stop_var = "P_A"
        viewer.city_limits_pending_node_keys = ("coord:0,0", "coord:1,0", "coord:0,1")
        alpha = base.MetroStop("P_A", "Alpha", 0, 0)

        with (
            mock.patch.object(base, "STOPS_BY_VAR", {alpha.var: alpha}),
            mock.patch.object(base, "set_stop_city_limit_node_keys") as save_limits,
        ):
            base.MetroMapViewer._confirm_city_limits_edit(viewer)

        save_limits.assert_called_once_with("P_A", ("coord:0,0", "coord:1,0", "coord:0,1"))
        self.assertIsNone(viewer.city_limits_edit_stop_var)
        self.assertEqual(viewer.city_limits_pending_node_keys, ())
        self.assertTrue(viewer.route_dirty)


if __name__ == "__main__":
    unittest.main()
