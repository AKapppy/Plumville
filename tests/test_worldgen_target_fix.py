from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

import worldgen_target_fix
from worldgen import generator


class WorldgenTargetPlannerTests(unittest.TestCase):
    def test_render_area_teleport_points_prepends_promoted_targets(self) -> None:
        with (
            mock.patch.object(
                generator,
                "_blank_pixel_fill_teleport_points",
                return_value=((10, 10), (20, 20), (30, 30)),
            ),
            mock.patch.object(
                generator,
                "_promoted_largest_targets",
                return_value=((20, 20), (5, 5)),
            ),
        ):
            blank_coverage = SimpleNamespace(blank_pixels_by_chunk={})
            points = generator._render_area_teleport_points(
                object(),
                world_path=object(),
                blank_coverage=blank_coverage,
            )

        self.assertEqual(points, ((20, 20), (5, 5), (10, 10), (30, 30)))

    def test_render_area_teleport_points_keeps_base_planner_without_blank_coverage(self) -> None:
        with mock.patch.object(
            generator,
            "_blank_space_fill_teleport_points",
            return_value=((10, 10),),
        ):
            points = generator._render_area_teleport_points(
                object(),
                world_path=None,
                blank_coverage=None,
            )

        self.assertEqual(points, ((10, 10),))

    def test_next_undercovered_index_prefers_promoted_missing_target(self) -> None:
        with (
            mock.patch.object(
                generator,
                "_promoted_largest_targets",
                return_value=((20, 20),),
            ),
            mock.patch.object(
                generator,
                "_teleport_point_missing_pixel_count",
                side_effect=lambda _config, point, _coverage: 1 if point == (20, 20) else 0,
            ),
        ):
            index = generator._next_undercovered_teleport_index(
                object(),
                ((10, 10), (20, 20), (30, 30)),
                start_index=2,
                world_path=object(),
                blank_coverage=object(),
            )

        self.assertEqual(index, 1)

    def test_next_undercovered_index_uses_actionable_then_positive_missing_pixels(self) -> None:
        missing_by_point = {
            (10, 10): 0,
            (20, 20): 1,
            (30, 30): 4_096,
        }

        with (
            mock.patch.object(generator, "_promoted_largest_targets", return_value=()),
            mock.patch.object(
                generator,
                "_teleport_point_missing_pixel_count",
                side_effect=lambda _config, point, _coverage: missing_by_point[point],
            ),
        ):
            index = generator._next_undercovered_teleport_index(
                object(),
                ((10, 10), (20, 20), (30, 30)),
                start_index=0,
                world_path=object(),
                blank_coverage=object(),
            )

        self.assertEqual(index, 2)

        missing_by_point[(30, 30)] = 0
        with (
            mock.patch.object(generator, "_promoted_largest_targets", return_value=()),
            mock.patch.object(
                generator,
                "_teleport_point_missing_pixel_count",
                side_effect=lambda _config, point, _coverage: missing_by_point[point],
            ),
        ):
            index = generator._next_undercovered_teleport_index(
                object(),
                ((10, 10), (20, 20), (30, 30)),
                start_index=0,
                world_path=object(),
                blank_coverage=object(),
            )

        self.assertEqual(index, 1)

    def test_target_fix_apply_is_compatibility_noop(self) -> None:
        before_render_points = generator._render_area_teleport_points
        before_next_index = generator._next_undercovered_teleport_index

        worldgen_target_fix._APPLIED = False
        worldgen_target_fix.apply()

        self.assertTrue(worldgen_target_fix._APPLIED)
        self.assertIs(generator._render_area_teleport_points, before_render_points)
        self.assertIs(generator._next_undercovered_teleport_index, before_next_index)


if __name__ == "__main__":
    unittest.main()
