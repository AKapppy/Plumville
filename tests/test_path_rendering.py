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


def _viewer(*, show_path_nodes: bool = True, selected_path_node_key: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        canvas=_Canvas(),
        zoom=1.0,
        path_node_canvas_positions={},
        show_path_nodes_var=_BoolVar(show_path_nodes),
        show_suggested_walking_paths_var=_BoolVar(False),
        path_click_mode_var=_BoolVar(False),
        city_limits_edit_stop_var=None,
        selected_path_node_key=selected_path_node_key,
        show_labels_var=_BoolVar(True),
        world_to_canvas=lambda point: point,
        _label_offset=lambda: (7, 7),
    )


class PathRenderingConsolidationTests(unittest.TestCase):
    def test_hidden_path_nodes_skip_shapes_when_no_hit_targets_needed(self) -> None:
        viewer = _viewer(show_path_nodes=False)
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

    def test_hidden_path_nodes_keep_positions_for_selection_hit_targets(self) -> None:
        viewer = _viewer(show_path_nodes=False, selected_path_node_key="node:a")
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
        self.assertEqual(viewer.canvas.rectangles, [])

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
