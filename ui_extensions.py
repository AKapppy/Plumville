from __future__ import annotations

import tkinter as tk

import legacy_core as base
import path_rendering
import world_map_overrides
import worldgen_target_fix


_ORIGINAL_BUILD_ROUTE_PANEL = base.MetroMapViewer._build_route_panel


def _patched_build_route_panel(self: "base.MetroMapViewer") -> None:
    if not hasattr(self, "show_suggested_walking_paths_var"):
        self.show_suggested_walking_paths_var = tk.BooleanVar(master=self.root, value=False)
    if not hasattr(self, "hide_path_nodes_var"):
        self.hide_path_nodes_var = tk.BooleanVar(master=self.root, value=False)

    _ORIGINAL_BUILD_ROUTE_PANEL(self)

    suggested_section = self._make_collapsible_sidebar_section("Suggested Walking Paths", expanded=False)
    self._make_sidebar_hint(
        "Temporary dotted links that connect village anchors using the current walk network. "
        "A nearby explicit node is used when available; otherwise the station is used.",
        parent=suggested_section,
    ).pack(anchor="w", padx=16, pady=(4, 6))
    self._make_sidebar_checkbox(
        suggested_section,
        text="View suggested walking paths",
        variable=self.show_suggested_walking_paths_var,
        command=self.redraw,
    ).pack(anchor="w", padx=16, pady=(0, 6))
    self._make_sidebar_checkbox(
        suggested_section,
        text="Hide path nodes",
        variable=self.hide_path_nodes_var,
        command=self.redraw,
    ).pack(anchor="w", padx=16, pady=(0, 12))


def apply() -> None:
    worldgen_target_fix.apply()
    base.MetroMapViewer._build_route_panel = _patched_build_route_panel
    path_rendering.apply()
    world_map_overrides.apply()
