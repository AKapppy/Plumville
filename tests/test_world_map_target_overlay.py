from __future__ import annotations

import unittest

import legacy_core as base


class WorldMapTargetOverlayTests(unittest.TestCase):
    def test_active_target_parser_reads_loader_status(self) -> None:
        self.assertEqual(
            base._world_map_active_target_from_text(
                "Loading Local Seed Surface chunks...\n\nActive target: -6260,3889"
            ),
            (-6260, 3889),
        )

    def test_active_target_parser_reads_rendered_target_status(self) -> None:
        self.assertEqual(
            base._world_map_active_target_from_text("Rendered target square: 120,-80"),
            (120, -80),
        )

    def test_active_target_parser_ignores_target_pool_counts(self) -> None:
        self.assertIsNone(
            base._world_map_active_target_from_text("Pass 1 target pool: 12 blank-pixel targets")
        )


if __name__ == "__main__":
    unittest.main()
