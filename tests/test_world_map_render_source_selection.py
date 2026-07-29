from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from PIL import Image

import legacy_core as base


class WorldMapRenderSourceSelectionTests(unittest.TestCase):
    def test_prefers_newer_docs_render_metadata_over_stale_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            repo_root = Path(temporary_dir)
            docs_assets = repo_root / "docs" / "assets"
            cache_dir = repo_root / "worldgen_data" / "cache"
            output_dir = repo_root / "worldgen_output"
            docs_assets.mkdir(parents=True)
            cache_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            docs_metadata = docs_assets / "blackport_topdown.render.json"
            stale_cache = cache_dir / "render_cache.json"

            stale_cache.write_text("{}", encoding="utf-8")
            docs_metadata.write_text("{}", encoding="utf-8")

            mode_paths = SimpleNamespace(
                docs_render_image_path=docs_assets / "blackport_topdown.png",
                render_cache_path=stale_cache,
                render_image_path=output_dir / "blackport_topdown.png",
            )

            preferred = base._world_map_preferred_render_metadata_path(
                repo_root,
                mode_paths,
            )

            self.assertIsNotNone(preferred)
            assert preferred is not None
            self.assertEqual(preferred[0], docs_metadata)

    def test_docs_metadata_uses_docs_image_first(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            repo_root = Path(temporary_dir)
            docs_assets = repo_root / "docs" / "assets"
            output_dir = repo_root / "worldgen_output"
            docs_assets.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            docs_image = docs_assets / "blackport_topdown.png"
            output_image = output_dir / "blackport_topdown.png"
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(docs_image)
            Image.new("RGBA", (2, 2), (0, 255, 0, 255)).save(output_image)

            mode_paths = SimpleNamespace(
                docs_render_image_path=docs_image,
                render_cache_path=repo_root / "worldgen_data" / "cache" / "render_cache.json",
                render_image_path=output_image,
            )
            payload = {
                "image_path": str(output_image),
            }
            metadata_path = docs_image.with_suffix(".render.json")

            candidates = base._world_map_image_candidate_paths(
                repo_root,
                mode_paths,
                payload,
                metadata_path,
            )

            self.assertEqual(candidates[0], docs_image)
            self.assertEqual(candidates[1], output_image)


if __name__ == "__main__":
    unittest.main()
