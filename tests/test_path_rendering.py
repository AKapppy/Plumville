from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest import mock

import legacy_core as base
import path_rendering


class _BoolVar:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = value


class _Canvas:
    def __init__(self) -> None:
        self.lines: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.ovals: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.rectangles: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.polygons: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.text: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def create_line(self, *args: object, **kwargs: object) -> None:
        self.lines.append((args, kwargs))

    def create_oval(self, *args: object, **kwargs: object) -> None:
        self.ovals.append((args, kwargs))

    def create_rectangle(self, *args: object, **kwargs: object) -> None:
        self.rectangles.append((args, kwargs))

    def create_polygon(self, *args: object, **kwargs: object) -> None:
        self.polygons.append((args, kwargs))

    def create_text(self, *args: object, **kwargs: object) -> None:
        self.text.append((args, kwargs))


def _viewer(
    *,
    path_click_mode: bool = False,
    selected_path_node_key: str | None = None,
    show_non_orthogonal_segments: bool = False,
) -> SimpleNamespace:
    viewer = SimpleNamespace(
        canvas=_Canvas(),
        zoom=1.0,
        path_node_canvas_positions={},
        show_path_nodes_var=_BoolVar(False),
        show_suggested_walking_paths_var=_BoolVar(False),
        show_non_orthogonal_segments_var=_BoolVar(show_non_orthogonal_segments),
        path_click_mode_var=_BoolVar(path_click_mode),
        city_limits_edit_stop_var=None,
        selected_path_node_key=selected_path_node_key,
        show_labels_var=_BoolVar(True),
        world_to_canvas=lambda point: point,
        _label_offset=lambda: (7, 7),
        _path_nodes_should_show=lambda: path_click_mode,
        _stop_visible_line_names=lambda _stop, visible_line_names: visible_line_names,
    )
    viewer._draw_plot_polyline = lambda plot_points, **kwargs: base.MetroMapViewer._draw_plot_polyline(
        viewer,
        plot_points,
        **kwargs,
    )
    viewer._plot_points_to_canvas_line_points = (
        lambda plot_points: base.MetroMapViewer._plot_points_to_canvas_line_points(
            viewer,
            plot_points,
        )
    )
    return viewer


class PathRenderingConsolidationTests(unittest.TestCase):
    def test_hidden_path_nodes_skip_shapes_when_no_hit_targets_needed(self) -> None:
        viewer = _viewer(path_click_mode=False)
        path_node = SimpleNamespace(
            key="node:a",
            plot_coordinates=(10, 20),
            poi_kind=None,
            label="A",
            display_label="A",
        )

        with mock.patch.object(base, "_all_path_nodes", return_value=(path_node,)):
            base.MetroMapViewer._draw_path_nodes(viewer)

        self.assertEqual(viewer.path_node_canvas_positions, {})
        self.assertEqual(viewer.canvas.ovals, [])
        self.assertEqual(viewer.canvas.rectangles, [])
        self.assertEqual(viewer.canvas.text, [])

    def test_map_pathing_mode_draws_path_nodes(self) -> None:
        viewer = _viewer(path_click_mode=True, selected_path_node_key="node:a")
        path_node = SimpleNamespace(
            key="node:a",
            plot_coordinates=(10, 20),
            poi_kind=None,
            label="A",
            display_label="A",
        )

        with mock.patch.object(base, "_all_path_nodes", return_value=(path_node,)):
            base.MetroMapViewer._draw_path_nodes(viewer)

        self.assertEqual(viewer.path_node_canvas_positions, {"node:a": (10, 20)})
        self.assertEqual(len(viewer.canvas.rectangles), 1)

    def test_suggested_walking_paths_draw_after_extra_edges(self) -> None:
        viewer = _viewer()
        viewer.show_suggested_walking_paths_var = _BoolVar(True)
        segment = SimpleNamespace(path_coordinates=((1, 2), (3, 4)))

        with (
            mock.patch.object(base, "EXTRA_EDGES", ()),
            mock.patch("walking_suggestions.build_suggested_segments", return_value=(segment,)),
        ):
            base.MetroMapViewer._draw_extra_edges(viewer)

        self.assertEqual(len(viewer.canvas.lines), 1)
        args, kwargs = viewer.canvas.lines[0]
        self.assertEqual(args, (1, -2, 3, -4))
        self.assertEqual(kwargs["dash"], (8, 6))
        self.assertTrue(kwargs["smooth"])

    def test_station_entry_draws_small_dot_with_dotted_link_when_zoomed_in(self) -> None:
        viewer = _viewer()
        viewer.zoom = base.STATION_ENTRY_MIN_ZOOM
        stop = base.MetroStop(
            "P_A",
            "Alpha",
            10,
            20,
            station_entry_x=14,
            station_entry_y=24,
        )

        with (
            mock.patch.object(base, "METRO_STOPS", (stop,)),
            mock.patch.object(base, "STOP_LINE_NAMES", {stop.var: ("A",)}),
        ):
            base.MetroMapViewer._draw_station_entries(viewer, frozenset({"A"}))

        self.assertEqual(len(viewer.canvas.lines), 1)
        self.assertEqual(viewer.canvas.lines[0][1]["dash"], base.STATION_ENTRY_LINK_DASH)
        self.assertEqual(viewer.canvas.lines[0][1]["fill"], base.STATION_ENTRY_LINK_COLOR)
        self.assertEqual(len(viewer.canvas.ovals), 1)
        self.assertLessEqual(
            viewer.canvas.ovals[0][0][2] - viewer.canvas.ovals[0][0][0],
            base.STATION_RADIUS,
        )

    def test_metro_segments_draw_solid_dashed_and_dotted_by_construction_state(self) -> None:
        viewer = _viewer()
        connected = base.MetroLineSegment(
            "A",
            "P_A1",
            "P_A2",
            (base.LinePathPointSpec("P_A1", "P_A1"), base.LinePathPointSpec("P_A2", "P_A2")),
        )
        tunneled = base.MetroLineSegment(
            "A",
            "P_A3",
            "P_A4",
            (base.LinePathPointSpec("P_A3", "P_A3"), base.LinePathPointSpec("P_A4", "P_A4")),
        )
        planned = base.MetroLineSegment(
            "A",
            "P_A5",
            "P_A6",
            (base.LinePathPointSpec("P_A5", "P_A5"), base.LinePathPointSpec("P_A6", "P_A6")),
        )
        stops = {
            "P_A1": base.MetroStop("P_A1", "A1", 0, 0, is_connected=True),
            "P_A2": base.MetroStop("P_A2", "A2", 10, 0, is_connected=True),
            "P_A3": base.MetroStop("P_A3", "A3", 20, 0, is_tunneled=True),
            "P_A4": base.MetroStop("P_A4", "A4", 30, 0, is_tunneled=True),
            "P_A5": base.MetroStop("P_A5", "A5", 40, 0),
            "P_A6": base.MetroStop("P_A6", "A6", 50, 0),
        }

        with (
            mock.patch.object(base, "STOPS_BY_VAR", stops),
            mock.patch.object(base, "LINE_COLORS", {"A": "#ff0000"}),
            mock.patch.object(base, "LINE_TUNNELED_STOP_VARS", {"A": frozenset(("P_A1", "P_A2", "P_A3", "P_A4"))}),
            mock.patch.object(base, "_all_metro_segments", return_value=(connected, tunneled, planned)),
        ):
            base.MetroMapViewer._draw_metro_lines(viewer, {"A"})

        self.assertNotIn("dash", viewer.canvas.lines[0][1])
        self.assertEqual(viewer.canvas.lines[1][1]["dash"], base.TUNNELED_RAILWAY_DASH)
        self.assertEqual(viewer.canvas.lines[2][1]["dash"], base.PLANNED_RAILWAY_DASH)

    def test_non_orthogonal_highlight_draws_only_when_toggle_is_on(self) -> None:
        diagonal_segment = base.MetroLineSegment(
            "A",
            "P_A1",
            "P_A2",
            (
                base.LinePathPointSpec("P_A1", "P_A1"),
                base.LinePathPointSpec("P_A2", "P_A2"),
            ),
        )
        stops = {
            "P_A1": base.MetroStop("P_A1", "A1", 0, 0),
            "P_A2": base.MetroStop("P_A2", "A2", 10, 10),
        }

        hidden_viewer = _viewer(show_non_orthogonal_segments=False)
        visible_viewer = _viewer(show_non_orthogonal_segments=True)
        with (
            mock.patch.object(base, "STOPS_BY_VAR", stops),
            mock.patch.object(base, "_all_metro_segments", return_value=(diagonal_segment,)),
        ):
            base.MetroMapViewer._draw_non_orthogonal_segment_highlights(hidden_viewer, {"A"})
            base.MetroMapViewer._draw_non_orthogonal_segment_highlights(visible_viewer, {"A"})

        self.assertEqual(hidden_viewer.canvas.lines, [])
        self.assertEqual(len(visible_viewer.canvas.lines), 1)
        self.assertEqual(
            visible_viewer.canvas.lines[0][1]["fill"],
            base.NON_ORTHOGONAL_SEGMENT_HIGHLIGHT,
        )

    def test_shared_geometry_can_be_tunneled_for_one_line_only(self) -> None:
        viewer = _viewer()
        line_a_segment = base.MetroLineSegment(
            "A",
            "P_AB1",
            "P_AB2",
            (base.LinePathPointSpec("P_AB1", "P_AB1"), base.LinePathPointSpec("P_AB2", "P_AB2")),
        )
        line_b_segment = base.MetroLineSegment(
            "B",
            "P_AB1",
            "P_AB2",
            (base.LinePathPointSpec("P_AB1", "P_AB1"), base.LinePathPointSpec("P_AB2", "P_AB2")),
        )
        stops = {
            "P_AB1": base.MetroStop("P_AB1", "AB1", 0, 0, is_tunneled=True),
            "P_AB2": base.MetroStop("P_AB2", "AB2", 10, 0, is_tunneled=True),
        }

        with (
            mock.patch.object(base, "STOPS_BY_VAR", stops),
            mock.patch.object(base, "LINE_COLORS", {"A": "#ff0000", "B": "#00ff00"}),
            mock.patch.object(
                base,
                "LINE_TUNNELED_STOP_VARS",
                {"A": frozenset(("P_AB1", "P_AB2")), "B": frozenset()},
            ),
            mock.patch.object(base, "_all_metro_segments", return_value=(line_a_segment, line_b_segment)),
        ):
            base.MetroMapViewer._draw_metro_lines(viewer, {"A", "B"})

        self.assertEqual(viewer.canvas.lines[0][1]["dash"], base.TUNNELED_RAILWAY_DASH)
        self.assertEqual(viewer.canvas.lines[1][1]["dash"], base.PLANNED_RAILWAY_DASH)

    def test_path_rendering_apply_is_compatibility_noop(self) -> None:
        before_extra_edges = base.MetroMapViewer._draw_extra_edges
        before_path_nodes = base.MetroMapViewer._draw_path_nodes

        original_applied = path_rendering._APPLIED
        applied_after_call = False
        try:
            path_rendering._APPLIED = False
            path_rendering.apply()
            applied_after_call = path_rendering._APPLIED
        finally:
            path_rendering._APPLIED = original_applied

        self.assertTrue(applied_after_call)
        self.assertIs(base.MetroMapViewer._draw_extra_edges, before_extra_edges)
        self.assertIs(base.MetroMapViewer._draw_path_nodes, before_path_nodes)


if __name__ == "__main__":
    unittest.main()
