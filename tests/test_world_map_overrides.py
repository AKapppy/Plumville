from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from PIL import Image

import legacy_core as base
import world_map_overrides


def _payload() -> dict[str, object]:
    return {
        "min_x": 0,
        "max_x": 3,
        "min_z": 0,
        "max_z": 3,
        "colored_min_x": 0,
        "colored_max_x": 3,
        "colored_min_z": 0,
        "colored_max_z": 3,
    }


def _viewer(source_image: Image.Image) -> SimpleNamespace:
    viewer = SimpleNamespace()
    viewer.width = 4
    viewer.height = 4
    viewer.root = SimpleNamespace(update_idletasks=mock.Mock())
    viewer.canvas = SimpleNamespace(
        winfo_width=mock.Mock(return_value=4),
        winfo_height=mock.Mock(return_value=4),
    )
    viewer.world_to_canvas = lambda point: (point[0], -point[1])
    viewer._current_world_map_render_underlay = mock.Mock(return_value=(_payload(), source_image))
    viewer._selected_world_map_mode_key = mock.Mock(return_value=None)
    return viewer


class WorldMapOverrideConsolidationTests(unittest.TestCase):
    def test_current_world_map_svg_image_uses_canonical_draw_plan(self) -> None:
        source_image = Image.new("RGBA", (4, 4), (255, 0, 0, 255))
        viewer = _viewer(source_image)

        svg_image = base.MetroMapViewer._current_world_map_svg_image(viewer)

        self.assertIsNotNone(svg_image)
        assert svg_image is not None
        self.assertEqual(svg_image.left, 0)
        self.assertEqual(svg_image.top, 0)
        self.assertEqual(svg_image.width, 3)
        self.assertEqual(svg_image.height, 3)
        self.assertTrue(svg_image.data_uri.startswith("data:image/png;base64,"))

    def test_export_visible_block_png_writes_block_level_file(self) -> None:
        source_image = Image.new("RGBA", (4, 4), (0, 255, 0, 255))
        viewer = _viewer(source_image)

        with tempfile.TemporaryDirectory() as temporary_dir:
            with (
                mock.patch.object(base, "EXPORTS_DIR", Path(temporary_dir)),
                mock.patch("tkinter.messagebox.showerror") as showerror,
                mock.patch("tkinter.messagebox.showinfo") as showinfo,
            ):
                base.MetroMapViewer._export_visible_block_png(viewer)

            exported_files = sorted(Path(temporary_dir).glob("world-map-blocks-*.png"))

        self.assertEqual(len(exported_files), 1)
        showerror.assert_not_called()
        showinfo.assert_called_once()

    def test_world_map_overrides_apply_is_compatibility_noop(self) -> None:
        before_underlay = base.MetroMapViewer._draw_world_map_render_underlay
        before_svg = base.MetroMapViewer._current_world_map_svg_image
        before_export = base.MetroMapViewer._export_visible_block_png

        original_applied = world_map_overrides._APPLIED
        applied_after_call = False
        try:
            world_map_overrides._APPLIED = False
            world_map_overrides.apply()
            applied_after_call = world_map_overrides._APPLIED
        finally:
            world_map_overrides._APPLIED = original_applied

        self.assertTrue(applied_after_call)
        self.assertIs(base.MetroMapViewer._draw_world_map_render_underlay, before_underlay)
        self.assertIs(base.MetroMapViewer._current_world_map_svg_image, before_svg)
        self.assertIs(base.MetroMapViewer._export_visible_block_png, before_export)


if __name__ == "__main__":
    unittest.main()
