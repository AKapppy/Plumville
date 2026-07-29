from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from plumville.core import public_export


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"


class EntrypointAndPublicOutputTests(unittest.TestCase):
    def test_metro_stops_extension_application_is_idempotent(self) -> None:
        probe = """
import json
import metro_stops
import ui_extensions

metro_stops._apply_extensions_once()
base = metro_stops.base
first = {
    name: id(getattr(base.MetroMapViewer, name))
    for name in (
        "_build_route_panel",
        "redraw",
        "_draw_selected_stop_info",
        "_draw_extra_edges",
        "_draw_path_nodes",
        "_draw_world_map_render_underlay",
    )
}
metro_stops._apply_extensions_once()
second = {name: id(getattr(base.MetroMapViewer, name)) for name in first}
ui_extensions.apply()
third = {name: id(getattr(base.MetroMapViewer, name)) for name in first}
print(json.dumps({"applied": metro_stops._EXTENSIONS_APPLIED, "stable": first == second == third}))
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["applied"])
        self.assertTrue(payload["stable"])

    def test_extension_reapply_after_module_reload_keeps_wrapper_chain(self) -> None:
        probe = """
import importlib
import json
import metro_stops
import ui_extensions
import desktop_improvements

metro_stops._apply_extensions_once()
base = metro_stops.base

def snapshot():
    return {
        name: id(getattr(base.MetroMapViewer, name))
        for name in (
            "_build_route_panel",
            "_draw_selected_stop_info",
            "_refresh_current_route",
            "_plan_route",
            "_on_route_options_changed",
            "_set_world_map_status_text",
        )
    }

first = snapshot()
importlib.reload(ui_extensions)
ui_extensions.apply()
after_ui_reload = snapshot()
importlib.reload(desktop_improvements)
desktop_improvements.apply()
after_desktop_reload = snapshot()

payload = {
    "stable": first == after_ui_reload == after_desktop_reload,
    "build_wrapper": [
        base.MetroMapViewer._build_route_panel.__module__,
        base.MetroMapViewer._build_route_panel.__name__,
    ],
    "draw_wrapper": [
        base.MetroMapViewer._draw_selected_stop_info.__module__,
        base.MetroMapViewer._draw_selected_stop_info.__name__,
    ],
    "ui_original_ready": (
        ui_extensions._ORIGINAL_BUILD_ROUTE_PANEL is not None
    ),
    "desktop_originals_ready": all(
        getattr(desktop_improvements, name) is not None
        for name in (
            "_ORIGINAL_BUILD_ROUTE_PANEL",
            "_ORIGINAL_REFRESH_CURRENT_ROUTE",
            "_ORIGINAL_PLAN_ROUTE",
            "_ORIGINAL_ON_ROUTE_OPTIONS_CHANGED",
            "_ORIGINAL_SET_WORLD_MAP_STATUS_TEXT",
            "_NORMAL_DRAW_SELECTED_STOP_INFO",
        )
    ),
}
print(json.dumps(payload))
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["stable"])
        self.assertEqual(
            payload["build_wrapper"],
            ["desktop_improvements", "_patched_build_route_panel"],
        )
        self.assertEqual(
            payload["draw_wrapper"],
            [
                "desktop_improvements",
                "_draw_selected_stop_info_without_detection_button",
            ],
        )
        self.assertTrue(payload["ui_original_ready"])
        self.assertTrue(payload["desktop_originals_ready"])

    def test_public_docs_text_outputs_do_not_expose_private_local_details(self) -> None:
        for relative_path in public_export.PUBLIC_TEXT_PATHS:
            path = DOCS_ROOT / relative_path
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                public_export.validate_public_text(path.read_text(encoding="utf-8"))

    def test_public_json_outputs_do_not_include_private_fields(self) -> None:
        for relative_path in public_export.PUBLIC_JSON_PATHS:
            path = DOCS_ROOT / relative_path
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                public_export.validate_public_json_keys(
                    json.loads(path.read_text(encoding="utf-8")),
                    path=(path.name,),
                )


if __name__ == "__main__":
    unittest.main()
