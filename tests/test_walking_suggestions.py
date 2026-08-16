from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest import mock

from PIL import Image

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
    path_points: tuple[tuple[int, int], ...] = ()
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

    def test_build_suggested_segments_only_shows_primary_walking_frontier(self) -> None:
        alpha = FakeStop("ALPHA", 0, 0, True)
        beta = FakeStop("BETA", 10, 0, True)
        frontier = FakeStop("FRONTIER", 20, 0, True)
        deeper = FakeStop("DEEPER", 21, 0, True)
        edge = FakeWalkEdge(
            FakeEndpoint("ALPHA", (0, 0), "Alpha"),
            FakeEndpoint("BETA", (10, 0), "Beta"),
        )

        class SuggestionBase(FakeBase):
            METRO_STOPS = (alpha, beta, frontier, deeper)
            PATH_NODES = ()
            EXTRA_EDGES = (edge,)

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "ALPHA": FakeEndpoint("ALPHA", (0, 0), "Alpha"),
                    "BETA": FakeEndpoint("BETA", (10, 0), "Beta"),
                    "FRONTIER": FakeEndpoint("FRONTIER", (20, 0), "Frontier"),
                    "DEEPER": FakeEndpoint("DEEPER", (21, 0), "Deeper"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("frontier-only",)

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

        segment_pairs = {frozenset((segment.start_key, segment.end_key)) for segment in segments}
        self.assertIn(frozenset(("BETA", "FRONTIER")), segment_pairs)
        self.assertNotIn(frozenset(("FRONTIER", "DEEPER")), segment_pairs)

    def test_build_suggested_segments_keeps_one_direct_route_to_same_frontier(self) -> None:
        alpha = FakeStop("ALPHA", 0, 0, True)
        beta = FakeStop("BETA", 1, 0, True)
        frontier = FakeStop("FRONTIER", 10, 0, True)
        edge = FakeWalkEdge(
            FakeEndpoint("ALPHA", (0, 0), "Alpha"),
            FakeEndpoint("BETA", (1, 0), "Beta"),
        )

        class SuggestionBase(FakeBase):
            METRO_STOPS = (alpha, beta, frontier)
            PATH_NODES = ()
            EXTRA_EDGES = (edge,)

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "ALPHA": FakeEndpoint("ALPHA", (0, 0), "Alpha"),
                    "BETA": FakeEndpoint("BETA", (1, 0), "Beta"),
                    "FRONTIER": FakeEndpoint("FRONTIER", (10, 0), "Frontier"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("loop",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                route_cost = abs(end_coordinates[0] - start_coordinates[0])
                return (route_cost, (start_coordinates, end_coordinates))

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

        segment_pairs = {frozenset((segment.start_key, segment.end_key)) for segment in segments}
        self.assertEqual(
            segment_pairs,
            {
                frozenset(("BETA", "FRONTIER")),
            },
        )

    def test_build_suggested_segments_combines_close_alternate_routes(self) -> None:
        alpha = FakeStop("ALPHA", 0, 0, True)
        beta = FakeStop("BETA", 0, 10, True)
        frontier = FakeStop("FRONTIER", 10, 10, True)
        edge = FakeWalkEdge(
            FakeEndpoint("ALPHA", (0, 0), "Alpha"),
            FakeEndpoint("BETA", (0, 10), "Beta"),
            path_points=(),
        )

        class SuggestionBase(FakeBase):
            METRO_STOPS = (alpha, beta, frontier)
            PATH_NODES = ()
            EXTRA_EDGES = (edge,)

            @staticmethod
            def _coordinate_endpoint_key(x: int, y: int) -> str:
                return f"coord:{x},{y}"

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "ALPHA": FakeEndpoint("ALPHA", (0, 0), "Alpha"),
                    "BETA": FakeEndpoint("BETA", (0, 10), "Beta"),
                    "FRONTIER": FakeEndpoint("FRONTIER", (10, 10), "Frontier"),
                    "coord:5,5": FakeEndpoint("coord:5,5", (5, 5), "5,5"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("shared-trunk",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                paths = {
                    ((0, 0), (10, 10)): (10.0, ((0, 0), (5, 5), (10, 10))),
                    ((0, 10), (10, 10)): (11.0, ((0, 10), (5, 5), (10, 10))),
                }
                route = paths.get((start_coordinates, end_coordinates))
                if route is not None:
                    return route
                reverse_route = paths.get((end_coordinates, start_coordinates))
                if reverse_route is None:
                    return (100.0, (start_coordinates, end_coordinates))
                return (reverse_route[0], tuple(reversed(reverse_route[1])))

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

        segment_pairs = {frozenset((segment.start_key, segment.end_key)) for segment in segments}
        self.assertEqual(
            segment_pairs,
            {
                frozenset(("ALPHA", "coord:5,5")),
                frozenset(("BETA", "coord:5,5")),
                frozenset(("coord:5,5", "FRONTIER")),
            },
        )

    def test_build_suggested_segments_can_route_through_isolated_walk_segment(self) -> None:
        primary = FakeStop("PRIMARY", 0, 0, True)
        frontier = FakeStop("FRONTIER", 100, 0, True)
        isolated_edge = FakeWalkEdge(
            FakeEndpoint("coord:40,0", (40, 0), "40,0"),
            FakeEndpoint("coord:60,0", (60, 0), "60,0"),
            path_points=(),
        )

        class SuggestionBase(FakeBase):
            METRO_STOPS = (primary, frontier)
            PATH_NODES = ()
            EXTRA_EDGES = (isolated_edge,)

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "PRIMARY": FakeEndpoint("PRIMARY", (0, 0), "Primary"),
                    "FRONTIER": FakeEndpoint("FRONTIER", (100, 0), "Frontier"),
                    "coord:40,0": FakeEndpoint("coord:40,0", (40, 0), "40,0"),
                    "coord:60,0": FakeEndpoint("coord:60,0", (60, 0), "60,0"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("isolated-segment",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                coordinate_pair = {start_coordinates, end_coordinates}
                if coordinate_pair == {(0, 0), (100, 0)}:
                    return (100.0, (start_coordinates, end_coordinates))
                if coordinate_pair in ({(0, 0), (40, 0)}, {(60, 0), (100, 0)}):
                    return (10.0, (start_coordinates, end_coordinates))
                return (80.0, (start_coordinates, end_coordinates))

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

        segment_pairs = {frozenset((segment.start_key, segment.end_key)) for segment in segments}
        self.assertEqual(
            segment_pairs,
            {
                frozenset(("PRIMARY", "coord:40,0")),
                frozenset(("coord:60,0", "FRONTIER")),
            },
        )

    def test_build_suggested_segments_can_connect_to_middle_of_existing_path(self) -> None:
        primary = FakeStop("PRIMARY", 0, 0, True)
        branch = FakeStop("BRANCH", 20, 0, True)
        frontier = FakeStop("FRONTIER", 10, 30, True)
        existing_edge = FakeWalkEdge(
            FakeEndpoint("PRIMARY", (0, 0), "Primary"),
            FakeEndpoint("BRANCH", (20, 0), "Branch"),
            path_points=((0, 0), (10, 0), (20, 0)),
        )

        class SuggestionBase(FakeBase):
            METRO_STOPS = (primary, branch, frontier)
            PATH_NODES = ()
            EXTRA_EDGES = (existing_edge,)

            @staticmethod
            def _coordinate_endpoint_key(x: int, y: int) -> str:
                return f"coord:{x},{y}"

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "PRIMARY": FakeEndpoint("PRIMARY", (0, 0), "Primary"),
                    "BRANCH": FakeEndpoint("BRANCH", (20, 0), "Branch"),
                    "FRONTIER": FakeEndpoint("FRONTIER", (10, 30), "Frontier"),
                    "coord:10,0": FakeEndpoint("coord:10,0", (10, 0), "10,0"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("middle-connect",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                coordinate_pair = {start_coordinates, end_coordinates}
                route_cost = 1.0 if coordinate_pair == {(10, 0), (10, 30)} else 50.0
                return (route_cost, (start_coordinates, end_coordinates))

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
        self.assertIn("coord:10,0", {segments[0].start_key, segments[0].end_key})

    def test_build_suggested_segments_branches_from_walk_ready_middle_village(self) -> None:
        primary = FakeStop("A_PRIMARY", 0, 0, True, has_walking_paths=True)
        middle = FakeStop("B_MIDDLE", 10, 0, True, has_walking_paths=True)
        far = FakeStop("C_FAR", 20, 0, True)

        class SuggestionBase(FakeBase):
            METRO_STOPS = (primary, middle, far)
            PATH_NODES = ()
            EXTRA_EDGES = ()

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "A_PRIMARY": FakeEndpoint("A_PRIMARY", (0, 0), "Primary"),
                    "B_MIDDLE": FakeEndpoint("B_MIDDLE", (10, 0), "Middle"),
                    "C_FAR": FakeEndpoint("C_FAR", (20, 0), "Far"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("middle-village",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                costs = {
                    frozenset(((0, 0), (10, 0))): 10.0,
                    frozenset(((10, 0), (20, 0))): 10.0,
                    frozenset(((0, 0), (20, 0))): 15.0,
                }
                return (
                    costs[frozenset((start_coordinates, end_coordinates))],
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

        segment_pairs = {frozenset((segment.start_key, segment.end_key)) for segment in segments}
        self.assertEqual(
            segment_pairs,
            {
                frozenset(("A_PRIMARY", "B_MIDDLE")),
                frozenset(("B_MIDDLE", "C_FAR")),
            },
        )
        self.assertNotIn(frozenset(("A_PRIMARY", "C_FAR")), segment_pairs)

    def test_build_suggested_segments_keeps_non_walk_ready_middle_as_leaf(self) -> None:
        primary = FakeStop("A_PRIMARY", 0, 0, True, has_walking_paths=True)
        middle = FakeStop("B_MIDDLE", 10, 0, True)
        far = FakeStop("C_FAR", 20, 0, True)

        class SuggestionBase(FakeBase):
            METRO_STOPS = (primary, middle, far)
            PATH_NODES = ()
            EXTRA_EDGES = ()

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "A_PRIMARY": FakeEndpoint("A_PRIMARY", (0, 0), "Primary"),
                    "B_MIDDLE": FakeEndpoint("B_MIDDLE", (10, 0), "Middle"),
                    "C_FAR": FakeEndpoint("C_FAR", (20, 0), "Far"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("middle-leaf",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                costs = {
                    frozenset(((0, 0), (10, 0))): 10.0,
                    frozenset(((10, 0), (20, 0))): 1.0,
                    frozenset(((0, 0), (20, 0))): 15.0,
                }
                return (
                    costs[frozenset((start_coordinates, end_coordinates))],
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

        segment_pairs = {frozenset((segment.start_key, segment.end_key)) for segment in segments}
        self.assertEqual(
            segment_pairs,
            {
                frozenset(("A_PRIMARY", "B_MIDDLE")),
                frozenset(("A_PRIMARY", "C_FAR")),
            },
        )

    def test_build_suggested_segments_splits_shared_outgoing_stems(self) -> None:
        primary = FakeStop("A_PRIMARY", 0, 0, True, has_walking_paths=True)
        first = FakeStop("FIRST", 10, 10, True)
        second = FakeStop("SECOND", 10, 0, True)

        class SuggestionBase(FakeBase):
            METRO_STOPS = (primary, first, second)
            PATH_NODES = ()
            EXTRA_EDGES = ()

            @staticmethod
            def _coordinate_endpoint_key(x: int, y: int) -> str:
                return f"coord:{x},{y}"

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "A_PRIMARY": FakeEndpoint("A_PRIMARY", (0, 0), "Primary"),
                    "FIRST": FakeEndpoint("FIRST", (10, 10), "First"),
                    "SECOND": FakeEndpoint("SECOND", (10, 0), "Second"),
                    "coord:5,5": FakeEndpoint("coord:5,5", (5, 5), "5,5"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("shared-stem",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                paths = {
                    ((0, 0), (10, 10)): (10.0, ((0, 0), (5, 5), (10, 10))),
                    ((0, 0), (10, 0)): (11.0, ((0, 0), (5, 5), (10, 0))),
                    ((10, 10), (10, 0)): (100.0, ((10, 10), (10, 0))),
                }
                route = paths.get((start_coordinates, end_coordinates))
                if route is not None:
                    return route
                reverse_route = paths.get((end_coordinates, start_coordinates))
                if reverse_route is None:
                    return None
                return (reverse_route[0], tuple(reversed(reverse_route[1])))

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

        segment_pairs = {frozenset((segment.start_key, segment.end_key)) for segment in segments}
        self.assertEqual(
            segment_pairs,
            {
                frozenset(("A_PRIMARY", "coord:5,5")),
                frozenset(("coord:5,5", "FIRST")),
                frozenset(("coord:5,5", "SECOND")),
            },
        )

    def test_close_coordinate_branch_points_are_canonicalized(self) -> None:
        class CoordinateBase:
            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                if not endpoint_key.startswith("coord:"):
                    return None
                point_x_text, point_y_text = endpoint_key.removeprefix("coord:").split(",", 1)
                coordinates = (int(point_x_text), int(point_y_text))
                return FakeEndpoint(endpoint_key, coordinates, endpoint_key)

        candidates = (
            walking_suggestions._RouteCandidate(
                cost=10.0,
                first_key="coord:0,0",
                second_key="coord:100,100",
                first_component=0,
                second_component=1,
                path_coordinates=((0, 0), (100, 100)),
            ),
            walking_suggestions._RouteCandidate(
                cost=20.0,
                first_key="coord:105,102",
                second_key="coord:300,100",
                first_component=1,
                second_component=2,
                path_coordinates=((105, 102), (300, 100)),
            ),
            walking_suggestions._RouteCandidate(
                cost=25.0,
                first_key="coord:105,102",
                second_key="coord:300,200",
                first_component=1,
                second_component=3,
                path_coordinates=((105, 102), (300, 200)),
            ),
        )

        rewritten = walking_suggestions._canonicalize_close_virtual_endpoints(
            CoordinateBase,
            candidates,
            {"coord:0,0", "coord:100,100", "coord:300,100", "coord:300,200"},
        )

        endpoint_pairs = {frozenset((candidate.first_key, candidate.second_key)) for candidate in rewritten}
        self.assertEqual(
            endpoint_pairs,
            {
                frozenset(("coord:0,0", "coord:100,100")),
                frozenset(("coord:100,100", "coord:300,100")),
                frozenset(("coord:100,100", "coord:300,200")),
            },
        )
        self.assertNotIn(
            "coord:105,102",
            {candidate.first_key for candidate in rewritten}
            | {candidate.second_key for candidate in rewritten},
        )

    def test_build_suggested_segments_splits_rational_slope_segments(self) -> None:
        primary = FakeStop("PRIMARY", 0, 0, True)
        frontier = FakeStop("FRONTIER", 7, 3, True)

        class SuggestionBase(FakeBase):
            METRO_STOPS = (primary, frontier)
            PATH_NODES = ()
            EXTRA_EDGES = ()

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "PRIMARY": FakeEndpoint("PRIMARY", (0, 0), "Primary"),
                    "FRONTIER": FakeEndpoint("FRONTIER", (7, 3), "Frontier"),
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("rational-slope",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                return (10.0, (start_coordinates, end_coordinates))

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
        self.assertEqual(len(segments[0].path_coordinates), 3)
        self.assertEqual(
            {segments[0].path_coordinates[0], segments[0].path_coordinates[-1]},
            {(0, 0), (7, 3)},
        )
        for first_point, second_point in zip(
            segments[0].path_coordinates,
            segments[0].path_coordinates[1:],
        ):
            self.assertTrue(
                walking_suggestions._has_minecraft_buildable_slope(first_point, second_point)
            )

    def test_build_suggested_segments_keeps_integer_slope_segments(self) -> None:
        self.assertEqual(
            walking_suggestions._minecraft_buildable_path(((0, 0), (3, 6))),
            ((0, 0), (3, 6)),
        )
        self.assertEqual(
            walking_suggestions._minecraft_buildable_path(((0, 0), (6, 3))),
            ((0, 0), (6, 3)),
        )

    def test_direct_frontier_refinement_can_choose_longer_endpoint_search(self) -> None:
        primary = FakeStop("PRIMARY", 0, 0, True)
        frontier = FakeStop("FRONTIER", 100, 0, True)
        extra_endpoints = tuple(
            FakeEndpoint(f"coord:{index},0", (index, 0), str(index))
            for index in range(1, 10)
        )
        edges = (
            FakeWalkEdge(
                FakeEndpoint("PRIMARY", (0, 0), "Primary"),
                extra_endpoints[0],
                id="edge_1",
                path_points=((0, 0), extra_endpoints[0].coordinates),
            ),
            *(
                FakeWalkEdge(
                    extra_endpoints[index - 1],
                    extra_endpoints[index],
                    id=f"edge_{index + 1}",
                    path_points=(extra_endpoints[index - 1].coordinates, extra_endpoints[index].coordinates),
                )
                for index in range(1, len(extra_endpoints))
            ),
        )

        class SuggestionBase(FakeBase):
            METRO_STOPS = (primary, frontier)
            PATH_NODES = ()
            EXTRA_EDGES = edges

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "PRIMARY": FakeEndpoint("PRIMARY", (0, 0), "Primary"),
                    "FRONTIER": FakeEndpoint("FRONTIER", (100, 0), "Frontier"),
                    **{endpoint.key: endpoint for endpoint in extra_endpoints},
                }
                return endpoints.get(endpoint_key)

        class FakeTerrain:
            signature = ("refined",)

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                route_cost = 1.0 if (9, 0) in {start_coordinates, end_coordinates} else 100.0
                return (route_cost, (start_coordinates, end_coordinates))

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
        self.assertIn("coord:9,0", {segments[0].start_key, segments[0].end_key})

    def test_cached_suggestions_skip_second_terrain_grid_build(self) -> None:
        alpha = FakeStop("ALPHA", 0, 0, True)
        beta = FakeStop("BETA", 20, 0, True)

        class SuggestionBase(FakeBase):
            METRO_STOPS = (alpha, beta)
            PATH_NODES = ()
            EXTRA_EDGES = ()

            @staticmethod
            def _path_endpoint_from_key(endpoint_key: str) -> FakeEndpoint | None:
                endpoints = {
                    "ALPHA": FakeEndpoint("ALPHA", (0, 0), "Alpha"),
                    "BETA": FakeEndpoint("BETA", (20, 0), "Beta"),
                }
                return endpoints.get(endpoint_key)

        image = Image.new("RGBA", (32, 32), (80, 160, 80, 255))
        payload = {
            "min_x": 0,
            "max_x": 32,
            "min_z": 0,
            "max_z": 32,
        }

        class FakeViewer:
            @staticmethod
            def _current_world_map_render_underlay() -> tuple[
                dict[str, int],
                Image.Image,
            ]:
                return (payload, image)

        terrain_builds = 0

        class FakeTerrainGrid:
            def __init__(self, **_kwargs: object) -> None:
                nonlocal terrain_builds
                terrain_builds += 1

            @staticmethod
            def find_path(
                start_coordinates: tuple[int, int],
                end_coordinates: tuple[int, int],
            ) -> tuple[float, tuple[tuple[int, int], ...]] | None:
                return (
                    abs(end_coordinates[0] - start_coordinates[0]),
                    (start_coordinates, end_coordinates),
                )

        original_cache_key = walking_suggestions._CACHE_KEY
        original_cache_value = walking_suggestions._CACHE_VALUE
        try:
            walking_suggestions._CACHE_KEY = None
            walking_suggestions._CACHE_VALUE = ()
            with mock.patch.object(
                walking_suggestions,
                "TerrainGrid",
                FakeTerrainGrid,
            ):
                first_segments = walking_suggestions.build_suggested_segments(
                    SuggestionBase,
                    viewer=FakeViewer(),
                )
                second_segments = walking_suggestions.build_suggested_segments(
                    SuggestionBase,
                    viewer=FakeViewer(),
                )
        finally:
            walking_suggestions._CACHE_KEY = original_cache_key
            walking_suggestions._CACHE_VALUE = original_cache_value

        self.assertEqual(terrain_builds, 1)
        self.assertEqual(first_segments, second_segments)


if __name__ == "__main__":
    unittest.main()
