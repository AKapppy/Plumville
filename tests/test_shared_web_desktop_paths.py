from __future__ import annotations

from pathlib import Path
import unittest

import legacy_core as base
from worldgen.config import load_config
from worldgen.generator import _docs_render_metadata_path


class SharedWebDesktopPathTests(unittest.TestCase):
    def test_desktop_and_web_share_canonical_network_dataset(self) -> None:
        repo_root = Path(base.__file__).resolve().parent
        canonical_network_path = repo_root / "docs" / "metro_network.json"

        self.assertEqual(base.METRO_NETWORK_PATH, canonical_network_path)
        self.assertTrue(canonical_network_path.exists())
        self.assertFalse((repo_root / "metro_network.json").exists())

    def test_worldgen_public_assets_target_web_viewer_files(self) -> None:
        repo_root = Path(base.__file__).resolve().parent
        paths = load_config().paths

        self.assertEqual(
            paths.docs_render_image_path,
            repo_root / "docs" / "assets" / "blackport_topdown.png",
        )
        self.assertEqual(
            _docs_render_metadata_path(paths.docs_render_image_path),
            repo_root / "docs" / "assets" / "blackport_topdown.render.json",
        )


if __name__ == "__main__":
    unittest.main()
