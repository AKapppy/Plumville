from __future__ import annotations

import unittest
from dataclasses import dataclass

import walking_suggestions


@dataclass(frozen=True)
class FakeStop:
    var: str
    x: int
    y: int
    is_connected: bool
    has_walking_paths: bool = False
    city_limit_node_keys: tuple[str, ...] = ()

    @property
    def coordinates(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def walking_coordinates(self) -> tuple[int, int]:
        return self.coordinates

    @property
    def station_entry_coordinates(self) -> tuple[int, int] | None:
        return None


@dataclass(frozen=True)
class FakeEndpoint:
    key: str
    coordinates: tuple[int, int] = (0, 0)
    display_label: str = ""


@dataclass(frozen=True)
class FakeWalkEdge:
    from_endpoint: FakeEndpoint
    to_endpoint: FakeEndpoint
    kind: str = "walk"
    id: str = "walk_edge"
    path_points: tuple[tuple[int, int], ...] = ((0, 5), (10, 5))
    label: str = "City Road"

class FakeBase:
    PATH_NODES = ()
    EXTRA_EDGES = ()
    METRO_STOPS = (
        FakeStop("CONNECTED", 0, 0, True),
        FakeStop("FRONTIER", 10, 0, False),
        FakeStop("BACKLOG", 20, 0, False),
    )

    @staticmethod
    def _frontier_highlight_stop_vars() -> frozenset[str]:
        return frozenset({"FRONTIER"})


class WalkingSuggestionScopeTests(unittest.TestCase):
    def test_village_anchor_keys_include_connected_and_frontier_only(self) -> None:
        anchors = walking_suggestions.village_anchor_keys(FakeBase)

        self.assertEqual(set(anchors), {"CONNECTED", "FRONTIER"})
        self.assertNotIn("BACKLOG", anchors)

    def test_network_signature_changes_when_connectivity_changes(self) -> None:
        class UpdatedBase(FakeBase):
            METRO_STOPS = (
                FakeStop("CONNECTED", 0, 0, True),
                FakeStop("FRONTIER", 10, 0, True),
                FakeStop("BACKLOG", 20, 0, False),
            )

        self.assertNotEqual(
            walking_suggestions._network_signature(FakeBase),
            walking_suggestions._network_signature(UpdatedBase),
        )

    def test_city_limit_anchor_uses_closest_point_on_walk_edge(self) -> None:
        city_stop = FakeStop(
            "CITY",
            5,
            2,
            True,
            has_walking_paths=True,
            city_limit_node_keys=("coord:0,0", "coord:10,0", "coord:10,10", "coord:0,10"),
        )
        city_edge = FakeWalkEdge(FakeEndpoint("coord:0,5"), FakeEndpoint("coord:10,5"))

        class CityBase(FakeBase):
            METRO_STOPS = (city_stop,)
            EXTRA_EDGES = (city_edge,)

            @staticmethod
            def _coordinate_endpoint_key(x: int, y: int) -> str:
                return f"coord:{x},{y}"

            @staticmethod
            def _display_label(label: str) -> str:
                return label

            @staticmethod
            def _city_limit_world_points(_stop: FakeStop) -> tuple[tuple[int, int], ...]:
                return ((0, 0), (10, 0), (10, 10), (0, 10))

            @staticmethod
            def _city_path_anchor_candidate_for_edge(
                _stop: FakeStop,
                _city_limit_points: tuple[tuple[int, int], ...],
                _edge: FakeWalkEdge,
            ) -> tuple[float, float, tuple[int, int]]:
                return (3.0, 5.0, (5, 5))

        anchors = walking_suggestions.village_anchors(CityBase)
        component_by_key = walking_suggestions._walk_component_index(CityBase, anchors.values())

        self.assertEqual(anchors["CITY"].key, "coord:5,5")
        self.assertEqual(anchors["CITY"].coordinates, (5, 5))
        self.assertEqual(
            component_by_key["coord:5,5"],
            component_by_key["coord:0,5"],
        )

    def test_walk_component_index_includes_connected_branch_beyond_anchor_edge(self) -> None:
        city_stop = FakeStop(
            "CITY",
            5,
            2,
            True,
            has_walking_paths=True,
            city_limit_node_keys=("coord:0,0", "coord:10,0", "coord:10,10", "coord:0,10"),
        )
        city_edge = FakeWalkEdge(
            FakeEndpoint("coord:0,5"),
            FakeEndpoint("coord:10,5"),
        )
        branch_edge = FakeWalkEdge(
            FakeEndpoint("coord:10,5"),
            FakeEndpoint("coord:20,5"),
            id="branch_edge",
            path_points=((10, 5), (20, 5)),
        )

        class CityBase(FakeBase):
            METRO_STOPS = (city_stop,)
            EXTRA_EDGES = (city_edge, branch_edge)

            @staticmethod
            def _coordinate_endpoint_key(x: int, y: int) -> str:
                return f"coord:{x},{y}"

            @staticmethod
            def _display_label(label: str) -> str:
                return label

            @staticmethod
            def _city_limit_world_points(_stop: FakeStop) -> tuple[tuple[int, int], ...]:
                return ((0, 0), (10, 0), (10, 10), (0, 10))

            @staticmethod
            def _city_path_anchor_candidate_for_edge(
                _stop: FakeStop,
                _city_limit_points: tuple[tuple[int, int], ...],
                _edge: FakeWalkEdge,
            ) -> tuple[float, float, tuple[int, int]]:
                return (3.0, 5.0, (5, 5))

        anchors = walking_suggestions.village_anchors(CityBase)
        component_by_key = walking_suggestions._walk_component_index(CityBase, anchors.values())

        self.assertEqual(
            component_by_key["coord:5,5"],
            component_by_key["coord:20,5"],
        )

    def test_build_suggested_segments_uses_preexisting_branch_endpoint(self) -> None:
        city_stop = FakeStop(
            "CITY",
            5,
            2,
            True,
            has_walking_paths=True,
            city_limit_node_keys=("coord:0,0", "coord:10,0", "coord:10,10", "coord:0,10"),
        )
        remote_stop = FakeStop("REMOTE", 28, 5, True)
        city_edge = FakeWalkEdge(
            FakeEndpoint("coord:0,5", (0, 5), "0,5"),
            FakeEndpoint("coord:10,5", (10, 5), "10,5"),
        )
        branch_edge = FakeWalkEdge(
            FakeEndpoint("coord:10,5", (10, 5), "10,5"),
            FakeEndpoint("coord:20,5", (20, 5), "20,5"),
            id="branch_edge",
            path_points=((10, 5), (20, 5)),
        )

        class SuggestionBase(FakeBase):
            METRO_STOPS = (city_stop, remote_stop)
            PATH_NODES = ()
            EXTRA_EDGES = (city_edge, branch_edge)

            @staticmethod
            def _coordinate_endpoint_key(x: int, y: int) -> str:
                return f"coord:{x},{y}"

            @staticmethod
            def _display_label(label: str) -> str:
                return label

            @staticmethod
            def _city_limit_world_points(_stop: FakeStop) -> tuple[tuple[int, int], ...]:
                return ((0, 0), (10, 0), (10, 10), (0, 10))

            @staticmethod
            def _city_path_anchor_candidate_for_edge(
                _stop: FakeStop,
                _city_limit_points: tuple[tuple[int, int], ...],
                _edge: FakeWalkEdge,
            ) -> tuple[float, float, tuple[int, int]]:
                return (3.0, 5.0, (5, 5))

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "coord:0,5": FakeEndpoint("coord:0,5", (0, 5), "0,5"),
                    "coord:5,5": FakeEndpoint("coord:5,5", (5, 5), "5,5"),
                    "coord:10,5": FakeEndpoint("coord:10,5", (10, 5), "10,5"),
                    "coord:20,5": FakeEndpoint("coord:20,5", (20, 5), "20,5"),
                    "REMOTE": FakeEndpoint("REMOTE", (28, 5), "Remote"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("fake-terrain",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                return (
                    abs(end_coordinates[0] - start_coordinates[0]),
                    (start_coordinates, end_coordinates),
                )

        original_terrain_from_viewer = walking_suggestions._terrain_from_viewer
        original_cache_key = walking_suggestions._CACHE_KEY
        original_cache_value = walking_suggestions._CACHE_VALUE
        try:
            walking_suggestions._terrain_from_viewer = lambda _viewer: FakeTerrain()
            walking_suggestions._CACHE_KEY = None
            walking_suggestions._CACHE_VALUE = ()

            segments = walking_suggestions.build_suggested_segments(SuggestionBase, viewer=object())
        finally:
            walking_suggestions._terrain_from_viewer = original_terrain_from_viewer
            walking_suggestions._CACHE_KEY = original_cache_key
            walking_suggestions._CACHE_VALUE = original_cache_value

        self.assertEqual(len(segments), 1)
        self.assertEqual({segments[0].start_key, segments[0].end_key}, {"coord:20,5", "REMOTE"})
        self.assertIn((20, 5), {segments[0].start_coordinates, segments[0].end_coordinates})


if __name__ == "__main__":
    unittest.main()
