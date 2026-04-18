from __future__ import annotations

import legacy_core as base
from walking_suggestions import build_suggested_segments


_ORIGINAL_DRAW_EXTRA_EDGES = base.MetroMapViewer._draw_extra_edges
_ORIGINAL_DRAW_PATH_NODES = base.MetroMapViewer._draw_path_nodes


def _draw_suggested_walking_paths(self: "base.MetroMapViewer") -> None:
    if not self.show_suggested_walking_paths_var.get():
        return

    for segment in build_suggested_segments(base):
        start_x, start_y = self.world_to_canvas((segment.start_coordinates[0], -segment.start_coordinates[1]))
        end_x, end_y = self.world_to_canvas((segment.end_coordinates[0], -segment.end_coordinates[1]))
        self.canvas.create_line(
            start_x,
            start_y,
            end_x,
            end_y,
            fill=base.WALK_ROUTE_COLOR,
            width=4,
            dash=(8, 6),
            capstyle="round",
            joinstyle="round",
        )


def _patched_draw_extra_edges(self: "base.MetroMapViewer") -> None:
    _ORIGINAL_DRAW_EXTRA_EDGES(self)
    _draw_suggested_walking_paths(self)


def _patched_draw_path_nodes(self: "base.MetroMapViewer") -> None:
    if self.show_suggested_walking_paths_var.get() and self.hide_path_nodes_var.get():
        self.path_node_canvas_positions = {}
        for path_node in base._all_path_nodes():
            canvas_x, canvas_y = self.world_to_canvas(path_node.plot_coordinates)
            self.path_node_canvas_positions[path_node.key] = (canvas_x, canvas_y)
        return

    label_font_size = max(10, base._label_font_size(self.zoom) - 1)
    label_offset_x, label_offset_y = self._label_offset()
    self.path_node_canvas_positions = {}

    for path_node in base._all_path_nodes():
        canvas_x, canvas_y = self.world_to_canvas(path_node.plot_coordinates)
        self.path_node_canvas_positions[path_node.key] = (canvas_x, canvas_y)
        radius = 5 if path_node.key == self.selected_path_node_key else 3
        outline_width = 2 if path_node.key == self.selected_path_node_key else 1
        self.canvas.create_oval(
            canvas_x - radius,
            canvas_y - radius,
            canvas_x + radius,
            canvas_y + radius,
            fill=base.PATH_NODE_FILL,
            outline=base.PATH_NODE_OUTLINE,
            width=outline_width,
        )
        if self.show_labels_var.get() and path_node.label:
            self.canvas.create_text(
                canvas_x + label_offset_x,
                canvas_y - label_offset_y,
                anchor="sw",
                angle=base.LABEL_ANGLE,
                text=path_node.label,
                fill=base.PATH_NODE_LABEL_COLOR,
                font=("Helvetica", label_font_size),
            )


def apply() -> None:
    base.MetroMapViewer._draw_extra_edges = _patched_draw_extra_edges
    base.MetroMapViewer._draw_path_nodes = _patched_draw_path_nodes
