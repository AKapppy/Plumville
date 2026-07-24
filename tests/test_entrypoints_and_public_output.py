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
