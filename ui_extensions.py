from __future__ import annotations

import tkinter as tk

import legacy_core as base
import path_detection
import path_rendering
import world_map_overrides
import worldgen_speedups
import worldgen_target_fix


_ORIGINAL_BUILD_ROUTE_PANEL = base.MetroMapViewer._build_route_panel


def _append_pathing_extensions(self: "base.MetroMapViewer", parent: tk.Misc) -> None:
    self._make_sidebar_caption('Suggested Walking Paths', parent=parent).pack(anchor='w', padx=16)
    self._make_sidebar_hint(
        'Temporary dotted links that connect village anchors using the current walk network. '
        'Detected village-road nodes are preferred when available.',
        parent=parent,
    ).pack(anchor='w', padx=16, pady=(4, 6))
    self._make_sidebar_checkbox(
        parent,
        text='View suggested walking paths',
        variable=self.show_suggested_walking_paths_var,
        command=self.redraw,
    ).pack(anchor='w', padx=16, pady=(0, 6))
    self._make_sidebar_checkbox(
        parent,
        text='Hide path nodes',
        variable=self.hide_path_nodes_var,
        command=self.redraw,
    ).pack(anchor='w', padx=16, pady=(0, 12))


def _append_world_map_extensions(self: "base.MetroMapViewer", parent: tk.Misc) -> None:
    self._make_sidebar_caption('World Map Analysis', parent=parent).pack(anchor='w', padx=16)
    self._make_sidebar_hint(
        'Circle internal blank holes inside the currently rendered map. '
        'They are found in the background and appear one by one.',
        parent=parent,
    ).pack(anchor='w', padx=16, pady=(4, 6))
    self._make_sidebar_checkbox(
        parent,
        text='Circle internal voids',
        variable=self.circle_internal_voids_var,
        command=self.redraw,
    ).pack(anchor='w', padx=16, pady=(0, 12))
    self._make_sidebar_button(
        parent,
        text='Export Block PNG',
        command=self._export_visible_block_png,
    ).pack(anchor='w', padx=16, pady=(0, 12))


def _patched_build_route_panel(self: "base.MetroMapViewer") -> None:
    if not hasattr(self, "show_suggested_walking_paths_var"):
        self.show_suggested_walking_paths_var = tk.BooleanVar(master=self.root, value=False)
    if not hasattr(self, "hide_path_nodes_var"):
        self.hide_path_nodes_var = tk.BooleanVar(master=self.root, value=False)
    if not hasattr(self, "circle_internal_voids_var"):
        self.circle_internal_voids_var = tk.BooleanVar(master=self.root, value=False)

    captured_sections: dict[str, tk.Frame] = {}
    original_make_section = self._make_collapsible_sidebar_section

    def capture_section(title: str, *, expanded: bool) -> tk.Frame:
        section_body = original_make_section(title, expanded=expanded)
        captured_sections[title] = section_body
        return section_body

    self._make_collapsible_sidebar_section = capture_section
    try:
        _ORIGINAL_BUILD_ROUTE_PANEL(self)
    finally:
        self._make_collapsible_sidebar_section = original_make_section

    pathing_section = captured_sections.get('Pathing')
    if pathing_section is not None:
        _append_pathing_extensions(self, pathing_section)

    world_map_section = captured_sections.get('World Map')
    if world_map_section is not None:
        _append_world_map_extensions(self, world_map_section)


def apply() -> None:
    worldgen_target_fix.apply()
    worldgen_speedups.apply()
    base.MetroMapViewer._build_route_panel = _patched_build_route_panel
    path_rendering.apply()
    path_detection.apply()
    world_map_overrides.apply()
