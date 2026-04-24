from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest.mock import patch

from worldgen import village_paths


@dataclass(frozen=True)
class FakeBlockInfo:
    name: str


class FakeSubchunk:
    chunk_x = 20
    chunk_z = 22
    min_y = 64

    def visible_block_info(self, local_x: int, local_y: int, local_z: int) -> FakeBlockInfo | None:
        if (local_x, local_y, local_z) == (7, 13, 2):
            return FakeBlockInfo("minecraft:grass_path")
        return None


class VillagePathSurfaceScanTests(unittest.TestCase):
    def test_dirt_path_names_include_bedrock_legacy_grass_path(self) -> None:
        self.assertTrue(village_paths._is_path_block("minecraft:grass_path"))
        self.assertTrue(village_paths._is_path_block("minecraft:dirt_path"))
        self.assertTrue(village_paths._is_path_block("minecraft:unknown_runtime_-410119178"))
        self.assertFalse(village_paths._is_path_block("minecraft:grass_block"))
        self.assertFalse(village_paths._is_path_block("minecraft:podzol"))

    def test_collect_surface_points_preserves_raw_path_block_name(self) -> None:
        surface_points: dict[tuple[int, int], village_paths.SurfacePoint] = {}

        village_paths._collect_surface_points(
            surface_points,
            FakeSubchunk(),
            min_x=327,
            max_x=327,
            min_z=354,
            max_z=354,
        )

        point = surface_points[(327, 354)]
        self.assertEqual(point.block_name, "minecraft:grass_path")
        self.assertTrue(village_paths._is_path_block(point.block_name))

    def test_preview_scan_is_centered_on_first_seed(self) -> None:
        scan = village_paths.SurfaceScan(
            mode_key="local_seed_surface",
            center=(327, 354),
            radius=village_paths.DEFAULT_SCAN_RADIUS,
            surface_points={},
        )
        preview = village_paths.DetectedVillagePreview(
            stop_var="P_TEST",
            node_coordinates=(),
            edges=(),
            bounds=(320, 335, 350, 365),
            pier_node_coordinates=frozenset(),
            snapped_seed_points=((327, 354),),
        )

        with (
            patch.object(village_paths, "load_surface_scan", return_value=scan) as load_surface_scan,
            patch.object(village_paths, "_path_points_from_scan", return_value={(327, 354)}),
            patch.object(village_paths, "_nearest_seed_path", return_value=(327, 354)),
            patch.object(village_paths, "_connected_path_component", return_value={(327, 354)}),
            patch.object(village_paths, "_build_preview_from_component", return_value=preview),
        ):
            result = village_paths.build_preview_from_seeds(
                stop_var="P_TEST",
                stop_coordinates=(715, 141),
                seed_points=[(327, 354), (330, 356)],
                render_payload={"render_style": "surface"},
                config=object(),  # type: ignore[arg-type]
            )

        self.assertIs(result, preview)
        self.assertEqual(load_surface_scan.call_args.kwargs["center"], (327, 354))

    def test_unknown_runtime_groups_prefer_seed_nearby_blocks(self) -> None:
        scan = village_paths.SurfaceScan(
            mode_key="local_seed_surface",
            center=(715, 141),
            radius=village_paths.DEFAULT_SCAN_RADIUS,
            surface_points={
                (500, 280): village_paths.SurfacePoint(500, 280, 64, "minecraft:unknown_runtime_-1"),
                (501, 280): village_paths.SurfacePoint(501, 280, 64, "minecraft:unknown_runtime_-1"),
                (715, 129): village_paths.SurfacePoint(715, 129, 64, "minecraft:unknown_runtime_-2"),
            },
        )

        groups = village_paths.unknown_runtime_block_groups(
            scan,
            focus_points=[(715, 141)],
            focus_radius=48,
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].block_name, "minecraft:unknown_runtime_-2")
        self.assertEqual(groups[0].coordinates, ((715, 129),))


if __name__ == "__main__":
    unittest.main()
