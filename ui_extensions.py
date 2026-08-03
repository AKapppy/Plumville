from __future__ import annotations

import tkinter as tk
from typing import Callable

import desktop_improvements
import legacy_core as base
import metro_station_extensions
import path_detection
import path_rendering
import poi_extensions
import world_map_overrides
import worldgen_speedups


_ORIGINAL_BUILD_ROUTE_PANEL: Callable[..., None] | None = None
_APPLIED = False
_APPLIED_ATTR = "_plumville_ui_extensions_applied"
_ORIGINAL_BUILD_ATTR = "_plumville_ui_original_build_route_panel"


def _append_pathing_extensions(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
) -> None:
    self._make_sidebar_caption(
        "Add",
        parent=parent,
    ).pack(anchor="w", padx=16)
    button_row = tk.Frame(parent, bg=base.BACKGROUND_COLOR)
    button_row.pack(fill="x", padx=16, pady=(4, 12))
    for column in range(3):
        button_row.grid_columnconfigure(column, weight=1, uniform="pathing-add")
    self._make_sidebar_button(
        button_row,
        text="Add Metro Station",
        command=self._show_add_metro_station_dialog,
    ).grid(row=0, column=0, sticky="ew")
    self._make_sidebar_button(
        button_row,
        text="Add PoI",
        command=self._show_add_poi_dialog,
    ).grid(row=0, column=1, sticky="ew", padx=(8, 0))
    self._make_sidebar_button(
        button_row,
        text="Add Path",
        command=self._activate_intercity_pathing,
    ).grid(row=0, column=2, sticky="ew", padx=(8, 0))

    self._make_sidebar_caption(
        "Suggested Walking Paths",
        parent=parent,
    ).pack(anchor="w", padx=16)
    self._make_sidebar_checkbox(
        parent,
        text="View suggested walking paths",
        variable=self.show_suggested_walking_paths_var,
        command=self.redraw,
    ).pack(anchor="w", padx=16, pady=(4, 6))


def _append_world_map_extensions(
    self: "base.MetroMapViewer",
    parent: tk.Misc,
) -> None:
    self._make_sidebar_caption(
        "World Map Analysis",
        parent=parent,
    ).pack(anchor="w", padx=16)
    self._make_sidebar_hint(
        (
            "Circle internal blank holes inside the "
            "currently rendered map. They are found "
            "in the background and appear one by one."
        ),
        parent=parent,
    ).pack(anchor="w", padx=16, pady=(4, 6))
    self._make_sidebar_checkbox(
        parent,
        text="Circle internal voids",
        variable=self.circle_internal_voids_var,
        command=self.redraw,
    ).pack(anchor="w", padx=16, pady=(0, 12))
    self._make_sidebar_button(
        parent,
        text="Export Block PNG",
        command=self._export_visible_block_png,
    ).pack(anchor="w", padx=16, pady=(0, 12))


def _patched_build_route_panel(
    self: "base.MetroMapViewer",
) -> None:
    assert _ORIGINAL_BUILD_ROUTE_PANEL is not None
    if not hasattr(
        self,
        "show_suggested_walking_paths_var",
    ):
        self.show_suggested_walking_paths_var = (
            tk.BooleanVar(
                master=self.root,
                value=False,
            )
        )
    if not hasattr(self, "show_path_nodes_var"):
        self.show_path_nodes_var = tk.BooleanVar(
            master=self.root,
            value=False,
        )
    if not hasattr(self, "circle_internal_voids_var"):
        self.circle_internal_voids_var = tk.BooleanVar(
            master=self.root,
            value=False,
        )

    captured_sections: dict[str, tk.Frame] = {}
    original_make_section = (
        self._make_collapsible_sidebar_section
    )

    def capture_section(
        title: str,
        *,
        expanded: bool,
    ) -> tk.Frame:
        section_body = original_make_section(
            title,
            expanded=(
                True
                if title == "Pathing"
                else expanded
            ),
        )
        captured_sections[title] = section_body
        return section_body

    self._make_collapsible_sidebar_section = (
        capture_section
    )
    try:
        _ORIGINAL_BUILD_ROUTE_PANEL(self)
    finally:
        self._make_collapsible_sidebar_section = (
            original_make_section
        )

    pathing_section = captured_sections.get("Pathing")
    if pathing_section is not None:
        _append_pathing_extensions(
            self,
            pathing_section,
        )

    world_map_section = captured_sections.get(
        "World Map"
    )
    if world_map_section is not None:
        _append_world_map_extensions(
            self,
            world_map_section,
        )


def apply() -> None:
    global _APPLIED
    global _ORIGINAL_BUILD_ROUTE_PANEL

    if _APPLIED:
        return
    if getattr(base.MetroMapViewer, _APPLIED_ATTR, False):
        _ORIGINAL_BUILD_ROUTE_PANEL = getattr(
            base.MetroMapViewer,
            _ORIGINAL_BUILD_ATTR,
            None,
        )
        _APPLIED = True
        return

    worldgen_speedups.apply()
    metro_station_extensions.apply()
    poi_extensions.apply()
    _ORIGINAL_BUILD_ROUTE_PANEL = (
        base.MetroMapViewer._build_route_panel
    )
    setattr(
        base.MetroMapViewer,
        _ORIGINAL_BUILD_ATTR,
        _ORIGINAL_BUILD_ROUTE_PANEL,
    )
    base.MetroMapViewer._build_route_panel = (
        _patched_build_route_panel
    )
    path_rendering.apply()
    path_detection.apply()
    world_map_overrides.apply()
    desktop_improvements.apply()
    setattr(base.MetroMapViewer, _APPLIED_ATTR, True)
    _APPLIED = True
