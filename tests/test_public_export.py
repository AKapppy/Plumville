from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from PIL import Image

import legacy_core as base
from plumville.core import public_export


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"


class PublicExportTests(unittest.TestCase):
    def test_public_docs_pass_shared_export_validation(self) -> None:
        public_export.validate_public_docs(DOCS_ROOT)

    def test_text_validator_rejects_private_path_fragments(self) -> None:
        with self.assertRaisesRegex(ValueError, "private/local text fragment"):
            public_export.validate_public_text("bad path: /Users/example/Library/Application Support")

    def test_json_validator_rejects_private_keys_with_location(self) -> None:
        with self.assertRaisesRegex(ValueError, "metro_network.json.stops.0.private_notes"):
            public_export.validate_public_json_keys(
                {"stops": [{"private_notes": "hide me"}]},
                path=("metro_network.json",),
            )

    def test_format_byte_size_uses_human_readable_units(self) -> None:
        self.assertEqual(public_export.format_byte_size(512), "512 B")
        self.assertEqual(public_export.format_byte_size(1536), "1.5 KB")
        self.assertEqual(public_export.format_byte_size(2 * 1024 * 1024), "2.0 MB")

    def test_validate_public_docs_checks_declared_text_and_json_files(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            docs_root = Path(tempdir)
            (docs_root / "assets").mkdir()
            for relative_path in public_export.PUBLIC_TEXT_PATHS:
                path = docs_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            for relative_path in public_export.PUBLIC_JSON_PATHS:
                path = docs_root / relative_path
                path.write_text(json.dumps({"ok": True}), encoding="utf-8")

            public_export.validate_public_docs(docs_root)

    def test_legacy_svg_export_builder_validates_generated_text_before_write(self) -> None:
        options = base.SvgExportOptions(
            include_world_map=False,
            include_grid=False,
            include_metro_lines=False,
            include_stations=False,
            include_labels=False,
            include_path_nodes=False,
            include_walking_paths=False,
            include_connector_paths=False,
            include_current_route=False,
            include_planning_circle=False,
            include_connected_area=False,
            include_alignment_ellipses=False,
            include_frontier_highlights=False,
            include_railway_finishing=False,
        )

        with mock.patch.object(base, "_build_map_svg", return_value="<svg>/Users/example</svg>"):
            with self.assertRaisesRegex(ValueError, "private/local text fragment"):
                base._build_validated_map_svg(
                    width=100,
                    height=100,
                    padding=10,
                    zoom=1.0,
                    pan_x=0.0,
                    pan_y=0.0,
                    visible_line_names=set(),
                    export_options=options,
                    world_map_image=None,
                    current_route=None,
                )

    def test_legacy_current_map_export_text_raises_for_unready_canvas(self) -> None:
        options = base.SvgExportOptions(
            include_world_map=False,
            include_grid=False,
            include_metro_lines=False,
            include_stations=False,
            include_labels=False,
            include_path_nodes=False,
            include_walking_paths=False,
            include_connector_paths=False,
            include_current_route=False,
            include_planning_circle=False,
            include_connected_area=False,
            include_alignment_ellipses=False,
            include_frontier_highlights=False,
            include_railway_finishing=False,
        )
        viewer = object.__new__(base.MetroMapViewer)
        viewer.root = mock.Mock()
        viewer.canvas = mock.Mock()
        viewer.canvas.winfo_width.return_value = 1
        viewer.canvas.winfo_height.return_value = 100

        with self.assertRaisesRegex(ValueError, "canvas is not ready"):
            viewer._build_current_map_svg_export_text(options)

    def test_legacy_current_map_export_text_uses_validated_builder(self) -> None:
        options = base.SvgExportOptions(
            include_world_map=False,
            include_grid=False,
            include_metro_lines=False,
            include_stations=False,
            include_labels=False,
            include_path_nodes=False,
            include_walking_paths=False,
            include_connector_paths=False,
            include_current_route=False,
            include_planning_circle=False,
            include_connected_area=False,
            include_alignment_ellipses=False,
            include_frontier_highlights=False,
            include_railway_finishing=False,
        )
        viewer = object.__new__(base.MetroMapViewer)
        viewer.root = mock.Mock()
        viewer.canvas = mock.Mock()
        viewer.canvas.winfo_width.return_value = 640
        viewer.canvas.winfo_height.return_value = 480
        viewer.padding = 24
        viewer.zoom = 1.5
        viewer.pan_x = 2.0
        viewer.pan_y = -3.0
        viewer.current_route = None
        viewer._visible_line_names = mock.Mock(return_value={"A"})

        with mock.patch.object(base, "_build_validated_map_svg", return_value="<svg />\n") as build:
            self.assertEqual(viewer._build_current_map_svg_export_text(options), "<svg />\n")

        build.assert_called_once()
        self.assertEqual(viewer.width, 640)
        self.assertEqual(viewer.height, 480)
        self.assertEqual(build.call_args.kwargs["visible_line_names"], {"A"})

    def test_legacy_current_map_png_export_writes_visible_block_crop(self) -> None:
        options = base.SvgExportOptions(
            include_world_map=True,
            include_grid=False,
            include_metro_lines=True,
            include_stations=False,
            include_labels=False,
            include_path_nodes=False,
            include_walking_paths=False,
            include_connector_paths=False,
            include_current_route=False,
            include_planning_circle=False,
            include_connected_area=False,
            include_alignment_ellipses=False,
            include_frontier_highlights=False,
            include_railway_finishing=False,
        )
        viewer = object.__new__(base.MetroMapViewer)
        viewer.root = mock.Mock()
        viewer.canvas = mock.Mock()
        viewer.canvas.winfo_width.return_value = 4
        viewer.canvas.winfo_height.return_value = 4
        viewer.world_to_canvas = lambda point: (point[0], -point[1])
        viewer._plot_transform = mock.Mock(return_value=(0, 3, 0, 3, 1.0))
        viewer._visible_line_names = mock.Mock(return_value={"A"})
        viewer.current_route = None
        source_image = Image.new("RGBA", (4, 4), (0, 255, 0, 255))
        source_image.putpixel((2, 2), (255, 0, 0, 255))
        payload = {
            "min_x": 0,
            "max_x": 3,
            "min_z": 0,
            "max_z": 3,
        }
        viewer._current_world_map_render_underlay = mock.Mock(
            return_value=(payload, source_image),
        )
        viewer._selected_world_map_mode_key = mock.Mock(return_value=None)

        original_import = __import__

        def guarded_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "cairosvg":
                raise AssertionError("cairosvg should not be imported")
            return original_import(name, *args, **kwargs)

        with (
            mock.patch("builtins.__import__", side_effect=guarded_import),
            mock.patch.object(
                base,
                "_all_metro_segments",
                return_value=(
                    SimpleNamespace(
                        line_name="A",
                        plot_points=((0, 0), (3, 0)),
                    ),
                ),
            ),
            mock.patch.object(base, "_metro_segment_style", return_value=(1, None)),
            tempfile.TemporaryDirectory() as temporary_dir,
        ):
            png_path = Path(temporary_dir) / "export.png"
            png_path.write_bytes(viewer._build_current_map_png_export_bytes(options))
            with Image.open(png_path) as exported_image:
                exported_image.load()
                self.assertEqual(exported_image.size, (4, 4))
                self.assertEqual(exported_image.getpixel((2, 2)), (255, 0, 0, 255))
                self.assertNotEqual(exported_image.getpixel((1, 0)), (0, 255, 0, 255))

    def test_legacy_current_map_png_export_requires_world_map(self) -> None:
        options = base.SvgExportOptions(
            include_world_map=False,
            include_grid=False,
            include_metro_lines=False,
            include_stations=False,
            include_labels=False,
            include_path_nodes=False,
            include_walking_paths=False,
            include_connector_paths=False,
            include_current_route=False,
            include_planning_circle=False,
            include_connected_area=False,
            include_alignment_ellipses=False,
            include_frontier_highlights=False,
            include_railway_finishing=False,
        )
        viewer = object.__new__(base.MetroMapViewer)

        with self.assertRaisesRegex(ValueError, "World map image"):
            viewer._build_current_map_png_export_bytes(options)


if __name__ == "__main__":
    unittest.main()
