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
            "- Priority List",
            "+ Railway Finishing",
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
            "hide_path_nodes_var": False,
            "circle_internal_voids_var": False,
        }
        for attr_name, expected in defaults.items():
            actual = bool(getattr(viewer, attr_name).get())
            if actual != expected:
                raise AssertionError(f"{attr_name} defaulted to {actual}, expected {expected}")

        print("OK: Tk sidebar built and default section state is intact.")
        return 0
    finally:
        viewer.root.destroy()


if __name__ == "__main__":
    sys.exit(main())
