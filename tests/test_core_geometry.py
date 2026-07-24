from __future__ import annotations

import unittest

import legacy_core as base
from plumville.core import geometry


class CoreGeometryTests(unittest.TestCase):
    def test_polyline_distances_match_legacy_wrappers(self) -> None:
        points = ((0, 0), (3, 4), (6, 8))

        self.assertEqual(geometry.polyline_distance(points), 10)
        self.assertEqual(base._polyline_distance(points), geometry.polyline_distance(points))
        self.assertEqual(geometry.polyline_distance_float(points), 10.0)
        self.assertEqual(base._polyline_distance_float(points), geometry.polyline_distance_float(points))

    def test_point_to_segment_distance_handles_projection_and_degenerate_segments(self) -> None:
        self.assertEqual(
            geometry.point_to_segment_distance_sq((5.0, 3.0), (0.0, 0.0), (10.0, 0.0)),
            9.0,
        )
        self.assertEqual(
            geometry.point_to_segment_distance_sq((3.0, 4.0), (0.0, 0.0), (0.0, 0.0)),
            25.0,
        )

    def test_point_to_polyline_distance(self) -> None:
        points = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0))

        self.assertEqual(geometry.point_to_polyline_distance_sq((6.0, 2.0), points), 4.0)
        self.assertIsNone(geometry.point_to_polyline_distance_sq((6.0, 2.0), ((0.0, 0.0),)))
        self.assertEqual(
            base._point_to_polyline_distance_sq((6.0, 2.0), points),
            geometry.point_to_polyline_distance_sq((6.0, 2.0), points),
        )

    def test_polyline_midpoint(self) -> None:
        self.assertEqual(geometry.polyline_midpoint(()), (0.0, 0.0))
        self.assertEqual(geometry.polyline_midpoint(((3.0, 4.0),)), (3.0, 4.0))
        self.assertEqual(geometry.polyline_midpoint(((0.0, 0.0), (10.0, 0.0))), (5.0, 0.0))
        self.assertEqual(
            geometry.polyline_midpoint(((0.0, 0.0), (10.0, 0.0), (10.0, 10.0))),
            (10.0, 0.0),
        )
        self.assertEqual(
            base._polyline_midpoint(((0.0, 0.0), (10.0, 0.0))),
            geometry.polyline_midpoint(((0.0, 0.0), (10.0, 0.0))),
        )

    def test_cumulative_distances(self) -> None:
        self.assertEqual(
            geometry.cumulative_distances(((0.0, 0.0), (3.0, 4.0), (6.0, 8.0))),
            (0.0, 5.0, 10.0),
        )


if __name__ == "__main__":
    unittest.main()
