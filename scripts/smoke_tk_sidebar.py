from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ENV_VAR = "PLUMVILLE_RUN_TK_SMOKE"


def _label_texts(widget: tk.Misc) -> list[str]:
    texts: list[str] = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            text = child.cget("text")
            if isinstance(text, str):
                texts.append(text)
        texts.extend(_label_texts(child))
    return texts


def main() -> int:
    if os.environ.get(RUN_ENV_VAR) != "1":
        print(f"SKIP: set {RUN_ENV_VAR}=1 to launch the Tk sidebar smoke test.")
        return 0

    sys.path.insert(0, str(REPO_ROOT))
    import metro_stops

    try:
        metro_stops._apply_extensions_once()
        viewer = metro_stops.base.MetroMapViewer(width=900, height=640)
        viewer.root.update_idletasks()
    except tk.TclError as exc:
        print(f"SKIP: Tk display unavailable: {exc}")
        return 0

    try:
        labels = set(_label_texts(viewer.sidebar))
        expected_headers = {
            "+ Checklist",
            "+ Show/Hide",
            "- Priority List",
            "- Directions",
            "- Pathing",
            "- World Map",
        }
        missing_headers = sorted(expected_headers - labels)
        if missing_headers:
            raise AssertionError(f"Missing sidebar section headers: {', '.join(missing_headers)}")

        defaults = {
            "show_world_map_render_var": True,
            "show_labels_var": True,
            "show_connected_area_var": False,
            "show_planning_circle_var": False,
            "show_alignment_reminders_var": False,
            "show_frontier_highlights_var": False,
            "show_suggested_walking_paths_var": False,
            "show_path_nodes_var": False,
            "circle_internal_voids_var": False,
        }
        for attr_name, expected in defaults.items():
            actual = bool(getattr(viewer, attr_name).get())
            if actual != expected:
                raise AssertionError(f"{attr_name} defaulted to {actual}, expected {expected}")

        if not viewer.route_start_entry.winfo_ismapped():
            viewer.route_start_entry.master.pack(fill="x")

        viewer.route_start_entry.focus_set()
        viewer.root.update()
        viewer._show_suggestion_popup(
            viewer.route_start_entry,
            ["Blackport"],
            on_select=lambda value: viewer.route_start_var.set(value),
        )
        viewer.root.update()
        viewer._apply_suggestion_value("Blackport")
        viewer.root.update()
        if viewer.root.focus_get() is not viewer.route_start_entry:
            raise AssertionError("Route suggestion selection did not restore focus to the From field.")

        viewer.route_end_entry.focus_set()
        viewer.root.update()
        if viewer.root.focus_get() is not viewer.route_end_entry:
            raise AssertionError("Route To field could not receive focus after selecting From.")
        viewer.route_end_var.set("Dicton")
        viewer.root.update()
        if viewer.route_end_var.get() != "Dicton":
            raise AssertionError("Route To field could not be edited after selecting From.")

        if "+ Railway Finishing" in labels or "- Railway Finishing" in labels:
            raise AssertionError("Retired Railway Finishing section is still visible.")

        print("OK: Tk sidebar built and default section state is intact.")
        return 0
    finally:
        viewer.root.destroy()


if __name__ == "__main__":
    sys.exit(main())
