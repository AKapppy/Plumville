from __future__ import annotations

import base64
import csv
import heapq
import html
import io
import json
import queue
import re
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from math import ceil, dist, floor, log
from pathlib import Path
from typing import Any, Callable, ClassVar, Final, Iterable, Literal, NotRequired, Sequence, TypedDict, cast

from PIL import Image, ImageDraw, ImageTk

Image.MAX_IMAGE_PIXELS = None


BLACKPORT_LBL: Final[str] = 'Blackport'
BLACKPORT_VAR: Final[str] = 'P_ABCDE'
COORDINATE_ENDPOINT_PREFIX: Final[str] = 'coord:'
CITY_LIMIT_ENDPOINT_PREFIX: Final[str] = 'city:'
COORDINATE_NODE_CONTEXT: Final[str] = '__coord__'
STATION_CITY_PATH_CONTEXT: Final[str] = '__station_city_path__'
METRO_NETWORK_PATH: Final[Path] = Path(__file__).with_name('docs') / 'metro_network.json'
METRO_NETWORK_BACKUP_PATH: Final[Path] = Path(__file__).with_name('metro_network.last.json')
METRO_NETWORK_HISTORY_DIR: Final[Path] = Path(__file__).with_name('metro_network.history')
PRIORITY_LIST_CSV_PATH: Final[Path] = Path(__file__).with_name('priority_list.csv')
EXPORTS_DIR: Final[Path] = Path(__file__).with_name('exports')
PLOT_WIDTH: Final[int] = 1600
PLOT_HEIGHT: Final[int] = 1000
PLOT_PADDING: Final[int] = 80
BACKGROUND_COLOR: Final[str] = '#050505'
TEXT_COLOR: Final[str] = '#f7f7f7'
GRID_COLOR: Final[str] = '#4b4b4b'
INTERSECTION_COLOR: Final[str] = '#ffffff'
UNASSOCIATED_STATION_LABEL: Final[str] = 'Unassociated station'
UNASSOCIATED_STATION_FILL: Final[str] = '#050505'
UNASSOCIATED_STATION_OUTLINE: Final[str] = '#ffffff'
DEFAULT_ZOOM: Final[float] = 1.0
MAX_VISIBLE_BLOCKS_AT_MAX_ZOOM: Final[float] = 10.0
ZOOM_STEP: Final[float] = 1.7
FRONTIER_LABEL_SIZE_BOOST: Final[int] = 6
LABEL_ANGLE: Final[float] = 30.0
BASE_LABEL_FONT_SIZE: Final[int] = 13
MAX_LABEL_FONT_GROWTH: Final[int] = 14
LABEL_FONT_GROWTH_PER_ZOOM_STEP: Final[float] = 0.3
LABEL_OFFSET_X: Final[int] = 7
LABEL_OFFSET_Y: Final[int] = 7
STATION_RADIUS: Final[int] = 4
STATION_CLICK_TOLERANCE: Final[int] = 10
PATH_NODE_RADIUS: Final[int] = 5
PATH_NODE_CLICK_TOLERANCE: Final[int] = 10
PATH_NODE_FILL: Final[str] = '#0d1620'
PATH_NODE_OUTLINE: Final[str] = '#8ad4ff'
PATH_NODE_LABEL_COLOR: Final[str] = '#c8ebff'
PATH_EDIT_HANDLE_RADIUS: Final[int] = 5
PATH_EDIT_HANDLE_TOLERANCE: Final[int] = 10
PATH_EDIT_ACTIVE_OUTLINE_WIDTH: Final[int] = 9
PATH_EDIT_ACTIVE_WIDTH: Final[int] = 4
SELECTED_PATH_NODE_RADIUS: Final[int] = 9
CITY_LIMIT_FILL: Final[str] = '#f3d66b'
CITY_LIMIT_OUTLINE: Final[str] = '#ffe8a3'
CITY_LIMIT_ACTIVE_FILL: Final[str] = '#8ad4ff'
CITY_LIMIT_ACTIVE_OUTLINE: Final[str] = '#d8f3ff'
CITY_LIMIT_WIDTH: Final[int] = 2
CITY_LIMIT_DASH: Final[tuple[int, int]] = (8, 4)
LINE_CLICK_TOLERANCE: Final[int] = 8
DRAG_THRESHOLD: Final[int] = 4
INFO_BOX_BACKGROUND: Final[str] = '#111111'
INFO_BOX_BORDER: Final[str] = '#2d2d2d'
INFO_BOX_OFFSET_X: Final[int] = 14
INFO_BOX_OFFSET_Y: Final[int] = 14
INFO_TITLE_FONT_SIZE: Final[int] = 24
INFO_TEXT_FONT_SIZE: Final[int] = 12
INFO_BUTTON_FONT_SIZE: Final[int] = 11
INFO_BUTTON_BACKGROUND: Final[str] = '#181818'
INFO_BUTTON_ACTIVE_BACKGROUND: Final[str] = '#2a2a2a'
INFO_BOX_PAD_X: Final[int] = 10
INFO_BOX_PAD_Y: Final[int] = 9
INFO_BOX_SECTION_GAP: Final[int] = 7
INFO_BUTTON_PAD_X: Final[int] = 10
INFO_BUTTON_PAD_Y: Final[int] = 5
INFO_CHECKBOX_TEXT_COLOR: Final[str] = '#8f8f8f'
COMPLETE_HULL_FILL: Final[str] = '#101010'
COMPLETE_HULL_OUTLINE: Final[str] = '#6e6e6e'
COMPLETE_ROUTE_OUTLINE_WIDTH: Final[int] = 24
AREA_OVERLAY_RGBA: Final[tuple[int, int, int, int]] = (176, 84, 132, 74)
CIRCLE_OVERLAY_RGBA: Final[tuple[int, int, int, int]] = (104, 32, 68, 86)
ALIGNMENT_REMINDER_OUTLINE: Final[str] = '#d8d8d8'
ALIGNMENT_REMINDER_WIDTH: Final[int] = 2
ALIGNMENT_REMINDER_PADDING: Final[int] = 16
ALIGNMENT_REMINDER_MIN_SIZE: Final[int] = 30
ALIGNMENT_REMINDER_LABEL_FONT_SIZE: Final[int] = 10
FRONTIER_HIGHLIGHT_OUTLINE: Final[str] = '#ffd6e6'
FRONTIER_HIGHLIGHT_WIDTH: Final[int] = 3
FRONTIER_HIGHLIGHT_RADIUS: Final[int] = 10
FRONTIER_SEGMENT_OUTLINE_WIDTH: Final[int] = 12
FRONTIER_SEGMENT_WIDTH: Final[int] = 8
CONNECTOR_ROUTE_COLOR: Final[str] = '#f0f0f0'
WALK_ROUTE_COLOR: Final[str] = '#f7c7db'
FLY_ROUTE_COLOR: Final[str] = '#8ad4ff'
CURSOR_GUIDE_COLOR: Final[str] = '#8ad4ff'
CURSOR_GUIDE_WIDTH: Final[int] = 1
CURSOR_GUIDE_DASH: Final[tuple[int, int]] = (6, 4)
CURSOR_CROSSHAIR_RADIUS: Final[int] = 7
CURSOR_INFO_MARGIN: Final[int] = 14
CURSOR_INFO_PAD_X: Final[int] = 8
CURSOR_INFO_PAD_Y: Final[int] = 5
CURSOR_INFO_FONT_SIZE: Final[int] = 12
CURSOR_INFO_BACKGROUND: Final[str] = '#0f1820'
CURSOR_INFO_BORDER: Final[str] = '#395a70'
PRIORITY_FILTER_ALL_LABEL: Final[str] = 'All needs'
PRIORITY_HIGHLIGHT_COLOR: Final[str] = '#ffffff'
PRIORITY_HIGHLIGHT_SOFT_COLOR: Final[str] = '#d8f3ff'
BLACKPORT_VIEW_RADIUS: Final[int] = 2000
WORLD_MAP_RENDER_ALPHA: Final[int] = 190
WORLD_MAP_RENDER_BOUNDS_COLOR: Final[str] = '#f3d66b'
WORLD_MAP_RENDER_BOUNDS_WIDTH: Final[int] = 2
WORLD_MAP_RENDER_BOUNDS_DASH: Final[tuple[int, int]] = (6, 4)
WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE: Final[int] = 24
WORLD_MAP_ACTIVE_TARGET_COLOR: Final[str] = '#8ad4ff'
WORLD_MAP_ACTIVE_TARGET_WIDTH: Final[int] = 2
WORLD_MAP_ACTIVE_TARGET_DASH: Final[tuple[int, int]] = (10, 5)
WORLD_MAP_ACTIVE_TARGET_MIN_CANVAS_SIZE: Final[int] = 24
WORLD_MAP_AUTO_LOAD_PASSES: Final[int] = 1
WORLD_MAP_RENDER_PROGRESS_PIXEL_INTERVAL: Final[int] = 5_000
WORLD_MAP_PREVIEW_MAX_DIMENSION: Final[int] = 4096
WORLD_MAP_PREVIEW_SUFFIX: Final[str] = '.app-preview.png'
WORLD_MAP_FILE_POLL_MIN_SECONDS: Final[float] = 0.75
WORLD_MAP_SPIRAL_CHECK_COLOR: Final[str] = '#ff8ad8'
WORLD_MAP_SPIRAL_CHECK_WIDTH: Final[int] = 2
WORLD_MAP_SPIRAL_CHECK_DASH: Final[tuple[int, int]] = (8, 4)
WORLD_MAP_SPIRAL_BLANK_COLOR: Final[str] = '#ffffff'
WORLD_MAP_SPIRAL_BLANK_MIN_CANVAS_SIZE: Final[int] = 18
SIDEBAR_SCROLL_PIXELS: Final[int] = 36
SIDEBAR_SCROLL_FRAMES: Final[int] = 3
SIDEBAR_SCROLL_FRAME_DELAY_MS: Final[int] = 8
MINECART_SPEED_MPS: Final[float] = 8.0
VIEWPORT_REDRAW_BATCH_DELAY_MS: Final[int] = 16
VIEWPORT_INTERACTION_FULL_REDRAW_DELAY_MS: Final[int] = 240
TARGET_MAP_VIEW_MARGIN_PIXELS: Final[int] = 24
SIDEBAR_WIDTH: Final[int] = 340
SIDEBAR_TITLE_FONT_SIZE: Final[int] = 20
SIDEBAR_TEXT_FONT_SIZE: Final[int] = 12
SIDEBAR_INPUT_BACKGROUND: Final[str] = '#050505'
SIDEBAR_INPUT_ACTIVE_BACKGROUND: Final[str] = '#111111'
SIDEBAR_INPUT_BORDER: Final[str] = '#202020'
ROUTE_HIGHLIGHT_OUTLINE: Final[str] = '#ffffff'
ROUTE_HIGHLIGHT_OUTLINE_WIDTH: Final[int] = 10
ROUTE_HIGHLIGHT_WIDTH: Final[int] = 6
SELECTED_SEGMENT_OUTLINE_WIDTH: Final[int] = 12
SELECTED_SEGMENT_WIDTH: Final[int] = 7
LABEL_CASING_COLOR: Final[str] = '#f2efe6'
LABEL_CASING_WIDTH: Final[int] = 2
JUNCTION_LABEL_COLOR: Final[str] = '#050505'
FINISHED_RAILWAY_MAJOR_LINES: Final[frozenset[str]] = frozenset(('A', 'B', 'C', 'D', 'E'))
SHOW_RAILWAY_FINISHING_UI: Final[bool] = False
FINISHED_RAILWAY_COORDINATE_TOLERANCE: Final[float] = 0.01
FINISHED_RAILWAY_HIGHLIGHT_OUTLINE: Final[str] = '#ffffff'
FINISHED_RAILWAY_HIGHLIGHT_OUTLINE_WIDTH: Final[int] = 14
FINISHED_RAILWAY_HIGHLIGHT_WIDTH: Final[int] = 9
UNCONNECTED_RAILWAY_DASH: Final[tuple[int, int]] = (10, 6)
UNCONNECTED_RAILWAY_WIDTH: Final[int] = 3
CONNECTED_TASK_WEIGHTS: Final[dict[str, int]] = {
    'name': 1,
    'façade': 3,
    'station': 6,
    'station entrance': 2,
    'paths': 3,
    'city limits': 2,
    'alignment': 2,
    'finished railway': 4,
    'signs': 2,
    'chimes': 2,
}
PRIORITY_NEED_LABELS: Final[dict[str, str]] = {
    'name': 'Names',
    'façade': 'Façades',
    'station': 'Stations',
    'station entrance': 'Station Entrances',
    'paths': 'Walking Paths',
    'city limits': 'City Limits',
    'alignment': 'Align to Other Station(s)',
    'finished railway': 'Finished Railway',
    'signs': 'Signs',
    'chimes': 'Chimes',
}
PRIORITY_CSV_CHECKLIST_COLUMNS: Final[tuple[tuple[str, str], ...]] = (
    ('Named', 'name'),
    ('Facade', 'façade'),
    ('Station', 'station'),
    ('Station Entrance', 'station entrance'),
    ('Walking Paths', 'paths'),
    ('City Limits', 'city limits'),
    ('Connected', 'connected'),
    ('Aligned', 'alignment'),
    ('Finished Railway', 'finished railway'),
    ('Signs', 'signs'),
    ('Chimes', 'chimes'),
)
PRIORITY_TASK_PHRASES: Final[dict[str, str]] = {
    'alignment': 'align to other station(s)',
}
ALIGNMENT_PRIORITY_PENALTY: Final[int] = 2
PRIORITY_NAME_WEIGHT: Final[int] = 1
PRIORITY_JUNCTION_WEIGHT: Final[int] = 2
PRIORITY_DISTANCE_WEIGHT: Final[int] = 3
PRIORITY_STATION_WEIGHT: Final[int] = 4
SUBSCRIPT_TRANSLATION: Final[dict[int, int]] = str.maketrans('0123456789-', '₀₁₂₃₄₅₆₇₈₉₋')
MAX_HISTORY_SNAPSHOTS: Final[int] = 100


ChimeDirection = Literal['north', 'east', 'south', 'west']
CHIME_DIRECTIONS: Final[tuple[ChimeDirection, ...]] = ('north', 'east', 'south', 'west')
CHIME_DIRECTION_LABELS: Final[dict[ChimeDirection, str]] = {
    'north': 'North',
    'east': 'East',
    'south': 'South',
    'west': 'West',
}
WorldMapTaskQueueItem = tuple[
    Literal['progress', 'rendered', 'done'],
    bool,
    str,
]
WorldMapPreviewQueueItem = tuple[bool, str, str]
FileStatKey = tuple[str, int, int]


class StopRecord(TypedDict):
    var: str
    lbl: str
    x: int
    y: int
    has_connector: bool
    has_full_station: bool
    has_walking_paths: bool
    is_connected: bool
    has_finished_railway: bool
    has_signs: bool
    chime_directions: list[ChimeDirection]
    station_entry_x: NotRequired[int]
    station_entry_y: NotRequired[int]
    city_limit_node_keys: NotRequired[list[str]]


class LinePathSpecRecord(TypedDict):
    x_var: str
    y_var: str
    dx: int
    dy: int


class StopPathEndpointRecord(TypedDict):
    kind: Literal['stop']
    stop_var: str


class CoordPathEndpointRecord(TypedDict):
    kind: Literal['coord']
    x: int
    y: int


PathEndpointRecord = StopPathEndpointRecord | CoordPathEndpointRecord


class PathPointRecord(TypedDict):
    x: int
    y: int


class PathNodeRecord(TypedDict):
    id: str
    x: int
    y: int
    label: NotRequired[str]
    poi_kind: NotRequired[str]
    category: NotRequired[str]


class AlignmentReminderRecord(TypedDict):
    first_var: str
    second_var: str
    axis: str


class ExtraEdgeRecord(TypedDict):
    id: str
    kind: str
    bidirectional: bool
    from_endpoint: NotRequired[PathEndpointRecord]
    to_endpoint: NotRequired[PathEndpointRecord]
    path_points: NotRequired[list[PathPointRecord]]
    from_var: NotRequired[str]
    to_var: NotRequired[str]
    path_specs: NotRequired[list[LinePathSpecRecord]]
    label: NotRequired[str]
    distance: NotRequired[int]


def _file_stat_key(path: Path) -> FileStatKey | None:
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return (str(path), stat_result.st_mtime_ns, stat_result.st_size)


class MetroNetworkPayload(TypedDict):
    stops: list[StopRecord]
    line_colors: dict[str, str]
    wool_colors: NotRequired[dict[str, str]]
    line_stop_vars: dict[str, list[str]]
    line_path_specs: dict[str, list[LinePathSpecRecord]]
    path_nodes: list[PathNodeRecord]
    extra_edges: list[ExtraEdgeRecord]
    alignment_reminders: list[AlignmentReminderRecord]
    railway_finish_progress: NotRequired[dict[str, PathPointRecord]]
    railway_finish_origins: NotRequired[dict[str, str]]


CheckpointField = Literal[
    'has_connector',
    'has_full_station',
    'has_walking_paths',
    'is_connected',
    'has_finished_railway',
    'has_signs',
]
CHECKPOINT_FIELDS: Final[tuple[CheckpointField, ...]] = (
    'has_connector',
    'has_full_station',
    'has_walking_paths',
    'is_connected',
    'has_finished_railway',
    'has_signs',
)
AlignmentAxis = Literal['x', 'y']
AlignmentAxisInput = Literal['x', 'y', 'auto']
RouteNode = tuple[str, str]
RouteKind = Literal['ride', 'transfer', 'connector', 'walk', 'fly']
ExtraEdgeKind = Literal['connector', 'walk']
PathEndpointKind = Literal['stop', 'coord', 'city_limit']
MetroSegmentShape = Literal['direct', 'turn', 'custom']


@dataclass(frozen=True, slots=True)
class MetroStop:
    var: str
    lbl: str
    x: int
    y: int
    has_connector: bool = False
    has_full_station: bool = False
    has_walking_paths: bool = False
    is_connected: bool = False
    has_finished_railway: bool = False
    has_signs: bool = False
    chime_directions: tuple[ChimeDirection, ...] = ()
    station_entry_x: int | None = None
    station_entry_y: int | None = None
    city_limit_node_keys: tuple[str, ...] = ()

    @property
    def coordinates(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def station_entry_coordinates(self) -> tuple[int, int] | None:
        if self.station_entry_x is None or self.station_entry_y is None:
            return None
        return (self.station_entry_x, self.station_entry_y)

    @property
    def walking_coordinates(self) -> tuple[int, int]:
        return self.station_entry_coordinates or self.coordinates

    @property
    def plot_coordinates(self) -> tuple[int, int]:
        return (self.x, -self.y)

    @property
    def walking_plot_coordinates(self) -> tuple[int, int]:
        walking_x, walking_y = self.walking_coordinates
        return (walking_x, -walking_y)

    @property
    def distance_to_blackport(self) -> int:
        return d2blckprt(self)

    @property
    def has_name(self) -> bool:
        return _stop_has_name(self)

    @property
    def checkpoint_count(self) -> int:
        return _station_checkpoint_count(self)

    @property
    def checkpoint_total(self) -> int:
        return _station_checkpoint_total(self)


@dataclass(frozen=True, slots=True)
class LinePathPointSpec:
    x_var: str
    y_var: str
    dx: int = 0
    dy: int = 0

    @property
    def plot_coordinates(self) -> tuple[int, int]:
        return (
            STOPS_BY_VAR[self.x_var].x + self.dx,
            STOPS_BY_VAR[self.y_var].plot_coordinates[1] + self.dy,
        )

    @property
    def coordinates(self) -> tuple[int, int]:
        plot_x, plot_y = self.plot_coordinates
        return (plot_x, -plot_y)


@dataclass(frozen=True, slots=True)
class RouteEdge:
    start: RouteNode
    end: RouteNode
    distance: int
    transfer_count: int
    kind: RouteKind
    line_name: str | None = None
    label: str | None = None
    path_points: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class PathEndpoint:
    kind: PathEndpointKind
    key: str
    x: int
    y: int

    @property
    def coordinates(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def plot_coordinates(self) -> tuple[int, int]:
        return (self.x, -self.y)

    @property
    def display_label(self) -> str:
        if self.kind == 'stop':
            return _display_label(STOPS_BY_VAR[self.key].lbl)
        if self.kind == 'city_limit':
            stop_var = _city_limit_stop_var_from_key(self.key)
            if stop_var in STOPS_BY_VAR:
                return f'{_display_label(STOPS_BY_VAR[stop_var].lbl)} city limits'
            return 'City limits'
        path_node = PATH_NODES_BY_KEY.get(self.key)
        if path_node is not None:
            return path_node.display_label
        return f'({self.x}, {self.y})'

    @property
    def input_text(self) -> str:
        if self.kind == 'stop':
            return STOPS_BY_VAR[self.key].lbl
        if self.kind == 'city_limit':
            stop_var = _city_limit_stop_var_from_key(self.key)
            if stop_var in STOPS_BY_VAR:
                return f'City limits: {STOPS_BY_VAR[stop_var].lbl}'
            return self.key
        path_node = PATH_NODES_BY_KEY.get(self.key)
        if path_node is not None:
            return path_node.input_text
        return f'{self.x}, {self.y}'


@dataclass(frozen=True, slots=True)
class PathNode:
    id: str
    x: int
    y: int
    label: str | None = None
    is_explicit: bool = True
    poi_kind: str | None = None
    category: str | None = None

    @property
    def key(self) -> str:
        return _coordinate_endpoint_key(self.x, self.y)

    @property
    def coordinates(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def plot_coordinates(self) -> tuple[int, int]:
        return (self.x, -self.y)

    @property
    def input_text(self) -> str:
        if self.label:
            return self.label
        if self.poi_kind == 'pillager_tower':
            return 'Pillager Tower'
        if self.poi_kind == 'monument' and self.category:
            return f'Unnamed {self.category}'
        if self.is_explicit:
            return self.id
        return f'{self.x}, {self.y}'

    @property
    def display_label(self) -> str:
        if self.label:
            return self.label
        if self.poi_kind == 'pillager_tower':
            return 'Pillager Tower'
        if self.poi_kind == 'monument' and self.category:
            return f'Unnamed {self.category}'
        if self.is_explicit:
            return f'Node {self.id}'
        return f'Node ({self.x}, {self.y})'

    @property
    def debug_label(self) -> str:
        return f'{self.display_label} ({self.x}, {self.y})'


@dataclass(frozen=True, slots=True)
class RouteStep:
    kind: RouteKind
    start_key: str
    end_key: str
    distance: int
    path_points: tuple[tuple[int, int], ...]
    line_name: str | None = None
    label: str | None = None
    stop_vars: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        if self.kind == 'ride':
            return f'Line {self.line_name}'
        if self.label:
            return self.label
        return self.kind.title()

    @property
    def stop_count(self) -> int:
        if len(self.stop_vars) < 2:
            return 0
        return max(0, len(self.stop_vars) - 1)


def _path_node_type_label(path_node: PathNode) -> str:
    if path_node.poi_kind == 'monument':
        return f'monument ({path_node.category})' if path_node.category else 'monument'
    if path_node.poi_kind == 'pillager_tower':
        return 'pillager tower'
    return 'saved' if path_node.is_explicit else 'derived from paths'


@dataclass(frozen=True, slots=True)
class RouteResult:
    start_key: str
    end_key: str
    total_distance: int
    total_interchanges: int
    steps: tuple[RouteStep, ...]


@dataclass(frozen=True, slots=True)
class ExtraEdgeDefinition:
    id: str
    kind: ExtraEdgeKind
    from_endpoint: PathEndpoint
    to_endpoint: PathEndpoint
    bidirectional: bool = True
    label: str | None = None
    distance: int | None = None
    path_points: tuple[tuple[int, int], ...] = ()

    @property
    def plot_points(self) -> tuple[tuple[int, int], ...]:
        if self.path_points:
            return tuple((point_x, -point_y) for point_x, point_y in self.path_points)
        return (
            self.from_endpoint.plot_coordinates,
            self.to_endpoint.plot_coordinates,
        )

    @property
    def reverse_plot_points(self) -> tuple[tuple[int, int], ...]:
        return tuple(reversed(self.plot_points))

    @property
    def resolved_distance(self) -> int:
        if self.distance is not None:
            return self.distance
        return _polyline_distance(self.plot_points)

    @property
    def display_label(self) -> str:
        if self.label:
            return self.label
        return 'Metro' if self.kind == 'connector' else 'Walk'

    @property
    def can_turn(self) -> bool:
        return (
            self.from_endpoint.x != self.to_endpoint.x
            and self.from_endpoint.y != self.to_endpoint.y
        )

    @property
    def turn_variant(self) -> int | None:
        return _extra_edge_turn_variant_from_points(
            self.path_points,
            from_coordinates=self.from_endpoint.coordinates,
            to_coordinates=self.to_endpoint.coordinates,
        )

    @property
    def shape_label(self) -> str:
        if not self.path_points:
            return 'direct'
        if self.turn_variant is not None:
            return 'turn'
        return 'custom'


@dataclass(frozen=True, slots=True)
class AlignmentReminder:
    first_var: str
    second_var: str
    axis: AlignmentAxis

    @property
    def first_stop(self) -> MetroStop:
        return STOPS_BY_VAR[self.first_var]

    @property
    def second_stop(self) -> MetroStop:
        return STOPS_BY_VAR[self.second_var]

    @property
    def is_aligned(self) -> bool:
        first_stop = self.first_stop
        second_stop = self.second_stop
        if self.axis == 'x':
            return first_stop.x == second_stop.x
        return first_stop.y == second_stop.y

    @property
    def included_stop_vars(self) -> tuple[str, ...]:
        return _alignment_included_stop_vars(self)

    @property
    def included_stops(self) -> tuple[MetroStop, ...]:
        return tuple(STOPS_BY_VAR[stop_var] for stop_var in self.included_stop_vars)

    @property
    def debug_label(self) -> str:
        return _alignment_reminder_debug_label(self)


@dataclass(frozen=True, slots=True)
class MetroLineSegment:
    line_name: str
    start_var: str
    end_var: str
    specs: tuple[LinePathPointSpec, ...]

    @property
    def start_stop(self) -> MetroStop:
        return STOPS_BY_VAR[self.start_var]

    @property
    def end_stop(self) -> MetroStop:
        return STOPS_BY_VAR[self.end_var]

    @property
    def plot_points(self) -> tuple[tuple[int, int], ...]:
        return tuple(spec.plot_coordinates for spec in self.specs)

    @property
    def can_turn(self) -> bool:
        return self.start_stop.x != self.end_stop.x and self.start_stop.y != self.end_stop.y

    @property
    def turn_variant(self) -> int | None:
        return _metro_segment_turn_variant(
            self.specs,
            start_var=self.start_var,
            end_var=self.end_var,
        )

    @property
    def shape_label(self) -> MetroSegmentShape:
        return _metro_segment_shape_label(
            self.specs,
            start_var=self.start_var,
            end_var=self.end_var,
        )

def d2blckprt(stop: MetroStop) -> int:
    blackport = _blackport_stop()
    return round(dist(stop.coordinates, blackport.coordinates))


def _blackport_stop() -> MetroStop:
    if BLACKPORT_VAR in STOPS_BY_VAR:
        return STOPS_BY_VAR[BLACKPORT_VAR]
    return STOPS_BY_LBL[BLACKPORT_LBL]


def _coordinate_endpoint_key(x: int, y: int) -> str:
    return f'{COORDINATE_ENDPOINT_PREFIX}{x},{y}'


def _city_limit_endpoint_key(stop_var: str) -> str:
    return f'{CITY_LIMIT_ENDPOINT_PREFIX}{stop_var}'


def _city_limit_stop_var_from_key(endpoint_key: str) -> str:
    return endpoint_key.removeprefix(CITY_LIMIT_ENDPOINT_PREFIX)


def _coerce_int(value: object) -> int | None:
    try:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(value)
        if isinstance(value, (bytes, bytearray)):
            return int(value)
        return None
    except (TypeError, ValueError):
        return None


def _copy_path_spec_record(spec: LinePathSpecRecord) -> LinePathSpecRecord:
    return {
        'x_var': spec['x_var'],
        'y_var': spec['y_var'],
        'dx': spec['dx'],
        'dy': spec['dy'],
    }


def _coordinates_from_endpoint_key(endpoint_key: str) -> tuple[int, int] | None:
    if not endpoint_key.startswith(COORDINATE_ENDPOINT_PREFIX):
        return None
    coordinate_text = endpoint_key.removeprefix(COORDINATE_ENDPOINT_PREFIX)
    return _parse_coordinate_text(coordinate_text)


def _parse_coordinate_text(text: str) -> tuple[int, int] | None:
    match = re.fullmatch(r'\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?', text.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _resolve_stop_var_runtime(identifier: str) -> str | None:
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return None
    if normalized_identifier in STOPS_BY_VAR:
        return normalized_identifier
    if normalized_identifier in STOPS_BY_LBL:
        return STOPS_BY_LBL[normalized_identifier].var

    display_label_matches = [
        stop.var
        for stop in METRO_STOPS
        if _display_label(stop.lbl) == normalized_identifier
    ]
    if len(display_label_matches) == 1:
        return display_label_matches[0]

    normalized_query = _normalize_stop_identity(normalized_identifier)
    exact_matches = [
        stop.var
        for stop in METRO_STOPS
        if normalized_query in {
            _normalize_stop_identity(stop.lbl),
            _normalize_stop_identity(_display_label(stop.lbl)),
            _normalize_stop_identity(stop.var.removeprefix('P_')),
        }
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    return None


def _resolve_path_node_runtime(identifier: str) -> PathNode | None:
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return None

    if normalized_identifier in PATH_NODES_BY_ID:
        return PATH_NODES_BY_ID[normalized_identifier]

    exact_label_matches = [
        node
        for node in PATH_NODES
        if node.label and node.label == normalized_identifier
    ]
    if len(exact_label_matches) == 1:
        return exact_label_matches[0]

    display_label_matches = [
        node
        for node in PATH_NODES
        if node.display_label == normalized_identifier
    ]
    if len(display_label_matches) == 1:
        return display_label_matches[0]

    normalized_query = _normalize_stop_identity(normalized_identifier)
    normalized_matches = [
        node
        for node in PATH_NODES
        if normalized_query in {
            _normalize_stop_identity(node.id),
            _normalize_stop_identity(node.display_label),
            _normalize_stop_identity(node.input_text),
            *(
                {_normalize_stop_identity(node.label)}
                if node.label is not None
                else set()
            ),
        }
    ]
    if len(normalized_matches) == 1:
        return normalized_matches[0]
    return None


def _all_path_nodes() -> tuple[PathNode, ...]:
    global _ALL_PATH_NODES_CACHE_KEY
    global _ALL_PATH_NODES_CACHE
    global _ALL_PATH_NODES_BY_KEY_CACHE

    cache_key = (id(PATH_NODES), id(EXTRA_EDGES))
    if _ALL_PATH_NODES_CACHE_KEY == cache_key:
        return _ALL_PATH_NODES_CACHE

    nodes_by_key = {node.key: node for node in PATH_NODES}
    for extra_edge in EXTRA_EDGES:
        for endpoint in (extra_edge.from_endpoint, extra_edge.to_endpoint):
            if endpoint.kind != 'coord':
                continue
            nodes_by_key.setdefault(
                endpoint.key,
                PathNode(
                    id=endpoint.key.removeprefix(COORDINATE_ENDPOINT_PREFIX).replace(',', '_'),
                    x=endpoint.x,
                    y=endpoint.y,
                    label=None,
                    is_explicit=False,
                    poi_kind=None,
                    category=None,
                ),
            )
    all_nodes = tuple(
        sorted(
            nodes_by_key.values(),
            key=lambda node: (
                node.y,
                node.x,
                node.display_label.lower(),
            ),
        )
    )
    _ALL_PATH_NODES_CACHE_KEY = cache_key
    _ALL_PATH_NODES_CACHE = all_nodes
    _ALL_PATH_NODES_BY_KEY_CACHE = {node.key: node for node in all_nodes}
    return all_nodes


def _all_path_nodes_by_key() -> dict[str, PathNode]:
    _all_path_nodes()
    return _ALL_PATH_NODES_BY_KEY_CACHE


def _city_limit_world_points(stop: MetroStop) -> tuple[tuple[int, int], ...]:
    points: list[tuple[int, int]] = []
    for node_key in stop.city_limit_node_keys:
        coordinates = _coordinates_from_endpoint_key(node_key)
        if coordinates is not None:
            points.append(coordinates)
    return tuple(points)


def _city_limit_centroid_coordinates(stop: MetroStop) -> tuple[int, int] | None:
    points = _city_limit_world_points(stop)
    if not points:
        return None
    return (
        round(sum(point[0] for point in points) / len(points)),
        round(sum(point[1] for point in points) / len(points)),
    )


def _path_endpoint_from_key(endpoint_key: str) -> PathEndpoint | None:
    if endpoint_key.startswith(CITY_LIMIT_ENDPOINT_PREFIX):
        stop_var = _city_limit_stop_var_from_key(endpoint_key)
        stop = STOPS_BY_VAR.get(stop_var)
        if stop is None:
            return None
        coordinates = _city_limit_centroid_coordinates(stop)
        if coordinates is None:
            return None
        return PathEndpoint(kind='city_limit', key=endpoint_key, x=coordinates[0], y=coordinates[1])

    if endpoint_key in STOPS_BY_VAR:
        stop = STOPS_BY_VAR[endpoint_key]
        walking_x, walking_y = stop.walking_coordinates
        return PathEndpoint(kind='stop', key=stop.var, x=walking_x, y=walking_y)

    coordinates = _coordinates_from_endpoint_key(endpoint_key)
    if coordinates is None:
        return None
    return PathEndpoint(kind='coord', key=endpoint_key, x=coordinates[0], y=coordinates[1])


def _path_endpoint_from_runtime_identifier(identifier: str) -> PathEndpoint | None:
    normalized_identifier = identifier.strip()
    for prefix in ('City limits:', 'City limit:'):
        if normalized_identifier.lower().startswith(prefix.lower()):
            stop_var = _resolve_stop_var_runtime(normalized_identifier[len(prefix):].strip())
            if stop_var is not None:
                return _path_endpoint_from_key(_city_limit_endpoint_key(stop_var))

    lower_identifier = normalized_identifier.lower()
    if lower_identifier.endswith(' city limits') or lower_identifier.endswith(' city limit'):
        suffix = ' city limits' if lower_identifier.endswith(' city limits') else ' city limit'
        stop_var = _resolve_stop_var_runtime(normalized_identifier[:-len(suffix)].strip())
        if stop_var is not None:
            return _path_endpoint_from_key(_city_limit_endpoint_key(stop_var))

    stop_var = _resolve_stop_var_runtime(identifier)
    if stop_var is not None:
        return _path_endpoint_from_key(stop_var)

    path_node = _resolve_path_node_runtime(identifier)
    if path_node is not None:
        return _path_endpoint_from_key(path_node.key)

    coordinates = _parse_coordinate_text(identifier)
    if coordinates is None:
        return None
    return _path_endpoint_from_key(_coordinate_endpoint_key(coordinates[0], coordinates[1]))


def _path_endpoint_record_from_identifier(
    payload: MetroNetworkPayload,
    identifier: str,
) -> PathEndpointRecord | None:
    stop_var = _resolve_stop_var_in_payload(payload, identifier)
    if stop_var is not None:
        return {'kind': 'stop', 'stop_var': stop_var}

    path_node = _resolve_path_node_in_payload(payload, identifier)
    if path_node is not None:
        return {
            'kind': 'coord',
            'x': int(path_node['x']),
            'y': int(path_node['y']),
        }

    coordinates = _parse_coordinate_text(identifier)
    if coordinates is None:
        return None
    return {'kind': 'coord', 'x': coordinates[0], 'y': coordinates[1]}


def _path_endpoint_record_coordinates(endpoint_record: PathEndpointRecord) -> tuple[int, int]:
    if endpoint_record['kind'] == 'stop':
        stop = STOPS_BY_VAR[endpoint_record['stop_var']]
        return stop.walking_coordinates
    return (int(endpoint_record['x']), int(endpoint_record['y']))


def _path_endpoint_from_record(endpoint_record: PathEndpointRecord) -> PathEndpoint:
    if endpoint_record['kind'] == 'stop':
        stop = STOPS_BY_VAR[endpoint_record['stop_var']]
        walking_x, walking_y = stop.walking_coordinates
        return PathEndpoint(kind='stop', key=stop.var, x=walking_x, y=walking_y)

    x = int(endpoint_record['x'])
    y = int(endpoint_record['y'])
    return PathEndpoint(kind='coord', key=_coordinate_endpoint_key(x, y), x=x, y=y)


def _required_extra_edge_endpoint(
    edge_record: ExtraEdgeRecord,
    field_name: Literal['from_endpoint', 'to_endpoint'],
) -> PathEndpointRecord:
    endpoint_record = edge_record.get(field_name)
    if endpoint_record is None:
        raise ValueError(f'Path edge is missing {field_name}.')
    return endpoint_record


def _route_input_text_for_endpoint_key(endpoint_key: str) -> str:
    endpoint = _path_endpoint_from_key(endpoint_key)
    if endpoint is None:
        return endpoint_key
    return endpoint.input_text


def _display_label_for_endpoint_key(endpoint_key: str) -> str:
    endpoint = _path_endpoint_from_key(endpoint_key)
    if endpoint is None:
        return endpoint_key
    return endpoint.display_label


def _normalize_stop_identity(text: str) -> str:
    return ''.join(char for char in text.upper() if char.isalnum())


def _stop_has_name(stop: MetroStop) -> bool:
    return _normalize_stop_identity(stop.lbl) != _normalize_stop_identity(stop.var.removeprefix('P_'))


def _infer_alignment_axis_from_coordinates(
    first_x: int,
    first_y: int,
    second_x: int,
    second_y: int,
) -> AlignmentAxis:
    if first_x == second_x and first_y != second_y:
        return 'x'
    if first_y == second_y and first_x != second_x:
        return 'y'
    return 'x' if abs(first_x - second_x) <= abs(first_y - second_y) else 'y'


def _stops_are_aligned(first_stop: MetroStop, second_stop: MetroStop, axis: AlignmentAxis) -> bool:
    if axis == 'x':
        return first_stop.x == second_stop.x
    return first_stop.y == second_stop.y


def _path_spec_identity(spec: LinePathPointSpec | LinePathSpecRecord) -> tuple[str, str, int, int]:
    if isinstance(spec, dict):
        return (
            str(spec['x_var']),
            str(spec['y_var']),
            int(spec.get('dx', 0)),
            int(spec.get('dy', 0)),
        )
    return (spec.x_var, spec.y_var, spec.dx, spec.dy)


def _same_stop_anchor_spec(
    spec: LinePathPointSpec | LinePathSpecRecord,
    stop_var: str,
) -> bool:
    x_var, y_var, _dx, _dy = _path_spec_identity(spec)
    return x_var == y_var == stop_var


def _line_segment_specs(
    line_name: str,
    start_var: str,
    end_var: str,
) -> tuple[LinePathPointSpec, ...]:
    anchor_indices = _line_anchor_index_map(line_name)
    start_index = anchor_indices[start_var]
    end_index = anchor_indices[end_var]
    return tuple(LINE_PATH_SPECS[line_name][start_index:end_index + 1])


def _segment_track_start_spec(
    specs: tuple[LinePathPointSpec, ...] | tuple[LinePathSpecRecord, ...] | list[LinePathSpecRecord],
    *,
    start_var: str,
) -> LinePathPointSpec | LinePathSpecRecord:
    spec_list = list(specs)
    if not spec_list:
        raise ValueError('Segment path specs cannot be empty.')
    if len(spec_list) > 2 and _same_stop_anchor_spec(spec_list[1], start_var):
        return spec_list[1]
    return spec_list[0]


def _segment_turn_middle_variants(
    track_start_spec: LinePathPointSpec | LinePathSpecRecord,
    track_end_spec: LinePathPointSpec | LinePathSpecRecord,
) -> tuple[tuple[str, str, int, int], tuple[str, str, int, int]]:
    start_x_var, _start_y_var, start_dx, _start_dy = _path_spec_identity(track_start_spec)
    _end_x_var, end_y_var, _end_dx, end_dy = _path_spec_identity(track_end_spec)
    end_x_var, _end_anchor_y_var, end_dx, _end_anchor_dy = _path_spec_identity(track_end_spec)
    _start_anchor_x_var, start_y_var, _start_anchor_dx, start_dy = _path_spec_identity(track_start_spec)
    return (
        (start_x_var, end_y_var, start_dx, end_dy),
        (end_x_var, start_y_var, end_dx, start_dy),
    )


def _segment_turn_middle_variant_axes(
    track_start_spec: LinePathPointSpec | LinePathSpecRecord,
    track_end_spec: LinePathPointSpec | LinePathSpecRecord,
) -> tuple[tuple[str, str], tuple[str, str]]:
    start_x_var, start_y_var, _start_dx, _start_dy = _path_spec_identity(track_start_spec)
    end_x_var, end_y_var, _end_dx, _end_dy = _path_spec_identity(track_end_spec)
    return (
        (start_x_var, end_y_var),
        (end_x_var, start_y_var),
    )


def _line_point_from_spec(spec: LinePathPointSpec | LinePathSpecRecord) -> tuple[int, int]:
    x_var, y_var, dx, dy = _path_spec_identity(spec)
    return (
        STOPS_BY_VAR[x_var].x + dx,
        STOPS_BY_VAR[y_var].plot_coordinates[1] + dy,
    )


def _segment_direction(
    specs: tuple[LinePathPointSpec, ...] | tuple[LinePathSpecRecord, ...] | list[LinePathSpecRecord],
    *,
    from_start: bool,
) -> tuple[str, int] | None:
    point_pairs = zip(specs, specs[1:]) if from_start else zip(reversed(specs[:-1]), reversed(specs[1:]))
    for first_spec, second_spec in point_pairs:
        first_x, first_y = _line_point_from_spec(first_spec)
        second_x, second_y = _line_point_from_spec(second_spec)
        delta_x = second_x - first_x
        delta_y = second_y - first_y
        if delta_x == 0 and delta_y == 0:
            continue
        if delta_x != 0 and delta_y == 0:
            return ('x', 1 if delta_x > 0 else -1)
        if delta_y != 0 and delta_x == 0:
            return ('y', 1 if delta_y > 0 else -1)
        return ('other', 0)
    return None


def _spec_points(
    specs: tuple[LinePathPointSpec, ...] | tuple[LinePathSpecRecord, ...] | list[LinePathSpecRecord],
) -> tuple[tuple[int, int], ...]:
    return tuple(_line_point_from_spec(spec) for spec in specs)


def _combined_spec_points(
    *spec_groups: tuple[LinePathPointSpec, ...] | tuple[LinePathSpecRecord, ...] | list[LinePathSpecRecord] | None,
) -> tuple[tuple[int, int], ...]:
    combined_points: list[tuple[int, int]] = []
    for spec_group in spec_groups:
        if spec_group is None:
            continue
        for point in _spec_points(spec_group):
            if combined_points and combined_points[-1] == point:
                continue
            combined_points.append(point)
    return tuple(combined_points)


def _polyline_turn_count(points: tuple[tuple[int, int], ...]) -> int:
    directions: list[tuple[str, int]] = []
    for (start_x, start_y), (end_x, end_y) in zip(points, points[1:]):
        delta_x = end_x - start_x
        delta_y = end_y - start_y
        if delta_x == 0 and delta_y == 0:
            continue
        if delta_x != 0 and delta_y == 0:
            directions.append(('x', 1 if delta_x > 0 else -1))
            continue
        if delta_y != 0 and delta_x == 0:
            directions.append(('y', 1 if delta_y > 0 else -1))
            continue
        directions.append(('other', 0))

    turn_count = 0
    for previous_direction, next_direction in zip(directions, directions[1:]):
        if previous_direction != next_direction:
            turn_count += 1
    return turn_count


def _hook_spec_for_turn_start(
    start_var: str,
    previous_segment_specs: tuple[LinePathSpecRecord, ...] | None,
    bare_segment_specs: list[LinePathSpecRecord],
) -> LinePathSpecRecord | None:
    if previous_segment_specs is None:
        return None

    previous_end_direction = _segment_direction(previous_segment_specs, from_start=False)
    current_start_direction = _segment_direction(bare_segment_specs, from_start=True)
    if previous_end_direction is None or current_start_direction is None:
        return None

    previous_axis, previous_sign = previous_end_direction
    current_axis, _current_sign = current_start_direction
    if previous_axis not in {'x', 'y'} or current_axis not in {'x', 'y'}:
        return None
    if previous_axis == current_axis:
        return None

    return {
        'x_var': start_var,
        'y_var': start_var,
        'dx': 3 * previous_sign if previous_axis == 'x' else 0,
        'dy': 3 * previous_sign if previous_axis == 'y' else 0,
    }


def _extra_edge_turn_variant_from_specs(
    path_specs: tuple[LinePathPointSpec, ...] | list[LinePathSpecRecord],
    *,
    from_var: str,
    to_var: str,
) -> int | None:
    if len(path_specs) != 3:
        return None

    normalized_specs = tuple(_path_spec_identity(spec) for spec in path_specs)
    turn_variants = (
        (
            (from_var, from_var, 0, 0),
            (from_var, to_var, 0, 0),
            (to_var, to_var, 0, 0),
        ),
        (
            (from_var, from_var, 0, 0),
            (to_var, from_var, 0, 0),
            (to_var, to_var, 0, 0),
        ),
    )
    for index, variant in enumerate(turn_variants):
        if normalized_specs == variant:
            return index
    return None


def _turn_path_points(
    from_coordinates: tuple[int, int],
    to_coordinates: tuple[int, int],
    *,
    variant: int,
) -> list[PathPointRecord]:
    if variant not in (0, 1):
        raise ValueError(f'Unknown turn variant: {variant}')

    from_x, from_y = from_coordinates
    to_x, to_y = to_coordinates
    corner_point = (from_x, to_y) if variant == 0 else (to_x, from_y)
    return [
        {'x': from_x, 'y': from_y},
        {'x': corner_point[0], 'y': corner_point[1]},
        {'x': to_x, 'y': to_y},
    ]


def _extra_edge_turn_variant_from_points(
    path_points: tuple[tuple[int, int], ...] | list[tuple[int, int]],
    *,
    from_coordinates: tuple[int, int],
    to_coordinates: tuple[int, int],
) -> int | None:
    if len(path_points) != 3:
        return None
    if path_points[0] != from_coordinates or path_points[-1] != to_coordinates:
        return None

    turn_variants = (
        (
            from_coordinates,
            (from_coordinates[0], to_coordinates[1]),
            to_coordinates,
        ),
        (
            from_coordinates,
            (to_coordinates[0], from_coordinates[1]),
            to_coordinates,
        ),
    )
    for index, variant in enumerate(turn_variants):
        if tuple(path_points) == variant:
            return index
    return None


def _metro_segment_turn_variant(
    specs: tuple[LinePathPointSpec, ...] | tuple[LinePathSpecRecord, ...] | list[LinePathSpecRecord],
    *,
    start_var: str,
    end_var: str,
) -> int | None:
    if len(specs) < 3:
        return None

    start_anchor = specs[0]
    end_anchor = specs[-1]
    track_start = _segment_track_start_spec(specs, start_var=start_var)
    core_specs = list(specs[1:] if track_start is start_anchor else specs[2:])
    if not core_specs:
        return None
    if _path_spec_identity(core_specs[-1]) != _path_spec_identity(end_anchor):
        return None
    if len(core_specs) != 2:
        return None

    middle_identity = _path_spec_identity(core_specs[0])
    for index, variant_identity in enumerate(_segment_turn_middle_variants(track_start, end_anchor)):
        if middle_identity == variant_identity:
            return index
    middle_x_var, middle_y_var, _middle_dx, _middle_dy = middle_identity
    for index, variant_axes in enumerate(_segment_turn_middle_variant_axes(track_start, end_anchor)):
        if (middle_x_var, middle_y_var) == variant_axes:
            return index
    return None


def _metro_segment_shape_label(
    specs: tuple[LinePathPointSpec, ...] | tuple[LinePathSpecRecord, ...] | list[LinePathSpecRecord],
    *,
    start_var: str,
    end_var: str,
) -> MetroSegmentShape:
    track_start = _segment_track_start_spec(specs, start_var=start_var)
    expected_direct_length = 3 if track_start is not specs[0] else 2
    if len(specs) == expected_direct_length:
        if track_start is specs[0]:
            return 'direct'
        if len(specs) == 3 and _path_spec_identity(specs[1]) == _path_spec_identity(track_start):
            return 'direct'
    if _metro_segment_turn_variant(specs, start_var=start_var, end_var=end_var) is not None:
        return 'turn'
    return 'custom'


def _turn_path_specs(from_var: str, to_var: str, *, variant: int) -> list[LinePathSpecRecord]:
    if variant not in (0, 1):
        raise ValueError(f'Unknown turn variant: {variant}')

    corner_x_var, corner_y_var = (from_var, to_var) if variant == 0 else (to_var, from_var)
    return [
        {'x_var': from_var, 'y_var': from_var, 'dx': 0, 'dy': 0},
        {'x_var': corner_x_var, 'y_var': corner_y_var, 'dx': 0, 'dy': 0},
        {'x_var': to_var, 'y_var': to_var, 'dx': 0, 'dy': 0},
    ]


def _metro_segment_path_specs(
    start_anchor_spec: LinePathSpecRecord,
    end_anchor_spec: LinePathSpecRecord,
    *,
    start_var: str,
    shape: MetroSegmentShape,
    turn_variant: int | None = None,
    start_hook_spec: LinePathSpecRecord | None = None,
) -> list[LinePathSpecRecord]:
    new_specs: list[LinePathSpecRecord] = [_copy_path_spec_record(start_anchor_spec)]
    if start_hook_spec is not None:
        new_specs.append(_copy_path_spec_record(start_hook_spec))

    if shape == 'direct':
        new_specs.append(_copy_path_spec_record(end_anchor_spec))
        return new_specs

    if turn_variant not in (0, 1):
        raise ValueError('Turn segments need a valid turn variant.')

    active_start_spec = start_hook_spec or start_anchor_spec
    middle_variants = _segment_turn_middle_variants(active_start_spec, end_anchor_spec)
    middle_x_var, middle_y_var, middle_dx, middle_dy = middle_variants[turn_variant]
    new_specs.append(
        {
            'x_var': middle_x_var,
            'y_var': middle_y_var,
            'dx': middle_dx,
            'dy': middle_dy,
        }
    )
    new_specs.append(_copy_path_spec_record(end_anchor_spec))
    return new_specs


def _shared_line_names_for_stops(first_var: str, second_var: str) -> tuple[str, ...]:
    return tuple(
        line_name
        for line_name, stop_vars in sorted(LINE_STOP_VARS.items())
        if first_var in stop_vars and second_var in stop_vars
    )


def _line_segment_stop_vars(line_name: str, first_var: str, second_var: str) -> tuple[str, ...]:
    stop_vars = LINE_STOP_VARS[line_name]
    first_index = stop_vars.index(first_var)
    second_index = stop_vars.index(second_var)
    start_index, end_index = sorted((first_index, second_index))
    return stop_vars[start_index:end_index + 1]


def _alignment_included_stop_vars(reminder: AlignmentReminder) -> tuple[str, ...]:
    ordered_stop_vars: list[str] = []
    seen_stop_vars: set[str] = set()

    for line_name in _shared_line_names_for_stops(reminder.first_var, reminder.second_var):
        for stop_var in _line_segment_stop_vars(line_name, reminder.first_var, reminder.second_var):
            if stop_var in seen_stop_vars:
                continue
            ordered_stop_vars.append(stop_var)
            seen_stop_vars.add(stop_var)

    if not ordered_stop_vars:
        return (reminder.first_var, reminder.second_var)
    return tuple(ordered_stop_vars)


def _alignment_reminder_debug_label(reminder: AlignmentReminder) -> str:
    included_labels = ', '.join(
        _display_label(STOPS_BY_VAR[stop_var].lbl)
        for stop_var in reminder.included_stop_vars
    )
    return f'{reminder.axis}: {included_labels}'


def _alignment_reminder_bounds(
    reminder: AlignmentReminder,
    world_to_canvas: Callable[[tuple[float, float]], tuple[float, float]],
    *,
    zoom: float,
) -> tuple[float, float, float, float]:
    canvas_points = [
        world_to_canvas(stop.plot_coordinates)
        for stop in reminder.included_stops
    ]
    xs = [point[0] for point in canvas_points]
    ys = [point[1] for point in canvas_points]
    padding = max(ALIGNMENT_REMINDER_PADDING, round(ALIGNMENT_REMINDER_PADDING * zoom))
    left = min(xs) - padding
    right = max(xs) + padding
    top = min(ys) - padding
    bottom = max(ys) + padding

    if (right - left) < ALIGNMENT_REMINDER_MIN_SIZE:
        center_x = (left + right) / 2
        half_width = ALIGNMENT_REMINDER_MIN_SIZE / 2
        left = center_x - half_width
        right = center_x + half_width
    if (bottom - top) < ALIGNMENT_REMINDER_MIN_SIZE:
        center_y = (top + bottom) / 2
        half_height = ALIGNMENT_REMINDER_MIN_SIZE / 2
        top = center_y - half_height
        bottom = center_y + half_height

    return (left, right, top, bottom)


def _all_plot_points() -> list[tuple[int, int]]:
    plot_points = [stop.plot_coordinates for stop in METRO_STOPS]
    plot_points.extend(path_node.plot_coordinates for path_node in _all_path_nodes())
    for path_points in METRO_LINE_PLOT_PATHS.values():
        plot_points.extend(path_points)
    for extra_edge in EXTRA_EDGES:
        plot_points.extend(extra_edge.plot_points)
    return plot_points


def _plot_bounds(
    points: Sequence[tuple[float, float]],
) -> tuple[float, float, float, float] | None:
    if not points:
        return None

    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (min(xs), max(xs), min(ys), max(ys))


def _plot_transform(
    width: int = PLOT_WIDTH,
    height: int = PLOT_HEIGHT,
    padding: int = PLOT_PADDING,
) -> tuple[int, int, int, int, float]:
    plot_points = _all_plot_points()
    xs = [point[0] for point in plot_points]
    ys = [point[1] for point in plot_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    x_span = max(max_x - min_x, 1)
    y_span = max(max_y - min_y, 1)
    scale = min((width - (padding * 2)) / x_span, (height - (padding * 2)) / y_span)
    return (min_x, max_x, min_y, max_y, scale)


def _to_canvas(
    point: tuple[float, float],
    width: int = PLOT_WIDTH,
    height: int = PLOT_HEIGHT,
    padding: int = PLOT_PADDING,
) -> tuple[float, float]:
    min_x, _, min_y, _, scale = _plot_transform(width=width, height=height, padding=padding)
    return (
        padding + ((point[0] - min_x) * scale),
        height - padding - ((point[1] - min_y) * scale),
    )


def _apply_viewport_to_canvas(
    point: tuple[float, float],
    *,
    width: int,
    height: int,
    padding: int,
    zoom: float,
    pan_x: float,
    pan_y: float,
) -> tuple[float, float]:
    base_x, base_y = _to_canvas(point, width=width, height=height, padding=padding)
    center_x = width / 2
    center_y = height / 2
    return (
        center_x + ((base_x - center_x) * zoom) + pan_x,
        center_y + ((base_y - center_y) * zoom) + pan_y,
    )


def _visible_stop_line_names(stop: MetroStop, visible_line_names: set[str]) -> tuple[str, ...]:
    return tuple(
        line_name
        for line_name in STOP_LINE_NAMES[stop.var]
        if line_name in visible_line_names
    )


def _fill_for_visible_line_names(visible_line_names: tuple[str, ...]) -> str:
    if not visible_line_names:
        return UNASSOCIATED_STATION_FILL
    if len(visible_line_names) != 1:
        return INTERSECTION_COLOR
    return LINE_COLORS[visible_line_names[0]]


def _label_fill_for_visible_line_names(visible_line_names: tuple[str, ...]) -> str:
    if not visible_line_names:
        return UNASSOCIATED_STATION_OUTLINE
    if len(visible_line_names) != 1:
        return JUNCTION_LABEL_COLOR
    return LINE_COLORS[visible_line_names[0]]


def _station_fill(stop: MetroStop) -> str:
    line_names = STOP_LINE_NAMES[stop.var]
    if not line_names:
        return UNASSOCIATED_STATION_FILL
    if len(line_names) != 1:
        return INTERSECTION_COLOR
    return LINE_COLORS[line_names[0]]


def _display_label(lbl: str) -> str:
    match = re.fullmatch(r'([A-Za-z]+)_\{?([0-9-]+)\}?', lbl)
    if not match:
        return lbl
    return f"{match.group(1)}{match.group(2).translate(SUBSCRIPT_TRANSLATION)}"


def _is_placeholder_station_label(lbl: str) -> bool:
    return bool(re.fullmatch(r'[A-Z0-9_{}]+', lbl.strip()))


def _station_signage_label(stop_var: str, line_name: str) -> str:
    stop = STOPS_BY_VAR[stop_var]
    label = _display_label(stop.lbl)
    other_line_names = ''.join(
        other_line_name
        for other_line_name in STOP_LINE_NAMES[stop_var]
        if other_line_name != line_name
    )
    if other_line_names and not _is_placeholder_station_label(stop.lbl):
        return f'{label} ({other_line_names})'
    return label


def _station_signage_direction_stop_vars(
    stop_var: str,
    line_name: str,
    *,
    flipped: bool = False,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    stop_vars = LINE_STOP_VARS[line_name]
    stop_index = stop_vars.index(stop_var)
    before_stop_vars = tuple(reversed(stop_vars[:stop_index]))
    after_stop_vars = tuple(stop_vars[stop_index + 1:])

    if stop_index == 0:
        return (after_stop_vars, ())
    if stop_index == len(stop_vars) - 1:
        return (before_stop_vars, ())
    if flipped:
        return (before_stop_vars, after_stop_vars)
    return (after_stop_vars, before_stop_vars)


def _label_font_size(zoom: float) -> int:
    if zoom <= DEFAULT_ZOOM:
        return BASE_LABEL_FONT_SIZE
    growth_steps = log(zoom, ZOOM_STEP)
    growth = min(MAX_LABEL_FONT_GROWTH, round(growth_steps * LABEL_FONT_GROWTH_PER_ZOOM_STEP))
    return BASE_LABEL_FONT_SIZE + growth


def _svg_escape(value: str) -> str:
    return html.escape(value, quote=True)


def _svg_points(points: list[tuple[float, float]] | tuple[tuple[float, float], ...]) -> str:
    return ' '.join(f'{point_x:.2f},{point_y:.2f}' for point_x, point_y in points)


def _svg_dasharray(values: tuple[int, int]) -> str:
    return ' '.join(str(value) for value in values)


def _svg_rgba(rgba: tuple[int, int, int, int]) -> tuple[str, float]:
    red, green, blue, alpha = rgba
    return (f'#{red:02x}{green:02x}{blue:02x}', alpha / 255)


@dataclass(frozen=True, slots=True)
class SvgRasterImage:
    data_uri: str
    left: float
    top: float
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class SvgExportOptions:
    include_world_map: bool
    include_grid: bool
    include_metro_lines: bool
    include_stations: bool
    include_labels: bool
    include_path_nodes: bool
    include_walking_paths: bool
    include_connector_paths: bool
    include_current_route: bool
    include_planning_circle: bool
    include_connected_area: bool
    include_alignment_ellipses: bool
    include_frontier_highlights: bool
    include_railway_finishing: bool


def _build_map_svg(
    *,
    width: int,
    height: int,
    padding: int,
    zoom: float,
    pan_x: float,
    pan_y: float,
    visible_line_names: set[str],
    export_options: SvgExportOptions,
    world_map_image: SvgRasterImage | None,
    current_route: RouteResult | None,
) -> str:
    min_x, max_x, min_y, max_y, scale = _plot_transform(width=width, height=height, padding=padding)
    label_font_size = _label_font_size(zoom)
    label_growth = label_font_size - BASE_LABEL_FONT_SIZE
    label_offset_x = LABEL_OFFSET_X + label_growth
    label_offset_y = LABEL_OFFSET_Y + label_growth
    frontier_label_stop_vars = (
        _frontier_highlight_stop_vars()
        if export_options.include_frontier_highlights
        else frozenset()
    )

    def world_to_canvas(point: tuple[float, float]) -> tuple[float, float]:
        return _apply_viewport_to_canvas(
            point,
            width=width,
            height=height,
            padding=padding,
            zoom=zoom,
            pan_x=pan_x,
            pan_y=pan_y,
        )

    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
        f'  <rect width="{width}" height="{height}" fill="{BACKGROUND_COLOR}" />',
    ]

    if export_options.include_world_map and world_map_image is not None:
        svg_lines.append(
            (
                f'  <image x="{world_map_image.left:.2f}" y="{world_map_image.top:.2f}" '
                f'width="{world_map_image.width}" height="{world_map_image.height}" '
                f'href="{world_map_image.data_uri}" preserveAspectRatio="none" '
                f'style="image-rendering: pixelated;" />'
            )
        )

    if export_options.include_grid and min_x <= 0 <= max_x:
        zero_x = world_to_canvas((0, min_y))[0]
        zero_top = world_to_canvas((0, max_y))[1]
        zero_bottom = world_to_canvas((0, min_y))[1]
        svg_lines.append(
            (
                f'  <line x1="{zero_x:.2f}" y1="{zero_top:.2f}" x2="{zero_x:.2f}" '
                f'y2="{zero_bottom:.2f}" stroke="{GRID_COLOR}" stroke-width="1" '
                f'stroke-dasharray="{_svg_dasharray((4, 4))}" />'
            )
        )
    if export_options.include_grid and min_y <= 0 <= max_y:
        zero_left = world_to_canvas((min_x, 0))[0]
        zero_right = world_to_canvas((max_x, 0))[0]
        zero_y = world_to_canvas((min_x, 0))[1]
        svg_lines.append(
            (
                f'  <line x1="{zero_left:.2f}" y1="{zero_y:.2f}" x2="{zero_right:.2f}" '
                f'y2="{zero_y:.2f}" stroke="{GRID_COLOR}" stroke-width="1" '
                f'stroke-dasharray="{_svg_dasharray((4, 4))}" />'
            )
        )

    if export_options.include_planning_circle:
        planning_radius = _planning_radius_distance()
        if planning_radius > 0:
            center_stop = _blackport_stop()
            center_x, center_y = world_to_canvas(center_stop.plot_coordinates)
            canvas_radius = planning_radius * scale * zoom
            if canvas_radius > 0:
                circle_fill, circle_opacity = _svg_rgba(CIRCLE_OVERLAY_RGBA)
                svg_lines.append(
                    (
                        f'  <circle cx="{center_x:.2f}" cy="{center_y:.2f}" r="{canvas_radius:.2f}" '
                        f'fill="{circle_fill}" fill-opacity="{circle_opacity:.3f}" />'
                    )
                )

    if export_options.include_connected_area:
        area_loops = _connected_route_area_world_loops()
        if area_loops:
            area_fill, area_opacity = _svg_rgba(AREA_OVERLAY_RGBA)
            for area_loop in area_loops:
                polygon_points = [world_to_canvas(point) for point in area_loop]
                if len(polygon_points) < 3:
                    continue
                svg_lines.append(
                    (
                        f'  <polygon points="{_svg_points(polygon_points)}" fill="{area_fill}" '
                        f'fill-opacity="{area_opacity:.3f}" />'
                    )
                )

    if export_options.include_metro_lines:
        for segment in _all_metro_segments():
            if segment.line_name not in visible_line_names:
                continue
            canvas_points = [world_to_canvas(point) for point in segment.plot_points]
            if len(canvas_points) < 2:
                continue
            stroke_width, dash = _metro_segment_style(segment)
            dash_markup = ''
            if dash is not None:
                dash_markup = f' stroke-dasharray="{_svg_dasharray(dash)}"'
            svg_lines.append(
                (
                    f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                    f'stroke="{LINE_COLORS[segment.line_name]}" stroke-width="{stroke_width}" '
                    f'stroke-linecap="round" stroke-linejoin="round"{dash_markup} />'
                )
            )

    for extra_edge in EXTRA_EDGES:
        if extra_edge.kind == 'walk' and not export_options.include_walking_paths:
            continue
        if extra_edge.kind == 'connector' and not export_options.include_connector_paths:
            continue
        canvas_points = [world_to_canvas(point) for point in extra_edge.plot_points]
        if len(canvas_points) < 2:
            continue
        dash_markup = ''
        if extra_edge.kind == 'walk':
            dash_markup = f' stroke-dasharray="{_svg_dasharray((6, 4))}"'
        svg_lines.append(
            (
                f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                f'stroke="{CONNECTOR_ROUTE_COLOR if extra_edge.kind == "connector" else WALK_ROUTE_COLOR}" '
                f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"{dash_markup} />'
            )
        )

    if export_options.include_path_nodes:
        for path_node in _all_path_nodes():
            canvas_x, canvas_y = world_to_canvas(path_node.plot_coordinates)
            svg_lines.append(
                (
                    f'  <rect x="{(canvas_x - PATH_NODE_RADIUS):.2f}" y="{(canvas_y - PATH_NODE_RADIUS):.2f}" '
                    f'width="{(PATH_NODE_RADIUS * 2):.2f}" height="{(PATH_NODE_RADIUS * 2):.2f}" '
                    f'fill="{PATH_NODE_FILL}" stroke="{PATH_NODE_OUTLINE}" stroke-width="1" />'
                )
            )
            if export_options.include_labels and path_node.label:
                label_x = canvas_x + label_offset_x
                label_y = canvas_y - label_offset_y
                svg_lines.append(
                    (
                        f'  <text x="{label_x:.2f}" y="{label_y:.2f}" fill="{PATH_NODE_LABEL_COLOR}" '
                        f'font-family="Helvetica, Arial, sans-serif" font-size="{max(10, label_font_size - 1)}" '
                        f'text-anchor="start" dominant-baseline="alphabetic" '
                        f'transform="rotate(-{LABEL_ANGLE:.2f} {label_x:.2f} {label_y:.2f})">'
                        f'{_svg_escape(path_node.label)}</text>'
                    )
                )

    if export_options.include_current_route and current_route is not None:
        for step in current_route.steps:
            if not step.path_points:
                continue
            canvas_points = [world_to_canvas(point) for point in step.path_points]
            if len(canvas_points) < 2:
                continue
            svg_lines.append(
                (
                    f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                    f'stroke="{ROUTE_HIGHLIGHT_OUTLINE}" stroke-width="{ROUTE_HIGHLIGHT_OUTLINE_WIDTH}" '
                    f'stroke-linecap="round" stroke-linejoin="round" />'
                )
            )
            svg_lines.append(
                (
                    f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                    f'stroke="{_route_step_color(step)}" stroke-width="{ROUTE_HIGHLIGHT_WIDTH}" '
                    f'stroke-linecap="round" stroke-linejoin="round" />'
                )
            )

    if export_options.include_railway_finishing:
        for line_name in _railway_finish_line_names():
            if line_name not in visible_line_names:
                continue
            for start_distance, end_distance in _line_unfinished_connected_intervals(line_name):
                highlight_points = _polyline_slice_between_distances(
                    METRO_LINE_PLOT_PATHS[line_name],
                    start_distance,
                    end_distance,
                )
                canvas_points = [world_to_canvas(point) for point in highlight_points]
                if len(canvas_points) < 2:
                    continue
                svg_lines.append(
                    (
                        f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                        f'stroke="{FINISHED_RAILWAY_HIGHLIGHT_OUTLINE}" '
                        f'stroke-width="{FINISHED_RAILWAY_HIGHLIGHT_OUTLINE_WIDTH}" '
                        f'stroke-linecap="round" stroke-linejoin="round" />'
                    )
                )
                svg_lines.append(
                    (
                        f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                        f'stroke="{LINE_COLORS[line_name]}" stroke-width="{FINISHED_RAILWAY_HIGHLIGHT_WIDTH}" '
                        f'stroke-linecap="round" stroke-linejoin="round" />'
                    )
                )

    if export_options.include_frontier_highlights and not export_options.include_railway_finishing:
        for line_name, frontier_var, target_var in _frontier_highlight_segments():
            if line_name not in visible_line_names:
                continue
            try:
                highlight_points = _line_segment_plot_points(line_name, frontier_var, target_var)
            except (KeyError, ValueError):
                continue
            canvas_points = [world_to_canvas(point) for point in highlight_points]
            if len(canvas_points) < 2:
                continue
            svg_lines.append(
                (
                    f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                    f'stroke="{FRONTIER_HIGHLIGHT_OUTLINE}" '
                    f'stroke-width="{FRONTIER_SEGMENT_OUTLINE_WIDTH}" '
                    f'stroke-linecap="round" stroke-linejoin="round" />'
                )
            )
            svg_lines.append(
                (
                    f'  <polyline points="{_svg_points(canvas_points)}" fill="none" '
                    f'stroke="{LINE_COLORS[line_name]}" stroke-width="{FRONTIER_SEGMENT_WIDTH}" '
                    f'stroke-linecap="round" stroke-linejoin="round" />'
                )
            )

    if export_options.include_alignment_ellipses:
        for reminder in ALIGNMENT_REMINDERS:
            if reminder.is_aligned:
                continue

            left, right, top, bottom = _alignment_reminder_bounds(
                reminder,
                world_to_canvas,
                zoom=zoom,
            )

            svg_lines.append(
                (
                    f'  <ellipse cx="{((left + right) / 2):.2f}" cy="{((top + bottom) / 2):.2f}" '
                    f'rx="{((right - left) / 2):.2f}" ry="{((bottom - top) / 2):.2f}" fill="none" '
                    f'stroke="{ALIGNMENT_REMINDER_OUTLINE}" stroke-width="{ALIGNMENT_REMINDER_WIDTH}" '
                    f'stroke-dasharray="{_svg_dasharray((8, 4))}" />'
                )
            )
            label_x = (left + right) / 2
            label_y = max(ALIGNMENT_REMINDER_LABEL_FONT_SIZE + 2, top - 4)
            svg_lines.append(
                (
                    f'  <text x="{label_x:.2f}" y="{label_y:.2f}" fill="{ALIGNMENT_REMINDER_OUTLINE}" '
                    f'font-family="Helvetica, Arial, sans-serif" '
                    f'font-size="{ALIGNMENT_REMINDER_LABEL_FONT_SIZE}" text-anchor="middle">'
                    f'{_svg_escape(reminder.debug_label)}</text>'
                )
            )

    if export_options.include_stations:
        for stop in METRO_STOPS:
            stop_visible_line_names = _visible_stop_line_names(stop, visible_line_names)
            if not stop_visible_line_names:
                continue
            canvas_x, canvas_y = world_to_canvas(stop.plot_coordinates)
            stop_fill = _fill_for_visible_line_names(stop_visible_line_names)
            label_fill = _label_fill_for_visible_line_names(stop_visible_line_names)
            svg_lines.append(
                (
                    f'  <circle cx="{canvas_x:.2f}" cy="{canvas_y:.2f}" r="{STATION_RADIUS:.2f}" '
                    f'fill="{stop_fill}" />'
                )
            )
            if export_options.include_labels:
                label_x = canvas_x + label_offset_x
                label_y = canvas_y - label_offset_y
                font_weight_markup = ' font-weight="bold"' if stop.var in frontier_label_stop_vars else ''
                label_size = label_font_size + (
                    FRONTIER_LABEL_SIZE_BOOST if stop.var in frontier_label_stop_vars else 0
                )
                label_markup = (
                    f'x="{label_x:.2f}" y="{label_y:.2f}" '
                    f'font-family="Helvetica, Arial, sans-serif" font-size="{label_size}"'
                    f'{font_weight_markup} '
                    f'text-anchor="start" dominant-baseline="alphabetic" '
                    f'transform="rotate(-{LABEL_ANGLE:.2f} {label_x:.2f} {label_y:.2f})"'
                )
                label_text = _svg_escape(_display_label(stop.lbl))
                svg_lines.append(
                    (
                        f'  <text {label_markup} fill="none" stroke="{LABEL_CASING_COLOR}" '
                        f'stroke-width="{LABEL_CASING_WIDTH}" stroke-linejoin="round" '
                        f'paint-order="stroke">{label_text}</text>'
                    )
                )
                svg_lines.append(
                    (
                        f'  <text {label_markup} fill="{label_fill}">{label_text}</text>'
                    )
                )

    svg_lines.append('</svg>')
    return '\n'.join(svg_lines) + '\n'


def _connected_route_plot_paths() -> list[tuple[tuple[int, int], ...]]:
    connected_paths: list[tuple[tuple[int, int], ...]] = []

    for line_name, stop_vars in LINE_STOP_VARS.items():
        connected_stop_vars = [stop_var for stop_var in stop_vars if STOPS_BY_VAR[stop_var].is_connected]
        if not connected_stop_vars:
            continue

        point_specs = LINE_PATH_SPECS[line_name]
        anchor_indices = {
            stop_var: [
                index
                for index, spec in enumerate(point_specs)
                if spec.x_var == stop_var and spec.y_var == stop_var
            ]
            for stop_var in connected_stop_vars
        }
        if not all(anchor_indices.values()):
            continue

        start_index = min(anchor_indices[connected_stop_vars[0]])
        end_index = max(anchor_indices[connected_stop_vars[-1]])

        route_points = tuple(
            spec.plot_coordinates for spec in point_specs[start_index:end_index + 1]
        )
        if route_points:
            connected_paths.append(route_points)

    return connected_paths


def _extra_edges_for_stop(stop_var: str) -> tuple[ExtraEdgeDefinition, ...]:
    return tuple(
        extra_edge
        for extra_edge in EXTRA_EDGES
        if stop_var in (extra_edge.from_endpoint.key, extra_edge.to_endpoint.key)
    )


def _extra_edges_for_endpoint_key(endpoint_key: str) -> tuple[ExtraEdgeDefinition, ...]:
    return tuple(
        extra_edge
        for extra_edge in EXTRA_EDGES
        if endpoint_key in (extra_edge.from_endpoint.key, extra_edge.to_endpoint.key)
    )


def _extra_edge_other_endpoint(extra_edge: ExtraEdgeDefinition, stop_var: str) -> PathEndpoint:
    return extra_edge.to_endpoint if extra_edge.from_endpoint.key == stop_var else extra_edge.from_endpoint


def _extra_edge_summary(extra_edge: ExtraEdgeDefinition, stop_var: str) -> str:
    other_endpoint = _extra_edge_other_endpoint(extra_edge, stop_var)
    return (
        f'{extra_edge.display_label} to {other_endpoint.display_label} '
        f'({_format_track_distance(extra_edge.resolved_distance)}, '
        f'{extra_edge.shape_label}{_extra_edge_turn_coordinate_suffix(extra_edge)})'
    )


def _extra_edge_turn_coordinates(extra_edge: ExtraEdgeDefinition) -> tuple[tuple[int, int], ...]:
    if len(extra_edge.path_points) <= 2:
        return ()
    return extra_edge.path_points[1:-1]


def _extra_edge_turn_coordinate_suffix(extra_edge: ExtraEdgeDefinition) -> str:
    turn_coordinates = _extra_edge_turn_coordinates(extra_edge)
    if not turn_coordinates:
        return ''
    coordinate_text = ', '.join(f'({point_x}, {point_y})' for point_x, point_y in turn_coordinates)
    return f', turns at {coordinate_text}'


def _extra_edge_full_summary(extra_edge: ExtraEdgeDefinition) -> str:
    return (
        f'{extra_edge.display_label}: {extra_edge.from_endpoint.display_label} '
        f'to {extra_edge.to_endpoint.display_label} '
        f'({_format_track_distance(extra_edge.resolved_distance)}, '
        f'{extra_edge.shape_label}{_extra_edge_turn_coordinate_suffix(extra_edge)})'
    )


def _extra_edge_summary_for_endpoint(extra_edge: ExtraEdgeDefinition, endpoint_key: str) -> str:
    other_endpoint = (
        extra_edge.to_endpoint
        if extra_edge.from_endpoint.key == endpoint_key
        else extra_edge.from_endpoint
    )
    return (
        f'{extra_edge.display_label} to {other_endpoint.display_label} '
        f'({_format_track_distance(extra_edge.resolved_distance)}, '
        f'{extra_edge.shape_label}{_extra_edge_turn_coordinate_suffix(extra_edge)})'
    )


def _polyline_distance(points: tuple[tuple[int, int], ...]) -> int:
    return sum(round(dist(start_point, end_point)) for start_point, end_point in zip(points, points[1:]))


def _point_to_segment_distance_sq(
    point: tuple[float, float],
    start_point: tuple[float, float],
    end_point: tuple[float, float],
) -> float:
    point_x, point_y = point
    start_x, start_y = start_point
    end_x, end_y = end_point
    delta_x = end_x - start_x
    delta_y = end_y - start_y
    segment_length_sq = (delta_x * delta_x) + (delta_y * delta_y)
    if segment_length_sq == 0:
        return ((point_x - start_x) ** 2) + ((point_y - start_y) ** 2)

    projection = (
        ((point_x - start_x) * delta_x) + ((point_y - start_y) * delta_y)
    ) / segment_length_sq
    clamped_projection = max(0.0, min(1.0, projection))
    closest_x = start_x + (clamped_projection * delta_x)
    closest_y = start_y + (clamped_projection * delta_y)
    return ((point_x - closest_x) ** 2) + ((point_y - closest_y) ** 2)


def _point_to_polyline_distance_sq(
    point: tuple[float, float],
    polyline_points: tuple[tuple[float, float], ...],
) -> float | None:
    if len(polyline_points) < 2:
        return None

    best_distance_sq: float | None = None
    for start_point, end_point in zip(polyline_points, polyline_points[1:]):
        distance_sq = _point_to_segment_distance_sq(point, start_point, end_point)
        if best_distance_sq is None or distance_sq < best_distance_sq:
            best_distance_sq = distance_sq
    return best_distance_sq


def _polyline_midpoint(points: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    if not points:
        return (0.0, 0.0)
    if len(points) == 1:
        return points[0]

    segment_lengths = [
        dist(start_point, end_point)
        for start_point, end_point in zip(points, points[1:])
    ]
    total_length = sum(segment_lengths)
    if total_length <= 0:
        return points[0]

    target_length = total_length / 2
    traversed_length = 0.0
    for (start_x, start_y), (end_x, end_y), segment_length in zip(points, points[1:], segment_lengths):
        if traversed_length + segment_length < target_length:
            traversed_length += segment_length
            continue
        if segment_length == 0:
            return (start_x, start_y)
        ratio = (target_length - traversed_length) / segment_length
        return (
            start_x + ((end_x - start_x) * ratio),
            start_y + ((end_y - start_y) * ratio),
        )

    return points[-1]


def _format_track_distance(distance_meters: int) -> str:
    if distance_meters < 1000:
        return f'{distance_meters:,} m'
    distance_km = distance_meters / 1000
    formatted_km = f'{distance_km:,.1f}'.rstrip('0').rstrip('.')
    return f'{formatted_km} km'


def _travel_time_seconds(distance_meters: int | float) -> int:
    return max(0, round(float(distance_meters) / MINECART_SPEED_MPS))


def _format_travel_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f'{seconds}s'
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes < 60:
        if remaining_seconds == 0:
            return f'{minutes}m'
        return f'{minutes}m {remaining_seconds}s'
    hours, remaining_minutes = divmod(minutes, 60)
    if remaining_minutes == 0:
        return f'{hours}h'
    return f'{hours}h {remaining_minutes}m'


def _format_travel_time_for_distance(distance_meters: int | float) -> str:
    return _format_travel_time(_travel_time_seconds(distance_meters))


def _format_distance_and_time(distance_meters: int | float) -> str:
    rounded_distance = round(float(distance_meters))
    return (
        f'{_format_track_distance(rounded_distance)} / '
        f'{_format_travel_time_for_distance(rounded_distance)}'
    )


def _planning_radius_distance() -> float:
    blackport = _blackport_stop()
    return max(
        (dist(stop.coordinates, blackport.coordinates) for stop in METRO_STOPS if stop.is_connected),
        default=0.0,
    )


def _is_within_planning_radius(stop: MetroStop, planning_radius: float) -> bool:
    blackport = _blackport_stop()
    return dist(stop.coordinates, blackport.coordinates) <= planning_radius + 1e-9


def _line_distance_between_stops(line_name: str, start_var: str, end_var: str) -> int:
    return _polyline_distance(_line_segment_plot_points(line_name, start_var, end_var))


def _route_step_color(step: RouteStep) -> str:
    if step.kind == 'ride' and step.line_name is not None:
        return LINE_COLORS[step.line_name]
    if step.kind == 'walk':
        return WALK_ROUTE_COLOR
    if step.kind == 'fly':
        return FLY_ROUTE_COLOR
    if step.kind == 'connector':
        return CONNECTOR_ROUTE_COLOR
    return ROUTE_HIGHLIGHT_OUTLINE


def _world_map_mode_labels() -> list[str]:
    try:
        from worldgen.modes import WORLDGEN_MODES
    except Exception:
        return ['Local Worldgen', 'LAN Surface', 'LAN Y=40']
    return [mode.label for mode in WORLDGEN_MODES.values()]


def _world_map_mode_label(mode_key: str | None) -> str:
    try:
        from worldgen.modes import worldgen_mode
    except Exception:
        return 'Local Worldgen'
    return worldgen_mode(mode_key).label


def _world_map_mode_key_for_label(label: str | None) -> str:
    try:
        from worldgen.modes import worldgen_mode_key_for_label
    except Exception:
        return 'local_seed_surface'
    return worldgen_mode_key_for_label(label)


def _world_map_cached_status_text(mode_key: str | None = None) -> str:
    try:
        from worldgen.cache import load_world_cache
        from worldgen.config import load_config
        from worldgen.generator import BedrockWorldGenerator
        from worldgen.modes import worldgen_mode
    except Exception as exc:
        return f'World map backend unavailable.\n{exc}'

    try:
        config = load_config()
        mode = worldgen_mode(mode_key)
        generator = BedrockWorldGenerator(config)
        mode_paths = generator.paths_for_mode(mode.key)
        cache_record = load_world_cache(config.paths.world_cache_path)
    except Exception as exc:
        return f'World map status unavailable.\n{exc}'

    lines = [f'World map cache - {mode.label}']
    if mode.is_lan:
        lines.append(f'LAN: {"enabled" if config.lan.enabled else "disabled"}')
        lines.append(f'World: {config.lan.world_name}')
        lines.append(f'Server: {config.lan.host}:{config.lan.port}')
        packet_cache_status = 'ready' if mode_paths.headless_chunk_packet_path.exists() else 'not loaded yet'
        lines.append(f'Packet cache: {packet_cache_status}')
        render_plan_status = 'ready' if mode_paths.render_plan_path.exists() else 'not written yet'
        lines.append(f'Render plan: {render_plan_status}')
        render_image_status = 'ready' if mode_paths.render_image_path.exists() else 'not rendered yet'
        lines.append(f'Rendered map: {render_image_status}')
        render_summary = _world_map_render_cache_summary_text(mode_paths.render_cache_path)
        if render_summary:
            lines.extend(render_summary)
        lines.append('Load and render run only when clicked.')
        return '\n'.join(lines)

    if cache_record is None:
        lines.append('No cached world yet.')
    else:
        world_path = Path(cache_record.world_path)
        expected_world_path = config.paths.data_dir / 'worlds' / config.world.level_name
        if not world_path.exists() and expected_world_path.exists():
            world_path = expected_world_path
            world_status = 'ready at current project path'
        else:
            world_status = 'ready' if world_path.exists() else 'missing on disk'
        lines.append(f'Cached world: {world_status}')
        lines.append(f'Prepared: {cache_record.prepared_at}')
        lines.append(f'World: {world_path}')

    render_plan_path = mode_paths.render_plan_path
    render_plan_status = 'ready' if render_plan_path.exists() else 'not written yet'
    lines.append(f'Render plan: {render_plan_status}')
    render_image_status = 'ready' if mode_paths.render_image_path.exists() else 'not rendered yet'
    lines.append(f'Rendered map: {render_image_status}')
    render_summary = _world_map_render_cache_summary_text(mode_paths.render_cache_path)
    if render_summary:
        lines.extend(render_summary)
    lines.append('Generate and render run only when clicked.')
    return '\n'.join(lines)


def _world_map_live_status_text(mode_key: str | None = None) -> str:
    from worldgen.cache import load_world_cache
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator
    from worldgen.modes import worldgen_mode

    config = load_config()
    mode = worldgen_mode(mode_key)
    generator = BedrockWorldGenerator(config)
    mode_paths = generator.paths_for_mode(mode.key)

    if mode.is_lan:
        lines = [
            f'World map status - {mode.label}',
            f'Docker: {"available" if generator.status().docker_available else "not found"}',
            f'LAN: {"enabled" if config.lan.enabled else "disabled"}',
            f'World: {config.lan.world_name}',
            f'Server: {config.lan.host}:{config.lan.port}',
            f'Packet cache: {"exists" if mode_paths.headless_chunk_packet_path.exists() else "not loaded yet"}',
            f'Render plan: {"exists" if mode_paths.render_plan_path.exists() else "not written yet"}',
            f'Rendered map: {"exists" if mode_paths.render_image_path.exists() else "not rendered yet"}',
        ]
        render_summary = _world_map_render_cache_summary_text(mode_paths.render_cache_path)
        if render_summary:
            lines.extend(render_summary)
        return '\n'.join(lines)

    status = generator.status()
    cache_record = load_world_cache(config.paths.world_cache_path)
    lines = [
        f'World map status - {mode.label}',
        f'Docker: {"available" if status.docker_available else "not found"}',
        f'Container: {_world_map_service_status_label(status.service_running)}',
        f'Expected world: {"exists" if status.expected_world_exists else "not found"}',
    ]
    if status.cached_world_path is None:
        lines.append('Cached world: none')
    else:
        if status.cached_world_exists:
            cached_status = 'exists'
        elif status.expected_world_exists:
            cached_status = 'stale; expected world exists'
        else:
            cached_status = 'missing'
        lines.append(f'Cached world: {cached_status}')
        if cache_record is not None:
            lines.append(f'Prepared: {cache_record.prepared_at}')
    lines.append(f'Render plan: {"exists" if mode_paths.render_plan_path.exists() else "not written yet"}')
    lines.append(f'Rendered map: {"exists" if mode_paths.render_image_path.exists() else "not rendered yet"}')
    render_summary = _world_map_render_cache_summary_text(mode_paths.render_cache_path)
    if render_summary:
        lines.extend(render_summary)
    return '\n'.join(lines)


def _world_map_render_cache_summary_text(render_cache_path: Path) -> list[str]:
    if not render_cache_path.exists():
        return []
    try:
        payload = json.loads(render_cache_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return ['Render cache: unreadable']
    colored_pixels = payload.get('colored_pixels')
    total_pixels = payload.get('total_pixels')
    chunk_columns_read = payload.get('chunk_columns_read')
    chunk_columns_requested = payload.get('chunk_columns_requested')
    colored_min_x = payload.get('colored_min_x')
    colored_max_x = payload.get('colored_max_x')
    colored_min_z = payload.get('colored_min_z')
    colored_max_z = payload.get('colored_max_z')
    generated_at = payload.get('generated_at')
    render_style = payload.get('render_style')
    fixed_y = payload.get('fixed_y')
    unfinished_point_count = payload.get('unfinished_point_count')
    unfinished_group_count = payload.get('unfinished_group_count')
    unfinished_points_path = payload.get('unfinished_points_path')
    lines = []
    if generated_at:
        lines.append(f'Rendered: {generated_at}')
    if render_style == 'fixed_y' and isinstance(fixed_y, int):
        lines.append(f'Render style: y={fixed_y}')
    if isinstance(colored_pixels, int) and isinstance(total_pixels, int):
        lines.append(_world_map_completion_text_from_payload(payload))
        lines.append(f'Colored pixels: {colored_pixels}/{total_pixels}')
    if isinstance(unfinished_point_count, int) and isinstance(unfinished_group_count, int):
        lines.append(f'Unfinished points: {unfinished_point_count}')
        lines.append(f'Unfinished point groups: {unfinished_group_count}')
    if isinstance(unfinished_points_path, str) and unfinished_points_path:
        lines.append(f'Unfinished point report: {unfinished_points_path}')
    if isinstance(chunk_columns_read, int) and isinstance(chunk_columns_requested, int):
        lines.append(f'Chunk columns: {chunk_columns_read}/{chunk_columns_requested}')
    if all(
        isinstance(value, int)
        for value in (colored_min_x, colored_max_x, colored_min_z, colored_max_z)
    ):
        lines.append(
            f'Visible render bounds: x {colored_min_x}..{colored_max_x}, '
            f'z {colored_min_z}..{colored_max_z}'
        )
    return lines


def _world_map_completion_text(
    colored_pixels: int,
    total_pixels: int,
) -> str:
    if total_pixels <= 0:
        return 'Map completed: unknown'
    completed_percent = (colored_pixels / total_pixels) * 100
    return f'Map completed: {completed_percent:.2f}%'


def _world_map_completion_text_from_payload(payload: dict[str, object]) -> str:
    colored_pixels = payload.get('colored_pixels')
    total_pixels = payload.get('total_pixels')
    if not isinstance(colored_pixels, int) or not isinstance(total_pixels, int):
        return 'Map completed: unknown'
    return _world_map_completion_text(colored_pixels, total_pixels)


def _world_map_visible_render_bounds_from_payload(
    payload: dict[str, object],
) -> tuple[int, int, int, int] | None:
    colored_min_x_value = payload.get('colored_min_x')
    colored_max_x_value = payload.get('colored_max_x')
    colored_min_z_value = payload.get('colored_min_z')
    colored_max_z_value = payload.get('colored_max_z')
    if (
        isinstance(colored_min_x_value, int)
        and isinstance(colored_max_x_value, int)
        and isinstance(colored_min_z_value, int)
        and isinstance(colored_max_z_value, int)
        and colored_min_x_value <= colored_max_x_value
        and colored_min_z_value <= colored_max_z_value
    ):
        return (
            colored_min_x_value,
            colored_max_x_value,
            colored_min_z_value,
            colored_max_z_value,
        )

    try:
        return (
            _render_cache_int(payload, 'min_x'),
            _render_cache_int(payload, 'max_x'),
            _render_cache_int(payload, 'min_z'),
            _render_cache_int(payload, 'max_z'),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _world_map_preview_bounds(
    payload: dict[str, object],
    prefix: str,
) -> tuple[int, int, int, int] | None:
    min_x_value = payload.get(f'{prefix}_min_x')
    max_x_value = payload.get(f'{prefix}_max_x')
    min_z_value = payload.get(f'{prefix}_min_z')
    max_z_value = payload.get(f'{prefix}_max_z')
    if not isinstance(min_x_value, int):
        return None
    if not isinstance(max_x_value, int):
        return None
    if not isinstance(min_z_value, int):
        return None
    if not isinstance(max_z_value, int):
        return None
    min_x = min_x_value
    max_x = max_x_value
    min_z = min_z_value
    max_z = max_z_value
    if min_x > max_x or min_z > max_z:
        return None
    return (min_x, max_x, min_z, max_z)


def _world_map_active_target_from_text(message: str) -> tuple[int, int] | None:
    match = re.search(
        r'\b(?:active|current|loaded|rendered)?\s*target(?:\s+square)?\s*:\s*(-?\d+)\s*,\s*(-?\d+)',
        message,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _post_world_map_active_target_progress(
    progress_callback: Callable[[str, bool], None] | None,
    status_label: str,
    target: tuple[int, int],
) -> None:
    if progress_callback is None:
        return
    progress_callback(
        (
            f'{status_label}.\n\n'
            f'Active target: {target[0]},{target[1]}\n'
            'The outlined box on the map is the target square being fetched.'
        ),
        False,
    )


def _world_map_completion_text_from_result(result: Any) -> str:
    payload = {
        'colored_pixels': result.colored_pixels,
        'total_pixels': result.total_pixels,
    }
    return _world_map_completion_text_from_payload(payload)


def _render_cache_int(payload: dict[str, object], key: str) -> int:
    value = payload[key]
    if not isinstance(value, (int, float, str)):
        raise TypeError(f'Render metadata value is not numeric: {key}')
    return int(value)


def _limit_world_map_alpha(value: int) -> int:
    return min(value, WORLD_MAP_RENDER_ALPHA)


def _world_map_service_status_label(service_running: bool | None) -> str:
    if service_running is True:
        return 'running'
    if service_running is False:
        return 'stopped'
    return 'unknown'


def _world_map_generate_world_text() -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator

    config = load_config()
    generator = BedrockWorldGenerator(config)
    world_path, render_plan_path = generator.prepare()
    return '\n'.join(
        (
            'World generation ready.',
            f'World: {world_path}',
            f'Render plan: {render_plan_path}',
            'Use Load Chunks to visit the render area without opening Minecraft.',
        )
    )


def _world_map_load_chunks_text(mode_key: str | None = None) -> str:
    return _world_map_load_chunks_text_with_progress(mode_key)


def _world_map_load_chunks_text_with_progress(
    mode_key: str | None = None,
    progress_callback: Callable[[str, bool], None] | None = None,
) -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator
    from worldgen.modes import worldgen_mode

    config = load_config()
    mode = worldgen_mode(mode_key)
    generator = BedrockWorldGenerator(config)
    result = (
        generator.load_lan_chunks_headless(mode.key)
        if mode.is_lan
        else generator.load_chunks_headless(
            active_target_callback=(
                lambda target: _post_world_map_active_target_progress(
                    progress_callback,
                    f'Loading {mode.label} chunks',
                    target,
                )
                if progress_callback is not None
                else None
            )
        )
    )
    return _world_map_load_chunks_result_text(mode, result)


def _world_map_load_chunks_result_text(mode: Any, result: Any) -> str:
    lines = [
        f'{mode.label} chunk loading finished.',
        f'World: {result.world_path}',
        f'Metadata: {result.result_path}',
        f'Chunks received: {result.chunks_received}',
        f'Chunk columns received: {result.unique_chunk_columns}',
        f'Load attempts: {result.load_attempts}',
    ]
    if mode.is_lan:
        lines.append('LAN path used client packet data only; no server console commands were sent.')
    else:
        lines.extend(
            (
                f'Teleport commands sent: {result.teleport_commands_sent}',
                f'Teleport targets this pass: {", ".join(result.teleport_targets) or "none"}',
                (
                    f'Next teleport target: {result.teleport_next_index + 1}/{result.teleport_target_count}'
                    if result.teleport_target_count > 0
                    else 'Next teleport target: none'
                ),
                f'Server stopped: {"yes" if result.server_stopped else "no"}',
            )
        )
    if result.returncode != 0:
        lines.append(f'Loader exited with code {result.returncode}.')
    if result.output:
        lines.append('')
        lines.append(result.output)
    lines.append('')
    lines.append(f'Use Render Map next to draw {mode.label}.')
    return '\n'.join(lines)


def _world_map_render_text(mode_key: str | None = None) -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator
    from worldgen.modes import worldgen_mode

    config = load_config()
    mode = worldgen_mode(mode_key)
    generator = BedrockWorldGenerator(config)
    result = generator.render_map(mode_key=mode.key)
    lines = [
        f'Rendered {mode.label}.',
        f'Image: {result.image_path}',
        f'Metadata: {result.metadata_path}',
        f'Uncolored block report: {result.uncolored_blocks_report_path}',
        _world_map_completion_text_from_result(result),
        f'Colored pixels: {result.colored_pixels}/{result.total_pixels}',
        f'Unfinished points: {result.unfinished_point_count}',
        f'Unfinished point groups: {result.unfinished_group_count}',
        f'Unfinished point report: {result.unfinished_points_path}',
        f'Uncolored block occurrences: {result.uncolored_block_occurrences}',
        f'Chunk columns read: {result.chunk_columns_read}/{result.chunk_columns_requested}',
    ]
    if result.colored_min_x is not None:
        lines.append(
            f'Visible render bounds: x {result.colored_min_x}..{result.colored_max_x}, '
            f'z {result.colored_min_z}..{result.colored_max_z}'
        )
    if result.chunk_columns_read == 0:
        lines.append('No generated chunk columns were found in the requested render area yet.')
        lines.append(f'Use Load Chunks for {mode.label}, then render again.')
    if result.subchunk_decode_errors:
        lines.append(f'Subchunk decode errors: {result.subchunk_decode_errors}')
    return '\n'.join(lines)


def _world_map_load_and_render_text(
    mode_key: str,
    progress_callback: Callable[[str, bool], None] | None = None,
) -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator
    from worldgen.modes import worldgen_mode

    config = load_config()
    mode = worldgen_mode(mode_key)
    generator = BedrockWorldGenerator(config)
    result = (
        generator.load_lan_chunks_headless(mode.key)
        if mode.is_lan
        else generator.load_chunks_headless(
            active_target_callback=(
                lambda target: _post_world_map_active_target_progress(
                    progress_callback,
                    f'Loading {mode.label} chunks',
                    target,
                )
                if progress_callback is not None
                else None
            )
        )
    )
    load_message = _world_map_load_chunks_result_text(mode, result)
    if result.returncode != 0 or result.unique_chunk_columns == 0:
        return '\n'.join(
            (
                load_message,
                '',
                f'Render skipped because {mode.label} did not load any chunk columns.',
            )
        )
    render_message = _world_map_render_text(mode_key)
    return f'{load_message}\n\n{render_message}'


def _world_map_auto_fill_step_text_for_generator(
    generator: Any,
    *,
    step_number: int | None = None,
    progress_callback: Callable[[str, bool], None] | None = None,
) -> str:
    step_label = f'Auto fill step {step_number}' if step_number is not None else 'Auto fill step'
    cached_pixel_result = generator.render_cached_blank_pixel_batch()
    if cached_pixel_result is not None and cached_pixel_result.colored_pixels_added > 0:
        render_result = cached_pixel_result.render_result
        lines = [
            f'{step_label} finished.',
            'Rendered cached blank pixels in a spiral around Blackport.',
            f'World: {render_result.world_path}',
            f'Pixels checked: {cached_pixel_result.scanned_pixels}',
            f'Blank pixels sampled: {cached_pixel_result.blank_pixels_selected}',
            f'Pixels filled this step: {cached_pixel_result.colored_pixels_added}',
            f'Image: {render_result.image_path}',
            f'Uncolored block report: {render_result.uncolored_blocks_report_path}',
            _world_map_completion_text_from_result(render_result),
            f'Colored pixels: {render_result.colored_pixels}/{render_result.total_pixels}',
            f'Unfinished points: {render_result.unfinished_point_count}',
            f'Unfinished point groups: {render_result.unfinished_group_count}',
            f'Unfinished point report: {render_result.unfinished_points_path}',
            f'Uncolored block occurrences: {render_result.uncolored_block_occurrences}',
            (
                f'Chunk columns read: '
                f'{render_result.chunk_columns_read}/{render_result.chunk_columns_requested}'
            ),
        ]
        if render_result.colored_min_x is not None:
            lines.append(
                f'Visible render bounds: x {render_result.colored_min_x}..{render_result.colored_max_x}, '
                f'z {render_result.colored_min_z}..{render_result.colored_max_z}'
            )
        if render_result.subchunk_decode_errors:
            lines.append(f'Subchunk decode errors: {render_result.subchunk_decode_errors}')
        lines.append('Auto Fill can continue with the next spiral batch.')
        return '\n'.join(lines)

    if cached_pixel_result is not None and progress_callback is not None:
        progress_callback(
            (
                f'{step_label} checked a spiral batch around Blackport.\n\n'
                f'Pixels checked: {cached_pixel_result.scanned_pixels}\n'
                f'Blank pixels sampled: {cached_pixel_result.blank_pixels_selected}\n'
                'No cached pixels could be filled from that batch, so Auto Fill is loading more terrain.'
            ),
            True,
        )

    before_load_colored_pixels = (
        generator.cached_colored_pixel_count()
        if hasattr(generator, 'cached_colored_pixel_count')
        else 0
    )

    def post_active_target_progress(target: tuple[int, int]) -> None:
        _post_world_map_active_target_progress(
            progress_callback,
            f'{step_label} is loading a target square',
            target,
        )

    load_results = [
        generator.load_chunks_headless(
            stop_after=True,
            restart_existing=False,
            active_target_callback=post_active_target_progress,
        )
        for _index in range(WORLD_MAP_AUTO_LOAD_PASSES)
    ]
    render_target: tuple[int, int] | None = None

    def post_render_progress(new_pixels_added: int) -> None:
        if progress_callback is None:
            return
        progress_callback(
            (
                f'{step_label} is painting newly loaded pixels.\n\n'
                f'Pixels filled so far in this render: {new_pixels_added}\n'
                'The map preview will update when this render pass finishes.'
            ),
            False,
        )

    for load_result in load_results:
        for target_text in load_result.teleport_targets:
            try:
                target_x_text, target_z_text = target_text.split(',', 1)
                render_target = (int(target_x_text), int(target_z_text))
                break
            except ValueError:
                continue
        if render_target is not None:
            break

    if render_target is not None and hasattr(generator, 'render_loaded_target_map'):
        render_result = generator.render_loaded_target_map(
            render_target,
            image_progress_callback=post_render_progress,
            image_progress_interval=WORLD_MAP_RENDER_PROGRESS_PIXEL_INTERVAL,
        )
    else:
        render_result = generator.render_map(
            image_progress_callback=post_render_progress,
            image_progress_interval=WORLD_MAP_RENDER_PROGRESS_PIXEL_INTERVAL,
        )
    colored_pixels_added = max(0, render_result.colored_pixels - before_load_colored_pixels)
    if render_target is not None and hasattr(generator, 'mark_headless_loader_target_progress'):
        generator.mark_headless_loader_target_progress(
            render_target,
            pixels_added=colored_pixels_added,
        )
    lines = [
        f'{step_label} finished.',
        f'World: {render_result.world_path}',
        f'Load passes: {len(load_results)}',
    ]
    if render_target is not None:
        lines.append(f'Rendered target square: {render_target[0]},{render_target[1]}')
    for index, load_result in enumerate(load_results, start=1):
        lines.extend(
            (
                f'Pass {index}: {load_result.chunks_received} chunks, '
                f'{load_result.unique_chunk_columns} chunk columns',
                f'Pass {index} target pool: {load_result.teleport_target_count} blank-pixel targets',
                f'Pass {index} targets: {", ".join(load_result.teleport_targets) or "none"}',
            )
        )
        if load_result.returncode != 0:
            lines.append(f'Pass {index} loader exited with code {load_result.returncode}.')
            if load_result.output:
                lines.append(load_result.output)

    lines.extend(
        (
            'Rendered world map.',
            f'Image: {render_result.image_path}',
            f'Uncolored block report: {render_result.uncolored_blocks_report_path}',
            _world_map_completion_text_from_result(render_result),
            f'Pixels filled this step: {colored_pixels_added}',
            f'Colored pixels: {render_result.colored_pixels}/{render_result.total_pixels}',
            f'Unfinished points: {render_result.unfinished_point_count}',
            f'Unfinished point groups: {render_result.unfinished_group_count}',
            f'Unfinished point report: {render_result.unfinished_points_path}',
            f'Uncolored block occurrences: {render_result.uncolored_block_occurrences}',
            (
                f'Chunk columns read: '
                f'{render_result.chunk_columns_read}/{render_result.chunk_columns_requested}'
            ),
        )
    )
    if render_result.colored_min_x is not None:
        lines.append(
            f'Visible render bounds: x {render_result.colored_min_x}..{render_result.colored_max_x}, '
            f'z {render_result.colored_min_z}..{render_result.colored_max_z}'
        )
    if render_result.subchunk_decode_errors:
        lines.append(f'Subchunk decode errors: {render_result.subchunk_decode_errors}')
    if colored_pixels_added == 0 and any(load_result.chunks_received > 0 for load_result in load_results):
        lines.append(
            'Chunks loaded, but this target did not add newly colored pixels. '
            'Auto Fill will mark this target as stalled and continue with the next blank target.'
        )
    lines.append('Auto Fill can continue with the next step.')
    return '\n'.join(lines)


def _world_map_auto_fill_step_text() -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator

    config = load_config()
    generator = BedrockWorldGenerator(config)
    return _world_map_auto_fill_step_text_for_generator(generator)


def _world_map_auto_fill_until_stopped_text(
    stop_event: threading.Event,
    progress_callback: Callable[[str, bool], None] | None = None,
) -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator

    config = load_config()
    generator = BedrockWorldGenerator(config)
    step_count = 0
    last_step_message = ''

    while True:
        if generator.render_area_coverage_complete():
            completion_message = 'Auto fill coverage is complete for the requested render area.'
            if last_step_message:
                return '\n'.join((completion_message, '', last_step_message))
            return completion_message

        if stop_event.is_set() and step_count > 0:
            break

        step_count += 1
        if progress_callback is not None:
            progress_callback(
                f'Auto filling world map...\n\n'
                f'Running step {step_count}. Stop will happen after this step finishes.',
                False,
            )

        last_step_message = _world_map_auto_fill_step_text_for_generator(
            generator,
            step_number=step_count,
            progress_callback=progress_callback,
        )
        if stop_event.is_set():
            break

        if progress_callback is not None:
            progress_callback(
                f'{last_step_message}\n\n'
                'Still running. Press Stop Auto Fill to stop after the current step.',
                True,
            )

    return '\n'.join(
        (
            f'Auto fill stopped after {step_count} step{"s" if step_count != 1 else ""}.',
            'The stop request waited for the active step to finish.',
            '',
            last_step_message,
        )
    )


def _world_map_stop_world_text() -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator

    config = load_config()
    generator = BedrockWorldGenerator(config)
    generator.stop()
    return 'Bedrock worldgen container stopped.'


def _world_map_repair_db_text() -> str:
    from worldgen.config import load_config
    from worldgen.generator import BedrockWorldGenerator

    config = load_config()
    generator = BedrockWorldGenerator(config)
    result = generator.repair_world_db()
    return '\n'.join(
        (
            'Built a repaired Bedrock LevelDB copy.',
            f'DB: {result.db_path}',
            f'Backup: {result.backup_path}',
            f'Repaired copy: {result.repaired_copy_path}',
            'The live Bedrock DB was left in place.',
        )
    )


def _missing_station_tasks(stop: MetroStop) -> list[str]:
    tasks: list[str] = []
    if not stop.has_name:
        tasks.append('name')
    if not stop.has_connector:
        tasks.append('façade')
    if not stop.has_full_station:
        tasks.append('station')
    if stop.station_entry_coordinates is None:
        tasks.append('station entrance')
    if not stop.has_walking_paths:
        tasks.append('paths')
    if not stop.city_limit_node_keys:
        tasks.append('city limits')
    if not stop.is_connected and _priority_alignment_count(stop.var) > 0:
        tasks.append('alignment')
    if SHOW_RAILWAY_FINISHING_UI and stop.is_connected and not stop.has_finished_railway:
        tasks.append('finished railway')
    if _station_signs_available(stop) and not stop.has_signs:
        tasks.append('signs')
    if stop.is_connected and _station_max_chime_count(stop) > 0 and not _station_has_required_chimes(stop):
        tasks.append('chimes')
    return tasks


def _priority_task_phrase(task: str) -> str:
    return PRIORITY_TASK_PHRASES.get(task, task)


def _join_priority_tasks(tasks: list[str]) -> str:
    if not tasks:
        return ''
    task_phrases = [_priority_task_phrase(task) for task in tasks]
    if len(tasks) == 1:
        return task_phrases[0]
    if len(tasks) == 2:
        return f'{task_phrases[0]} and {task_phrases[1]}'
    return f"{', '.join(task_phrases[:-1])}, and {task_phrases[-1]}"


def _priority_route_summary(route_distance: int, transfer_count: int) -> str:
    change_word = 'line change' if transfer_count == 1 else 'line changes'
    return f'route {_format_track_distance(route_distance)}, {transfer_count} {change_word}'


def _active_alignment_reminders_for_stop(stop_var: str) -> tuple[AlignmentReminder, ...]:
    return tuple(
        reminder
        for reminder in _alignment_reminders_for_stop(stop_var)
        if not reminder.is_aligned
    )


def _priority_alignment_count(stop_var: str) -> int:
    return len(_active_alignment_reminders_for_stop(stop_var))


def _priority_work_weight(stop: MetroStop) -> int:
    return sum(CONNECTED_TASK_WEIGHTS[task] for task in _missing_station_tasks(stop))


def _priority_work_summary(stop: MetroStop) -> str:
    parts: list[str] = []
    missing_tasks = _missing_station_tasks(stop)
    if missing_tasks:
        parts.append(f'needs {_join_priority_tasks(missing_tasks)}')

    if not parts:
        return 'no remaining station work'
    return '; '.join(parts)


def _priority_junction_count(stop: MetroStop) -> int:
    return len(STOP_LINE_NAMES[stop.var]) if len(STOP_LINE_NAMES[stop.var]) > 1 else 0


def _station_has_priority_progress(stop: MetroStop) -> bool:
    return any((
        stop.has_name,
        stop.has_connector,
        stop.has_full_station,
        stop.station_entry_coordinates is not None,
        stop.has_walking_paths,
        bool(stop.city_limit_node_keys),
        stop.is_connected,
        stop.has_finished_railway,
        stop.has_signs,
        bool(stop.chime_directions),
    ))


def _priority_frontier_route_details(
    stop: MetroStop,
    route_costs: dict[str, tuple[int, int]],
) -> tuple[tuple[int | str, ...], int, int] | None:
    best_candidate: tuple[tuple[int | str, ...], int, int] | None = None

    for line_name in STOP_LINE_NAMES[stop.var]:
        candidate = _unconnected_line_priority_candidate_with_frontier(stop, line_name)
        if candidate is None:
            continue
        candidate_sort_key, _detail, frontier_var = candidate
        frontier_route_cost = route_costs.get(frontier_var)
        if frontier_route_cost is None:
            continue

        frontier_distance, frontier_transfer_count = frontier_route_cost
        sort_key: tuple[int | str, ...] = (
            *candidate_sort_key,
            frontier_distance,
            frontier_transfer_count,
            line_name.lower(),
        )
        candidate_entry = (sort_key, frontier_distance, frontier_transfer_count)
        if best_candidate is None or candidate_entry[0] < best_candidate[0]:
            best_candidate = candidate_entry

    return best_candidate


def _priority_list_entries(
    origin_key: str,
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
) -> list[tuple[str, str]]:
    route_costs = _route_costs_from_endpoint_key(
        origin_key,
        allow_connector=allow_connector,
        allow_walk=allow_walk,
    )
    entries: list[tuple[tuple[int | str, ...], str, str]] = []

    for stop in METRO_STOPS:
        missing_tasks = _missing_station_tasks(stop)
        has_progress = _station_has_priority_progress(stop)
        junction_count = _priority_junction_count(stop)
        alignment_count = _priority_alignment_count(stop.var)

        distance_value: int | None = None
        route_distance = 0
        transfer_count = 0
        route_rank = 0
        next_on_line = False

        if stop.is_connected:
            route_cost = route_costs.get(stop.var)
            if route_cost is None:
                route_rank = 2
            else:
                route_distance, transfer_count = route_cost
        else:
            frontier_details = _priority_frontier_route_details(stop, route_costs)
            if frontier_details is not None:
                _frontier_sort_key, frontier_distance, frontier_transfer_count = frontier_details
                distance_value = frontier_distance
                route_distance = frontier_distance
                transfer_count = frontier_transfer_count
                next_on_line = True
                route_rank = 1
            else:
                route_rank = 3

        if not (next_on_line or (missing_tasks and has_progress)):
            continue

        fragments: list[str] = []
        if distance_value is not None:
            fragments.append(_format_track_distance(distance_value))
        if junction_count > 1:
            fragments.append(f'{junction_count}-line junction')
        if missing_tasks:
            fragments.append(f'needs {_join_priority_tasks(missing_tasks)}')
        if not fragments:
            continue

        complexity_score = (
            (PRIORITY_DISTANCE_WEIGHT if distance_value is not None else 0)
            + (PRIORITY_JUNCTION_WEIGHT if junction_count > 1 else 0)
            + sum(CONNECTED_TASK_WEIGHTS[task] for task in missing_tasks)
        )
        sort_key: tuple[int | str, ...] = (
            complexity_score,
            len(fragments),
            route_rank,
            route_distance,
            transfer_count,
            junction_count,
            alignment_count,
            stop.lbl.lower(),
        )
        entries.append(
            (
                sort_key,
                stop.var,
                f'{_display_label(stop.lbl)}: {", ".join(fragments)}',
            )
        )

    entries.sort(key=lambda item: item[0])
    return [(stop_var, text) for _sort_key, stop_var, text in entries]


def _csv_bool(value: bool) -> str:
    return 'TRUE' if value else 'FALSE'


def _priority_checklist_csv_value(stop: MetroStop, task_name: str) -> str:
    if task_name == 'name':
        return _csv_bool(stop.has_name)
    if task_name == 'façade':
        return _csv_bool(stop.has_connector)
    if task_name == 'station':
        return _csv_bool(stop.has_full_station)
    if task_name == 'station entrance':
        return _csv_bool(stop.station_entry_coordinates is not None)
    if task_name == 'paths':
        return _csv_bool(stop.has_walking_paths)
    if task_name == 'city limits':
        return _csv_bool(bool(stop.city_limit_node_keys))
    if task_name == 'connected':
        return _csv_bool(stop.is_connected)
    if task_name == 'alignment':
        if stop.is_connected:
            return ''
        return _csv_bool(_priority_alignment_count(stop.var) == 0)
    if task_name == 'finished railway':
        if not SHOW_RAILWAY_FINISHING_UI or not stop.is_connected:
            return ''
        return _csv_bool(stop.has_finished_railway)
    if task_name == 'signs':
        if not _station_signs_available(stop):
            return ''
        return _csv_bool(stop.has_signs)
    if task_name == 'chimes':
        if not stop.is_connected or _station_max_chime_count(stop) <= 0:
            return ''
        return _csv_bool(_station_has_required_chimes(stop))
    raise ValueError(f'Unknown priority checklist task: {task_name}')


def _priority_list_csv_fieldnames() -> list[str]:
    return [
        'Rank',
        'Station ID',
        'Station Name',
        'Lines',
        'Priority Note',
        *(label for label, _task_name in PRIORITY_CSV_CHECKLIST_COLUMNS),
    ]


def _priority_list_csv_rows(entries: list[tuple[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rank, (stop_var, priority_text) in enumerate(entries, start=1):
        stop = STOPS_BY_VAR.get(stop_var)
        if stop is None:
            continue
        row = {
            'Rank': str(rank),
            'Station ID': stop.var,
            'Station Name': _display_label(stop.lbl),
            'Lines': ', '.join(STOP_LINE_NAMES.get(stop.var, ())),
            'Priority Note': priority_text,
        }
        for label, task_name in PRIORITY_CSV_CHECKLIST_COLUMNS:
            row[label] = _priority_checklist_csv_value(stop, task_name)
        rows.append(row)
    return rows


def _write_priority_list_csv(entries: list[tuple[str, str]]) -> None:
    output = io.StringIO(newline='')
    fieldnames = _priority_list_csv_fieldnames()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    writer.writerows(_priority_list_csv_rows(entries))
    csv_text = output.getvalue()

    existing_text = ''
    if PRIORITY_LIST_CSV_PATH.exists():
        existing_text = PRIORITY_LIST_CSV_PATH.read_text(encoding='utf-8')
    if existing_text != csv_text:
        PRIORITY_LIST_CSV_PATH.write_text(csv_text, encoding='utf-8')


def _unconnected_line_priority_candidate_with_frontier(
    stop: MetroStop,
    line_name: str,
) -> tuple[tuple[int, int, int, int], str, str] | None:
    stop_vars = LINE_STOP_VARS[line_name]
    stop_index = stop_vars.index(stop.var)
    left_index = next(
        (
            index
            for index in range(stop_index - 1, -1, -1)
            if STOPS_BY_VAR[stop_vars[index]].is_connected
        ),
        None,
    )
    right_index = next(
        (
            index
            for index in range(stop_index + 1, len(stop_vars))
            if STOPS_BY_VAR[stop_vars[index]].is_connected
        ),
        None,
    )
    left_is_adjacent = left_index is not None and (stop_index - left_index) == 1
    right_is_adjacent = right_index is not None and (right_index - stop_index) == 1

    if not left_is_adjacent and not right_is_adjacent:
        return None

    if left_index is not None and right_index is not None:
        left_var = stop_vars[left_index]
        right_var = stop_vars[right_index]
        left_lbl = _display_label(STOPS_BY_VAR[left_var].lbl)
        right_lbl = _display_label(STOPS_BY_VAR[right_var].lbl)
        gap_size = right_index - left_index - 1
        left_steps = stop_index - left_index
        right_steps = right_index - stop_index
        if left_steps <= right_steps:
            frontier_var = left_var
            frontier_steps = left_steps
        else:
            frontier_var = right_var
            frontier_steps = right_steps
        frontier_distance = _line_distance_between_stops(line_name, frontier_var, stop.var)
        if gap_size == 1:
            detail = (
                f'{_display_label(stop.lbl)}: reconnects Line {line_name} '
                f'between {left_lbl} and {right_lbl}.'
            )
        else:
            nearer_frontier_lbl = left_lbl if left_steps <= right_steps else right_lbl
            detail = (
                f'{_display_label(stop.lbl)}: next step toward closing a {gap_size}-stop gap on '
                f'Line {line_name} between {left_lbl} and {right_lbl} from {nearer_frontier_lbl}.'
            )
        return ((0, gap_size, frontier_steps, frontier_distance), detail, frontier_var)

    frontier_index = left_index if left_index is not None else right_index
    if frontier_index is None:
        raise ValueError('frontier_index unexpectedly missing')
    frontier_var = stop_vars[frontier_index]
    frontier_steps = abs(stop_index - frontier_index)
    frontier_distance = _line_distance_between_stops(line_name, frontier_var, stop.var)
    frontier_lbl = _display_label(STOPS_BY_VAR[frontier_var].lbl)
    detail = f'{_display_label(stop.lbl)}: next on Line {line_name} after {frontier_lbl}.'
    return ((1, 10**6, frontier_steps, frontier_distance), detail, frontier_var)


def _unconnected_line_priority_candidate(
    stop: MetroStop,
    line_name: str,
) -> tuple[tuple[int, int, int, int], str] | None:
    candidate = _unconnected_line_priority_candidate_with_frontier(stop, line_name)
    if candidate is None:
        return None
    sort_key, detail, _frontier_var = candidate
    return (sort_key, detail)


def _frontier_unlock_preview(line_name: str, frontier_var: str) -> str:
    stop_vars = LINE_STOP_VARS[line_name]
    frontier_index = stop_vars.index(frontier_var)
    unlocked_labels: list[str] = []

    for neighbor_index in (frontier_index - 1, frontier_index + 1):
        if not (0 <= neighbor_index < len(stop_vars)):
            continue
        neighbor_var = stop_vars[neighbor_index]
        neighbor_stop = STOPS_BY_VAR[neighbor_var]
        if neighbor_stop.is_connected or neighbor_var == frontier_var:
            continue
        unlocked_labels.append(_display_label(neighbor_stop.lbl))

    if unlocked_labels:
        unique_labels = list(dict.fromkeys(unlocked_labels))
        if len(unique_labels) == 1:
            return f' Unlocks next: {unique_labels[0]}.'
        return f" Unlocks next: {', '.join(unique_labels[:-1])}, and {unique_labels[-1]}."

    left_connected = any(
        STOPS_BY_VAR[stop_vars[index]].is_connected
        for index in range(frontier_index - 1, -1, -1)
    )
    right_connected = any(
        STOPS_BY_VAR[stop_vars[index]].is_connected
        for index in range(frontier_index + 1, len(stop_vars))
    )
    if left_connected and right_connected:
        return ' Restores through-service across the current gap.'
    return ' Extends the connected frontier on this line.'


def _reachable_station_work_lines(
    origin_key: str,
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
) -> list[str]:
    route_costs = _route_costs_from_endpoint_key(
        origin_key,
        allow_connector=allow_connector,
        allow_walk=allow_walk,
    )
    items: list[tuple[tuple[int | str, ...], str]] = []

    for stop in METRO_STOPS:
        if not stop.is_connected:
            continue
        route_cost = route_costs.get(stop.var)
        if route_cost is None:
            continue

        work_weight = _priority_work_weight(stop)
        if work_weight <= 0:
            continue

        route_distance, transfer_count = route_cost
        sort_key: tuple[int | str, ...] = (
            work_weight,
            _priority_alignment_count(stop.var),
            route_distance,
            transfer_count,
            max(0, len(STOP_LINE_NAMES[stop.var]) - 1),
            stop.lbl.lower(),
        )
        items.append(
            (
                sort_key,
                f'{_display_label(stop.lbl)}: {_priority_work_summary(stop)}; '
                f'{_priority_route_summary(route_distance, transfer_count)}.',
            )
        )

    items.sort(key=lambda item: item[0])
    return [text for _sort_key, text in items]


def _reachable_frontier_build_lines(
    origin_key: str,
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
) -> list[str]:
    route_costs = _route_costs_from_endpoint_key(
        origin_key,
        allow_connector=allow_connector,
        allow_walk=allow_walk,
    )
    items: list[tuple[tuple[int | str, ...], str]] = []

    for stop in METRO_STOPS:
        if stop.is_connected:
            continue

        work_weight = _priority_work_weight(stop)
        alignment_count = _priority_alignment_count(stop.var)
        target_work_summary = _priority_work_summary(stop) if work_weight > 0 else 'track work only'

        candidate_items: list[tuple[tuple[int | str, ...], str]] = []
        for line_name in STOP_LINE_NAMES[stop.var]:
            candidate = _unconnected_line_priority_candidate_with_frontier(stop, line_name)
            if candidate is None:
                continue

            candidate_sort_key, _detail, frontier_var = candidate
            frontier_route_cost = route_costs.get(frontier_var)
            if frontier_route_cost is None:
                continue

            frontier_distance, frontier_transfer_count = frontier_route_cost
            sort_key: tuple[int | str, ...] = (
                *candidate_sort_key,
                work_weight,
                alignment_count,
                frontier_distance,
                frontier_transfer_count,
                stop.lbl.lower(),
                line_name.lower(),
            )
            target_label = _display_label(stop.lbl)
            frontier_label = _display_label(STOPS_BY_VAR[frontier_var].lbl)
            candidate_items.append(
                (
                sort_key,
                f'{target_label}: next frontier build on Line {line_name} from {frontier_label}; '
                f'{target_work_summary}; '
                f'{_priority_route_summary(frontier_distance, frontier_transfer_count)}.'
                f'{_frontier_unlock_preview(line_name, frontier_var)}',
                )
            )

        if candidate_items:
            items.append(min(candidate_items, key=lambda item: item[0]))

    items.sort(key=lambda item: item[0])
    return [text for _sort_key, text in items]


def _priority_list_text(
    origin_key: str,
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
) -> str:
    station_work_lines = _reachable_station_work_lines(
        origin_key,
        allow_connector=allow_connector,
        allow_walk=allow_walk,
    )
    frontier_build_lines = _reachable_frontier_build_lines(
        origin_key,
        allow_connector=allow_connector,
        allow_walk=allow_walk,
    )
    lines = ['1. Reachable Station Work']
    if station_work_lines:
        lines.extend(f'- {line}' for line in station_work_lines)
    else:
        lines.append('- Nothing in this category.')

    lines.extend(['', '2. Reachable Frontier Builds'])
    if frontier_build_lines:
        lines.extend(f'- {line}' for line in frontier_build_lines)
    else:
        lines.append('- Nothing in this category.')

    return '\n'.join(lines)


def _alignment_reminders_for_stop(stop_var: str) -> tuple[AlignmentReminder, ...]:
    return tuple(
        reminder
        for reminder in ALIGNMENT_REMINDERS
        if stop_var in reminder.included_stop_vars
    )


def _metro_segments_for_stop(stop_var: str) -> tuple[MetroLineSegment, ...]:
    segments: list[MetroLineSegment] = []
    for line_name in STOP_LINE_NAMES[stop_var]:
        stop_vars = LINE_STOP_VARS[line_name]
        stop_index = stop_vars.index(stop_var)
        if stop_index > 0:
            previous_var = stop_vars[stop_index - 1]
            segments.append(
                MetroLineSegment(
                    line_name=line_name,
                    start_var=previous_var,
                    end_var=stop_var,
                    specs=_line_segment_specs(line_name, previous_var, stop_var),
                )
            )
        if stop_index < len(stop_vars) - 1:
            next_var = stop_vars[stop_index + 1]
            segments.append(
                MetroLineSegment(
                    line_name=line_name,
                    start_var=stop_var,
                    end_var=next_var,
                    specs=_line_segment_specs(line_name, stop_var, next_var),
                )
            )
    return tuple(segments)


def _all_metro_segments() -> tuple[MetroLineSegment, ...]:
    segments: list[MetroLineSegment] = []
    for line_name, stop_vars in LINE_STOP_VARS.items():
        for start_var, end_var in zip(stop_vars, stop_vars[1:]):
            segments.append(
                MetroLineSegment(
                    line_name=line_name,
                    start_var=start_var,
                    end_var=end_var,
                    specs=_line_segment_specs(line_name, start_var, end_var),
                )
            )
    return tuple(segments)


def _metro_segment_key(segment: MetroLineSegment) -> tuple[str, str, str]:
    return (segment.line_name, segment.start_var, segment.end_var)


def _metro_segment_from_key(segment_key: tuple[str, str, str]) -> MetroLineSegment | None:
    line_name, start_var, end_var = segment_key
    stop_vars = LINE_STOP_VARS.get(line_name)
    if stop_vars is None:
        return None
    if start_var not in stop_vars or end_var not in stop_vars:
        return None
    if stop_vars.index(end_var) - stop_vars.index(start_var) != 1:
        return None
    return MetroLineSegment(
        line_name=line_name,
        start_var=start_var,
        end_var=end_var,
        specs=_line_segment_specs(line_name, start_var, end_var),
    )


def _line_frontier_entries() -> list[tuple[str, str | None]]:
    entries: list[tuple[str, str | None]] = []

    for line_name in sorted(LINE_STOP_VARS):
        stop_vars = LINE_STOP_VARS[line_name]
        connected_count = sum(STOPS_BY_VAR[stop_var].is_connected for stop_var in stop_vars)
        total_count = len(stop_vars)
        candidates: list[tuple[tuple[int, int, int, int], str, str]] = []

        for stop_var in stop_vars:
            stop = STOPS_BY_VAR[stop_var]
            if stop.is_connected:
                continue
            candidate = _unconnected_line_priority_candidate(stop, line_name)
            if candidate is None:
                continue
            sort_key, detail = candidate
            candidates.append((sort_key, stop.var, detail))

        if candidates:
            _sort_key, frontier_var, detail = min(candidates, key=lambda item: item[0])
            entries.append(
                (
                    f'Line {line_name} ({connected_count}/{total_count} connected): '
                    f'{detail}{_frontier_unlock_preview(line_name, frontier_var)}',
                    frontier_var,
                )
            )
            continue

        connected_incomplete = [
            stop
            for stop_var in stop_vars
            for stop in [STOPS_BY_VAR[stop_var]]
            if stop.is_connected and _missing_station_tasks(stop)
        ]
        if connected_count == total_count and connected_incomplete:
            next_station = min(
                connected_incomplete,
                key=lambda stop: (
                    sum(CONNECTED_TASK_WEIGHTS[task] for task in _missing_station_tasks(stop)),
                    stop.lbl.lower(),
                ),
            )
            entries.append(
                (
                    f'Line {line_name} ({connected_count}/{total_count} connected): '
                    f'track is connected; station work remains at '
                    f'{_display_label(next_station.lbl)}.',
                    next_station.var,
                )
            )
            continue

        if connected_count == total_count:
            continue

        if connected_count == 0:
            continue

        entries.append(
            (
                f'Line {line_name} ({connected_count}/{total_count} connected): no immediate next stop available yet.',
                None,
            )
        )

    return entries


def _frontier_highlight_segments() -> tuple[tuple[str, str, str], ...]:
    segments: list[tuple[str, str, str]] = []

    for line_name in sorted(LINE_STOP_VARS):
        candidates: list[tuple[tuple[int, int, int, int], str, str]] = []
        for stop_var in LINE_STOP_VARS[line_name]:
            stop = STOPS_BY_VAR[stop_var]
            if stop.is_connected:
                continue
            candidate = _unconnected_line_priority_candidate_with_frontier(stop, line_name)
            if candidate is None:
                continue
            sort_key, _detail, frontier_var = candidate
            candidates.append((sort_key, frontier_var, stop.var))

        if not candidates:
            continue

        _sort_key, frontier_var, target_var = min(candidates, key=lambda item: item[0])
        segments.append((line_name, frontier_var, target_var))

    return tuple(segments)


def _frontier_highlight_stop_vars() -> frozenset[str]:
    return frozenset(target_var for _line_name, _frontier_var, target_var in _frontier_highlight_segments())


def _frontier_summary_text() -> str:
    return '\n'.join(f'- {text}' for text, _frontier_var in _line_frontier_entries())


def _frontier_stop_vars() -> tuple[str, ...]:
    return tuple(
        frontier_var
        for _text, frontier_var in _line_frontier_entries()
        if frontier_var is not None
    )


def _checklist_ratio_line(
    label: str,
    completed: int,
    total: int,
    *,
    hide_when_total_zero: bool = False,
) -> str | None:
    if total <= 0 and hide_when_total_zero:
        return None
    if total > 0 and completed >= total:
        return None
    return f'{label}: {completed}/{total}'


def _world_map_checklist_completion_ratio() -> float | None:
    try:
        from worldgen.config import load_config
        from worldgen.generator import BedrockWorldGenerator

        config = load_config()
        mode_paths = BedrockWorldGenerator(config).paths_for_mode()
        payload = json.loads(mode_paths.render_cache_path.read_text(encoding='utf-8'))
    except Exception:
        return None

    colored_pixels = payload.get('colored_pixels')
    total_pixels = payload.get('total_pixels')
    if not isinstance(colored_pixels, int) or not isinstance(total_pixels, int) or total_pixels <= 0:
        return None
    return colored_pixels / total_pixels


def _world_map_checklist_completion_text() -> str:
    ratio = _world_map_checklist_completion_ratio()
    if ratio is None:
        return 'Map Completed: --.--%'
    return f'Map Completed: {ratio * 100:.2f}%'


def _world_map_checklist_completion_line() -> str | None:
    ratio = _world_map_checklist_completion_ratio()
    if ratio is None:
        return 'Map Completed: --.--%'
    if ratio >= 1.0:
        return None
    return f'Map Completed: {ratio * 100:.2f}%'


def _village_checklist_lines() -> tuple[str, ...]:
    total_villages = len(METRO_STOPS)
    walking_paths_count = sum(stop.has_walking_paths for stop in METRO_STOPS)
    boundary_count = sum(bool(stop.city_limit_node_keys) for stop in METRO_STOPS)

    lines = [
        _checklist_ratio_line(
            'Paths',
            walking_paths_count,
            total_villages,
            hide_when_total_zero=True,
        ),
        _checklist_ratio_line(
            'City Limits',
            boundary_count,
            total_villages,
            hide_when_total_zero=True,
        ),
    ]
    return tuple(line for line in lines if line is not None)


def _station_progress_summary_text() -> str:
    total_stations = len(METRO_STOPS)
    connected_stops = tuple(stop for stop in METRO_STOPS if stop.is_connected)
    connected_station_count = len(connected_stops)
    named_count = sum(stop.has_name for stop in METRO_STOPS)
    connector_count = sum(stop.has_connector for stop in METRO_STOPS)
    full_station_count = sum(stop.has_full_station for stop in METRO_STOPS)
    station_entry_count = sum(stop.station_entry_coordinates is not None for stop in METRO_STOPS)
    connected_count = sum(stop.is_connected for stop in METRO_STOPS)
    signs_available_stops = tuple(stop for stop in METRO_STOPS if _station_signs_available(stop))
    signs_count = sum(stop.has_signs for stop in signs_available_stops)
    required_chime_count = sum(_station_max_chime_count(stop) for stop in connected_stops)
    completed_chime_count = sum(_station_completed_chime_count(stop) for stop in connected_stops)
    lines = [
        _checklist_ratio_line('Named', named_count, total_stations, hide_when_total_zero=True),
        _checklist_ratio_line('Façades', connector_count, total_stations, hide_when_total_zero=True),
        _checklist_ratio_line('Stations', full_station_count, total_stations, hide_when_total_zero=True),
        _checklist_ratio_line(
            'Station Entrances',
            station_entry_count,
            total_stations,
            hide_when_total_zero=True,
        ),
        _checklist_ratio_line('Connected', connected_count, total_stations, hide_when_total_zero=True),
        _checklist_ratio_line(
            'Signs',
            signs_count,
            len(signs_available_stops),
            hide_when_total_zero=True,
        ),
        _checklist_ratio_line(
            'Chimes',
            completed_chime_count,
            required_chime_count,
            hide_when_total_zero=True,
        ),
        *_village_checklist_lines(),
        _world_map_checklist_completion_line(),
    ]
    return '\n'.join(line for line in lines if line is not None)


def _line_anchor_index_map(line_name: str) -> dict[str, int]:
    anchor_indices: dict[str, int] = {}
    for index, spec in enumerate(LINE_PATH_SPECS[line_name]):
        if spec.x_var == spec.y_var and spec.x_var in LINE_STOP_VARS[line_name]:
            anchor_indices.setdefault(spec.x_var, index)
    return anchor_indices


def _line_segment_plot_points(
    line_name: str,
    start_var: str,
    end_var: str,
) -> tuple[tuple[int, int], ...]:
    anchor_indices = _line_anchor_index_map(line_name)
    start_index = anchor_indices[start_var]
    end_index = anchor_indices[end_var]

    if start_index <= end_index:
        return tuple(
            spec.plot_coordinates
            for spec in LINE_PATH_SPECS[line_name][start_index:end_index + 1]
        )

    return tuple(
        reversed(
            tuple(
                spec.plot_coordinates
                for spec in LINE_PATH_SPECS[line_name][end_index:start_index + 1]
            )
        )
    )


def _polyline_distance_float(points: Sequence[tuple[float, float]]) -> float:
    return sum(dist(start_point, end_point) for start_point, end_point in zip(points, points[1:]))


def _line_cumulative_distances(line_name: str) -> tuple[float, ...]:
    points = METRO_LINE_PLOT_PATHS[line_name]
    cumulative_distances = [0.0]
    for start_point, end_point in zip(points, points[1:]):
        cumulative_distances.append(cumulative_distances[-1] + dist(start_point, end_point))
    return tuple(cumulative_distances)


def _line_anchor_distances(line_name: str) -> dict[str, float]:
    cumulative_distances = _line_cumulative_distances(line_name)
    return {
        stop_var: cumulative_distances[index]
        for stop_var, index in _line_anchor_index_map(line_name).items()
    }


def _point_location_on_polyline(
    point: tuple[float, float],
    polyline_points: Sequence[tuple[float, float]],
    *,
    tolerance: float,
) -> tuple[float, tuple[float, float]] | None:
    if len(polyline_points) < 2:
        return None

    best_location: tuple[float, float, tuple[float, float]] | None = None
    traversed_distance = 0.0
    for start_point, end_point in zip(polyline_points, polyline_points[1:]):
        start_x, start_y = start_point
        end_x, end_y = end_point
        delta_x = end_x - start_x
        delta_y = end_y - start_y
        segment_length_sq = (delta_x * delta_x) + (delta_y * delta_y)
        if segment_length_sq == 0:
            distance_sq = ((point[0] - start_x) ** 2) + ((point[1] - start_y) ** 2)
            closest_point = (float(start_x), float(start_y))
            location_distance = traversed_distance
        else:
            projection = (
                ((point[0] - start_x) * delta_x) + ((point[1] - start_y) * delta_y)
            ) / segment_length_sq
            clamped_projection = max(0.0, min(1.0, projection))
            closest_point = (
                start_x + (clamped_projection * delta_x),
                start_y + (clamped_projection * delta_y),
            )
            distance_sq = ((point[0] - closest_point[0]) ** 2) + ((point[1] - closest_point[1]) ** 2)
            location_distance = traversed_distance + (segment_length_sq ** 0.5 * clamped_projection)

        if best_location is None or distance_sq < best_location[0]:
            best_location = (distance_sq, location_distance, closest_point)
        traversed_distance += segment_length_sq ** 0.5

    if best_location is None or best_location[0] > tolerance * tolerance:
        return None
    return (best_location[1], best_location[2])


def _line_finish_location_for_coordinates(
    line_name: str,
    coordinates: tuple[int, int],
) -> tuple[float, tuple[float, float]] | None:
    if line_name not in METRO_LINE_PLOT_PATHS:
        return None
    for stop_var in LINE_STOP_VARS[line_name]:
        stop = STOPS_BY_VAR[stop_var]
        if stop.coordinates != coordinates:
            continue
        anchor_index = _line_anchor_index_map(line_name).get(stop_var)
        if anchor_index is None:
            continue
        return (
            _line_cumulative_distances(line_name)[anchor_index],
            METRO_LINE_PLOT_PATHS[line_name][anchor_index],
        )

    plot_point = (float(coordinates[0]), float(-coordinates[1]))
    return _point_location_on_polyline(
        plot_point,
        METRO_LINE_PLOT_PATHS[line_name],
        tolerance=FINISHED_RAILWAY_COORDINATE_TOLERANCE,
    )


def _railway_segment_is_connected(segment: MetroLineSegment) -> bool:
    return segment.start_stop.is_connected and segment.end_stop.is_connected


def _metro_segment_style(segment: MetroLineSegment) -> tuple[int, tuple[int, int] | None]:
    if _railway_segment_is_connected(segment):
        return (4, None)
    return (UNCONNECTED_RAILWAY_WIDTH, UNCONNECTED_RAILWAY_DASH)


def _normalize_chime_direction(value: object) -> ChimeDirection | None:
    normalized_value = str(value).strip().lower()
    if normalized_value in CHIME_DIRECTIONS:
        return cast(ChimeDirection, normalized_value)
    return None


def _normalized_chime_directions(values: object) -> tuple[ChimeDirection, ...]:
    if not isinstance(values, list | tuple | set | frozenset):
        return ()

    seen_directions: set[ChimeDirection] = set()
    directions: list[ChimeDirection] = []
    for value in values:
        direction = _normalize_chime_direction(value)
        if direction is None or direction in seen_directions:
            continue
        seen_directions.add(direction)
        directions.append(direction)

    return tuple(
        direction
        for direction in CHIME_DIRECTIONS
        if direction in seen_directions
    )


def _plot_point_to_coordinates(point: tuple[float, float]) -> tuple[float, float]:
    return (point[0], -point[1])


def _cardinal_direction_from_delta(delta_x: float, delta_y: float) -> ChimeDirection | None:
    if delta_x == 0 and delta_y == 0:
        return None
    if abs(delta_x) >= abs(delta_y):
        return 'east' if delta_x > 0 else 'west'
    return 'south' if delta_y > 0 else 'north'


def _metro_segment_outlet_direction(
    segment: MetroLineSegment,
    stop_var: str,
) -> ChimeDirection | None:
    if stop_var not in (segment.start_var, segment.end_var):
        return None

    segment_points: Sequence[tuple[int, int]] = segment.plot_points
    if segment.end_var == stop_var:
        segment_points = tuple(reversed(segment_points))

    for first_point, second_point in zip(segment_points, segment_points[1:]):
        first_x, first_y = _plot_point_to_coordinates(first_point)
        second_x, second_y = _plot_point_to_coordinates(second_point)
        direction = _cardinal_direction_from_delta(second_x - first_x, second_y - first_y)
        if direction is not None:
            return direction
    return None


def _station_chime_outlet_directions(stop_var: str) -> tuple[ChimeDirection, ...]:
    directions: set[ChimeDirection] = set()
    for segment in _metro_segments_for_stop(stop_var):
        if not _railway_segment_is_connected(segment):
            continue
        direction = _metro_segment_outlet_direction(segment, stop_var)
        if direction is not None:
            directions.add(direction)
    return tuple(direction for direction in CHIME_DIRECTIONS if direction in directions)


def _station_max_chime_count(stop: MetroStop) -> int:
    return len(_station_chime_outlet_directions(stop.var))


def _station_completed_chime_directions(stop: MetroStop) -> tuple[ChimeDirection, ...]:
    required_directions = set(_station_chime_outlet_directions(stop.var))
    return tuple(
        direction
        for direction in CHIME_DIRECTIONS
        if direction in required_directions and direction in stop.chime_directions
    )


def _station_completed_chime_count(stop: MetroStop) -> int:
    return len(_station_completed_chime_directions(stop))


def _station_has_required_chimes(stop: MetroStop) -> bool:
    max_chime_count = _station_max_chime_count(stop)
    return max_chime_count == 0 or _station_completed_chime_count(stop) >= max_chime_count


def _station_signs_available(stop: MetroStop) -> bool:
    return stop.has_full_station or stop.is_connected


def _station_checkpoint_total(stop: MetroStop) -> int:
    base_total = 5
    if stop.is_connected:
        if SHOW_RAILWAY_FINISHING_UI:
            base_total += 1
    if _station_signs_available(stop):
        base_total += 1
    if stop.is_connected and _station_max_chime_count(stop) > 0:
        base_total += 1
    return base_total


def _station_checkpoint_count(stop: MetroStop) -> int:
    completed_count = sum((
        stop.has_name,
        stop.has_connector,
        stop.has_full_station,
        stop.has_walking_paths,
        stop.is_connected,
    ))
    if stop.is_connected:
        if SHOW_RAILWAY_FINISHING_UI and stop.has_finished_railway:
            completed_count += 1
    if _station_signs_available(stop) and stop.has_signs:
        completed_count += 1
    if stop.is_connected and _station_max_chime_count(stop) > 0 and _station_has_required_chimes(stop):
        completed_count += 1
    return completed_count


def _line_has_connected_railway(line_name: str) -> bool:
    return any(
        STOPS_BY_VAR[start_var].is_connected and STOPS_BY_VAR[end_var].is_connected
        for start_var, end_var in zip(LINE_STOP_VARS[line_name], LINE_STOP_VARS[line_name][1:])
    )


def _line_finish_origin_options(line_name: str) -> tuple[str, ...]:
    connected_stop_vars = tuple(
        stop_var
        for stop_var in LINE_STOP_VARS[line_name]
        if STOPS_BY_VAR[stop_var].is_connected
    )
    if not connected_stop_vars:
        return ()
    if len(connected_stop_vars) == 1:
        return (connected_stop_vars[0],)
    return (connected_stop_vars[0], connected_stop_vars[-1])


def _railway_finish_line_names() -> tuple[str, ...]:
    return tuple(
        line_name
        for line_name in sorted(LINE_STOP_VARS)
        if _line_unfinished_connected_intervals(line_name)
    )


def _line_finish_origin_var(line_name: str) -> str:
    stop_vars = LINE_STOP_VARS[line_name]
    origin_options = _line_finish_origin_options(line_name)
    origin_override = RAILWAY_FINISH_ORIGINS.get(line_name)
    if origin_override in origin_options:
        return origin_override
    if line_name in FINISHED_RAILWAY_MAJOR_LINES and BLACKPORT_VAR in origin_options:
        return BLACKPORT_VAR
    if not origin_options:
        return stop_vars[0]

    route_costs = _route_costs_from_endpoint_key(BLACKPORT_VAR, allow_connector=True, allow_walk=True)
    reachable_stop_vars = [
        stop_var
        for stop_var in origin_options
        if stop_var in route_costs
    ]
    if reachable_stop_vars:
        return min(
            reachable_stop_vars,
            key=lambda stop_var: (
                route_costs[stop_var][0],
                route_costs[stop_var][1],
                stop_vars.index(stop_var),
                STOPS_BY_VAR[stop_var].lbl.lower(),
            ),
        )
    return origin_options[0]


def _line_finish_origin_distance(line_name: str) -> float:
    origin_var = _line_finish_origin_var(line_name)
    anchor_distances = _line_anchor_distances(line_name)
    if origin_var in anchor_distances:
        return anchor_distances[origin_var]
    origin_stop = STOPS_BY_VAR[origin_var]
    origin_location = _line_finish_location_for_coordinates(line_name, origin_stop.coordinates)
    if origin_location is None:
        return 0.0
    return origin_location[0]


def _line_finish_progress_point(line_name: str) -> tuple[int, int] | None:
    progress_point = RAILWAY_FINISH_PROGRESS.get(line_name)
    if progress_point is None:
        return None
    return (int(progress_point['x']), int(progress_point['y']))


def _line_finish_progress_location(line_name: str) -> tuple[float, tuple[float, float]] | None:
    progress_point = _line_finish_progress_point(line_name)
    if progress_point is None:
        return None
    return _line_finish_location_for_coordinates(line_name, progress_point)


def _line_finished_interval(line_name: str) -> tuple[float, float] | None:
    progress_location = _line_finish_progress_location(line_name)
    if progress_location is None:
        return None

    origin_distance = _line_finish_origin_distance(line_name)
    progress_distance = progress_location[0]
    return (
        min(origin_distance, progress_distance),
        max(origin_distance, progress_distance),
    )


def _merge_intervals(intervals: Sequence[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    sorted_intervals = sorted(
        (
            (min(start_distance, end_distance), max(start_distance, end_distance))
            for start_distance, end_distance in intervals
            if abs(end_distance - start_distance) > 1e-6
        ),
        key=lambda interval: interval[0],
    )
    merged_intervals: list[tuple[float, float]] = []
    for start_distance, end_distance in sorted_intervals:
        if not merged_intervals or start_distance > merged_intervals[-1][1] + 1e-6:
            merged_intervals.append((start_distance, end_distance))
            continue
        previous_start, previous_end = merged_intervals[-1]
        merged_intervals[-1] = (previous_start, max(previous_end, end_distance))
    return tuple(merged_intervals)


def _line_base_connected_intervals(line_name: str) -> tuple[tuple[float, float], ...]:
    anchor_distances = _line_anchor_distances(line_name)
    intervals: list[tuple[float, float]] = []
    for start_var, end_var in zip(LINE_STOP_VARS[line_name], LINE_STOP_VARS[line_name][1:]):
        if not STOPS_BY_VAR[start_var].is_connected or not STOPS_BY_VAR[end_var].is_connected:
            continue
        start_distance = anchor_distances[start_var]
        end_distance = anchor_distances[end_var]
        intervals.append((min(start_distance, end_distance), max(start_distance, end_distance)))
    return _merge_intervals(intervals)


def _line_connected_intervals(line_name: str) -> tuple[tuple[float, float], ...]:
    intervals = list(_line_base_connected_intervals(line_name))
    finished_interval = _line_finished_interval(line_name)
    if finished_interval is not None:
        intervals.append(finished_interval)
    return _merge_intervals(intervals)


def _interval_length(interval: tuple[float, float]) -> float:
    return max(0.0, interval[1] - interval[0])


def _interval_overlap_length(first: tuple[float, float], second: tuple[float, float]) -> float:
    return max(0.0, min(first[1], second[1]) - max(first[0], second[0]))


def _line_connected_length(line_name: str) -> float:
    return sum(_interval_length(interval) for interval in _line_connected_intervals(line_name))


def _line_finished_connected_length(line_name: str) -> float:
    finished_interval = _line_finished_interval(line_name)
    if finished_interval is None:
        return 0.0
    return sum(
        _interval_overlap_length(connected_interval, finished_interval)
        for connected_interval in _line_connected_intervals(line_name)
    )


def _line_finish_percent(line_name: str) -> float:
    connected_length = _line_connected_length(line_name)
    if connected_length <= 0:
        return 0.0
    return min(100.0, (_line_finished_connected_length(line_name) / connected_length) * 100)


def _subtract_interval(
    interval: tuple[float, float],
    remove_interval: tuple[float, float] | None,
) -> tuple[tuple[float, float], ...]:
    if remove_interval is None:
        return (interval,)

    start_distance, end_distance = interval
    remove_start, remove_end = remove_interval
    if remove_end <= start_distance or remove_start >= end_distance:
        return (interval,)

    remaining: list[tuple[float, float]] = []
    if remove_start > start_distance:
        remaining.append((start_distance, min(remove_start, end_distance)))
    if remove_end < end_distance:
        remaining.append((max(remove_end, start_distance), end_distance))
    return tuple(
        remaining_interval
        for remaining_interval in remaining
        if _interval_length(remaining_interval) > 1e-6
    )


def _line_unfinished_connected_intervals(line_name: str) -> tuple[tuple[float, float], ...]:
    finished_interval = _line_finished_interval(line_name)
    unfinished_intervals: list[tuple[float, float]] = []
    for connected_interval in _line_connected_intervals(line_name):
        unfinished_intervals.extend(_subtract_interval(connected_interval, finished_interval))
    return tuple(unfinished_intervals)


def _railway_finish_unfinished_plot_points() -> tuple[tuple[float, float], ...]:
    points: list[tuple[float, float]] = []
    for line_name in _railway_finish_line_names():
        for start_distance, end_distance in _line_unfinished_connected_intervals(line_name):
            points.extend(
                _polyline_slice_between_distances(
                    METRO_LINE_PLOT_PATHS[line_name],
                    start_distance,
                    end_distance,
                )
            )
    return tuple(points)


def _interpolated_point(
    start_point: tuple[float, float],
    end_point: tuple[float, float],
    ratio: float,
) -> tuple[float, float]:
    return (
        start_point[0] + ((end_point[0] - start_point[0]) * ratio),
        start_point[1] + ((end_point[1] - start_point[1]) * ratio),
    )


def _append_polyline_point(
    points: list[tuple[float, float]],
    point: tuple[float, float],
) -> None:
    if points and dist(points[-1], point) <= 1e-9:
        return
    points.append(point)


def _polyline_slice_between_distances(
    polyline_points: Sequence[tuple[float, float]],
    start_distance: float,
    end_distance: float,
) -> tuple[tuple[float, float], ...]:
    if len(polyline_points) < 2 or end_distance <= start_distance:
        return ()

    sliced_points: list[tuple[float, float]] = []
    traversed_distance = 0.0
    for start_point, end_point in zip(polyline_points, polyline_points[1:]):
        segment_length = dist(start_point, end_point)
        segment_start = traversed_distance
        segment_end = traversed_distance + segment_length
        traversed_distance = segment_end

        if segment_length <= 0:
            continue
        if segment_end < start_distance:
            continue
        if segment_start > end_distance:
            break

        slice_start = max(start_distance, segment_start)
        slice_end = min(end_distance, segment_end)
        if slice_end <= slice_start:
            continue

        start_ratio = (slice_start - segment_start) / segment_length
        end_ratio = (slice_end - segment_start) / segment_length
        _append_polyline_point(sliced_points, _interpolated_point(start_point, end_point, start_ratio))
        _append_polyline_point(sliced_points, _interpolated_point(start_point, end_point, end_ratio))

    return tuple(sliced_points)


def _line_finish_stop_vars_to_mark(
    line_name: str,
    coordinates: tuple[int, int],
) -> tuple[str, ...]:
    finish_location = _line_finish_location_for_coordinates(line_name, coordinates)
    if finish_location is None:
        raise ValueError(f'That coordinate is not on Line {line_name}. Try another coordinate.')

    origin_distance = _line_finish_origin_distance(line_name)
    finish_distance = finish_location[0]
    start_distance = min(origin_distance, finish_distance)
    end_distance = max(origin_distance, finish_distance)
    anchor_distances = _line_anchor_distances(line_name)
    return tuple(
        stop_var
        for stop_var in LINE_STOP_VARS[line_name]
        if (
            start_distance - 1e-6 <= anchor_distances[stop_var] <= end_distance + 1e-6
        )
    )


def _railway_finish_progress_summary_text() -> str:
    line_names = tuple(
        line_name
        for line_name in sorted(LINE_STOP_VARS)
        if _line_connected_length(line_name) > 0
    )
    if not line_names:
        return 'No connected railway segments yet.'
    return '\n'.join(
        (
            f'Line {line_name}: {_line_finish_percent(line_name):.0f}% '
            f'({_format_track_distance(round(_line_finished_connected_length(line_name)))} / '
            f'{_format_track_distance(round(_line_connected_length(line_name)))})'
        )
        for line_name in line_names
    )


def _line_total_distance(line_name: str) -> int:
    return _polyline_distance(METRO_LINE_PLOT_PATHS[line_name])


def _line_connected_distance(line_name: str) -> int:
    return round(_line_connected_length(line_name))


def _line_leg_distance(line_name: str, start_var: str, end_var: str) -> int:
    return _polyline_distance(_line_segment_plot_points(line_name, start_var, end_var))


def _line_summary_text(line_name: str) -> str:
    if line_name not in LINE_STOP_VARS:
        return 'Choose a line.'

    color = LINE_COLORS.get(line_name, '#ffffff')
    total_distance = _line_total_distance(line_name)
    connected_distance = _line_connected_distance(line_name)
    stop_vars = LINE_STOP_VARS[line_name]
    lines = [
        f'Line {line_name}',
        f'Color: {color}',
        f'Total: {_format_distance_and_time(total_distance)}',
        f'Connected: {_format_distance_and_time(connected_distance)}',
        '',
        'Stations',
    ]
    if not stop_vars:
        lines.append('No stations on this line.')
        return '\n'.join(lines)

    for index, stop_var in enumerate(stop_vars, start=1):
        stop = STOPS_BY_VAR[stop_var]
        entry_text = (
            f'entry ({stop.station_entry_coordinates[0]}, {stop.station_entry_coordinates[1]})'
            if stop.station_entry_coordinates is not None
            else 'entry not set'
        )
        lines.append(
            f'{index}. {_display_label(stop.lbl)}  '
            f'coords ({stop.x}, {stop.y}); {entry_text}'
        )
        if index < len(stop_vars):
            next_var = stop_vars[index]
            leg_distance = _line_leg_distance(line_name, stop_var, next_var)
            connected_marker = (
                'connected'
                if STOPS_BY_VAR[stop_var].is_connected and STOPS_BY_VAR[next_var].is_connected
                else 'planned'
            )
            lines.append(
                f'   -> {_format_distance_and_time(leg_distance)} '
                f'[{connected_marker}]'
            )
    return '\n'.join(lines)


def _normalize_line_color(color_text: str) -> str:
    normalized = color_text.strip()
    if not normalized.startswith('#'):
        normalized = f'#{normalized}'
    if re.fullmatch(r'#[0-9a-fA-F]{3}', normalized):
        return '#' + ''.join(char * 2 for char in normalized[1:]).lower()
    if re.fullmatch(r'#[0-9a-fA-F]{6}', normalized):
        return normalized.lower()
    raise ValueError('Line color must be a hex color like #2f80ed.')


def _normalize_line_name(line_name: str) -> str:
    normalized = line_name.strip().upper()
    if not re.fullmatch(r'[A-Z]', normalized):
        raise ValueError('Line names must be a single letter.')
    return normalized


def _auto_station_label_from_payload(
    payload: MetroNetworkPayload,
    stop_var: str,
) -> str:
    membership = _station_line_membership_from_payload(payload, stop_var)
    if not membership:
        return UNASSOCIATED_STATION_LABEL
    if len(membership) > 1:
        line_key = ''.join(membership)
        matching_stop_vars = [
            str(stop_record['var'])
            for stop_record in payload['stops']
            if _station_line_membership_from_payload(payload, str(stop_record['var'])) == membership
        ]
        if len(matching_stop_vars) <= 1:
            return line_key
        suffix = _station_var_suffix(stop_var)
        return f'{line_key}_{suffix}' if suffix else f'{line_key}_{sorted(matching_stop_vars).index(stop_var) + 1}'
    line_name = membership[0]
    try:
        stop_index = [str(var) for var in payload['line_stop_vars'][line_name]].index(stop_var) + 1
    except (KeyError, ValueError):
        stop_index = 1
    return f'{line_name}_{stop_index}'


def _railway_finish_line_status_text(line_name: str) -> str:
    if line_name not in LINE_STOP_VARS:
        return 'Choose an unfinished connected line.'

    origin_var = _line_finish_origin_var(line_name)
    origin_stop = STOPS_BY_VAR[origin_var]
    origin_options = _line_finish_origin_options(line_name)
    switch_text = ''
    if len(origin_options) > 1:
        next_origin_var = origin_options[(origin_options.index(origin_var) + 1) % len(origin_options)]
        switch_text = f'Switch target: {_display_label(STOPS_BY_VAR[next_origin_var].lbl)}'
    block_label = WOOL_COLORS.get(line_name, '').strip() or 'not set'
    progress_point = _line_finish_progress_point(line_name)
    finish_text = 'Finish point: none yet'
    if progress_point is not None:
        finish_text = f'Finish point: ({progress_point[0]}, {progress_point[1]})'

    lines = [
        f'Line {line_name}: {_line_finish_percent(line_name):.0f}% finished',
        f'Origin: {_display_label(origin_stop.lbl)}',
        f'Block label: {block_label}',
        finish_text,
    ]
    if switch_text:
        lines.append(switch_text)
    return '\n'.join(lines)


def _next_unfinished_railway_finish_line(after_line_name: str | None = None) -> str | None:
    line_names = list(_railway_finish_line_names())
    if not line_names:
        return None

    if after_line_name in line_names:
        start_index = line_names.index(cast(str, after_line_name)) + 1
        candidate_line_names = line_names[start_index:] + line_names[:start_index]
    else:
        candidate_line_names = line_names

    return candidate_line_names[0]


def _graph_nodes_for_endpoint(
    graph: dict[RouteNode, list[RouteEdge]],
    endpoint_key: str,
) -> list[RouteNode]:
    if endpoint_key.startswith(CITY_LIMIT_ENDPOINT_PREFIX):
        stop_var = _city_limit_stop_var_from_key(endpoint_key)
        stop = STOPS_BY_VAR.get(stop_var)
        if stop is None:
            return []
        city_nodes: list[RouteNode] = []
        for node_key in stop.city_limit_node_keys:
            city_nodes.extend(node for node in graph if node[0] == node_key)
        return sorted(dict.fromkeys(city_nodes))
    stop = STOPS_BY_VAR.get(endpoint_key)
    if stop is not None and (stop.var, STATION_CITY_PATH_CONTEXT) in graph:
        return [(stop.var, STATION_CITY_PATH_CONTEXT)]
    return _standard_graph_nodes_for_endpoint(graph, endpoint_key)


def _standard_graph_nodes_for_endpoint(
    graph: dict[RouteNode, list[RouteEdge]],
    endpoint_key: str,
) -> list[RouteNode]:
    return sorted(
        node
        for node in graph
        if node[0] == endpoint_key and node[1] != STATION_CITY_PATH_CONTEXT
    )


def _point_on_world_segment(
    point: tuple[int, int],
    segment_start: tuple[int, int],
    segment_end: tuple[int, int],
) -> bool:
    point_x, point_y = point
    start_x, start_y = segment_start
    end_x, end_y = segment_end
    cross_product = ((point_y - start_y) * (end_x - start_x)) - ((point_x - start_x) * (end_y - start_y))
    if cross_product != 0:
        return False
    return (
        min(start_x, end_x) <= point_x <= max(start_x, end_x)
        and min(start_y, end_y) <= point_y <= max(start_y, end_y)
    )


def _point_in_world_polygon(point: tuple[int, int], polygon: Sequence[tuple[int, int]]) -> bool:
    if len(polygon) < 3:
        return False

    inside = False
    point_x, point_y = point
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if _point_on_world_segment(point, (previous_x, previous_y), (current_x, current_y)):
            return True
        if (current_y > point_y) != (previous_y > point_y):
            intersection_x = previous_x + ((point_y - previous_y) * (current_x - previous_x) / (current_y - previous_y))
            if point_x < intersection_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _extra_edge_world_points(extra_edge: ExtraEdgeDefinition) -> tuple[tuple[int, int], ...]:
    if extra_edge.path_points:
        return extra_edge.path_points
    return (
        extra_edge.from_endpoint.coordinates,
        extra_edge.to_endpoint.coordinates,
    )


def _closest_point_on_world_segment(
    anchor: tuple[int, int],
    segment_start: tuple[int, int],
    segment_end: tuple[int, int],
) -> tuple[tuple[int, int], float]:
    anchor_x, anchor_y = anchor
    start_x, start_y = segment_start
    end_x, end_y = segment_end
    delta_x = end_x - start_x
    delta_y = end_y - start_y
    segment_length_squared = (delta_x * delta_x) + (delta_y * delta_y)
    if segment_length_squared <= 0:
        return (segment_start, 0.0)
    ratio = (((anchor_x - start_x) * delta_x) + ((anchor_y - start_y) * delta_y)) / segment_length_squared
    ratio = max(0.0, min(1.0, ratio))
    return (
        (
            round(start_x + (delta_x * ratio)),
            round(start_y + (delta_y * ratio)),
        ),
        ratio,
    )


def _rounded_world_polyline(points: Iterable[tuple[float, float]]) -> tuple[tuple[int, int], ...]:
    rounded_points: list[tuple[int, int]] = []
    for point_x, point_y in points:
        rounded_point = (round(point_x), round(point_y))
        if rounded_points and rounded_points[-1] == rounded_point:
            continue
        rounded_points.append(rounded_point)
    return tuple(rounded_points)


def _world_points_to_plot_points(points: Sequence[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    return tuple((point_x, -point_y) for point_x, point_y in points)


def _city_path_anchor_candidate_for_edge(
    stop: MetroStop,
    city_limit_points: Sequence[tuple[int, int]],
    extra_edge: ExtraEdgeDefinition,
) -> tuple[float, float, tuple[int, int]] | None:
    if extra_edge.kind != 'walk':
        return None

    world_points = _extra_edge_world_points(extra_edge)
    if len(world_points) < 2:
        return None

    anchor_coordinates = stop.walking_coordinates
    candidates: list[tuple[float, float, tuple[int, int]]] = []
    traversed_distance = 0.0
    for start_point, end_point in zip(world_points, world_points[1:]):
        segment_length = dist(start_point, end_point)
        for candidate_point, ratio in (
            (start_point, 0.0),
            (end_point, 1.0),
            _closest_point_on_world_segment(anchor_coordinates, start_point, end_point),
        ):
            if not _point_in_world_polygon(candidate_point, city_limit_points):
                continue
            candidate_distance = dist(anchor_coordinates, candidate_point)
            candidate_along_distance = traversed_distance + (segment_length * ratio)
            candidates.append((candidate_distance, candidate_along_distance, candidate_point))
        traversed_distance += segment_length

    if not candidates:
        return None
    return min(candidates, key=lambda candidate: (candidate[0], candidate[1], candidate[2]))


def _route_edge_from_city_anchor(
    anchor_node: RouteNode,
    target_node: RouteNode,
    *,
    distance: int,
    label: str,
    world_points: Sequence[tuple[int, int]],
) -> RouteEdge:
    return RouteEdge(
        start=anchor_node,
        end=target_node,
        distance=distance,
        transfer_count=0,
        kind='walk',
        label=label,
        path_points=_world_points_to_plot_points(world_points),
    )


def _append_station_city_path_anchors(graph: dict[RouteNode, list[RouteEdge]]) -> None:
    for stop in METRO_STOPS:
        if not stop.has_walking_paths:
            continue
        city_limit_points = _city_limit_world_points(stop)
        if len(city_limit_points) < 3:
            continue

        best_candidate: tuple[float, float, tuple[int, int], ExtraEdgeDefinition] | None = None
        for extra_edge in EXTRA_EDGES:
            if extra_edge.kind != 'walk':
                continue
            if not _standard_graph_nodes_for_endpoint(graph, extra_edge.from_endpoint.key):
                continue
            if not _standard_graph_nodes_for_endpoint(graph, extra_edge.to_endpoint.key):
                continue
            edge_candidate = _city_path_anchor_candidate_for_edge(stop, city_limit_points, extra_edge)
            if edge_candidate is None:
                continue
            candidate = (*edge_candidate, extra_edge)
            if best_candidate is None or candidate[:3] < best_candidate[:3]:
                best_candidate = candidate

        if best_candidate is None:
            continue

        _anchor_distance, anchor_along_distance, anchor_point, extra_edge = best_candidate
        world_points = _extra_edge_world_points(extra_edge)
        total_distance = _polyline_distance(world_points)
        anchor_node = (stop.var, STATION_CITY_PATH_CONTEXT)
        graph.setdefault(anchor_node, [])

        from_nodes = _standard_graph_nodes_for_endpoint(graph, extra_edge.from_endpoint.key)
        to_nodes = _standard_graph_nodes_for_endpoint(graph, extra_edge.to_endpoint.key)
        start_slice = _rounded_world_polyline(
            reversed(_polyline_slice_between_distances(world_points, 0.0, anchor_along_distance))
        ) or (anchor_point,)
        end_slice = _rounded_world_polyline(
            _polyline_slice_between_distances(world_points, anchor_along_distance, total_distance)
        ) or (anchor_point,)

        label = extra_edge.display_label
        start_distance = round(_polyline_distance(start_slice))
        end_distance = round(_polyline_distance(end_slice))
        for from_node in from_nodes:
            from_path = start_slice
            _append_graph_edge(
                graph,
                _route_edge_from_city_anchor(
                    anchor_node,
                    from_node,
                    distance=start_distance,
                    label=label,
                    world_points=from_path,
                ),
            )
            _append_graph_edge(
                graph,
                _route_edge_from_city_anchor(
                    from_node,
                    anchor_node,
                    distance=start_distance,
                    label=label,
                    world_points=tuple(reversed(from_path)),
                ),
            )

        for to_node in to_nodes:
            to_path = end_slice
            _append_graph_edge(
                graph,
                _route_edge_from_city_anchor(
                    anchor_node,
                    to_node,
                    distance=end_distance,
                    label=label,
                    world_points=to_path,
                ),
            )
            _append_graph_edge(
                graph,
                _route_edge_from_city_anchor(
                    to_node,
                    anchor_node,
                    distance=end_distance,
                    label=label,
                    world_points=tuple(reversed(to_path)),
                ),
            )


def _append_graph_edge(
    graph: dict[RouteNode, list[RouteEdge]],
    edge: RouteEdge,
) -> None:
    graph.setdefault(edge.start, []).append(edge)


def _build_route_graph(
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
    include_planned_metro: bool = False,
) -> dict[RouteNode, list[RouteEdge]]:
    graph: dict[RouteNode, list[RouteEdge]] = {}

    for stop in METRO_STOPS:
        if not include_planned_metro and not stop.is_connected:
            continue

        node_lines = tuple(STOP_LINE_NAMES[stop.var])
        for line_name in node_lines:
            graph.setdefault((stop.var, line_name), [])

        for first_line, second_line in combinations(node_lines, 2):
            first_node = (stop.var, first_line)
            second_node = (stop.var, second_line)
            graph[first_node].append(
                RouteEdge(
                    start=first_node,
                    end=second_node,
                    distance=0,
                    transfer_count=1,
                    kind='transfer',
                    line_name=second_line,
                )
            )
            graph[second_node].append(
                RouteEdge(
                    start=second_node,
                    end=first_node,
                    distance=0,
                    transfer_count=1,
                    kind='transfer',
                    line_name=first_line,
                )
            )

    for line_name, stop_vars in LINE_STOP_VARS.items():
        for start_var, end_var in zip(stop_vars, stop_vars[1:]):
            if (
                not include_planned_metro
                and (
                    not STOPS_BY_VAR[start_var].is_connected
                    or not STOPS_BY_VAR[end_var].is_connected
                )
            ):
                continue

            forward_points = _line_segment_plot_points(line_name, start_var, end_var)
            backward_points = tuple(reversed(forward_points))
            segment_distance = _polyline_distance(forward_points)
            start_node = (start_var, line_name)
            end_node = (end_var, line_name)
            _append_graph_edge(
                graph,
                RouteEdge(
                    start=start_node,
                    end=end_node,
                    distance=segment_distance,
                    transfer_count=0,
                    kind='ride',
                    line_name=line_name,
                    path_points=forward_points,
                ),
            )
            _append_graph_edge(
                graph,
                RouteEdge(
                    start=end_node,
                    end=start_node,
                    distance=segment_distance,
                    transfer_count=0,
                    kind='ride',
                    line_name=line_name,
                    path_points=backward_points,
                ),
            )

    for extra_edge in EXTRA_EDGES:
        if extra_edge.kind == 'connector' and not allow_connector:
            continue
        if extra_edge.kind == 'walk' and not allow_walk:
            continue
        if extra_edge.from_endpoint.kind == 'coord':
            graph.setdefault((extra_edge.from_endpoint.key, COORDINATE_NODE_CONTEXT), [])
        if extra_edge.to_endpoint.kind == 'coord':
            graph.setdefault((extra_edge.to_endpoint.key, COORDINATE_NODE_CONTEXT), [])

        start_nodes = _graph_nodes_for_endpoint(graph, extra_edge.from_endpoint.key)
        end_nodes = _graph_nodes_for_endpoint(graph, extra_edge.to_endpoint.key)
        if not start_nodes or not end_nodes:
            continue

        for start_node in start_nodes:
            for end_node in end_nodes:
                _append_graph_edge(
                    graph,
                    RouteEdge(
                        start=start_node,
                        end=end_node,
                        distance=extra_edge.resolved_distance,
                        transfer_count=0,
                        kind=extra_edge.kind,
                        label=extra_edge.display_label,
                        path_points=extra_edge.plot_points,
                    ),
                )
                if extra_edge.bidirectional:
                    _append_graph_edge(
                        graph,
                        RouteEdge(
                            start=end_node,
                            end=start_node,
                            distance=extra_edge.resolved_distance,
                            transfer_count=0,
                            kind=extra_edge.kind,
                            label=extra_edge.display_label,
                            path_points=extra_edge.reverse_plot_points,
                        ),
                    )

    if allow_walk:
        _append_station_city_path_anchors(graph)

    return graph


def _append_route_step(steps: list[RouteStep], edge: RouteEdge) -> None:
    start_key = edge.start[0]
    end_key = edge.end[0]

    if edge.kind == 'transfer':
        steps.append(
            RouteStep(
                kind='transfer',
                start_key=start_key,
                end_key=end_key,
                distance=0,
                line_name=edge.line_name,
                label=edge.label,
                stop_vars=(start_key,),
                path_points=(),
            )
        )
        return

    if (
        steps
        and edge.kind == 'ride'
        and steps[-1].kind == 'ride'
        and steps[-1].line_name == edge.line_name
    ):
        previous_step = steps[-1]
        combined_stop_vars = previous_step.stop_vars
        if combined_stop_vars[-1] != end_key:
            combined_stop_vars = combined_stop_vars + (end_key,)
        combined_path_points = previous_step.path_points
        if combined_path_points and edge.path_points and combined_path_points[-1] == edge.path_points[0]:
            combined_path_points = combined_path_points + edge.path_points[1:]
        else:
            combined_path_points = combined_path_points + edge.path_points
        steps[-1] = RouteStep(
            kind='ride',
            start_key=previous_step.start_key,
            end_key=end_key,
            distance=previous_step.distance + edge.distance,
            line_name=previous_step.line_name,
            label=previous_step.label,
            stop_vars=combined_stop_vars,
            path_points=combined_path_points,
        )
        return

    if (
        steps
        and edge.kind == 'walk'
        and steps[-1].kind == 'walk'
        and (steps[-1].label or '') == (edge.label or '')
    ):
        previous_step = steps[-1]
        combined_path_points = previous_step.path_points
        if combined_path_points and edge.path_points and combined_path_points[-1] == edge.path_points[0]:
            combined_path_points = combined_path_points + edge.path_points[1:]
        else:
            combined_path_points = combined_path_points + edge.path_points
        steps[-1] = RouteStep(
            kind='walk',
            start_key=previous_step.start_key,
            end_key=end_key,
            distance=previous_step.distance + edge.distance,
            line_name=previous_step.line_name,
            label=previous_step.label,
            stop_vars=previous_step.stop_vars + (end_key,),
            path_points=combined_path_points,
        )
        return

    steps.append(
        RouteStep(
            kind=edge.kind,
            start_key=start_key,
            end_key=end_key,
            distance=edge.distance,
            line_name=edge.line_name,
            label=edge.label,
            stop_vars=(start_key, end_key),
            path_points=edge.path_points,
        )
    )


def _find_route(
    start_key: str,
    end_key: str,
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
    allow_flying: bool = False,
) -> RouteResult | None:
    if start_key == end_key:
        return _direct_fly_route(start_key, end_key)

    graph = _build_route_graph(
        allow_connector=allow_connector,
        allow_walk=allow_walk,
        include_planned_metro=True,
    )
    start_nodes = _graph_nodes_for_endpoint(graph, start_key)
    end_nodes = set(_graph_nodes_for_endpoint(graph, end_key))
    if not start_nodes or not end_nodes:
        route_result = None
    else:
        best_costs: dict[RouteNode, tuple[int, int]] = {}
        predecessors: dict[RouteNode, tuple[RouteNode | None, RouteEdge | None]] = {}
        heap: list[tuple[int, int, RouteNode]] = []

        for start_node in start_nodes:
            best_costs[start_node] = (0, 0)
            predecessors[start_node] = (None, None)
            heapq.heappush(heap, (0, 0, start_node))

        best_end_node: RouteNode | None = None
        while heap:
            track_distance, transfer_count, node = heapq.heappop(heap)
            if (track_distance, transfer_count) != best_costs.get(node):
                continue
            if node in end_nodes:
                best_end_node = node
                break

            for edge in graph.get(node, []):
                next_node = edge.end
                next_cost = (
                    track_distance + edge.distance,
                    transfer_count + edge.transfer_count,
                )
                if next_cost < best_costs.get(next_node, (10**12, 10**12)):
                    best_costs[next_node] = next_cost
                    predecessors[next_node] = (node, edge)
                    heapq.heappush(heap, (next_cost[0], next_cost[1], next_node))

        if best_end_node is None:
            route_result = None
        else:
            route_edges: list[RouteEdge] = []
            cursor = best_end_node
            while True:
                previous_node, edge = predecessors[cursor]
                if edge is None or previous_node is None:
                    break
                route_edges.append(edge)
                cursor = previous_node
            route_edges.reverse()

            steps: list[RouteStep] = []
            for edge in route_edges:
                _append_route_step(steps, edge)

            total_distance, total_interchanges = best_costs[best_end_node]
            route_result = RouteResult(
                start_key=start_key,
                end_key=end_key,
                total_distance=total_distance,
                total_interchanges=total_interchanges,
                steps=tuple(steps),
            )

    fly_result = _direct_fly_route(start_key, end_key) if allow_flying else None
    if route_result is None:
        return fly_result
    if fly_result is None:
        return route_result
    return min(
        (route_result, fly_result),
        key=lambda route: (route.total_distance, route.total_interchanges, len(route.steps)),
    )


def _route_costs_from_endpoint_key(
    start_key: str,
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
) -> dict[str, tuple[int, int]]:
    if _path_endpoint_from_key(start_key) is None:
        return {}

    graph = _build_route_graph(
        allow_connector=allow_connector,
        allow_walk=allow_walk,
    )
    start_nodes = _graph_nodes_for_endpoint(graph, start_key)
    if not start_nodes:
        return {}

    best_costs: dict[RouteNode, tuple[int, int]] = {}
    heap: list[tuple[int, int, RouteNode]] = []
    for start_node in start_nodes:
        best_costs[start_node] = (0, 0)
        heapq.heappush(heap, (0, 0, start_node))

    while heap:
        track_distance, transfer_count, node = heapq.heappop(heap)
        if (track_distance, transfer_count) != best_costs.get(node):
            continue

        for edge in graph.get(node, []):
            next_node = edge.end
            next_cost = (
                track_distance + edge.distance,
                transfer_count + edge.transfer_count,
            )
            if next_cost < best_costs.get(next_node, (10**12, 10**12)):
                best_costs[next_node] = next_cost
                heapq.heappush(heap, (next_cost[0], next_cost[1], next_node))

    stop_costs: dict[str, tuple[int, int]] = {}
    for (stop_var, _line_name), cost in best_costs.items():
        if cost < stop_costs.get(stop_var, (10**12, 10**12)):
            stop_costs[stop_var] = cost
    return stop_costs


def _route_costs_from(
    start_var: str,
    *,
    allow_connector: bool = True,
    allow_walk: bool = True,
) -> dict[str, tuple[int, int]]:
    if start_var not in STOPS_BY_VAR or not STOPS_BY_VAR[start_var].is_connected:
        return {}
    return _route_costs_from_endpoint_key(
        start_var,
        allow_connector=allow_connector,
        allow_walk=allow_walk,
    )


def _format_line_name_list(line_names: Sequence[str]) -> str:
    if not line_names:
        return ''
    if len(line_names) == 1:
        return line_names[0]
    if len(line_names) == 2:
        return f'{line_names[0]} and {line_names[1]}'
    return f'{", ".join(line_names[:-1])}, and {line_names[-1]}'


def _unfinished_route_line_names(route: RouteResult) -> tuple[str, ...]:
    line_names: set[str] = set()
    for step in route.steps:
        if step.kind != 'ride' or step.line_name is None or len(step.stop_vars) < 2:
            continue
        for start_var, end_var in zip(step.stop_vars, step.stop_vars[1:]):
            if not STOPS_BY_VAR[start_var].is_connected or not STOPS_BY_VAR[end_var].is_connected:
                line_names.add(step.line_name)
    return tuple(sorted(line_names))


def _direct_fly_route(start_key: str, end_key: str) -> RouteResult | None:
    start_endpoint = _path_endpoint_from_key(start_key)
    end_endpoint = _path_endpoint_from_key(end_key)
    if start_endpoint is None or end_endpoint is None:
        return None
    if start_key == end_key:
        return RouteResult(
            start_key=start_key,
            end_key=end_key,
            total_distance=0,
            total_interchanges=0,
            steps=(),
        )

    distance = round(dist(start_endpoint.coordinates, end_endpoint.coordinates))
    return RouteResult(
        start_key=start_key,
        end_key=end_key,
        total_distance=distance,
        total_interchanges=0,
        steps=(
            RouteStep(
                kind='fly',
                start_key=start_key,
                end_key=end_key,
                distance=distance,
                label='Fly',
                path_points=(start_endpoint.plot_coordinates, end_endpoint.plot_coordinates),
            ),
        ),
    )


def _cross_product(
    origin: tuple[int, int],
    point_a: tuple[int, int],
    point_b: tuple[int, int],
) -> int:
    return (
        ((point_a[0] - origin[0]) * (point_b[1] - origin[1]))
        - ((point_a[1] - origin[1]) * (point_b[0] - origin[0]))
    )


def _convex_hull(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    unique_points = sorted(set(points))
    if len(unique_points) <= 1:
        return unique_points

    lower: list[tuple[int, int]] = []
    for point in unique_points:
        while len(lower) >= 2 and _cross_product(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper: list[tuple[int, int]] = []
    for point in reversed(unique_points):
        while len(upper) >= 2 and _cross_product(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _segment_orientation(
    start_point: tuple[int, int],
    end_point: tuple[int, int],
    point: tuple[int, int],
) -> int:
    cross_value = _cross_product(start_point, end_point, point)
    if cross_value == 0:
        return 0
    return 1 if cross_value > 0 else -1


def _point_on_segment(
    start_point: tuple[int, int],
    end_point: tuple[int, int],
    point: tuple[int, int],
) -> bool:
    if _segment_orientation(start_point, end_point, point) != 0:
        return False
    return (
        min(start_point[0], end_point[0]) <= point[0] <= max(start_point[0], end_point[0])
        and min(start_point[1], end_point[1]) <= point[1] <= max(start_point[1], end_point[1])
    )


def _segments_intersect(
    first_start: tuple[int, int],
    first_end: tuple[int, int],
    second_start: tuple[int, int],
    second_end: tuple[int, int],
) -> bool:
    shared_points = {first_start, first_end} & {second_start, second_end}
    first_orientation_start = _segment_orientation(first_start, first_end, second_start)
    first_orientation_end = _segment_orientation(first_start, first_end, second_end)
    second_orientation_start = _segment_orientation(second_start, second_end, first_start)
    second_orientation_end = _segment_orientation(second_start, second_end, first_end)

    if first_orientation_start == 0 and _point_on_segment(first_start, first_end, second_start):
        return second_start not in shared_points
    if first_orientation_end == 0 and _point_on_segment(first_start, first_end, second_end):
        return second_end not in shared_points
    if second_orientation_start == 0 and _point_on_segment(second_start, second_end, first_start):
        return first_start not in shared_points
    if second_orientation_end == 0 and _point_on_segment(second_start, second_end, first_end):
        return first_end not in shared_points

    return (
        first_orientation_start != first_orientation_end
        and second_orientation_start != second_orientation_end
    )


def _normalized_segment(
    start_point: tuple[int, int],
    end_point: tuple[int, int],
) -> tuple[tuple[int, int], tuple[int, int]]:
    if start_point <= end_point:
        return (start_point, end_point)
    return (end_point, start_point)


def _connected_area_obstacle_segments(
    route_paths: list[tuple[tuple[int, int], ...]],
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    included_segments = {
        _normalized_segment(start_point, end_point)
        for route_path in route_paths
        for start_point, end_point in zip(route_path, route_path[1:])
    }

    obstacle_segments: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for line_path_points in METRO_LINE_PLOT_PATHS.values():
        for start_point, end_point in zip(line_path_points, line_path_points[1:]):
            if _normalized_segment(start_point, end_point) in included_segments:
                continue
            obstacle_segments.append((start_point, end_point))
    return obstacle_segments


def _segment_crosses_obstacles(
    start_point: tuple[int, int],
    end_point: tuple[int, int],
    obstacle_segments: list[tuple[tuple[int, int], tuple[int, int]]],
) -> bool:
    return any(
        _segments_intersect(start_point, end_point, obstacle_start, obstacle_end)
        for obstacle_start, obstacle_end in obstacle_segments
    )


def _build_visibility_graph(
    candidate_points: list[tuple[int, int]],
    obstacle_segments: list[tuple[tuple[int, int], tuple[int, int]]],
) -> dict[tuple[int, int], list[tuple[tuple[int, int], float]]]:
    visibility_graph = {point: [] for point in candidate_points}
    sorted_points = sorted(candidate_points)
    for index, start_point in enumerate(sorted_points):
        for end_point in sorted_points[index + 1:]:
            if _segment_crosses_obstacles(start_point, end_point, obstacle_segments):
                continue
            segment_distance = dist(start_point, end_point)
            visibility_graph[start_point].append((end_point, segment_distance))
            visibility_graph[end_point].append((start_point, segment_distance))
    return visibility_graph


def _shortest_visible_path(
    start_point: tuple[int, int],
    end_point: tuple[int, int],
    visibility_graph: dict[tuple[int, int], list[tuple[tuple[int, int], float]]],
) -> list[tuple[int, int]]:
    if start_point == end_point:
        return [start_point]

    best_costs: dict[tuple[int, int], float] = {start_point: 0.0}
    previous_points: dict[tuple[int, int], tuple[int, int]] = {}
    heap: list[tuple[float, tuple[int, int]]] = [(0.0, start_point)]

    while heap:
        current_cost, current_point = heapq.heappop(heap)
        if current_cost != best_costs.get(current_point):
            continue
        if current_point == end_point:
            break

        for next_point, segment_distance in visibility_graph.get(current_point, []):
            next_cost = current_cost + segment_distance
            if next_cost < best_costs.get(next_point, float('inf')):
                best_costs[next_point] = next_cost
                previous_points[next_point] = current_point
                heapq.heappush(heap, (next_cost, next_point))

    if end_point not in best_costs:
        return []

    path = [end_point]
    while path[-1] != start_point:
        path.append(previous_points[path[-1]])
    path.reverse()
    return path


def _remove_collinear_loop_points(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if len(points) < 4:
        return points

    simplified = points[:]
    changed = True
    while changed and len(simplified) >= 4:
        changed = False
        next_points: list[tuple[int, int]] = []
        total_points = len(simplified)
        for index, point in enumerate(simplified):
            previous_point = simplified[index - 1]
            next_point = simplified[(index + 1) % total_points]
            if _segment_orientation(previous_point, point, next_point) == 0:
                changed = True
                continue
            next_points.append(point)
        if len(next_points) < 3:
            return simplified
        simplified = next_points
    return simplified


def _point_on_polygon_boundary(
    point: tuple[int, int],
    polygon: list[tuple[int, int]],
) -> bool:
    return any(
        _point_on_segment(start_point, end_point, point)
        for start_point, end_point in zip(polygon, polygon[1:] + polygon[:1])
    )


def _point_in_polygon(
    point: tuple[int, int],
    polygon: list[tuple[int, int]],
) -> bool:
    if _point_on_polygon_boundary(point, polygon):
        return True

    point_x, point_y = point
    inside = False
    for start_point, end_point in zip(polygon, polygon[1:] + polygon[:1]):
        start_x, start_y = start_point
        end_x, end_y = end_point
        if (start_y > point_y) == (end_y > point_y):
            continue
        x_at_y = start_x + (((end_x - start_x) * (point_y - start_y)) / (end_y - start_y))
        if point_x < x_at_y:
            inside = not inside
    return inside


def _polygon_has_self_intersection(points: list[tuple[int, int]]) -> bool:
    edges = list(zip(points, points[1:] + points[:1]))
    for first_index, (first_start, first_end) in enumerate(edges):
        for second_index, (second_start, second_end) in enumerate(edges):
            if abs(first_index - second_index) <= 1:
                continue
            if {first_index, second_index} == {0, len(edges) - 1}:
                continue
            if _segments_intersect(first_start, first_end, second_start, second_end):
                return True
    return False


def _can_insert_polygon_point(
    polygon: list[tuple[int, int]],
    edge_index: int,
    point: tuple[int, int],
    obstacle_segments: list[tuple[tuple[int, int], tuple[int, int]]],
) -> bool:
    start_point = polygon[edge_index]
    end_point = polygon[(edge_index + 1) % len(polygon)]
    if point in (start_point, end_point):
        return False
    if _segment_crosses_obstacles(start_point, point, obstacle_segments):
        return False
    if _segment_crosses_obstacles(point, end_point, obstacle_segments):
        return False

    trial_polygon = polygon[:edge_index + 1] + [point] + polygon[edge_index + 1:]
    return not _polygon_has_self_intersection(trial_polygon)


def _insert_outside_polygon_points(
    polygon: list[tuple[int, int]],
    candidate_points: list[tuple[int, int]],
    obstacle_segments: list[tuple[tuple[int, int], tuple[int, int]]],
) -> list[tuple[int, int]]:
    updated_polygon = polygon[:]

    while True:
        outside_points = [
            point
            for point in candidate_points
            if not _point_in_polygon(point, updated_polygon)
        ]
        if not outside_points:
            return updated_polygon

        best_insertion: tuple[float, int, tuple[int, int]] | None = None
        for point in outside_points:
            for edge_index, (start_point, end_point) in enumerate(
                zip(updated_polygon, updated_polygon[1:] + updated_polygon[:1])
            ):
                if not _can_insert_polygon_point(updated_polygon, edge_index, point, obstacle_segments):
                    continue
                added_distance = (
                    dist(start_point, point)
                    + dist(point, end_point)
                    - dist(start_point, end_point)
                )
                candidate_insertion = (added_distance, edge_index, point)
                if best_insertion is None or candidate_insertion < best_insertion:
                    best_insertion = candidate_insertion

        if best_insertion is None:
            return updated_polygon

        _added_distance, edge_index, point = best_insertion
        updated_polygon.insert(edge_index + 1, point)


def _connected_route_area_loops(
    route_paths: list[tuple[tuple[int, int], ...]],
) -> list[list[tuple[float, float]]]:
    candidate_points = sorted({point for route_path in route_paths for point in route_path})
    if len(candidate_points) < 3:
        return []

    hull_points = _convex_hull(candidate_points)
    if len(hull_points) < 3:
        return []

    obstacle_segments = _connected_area_obstacle_segments(route_paths)
    visibility_graph = _build_visibility_graph(candidate_points, obstacle_segments)

    loop_points: list[tuple[int, int]] = []
    for start_point, end_point in zip(hull_points, hull_points[1:] + hull_points[:1]):
        if _segment_crosses_obstacles(start_point, end_point, obstacle_segments):
            edge_path = _shortest_visible_path(start_point, end_point, visibility_graph)
        else:
            edge_path = [start_point, end_point]

        if not edge_path:
            return []
        if not loop_points:
            loop_points.extend(edge_path)
            continue
        if loop_points[-1] == edge_path[0]:
            loop_points.extend(edge_path[1:])
        else:
            loop_points.extend(edge_path)

    if len(loop_points) >= 2 and loop_points[0] == loop_points[-1]:
        loop_points.pop()

    loop_points = _remove_collinear_loop_points(loop_points)
    if len(loop_points) < 3:
        return []

    loop_points = _insert_outside_polygon_points(loop_points, candidate_points, obstacle_segments)
    loop_points = _remove_collinear_loop_points(loop_points)
    if len(loop_points) < 3:
        return []

    return [[(float(point_x), float(point_y)) for point_x, point_y in loop_points]]


CONNECTED_AREA_CACHE_KEY: tuple[
    tuple[tuple[tuple[int, int], ...], ...],
    tuple[tuple[tuple[int, int], ...], ...],
] | None = None
CONNECTED_AREA_WORLD_LOOPS: tuple[tuple[tuple[float, float], ...], ...] = ()


def _connected_route_area_world_loops() -> tuple[tuple[tuple[float, float], ...], ...]:
    global CONNECTED_AREA_CACHE_KEY
    global CONNECTED_AREA_WORLD_LOOPS

    route_paths = tuple(_connected_route_plot_paths())
    all_line_paths = tuple(
        tuple(line_path_points)
        for _line_name, line_path_points in sorted(METRO_LINE_PLOT_PATHS.items())
    )
    cache_key = (route_paths, all_line_paths)
    if cache_key == CONNECTED_AREA_CACHE_KEY:
        return CONNECTED_AREA_WORLD_LOOPS

    loops = _connected_route_area_loops(list(route_paths))
    CONNECTED_AREA_WORLD_LOOPS = tuple(tuple(loop) for loop in loops)
    CONNECTED_AREA_CACHE_KEY = cache_key
    return CONNECTED_AREA_WORLD_LOOPS


class MetroMapViewer:
    _path_detection_applied: ClassVar[bool] = False

    def __init__(
        self,
        width: int = PLOT_WIDTH,
        height: int = PLOT_HEIGHT,
        padding: int = PLOT_PADDING,
    ) -> None:
        self.width = width
        self.height = height
        self.padding = padding
        self.zoom = DEFAULT_ZOOM
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.drag_start: tuple[int, int] | None = None
        self.drag_origin: tuple[int, int] | None = None
        self.is_dragging = False
        self.selected_stop_var: str | None = None
        self.selected_path_node_key: str | None = None
        self.selected_metro_segment_key: tuple[str, str, str] | None = None
        self.selected_metro_segment_keys: tuple[tuple[str, str, str], ...] = ()
        self.metro_segment_selection_anchor_key: tuple[str, str, str] | None = None
        self.city_limits_edit_stop_var: str | None = None
        self.active_path_edge_id: str | None = None
        self.path_drag_start_endpoint_key: str | None = None
        self.path_drag_current_canvas_point: tuple[int, int] | None = None
        self.path_drag_preview_item_ids: list[int] = []
        self.station_canvas_positions: dict[str, tuple[float, float]] = {}
        self.path_node_canvas_positions: dict[str, tuple[float, float]] = {}
        self.info_popup_frame: tk.Frame | None = None
        self.info_popup_variables: list[tk.BooleanVar] = []
        self.station_signage_line_by_stop: dict[str, str] = {}
        self.station_signage_flipped_keys: set[tuple[str, str]] = set()
        self.station_signage_elevator_right_stop_vars: set[str] = set()
        self.sidebar_scroll_after_id: str | None = None
        self.sidebar_scroll_remaining = 0.0
        self.current_route: RouteResult | None = None
        self.route_request: tuple[str, str] | None = None
        self.priority_filter_options: dict[str, str | None] = {}
        self.priority_highlight_stop_vars: set[str] = set()
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.stats_dirty = True
        self.railway_finish_dirty = True
        self.path_edge_list_dirty = True
        self.route_controls_updating = False
        self.search_match_stop_vars: list[str] = []
        self.route_start_entry: tk.Entry
        self.route_end_entry: tk.Entry
        self.path_edge_list_frame: tk.Frame
        self.search_entry: tk.Entry
        self.route_steps_text: tk.Text
        self.world_map_status_text: tk.Text
        self.world_map_auto_fill_button: tk.Label
        self.path_nodes_heading: tk.Label
        self.priority_list_frame: tk.Frame
        self.railway_finish_line_menu: tk.Menubutton
        self.world_map_task_queue: queue.SimpleQueue[WorldMapTaskQueueItem] = queue.SimpleQueue()
        self.world_map_preview_queue: queue.SimpleQueue[WorldMapPreviewQueueItem] = queue.SimpleQueue()
        self.world_map_task_completion_callback: Callable[[bool, str], None] | None = None
        self.world_map_task_running = False
        self.world_map_preview_build_key: tuple[str, FileStatKey] | None = None
        self.world_map_preview_poll_after_id: str | None = None
        self.world_map_auto_fill_stop_event: threading.Event | None = None
        self.world_map_auto_fill_running = False
        self.world_map_auto_fill_stop_requested = False
        self.world_map_active_target_bounds: tuple[int, int, int, int] | None = None
        self.world_map_render_cache_stat: FileStatKey | None = None
        self.world_map_render_image_stat: FileStatKey | None = None
        self.world_map_render_image_path: Path | None = None
        self.world_map_render_payload: dict[str, object] | None = None
        self.world_map_render_source_image: Image.Image | None = None
        self.target_map_bounds_cache_stat: FileStatKey | None = None
        self.target_map_plot_bounds_cache: tuple[float, float, float, float] | None = None
        self._world_map_full_render_image_path: Path | None = None
        self._world_map_full_render_image_stat: FileStatKey | None = None
        self._world_map_full_render_source_image: Image.Image | None = None
        self.world_map_render_cache_checked_at = 0.0
        self.world_map_spiral_check_cache_stat: FileStatKey | None = None
        self.world_map_spiral_check_payload: dict[str, object] | None = None
        self._path_detection_preview: object | None = None
        self._path_detection_debug_points: tuple[tuple[int, int], ...] = ()
        self._path_detection_hide_selected_popup = False
        self._path_detection_session: object | None = None
        self._path_detection_click_bound = False
        self.overlay_image_refs: list[ImageTk.PhotoImage] = []
        self.hover_canvas_point: tuple[float, float] | None = None
        self.cursor_readout_coordinates: tuple[int, int] | None = None
        self.show_cursor_guides = False
        self.cursor_overlay_ids: dict[str, int] = {}
        self.suggestion_popup: tk.Toplevel | None = None
        self.suggestion_listbox: tk.Listbox | None = None
        self.suggestion_values: list[str] = []
        self.suggestion_active_entry: tk.Entry | None = None
        self.suggestion_select_callback: Callable[[str], None] | None = None
        self.redraw_after_id: str | None = None
        self.full_redraw_after_id: str | None = None
        self.defer_expensive_viewport_layers = False
        self.fast_viewport_transform_active = False

        self.root: tk.Tk = tk.Tk()
        self.root.title('Minecraft Metro Stops')
        self.root.configure(bg=BACKGROUND_COLOR)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f'{screen_width}x{screen_height}+0+0')
        self.search_var = tk.StringVar(master=self.root)
        self.search_status_var = tk.StringVar(
            master=self.root,
            value='Search stations by village name or station code.',
        )
        self.route_start_var = tk.StringVar(master=self.root)
        self.route_end_var = tk.StringVar(master=self.root)
        self.walk_path_from_var = tk.StringVar(master=self.root)
        self.walk_path_to_var = tk.StringVar(master=self.root)
        self.walk_path_label_var = tk.StringVar(master=self.root)
        self.path_node_coordinates_var = tk.StringVar(master=self.root)
        self.path_node_label_var = tk.StringVar(master=self.root)
        self.path_click_mode_var = tk.BooleanVar(master=self.root, value=False)
        self.path_drag_kind_var = tk.StringVar(master=self.root, value='Walk')
        self.path_click_status_var = tk.StringVar(
            master=self.root,
            value='Turn on map pathing to add nodes and drag paths on the map.',
        )
        self.route_summary_var = tk.StringVar(
            master=self.root,
            value='Choose two stations or coordinates.',
        )
        self.stats_summary_var = tk.StringVar(master=self.root, value='Loading station progress...')
        self.use_connector_routes_var = tk.BooleanVar(master=self.root, value=True)
        self.use_walk_routes_var = tk.BooleanVar(master=self.root, value=False)
        self.use_flying_routes_var = tk.BooleanVar(master=self.root, value=False)
        self.show_planning_circle_var = tk.BooleanVar(master=self.root, value=False)
        self.show_connected_area_var = tk.BooleanVar(master=self.root, value=False)
        self.show_city_limits_var = tk.BooleanVar(master=self.root, value=False)
        self.show_alignment_reminders_var = tk.BooleanVar(master=self.root, value=False)
        self.show_frontier_highlights_var = tk.BooleanVar(master=self.root, value=False)
        self.show_labels_var = tk.BooleanVar(master=self.root, value=True)
        self.show_world_map_render_var = tk.BooleanVar(master=self.root, value=True)
        self.show_suggested_walking_paths_var = tk.BooleanVar(master=self.root, value=False)
        self.show_path_nodes_var = tk.BooleanVar(master=self.root, value=False)
        self.circle_internal_voids_var = tk.BooleanVar(master=self.root, value=False)
        self.export_include_world_map_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_grid_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_metro_lines_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_stations_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_labels_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_path_nodes_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_walking_paths_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_connector_paths_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_current_route_var = tk.BooleanVar(master=self.root, value=True)
        self.export_include_planning_circle_var = tk.BooleanVar(master=self.root, value=False)
        self.export_include_connected_area_var = tk.BooleanVar(master=self.root, value=False)
        self.export_include_alignment_ellipses_var = tk.BooleanVar(master=self.root, value=False)
        self.export_include_frontier_highlights_var = tk.BooleanVar(master=self.root, value=False)
        self.export_include_railway_finishing_var = tk.BooleanVar(master=self.root, value=False)
        self.priority_summary_var = tk.StringVar(master=self.root, value='Planning radius unavailable.')
        self.priority_filter_var = tk.StringVar(master=self.root, value=PRIORITY_FILTER_ALL_LABEL)
        self.railway_finish_mode_var = tk.BooleanVar(master=self.root, value=False)
        self.railway_finish_line_var = tk.StringVar(master=self.root)
        self.railway_finish_coordinates_var = tk.StringVar(master=self.root)
        self.railway_finish_status_var = tk.StringVar(master=self.root, value='Choose a connected line.')
        self.railway_finish_progress_var = tk.StringVar(master=self.root, value='Loading railway progress...')
        self.world_map_mode_var = tk.StringVar(master=self.root, value=_world_map_mode_labels()[0])
        self.world_map_status_var = tk.StringVar(
            master=self.root,
            value=_world_map_cached_status_text(
                _world_map_mode_key_for_label(self.world_map_mode_var.get())
            ),
        )
        self.search_var.trace_add('write', self._on_search_changed)
        self.route_start_var.trace_add('write', self._on_route_input_changed)
        self.route_end_var.trace_add('write', self._on_route_input_changed)
        self.world_map_mode_var.trace_add('write', self._on_world_map_mode_changed)

        self.sidebar_container = tk.Frame(
            self.root,
            bg=BACKGROUND_COLOR,
            width=SIDEBAR_WIDTH,
        )
        self.sidebar_container.pack(side='left', fill='y')
        self.sidebar_container.pack_propagate(False)

        self.sidebar_canvas = tk.Canvas(
            self.sidebar_container,
            bg=BACKGROUND_COLOR,
            highlightthickness=0,
            width=SIDEBAR_WIDTH,
            bd=0,
        )
        self.sidebar_scrollbar = tk.Scrollbar(
            self.sidebar_container,
            orient='vertical',
            command=self.sidebar_canvas.yview,
        )
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scrollbar.set)
        self.sidebar_canvas.pack(side='left', fill='both', expand=True)
        self.sidebar_scrollbar.pack(side='right', fill='y')

        self.sidebar = tk.Frame(
            self.sidebar_canvas,
            bg=BACKGROUND_COLOR,
            width=SIDEBAR_WIDTH,
        )
        self.sidebar_window_id = self.sidebar_canvas.create_window((0, 0), anchor='nw', window=self.sidebar)
        self.sidebar.bind('<Configure>', self._on_sidebar_frame_configure)
        self.sidebar_canvas.bind('<Configure>', self._on_sidebar_canvas_configure)
        self._build_route_panel()

        self.canvas: tk.Canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=BACKGROUND_COLOR,
            highlightthickness=0,
            cursor='crosshair',
        )
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<Configure>', self._on_configure)
        self.canvas.bind('<ButtonPress-1>', self._on_drag_start)
        self.canvas.bind('<B1-Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_drag_end)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_zoom_in)
        self.canvas.bind('<Button-5>', self._on_zoom_out)
        self.canvas.focus_set()

        self.root.bind('r', self._on_reset_view)
        self.root.bind('R', self._on_reset_view)
        self.root.bind('a', self._on_focus_connected_area_view)
        self.root.bind('A', self._on_focus_connected_area_view)
        self.root.bind('b', self._on_focus_blackport_view)
        self.root.bind('B', self._on_focus_blackport_view)
        self.root.bind_all('<ButtonRelease-1>', self._on_global_left_click_release, add='+')
        self.root.bind_all('<MouseWheel>', self._on_global_mousewheel, add='+')
        self.root.bind_all('<Button-4>', self._on_global_mousewheel_linux_up, add='+')
        self.root.bind_all('<Button-5>', self._on_global_mousewheel_linux_down, add='+')
        self.root.after_idle(self._finish_startup)

    def run(self) -> None:
        self.root.mainloop()

    def _finish_startup(self) -> None:
        self.show_connected_area_view()
        self._bring_to_front()

    def _bring_to_front(self) -> None:
        try:
            self.root.lift()
            self.root.focus_force()
            self.root.attributes('-topmost', True)
            self.root.after(400, lambda: self.root.attributes('-topmost', False))
        except tk.TclError:
            return

    def _build_route_panel(self) -> None:
        self._make_sidebar_caption('Search').pack(anchor='w', padx=16)
        search_row = tk.Frame(self.sidebar, bg=BACKGROUND_COLOR)
        search_row.pack(fill='x', padx=16, pady=(4, 6))
        self.search_entry = self._make_sidebar_entry(search_row, self.search_var)
        self.search_entry.pack(side='left', fill='x', expand=True)
        self.search_entry.bind('<Return>', self._on_search_submit)
        self._bind_suggestion_entry(
            self.search_entry,
            self.search_var,
            include_nodes=False,
            on_select=self._select_search_suggestion,
        )
        self._make_sidebar_button(
            search_row,
            text='Go',
            command=self._jump_to_first_search_result,
        ).pack(side='left', padx=(10, 0))

        search_status_label = tk.Label(
            self.sidebar,
            textvariable=self.search_status_var,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 32,
        )
        search_status_label.pack(anchor='w', padx=16, pady=(0, 12))

        checklist_section = self._make_collapsible_sidebar_section('Checklist', expanded=True)
        checklist_top_row = tk.Frame(checklist_section, bg=BACKGROUND_COLOR)
        checklist_top_row.pack(fill='x', padx=16, pady=(4, 12))
        stats_label = tk.Label(
            checklist_top_row,
            textvariable=self.stats_summary_var,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 150,
        )
        stats_label.pack(side='left', fill='x', expand=True)
        self._make_sidebar_button(
            checklist_top_row,
            text='Export SVG',
            command=self._show_export_svg_options,
        ).pack(side='right', anchor='n', padx=(10, 0))

        show_hide_section = self._make_collapsible_sidebar_section('Show/Hide', expanded=True)
        connected_area_toggle = self._make_sidebar_checkbox(
            show_hide_section,
            text='Connected area',
            variable=self.show_connected_area_var,
            command=self.redraw,
        )
        connected_area_toggle.pack(anchor='w', padx=16, pady=(4, 6))
        city_limits_toggle = self._make_sidebar_checkbox(
            show_hide_section,
            text='City limits',
            variable=self.show_city_limits_var,
            command=self.redraw,
        )
        city_limits_toggle.pack(anchor='w', padx=16, pady=(0, 6))
        planning_toggle = self._make_sidebar_checkbox(
            show_hide_section,
            text='Planning radius',
            variable=self.show_planning_circle_var,
            command=self.redraw,
        )
        planning_toggle.pack(anchor='w', padx=16, pady=(0, 6))
        alignment_toggle = self._make_sidebar_checkbox(
            show_hide_section,
            text='Alignment ellipses',
            variable=self.show_alignment_reminders_var,
            command=self.redraw,
        )
        alignment_toggle.pack(anchor='w', padx=16, pady=(0, 6))
        frontier_toggle = self._make_sidebar_checkbox(
            show_hide_section,
            text='Frontier highlights',
            variable=self.show_frontier_highlights_var,
            command=self.redraw,
        )
        frontier_toggle.pack(anchor='w', padx=16, pady=(0, 6))
        labels_toggle = self._make_sidebar_checkbox(
            show_hide_section,
            text='Station labels',
            variable=self.show_labels_var,
            command=self.redraw,
        )
        labels_toggle.pack(anchor='w', padx=16, pady=(0, 12))

        priority_section = self._make_collapsible_sidebar_section('Priority List', expanded=False)
        planning_summary_label = tk.Label(
            priority_section,
            textvariable=self.priority_summary_var,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 32,
        )
        planning_summary_label.pack(anchor='w', padx=16, pady=(4, 12))
        priority_filter_row = tk.Frame(priority_section, bg=BACKGROUND_COLOR)
        priority_filter_row.pack(fill='x', padx=16, pady=(0, 8))
        tk.Label(
            priority_filter_row,
            text='Need',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=5,
            anchor='w',
        ).pack(side='left')
        self.priority_filter_menu = self._make_sidebar_option_menu(
            priority_filter_row,
            self.priority_filter_var,
        )
        self.priority_filter_menu.pack(side='left', fill='x', expand=True)
        priority_panel = tk.Frame(
            priority_section,
            bg=INFO_BOX_BACKGROUND,
            relief='flat',
            highlightthickness=1,
            highlightbackground=INFO_BOX_BORDER,
        )
        priority_panel.pack(fill='x', padx=16, pady=(0, 16))
        self.priority_list_frame = tk.Frame(
            priority_panel,
            bg=INFO_BOX_BACKGROUND,
        )
        self.priority_list_frame.pack(fill='x', padx=12, pady=12)

        railway_section = self._make_collapsible_sidebar_section('Railways', expanded=True)
        self._make_sidebar_hint(
            'Enter the farthest finished coordinate on the selected line. The app tracks finished rail from that line origin to the coordinate.',
            parent=railway_section,
        ).pack(anchor='w', padx=16, pady=(4, 6))
        self._make_sidebar_checkbox(
            railway_section,
            text='Railway finishing mode',
            variable=self.railway_finish_mode_var,
            command=self._on_railway_finish_mode_changed,
        ).pack(anchor='w', padx=16, pady=(0, 6))

        railway_line_row = tk.Frame(railway_section, bg=BACKGROUND_COLOR)
        railway_line_row.pack(fill='x', padx=16, pady=(0, 6))
        tk.Label(
            railway_line_row,
            text='Line',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=5,
            anchor='w',
        ).pack(side='left')
        self.railway_finish_line_menu = self._make_sidebar_option_menu(
            railway_line_row,
            self.railway_finish_line_var,
        )
        self.railway_finish_line_menu.pack(side='left', fill='x', expand=True)

        railway_coordinate_row = tk.Frame(railway_section, bg=BACKGROUND_COLOR)
        railway_coordinate_row.pack(fill='x', padx=16, pady=(0, 8))
        tk.Label(
            railway_coordinate_row,
            text='Coords',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=5,
            anchor='w',
        ).pack(side='left')
        railway_coordinate_entry = self._make_sidebar_entry(
            railway_coordinate_row,
            self.railway_finish_coordinates_var,
        )
        railway_coordinate_entry.pack(side='left', fill='x', expand=True)
        railway_coordinate_entry.bind('<Return>', self._on_railway_finish_submit)

        railway_button_row = tk.Frame(railway_section, bg=BACKGROUND_COLOR)
        railway_button_row.pack(fill='x', padx=16, pady=(0, 8))
        self._make_sidebar_button(
            railway_button_row,
            text='Save Point',
            command=self._save_railway_finish_point,
        ).pack(side='left')
        self._make_sidebar_button(
            railway_button_row,
            text='Switch Origin',
            command=self._switch_railway_finish_origin,
        ).pack(side='left', padx=(10, 0))

        railway_summary_row = tk.Frame(railway_section, bg=BACKGROUND_COLOR)
        railway_summary_row.pack(fill='x', padx=16, pady=(0, 8))
        self._make_sidebar_button(
            railway_summary_row,
            text='Line Summaries...',
            command=self._show_line_summary_dialog,
        ).pack(side='left')

        tk.Label(
            railway_section,
            textvariable=self.railway_finish_status_var,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 32,
        ).pack(anchor='w', padx=16, pady=(0, 8))
        tk.Label(
            railway_section,
            textvariable=self.railway_finish_progress_var,
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            padx=12,
            pady=10,
            wraplength=SIDEBAR_WIDTH - 56,
        ).pack(fill='x', padx=16, pady=(0, 12))

        directions_section = self._make_collapsible_sidebar_section('Directions', expanded=False)
        self._make_sidebar_caption('From', parent=directions_section).pack(anchor='w', padx=16)
        self.route_start_entry = self._make_sidebar_entry(directions_section, self.route_start_var)
        self.route_start_entry.pack(fill='x', padx=16, pady=(4, 4))
        self.route_start_entry.bind('<Return>', self._on_route_submit)
        self._bind_suggestion_entry(
            self.route_start_entry,
            self.route_start_var,
            include_nodes=True,
        )
        self._make_sidebar_hint('Station label / var, City limits: label, or x, y', parent=directions_section).pack(anchor='w', padx=16, pady=(0, 10))

        self._make_sidebar_caption('To', parent=directions_section).pack(anchor='w', padx=16)
        self.route_end_entry = self._make_sidebar_entry(directions_section, self.route_end_var)
        self.route_end_entry.pack(fill='x', padx=16, pady=(4, 4))
        self.route_end_entry.bind('<Return>', self._on_route_submit)
        self._bind_suggestion_entry(
            self.route_end_entry,
            self.route_end_var,
            include_nodes=True,
        )
        self._make_sidebar_hint('Station label / var, City limits: label, or x, y', parent=directions_section).pack(anchor='w', padx=16, pady=(0, 8))

        route_type_row = tk.Frame(directions_section, bg=BACKGROUND_COLOR)
        route_type_row.pack(fill='x', padx=16, pady=(0, 12))
        self._make_sidebar_checkbox(
            route_type_row,
            text='Use metro',
            variable=self.use_connector_routes_var,
            command=self._on_route_options_changed,
        ).pack(anchor='w')
        self._make_sidebar_checkbox(
            route_type_row,
            text='Use walking paths',
            variable=self.use_walk_routes_var,
            command=self._on_route_options_changed,
        ).pack(anchor='w')
        self._make_sidebar_checkbox(
            route_type_row,
            text='Use flying',
            variable=self.use_flying_routes_var,
            command=self._on_route_options_changed,
        ).pack(anchor='w')

        button_row = tk.Frame(directions_section, bg=BACKGROUND_COLOR)
        button_row.pack(fill='x', padx=16, pady=(0, 12))
        self._make_sidebar_button(button_row, text='Route', command=self._plan_route).pack(side='left')
        self._make_sidebar_button(button_row, text='Swap', command=self._swap_route_endpoints).pack(side='left', padx=(10, 0))
        self._make_sidebar_button(button_row, text='Clear', command=self._clear_route).pack(side='left', padx=(10, 0))
        self._make_sidebar_button(button_row, text='Undo', command=self._undo_last_saved_change).pack(side='left', padx=(10, 0))

        summary_label = tk.Label(
            directions_section,
            textvariable=self.route_summary_var,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE, 'bold'),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 32,
        )
        summary_label.pack(anchor='w', padx=16, pady=(0, 10))

        self.route_steps_text = tk.Text(
            directions_section,
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            wrap='word',
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground=INFO_BOX_BORDER,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            padx=12,
            pady=12,
            spacing1=2,
            spacing3=4,
            height=12,
        )
        self.route_steps_text.pack(fill='x', padx=16, pady=(0, 12))
        self._set_route_steps_text('Enter or select a start and destination, then press Route.')
        self.route_steps_text.pack_forget()

        pathing_section = self._make_collapsible_sidebar_section('Pathing', expanded=False)
        self.path_nodes_heading = self._make_sidebar_caption('Path Nodes', parent=pathing_section)
        self.path_nodes_heading.pack(anchor='w', padx=16)
        self._make_sidebar_hint(
            'Add non-station nodes by clicking the map or by typed coordinates. Drag between existing stations or nodes to add paths.',
            parent=pathing_section,
        ).pack(anchor='w', padx=16, pady=(4, 6))

        node_coords_row = tk.Frame(pathing_section, bg=BACKGROUND_COLOR)
        node_coords_row.pack(fill='x', padx=16, pady=(0, 6))
        tk.Label(
            node_coords_row,
            text='Coords',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=5,
            anchor='w',
        ).pack(side='left')
        self._make_sidebar_entry(node_coords_row, self.path_node_coordinates_var).pack(
            side='left',
            fill='x',
            expand=True,
            padx=(0, 10),
        )

        node_label_row = tk.Frame(pathing_section, bg=BACKGROUND_COLOR)
        node_label_row.pack(fill='x', padx=16, pady=(0, 8))
        tk.Label(
            node_label_row,
            text='Label',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=5,
            anchor='w',
        ).pack(side='left')
        self._make_sidebar_entry(node_label_row, self.path_node_label_var).pack(side='left', fill='x', expand=True)

        node_button_row = tk.Frame(pathing_section, bg=BACKGROUND_COLOR)
        node_button_row.pack(fill='x', padx=16, pady=(0, 12))
        self._make_sidebar_button(
            node_button_row,
            text='Add Node',
            command=self._add_path_node_from_sidebar,
        ).pack(side='left')
        self._make_sidebar_button(
            node_button_row,
            text='Clear Fields',
            command=self._clear_walk_path_fields,
        ).pack(side='left', padx=(10, 0))

        self._make_sidebar_caption('Map Pathing', parent=pathing_section).pack(anchor='w', padx=16)
        self._make_sidebar_hint(
            'When this is on: click empty map space to add a node, or click and drag from one existing station/node to another to add a path.',
            parent=pathing_section,
        ).pack(anchor='w', padx=16, pady=(4, 6))
        self._make_sidebar_checkbox(
            pathing_section,
            text='Map add/link mode',
            variable=self.path_click_mode_var,
            command=self._on_path_click_mode_changed,
        ).pack(anchor='w', padx=16, pady=(0, 6))

        drag_kind_row = tk.Frame(pathing_section, bg=BACKGROUND_COLOR)
        drag_kind_row.pack(fill='x', padx=16, pady=(0, 8))
        tk.Label(
            drag_kind_row,
            text='New paths',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=8,
            anchor='w',
        ).pack(side='left')
        path_kind_menu = self._make_sidebar_option_menu(drag_kind_row, self.path_drag_kind_var)
        path_kind_menu.pack(side='left', fill='x', expand=True)
        path_kind_menu_widget = self._option_menu_widget(path_kind_menu)
        for path_kind_label in ('Walk', 'Metro'):
            path_kind_menu_widget.add_command(
                label=path_kind_label,
                command=lambda value=path_kind_label: self.path_drag_kind_var.set(value),
            )

        tk.Label(
            pathing_section,
            textvariable=self.path_click_status_var,
            bg=BACKGROUND_COLOR,
            fg=INFO_CHECKBOX_TEXT_COLOR,
            font=('Helvetica', max(10, SIDEBAR_TEXT_FONT_SIZE - 1)),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 32,
        ).pack(anchor='w', padx=16, pady=(0, 12))

        self._make_sidebar_caption('Active Path Edit', parent=pathing_section).pack(anchor='w', padx=16)
        self.path_edge_list_frame = tk.Frame(
            pathing_section,
            bg=INFO_BOX_BACKGROUND,
            relief='flat',
            highlightthickness=1,
            highlightbackground=INFO_BOX_BORDER,
        )
        self.path_edge_list_frame.pack(fill='x', padx=16, pady=(4, 12))
        self._refresh_path_edge_list()

        world_map_section = self._make_collapsible_sidebar_section('World Map', expanded=False)
        self._make_sidebar_checkbox(
            world_map_section,
            text='Show rendered map',
            variable=self.show_world_map_render_var,
            command=self.redraw,
        ).pack(anchor='w', padx=16, pady=(4, 6))
        mode_row = tk.Frame(world_map_section, bg=BACKGROUND_COLOR)
        mode_row.pack(fill='x', padx=16, pady=(0, 6))
        tk.Label(
            mode_row,
            text='Mode',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=5,
            anchor='w',
        ).pack(side='left')
        world_map_mode_menu = self._make_sidebar_option_menu(mode_row, self.world_map_mode_var)
        world_map_mode_menu.pack(side='left', fill='x', expand=True)
        self._populate_option_menu(
            world_map_mode_menu,
            self.world_map_mode_var,
            _world_map_mode_labels(),
        )
        self._make_sidebar_hint(
            'Auto Fill keeps advancing through the planner until the rendered map is complete.',
            parent=world_map_section,
        ).pack(anchor='w', padx=16, pady=(0, 6))
        self.world_map_status_text = tk.Text(
            world_map_section,
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            wrap='word',
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground=INFO_BOX_BORDER,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            padx=12,
            pady=10,
            spacing1=2,
            spacing3=4,
            height=8,
            cursor='xterm',
            exportselection=True,
        )
        self.world_map_status_text.pack(fill='x', padx=16, pady=(0, 8))
        self._set_world_map_status_text(self.world_map_status_var.get())
        world_map_auto_row = tk.Frame(world_map_section, bg=BACKGROUND_COLOR)
        world_map_auto_row.pack(fill='x', padx=16, pady=(0, 12))
        self.world_map_auto_fill_button = self._make_sidebar_button(
            world_map_auto_row,
            text='Start Auto Fill',
            command=self._start_auto_fill_world_map,
        )
        self.world_map_auto_fill_button.pack(side='left')

        self._refresh_route_controls()

    def _make_collapsible_sidebar_section(self, title: str, *, expanded: bool) -> tk.Frame:
        body = tk.Frame(self.sidebar, bg=BACKGROUND_COLOR)
        is_expanded = expanded
        prefix = '+' if is_expanded else '-'
        header = tk.Label(
            self.sidebar,
            text=f'{prefix} {title}',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TITLE_FONT_SIZE, 'bold'),
            anchor='w',
            cursor='hand2',
        )
        header.pack(anchor='w', fill='x', padx=16, pady=(16, 8))
        if is_expanded:
            body.pack(fill='x')

        def toggle() -> None:
            nonlocal is_expanded
            is_expanded = not is_expanded
            prefix = '+' if is_expanded else '-'
            header.configure(text=f'{prefix} {title}')
            if is_expanded:
                body.pack(fill='x', after=header)
            else:
                body.pack_forget()

        header.bind('<Button-1>', lambda _event: toggle())
        return body

    def _make_sidebar_caption(self, text: str, *, parent: tk.Misc | None = None) -> tk.Label:
        return tk.Label(
            parent or self.sidebar,
            text=text,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE, 'bold'),
            anchor='w',
        )

    def _make_sidebar_hint(self, text: str, *, parent: tk.Misc | None = None) -> tk.Label:
        return tk.Label(
            parent or self.sidebar,
            text=text,
            bg=BACKGROUND_COLOR,
            fg=INFO_CHECKBOX_TEXT_COLOR,
            font=('Helvetica', max(10, SIDEBAR_TEXT_FONT_SIZE - 1)),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 32,
        )

    def _make_sidebar_entry(self, parent: tk.Misc, variable: tk.StringVar) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=variable,
            bg=SIDEBAR_INPUT_BACKGROUND,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief='solid',
            bd=1,
            highlightthickness=1,
            highlightbackground=SIDEBAR_INPUT_BORDER,
            highlightcolor=SIDEBAR_INPUT_BORDER,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
        )

    def _make_sidebar_option_menu(self, parent: tk.Misc, variable: tk.StringVar) -> tk.Menubutton:
        option_menu = tk.Menubutton(
            parent,
            textvariable=variable,
            bg=SIDEBAR_INPUT_BACKGROUND,
            fg=TEXT_COLOR,
            activebackground=SIDEBAR_INPUT_ACTIVE_BACKGROUND,
            activeforeground=TEXT_COLOR,
            highlightthickness=1,
            highlightbackground=SIDEBAR_INPUT_BORDER,
            highlightcolor=SIDEBAR_INPUT_BORDER,
            bd=1,
            relief='solid',
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            direction='below',
            padx=12,
            pady=8,
            cursor='hand2',
        )
        menu = tk.Menu(
            option_menu,
            bg=SIDEBAR_INPUT_BACKGROUND,
            fg=TEXT_COLOR,
            activebackground=SIDEBAR_INPUT_ACTIVE_BACKGROUND,
            activeforeground=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            bd=0,
            tearoff=False,
        )
        option_menu.configure(menu=menu)
        return option_menu

    def _option_menu_widget(self, option_menu: tk.Menubutton) -> tk.Menu:
        return cast(tk.Menu, option_menu.nametowidget(str(option_menu.cget('menu'))))

    def _make_sidebar_button(
        self,
        parent: tk.Misc,
        *,
        text: str,
        command: Callable[[], None],
    ) -> tk.Label:
        button = tk.Label(
            parent,
            text=text,
            bg=INFO_BUTTON_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_BUTTON_FONT_SIZE, 'bold'),
            padx=INFO_BUTTON_PAD_X,
            pady=INFO_BUTTON_PAD_Y,
            cursor='hand2',
            bd=1,
            relief='solid',
            highlightthickness=0,
        )
        button.bind('<Enter>', lambda _event: button.configure(bg=INFO_BUTTON_ACTIVE_BACKGROUND))
        button.bind('<Leave>', lambda _event: button.configure(bg=INFO_BUTTON_BACKGROUND))
        button.bind('<Button-1>', lambda _event: command())
        return button

    def _configure_sidebar_button(
        self,
        button: tk.Label,
        *,
        text: str,
        command: Callable[[], None],
    ) -> None:
        button.configure(text=text, bg=INFO_BUTTON_BACKGROUND, cursor='hand2')
        button.unbind('<Button-1>')
        button.bind('<Button-1>', lambda _event: command())

    def _make_sidebar_checkbox(
        self,
        parent: tk.Misc,
        *,
        text: str,
        variable: tk.BooleanVar,
        command: Callable[[], None],
    ) -> tk.Checkbutton:
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=command,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            activebackground=BACKGROUND_COLOR,
            activeforeground=TEXT_COLOR,
            selectcolor=INFO_BUTTON_BACKGROUND,
            highlightthickness=0,
            bd=0,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            cursor='hand2',
        )

    def _route_graph_options(self) -> dict[str, bool]:
        return {
            'allow_connector': self.use_connector_routes_var.get(),
            'allow_walk': self.use_walk_routes_var.get(),
        }

    def _route_search_options(self) -> dict[str, bool]:
        return {
            **self._route_graph_options(),
            'allow_flying': self.use_flying_routes_var.get(),
        }

    def _on_route_options_changed(self) -> None:
        self.route_dirty = True
        self.priority_dirty = True
        self.redraw()

    def _input_suggestion_values(self, query: str, *, include_nodes: bool) -> list[str]:
        normalized_query = query.strip()
        if not normalized_query or _parse_coordinate_text(normalized_query) is not None:
            return []

        values = [stop.lbl for stop in self._search_matches(normalized_query)[:8]]
        if include_nodes:
            values.extend(self._city_limit_suggestion_values(normalized_query))
            values.extend(self._node_suggestion_values(normalized_query))
        return list(dict.fromkeys(values))

    def _city_limit_suggestion_values(self, query: str) -> list[str]:
        normalized_query = _normalize_stop_identity(query)
        if not normalized_query:
            return []
        values: list[str] = []
        for stop in METRO_STOPS:
            if not stop.city_limit_node_keys:
                continue
            label = f'City limits: {stop.lbl}'
            candidates = [label, f'{stop.lbl} city limits', stop.var]
            if any(normalized_query in _normalize_stop_identity(candidate) for candidate in candidates):
                values.append(label)
        return values[:8]

    def _node_suggestion_values(self, query: str) -> list[str]:
        normalized_query = _normalize_stop_identity(query)
        if not normalized_query:
            return []

        values: list[str] = []
        for path_node in _all_path_nodes():
            if not path_node.is_explicit and not path_node.label:
                continue

            candidates = [
                path_node.id,
                path_node.display_label,
                path_node.input_text,
                *( [path_node.label] if path_node.label else [] ),
            ]
            if any(normalized_query in _normalize_stop_identity(candidate) for candidate in candidates):
                values.append(path_node.input_text)
        return values[:8]

    def _hide_suggestion_popup(self) -> None:
        if self.suggestion_popup is not None:
            self.suggestion_popup.destroy()
        self.suggestion_popup = None
        self.suggestion_listbox = None
        self.suggestion_values = []
        self.suggestion_active_entry = None
        self.suggestion_select_callback = None

    def _hide_suggestion_popup_if_unfocused(self, entry: tk.Entry) -> None:
        if self.suggestion_active_entry is not entry:
            return
        focus_widget = self.root.focus_get()
        if focus_widget is entry or focus_widget is self.suggestion_listbox:
            return
        self._hide_suggestion_popup()

    def _show_suggestion_popup(
        self,
        entry: tk.Entry,
        values: list[str],
        *,
        on_select: Callable[[str], None],
    ) -> None:
        if not values:
            self._hide_suggestion_popup()
            return

        if self.suggestion_popup is None or self.suggestion_listbox is None:
            self.suggestion_popup = tk.Toplevel(self.root)
            self.suggestion_popup.overrideredirect(True)
            self.suggestion_popup.transient(self.root)
            self.suggestion_listbox = tk.Listbox(
                self.suggestion_popup,
                bg=SIDEBAR_INPUT_BACKGROUND,
                fg=TEXT_COLOR,
                selectbackground=SIDEBAR_INPUT_ACTIVE_BACKGROUND,
                selectforeground=TEXT_COLOR,
                relief='solid',
                bd=1,
                highlightthickness=1,
                highlightbackground=SIDEBAR_INPUT_BORDER,
                highlightcolor=SIDEBAR_INPUT_BORDER,
                font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
                activestyle='none',
                exportselection=False,
            )
            self.suggestion_listbox.pack(fill='both', expand=True)
            self.suggestion_listbox.bind('<ButtonRelease-1>', self._on_suggestion_listbox_activate)
            self.suggestion_listbox.bind('<Return>', self._on_suggestion_listbox_activate)
            self.suggestion_listbox.bind('<Escape>', lambda _event: self._hide_suggestion_popup())

        if self.suggestion_listbox is None or self.suggestion_popup is None:
            return

        self.suggestion_values = values
        self.suggestion_active_entry = entry
        self.suggestion_select_callback = on_select
        self.suggestion_listbox.delete(0, 'end')
        for value in values:
            self.suggestion_listbox.insert('end', value)
        self.suggestion_listbox.selection_clear(0, 'end')
        self.suggestion_listbox.selection_set(0)
        self.suggestion_listbox.activate(0)

        entry.update_idletasks()
        popup_height = min(len(values), 6) * max(22, SIDEBAR_TEXT_FONT_SIZE + 10)
        popup_width = max(entry.winfo_width(), 180)
        popup_x = entry.winfo_rootx()
        popup_y = entry.winfo_rooty() + entry.winfo_height() + 2
        self.suggestion_popup.geometry(f'{popup_width}x{popup_height}+{popup_x}+{popup_y}')
        self.suggestion_popup.lift()

    def _apply_suggestion_value(self, value: str) -> None:
        callback = self.suggestion_select_callback
        active_entry = self.suggestion_active_entry
        self._hide_suggestion_popup()
        if callback is not None:
            callback(value)
        if active_entry is not None and active_entry.winfo_exists():
            try:
                active_entry.focus_force()
            except tk.TclError:
                active_entry.focus_set()
            active_entry.icursor('end')
            active_entry.selection_clear()

    def _on_suggestion_listbox_activate(self, _event: object) -> str:
        if self.suggestion_listbox is None:
            return 'break'
        selection = self.suggestion_listbox.curselection()
        if not selection:
            return 'break'
        self._apply_suggestion_value(self.suggestion_listbox.get(selection[0]))
        return 'break'

    def _focus_suggestion_listbox(self, entry: tk.Entry) -> str:
        if self.suggestion_active_entry is not entry or self.suggestion_listbox is None:
            return 'break'
        self.suggestion_listbox.focus_set()
        self.suggestion_listbox.selection_clear(0, 'end')
        self.suggestion_listbox.selection_set(0)
        self.suggestion_listbox.activate(0)
        return 'break'

    def _bind_suggestion_entry(
        self,
        entry: tk.Entry,
        variable: tk.StringVar,
        *,
        include_nodes: bool,
        on_select: Callable[[str], None] | None = None,
    ) -> None:
        def refresh_suggestions() -> None:
            values = self._input_suggestion_values(variable.get(), include_nodes=include_nodes)
            if len(values) == 1 and _normalize_stop_identity(values[0]) == _normalize_stop_identity(variable.get()):
                self._hide_suggestion_popup()
                return
            self._show_suggestion_popup(
                entry,
                values,
                on_select=on_select or (lambda value: variable.set(value)),
            )

        entry.bind('<KeyRelease>', lambda _event: refresh_suggestions(), add='+')
        entry.bind('<FocusIn>', lambda _event: refresh_suggestions(), add='+')
        entry.bind(
            '<FocusOut>',
            lambda _event, active_entry=entry: self.root.after(
                120,
                lambda: self._hide_suggestion_popup_if_unfocused(active_entry),
            ),
            add='+',
        )
        entry.bind('<Escape>', lambda _event: self._hide_suggestion_popup(), add='+')
        entry.bind('<Down>', lambda _event, active_entry=entry: self._focus_suggestion_listbox(active_entry), add='+')

    def _select_search_suggestion(self, value: str) -> None:
        self.search_var.set(value)
        self._jump_to_first_search_result()

    def _schedule_redraw(self) -> None:
        if self.redraw_after_id is not None:
            return
        self.redraw_after_id = self.root.after(
            VIEWPORT_REDRAW_BATCH_DELAY_MS,
            self._run_scheduled_redraw,
        )

    def _schedule_full_redraw(self) -> None:
        if self.full_redraw_after_id is not None:
            self.root.after_cancel(self.full_redraw_after_id)
        self.full_redraw_after_id = self.root.after(
            VIEWPORT_INTERACTION_FULL_REDRAW_DELAY_MS,
            self._run_full_redraw,
        )

    def _cancel_scheduled_redraw(self) -> None:
        if self.redraw_after_id is None:
            return
        self.root.after_cancel(self.redraw_after_id)
        self.redraw_after_id = None

    def _begin_viewport_interaction(self) -> None:
        self.defer_expensive_viewport_layers = True
        if not self.fast_viewport_transform_active:
            self._clear_info_popup()
            self.fast_viewport_transform_active = True
        self._schedule_full_redraw()

    def _finish_viewport_interaction(self) -> None:
        self.defer_expensive_viewport_layers = False
        self.fast_viewport_transform_active = False
        if self.full_redraw_after_id is None:
            return
        self.root.after_cancel(self.full_redraw_after_id)
        self.full_redraw_after_id = None

    def _run_scheduled_redraw(self) -> None:
        self.redraw_after_id = None
        self.redraw()

    def _run_full_redraw(self) -> None:
        self.full_redraw_after_id = None
        self.defer_expensive_viewport_layers = False
        self.fast_viewport_transform_active = False
        self.redraw()

    def _prepare_viewport_transform_tag(self, *, include_images: bool) -> str | None:
        transform_tag = '_viewport_transform'
        self.canvas.dtag('all', transform_tag)
        self.canvas.addtag_all(transform_tag)
        for item_id in self.canvas.find_all():
            item_type = self.canvas.type(item_id)
            if item_type == 'window' or (item_type == 'image' and not include_images):
                self.canvas.dtag(item_id, transform_tag)
        if not self.canvas.find_withtag(transform_tag):
            return None
        return transform_tag

    def _transform_cached_canvas_positions(
        self,
        transform: Callable[[tuple[float, float]], tuple[float, float]],
    ) -> None:
        self.station_canvas_positions = {
            key: transform(position)
            for key, position in self.station_canvas_positions.items()
        }
        self.path_node_canvas_positions = {
            key: transform(position)
            for key, position in self.path_node_canvas_positions.items()
        }

    def _delete_viewport_image_items(self) -> None:
        for item_id in self.canvas.find_all():
            if self.canvas.type(item_id) == 'image':
                self.canvas.delete(item_id)
        self.overlay_image_refs = []

    def _scale_viewport_canvas_items(self, anchor_x: float, anchor_y: float, ratio: float) -> None:
        transform_tag = self._prepare_viewport_transform_tag(include_images=False)
        if transform_tag is None:
            self._schedule_redraw()
            return

        self.canvas.scale(transform_tag, anchor_x, anchor_y, ratio, ratio)
        self.canvas.dtag('all', transform_tag)
        self._transform_cached_canvas_positions(
            lambda position: (
                anchor_x + ((position[0] - anchor_x) * ratio),
                anchor_y + ((position[1] - anchor_y) * ratio),
            )
        )
        self._delete_viewport_image_items()
        self._draw_world_map_render_underlay(fast_resample=True)

    def _move_viewport_canvas_items(self, delta_x: float, delta_y: float) -> None:
        self.canvas.move('all', delta_x, delta_y)
        self._transform_cached_canvas_positions(
            lambda position: (
                position[0] + delta_x,
                position[1] + delta_y,
            )
        )

    def _focused_typing_widget(self) -> tk.Widget | None:
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, (tk.Entry, tk.Text, tk.Listbox)):
            return focus_widget
        return None

    def _hotkeys_enabled(self) -> bool:
        return self._focused_typing_widget() is None

    def _set_sidebar_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.configure(state='disabled')

    def _set_route_steps_text(self, text: str) -> None:
        self._set_sidebar_text(self.route_steps_text, text)

    def _set_world_map_status_text(self, text: str) -> None:
        self.world_map_status_var.set(text)
        if hasattr(self, 'world_map_status_text'):
            self._set_sidebar_text(self.world_map_status_text, text)

    def _set_route_steps_visible(self, visible: bool) -> None:
        is_visible = bool(self.route_steps_text.winfo_manager())
        if visible == is_visible:
            return
        if visible:
            self.route_steps_text.pack(
                fill='x',
                padx=16,
                pady=(0, 12),
            )
        else:
            self.route_steps_text.pack_forget()

    def _center_toplevel(self, window: tk.Toplevel, *, width: int, height: int) -> None:
        self.root.update_idletasks()
        screen_width = max(1, self.root.winfo_screenwidth())
        screen_height = max(1, self.root.winfo_screenheight())
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def _show_line_summary_dialog(self) -> None:
        from tkinter import messagebox

        if not LINE_STOP_VARS:
            messagebox.showinfo('Line Summaries', 'No metro lines are defined yet.', parent=self.root)
            return

        dialog = tk.Toplevel(self.root)
        dialog.title('Line Summaries')
        dialog.configure(bg=BACKGROUND_COLOR)
        dialog.transient(self.root)
        self._center_toplevel(dialog, width=760, height=720)

        selected_line_var = tk.StringVar(master=dialog, value=sorted(LINE_STOP_VARS)[0])
        line_name_var = tk.StringVar(master=dialog, value=selected_line_var.get())
        line_color_var = tk.StringVar(master=dialog, value=LINE_COLORS.get(selected_line_var.get(), '#ffffff'))

        container = tk.Frame(dialog, bg=BACKGROUND_COLOR)
        container.pack(fill='both', expand=True, padx=16, pady=16)

        header_row = tk.Frame(container, bg=BACKGROUND_COLOR)
        header_row.pack(fill='x', pady=(0, 10))
        tk.Label(
            header_row,
            text='Line',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE, 'bold'),
            width=8,
            anchor='w',
        ).pack(side='left')
        line_menu = tk.OptionMenu(header_row, selected_line_var, *sorted(LINE_STOP_VARS))
        line_menu.configure(
            bg=INFO_BUTTON_BACKGROUND,
            fg=TEXT_COLOR,
            activebackground=INFO_BUTTON_ACTIVE_BACKGROUND,
            activeforeground=TEXT_COLOR,
            highlightthickness=0,
            relief='flat',
        )
        cast(tk.Menu, line_menu['menu']).configure(
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            activebackground=INFO_BUTTON_ACTIVE_BACKGROUND,
            activeforeground=TEXT_COLOR,
        )
        line_menu.pack(side='left')

        edit_row = tk.Frame(container, bg=BACKGROUND_COLOR)
        edit_row.pack(fill='x', pady=(0, 10))
        tk.Label(
            edit_row,
            text='Name',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=8,
            anchor='w',
        ).pack(side='left')
        self._make_sidebar_entry(edit_row, line_name_var).pack(side='left', fill='x', expand=True)
        tk.Label(
            edit_row,
            text='Color',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            width=7,
            anchor='e',
        ).pack(side='left', padx=(10, 4))
        self._make_sidebar_entry(edit_row, line_color_var).pack(side='left', fill='x', expand=True)
        swatch = tk.Frame(
            edit_row,
            bg=line_color_var.get(),
            width=24,
            height=24,
            highlightthickness=1,
            highlightbackground=INFO_BOX_BORDER,
        )
        swatch.pack(side='left', padx=(8, 0))
        swatch.pack_propagate(False)

        action_row = tk.Frame(container, bg=BACKGROUND_COLOR)
        action_row.pack(anchor='w', fill='x', pady=(0, 10))

        text_row = tk.Frame(container, bg=BACKGROUND_COLOR)
        text_row.pack(fill='both', expand=True)
        summary_text = tk.Text(
            text_row,
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            wrap='word',
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground=INFO_BOX_BORDER,
            font=('Menlo', 12),
        )
        summary_scrollbar = tk.Scrollbar(text_row, orient='vertical', command=summary_text.yview)
        summary_text.configure(yscrollcommand=summary_scrollbar.set)
        summary_text.pack(side='left', fill='both', expand=True)
        summary_scrollbar.pack(side='right', fill='y')

        def set_summary_text(text: str) -> None:
            summary_text.configure(state='normal')
            summary_text.delete('1.0', 'end')
            summary_text.insert('1.0', text)
            summary_text.configure(state='disabled')

        def refresh_fields() -> None:
            line_name = selected_line_var.get()
            line_name_var.set(line_name)
            line_color_var.set(LINE_COLORS.get(line_name, '#ffffff'))
            try:
                swatch.configure(bg=_normalize_line_color(line_color_var.get()))
            except ValueError:
                swatch.configure(bg=INFO_BOX_BACKGROUND)
            set_summary_text(_line_summary_text(line_name))

        def refresh_line_menu() -> None:
            menu = cast(tk.Menu, line_menu['menu'])
            menu.delete(0, 'end')
            for line_name in sorted(LINE_STOP_VARS):
                menu.add_command(label=line_name, command=lambda value=line_name: selected_line_var.set(value))

        def apply_color() -> None:
            try:
                normalized_color = set_metro_line_color(selected_line_var.get(), line_color_var.get())
            except ValueError as exc:
                messagebox.showerror('Could Not Save Line Color', str(exc), parent=dialog)
                return
            line_color_var.set(normalized_color)
            refresh_fields()
            self.redraw()

        def apply_name() -> None:
            try:
                new_line_name = rename_metro_line(selected_line_var.get(), line_name_var.get())
            except ValueError as exc:
                messagebox.showerror('Could Not Rename Line', str(exc), parent=dialog)
                return
            selected_line_var.set(new_line_name)
            refresh_line_menu()
            refresh_fields()
            self.route_controls_dirty = True
            self.route_dirty = True
            self.priority_dirty = True
            self.stats_dirty = True
            self.railway_finish_dirty = True
            self.redraw()

        def reorder_stations() -> None:
            reorder_dialog = getattr(self, '_show_reorder_metro_line_dialog', None)
            if not callable(reorder_dialog):
                messagebox.showerror(
                    'Reorder Stations Unavailable',
                    'Metro station editing tools are not loaded.',
                    parent=dialog,
                )
                return

            def after_reorder(saved_line_name: str) -> None:
                selected_line_var.set(saved_line_name)
                refresh_fields()

            reorder_dialog(selected_line_var.get(), on_saved=after_reorder)

        self._make_sidebar_button(action_row, text='Save Name', command=apply_name).pack(side='left')
        self._make_sidebar_button(action_row, text='Save Color', command=apply_color).pack(side='left', padx=(10, 0))
        self._make_sidebar_button(
            action_row,
            text='Reorder Stations',
            command=reorder_stations,
        ).pack(side='left', padx=(10, 0))
        self._make_sidebar_button(action_row, text='Close', command=dialog.destroy).pack(side='right')

        selected_line_var.trace_add('write', lambda *_args: refresh_fields())
        refresh_fields()

    def _post_world_map_task_progress(
        self,
        message: str,
        rendered_map: bool,
    ) -> None:
        message_kind: Literal['progress', 'rendered'] = 'rendered' if rendered_map else 'progress'
        self.world_map_task_queue.put((message_kind, True, message))

    def _world_map_active_target_bounds_for_center(
        self,
        target: tuple[int, int],
    ) -> tuple[int, int, int, int] | None:
        try:
            from worldgen.config import load_config
            from worldgen.generator import _teleport_target_world_bounds

            return _teleport_target_world_bounds(load_config(), target)
        except Exception:
            return None

    def _set_world_map_active_target(
        self,
        target: tuple[int, int] | None,
    ) -> bool:
        next_bounds = (
            self._world_map_active_target_bounds_for_center(target)
            if target is not None
            else None
        )
        if next_bounds == self.world_map_active_target_bounds:
            return False
        self.world_map_active_target_bounds = next_bounds
        return True

    def _update_world_map_active_target_from_message(self, message: str) -> bool:
        target = _world_map_active_target_from_text(message)
        if target is None:
            return False
        return self._set_world_map_active_target(target)

    def _selected_world_map_mode_key(self) -> str:
        return _world_map_mode_key_for_label(self.world_map_mode_var.get())

    def _on_world_map_mode_changed(self, *_args: object) -> None:
        self._invalidate_world_map_render_cache()
        self._set_world_map_auto_fill_button('idle')
        self._set_world_map_status_text(
            _world_map_cached_status_text(self._selected_world_map_mode_key())
        )
        self.redraw()

    def _start_world_map_task(
        self,
        task_label: str,
        worker: Callable[[], str],
        *,
        on_finished: Callable[[bool, str], None] | None = None,
    ) -> None:
        if self.world_map_task_running:
            self._set_world_map_status_text('World map task already running.')
            return

        self.world_map_task_running = True
        self._set_world_map_active_target(None)
        self.world_map_task_completion_callback = on_finished
        self._set_world_map_status_text(f'{task_label}...')

        def run_worker() -> None:
            try:
                message = worker()
            except Exception as exc:
                self.world_map_task_queue.put(('done', False, f'{task_label} failed.\n{exc}'))
                return
            self.world_map_task_queue.put(('done', True, message))

        threading.Thread(target=run_worker, daemon=True).start()
        self.root.after(200, self._poll_world_map_task)

    def _poll_world_map_task(self) -> None:
        try:
            message_kind, succeeded, message = self.world_map_task_queue.get_nowait()
        except queue.Empty:
            if self.world_map_task_running:
                self.root.after(200, self._poll_world_map_task)
            return

        if message_kind in ('progress', 'rendered'):
            target_changed = self._update_world_map_active_target_from_message(message)
            if self.world_map_auto_fill_stop_requested:
                message = (
                    f'{message.rstrip()}\n\n'
                    'Stop requested. The current step will finish, then Auto Fill will stop.'
                )
            self._set_world_map_status_text(message)
            if message_kind == 'rendered':
                self._invalidate_world_map_render_cache()
                self.stats_dirty = True
                self.redraw()
            elif target_changed:
                self.redraw()
            if self.world_map_task_running:
                self.root.after(200, self._poll_world_map_task)
            return

        self.world_map_task_running = False
        target_changed = self._set_world_map_active_target(None)
        completion_callback = self.world_map_task_completion_callback
        self.world_map_task_completion_callback = None
        self._set_world_map_status_text(message)
        if succeeded:
            self._invalidate_world_map_render_cache()
            self.stats_dirty = True
            self._set_world_map_status_text(
                f'{message}\n\n'
                f'{_world_map_cached_status_text(self._selected_world_map_mode_key())}'
            )
            self.redraw()
        elif target_changed:
            self.redraw()
        if completion_callback is not None:
            completion_callback(succeeded, message)

    def _refresh_world_map_live_status(self) -> None:
        mode_key = self._selected_world_map_mode_key()
        self._start_world_map_task(
            'Refreshing world map status',
            lambda: _world_map_live_status_text(mode_key),
        )

    def _generate_world_map_world(self) -> None:
        self._start_world_map_task('Generating Bedrock world', _world_map_generate_world_text)

    def _load_world_map_chunks(self) -> None:
        mode_key = self._selected_world_map_mode_key()
        self._start_world_map_task(
            f'Loading {_world_map_mode_label(mode_key)} chunks',
            lambda: _world_map_load_chunks_text_with_progress(
                mode_key,
                progress_callback=self._post_world_map_task_progress,
            ),
        )

    def _render_world_map(self) -> None:
        mode_key = self._selected_world_map_mode_key()
        self._start_world_map_task(
            f'Rendering {_world_map_mode_label(mode_key)}',
            lambda: _world_map_render_text(mode_key),
        )

    def _set_world_map_auto_fill_button(self, state: Literal['idle', 'running', 'stopping']) -> None:
        if not hasattr(self, 'world_map_auto_fill_button'):
            return

        if state == 'idle':
            mode_key = self._selected_world_map_mode_key()
            button_text = 'Start Auto Fill' if mode_key == 'local_seed_surface' else 'Load + Render'
            self._configure_sidebar_button(
                self.world_map_auto_fill_button,
                text=button_text,
                command=self._start_auto_fill_world_map,
            )
            return

        if state == 'running':
            self._configure_sidebar_button(
                self.world_map_auto_fill_button,
                text='Stop Auto Fill',
                command=self._request_stop_auto_fill_world_map,
            )
            return

        self._configure_sidebar_button(
            self.world_map_auto_fill_button,
            text='Stopping...',
            command=lambda: None,
        )

    def _start_auto_fill_world_map(self) -> None:
        if self.world_map_task_running:
            self._set_world_map_status_text('World map task already running.')
            return

        mode_key = self._selected_world_map_mode_key()
        if mode_key != 'local_seed_surface':
            self._start_world_map_task(
                f'Loading and rendering {_world_map_mode_label(mode_key)}',
                lambda: _world_map_load_and_render_text(
                    mode_key,
                    progress_callback=self._post_world_map_task_progress,
                ),
            )
            return

        stop_event = threading.Event()
        self.world_map_auto_fill_stop_event = stop_event
        self.world_map_auto_fill_running = True
        self.world_map_auto_fill_stop_requested = False
        self._set_world_map_auto_fill_button('running')

        self._start_world_map_task(
            'Auto filling world map',
            lambda: _world_map_auto_fill_until_stopped_text(
                stop_event,
                progress_callback=self._post_world_map_task_progress,
            ),
            on_finished=self._finish_auto_fill_world_map,
        )

    def _request_stop_auto_fill_world_map(self) -> None:
        if self.world_map_auto_fill_stop_event is None or not self.world_map_auto_fill_running:
            return

        self.world_map_auto_fill_stop_event.set()
        if self.world_map_auto_fill_stop_requested:
            return

        self.world_map_auto_fill_stop_requested = True
        self._set_world_map_auto_fill_button('stopping')
        current_status = self.world_map_status_var.get().rstrip()
        self._set_world_map_status_text(
            f'{current_status}\n\nStop requested. The current step will finish, then Auto Fill will stop.'
        )

    def _finish_auto_fill_world_map(self, _succeeded: bool, _message: str) -> None:
        self.world_map_auto_fill_stop_event = None
        self.world_map_auto_fill_running = False
        self.world_map_auto_fill_stop_requested = False
        self._set_world_map_auto_fill_button('idle')
        self.redraw()

    def _stop_world_map_world(self) -> None:
        self._start_world_map_task('Stopping Bedrock worldgen container', _world_map_stop_world_text)

    def _repair_world_map_db(self) -> None:
        self._start_world_map_task('Repairing Bedrock LevelDB folder', _world_map_repair_db_text)

    def _priority_need_counts(self, entries: list[tuple[str, str]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for stop_var, _text in entries:
            stop = STOPS_BY_VAR.get(stop_var)
            if stop is None:
                continue
            for task_name in _missing_station_tasks(stop):
                counts[task_name] = counts.get(task_name, 0) + 1
        return counts

    def _priority_filter_task(self) -> str | None:
        return self.priority_filter_options.get(self.priority_filter_var.get())

    def _select_priority_filter(self, label: str) -> None:
        self.priority_filter_var.set(label)
        self.priority_dirty = True
        self.redraw()

    def _refresh_priority_filter_menu(self, entries: list[tuple[str, str]]) -> None:
        if not hasattr(self, 'priority_filter_menu'):
            return

        selected_task = self._priority_filter_task()
        counts = self._priority_need_counts(entries)
        ordered_tasks = sorted(
            counts,
            key=lambda task_name: (
                -counts[task_name],
                -CONNECTED_TASK_WEIGHTS.get(task_name, 0),
                PRIORITY_NEED_LABELS.get(task_name, task_name).lower(),
            ),
        )
        self.priority_filter_options = {PRIORITY_FILTER_ALL_LABEL: None}
        labels = [PRIORITY_FILTER_ALL_LABEL]
        selected_label = PRIORITY_FILTER_ALL_LABEL
        for task_name in ordered_tasks:
            label = f'{PRIORITY_NEED_LABELS.get(task_name, task_name.title())} ({counts[task_name]})'
            self.priority_filter_options[label] = task_name
            labels.append(label)
            if task_name == selected_task:
                selected_label = label

        self.priority_filter_var.set(selected_label)

        menu = self._option_menu_widget(self.priority_filter_menu)
        menu.delete(0, 'end')
        for label in labels:
            menu.add_command(label=label, command=lambda selected=label: self._select_priority_filter(selected))

    def _priority_filter_entries(self, entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
        selected_task = self._priority_filter_task()
        if selected_task is None:
            self.priority_highlight_stop_vars = set()
            return entries

        filtered_entries = [
            (stop_var, text)
            for stop_var, text in entries
            if selected_task in _missing_station_tasks(STOPS_BY_VAR[stop_var])
        ]
        self.priority_highlight_stop_vars = {stop_var for stop_var, _text in filtered_entries}
        return filtered_entries

    def _populate_priority_list(self, entries: list[tuple[str, str]]) -> None:
        if not hasattr(self, 'priority_list_frame'):
            return

        for child in self.priority_list_frame.winfo_children():
            child.destroy()

        if not entries:
            tk.Label(
                self.priority_list_frame,
                text='Nothing to work on right now.',
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
                anchor='w',
                justify='left',
                wraplength=SIDEBAR_WIDTH - 80,
            ).pack(fill='x')
            return

        for index, (stop_var, text) in enumerate(entries):
            item_label = tk.Label(
                self.priority_list_frame,
                text=text,
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
                anchor='w',
                justify='left',
                wraplength=SIDEBAR_WIDTH - 80,
                cursor='hand2',
            )
            item_label.pack(fill='x', pady=(0, 8 if index < len(entries) - 1 else 0))
            item_label.bind('<Enter>', lambda _event, label=item_label: label.configure(fg=PATH_NODE_LABEL_COLOR))
            item_label.bind('<Leave>', lambda _event, label=item_label: label.configure(fg=TEXT_COLOR))
            item_label.bind('<Button-1>', lambda _event, target_stop_var=stop_var: self._focus_stop(target_stop_var))

    def _refresh_station_stats(self) -> None:
        self.stats_summary_var.set(_station_progress_summary_text())

    def _priority_origin_key(self) -> str:
        default_key = _blackport_stop().var
        candidate_keys: list[str] = []
        if self.route_request is not None:
            candidate_keys.append(self.route_request[0])
        for candidate_key in candidate_keys:
            if _route_costs_from_endpoint_key(candidate_key, **self._route_graph_options()):
                return candidate_key
        return default_key

    def _refresh_priority_list(self) -> None:
        origin_key = self._priority_origin_key()
        origin_label = _display_label_for_endpoint_key(origin_key)
        self.priority_summary_var.set(
            f'From {origin_label}. Click a station below.'
        )
        entries = _priority_list_entries(origin_key, **self._route_graph_options())
        _write_priority_list_csv(entries)
        self._refresh_priority_filter_menu(entries)
        self._populate_priority_list(self._priority_filter_entries(entries))

    def _select_railway_finish_line(self, line_name: str) -> None:
        self.railway_finish_line_var.set(line_name)
        self._refresh_railway_finish_status()
        self.redraw()

    def _populate_railway_finish_line_menu(self, line_names: tuple[str, ...]) -> None:
        menu = self._option_menu_widget(self.railway_finish_line_menu)
        menu.delete(0, 'end')
        if not line_names:
            menu.add_command(label='No unfinished lines', command=lambda: None)
            return
        for line_name in line_names:
            menu.add_command(
                label=f'Line {line_name}',
                command=lambda selected=line_name: self._select_railway_finish_line(selected),
            )

    def _refresh_railway_finish_status(self) -> None:
        line_name = self.railway_finish_line_var.get().strip()
        line_names = _railway_finish_line_names()
        if line_name not in line_names:
            self.railway_finish_status_var.set('Choose an unfinished connected line.')
            return
        self.railway_finish_status_var.set(_railway_finish_line_status_text(line_name))

    def _refresh_railway_finish_controls(self) -> None:
        line_names = _railway_finish_line_names()
        self._populate_railway_finish_line_menu(line_names)

        current_line_name = self.railway_finish_line_var.get().strip()
        if current_line_name not in line_names:
            next_line_name = _next_unfinished_railway_finish_line()
            self.railway_finish_line_var.set(next_line_name or '')

        self._refresh_railway_finish_status()
        self.railway_finish_progress_var.set(_railway_finish_progress_summary_text())

    def _on_railway_finish_mode_changed(self) -> None:
        self.railway_finish_dirty = True
        self._refresh_railway_finish_controls()
        self.railway_finish_dirty = False
        if self.railway_finish_mode_var.get():
            self.show_railway_finish_unfinished_view()
            return
        self.redraw()

    def _on_railway_finish_submit(self, _event: object) -> str:
        self._save_railway_finish_point()
        return 'break'

    def _save_railway_finish_point(self) -> None:
        from tkinter import messagebox

        line_name = self.railway_finish_line_var.get().strip()
        if line_name not in LINE_STOP_VARS:
            messagebox.showerror(
                'Choose a Line',
                'Choose a connected line before saving a finished railway point.',
                parent=self.root,
            )
            return

        coordinates_text = self.railway_finish_coordinates_var.get().strip()
        coordinates = _parse_coordinate_text(coordinates_text)
        if coordinates is None:
            messagebox.showerror(
                'Invalid Coordinates',
                'Enter Minecraft coordinates as x, y.',
                parent=self.root,
            )
            return

        if _line_finish_location_for_coordinates(line_name, coordinates) is None:
            messagebox.showerror(
                'Coordinate Not On Line',
                f'({coordinates[0]}, {coordinates[1]}) is not on Line {line_name}. Try another coordinate.',
                parent=self.root,
            )
            return

        try:
            set_railway_finish_progress(line_name, coordinates)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Railway Finish', str(exc), parent=self.root)
            return

        self.railway_finish_coordinates_var.set('')
        self.railway_finish_status_var.set(_railway_finish_line_status_text(line_name))
        self.stats_dirty = True
        self.priority_dirty = True
        self.route_controls_dirty = True
        self.route_dirty = True
        self.railway_finish_dirty = True
        if self.railway_finish_mode_var.get():
            self.show_railway_finish_unfinished_view()
            return
        self.redraw()

    def _switch_railway_finish_origin(self) -> None:
        from tkinter import messagebox

        line_name = self.railway_finish_line_var.get().strip()
        if line_name not in LINE_STOP_VARS:
            messagebox.showerror(
                'Choose a Line',
                'Choose an unfinished connected line before switching the origin.',
                parent=self.root,
            )
            return

        try:
            switch_railway_finish_origin(line_name)
        except ValueError as exc:
            messagebox.showerror('Could Not Switch Origin', str(exc), parent=self.root)
            return

        self.railway_finish_dirty = True
        self._refresh_railway_finish_controls()
        self.railway_finish_dirty = False
        self.redraw()

    def _connected_stop_labels(self) -> list[str]:
        return sorted(
            (stop.lbl for stop in METRO_STOPS if stop.is_connected),
            key=str.lower,
        )

    def _search_matches(self, query: str) -> list[MetroStop]:
        normalized_query = _normalize_stop_identity(query)
        if not normalized_query:
            return []

        ranked_matches: list[tuple[tuple[int, int, str], MetroStop]] = []
        for stop in METRO_STOPS:
            normalized_label = _normalize_stop_identity(stop.lbl)
            normalized_display_label = _normalize_stop_identity(_display_label(stop.lbl))
            normalized_var = _normalize_stop_identity(stop.var.removeprefix('P_'))

            if normalized_query in (normalized_label, normalized_display_label):
                rank = (0, len(stop.lbl), stop.lbl.lower())
            elif normalized_query == normalized_var:
                rank = (1, len(stop.var), stop.lbl.lower())
            elif any(
                candidate.startswith(normalized_query)
                for candidate in (normalized_label, normalized_display_label)
            ):
                rank = (2, len(stop.lbl), stop.lbl.lower())
            elif normalized_var.startswith(normalized_query):
                rank = (3, len(stop.var), stop.lbl.lower())
            elif any(
                normalized_query in candidate
                for candidate in (normalized_label, normalized_display_label)
            ):
                rank = (4, len(stop.lbl), stop.lbl.lower())
            elif normalized_query in normalized_var:
                rank = (5, len(stop.var), stop.lbl.lower())
            else:
                continue

            ranked_matches.append((rank, stop))

        ranked_matches.sort(key=lambda item: item[0])
        return [stop for _rank, stop in ranked_matches]

    def _refresh_search_results(self) -> None:
        query = self.search_var.get().strip()
        self.search_match_stop_vars = []

        if not query:
            self.search_status_var.set('Search stations by village name or station code.')
            return

        matches = self._search_matches(query)
        if not matches:
            self.search_status_var.set('No station matches that search.')
            return

        visible_matches = matches[:8]
        self.search_match_stop_vars = [stop.var for stop in visible_matches]
        if len(matches) == 1:
            self.search_status_var.set('Press Enter or click Go to jump to the match.')
        elif len(matches) > len(visible_matches):
            self.search_status_var.set(
                f'{len(matches)} matches. Use the popup or press Enter to jump to the best match.'
            )
        else:
            self.search_status_var.set(
                f'{len(matches)} matches. Press Enter or click Go to jump to the best match.'
            )

    def _center_on_world_point(self, point: tuple[int, int]) -> None:
        base_x, base_y = self._world_to_base_canvas(point)
        center_x = self.width / 2
        center_y = self.height / 2
        self.pan_x = -((base_x - center_x) * self.zoom)
        self.pan_y = -((base_y - center_y) * self.zoom)

    def _visible_line_names(self) -> set[str]:
        return set(LINE_COLORS)

    def _stop_visible_line_names(
        self,
        stop: MetroStop,
        visible_line_names: set[str],
    ) -> tuple[str, ...]:
        return _visible_stop_line_names(stop, visible_line_names)

    def _stop_fill_for_visible_lines(
        self,
        visible_line_names: tuple[str, ...],
    ) -> str:
        return _fill_for_visible_line_names(visible_line_names)

    def _focus_stop(self, stop_var: str) -> None:
        if stop_var not in STOPS_BY_VAR:
            return
        stop = STOPS_BY_VAR[stop_var]
        self.selected_stop_var = stop.var
        self.selected_path_node_key = None
        self._clear_metro_segment_selection()
        self._center_on_world_point(stop.plot_coordinates)
        self.redraw()

    def _jump_to_first_search_result(self) -> None:
        self._refresh_search_results()
        if not self.search_match_stop_vars:
            return

        self._hide_suggestion_popup()
        stop_var = self.search_match_stop_vars[0]
        self.search_var.set(STOPS_BY_VAR[stop_var].lbl)
        self.search_status_var.set(f'Centered on {_display_label(STOPS_BY_VAR[stop_var].lbl)}.')
        self._focus_stop(stop_var)

    def _jump_to_selected_search_result(self) -> None:
        self._jump_to_first_search_result()

    def _default_route_start_label(self, connected_labels: list[str]) -> str:
        blackport_label = _blackport_stop().lbl
        if blackport_label in connected_labels:
            return blackport_label
        return connected_labels[0]

    def _destination_labels_for_origin(self, origin_var: str | None) -> list[str]:
        connected_stops = [stop for stop in METRO_STOPS if stop.is_connected]
        if origin_var is None:
            return sorted((stop.lbl for stop in connected_stops), key=str.lower)

        route_costs = _route_costs_from(origin_var, **self._route_graph_options())
        return [
            stop.lbl
            for stop in sorted(
                (stop for stop in connected_stops if stop.var != origin_var),
                key=lambda stop: (
                    route_costs.get(stop.var, (10**12, 10**12))[0],
                    route_costs.get(stop.var, (10**12, 10**12))[1],
                    stop.lbl.lower(),
                ),
            )
        ]

    def _populate_option_menu(
        self,
        option_menu: tk.Menubutton,
        variable: tk.StringVar,
        values: list[str],
    ) -> None:
        menu = self._option_menu_widget(option_menu)
        menu.delete(0, 'end')
        for value in values:
            menu.add_command(label=value, command=lambda selected=value: variable.set(selected))

    def _refresh_route_controls(self) -> None:
        self.route_controls_updating = True
        try:
            connected_labels = self._connected_stop_labels()
            if not connected_labels:
                return

            if self.route_request is not None:
                return

            if not self.route_start_var.get().strip() and not self.route_end_var.get().strip():
                self.route_start_var.set(self._default_route_start_label(connected_labels))
        finally:
            self.route_controls_updating = False

    def _on_route_start_changed(self, *_args: object) -> None:
        return

    def _on_route_input_changed(self, *_args: object) -> None:
        if self.route_controls_updating:
            return
        if self.route_request is None and self.current_route is None:
            return
        self.route_request = None
        self.current_route = None
        self.route_dirty = False
        self.priority_dirty = True
        if hasattr(self, 'route_summary_var'):
            self.route_summary_var.set('Choose two stations or coordinates.')
        if hasattr(self, 'route_steps_text'):
            self._set_route_steps_text('Enter or select a start and destination, then press Route.')
            self._set_route_steps_visible(False)

    def _on_search_changed(self, *_args: object) -> None:
        self._refresh_search_results()

    def _on_search_submit(self, _event: object) -> str:
        self._jump_to_first_search_result()
        return 'break'

    def _on_search_result_activate(self, _event: object) -> str:
        self._jump_to_selected_search_result()
        return 'break'

    def _on_route_submit(self, _event: object) -> str:
        self._plan_route()
        return 'break'

    def _route_instructions_text(self, route: RouteResult) -> str:
        start_label = _display_label_for_endpoint_key(route.start_key)
        end_label = _display_label_for_endpoint_key(route.end_key)
        if not route.steps:
            return (
                f'You are already at {start_label}.\n'
                f'Track distance: {_format_track_distance(0)}.'
            )

        rail_distance = sum(
            step.distance
            for step in route.steps
            if step.kind in {'ride', 'connector'}
        )
        lines = [
            f'Track distance: {_format_track_distance(route.total_distance)}',
            f'Rail time estimate: {_format_travel_time_for_distance(rail_distance)}',
            f'Interchanges: {route.total_interchanges}',
            '',
        ]
        step_number = 1
        for step in route.steps:
            start_step_label = _display_label_for_endpoint_key(step.start_key)
            end_step_label = _display_label_for_endpoint_key(step.end_key)

            if step.kind == 'ride':
                stop_word = 'stop' if step.stop_count == 1 else 'stops'
                lines.append(
                    f'{step_number}. Take Line {step.line_name} from {start_step_label} '
                    f'to {end_step_label} for {_format_distance_and_time(step.distance)} '
                    f'({step.stop_count} {stop_word}).'
                )
            elif step.kind == 'transfer':
                lines.append(
                    f'{step_number}. Transfer at {start_step_label} to Line {step.line_name}.'
                )
            elif step.kind == 'connector':
                lines.append(
                    f'{step_number}. Take {step.display_name.lower()} from {start_step_label} '
                    f'to {end_step_label} for {_format_distance_and_time(step.distance)}.'
                )
            elif step.kind == 'fly':
                lines.append(
                    f'{step_number}. Fly directly from {start_step_label} to {end_step_label} '
                    f'for {_format_track_distance(step.distance)}.'
                )
            else:
                if step.label and step.label != 'Walk':
                    lines.append(
                        f'{step_number}. Walk on {step.label} from {start_step_label} '
                        f'to {end_step_label} for {_format_track_distance(step.distance)}.'
                    )
                else:
                    lines.append(
                        f'{step_number}. Walk from {start_step_label} to {end_step_label} '
                        f'for {_format_track_distance(step.distance)}.'
                    )
            step_number += 1

        lines.append('')
        unfinished_line_names = _unfinished_route_line_names(route)
        if unfinished_line_names:
            line_word = 'line is' if len(unfinished_line_names) == 1 else 'lines are'
            lines.append(
                f'Warning: the {_format_line_name_list(unfinished_line_names)} {line_word} '
                'not fully constructed for this route. Consider direct flying instead.'
            )
            lines.append('')
        lines.append(
            f'Route from {start_label} to {end_label}.'
        )
        return '\n'.join(lines)

    def _refresh_current_route(self) -> None:
        if self.route_request is None:
            self.current_route = None
            self.route_summary_var.set('Choose two stations or coordinates.')
            self._set_route_steps_text('Enter or select a start and destination, then press Route.')
            self._set_route_steps_visible(False)
            return

        start_key, end_key = self.route_request
        if _path_endpoint_from_key(start_key) is None or _path_endpoint_from_key(end_key) is None:
            self.current_route = None
            self.route_request = None
            self.priority_dirty = True
            self.route_summary_var.set('Choose two stations or coordinates.')
            self._set_route_steps_text('The saved route endpoints are no longer available.')
            self._set_route_steps_visible(False)
            return

        route = _find_route(start_key, end_key, **self._route_search_options())
        if route is None:
            self.current_route = None
            self.route_summary_var.set(
                f'No route from {_display_label_for_endpoint_key(start_key)} '
                f'to {_display_label_for_endpoint_key(end_key)}.'
            )
            self._set_route_steps_text(
                'No route exists for those endpoints with the current metro + walking path data.'
            )
            self._set_route_steps_visible(False)
            return

        self.current_route = route
        self.route_summary_var.set(
            f'{_display_label_for_endpoint_key(start_key)} to '
            f'{_display_label_for_endpoint_key(end_key)}\n'
            f'{_format_track_distance(route.total_distance)}, {route.total_interchanges} interchange(s)'
        )
        self._set_route_steps_text(self._route_instructions_text(route))
        self._set_route_steps_visible(bool(route.steps))

    def _plan_route(self) -> None:
        start_text = self.route_start_var.get().strip()
        end_text = self.route_end_var.get().strip()
        if not start_text or not end_text:
            self.route_summary_var.set('Choose two stations or coordinates.')
            self._set_route_steps_text('Select both a start and a destination.')
            self._set_route_steps_visible(False)
            self.current_route = None
            self.route_request = None
            return

        start_endpoint = _path_endpoint_from_runtime_identifier(start_text)
        end_endpoint = _path_endpoint_from_runtime_identifier(end_text)
        if start_endpoint is None or end_endpoint is None:
            self.route_summary_var.set('Choose two stations or coordinates.')
            self._set_route_steps_text(
                'Enter each endpoint as a station label / var or Minecraft coordinates like x, y.'
            )
            self._set_route_steps_visible(False)
            self.current_route = None
            self.route_request = None
            return

        self.route_request = (start_endpoint.key, end_endpoint.key)
        self._hide_suggestion_popup()
        self.priority_dirty = True
        self.route_dirty = True
        self.redraw()

    def _swap_route_endpoints(self) -> None:
        start_label = self.route_start_var.get()
        end_label = self.route_end_var.get()
        self.route_controls_updating = True
        try:
            self.route_start_var.set(end_label)
            self.route_end_var.set(start_label)
        finally:
            self.route_controls_updating = False
        self.route_controls_dirty = True
        if start_label and end_label:
            self._plan_route()

    def _clear_route(self) -> None:
        self.route_request = None
        self.current_route = None
        self._hide_suggestion_popup()
        self._set_route_steps_visible(False)
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.redraw()

    def _fill_entry_from_selected_stop(self, variable: tk.StringVar) -> None:
        if self.selected_stop_var is None or self.selected_stop_var not in STOPS_BY_VAR:
            return
        variable.set(STOPS_BY_VAR[self.selected_stop_var].lbl)

    def _clear_walk_path_fields(self) -> None:
        self.walk_path_from_var.set('')
        self.walk_path_to_var.set('')
        self.walk_path_label_var.set('')
        self.path_node_coordinates_var.set('')
        self.path_node_label_var.set('')

    def _active_path_edge(self) -> ExtraEdgeDefinition | None:
        if self.active_path_edge_id is None:
            return None
        return next((edge for edge in EXTRA_EDGES if edge.id == self.active_path_edge_id), None)

    def _set_active_path_edge(self, extra_edge: ExtraEdgeDefinition | None) -> None:
        self.active_path_edge_id = None if extra_edge is None else extra_edge.id
        self.path_edge_list_dirty = True
        if extra_edge is None:
            self.path_click_status_var.set('Turn on map pathing to add nodes and drag paths on the map.')
            return
        self.path_click_status_var.set(
            f'Editing {_extra_edge_full_summary(extra_edge)}. Click the line to add a point, or a middle point to remove it.'
        )

    def _on_path_click_mode_changed(self) -> None:
        self._clear_path_drag()
        if self.path_click_mode_var.get():
            active_edge = self._active_path_edge()
            if active_edge is None:
                self.path_click_status_var.set(
                    'Click empty map space to add a node. Drag from an existing station/node to another to add a path.'
                )
            else:
                self._set_active_path_edge(active_edge)
        else:
            self.path_click_status_var.set('Map pathing is off. Typed coordinates still work.')
        self.redraw()

    def _edit_path_edge_points(self, extra_edge: ExtraEdgeDefinition) -> None:
        self.path_click_mode_var.set(True)
        self._set_active_path_edge(extra_edge)
        self.selected_stop_var = None
        self.selected_path_node_key = None
        self._clear_metro_segment_selection()
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = None
        self.show_cursor_guides = False
        self.redraw()

    def _edit_path_edge_label(self, extra_edge: ExtraEdgeDefinition) -> None:
        from tkinter import messagebox, simpledialog

        new_label = simpledialog.askstring(
            'Road Name',
            'Enter a road name for this walking path.\nLeave blank to clear it:',
            initialvalue=extra_edge.label or '',
            parent=self.root,
        )
        if new_label is None:
            return

        try:
            set_extra_edge_label(extra_edge.id, new_label)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Road Name', str(exc), parent=self.root)
            return

        refreshed_edge = self._active_path_edge()
        if refreshed_edge is not None:
            self._set_active_path_edge(refreshed_edge)
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.redraw()

    def _export_visible_block_png(self) -> None:
        from tkinter import messagebox

        messagebox.showinfo(
            'Export Block PNG',
            'Block-level PNG export is not available until UI extensions are loaded.',
            parent=self.root,
        )

    def _add_path_node_from_sidebar(self) -> None:
        from tkinter import messagebox

        coordinates_text = self.path_node_coordinates_var.get().strip()
        if not coordinates_text:
            messagebox.showerror(
                'Missing Path Node Coordinates',
                'Enter Minecraft coordinates as x, y.',
                parent=self.root,
            )
            return

        node_label = self.path_node_label_var.get().strip() or None
        try:
            add_path_node(coordinates_text, label=node_label)
        except ValueError as exc:
            messagebox.showerror('Could Not Add Path Node', str(exc), parent=self.root)
            return

        self.path_node_coordinates_var.set('')
        self.path_node_label_var.set('')
        self.redraw()

    def _add_path_for_selected_node(self, kind: ExtraEdgeKind) -> None:
        from tkinter import messagebox, simpledialog

        path_node = self._selected_path_node()
        if path_node is None:
            return

        other_endpoint = simpledialog.askstring(
            'Add Path Edge',
            'Enter the other endpoint as a station label / var, path-node label / id, or x, y:',
            parent=self.root,
        )
        if other_endpoint is None:
            return

        other_endpoint = other_endpoint.strip()
        if not other_endpoint:
            messagebox.showerror(
                'Invalid Endpoint',
                'Enter a station label / var, path-node label / id, or coordinates like x, y.',
                parent=self.root,
            )
            return

        label_value = simpledialog.askstring(
            'Add Path Edge',
            'Optional label (leave blank for default):',
            parent=self.root,
        )
        edge_label = None if label_value is None else (label_value.strip() or None)

        try:
            add_extra_edge(
                f'{path_node.x}, {path_node.y}',
                other_endpoint,
                kind,
                label=edge_label,
            )
        except ValueError as exc:
            messagebox.showerror('Could Not Add Path Edge', str(exc), parent=self.root)
            return

        self.selected_path_node_key = path_node.key
        self._refresh_after_path_edit()

    def _remove_selected_path_node(self) -> None:
        from tkinter import messagebox

        path_node = self._selected_path_node()
        if path_node is None:
            return

        connected_edge_count = len(_extra_edges_for_endpoint_key(path_node.key))
        try:
            remove_path_node(path_node.input_text if path_node.is_explicit else f'{path_node.x}, {path_node.y}')
        except ValueError as exc:
            messagebox.showerror('Could Not Remove Path Node', str(exc), parent=self.root)
            return

        self.selected_path_node_key = None
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.path_click_status_var.set(
            f'Removed {path_node.display_label}. '
            f'Also deleted {connected_edge_count} connected path{"s" if connected_edge_count != 1 else ""}.'
        )
        self.redraw()

    def _edit_selected_path_node_coordinates(self) -> None:
        if self.selected_path_node_key is None:
            return

        from tkinter import messagebox, simpledialog

        path_node = self._selected_path_node()
        if path_node is None:
            return

        new_coordinates = simpledialog.askstring(
            'Edit Node',
            'Enter new Minecraft coordinates as x, y:',
            initialvalue=f'{path_node.x}, {path_node.y}',
            parent=self.root,
        )
        if new_coordinates is None:
            return

        parsed_coordinates = _parse_coordinate_text(new_coordinates.strip())
        if parsed_coordinates is None:
            messagebox.showerror(
                'Invalid Coordinates',
                'Enter coordinates in the format: x, y',
                parent=self.root,
            )
            return

        identifier = path_node.input_text if path_node.is_explicit else f'{path_node.x}, {path_node.y}'
        try:
            move_path_node(identifier, parsed_coordinates)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Node', str(exc), parent=self.root)
            return

        self.selected_stop_var = None
        self.selected_path_node_key = _coordinate_endpoint_key(parsed_coordinates[0], parsed_coordinates[1])
        self._clear_metro_segment_selection()
        self.cursor_readout_coordinates = parsed_coordinates
        self.show_cursor_guides = False
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.redraw()

    def _add_walk_path_from_sidebar(self) -> None:
        from tkinter import messagebox

        first_identifier = self.walk_path_from_var.get().strip()
        second_identifier = self.walk_path_to_var.get().strip()
        if not first_identifier or not second_identifier:
            messagebox.showerror(
                'Missing Walk Path Endpoint',
                'Enter both walking-path endpoints as a station label / var or x, y.',
                parent=self.root,
            )
            return

        edge_label = self.walk_path_label_var.get().strip() or None
        try:
            add_extra_edge(
                first_identifier,
                second_identifier,
                'walk',
                label=edge_label,
            )
        except ValueError as exc:
            messagebox.showerror('Could Not Add Walk Path', str(exc), parent=self.root)
            return

        self._clear_walk_path_fields()
        self._refresh_after_path_edit()

    def _plot_transform(self) -> tuple[int, int, int, int, float]:
        return _plot_transform(width=self.width, height=self.height, padding=self.padding)

    def _max_zoom(self) -> float:
        _, _, _, _, scale = self._plot_transform()
        visible_width = max(self.width - (self.padding * 2), 1) / scale
        visible_height = max(self.height - (self.padding * 2), 1) / scale
        return max(DEFAULT_ZOOM, max(visible_width, visible_height) / MAX_VISIBLE_BLOCKS_AT_MAX_ZOOM)

    def _target_map_plot_bounds(self) -> tuple[float, float, float, float] | None:
        try:
            from worldgen.config import default_config_path, load_config

            config_path = default_config_path()
            config_stat = _file_stat_key(config_path)
            if (
                config_stat is not None
                and config_stat == self.target_map_bounds_cache_stat
                and self.target_map_plot_bounds_cache is not None
            ):
                return self.target_map_plot_bounds_cache

            render = load_config(config_path).render
            bounds = (
                float(render.min_x),
                float(render.max_x),
                float(-render.max_z),
                float(-render.min_z),
            )
            self.target_map_bounds_cache_stat = config_stat
            self.target_map_plot_bounds_cache = bounds
            return bounds
        except Exception:
            self.target_map_bounds_cache_stat = None
            self.target_map_plot_bounds_cache = None
            pass

        render_underlay = self._current_world_map_render_underlay()
        if render_underlay is not None:
            payload, _source_image = render_underlay
            try:
                min_x = _render_cache_int(payload, 'min_x')
                max_x = _render_cache_int(payload, 'max_x')
                min_z = _render_cache_int(payload, 'min_z')
                max_z = _render_cache_int(payload, 'max_z')
            except (KeyError, TypeError, ValueError):
                return None
            return (float(min_x), float(max_x), float(-max_z), float(-min_z))
        return None

    def _minimum_zoom(self) -> float:
        bounds = self._target_map_plot_bounds()
        if bounds is None:
            return DEFAULT_ZOOM
        return self._target_zoom_for_plot_bounds(
            *bounds,
            margin_ratio=0.0,
            margin_pixels=TARGET_MAP_VIEW_MARGIN_PIXELS,
        )

    def _world_to_base_canvas(self, point: tuple[float, float]) -> tuple[float, float]:
        min_x, _, min_y, _, scale = self._plot_transform()
        return (
            self.padding + ((point[0] - min_x) * scale),
            self.height - self.padding - ((point[1] - min_y) * scale),
        )

    def _apply_viewport(self, point: tuple[float, float]) -> tuple[float, float]:
        center_x = self.width / 2
        center_y = self.height / 2
        return (
            center_x + ((point[0] - center_x) * self.zoom) + self.pan_x,
            center_y + ((point[1] - center_y) * self.zoom) + self.pan_y,
        )

    def world_to_canvas(self, point: tuple[float, float]) -> tuple[float, float]:
        return self._apply_viewport(self._world_to_base_canvas(point))

    def canvas_to_world(self, point: tuple[float, float]) -> tuple[int, int]:
        min_x, _, min_y, _, scale = self._plot_transform()
        center_x = self.width / 2
        center_y = self.height / 2
        base_x = center_x + ((point[0] - center_x - self.pan_x) / self.zoom)
        base_y = center_y + ((point[1] - center_y - self.pan_y) / self.zoom)
        world_x = min_x + ((base_x - self.padding) / scale)
        plot_y = min_y + ((self.height - self.padding - base_y) / scale)
        return (round(world_x), round(-plot_y))

    def _label_offset(self) -> tuple[int, int]:
        growth = _label_font_size(self.zoom) - BASE_LABEL_FONT_SIZE
        return (LABEL_OFFSET_X + growth, LABEL_OFFSET_Y + growth)

    def _draw_cursor_overlay(self) -> None:
        if self.cursor_readout_coordinates is None:
            self.cursor_overlay_ids = {}
            return

        horizontal_id = self.canvas.create_line(
            0,
            0,
            self.width,
            0,
            fill=CURSOR_GUIDE_COLOR,
            width=CURSOR_GUIDE_WIDTH,
            dash=CURSOR_GUIDE_DASH,
        )
        vertical_id = self.canvas.create_line(
            0,
            0,
            0,
            self.height,
            fill=CURSOR_GUIDE_COLOR,
            width=CURSOR_GUIDE_WIDTH,
            dash=CURSOR_GUIDE_DASH,
        )
        crosshair_horizontal_id = self.canvas.create_line(
            0,
            0,
            0,
            0,
            fill=CURSOR_GUIDE_COLOR,
            width=2,
        )
        crosshair_vertical_id = self.canvas.create_line(
            0,
            0,
            0,
            0,
            fill=CURSOR_GUIDE_COLOR,
            width=2,
        )
        info_box_id = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill=CURSOR_INFO_BACKGROUND,
            outline=CURSOR_INFO_BORDER,
            width=1,
        )
        info_text_id = self.canvas.create_text(
            self.width - CURSOR_INFO_MARGIN,
            CURSOR_INFO_MARGIN,
            anchor='ne',
            text='',
            fill=CURSOR_GUIDE_COLOR,
            font=('Helvetica', CURSOR_INFO_FONT_SIZE, 'bold'),
        )
        self.canvas.tag_lower(info_box_id, info_text_id)
        self.cursor_overlay_ids = {
            'horizontal': horizontal_id,
            'vertical': vertical_id,
            'crosshair_horizontal': crosshair_horizontal_id,
            'crosshair_vertical': crosshair_vertical_id,
            'info_box': info_box_id,
            'info_text': info_text_id,
        }
        self._update_cursor_overlay()

    def _update_cursor_overlay(self) -> None:
        if not self.cursor_overlay_ids:
            return

        item_ids = tuple(self.cursor_overlay_ids.values())
        if self.cursor_readout_coordinates is None:
            for item_id in item_ids:
                self.canvas.itemconfigure(item_id, state='hidden')
            return

        if self.show_cursor_guides and self.hover_canvas_point is not None:
            guide_x, guide_y = self.hover_canvas_point
            self.canvas.itemconfigure(self.cursor_overlay_ids['horizontal'], state='normal')
            self.canvas.itemconfigure(self.cursor_overlay_ids['vertical'], state='normal')
            self.canvas.itemconfigure(self.cursor_overlay_ids['crosshair_horizontal'], state='normal')
            self.canvas.itemconfigure(self.cursor_overlay_ids['crosshair_vertical'], state='normal')
            self.canvas.coords(self.cursor_overlay_ids['horizontal'], 0, guide_y, self.width, guide_y)
            self.canvas.coords(self.cursor_overlay_ids['vertical'], guide_x, 0, guide_x, self.height)
            self.canvas.coords(
                self.cursor_overlay_ids['crosshair_horizontal'],
                guide_x - CURSOR_CROSSHAIR_RADIUS,
                guide_y,
                guide_x + CURSOR_CROSSHAIR_RADIUS,
                guide_y,
            )
            self.canvas.coords(
                self.cursor_overlay_ids['crosshair_vertical'],
                guide_x,
                guide_y - CURSOR_CROSSHAIR_RADIUS,
                guide_x,
                guide_y + CURSOR_CROSSHAIR_RADIUS,
            )
        else:
            for item_name in ('horizontal', 'vertical', 'crosshair_horizontal', 'crosshair_vertical'):
                self.canvas.itemconfigure(self.cursor_overlay_ids[item_name], state='hidden')

        self.canvas.itemconfigure(self.cursor_overlay_ids['info_box'], state='normal')
        self.canvas.itemconfigure(self.cursor_overlay_ids['info_text'], state='normal')
        world_x, world_y = self.cursor_readout_coordinates
        info_text_id = self.cursor_overlay_ids['info_text']
        self.canvas.coords(info_text_id, self.width - CURSOR_INFO_MARGIN, CURSOR_INFO_MARGIN)
        self.canvas.itemconfigure(info_text_id, text=f'x={world_x}  y={world_y}')
        text_bounds = self.canvas.bbox(info_text_id)
        if text_bounds is None:
            return

        left, top, right, bottom = text_bounds
        self.canvas.coords(
            self.cursor_overlay_ids['info_box'],
            left - CURSOR_INFO_PAD_X,
            top - CURSOR_INFO_PAD_Y,
            right + CURSOR_INFO_PAD_X,
            bottom + CURSOR_INFO_PAD_Y,
        )
        self.canvas.tag_lower(self.cursor_overlay_ids['info_box'], info_text_id)

    def _station_hit_test(self, canvas_x: int, canvas_y: int) -> MetroStop | None:
        best_stop: MetroStop | None = None
        best_distance_sq: float | None = None
        max_distance_sq = float(STATION_CLICK_TOLERANCE ** 2)

        for stop in METRO_STOPS:
            station_position = self.station_canvas_positions.get(stop.var)
            if station_position is None:
                continue
            stop_x, stop_y = station_position
            distance_sq = ((stop_x - canvas_x) ** 2) + ((stop_y - canvas_y) ** 2)
            if distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_stop = stop
                best_distance_sq = distance_sq

        return best_stop

    def _selected_path_node(self) -> PathNode | None:
        if self.selected_path_node_key is None:
            return None
        return _all_path_nodes_by_key().get(self.selected_path_node_key)

    def _path_node_hit_test(self, canvas_x: int, canvas_y: int) -> PathNode | None:
        best_node: PathNode | None = None
        best_distance_sq: float | None = None
        max_distance_sq = float(PATH_NODE_CLICK_TOLERANCE ** 2)

        for path_node in _all_path_nodes():
            node_position = self.path_node_canvas_positions.get(path_node.key)
            if node_position is None:
                continue
            node_x, node_y = node_position
            distance_sq = ((node_x - canvas_x) ** 2) + ((node_y - canvas_y) ** 2)
            if distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_node = path_node
                best_distance_sq = distance_sq

        return best_node

    def _path_endpoint_hit_test(self, canvas_x: int, canvas_y: int) -> PathEndpoint | None:
        best_endpoint: PathEndpoint | None = None
        best_distance_sq: float | None = None
        max_distance_sq = float(max(STATION_CLICK_TOLERANCE, PATH_NODE_CLICK_TOLERANCE) ** 2)

        for stop in METRO_STOPS:
            station_position = self.station_canvas_positions.get(stop.var)
            if station_position is None:
                continue
            stop_x, stop_y = station_position
            distance_sq = ((stop_x - canvas_x) ** 2) + ((stop_y - canvas_y) ** 2)
            if distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_endpoint = PathEndpoint(kind='stop', key=stop.var, x=stop.x, y=stop.y)
                best_distance_sq = distance_sq

        for path_node in _all_path_nodes():
            node_position = self.path_node_canvas_positions.get(path_node.key)
            if node_position is None:
                continue
            node_x, node_y = node_position
            distance_sq = ((node_x - canvas_x) ** 2) + ((node_y - canvas_y) ** 2)
            if distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_endpoint = PathEndpoint(kind='coord', key=path_node.key, x=path_node.x, y=path_node.y)
                best_distance_sq = distance_sq

        return best_endpoint

    def _extra_edge_hit_test(self, canvas_x: int, canvas_y: int) -> ExtraEdgeDefinition | None:
        best_edge: ExtraEdgeDefinition | None = None
        best_distance_sq: float | None = None
        max_distance_sq = float(LINE_CLICK_TOLERANCE ** 2)
        click_point = (float(canvas_x), float(canvas_y))

        for extra_edge in EXTRA_EDGES:
            canvas_points = tuple(self.world_to_canvas(point) for point in extra_edge.plot_points)
            distance_sq = _point_to_polyline_distance_sq(click_point, canvas_points)
            if distance_sq is None or distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_edge = extra_edge
                best_distance_sq = distance_sq

        return best_edge

    def _path_edit_points_for_edge(self, extra_edge: ExtraEdgeDefinition) -> list[tuple[int, int]]:
        if extra_edge.path_points:
            return list(extra_edge.path_points)
        return [extra_edge.from_endpoint.coordinates, extra_edge.to_endpoint.coordinates]

    def _path_edit_handle_hit_test(
        self,
        extra_edge: ExtraEdgeDefinition,
        canvas_x: int,
        canvas_y: int,
    ) -> int | None:
        points = self._path_edit_points_for_edge(extra_edge)
        if len(points) <= 2:
            return None

        click_point = (float(canvas_x), float(canvas_y))
        max_distance_sq = float(PATH_EDIT_HANDLE_TOLERANCE ** 2)
        best_index: int | None = None
        best_distance_sq: float | None = None
        for index, point in enumerate(points[1:-1], start=1):
            handle_x, handle_y = self.world_to_canvas((point[0], -point[1]))
            distance_sq = ((handle_x - click_point[0]) ** 2) + ((handle_y - click_point[1]) ** 2)
            if distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_index = index
                best_distance_sq = distance_sq
        return best_index

    def _path_edit_insert_index(
        self,
        extra_edge: ExtraEdgeDefinition,
        canvas_x: int,
        canvas_y: int,
    ) -> int | None:
        points = self._path_edit_points_for_edge(extra_edge)
        if len(points) < 2:
            return None

        click_point = (float(canvas_x), float(canvas_y))
        max_distance_sq = float(LINE_CLICK_TOLERANCE ** 2)
        best_index: int | None = None
        best_distance_sq: float | None = None
        canvas_points = [self.world_to_canvas((point[0], -point[1])) for point in points]
        for index, (start_point, end_point) in enumerate(zip(canvas_points, canvas_points[1:]), start=1):
            distance_sq = _point_to_segment_distance_sq(click_point, start_point, end_point)
            if distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_index = index
                best_distance_sq = distance_sq
        return best_index

    def _selected_metro_segment(self) -> MetroLineSegment | None:
        if self.selected_metro_segment_key is None:
            return None
        return _metro_segment_from_key(self.selected_metro_segment_key)

    def _selected_metro_segments(self) -> tuple[MetroLineSegment, ...]:
        return tuple(
            segment
            for segment_key in self.selected_metro_segment_keys
            for segment in (_metro_segment_from_key(segment_key),)
            if segment is not None
        )

    def _set_metro_segment_selection(
        self,
        segment_keys: Sequence[tuple[str, str, str]],
        *,
        primary_key: tuple[str, str, str] | None = None,
        anchor_key: tuple[str, str, str] | None = None,
    ) -> None:
        valid_keys: list[tuple[str, str, str]] = []
        seen_keys: set[tuple[str, str, str]] = set()
        for segment_key in segment_keys:
            if segment_key in seen_keys or _metro_segment_from_key(segment_key) is None:
                continue
            valid_keys.append(segment_key)
            seen_keys.add(segment_key)

        self.selected_metro_segment_keys = tuple(valid_keys)
        if primary_key is not None and primary_key in seen_keys:
            self.selected_metro_segment_key = primary_key
        else:
            self.selected_metro_segment_key = valid_keys[-1] if valid_keys else None
        if anchor_key is not None and anchor_key in seen_keys:
            self.metro_segment_selection_anchor_key = anchor_key
        elif self.selected_metro_segment_key is not None:
            self.metro_segment_selection_anchor_key = self.selected_metro_segment_key
        else:
            self.metro_segment_selection_anchor_key = None

    def _clear_metro_segment_selection(self) -> None:
        self._set_metro_segment_selection(())

    def _metro_segment_range_keys(
        self,
        anchor_key: tuple[str, str, str],
        target_key: tuple[str, str, str],
    ) -> tuple[tuple[str, str, str], ...]:
        anchor_line, _anchor_start, _anchor_end = anchor_key
        target_line, _target_start, _target_end = target_key
        if anchor_line != target_line:
            return (target_key,)
        line_segment_keys = tuple(
            _metro_segment_key(segment)
            for segment in _all_metro_segments()
            if segment.line_name == target_line
        )
        if anchor_key not in line_segment_keys or target_key not in line_segment_keys:
            return (target_key,)
        anchor_index = line_segment_keys.index(anchor_key)
        target_index = line_segment_keys.index(target_key)
        start_index, end_index = sorted((anchor_index, target_index))
        return line_segment_keys[start_index:end_index + 1]

    def _event_has_modifier(self, event: object, masks: Sequence[int]) -> bool:
        event_state = int(getattr(event, 'state', 0))
        return any(event_state & mask for mask in masks)

    def _event_is_toggle_selection(self, event: object) -> bool:
        return self._event_has_modifier(event, (0x0004, 0x0008, 0x0010, 0x0080))

    def _event_is_range_selection(self, event: object) -> bool:
        return self._event_has_modifier(event, (0x0001,))

    def _select_metro_segment_from_event(self, segment: MetroLineSegment, event: object) -> None:
        segment_key = _metro_segment_key(segment)
        current_keys = list(self.selected_metro_segment_keys)

        if self._event_is_range_selection(event) and self.metro_segment_selection_anchor_key is not None:
            self._set_metro_segment_selection(
                self._metro_segment_range_keys(self.metro_segment_selection_anchor_key, segment_key),
                primary_key=segment_key,
                anchor_key=self.metro_segment_selection_anchor_key,
            )
            return

        if self._event_is_toggle_selection(event):
            if segment_key in current_keys:
                current_keys.remove(segment_key)
                self._set_metro_segment_selection(
                    current_keys,
                    primary_key=current_keys[-1] if current_keys else None,
                    anchor_key=self.metro_segment_selection_anchor_key,
                )
            else:
                current_keys.append(segment_key)
                self._set_metro_segment_selection(
                    current_keys,
                    primary_key=segment_key,
                    anchor_key=segment_key,
                )
            return

        self._set_metro_segment_selection((segment_key,), primary_key=segment_key, anchor_key=segment_key)

    def _metro_segment_hit_test(self, canvas_x: int, canvas_y: int) -> MetroLineSegment | None:
        best_segment: MetroLineSegment | None = None
        best_distance_sq: float | None = None
        max_distance_sq = float(LINE_CLICK_TOLERANCE ** 2)
        click_point = (float(canvas_x), float(canvas_y))
        visible_line_names = self._visible_line_names()

        for segment in _all_metro_segments():
            if segment.line_name not in visible_line_names:
                continue
            canvas_points = tuple(self.world_to_canvas(point) for point in segment.plot_points)
            distance_sq = _point_to_polyline_distance_sq(click_point, canvas_points)
            if distance_sq is None or distance_sq > max_distance_sq:
                continue
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_segment = segment
                best_distance_sq = distance_sq

        return best_segment

    def _draw_selected_metro_segment_highlight(self) -> None:
        segments = self._selected_metro_segments()
        if not segments:
            return

        for segment in segments:
            canvas_points: list[float] = []
            for point in segment.plot_points:
                canvas_x, canvas_y = self.world_to_canvas(point)
                canvas_points.extend((canvas_x, canvas_y))
            if len(canvas_points) < 4:
                continue

            self.canvas.create_line(
                *canvas_points,
                fill=ROUTE_HIGHLIGHT_OUTLINE,
                width=SELECTED_SEGMENT_OUTLINE_WIDTH,
                capstyle='round',
                joinstyle='round',
            )
            self.canvas.create_line(
                *canvas_points,
                fill=LINE_COLORS[segment.line_name],
                width=SELECTED_SEGMENT_WIDTH,
                capstyle='round',
                joinstyle='round',
            )

    def _draw_selected_metro_segment_info(self) -> None:
        segment = self._selected_metro_segment()
        if segment is None:
            return

        margin = self.padding // 2
        frame = tk.Frame(
            self.canvas,
            bg=INFO_BOX_BACKGROUND,
            highlightbackground=INFO_BOX_BORDER,
            highlightthickness=1,
        )

        tk.Label(
            frame,
            text=f'Line {segment.line_name}',
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TITLE_FONT_SIZE, 'bold'),
            anchor='w',
            justify='left',
        ).pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(INFO_BOX_PAD_Y, max(2, INFO_BOX_SECTION_GAP // 2)))

        tk.Label(
            frame,
            text=(
                f'{_display_label(segment.start_stop.lbl)} to {_display_label(segment.end_stop.lbl)}\n'
                f'Shape: {segment.shape_label}\n'
                f'Distance: {_format_distance_and_time(_polyline_distance(segment.plot_points))}'
            ),
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
        ).pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_SECTION_GAP))

        selected_segments = self._selected_metro_segments()
        if len(selected_segments) > 1:
            selected_distance = sum(_polyline_distance(active_segment.plot_points) for active_segment in selected_segments)
            tk.Label(
                frame,
                text=(
                    f'Selected legs: {len(selected_segments)}\n'
                    f'Selected total: {_format_distance_and_time(selected_distance)}'
                ),
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', INFO_TEXT_FONT_SIZE),
                anchor='w',
                justify='left',
            ).pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_SECTION_GAP))

        actions_row = tk.Frame(frame, bg=INFO_BOX_BACKGROUND)
        actions_row.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_PAD_Y))
        if segment.shape_label == 'direct':
            if segment.can_turn:
                self._make_info_button(
                    actions_row,
                    text='Add Turn',
                    command=lambda active_segment=segment: self._add_turn_to_metro_segment(active_segment),
                ).pack(side='left')
        else:
            self._make_info_button(
                actions_row,
                text='Direct',
                command=lambda active_segment=segment: self._make_metro_segment_direct(active_segment),
            ).pack(side='left')
            if segment.can_turn:
                self._make_info_button(
                    actions_row,
                    text='Flip Turn',
                    command=lambda active_segment=segment: self._flip_metro_segment_turn(active_segment),
                ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))

        frame.update_idletasks()
        box_width = frame.winfo_reqwidth()
        box_height = frame.winfo_reqheight()
        canvas_midpoint = _polyline_midpoint(tuple(self.world_to_canvas(point) for point in segment.plot_points))
        segment_x, segment_y = canvas_midpoint
        x0 = segment_x + INFO_BOX_OFFSET_X
        if x0 + box_width > self.width - margin:
            x0 = segment_x - INFO_BOX_OFFSET_X - box_width
        x0 = max(margin, min(x0, self.width - margin - box_width))

        y0 = segment_y - INFO_BOX_OFFSET_Y - box_height
        if y0 < margin:
            y0 = segment_y + INFO_BOX_OFFSET_Y
        y0 = max(margin, min(y0, self.height - margin - box_height))

        self.canvas.create_window(x0, y0, anchor='nw', window=frame)
        self.info_popup_frame = frame
        self._attach_info_popup_close_button(frame)

    def _draw_selected_path_node_info(self) -> None:
        path_node = self._selected_path_node()
        if path_node is None:
            return

        extra_edges = _extra_edges_for_endpoint_key(path_node.key)
        margin = self.padding // 2
        frame = tk.Frame(
            self.canvas,
            bg=INFO_BOX_BACKGROUND,
            highlightbackground=INFO_BOX_BORDER,
            highlightthickness=1,
        )

        tk.Label(
            frame,
            text=path_node.display_label,
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TITLE_FONT_SIZE, 'bold'),
            anchor='w',
            justify='left',
        ).pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(INFO_BOX_PAD_Y, max(2, INFO_BOX_SECTION_GAP // 2)))

        tk.Label(
            frame,
            text=(
                f'Coords: ({path_node.x}, {path_node.y})\n'
                f'Node Type: {_path_node_type_label(path_node)}\n'
                f'Path Edges: {len(extra_edges)}'
            ),
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
        ).pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_SECTION_GAP))

        actions_row = tk.Frame(frame, bg=INFO_BOX_BACKGROUND)
        actions_row.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_SECTION_GAP))
        self._make_info_button(
            actions_row,
            text='Add Walk Path',
            command=lambda: self._add_path_for_selected_node('walk'),
        ).pack(side='left')
        self._make_info_button(
            actions_row,
            text='Edit Node',
            command=self._edit_selected_path_node_coordinates,
        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
        self._make_info_button(
            actions_row,
            text='Add Metro Path',
            command=lambda: self._add_path_for_selected_node('connector'),
        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
        if path_node.is_explicit:
            self._make_info_button(
                actions_row,
                text='Remove Node',
                command=self._remove_selected_path_node,
            ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))

        if extra_edges:
            paths_label = tk.Label(
                frame,
                text='Path Edges',
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', INFO_TEXT_FONT_SIZE, 'bold'),
                anchor='w',
                justify='left',
            )
            paths_label.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, max(3, INFO_BOX_SECTION_GAP // 2)))
            paths_frame = tk.Frame(frame, bg=INFO_BOX_BACKGROUND)
            paths_frame.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_PAD_Y))
            for extra_edge in extra_edges:
                edge_row = tk.Frame(paths_frame, bg=INFO_BOX_BACKGROUND)
                edge_row.pack(anchor='w', pady=(0, 4))
                tk.Label(
                    edge_row,
                    text=_extra_edge_summary_for_endpoint(extra_edge, path_node.key),
                    bg=INFO_BOX_BACKGROUND,
                    fg=TEXT_COLOR,
                    font=('Helvetica', INFO_TEXT_FONT_SIZE),
                    anchor='w',
                    justify='left',
                    wraplength=280,
                ).pack(anchor='w')
                edge_actions_row = tk.Frame(edge_row, bg=INFO_BOX_BACKGROUND)
                edge_actions_row.pack(anchor='w', pady=(4, 0))
                self._make_info_button(
                    edge_actions_row,
                    text='Edit Points',
                    command=lambda active_edge=extra_edge: self._edit_path_edge_points(active_edge),
                ).pack(side='left')
                if extra_edge.kind == 'walk':
                    self._make_info_button(
                        edge_actions_row,
                        text='Road Name',
                        command=lambda active_edge=extra_edge: self._edit_path_edge_label(active_edge),
                    ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
                if extra_edge.shape_label == 'direct':
                    if extra_edge.can_turn:
                        self._make_info_button(
                            edge_actions_row,
                            text='Add Turn',
                            command=lambda active_edge=extra_edge: self._add_turn_to_path_edge(active_edge),
                        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
                else:
                    self._make_info_button(
                        edge_actions_row,
                        text='Direct',
                        command=lambda active_edge=extra_edge: self._make_path_edge_direct(active_edge),
                    ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
                    if extra_edge.can_turn:
                        self._make_info_button(
                            edge_actions_row,
                            text='Flip Turn',
                            command=lambda active_edge=extra_edge: self._flip_path_edge_turn(active_edge),
                        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
                self._make_info_button(
                    edge_actions_row,
                    text='Remove',
                    command=lambda active_edge=extra_edge: self._remove_path_edge(active_edge),
                ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))

        frame.update_idletasks()
        box_width = frame.winfo_reqwidth()
        box_height = frame.winfo_reqheight()

        x0 = margin
        y0 = max(margin, self.height - margin - box_height)

        self.canvas.create_window(x0, y0, anchor='nw', window=frame)
        self.info_popup_frame = frame
        self._attach_info_popup_close_button(frame)

    def _selected_station_signage_line(self, stop: MetroStop) -> str | None:
        line_names = STOP_LINE_NAMES[stop.var]
        if not line_names:
            return None
        selected_line = self.station_signage_line_by_stop.get(stop.var)
        if selected_line in line_names:
            return selected_line
        return line_names[0]

    def _select_station_signage_line(self, stop_var: str, line_name: str) -> None:
        self.station_signage_line_by_stop[stop_var] = line_name
        self.redraw()

    def _toggle_station_signage_sides(self, stop_var: str, line_name: str) -> None:
        key = (stop_var, line_name)
        if key in self.station_signage_flipped_keys:
            self.station_signage_flipped_keys.remove(key)
        else:
            self.station_signage_flipped_keys.add(key)
        self.redraw()

    def _toggle_station_signage_elevator(self, stop_var: str) -> None:
        if stop_var in self.station_signage_elevator_right_stop_vars:
            self.station_signage_elevator_right_stop_vars.remove(stop_var)
        else:
            self.station_signage_elevator_right_stop_vars.add(stop_var)
        self.redraw()

    def _make_signage_tab_button(
        self,
        parent: tk.Misc,
        *,
        stop_var: str,
        line_name: str,
        selected: bool,
    ) -> tk.Label:
        button = tk.Label(
            parent,
            text=line_name,
            bg=LINE_COLORS.get(line_name, INFO_BUTTON_BACKGROUND) if selected else INFO_BUTTON_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_BUTTON_FONT_SIZE, 'bold'),
            padx=8,
            pady=3,
            cursor='hand2',
            bd=1,
            relief='solid',
            highlightthickness=0,
        )
        self._bind_info_clickable(
            button,
            command=lambda: self._select_station_signage_line(stop_var, line_name),
            normal_background=cast(str, button.cget('bg')),
            active_background=INFO_BUTTON_ACTIVE_BACKGROUND,
        )
        return button

    def _draw_signage_station_list(
        self,
        parent: tk.Misc,
        *,
        title: str,
        stop_vars: tuple[str, ...],
        line_name: str,
        width: int,
    ) -> None:
        tk.Label(
            parent,
            text=title,
            bg=INFO_BOX_BACKGROUND,
            fg=INFO_CHECKBOX_TEXT_COLOR,
            font=('Menlo', INFO_TEXT_FONT_SIZE, 'bold'),
            anchor='center',
            justify='center',
            width=width,
        ).pack(anchor='n')
        if not stop_vars:
            tk.Label(
                parent,
                text='End of line',
                bg=INFO_BOX_BACKGROUND,
                fg=INFO_CHECKBOX_TEXT_COLOR,
                font=('Helvetica', max(10, INFO_TEXT_FONT_SIZE - 1)),
                anchor='w',
                justify='left',
                width=width,
            ).pack(anchor='w', pady=(5, 0))
            return

        for index, listed_stop_var in enumerate(stop_vars, start=1):
            tk.Label(
                parent,
                text=f'{index} {_station_signage_label(listed_stop_var, line_name)}',
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', max(10, INFO_TEXT_FONT_SIZE - 1)),
                anchor='w',
                justify='left',
                width=width,
            ).pack(anchor='w')

    def _draw_station_signage_panel(self, parent: tk.Misc, stop: MetroStop) -> None:
        selected_line = self._selected_station_signage_line(stop)
        if selected_line is None:
            return

        line_names = STOP_LINE_NAMES[stop.var]
        flipped = (stop.var, selected_line) in self.station_signage_flipped_keys
        left_stop_vars, right_stop_vars = _station_signage_direction_stop_vars(
            stop.var,
            selected_line,
            flipped=flipped,
        )
        has_two_direction_lists = bool(left_stop_vars and right_stop_vars)
        elevator_points_right = stop.var in self.station_signage_elevator_right_stop_vars
        display_name = _display_label(stop.lbl)
        uppercase_name = display_name.upper()

        panel = tk.Frame(
            parent,
            bg=INFO_BOX_BACKGROUND,
            highlightbackground=INFO_BOX_BORDER,
            highlightthickness=1,
        )
        panel.pack(anchor='n', fill='x')

        header_row = tk.Frame(panel, bg=INFO_BOX_BACKGROUND)
        header_row.pack(anchor='w', fill='x', padx=8, pady=(7, 4))
        tk.Label(
            header_row,
            text='Signs',
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TEXT_FONT_SIZE, 'bold'),
            anchor='w',
        ).pack(side='left')
        if len(line_names) > 1:
            tabs_row = tk.Frame(header_row, bg=INFO_BOX_BACKGROUND)
            tabs_row.pack(side='left', padx=(10, 0))
            for line_name in line_names:
                self._make_signage_tab_button(
                    tabs_row,
                    stop_var=stop.var,
                    line_name=line_name,
                    selected=line_name == selected_line,
                ).pack(side='left', padx=(0, 4))

        table_row = tk.Frame(panel, bg=INFO_BOX_BACKGROUND)
        table_row.pack(anchor='w', padx=8, pady=(0, 7))

        left_column = tk.Frame(table_row, bg=INFO_BOX_BACKGROUND)
        left_column.pack(side='left', anchor='n')
        center_column = tk.Frame(table_row, bg=INFO_BOX_BACKGROUND)
        center_column.pack(side='left', anchor='n', padx=12)
        right_column = tk.Frame(table_row, bg=INFO_BOX_BACKGROUND)

        if has_two_direction_lists:
            self._draw_signage_station_list(
                left_column,
                title='<<<<<',
                stop_vars=left_stop_vars,
                line_name=selected_line,
                width=20,
            )
        else:
            self._draw_signage_station_list(
                left_column,
                title=f'Line {selected_line}',
                stop_vars=left_stop_vars,
                line_name=selected_line,
                width=20,
            )

        arriving_label = tk.Label(
            center_column,
            text=f'Arriving:\n{display_name}',
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', max(10, INFO_TEXT_FONT_SIZE - 1)),
            anchor='center',
            justify='center',
            width=18,
        )
        arriving_label.pack(anchor='center', pady=(20 if has_two_direction_lists else 8, 16))
        tk.Label(
            center_column,
            text=f'{uppercase_name}\nSTATION',
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TEXT_FONT_SIZE, 'bold'),
            anchor='center',
            justify='center',
            width=18,
        ).pack(anchor='center', pady=(0, 16))
        elevator_arrow = '>> ELEVATOR >>' if elevator_points_right else '<< ELEVATOR <<'
        tk.Label(
            center_column,
            text=f'{elevator_arrow}\nTO {uppercase_name}',
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', max(10, INFO_TEXT_FONT_SIZE - 1), 'bold'),
            anchor='center',
            justify='center',
            width=18,
        ).pack(anchor='center')

        if has_two_direction_lists:
            right_column.pack(side='left', anchor='n')
            self._draw_signage_station_list(
                right_column,
                title='>>>>>',
                stop_vars=right_stop_vars,
                line_name=selected_line,
                width=20,
            )

        control_row = tk.Frame(panel, bg=INFO_BOX_BACKGROUND)
        control_row.pack(anchor='w', padx=8, pady=(0, 8))
        if has_two_direction_lists:
            self._make_info_button(
                control_row,
                text='Swap Sides',
                command=lambda: self._toggle_station_signage_sides(stop.var, selected_line),
            ).pack(side='left')
        elevator_button_text = 'Elevator ->' if not elevator_points_right else 'Elevator <-'
        self._make_info_button(
            control_row,
            text=elevator_button_text,
            command=lambda: self._toggle_station_signage_elevator(stop.var),
        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP if has_two_direction_lists else 0, 0))

    def _draw_selected_stop_info(self) -> None:
        if self.selected_stop_var is None or self.selected_stop_var not in self.station_canvas_positions:
            return

        stop = STOPS_BY_VAR[self.selected_stop_var]
        lines = ', '.join(STOP_LINE_NAMES[stop.var]) or 'none'
        reminders = _alignment_reminders_for_stop(stop.var)
        alignment_summary = 'none' if not reminders else f'{len(reminders)} active'
        chime_outlet_directions = _station_chime_outlet_directions(stop.var)
        completed_chime_count = _station_completed_chime_count(stop)
        max_chime_count = _station_max_chime_count(stop)
        chime_summary = f'{completed_chime_count}/{max_chime_count}'
        if max_chime_count == 0:
            chime_summary = 'none needed yet'
        detail_lines = [
            f'Coords: ({stop.x}, {stop.y})',
            f'Lines: {lines}',
            f'Progress: {stop.checkpoint_count}/{stop.checkpoint_total}',
        ]
        if stop.station_entry_coordinates is not None:
            entry_x, entry_y = stop.station_entry_coordinates
            detail_lines.append(f'Station entry: ({entry_x}, {entry_y})')
        if stop.city_limit_node_keys:
            detail_lines.append(f'City limits: {len(stop.city_limit_node_keys)} nodes')
        if stop.is_connected:
            detail_lines.append(f'Chimes: {chime_summary}')
        detail_lines.append(f'Alignments: {alignment_summary}')
        margin = self.padding // 2
        self.info_popup_variables = []
        frame = tk.Frame(
            self.canvas,
            bg=INFO_BOX_BACKGROUND,
            highlightbackground=INFO_BOX_BORDER,
            highlightthickness=1,
        )

        title_label = tk.Label(
            frame,
            text=_display_label(stop.lbl),
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TITLE_FONT_SIZE, 'bold'),
            anchor='w',
            justify='left',
        )
        title_label.pack(
            anchor='w',
            padx=INFO_BOX_PAD_X,
            pady=(INFO_BOX_PAD_Y, max(2, INFO_BOX_SECTION_GAP // 2)),
        )

        body_row = tk.Frame(frame, bg=INFO_BOX_BACKGROUND)
        body_row.pack(anchor='w', fill='x')
        left_column = tk.Frame(body_row, bg=INFO_BOX_BACKGROUND)
        left_column.pack(side='left', anchor='n', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_SECTION_GAP))
        signage_column = tk.Frame(body_row, bg=INFO_BOX_BACKGROUND)
        signage_column.pack(side='left', anchor='n', padx=(18, INFO_BOX_PAD_X), pady=(0, INFO_BOX_SECTION_GAP))

        details_label = tk.Label(
            left_column,
            text='\n'.join(detail_lines),
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
        )
        details_label.pack(anchor='w', pady=(0, INFO_BOX_SECTION_GAP))

        checkpoint_frame = tk.Frame(left_column, bg=INFO_BOX_BACKGROUND)
        checkpoint_frame.pack(anchor='w', pady=(0, INFO_BOX_SECTION_GAP))
        self._make_info_checkbox(
            checkpoint_frame,
            text='Has Name',
            checked=stop.has_name,
            enabled=False,
        ).pack(anchor='w')
        self._make_info_checkbox(
            checkpoint_frame,
            text='Façade',
            checked=stop.has_connector,
            on_toggle=lambda value: self._update_selected_checkpoint('has_connector', value),
        ).pack(anchor='w')
        self._make_info_checkbox(
            checkpoint_frame,
            text='Station',
            checked=stop.has_full_station,
            on_toggle=lambda value: self._update_selected_checkpoint('has_full_station', value),
        ).pack(anchor='w')
        self._make_info_checkbox(
            checkpoint_frame,
            text='Walking Paths',
            checked=stop.has_walking_paths,
            on_toggle=lambda value: self._update_selected_checkpoint('has_walking_paths', value),
        ).pack(anchor='w')
        self._make_info_checkbox(
            checkpoint_frame,
            text='Connected',
            checked=stop.is_connected,
            on_toggle=lambda value: self._update_selected_checkpoint('is_connected', value),
        ).pack(anchor='w')
        if stop.is_connected and SHOW_RAILWAY_FINISHING_UI:
            self._make_info_checkbox(
                checkpoint_frame,
                text='Finished Railway',
                checked=stop.has_finished_railway,
                on_toggle=lambda value: self._update_selected_checkpoint('has_finished_railway', value),
            ).pack(anchor='w')
        if _station_signs_available(stop):
            self._make_info_checkbox(
                checkpoint_frame,
                text='Signs',
                checked=stop.has_signs,
                on_toggle=lambda value: self._update_selected_checkpoint('has_signs', value),
            ).pack(anchor='w')

        if stop.is_connected and chime_outlet_directions:
            tk.Label(
                checkpoint_frame,
                text='Chimes',
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', INFO_TEXT_FONT_SIZE, 'bold'),
                anchor='w',
                justify='left',
            ).pack(anchor='w', pady=(max(2, INFO_BOX_SECTION_GAP // 2), 0))
            for direction in chime_outlet_directions:
                self._make_info_checkbox(
                    checkpoint_frame,
                    text=f'{CHIME_DIRECTION_LABELS[direction]} Chime',
                    checked=direction in stop.chime_directions,
                    on_toggle=(
                        lambda value, chime_direction=direction:
                        self._update_selected_chime_direction(chime_direction, value)
                    ),
                ).pack(anchor='w')

        self._draw_station_signage_panel(signage_column, stop)

        button_row = tk.Frame(frame, bg=INFO_BOX_BACKGROUND)
        button_row.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_PAD_Y))
        self._make_info_button(
            button_row,
            text='Change Coordinates',
            command=self._edit_selected_coordinates,
        ).pack(side='left')
        self._make_info_button(
            button_row,
            text='Change Name',
            command=self._edit_selected_label,
        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
        self._make_info_button(
            button_row,
            text='Station Entry',
            command=self._edit_selected_station_entry,
        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
        city_limit_button_text = (
            'Done City Limits'
            if self.city_limits_edit_stop_var == stop.var
            else ('Edit City Limits' if stop.city_limit_node_keys else 'Decide City Limits')
        )
        self._make_info_button(
            button_row,
            text=city_limit_button_text,
            command=self._toggle_selected_city_limits_edit,
        ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
        if stop.city_limit_node_keys:
            self._make_info_button(
                button_row,
                text='Clear City Limits',
                command=self._clear_selected_city_limits,
            ).pack(side='left', padx=(INFO_BOX_SECTION_GAP, 0))
        if STOP_LINE_NAMES[stop.var]:
            line_button_row = tk.Frame(frame, bg=INFO_BOX_BACKGROUND)
            line_button_row.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_SECTION_GAP))
            for line_name in STOP_LINE_NAMES[stop.var]:
                self._make_info_button(
                    line_button_row,
                    text=f'Remove from Line {line_name}',
                    command=lambda active_line=line_name: self._remove_selected_station_from_line(active_line),
                ).pack(side='left', padx=(0, INFO_BOX_SECTION_GAP))

        if reminders:
            reminders_label = tk.Label(
                frame,
                text='Alignment Reminders',
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', INFO_TEXT_FONT_SIZE, 'bold'),
                anchor='w',
                justify='left',
            )
            reminders_label.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, max(3, INFO_BOX_SECTION_GAP // 2)))
            reminders_frame = tk.Frame(frame, bg=INFO_BOX_BACKGROUND)
            reminders_frame.pack(anchor='w', padx=INFO_BOX_PAD_X, pady=(0, INFO_BOX_SECTION_GAP))
            for reminder in reminders:
                reminder_row = tk.Frame(reminders_frame, bg=INFO_BOX_BACKGROUND)
                reminder_row.pack(anchor='w', pady=(0, 4))
                tk.Label(
                    reminder_row,
                    text=reminder.debug_label,
                    bg=INFO_BOX_BACKGROUND,
                    fg=TEXT_COLOR,
                    font=('Helvetica', INFO_TEXT_FONT_SIZE),
                    anchor='w',
                    justify='left',
                    wraplength=280,
                ).pack(side='left')

        frame.update_idletasks()
        box_width = frame.winfo_reqwidth()
        box_height = frame.winfo_reqheight()

        x0 = margin
        y0 = max(margin, self.height - margin - box_height)

        self.canvas.create_window(x0, y0, anchor='nw', window=frame)
        self.info_popup_frame = frame
        self._attach_info_popup_close_button(frame)

    def _make_info_button(
        self,
        parent: tk.Misc,
        *,
        text: str,
        command: Callable[[], None],
    ) -> tk.Label:
        button = tk.Label(
            parent,
            text=text,
            bg=INFO_BUTTON_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', INFO_BUTTON_FONT_SIZE, 'bold'),
            padx=INFO_BUTTON_PAD_X,
            pady=INFO_BUTTON_PAD_Y,
            cursor='hand2',
            bd=1,
            relief='solid',
            highlightthickness=0,
        )
        self._bind_info_clickable(
            button,
            command=command,
            normal_background=INFO_BUTTON_BACKGROUND,
            active_background=INFO_BUTTON_ACTIVE_BACKGROUND,
        )
        return button

    def _dismiss_info_selection(self) -> None:
        self.selected_stop_var = None
        self.selected_path_node_key = None
        self._clear_metro_segment_selection()
        self.redraw()

    def _attach_info_popup_close_button(self, frame: tk.Misc) -> None:
        close_button = tk.Label(
            frame,
            text='x',
            bg=INFO_BOX_BACKGROUND,
            fg=INFO_CHECKBOX_TEXT_COLOR,
            font=('Helvetica', INFO_BUTTON_FONT_SIZE, 'bold'),
            padx=4,
            pady=2,
            cursor='hand2',
        )
        self._bind_info_clickable(
            close_button,
            command=self._dismiss_info_selection,
            normal_foreground=INFO_CHECKBOX_TEXT_COLOR,
            active_foreground=TEXT_COLOR,
        )
        close_button.place(relx=1.0, x=-4, y=4, anchor='ne')

    def _bind_info_clickable(
        self,
        widget: tk.Label,
        *,
        command: Callable[[], None],
        normal_background: str | None = None,
        active_background: str | None = None,
        normal_foreground: str | None = None,
        active_foreground: str | None = None,
    ) -> None:
        def _restore_normal_style(_event: object | None = None) -> None:
            if normal_background is not None:
                widget.configure(bg=normal_background)
            if normal_foreground is not None:
                widget.configure(fg=normal_foreground)

        def _apply_active_style(_event: object | None = None) -> None:
            if active_background is not None:
                widget.configure(bg=active_background)
            if active_foreground is not None:
                widget.configure(fg=active_foreground)

        def _on_press(_event: object) -> str:
            _apply_active_style()
            command()
            return 'break'

        def _swallow_mouse_event(_event: object) -> str:
            return 'break'

        widget.bind('<Enter>', _apply_active_style)
        widget.bind('<Leave>', _restore_normal_style)
        widget.bind('<ButtonPress-1>', _on_press)
        widget.bind('<ButtonRelease-1>', _swallow_mouse_event)
        widget.bind('<B1-Motion>', _swallow_mouse_event)
        _restore_normal_style()

    def _make_info_checkbox(
        self,
        parent: tk.Misc,
        *,
        text: str,
        checked: bool,
        enabled: bool = True,
        on_toggle: Callable[[bool], None] | None = None,
    ) -> tk.Checkbutton:
        variable = tk.BooleanVar(master=self.root, value=checked)
        self.info_popup_variables.append(variable)
        command_value: str | Callable[[], None] = ''
        if on_toggle is not None and enabled:
            command_value = lambda: on_toggle(variable.get())

        checkbox = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            activebackground=INFO_BOX_BACKGROUND,
            activeforeground=TEXT_COLOR,
            selectcolor=INFO_BUTTON_BACKGROUND,
            disabledforeground=TEXT_COLOR if checked else INFO_CHECKBOX_TEXT_COLOR,
            font=('Helvetica', INFO_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            highlightthickness=0,
            bd=0,
            padx=0,
            pady=0,
            cursor='hand2' if enabled else 'arrow',
            state='normal' if enabled else 'disabled',
            command=command_value,
        )
        return checkbox

    def _update_selected_checkpoint(self, field_name: CheckpointField, value: bool) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox

        try:
            if field_name == 'has_connector':
                _update_stop_record(self.selected_stop_var, has_connector=value)
            elif field_name == 'has_full_station':
                _update_stop_record(self.selected_stop_var, has_full_station=value)
            elif field_name == 'has_walking_paths':
                _update_stop_record(self.selected_stop_var, has_walking_paths=value)
            elif field_name == 'is_connected':
                _update_stop_record(self.selected_stop_var, is_connected=value)
            elif field_name == 'has_finished_railway':
                _update_stop_record(self.selected_stop_var, has_finished_railway=value)
            else:
                _update_stop_record(self.selected_stop_var, has_signs=value)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Checkpoint', str(exc), parent=self.root)
            return

        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.stats_dirty = True
        self.redraw()

    def _update_selected_chime_direction(self, direction: ChimeDirection, value: bool) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox

        stop = STOPS_BY_VAR[self.selected_stop_var]
        chime_directions: set[ChimeDirection] = set(stop.chime_directions)
        if value:
            chime_directions.add(direction)
        else:
            chime_directions.discard(direction)

        ordered_directions: tuple[ChimeDirection, ...] = tuple(
            chime_direction
            for chime_direction in CHIME_DIRECTIONS
            if chime_direction in chime_directions
        )
        try:
            _update_stop_record(stop.var, chime_directions=ordered_directions)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Chime Checkpoint', str(exc), parent=self.root)
            return

        self.priority_dirty = True
        self.stats_dirty = True
        self.redraw()

    def _clear_info_popup(self) -> None:
        self.info_popup_variables = []
        if self.info_popup_frame is None:
            return
        self.info_popup_frame.destroy()
        self.info_popup_frame = None

    def _edit_selected_label(self) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox, simpledialog

        stop = STOPS_BY_VAR[self.selected_stop_var]
        new_label = simpledialog.askstring(
            'Change Name',
            'Enter the new station label:',
            initialvalue=stop.lbl,
            parent=self.root,
        )
        if new_label is None:
            return

        new_label = new_label.strip()
        if not new_label:
            messagebox.showerror('Invalid Label', 'Station label cannot be blank.', parent=self.root)
            return

        try:
            _update_stop_record(stop.var, lbl=new_label)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Label', str(exc), parent=self.root)
            return

        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.stats_dirty = True
        self.redraw()

    def _edit_selected_coordinates(self) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox, simpledialog

        stop = STOPS_BY_VAR[self.selected_stop_var]
        new_coordinates = simpledialog.askstring(
            'Change Coordinates',
            'Enter new Minecraft coordinates as x, y:',
            initialvalue=f'{stop.x}, {stop.y}',
            parent=self.root,
        )
        if new_coordinates is None:
            return

        parts = [part.strip() for part in new_coordinates.split(',')]
        if len(parts) != 2:
            messagebox.showerror(
                'Invalid Coordinates',
                'Enter coordinates in the format: x, y',
                parent=self.root,
            )
            return

        try:
            new_x = int(parts[0])
            new_y = int(parts[1])
            _update_stop_record(stop.var, x=new_x, y=new_y)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Coordinates', str(exc), parent=self.root)
            return

        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.redraw()

    def _edit_selected_station_entry(self) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox, simpledialog

        stop = STOPS_BY_VAR[self.selected_stop_var]
        initial_coordinates = stop.station_entry_coordinates or stop.coordinates
        new_coordinates = simpledialog.askstring(
            'Station Entry',
            'Enter station-building entry coordinates as x, y.\nLeave blank to clear the entryway:',
            initialvalue=f'{initial_coordinates[0]}, {initial_coordinates[1]}',
            parent=self.root,
        )
        if new_coordinates is None:
            return

        normalized_coordinates = new_coordinates.strip()
        try:
            if not normalized_coordinates:
                _update_stop_record(stop.var, station_entry=False)
            else:
                parsed_coordinates = _parse_coordinate_text(normalized_coordinates)
                if parsed_coordinates is None:
                    raise ValueError('Enter coordinates in the format: x, y')
                _update_stop_record(stop.var, station_entry=parsed_coordinates)
        except ValueError as exc:
            messagebox.showerror('Could Not Save Station Entry', str(exc), parent=self.root)
            return

        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.redraw()

    def _remove_selected_station_from_line(self, line_name: str) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox

        old_stop_var = self.selected_stop_var
        try:
            new_stop_var = remove_station_from_line(old_stop_var, line_name)
        except ValueError as exc:
            messagebox.showerror('Could Not Remove Station From Line', str(exc), parent=self.root)
            return

        self.selected_stop_var = new_stop_var
        self.selected_path_node_key = None
        self._clear_metro_segment_selection()
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.stats_dirty = True
        self.railway_finish_dirty = True
        self.path_edge_list_dirty = True
        self.redraw()

    def _toggle_selected_city_limits_edit(self) -> None:
        if self.selected_stop_var is None:
            return
        if self.city_limits_edit_stop_var == self.selected_stop_var:
            self.city_limits_edit_stop_var = None
            self.path_click_status_var.set('City limit editing is off.')
        else:
            self.city_limits_edit_stop_var = self.selected_stop_var
            self.show_city_limits_var.set(True)
            stop_label = _display_label(STOPS_BY_VAR[self.selected_stop_var].lbl)
            self.path_click_status_var.set(
                f'Editing city limits for {stop_label}. Click path nodes to add or remove boundary points.'
            )
        self.redraw()

    def _clear_selected_city_limits(self) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox

        try:
            set_stop_city_limit_node_keys(self.selected_stop_var, ())
        except ValueError as exc:
            messagebox.showerror('Could Not Clear City Limits', str(exc), parent=self.root)
            return

        if self.city_limits_edit_stop_var == self.selected_stop_var:
            self.city_limits_edit_stop_var = None
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.redraw()

    def _toggle_city_limit_node(self, path_node: PathNode) -> None:
        if self.city_limits_edit_stop_var is None:
            return

        from tkinter import messagebox

        stop = STOPS_BY_VAR.get(self.city_limits_edit_stop_var)
        if stop is None:
            self.city_limits_edit_stop_var = None
            return

        node_keys = list(stop.city_limit_node_keys)
        if path_node.key in node_keys:
            node_keys.remove(path_node.key)
            action_text = 'Removed'
        else:
            node_keys.append(path_node.key)
            action_text = 'Added'

        try:
            set_stop_city_limit_node_keys(stop.var, node_keys)
        except ValueError as exc:
            messagebox.showerror('Could Not Save City Limits', str(exc), parent=self.root)
            return

        refreshed_stop = STOPS_BY_VAR[stop.var]
        self.selected_stop_var = stop.var
        self.selected_path_node_key = None
        self._clear_metro_segment_selection()
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.path_click_status_var.set(
            f'{action_text} {path_node.display_label} for {_display_label(refreshed_stop.lbl)} city limits '
            f'({len(refreshed_stop.city_limit_node_keys)} nodes).'
        )
        self.redraw()

    def _refresh_after_path_edit(
        self,
        *,
        refresh_path_status: bool = True,
        refresh_routes: bool = True,
    ) -> None:
        if refresh_routes:
            self.route_controls_dirty = True
            self.route_dirty = True
            self.priority_dirty = True
        self.path_edge_list_dirty = True
        if refresh_path_status and self.active_path_edge_id is not None:
            self._set_active_path_edge(self._active_path_edge())
        self.redraw()

    def _refresh_path_edge_list(self) -> None:
        if not hasattr(self, 'path_edge_list_frame'):
            return

        for child in self.path_edge_list_frame.winfo_children():
            child.destroy()

        active_edge = self._active_path_edge()
        if active_edge is None:
            tk.Label(
                self.path_edge_list_frame,
                text='No path edge selected. Turn on map add/link mode, then click an existing path edge to edit it.',
                bg=INFO_BOX_BACKGROUND,
                fg=TEXT_COLOR,
                font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
                anchor='w',
                justify='left',
                padx=12,
                pady=12,
                wraplength=SIDEBAR_WIDTH - 56,
            ).pack(fill='x')
            return

        edge_frame = tk.Frame(self.path_edge_list_frame, bg=INFO_BOX_BACKGROUND)
        edge_frame.pack(fill='x', padx=12, pady=12)
        tk.Label(
            edge_frame,
            text=f'Editing: {_extra_edge_full_summary(active_edge)}',
            bg=INFO_BOX_BACKGROUND,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE),
            anchor='w',
            justify='left',
            wraplength=SIDEBAR_WIDTH - 80,
        ).pack(anchor='w')
        self._make_sidebar_button(
            edge_frame,
            text='Stop Editing',
            command=lambda: self._edit_path_edge_points_off(),
        ).pack(anchor='w', pady=(6, 0))
        if active_edge.kind == 'walk':
            self._make_sidebar_button(
                edge_frame,
                text='Road Name',
                command=lambda active_edge=active_edge: self._edit_path_edge_label(active_edge),
            ).pack(anchor='w', pady=(6, 0))

    def _edit_path_edge_points_off(self) -> None:
        self.path_click_mode_var.set(False)
        self._set_active_path_edge(None)
        self.redraw()

    def _make_metro_segment_direct(self, segment: MetroLineSegment) -> None:
        from tkinter import messagebox

        try:
            make_metro_line_segment_direct(segment.line_name, segment.start_var, segment.end_var)
        except ValueError as exc:
            messagebox.showerror('Could Not Make Metro Segment Direct', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _add_turn_to_metro_segment(self, segment: MetroLineSegment) -> None:
        from tkinter import messagebox

        try:
            add_turn_to_metro_line_segment(segment.line_name, segment.start_var, segment.end_var)
        except ValueError as exc:
            messagebox.showerror('Could Not Add Metro Turn', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _flip_metro_segment_turn(self, segment: MetroLineSegment) -> None:
        from tkinter import messagebox

        try:
            flip_metro_line_segment_turn(segment.line_name, segment.start_var, segment.end_var)
        except ValueError as exc:
            messagebox.showerror('Could Not Flip Metro Turn', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _add_path_edge_for_selected_stop(self) -> None:
        if self.selected_stop_var is None:
            return

        from tkinter import messagebox, simpledialog

        stop = STOPS_BY_VAR[self.selected_stop_var]
        other_station = simpledialog.askstring(
            'Add Path Edge',
            'Enter the other endpoint as a station label / var or x, y:',
            parent=self.root,
        )
        if other_station is None:
            return

        other_station = other_station.strip()
        if not other_station:
            messagebox.showerror(
                'Invalid Endpoint',
                'Enter a station label / var or coordinates like x, y.',
                parent=self.root,
            )
            return

        kind_value = simpledialog.askstring(
            'Add Path Edge',
            'Path kind? Enter metro or walk:',
            initialvalue='metro',
            parent=self.root,
        )
        if kind_value is None:
            return

        normalized_kind = kind_value.strip().lower()
        if normalized_kind == 'metro':
            normalized_kind = 'connector'
        if normalized_kind not in {'connector', 'walk'}:
            messagebox.showerror('Invalid Path Kind', 'Path kind must be metro or walk.', parent=self.root)
            return

        label_value = simpledialog.askstring(
            'Add Path Edge',
            'Optional label (leave blank for default):',
            parent=self.root,
        )
        edge_label = None if label_value is None else (label_value.strip() or None)

        try:
            add_extra_edge(
                stop.var,
                other_station,
                cast(ExtraEdgeKind, normalized_kind),
                label=edge_label,
            )
        except ValueError as exc:
            messagebox.showerror('Could Not Add Path Edge', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _path_drag_kind(self) -> ExtraEdgeKind:
        value = self.path_drag_kind_var.get().strip().lower()
        return 'connector' if value in {'metro', 'connector'} else 'walk'

    def _path_drag_kind_label(self) -> str:
        return 'Metro' if self._path_drag_kind() == 'connector' else 'Walk'

    def _path_endpoint_identifier(self, endpoint: PathEndpoint) -> str:
        if endpoint.kind == 'stop':
            return endpoint.key
        return f'{endpoint.x}, {endpoint.y}'

    def _delete_path_drag_preview(self) -> None:
        for item_id in self.path_drag_preview_item_ids:
            self.canvas.delete(item_id)
        self.path_drag_preview_item_ids = []

    def _clear_path_drag(self) -> None:
        self._delete_path_drag_preview()
        self.path_drag_start_endpoint_key = None
        self.path_drag_current_canvas_point = None

    def _path_drag_preview_points(self) -> tuple[float, float, float, float] | None:
        if self.path_drag_start_endpoint_key is None or self.path_drag_current_canvas_point is None:
            return None

        start_endpoint = _path_endpoint_from_key(self.path_drag_start_endpoint_key)
        if start_endpoint is None:
            return None

        start_x, start_y = self.world_to_canvas(start_endpoint.plot_coordinates)
        end_x, end_y = self.path_drag_current_canvas_point
        target_endpoint = self._path_endpoint_hit_test(end_x, end_y)
        if target_endpoint is not None and target_endpoint.key != start_endpoint.key:
            end_x, end_y = self.world_to_canvas(target_endpoint.plot_coordinates)
        return (start_x, start_y, float(end_x), float(end_y))

    def _update_path_drag_preview(self) -> None:
        self._delete_path_drag_preview()
        preview_points = self._path_drag_preview_points()
        if preview_points is None:
            return

        start_x, start_y, end_x, end_y = preview_points
        preview_color = WALK_ROUTE_COLOR if self._path_drag_kind() == 'walk' else CONNECTOR_ROUTE_COLOR
        self.path_drag_preview_item_ids.append(
            self.canvas.create_line(
                start_x,
                start_y,
                end_x,
                end_y,
                fill=ROUTE_HIGHLIGHT_OUTLINE,
                width=PATH_EDIT_ACTIVE_OUTLINE_WIDTH,
                capstyle='round',
            )
        )
        line_kwargs: dict[str, object] = {}
        if self._path_drag_kind() == 'walk':
            line_kwargs['dash'] = (6, 4)
        self.path_drag_preview_item_ids.append(
            self.canvas.create_line(
                start_x,
                start_y,
                end_x,
                end_y,
                fill=preview_color,
                width=PATH_EDIT_ACTIVE_WIDTH,
                capstyle='round',
                **line_kwargs,
            )
        )

    def _add_path_node_at_canvas_point(self, canvas_x: int, canvas_y: int) -> bool:
        from tkinter import messagebox

        coordinates = self.canvas_to_world((float(canvas_x), float(canvas_y)))
        try:
            add_path_node(f'{coordinates[0]}, {coordinates[1]}')
        except ValueError as exc:
            messagebox.showerror('Could Not Add Path Node', str(exc), parent=self.root)
            return True

        self.selected_stop_var = None
        self.selected_path_node_key = _coordinate_endpoint_key(coordinates[0], coordinates[1])
        self._clear_metro_segment_selection()
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = coordinates
        self.show_cursor_guides = False
        self.path_click_status_var.set(
            f'Added node at ({coordinates[0]}, {coordinates[1]}). Drag from it to another station/node to add a {self._path_drag_kind_label()} path.'
        )
        self._refresh_after_path_edit(refresh_path_status=False, refresh_routes=False)
        return True

    def _finish_path_drag(self, canvas_x: int, canvas_y: int) -> bool:
        from tkinter import messagebox

        if self.path_drag_start_endpoint_key is None:
            return False

        start_endpoint = _path_endpoint_from_key(self.path_drag_start_endpoint_key)
        target_endpoint = self._path_endpoint_hit_test(canvas_x, canvas_y)
        if start_endpoint is None:
            self.path_click_status_var.set('That starting node is no longer available.')
            self.redraw()
            return True
        if target_endpoint is None:
            self.path_click_status_var.set('Drop on another existing station or node to add a path.')
            self.redraw()
            return True
        if target_endpoint.key == start_endpoint.key:
            self.path_click_status_var.set('Paths need two different endpoints.')
            self.redraw()
            return True

        try:
            add_extra_edge(
                self._path_endpoint_identifier(start_endpoint),
                self._path_endpoint_identifier(target_endpoint),
                self._path_drag_kind(),
            )
        except ValueError as exc:
            messagebox.showerror('Could Not Add Path Edge', str(exc), parent=self.root)
            return True

        self.selected_stop_var = target_endpoint.key if target_endpoint.kind == 'stop' else None
        self.selected_path_node_key = target_endpoint.key if target_endpoint.kind == 'coord' else None
        self._clear_metro_segment_selection()
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = target_endpoint.coordinates
        self.show_cursor_guides = False
        self._set_active_path_edge(None)
        self.path_click_status_var.set(
            f'Added {self._path_drag_kind_label()} path from {start_endpoint.display_label} to {target_endpoint.display_label}.'
        )
        self._refresh_after_path_edit(refresh_path_status=False)
        return True

    def _add_turn_to_path_edge(self, extra_edge: ExtraEdgeDefinition) -> None:
        from tkinter import messagebox

        try:
            add_turn_to_extra_edge(extra_edge.id)
        except ValueError as exc:
            messagebox.showerror('Could Not Add Turn', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _flip_path_edge_turn(self, extra_edge: ExtraEdgeDefinition) -> None:
        from tkinter import messagebox

        try:
            flip_extra_edge_turn(extra_edge.id)
        except ValueError as exc:
            messagebox.showerror('Could Not Flip Turn', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _make_path_edge_direct(self, extra_edge: ExtraEdgeDefinition) -> None:
        from tkinter import messagebox

        try:
            make_extra_edge_direct(extra_edge.id)
        except ValueError as exc:
            messagebox.showerror('Could Not Make Edge Direct', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _remove_path_edge(self, extra_edge: ExtraEdgeDefinition) -> None:
        from tkinter import messagebox

        try:
            remove_extra_edge(extra_edge.id)
        except ValueError as exc:
            messagebox.showerror('Could Not Remove Path Edge', str(exc), parent=self.root)
            return

        self._refresh_after_path_edit()

    def _handle_path_click_edit(self, canvas_x: int, canvas_y: int) -> bool:
        if not self.path_click_mode_var.get():
            return False

        if self._path_endpoint_hit_test(canvas_x, canvas_y) is not None:
            return False

        from tkinter import messagebox

        active_edge = self._active_path_edge()
        if active_edge is None:
            clicked_edge = self._extra_edge_hit_test(canvas_x, canvas_y)
            if clicked_edge is None:
                return self._add_path_node_at_canvas_point(canvas_x, canvas_y)
            else:
                self._set_active_path_edge(clicked_edge)
            self.redraw()
            return True

        remove_index = self._path_edit_handle_hit_test(active_edge, canvas_x, canvas_y)
        points = self._path_edit_points_for_edge(active_edge)
        try:
            if remove_index is not None:
                removed_point = points.pop(remove_index)
                set_extra_edge_path_points(active_edge.id, points)
                refreshed_edge = self._active_path_edge()
                self.path_click_status_var.set(
                    f'Removed point ({removed_point[0]}, {removed_point[1]}).'
                    + (
                        f' Editing {_extra_edge_full_summary(refreshed_edge)}.'
                        if refreshed_edge is not None
                        else ''
                    )
                )
            else:
                insert_index = self._path_edit_insert_index(active_edge, canvas_x, canvas_y)
                if insert_index is None:
                    clicked_edge = self._extra_edge_hit_test(canvas_x, canvas_y)
                    if clicked_edge is not None and clicked_edge.id != active_edge.id:
                        self._set_active_path_edge(clicked_edge)
                    else:
                        return self._add_path_node_at_canvas_point(canvas_x, canvas_y)
                    self.redraw()
                    return True

                new_point = self.canvas_to_world((float(canvas_x), float(canvas_y)))
                if new_point in points:
                    self.path_click_status_var.set(f'Point ({new_point[0]}, {new_point[1]}) is already on this path.')
                    self.redraw()
                    return True
                points.insert(insert_index, new_point)
                set_extra_edge_path_points(active_edge.id, points)
                refreshed_edge = self._active_path_edge()
                self.path_click_status_var.set(
                    f'Added point ({new_point[0]}, {new_point[1]}).'
                    + (
                        f' Editing {_extra_edge_full_summary(refreshed_edge)}.'
                        if refreshed_edge is not None
                        else ''
                    )
                )
        except ValueError as exc:
            messagebox.showerror('Could Not Edit Path Points', str(exc), parent=self.root)
            return True

        self._refresh_after_path_edit(refresh_path_status=False)
        return True

    def _undo_last_saved_change(self) -> None:
        from tkinter import messagebox

        try:
            _restore_last_network_snapshot()
        except ValueError as exc:
            messagebox.showinfo('Nothing To Undo', str(exc), parent=self.root)
            return

        if self.selected_stop_var not in STOPS_BY_VAR:
            self.selected_stop_var = None
        if self.city_limits_edit_stop_var not in STOPS_BY_VAR:
            self.city_limits_edit_stop_var = None
        if self.selected_path_node_key is not None and self._selected_path_node() is None:
            self.selected_path_node_key = None
        if self.selected_metro_segment_key is not None and self._selected_metro_segment() is None:
            self._clear_metro_segment_selection()
        self.route_controls_dirty = True
        self.route_dirty = True
        self.priority_dirty = True
        self.stats_dirty = True
        self.redraw()

    def _current_svg_export_options(self) -> SvgExportOptions:
        return SvgExportOptions(
            include_world_map=self.export_include_world_map_var.get(),
            include_grid=self.export_include_grid_var.get(),
            include_metro_lines=self.export_include_metro_lines_var.get(),
            include_stations=self.export_include_stations_var.get(),
            include_labels=self.export_include_labels_var.get(),
            include_path_nodes=self.export_include_path_nodes_var.get(),
            include_walking_paths=self.export_include_walking_paths_var.get(),
            include_connector_paths=self.export_include_connector_paths_var.get(),
            include_current_route=self.export_include_current_route_var.get(),
            include_planning_circle=self.export_include_planning_circle_var.get(),
            include_connected_area=self.export_include_connected_area_var.get(),
            include_alignment_ellipses=self.export_include_alignment_ellipses_var.get(),
            include_frontier_highlights=self.export_include_frontier_highlights_var.get(),
            include_railway_finishing=self.export_include_railway_finishing_var.get(),
        )

    def _sync_svg_export_options_to_current_view(self) -> None:
        self.export_include_world_map_var.set(self.show_world_map_render_var.get())
        self.export_include_labels_var.set(self.show_labels_var.get())
        self.export_include_planning_circle_var.set(self.show_planning_circle_var.get())
        self.export_include_connected_area_var.set(self.show_connected_area_var.get())
        self.export_include_alignment_ellipses_var.set(self.show_alignment_reminders_var.get())
        self.export_include_frontier_highlights_var.set(self.show_frontier_highlights_var.get())
        self.export_include_railway_finishing_var.set(self.railway_finish_mode_var.get())

    def _show_export_svg_options(self) -> None:
        self._sync_svg_export_options_to_current_view()

        dialog = tk.Toplevel(self.root)
        dialog.title('Export SVG')
        dialog.configure(bg=BACKGROUND_COLOR)
        dialog.transient(self.root)
        dialog.resizable(False, False)

        body = tk.Frame(dialog, bg=BACKGROUND_COLOR)
        body.pack(fill='both', expand=True, padx=16, pady=14)
        tk.Label(
            body,
            text='Export SVG',
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            font=('Helvetica', SIDEBAR_TEXT_FONT_SIZE, 'bold'),
            anchor='w',
        ).pack(anchor='w', pady=(0, 8))

        option_rows = [
            ('World map image', self.export_include_world_map_var),
            ('Grid axes', self.export_include_grid_var),
            ('Metro lines', self.export_include_metro_lines_var),
            ('Stations', self.export_include_stations_var),
            ('Labels', self.export_include_labels_var),
            ('Path nodes', self.export_include_path_nodes_var),
            ('Walking paths', self.export_include_walking_paths_var),
            ('Connector paths', self.export_include_connector_paths_var),
            ('Current route highlight', self.export_include_current_route_var),
            ('Planning radius', self.export_include_planning_circle_var),
            ('Connected area', self.export_include_connected_area_var),
            ('Alignment ellipses', self.export_include_alignment_ellipses_var),
            ('Frontier highlights', self.export_include_frontier_highlights_var),
        ]
        if SHOW_RAILWAY_FINISHING_UI:
            option_rows.append(('Railway finishing highlights', self.export_include_railway_finishing_var))
        for text, variable in option_rows:
            self._make_sidebar_checkbox(
                body,
                text=text,
                variable=variable,
                command=lambda: None,
            ).pack(anchor='w', pady=1)

        button_row = tk.Frame(body, bg=BACKGROUND_COLOR)
        button_row.pack(fill='x', pady=(12, 0))

        def export_and_close() -> None:
            dialog.destroy()
            self._export_current_map(self._current_svg_export_options())

        self._make_sidebar_button(
            button_row,
            text='Export',
            command=export_and_close,
        ).pack(side='right')
        self._make_sidebar_button(
            button_row,
            text='Cancel',
            command=dialog.destroy,
        ).pack(side='right', padx=(0, 10))

        dialog.update_idletasks()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        dialog_width = dialog.winfo_width()
        dialog.geometry(f'+{root_x + max(20, root_width - dialog_width - 36)}+{root_y + 80}')
        dialog.grab_set()
        dialog.focus_set()

    def _export_current_map(self, export_options: SvgExportOptions) -> None:
        from tkinter import messagebox

        self.root.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 2 or canvas_height < 2:
            messagebox.showerror('Export Failed', 'The map canvas is not ready to export yet.', parent=self.root)
            return

        self.width = canvas_width
        self.height = canvas_height
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        export_path = EXPORTS_DIR / f"metro-map-{datetime.now().strftime('%Y%m%d-%H%M%S')}.svg"
        world_map_image = (
            self._current_world_map_svg_image()
            if export_options.include_world_map
            else None
        )
        if export_options.include_world_map and world_map_image is None:
            messagebox.showerror(
                'Export Failed',
                'The world map image is not ready to export yet. Render the world map first, or uncheck World map image.',
                parent=self.root,
            )
            return
        try:
            export_path.write_text(
                _build_map_svg(
                    width=self.width,
                    height=self.height,
                    padding=self.padding,
                    zoom=self.zoom,
                    pan_x=self.pan_x,
                    pan_y=self.pan_y,
                    visible_line_names=self._visible_line_names(),
                    export_options=export_options,
                    world_map_image=world_map_image,
                    current_route=self.current_route,
                ),
                encoding='utf-8',
            )
        except Exception as exc:
            messagebox.showerror(
                'Export Failed',
                f'Could not write the SVG export.\n\n{exc}',
                parent=self.root,
            )
            return

        messagebox.showinfo('Map Exported', f'Saved SVG to:\n{export_path}', parent=self.root)

    def _current_world_map_svg_image(self) -> SvgRasterImage | None:
        render_underlay = self._current_world_map_render_underlay()
        if render_underlay is None:
            return None
        payload, source_image = render_underlay

        try:
            render_min_x = _render_cache_int(payload, 'min_x')
            render_max_x = _render_cache_int(payload, 'max_x')
            render_min_z = _render_cache_int(payload, 'min_z')
            render_max_z = _render_cache_int(payload, 'max_z')
        except (KeyError, TypeError, ValueError):
            return None

        top_left_x, top_left_y = self.world_to_canvas((render_min_x, -render_min_z))
        bottom_right_x, bottom_right_y = self.world_to_canvas((render_max_x, -render_max_z))
        left = min(top_left_x, bottom_right_x)
        right = max(top_left_x, bottom_right_x)
        top = min(top_left_y, bottom_right_y)
        bottom = max(top_left_y, bottom_right_y)
        if right <= left or bottom <= top:
            return None

        visible_left = max(0.0, left)
        visible_top = max(0.0, top)
        visible_right = min(float(self.width), right)
        visible_bottom = min(float(self.height), bottom)
        if visible_right <= visible_left or visible_bottom <= visible_top:
            return None

        image_width, image_height = source_image.size
        source_left = floor(max(0, min(image_width, ((visible_left - left) / (right - left)) * image_width)))
        source_right = ceil(max(0, min(image_width, ((visible_right - left) / (right - left)) * image_width)))
        source_top = floor(max(0, min(image_height, ((visible_top - top) / (bottom - top)) * image_height)))
        source_bottom = ceil(max(0, min(image_height, ((visible_bottom - top) / (bottom - top)) * image_height)))
        if source_right <= source_left or source_bottom <= source_top:
            return None

        visible_width = max(1, round(visible_right - visible_left))
        visible_height = max(1, round(visible_bottom - visible_top))
        try:
            resampling_filter = Image.Resampling.BILINEAR
        except AttributeError:
            resampling_filter = cast(Any, Image).BILINEAR
        underlay = source_image.crop((source_left, source_top, source_right, source_bottom))
        underlay = underlay.resize((visible_width, visible_height), resampling_filter)
        alpha = underlay.getchannel('A').point(_limit_world_map_alpha)
        underlay.putalpha(alpha)

        buffer = io.BytesIO()
        underlay.save(buffer, format='PNG')
        encoded_image = base64.b64encode(buffer.getvalue()).decode('ascii')
        return SvgRasterImage(
            data_uri=f'data:image/png;base64,{encoded_image}',
            left=visible_left,
            top=visible_top,
            width=visible_width,
            height=visible_height,
        )

    def redraw(self) -> None:
        self.fast_viewport_transform_active = False
        defer_expensive_layers = self.defer_expensive_viewport_layers
        self._clear_info_popup()
        if self.stats_dirty:
            self._refresh_station_stats()
            self.stats_dirty = False
        if self.route_controls_dirty:
            self._refresh_route_controls()
            self.route_controls_dirty = False
        if self.route_dirty:
            self._refresh_current_route()
            self.route_dirty = False
        if self.priority_dirty:
            self._refresh_priority_list()
            self.priority_dirty = False
        if self.railway_finish_dirty:
            self._refresh_railway_finish_controls()
            self.railway_finish_dirty = False
        if self.selected_stop_var not in STOPS_BY_VAR:
            self.selected_stop_var = None
        if self.selected_path_node_key is not None and self._selected_path_node() is None:
            self.selected_path_node_key = None
        if self.selected_metro_segment_key is not None and self._selected_metro_segment() is None:
            self._clear_metro_segment_selection()
        if self.selected_metro_segment_keys:
            self._set_metro_segment_selection(
                self.selected_metro_segment_keys,
                primary_key=self.selected_metro_segment_key,
                anchor_key=self.metro_segment_selection_anchor_key,
            )
        if self.active_path_edge_id is not None and self._active_path_edge() is None:
            self._set_active_path_edge(None)
        if self.path_edge_list_dirty:
            self._refresh_path_edge_list()
            self.path_edge_list_dirty = False
        self.canvas.delete('all')
        self.path_drag_preview_item_ids = []
        self.station_canvas_positions = {}
        self.path_node_canvas_positions = {}
        self.overlay_image_refs = []
        self.cursor_overlay_ids = {}
        visible_line_names = self._visible_line_names()
        frontier_label_stop_vars = (
            _frontier_highlight_stop_vars()
            if self.show_frontier_highlights_var.get()
            else frozenset()
        )

        min_x, max_x, min_y, max_y, _ = self._plot_transform()
        label_font_size = _label_font_size(self.zoom)
        label_offset_x, label_offset_y = self._label_offset()

        if not defer_expensive_layers:
            self._draw_world_map_render_underlay()
        if min_x <= 0 <= max_x:
            zero_x = self.world_to_canvas((0, min_y))[0]
            zero_top = self.world_to_canvas((0, max_y))[1]
            zero_bottom = self.world_to_canvas((0, min_y))[1]
            self.canvas.create_line(
                zero_x,
                zero_top,
                zero_x,
                zero_bottom,
                fill=GRID_COLOR,
                dash=(4, 4),
            )
        if min_y <= 0 <= max_y:
            zero_left = self.world_to_canvas((min_x, 0))[0]
            zero_right = self.world_to_canvas((max_x, 0))[0]
            zero_y = self.world_to_canvas((min_x, 0))[1]
            self.canvas.create_line(
                zero_left,
                zero_y,
                zero_right,
                zero_y,
                fill=GRID_COLOR,
                dash=(4, 4),
            )

        self._draw_world_map_active_target_bounds()
        if not defer_expensive_layers:
            self._draw_planning_circle()
            self._draw_connected_area()
        self._draw_city_limits()

        self._draw_metro_lines(visible_line_names)

        self._draw_extra_edges()
        self._draw_current_route()
        self._draw_path_nodes()
        self._draw_selected_metro_segment_highlight()
        if self.railway_finish_mode_var.get():
            self._draw_railway_finish_highlights(visible_line_names)
        else:
            self._draw_frontier_highlights(visible_line_names)
        self._draw_alignment_reminders()

        for stop in METRO_STOPS:
            stop_visible_line_names = self._stop_visible_line_names(stop, visible_line_names)
            if not stop_visible_line_names and STOP_LINE_NAMES[stop.var]:
                continue
            canvas_x, canvas_y = self.world_to_canvas(stop.plot_coordinates)
            self.station_canvas_positions[stop.var] = (canvas_x, canvas_y)
            stop_fill = self._stop_fill_for_visible_lines(stop_visible_line_names)
            label_fill = _label_fill_for_visible_line_names(stop_visible_line_names)
            is_priority_highlight = stop.var in self.priority_highlight_stop_vars
            if is_priority_highlight:
                self.canvas.create_oval(
                    canvas_x - STATION_RADIUS - 10,
                    canvas_y - STATION_RADIUS - 10,
                    canvas_x + STATION_RADIUS + 10,
                    canvas_y + STATION_RADIUS + 10,
                    fill='',
                    outline=PRIORITY_HIGHLIGHT_SOFT_COLOR,
                    width=3,
                )
                self.canvas.create_oval(
                    canvas_x - STATION_RADIUS - 5,
                    canvas_y - STATION_RADIUS - 5,
                    canvas_x + STATION_RADIUS + 5,
                    canvas_y + STATION_RADIUS + 5,
                    fill='',
                    outline=PRIORITY_HIGHLIGHT_COLOR,
                    width=2,
                )
            self.canvas.create_oval(
                canvas_x - STATION_RADIUS,
                canvas_y - STATION_RADIUS,
                canvas_x + STATION_RADIUS,
                canvas_y + STATION_RADIUS,
                fill=stop_fill,
                outline=UNASSOCIATED_STATION_OUTLINE if not stop_visible_line_names else '',
                width=2 if not stop_visible_line_names else 1,
            )
            if self.show_labels_var.get():
                active_label_font_size = label_font_size + (
                    FRONTIER_LABEL_SIZE_BOOST if stop.var in frontier_label_stop_vars else 0
                )
                label_font = (
                    ('Helvetica', active_label_font_size, 'bold')
                    if stop.var in frontier_label_stop_vars or is_priority_highlight
                    else ('Helvetica', active_label_font_size)
                )
                label_text = _display_label(stop.lbl)
                for casing_offset_x, casing_offset_y in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.canvas.create_text(
                        canvas_x + label_offset_x + casing_offset_x,
                        canvas_y - label_offset_y + casing_offset_y,
                        anchor='sw',
                        angle=LABEL_ANGLE,
                        text=label_text,
                        fill=LABEL_CASING_COLOR,
                        font=label_font,
                    )
                if is_priority_highlight:
                    for glow_offset_x, glow_offset_y in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                        self.canvas.create_text(
                            canvas_x + label_offset_x + glow_offset_x,
                            canvas_y - label_offset_y + glow_offset_y,
                            anchor='sw',
                            angle=LABEL_ANGLE,
                            text=label_text,
                            fill=PRIORITY_HIGHLIGHT_COLOR,
                            font=label_font,
                        )
                self.canvas.create_text(
                    canvas_x + label_offset_x,
                    canvas_y - label_offset_y,
                    anchor='sw',
                    angle=LABEL_ANGLE,
                    text=label_text,
                    fill=label_fill,
                    font=label_font,
                )

        self._draw_path_drag_preview()

        if not self.is_dragging:
            if self.selected_metro_segment_key is not None:
                self._draw_selected_metro_segment_info()
            elif self.selected_path_node_key is not None:
                self._draw_selected_path_node_info()
            else:
                self._draw_selected_stop_info()
        self._draw_cursor_overlay()

    def _draw_overlay_image(self, image: Image.Image) -> None:
        overlay_image = ImageTk.PhotoImage(image)
        self.overlay_image_refs.append(overlay_image)
        self.canvas.create_image(0, 0, anchor='nw', image=overlay_image)

    def _invalidate_world_map_render_cache(self) -> None:
        self.world_map_render_cache_stat = None
        self.world_map_render_image_stat = None
        self.world_map_render_image_path = None
        self.world_map_render_payload = None
        self.world_map_render_source_image = None
        self.world_map_render_cache_checked_at = 0.0
        self.world_map_spiral_check_cache_stat = None
        self.world_map_spiral_check_payload = None

    def _world_map_preview_path_for(self, source_image_path: Path, render_cache_path: Path) -> Path:
        return render_cache_path.with_name(f'{source_image_path.stem}{WORLD_MAP_PREVIEW_SUFFIX}')

    def _world_map_display_image_path(
        self,
        source_image_path: Path,
        render_cache_path: Path,
    ) -> tuple[Path, FileStatKey] | None:
        source_stat = _file_stat_key(source_image_path)
        if source_stat is None:
            return None

        try:
            with Image.open(source_image_path) as source_image:
                source_width, source_height = source_image.size
        except OSError:
            return None

        if max(source_width, source_height) <= WORLD_MAP_PREVIEW_MAX_DIMENSION:
            return (source_image_path, source_stat)

        preview_path = self._world_map_preview_path_for(source_image_path, render_cache_path)
        preview_stat = _file_stat_key(preview_path)
        if preview_stat is not None and preview_stat[1] >= source_stat[1]:
            return (preview_path, preview_stat)

        self._ensure_world_map_preview_async(source_image_path, preview_path, source_stat)
        if preview_stat is not None:
            return (preview_path, preview_stat)
        return None

    def _ensure_world_map_preview_async(
        self,
        source_image_path: Path,
        preview_path: Path,
        source_stat: FileStatKey,
    ) -> None:
        build_key = (str(source_image_path.resolve()), source_stat)
        if self.world_map_preview_build_key == build_key:
            return
        self.world_map_preview_build_key = build_key

        def build_preview() -> None:
            try:
                with Image.open(source_image_path) as source_image:
                    preview_image = source_image.convert('RGBA')
                try:
                    resampling_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resampling_filter = cast(Any, Image).LANCZOS
                preview_image.thumbnail(
                    (WORLD_MAP_PREVIEW_MAX_DIMENSION, WORLD_MAP_PREVIEW_MAX_DIMENSION),
                    resampling_filter,
                )
                preview_path.parent.mkdir(parents=True, exist_ok=True)
                preview_image.save(preview_path)
            except Exception as exc:
                self.world_map_preview_queue.put((False, str(source_image_path), str(exc)))
                return
            self.world_map_preview_queue.put((True, str(source_image_path), str(preview_path)))

        threading.Thread(target=build_preview, daemon=True).start()
        self._schedule_world_map_preview_poll()

    def _schedule_world_map_preview_poll(self) -> None:
        if self.world_map_preview_poll_after_id is not None:
            return
        self.world_map_preview_poll_after_id = self.root.after(250, self._poll_world_map_preview_queue)

    def _poll_world_map_preview_queue(self) -> None:
        self.world_map_preview_poll_after_id = None
        handled_message = False
        while True:
            try:
                _succeeded, _source, _detail = self.world_map_preview_queue.get_nowait()
            except queue.Empty:
                break
            handled_message = True
            self.world_map_preview_build_key = None

        if handled_message:
            self._invalidate_world_map_render_cache()
            self.redraw()
            return

        if self.world_map_preview_build_key is not None:
            self._schedule_world_map_preview_poll()

    def _current_world_map_render_underlay(self) -> tuple[dict[str, object], Image.Image] | None:
        now = time.monotonic()
        cached_underlay: tuple[dict[str, object], Image.Image] | None = None
        if self.world_map_render_payload is not None and self.world_map_render_source_image is not None:
            cached_underlay = (self.world_map_render_payload, self.world_map_render_source_image)
        if (
            cached_underlay is not None
            and now - self.world_map_render_cache_checked_at < WORLD_MAP_FILE_POLL_MIN_SECONDS
        ):
            return cached_underlay
        self.world_map_render_cache_checked_at = now

        try:
            from worldgen.config import load_config
            from worldgen.generator import BedrockWorldGenerator

            config = load_config()
            mode_paths = BedrockWorldGenerator(config).paths_for_mode(
                self._selected_world_map_mode_key()
            )
        except Exception:
            if cached_underlay is not None:
                return cached_underlay
            self._invalidate_world_map_render_cache()
            return None

        render_cache_path = mode_paths.render_cache_path
        render_cache_stat = _file_stat_key(render_cache_path)
        if render_cache_stat is None:
            legacy_cache_path = (
                config.repo_root
                / 'worldgen_data'
                / 'cache'
                / mode_paths.render_cache_path.name
            )
            legacy_cache_stat = _file_stat_key(legacy_cache_path)
            if legacy_cache_stat is not None:
                render_cache_path = legacy_cache_path
                render_cache_stat = legacy_cache_stat
        if render_cache_stat is None:
            if cached_underlay is not None:
                return cached_underlay
            self._invalidate_world_map_render_cache()
            return None

        if (
            self.world_map_render_cache_stat == render_cache_stat
            and self.world_map_render_payload is not None
            and self.world_map_render_source_image is not None
            and self.world_map_render_image_path is not None
        ):
            image_stat = _file_stat_key(self.world_map_render_image_path)
            if image_stat is not None and image_stat == self.world_map_render_image_stat:
                return (self.world_map_render_payload, self.world_map_render_source_image)

        try:
            payload = json.loads(render_cache_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            if cached_underlay is not None:
                return cached_underlay
            self._invalidate_world_map_render_cache()
            return None
        if not isinstance(payload, dict):
            if cached_underlay is not None:
                return cached_underlay
            self._invalidate_world_map_render_cache()
            return None

        image_candidates: list[Path] = []
        image_candidates.append(mode_paths.docs_render_image_path)
        image_candidates.append(mode_paths.render_image_path)
        payload_image_path = payload.get('image_path')
        if isinstance(payload_image_path, str) and payload_image_path:
            image_candidates.append(Path(payload_image_path))
        image_candidates.append(config.repo_root / 'worldgen_output' / mode_paths.render_image_path.name)
        image_candidates.append(
            config.repo_root / 'docs' / 'assets' / mode_paths.render_image_path.name
        )

        image_path: Path | None = None
        image_stat: FileStatKey | None = None
        source_image: Image.Image | None = None
        seen_image_paths: set[Path] = set()
        for candidate_image_path in image_candidates:
            try:
                resolved_candidate = candidate_image_path.resolve()
            except OSError:
                resolved_candidate = candidate_image_path
            if resolved_candidate in seen_image_paths:
                continue
            seen_image_paths.add(resolved_candidate)

            candidate_image_stat = _file_stat_key(candidate_image_path)
            if candidate_image_stat is None:
                continue
            display_image = self._world_map_display_image_path(
                candidate_image_path,
                mode_paths.render_cache_path,
            )
            if display_image is None:
                break
            display_image_path, display_image_stat = display_image
            try:
                candidate_source_image = Image.open(display_image_path).convert('RGBA')
            except OSError:
                continue
            image_path = display_image_path
            image_stat = display_image_stat
            source_image = candidate_source_image
            break

        if image_path is None or image_stat is None or source_image is None:
            if cached_underlay is not None:
                return cached_underlay
            self._invalidate_world_map_render_cache()
            return None

        self.world_map_render_cache_stat = render_cache_stat
        self.world_map_render_image_stat = image_stat
        self.world_map_render_image_path = image_path
        self.world_map_render_payload = payload
        self.world_map_render_source_image = source_image
        return (payload, source_image)

    def _current_world_map_spiral_check_preview(self) -> dict[str, object] | None:
        try:
            from worldgen.config import load_config
            from worldgen.generator import BedrockWorldGenerator, SPIRAL_CHECK_PREVIEW_FILE_NAME

            config = load_config()
            mode_key = self._selected_world_map_mode_key()
            if mode_key != 'local_seed_surface':
                self.world_map_spiral_check_cache_stat = None
                self.world_map_spiral_check_payload = None
                return None
            preview_path = (
                BedrockWorldGenerator(config).paths_for_mode(mode_key).render_cache_path
                .with_name(SPIRAL_CHECK_PREVIEW_FILE_NAME)
            )
        except Exception:
            self.world_map_spiral_check_cache_stat = None
            self.world_map_spiral_check_payload = None
            return None

        preview_stat = _file_stat_key(preview_path)
        if preview_stat is None:
            self.world_map_spiral_check_cache_stat = None
            self.world_map_spiral_check_payload = None
            return None
        if (
            preview_stat == self.world_map_spiral_check_cache_stat
            and self.world_map_spiral_check_payload is not None
        ):
            return self.world_map_spiral_check_payload

        try:
            payload = json.loads(preview_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            self.world_map_spiral_check_cache_stat = None
            self.world_map_spiral_check_payload = None
            return None
        if not isinstance(payload, dict):
            return None
        self.world_map_spiral_check_cache_stat = preview_stat
        self.world_map_spiral_check_payload = payload
        return payload

    def _draw_world_map_render_underlay(self, *, fast_resample: bool = False) -> None:
        if not self.show_world_map_render_var.get():
            return

        render_underlay = self._current_world_map_render_underlay()
        if render_underlay is None:
            return
        payload, source_image = render_underlay

        try:
            render_min_x = _render_cache_int(payload, 'min_x')
            render_max_x = _render_cache_int(payload, 'max_x')
            render_min_z = _render_cache_int(payload, 'min_z')
            render_max_z = _render_cache_int(payload, 'max_z')
        except (KeyError, TypeError, ValueError):
            return

        top_left_x, top_left_y = self.world_to_canvas((render_min_x, -render_min_z))
        bottom_right_x, bottom_right_y = self.world_to_canvas((render_max_x, -render_max_z))
        left = min(top_left_x, bottom_right_x)
        right = max(top_left_x, bottom_right_x)
        top = min(top_left_y, bottom_right_y)
        bottom = max(top_left_y, bottom_right_y)
        if right <= left or bottom <= top:
            return

        visible_left = max(0.0, left)
        visible_top = max(0.0, top)
        visible_right = min(float(self.width), right)
        visible_bottom = min(float(self.height), bottom)
        if visible_right <= visible_left or visible_bottom <= visible_top:
            return

        image_width, image_height = source_image.size
        source_left = floor(max(0, min(image_width, ((visible_left - left) / (right - left)) * image_width)))
        source_right = ceil(max(0, min(image_width, ((visible_right - left) / (right - left)) * image_width)))
        source_top = floor(max(0, min(image_height, ((visible_top - top) / (bottom - top)) * image_height)))
        source_bottom = ceil(max(0, min(image_height, ((visible_bottom - top) / (bottom - top)) * image_height)))
        if source_right <= source_left or source_bottom <= source_top:
            return

        visible_width = max(1, round(visible_right - visible_left))
        visible_height = max(1, round(visible_bottom - visible_top))
        if fast_resample:
            try:
                resampling_filter = Image.Resampling.NEAREST
            except AttributeError:
                resampling_filter = cast(Any, Image).NEAREST
        else:
            try:
                resampling_filter = Image.Resampling.BILINEAR
            except AttributeError:
                resampling_filter = cast(Any, Image).BILINEAR
        underlay = source_image.crop((source_left, source_top, source_right, source_bottom))
        underlay = underlay.resize((visible_width, visible_height), resampling_filter)
        alpha = underlay.getchannel('A').point(_limit_world_map_alpha)
        underlay.putalpha(alpha)
        underlay_image = ImageTk.PhotoImage(underlay)
        self.overlay_image_refs.append(underlay_image)
        image_id = self.canvas.create_image(visible_left, visible_top, anchor='nw', image=underlay_image)
        self.canvas.tag_lower(image_id)

    def _draw_world_map_render_bounds(self, payload: dict[str, object]) -> None:
        bounds = _world_map_visible_render_bounds_from_payload(payload)
        if bounds is None:
            return
        render_min_x, render_max_x, render_min_z, render_max_z = bounds

        if render_min_x > render_max_x or render_min_z > render_max_z:
            return

        top_left_x, top_left_y = self.world_to_canvas((render_min_x, -render_min_z))
        bottom_right_x, bottom_right_y = self.world_to_canvas((render_max_x, -render_max_z))
        left = min(top_left_x, bottom_right_x)
        right = max(top_left_x, bottom_right_x)
        top = min(top_left_y, bottom_right_y)
        bottom = max(top_left_y, bottom_right_y)

        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        if right - left < WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE:
            left = center_x - (WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE / 2)
            right = center_x + (WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE / 2)
        if bottom - top < WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE:
            top = center_y - (WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE / 2)
            bottom = center_y + (WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE / 2)

        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=WORLD_MAP_RENDER_BOUNDS_COLOR,
            width=WORLD_MAP_RENDER_BOUNDS_WIDTH,
            dash=WORLD_MAP_RENDER_BOUNDS_DASH,
        )

    def _draw_world_map_active_target_bounds(self) -> None:
        if not self.world_map_task_running:
            return

        bounds = self.world_map_active_target_bounds
        if bounds is None:
            return

        min_x, max_x, min_z, max_z = bounds
        if min_x > max_x or min_z > max_z:
            return

        top_left_x, top_left_y = self.world_to_canvas((min_x, -min_z))
        bottom_right_x, bottom_right_y = self.world_to_canvas((max_x, -max_z))
        left = min(top_left_x, bottom_right_x)
        right = max(top_left_x, bottom_right_x)
        top = min(top_left_y, bottom_right_y)
        bottom = max(top_left_y, bottom_right_y)

        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        if right - left < WORLD_MAP_ACTIVE_TARGET_MIN_CANVAS_SIZE:
            left = center_x - (WORLD_MAP_ACTIVE_TARGET_MIN_CANVAS_SIZE / 2)
            right = center_x + (WORLD_MAP_ACTIVE_TARGET_MIN_CANVAS_SIZE / 2)
        if bottom - top < WORLD_MAP_ACTIVE_TARGET_MIN_CANVAS_SIZE:
            top = center_y - (WORLD_MAP_ACTIVE_TARGET_MIN_CANVAS_SIZE / 2)
            bottom = center_y + (WORLD_MAP_ACTIVE_TARGET_MIN_CANVAS_SIZE / 2)

        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=WORLD_MAP_ACTIVE_TARGET_COLOR,
            width=WORLD_MAP_ACTIVE_TARGET_WIDTH,
            dash=WORLD_MAP_ACTIVE_TARGET_DASH,
        )

    def _draw_world_map_spiral_check_preview(self) -> None:
        payload = self._current_world_map_spiral_check_preview()
        if payload is None:
            return

        scan_bounds = _world_map_preview_bounds(payload, 'scan')
        if scan_bounds is not None:
            self._draw_world_map_preview_rectangle(
                scan_bounds,
                outline=WORLD_MAP_SPIRAL_CHECK_COLOR,
                width=WORLD_MAP_SPIRAL_CHECK_WIDTH,
                dash=WORLD_MAP_SPIRAL_CHECK_DASH,
                min_canvas_size=WORLD_MAP_RENDER_BOUNDS_MIN_CANVAS_SIZE,
            )

        center_x = payload.get('center_x')
        center_z = payload.get('center_z')
        last_checked_x = payload.get('last_checked_x')
        last_checked_z = payload.get('last_checked_z')
        if (
            isinstance(center_x, int)
            and isinstance(center_z, int)
            and isinstance(last_checked_x, int)
            and isinstance(last_checked_z, int)
        ):
            start_x, start_y = self.world_to_canvas((center_x, -center_z))
            end_x, end_y = self.world_to_canvas((last_checked_x, -last_checked_z))
            self.canvas.create_line(
                start_x,
                start_y,
                end_x,
                end_y,
                fill=WORLD_MAP_SPIRAL_CHECK_COLOR,
                width=WORLD_MAP_SPIRAL_CHECK_WIDTH,
                dash=WORLD_MAP_SPIRAL_CHECK_DASH,
            )
            radius = max(4, WORLD_MAP_SPIRAL_CHECK_WIDTH * 2)
            self.canvas.create_oval(
                end_x - radius,
                end_y - radius,
                end_x + radius,
                end_y + radius,
                outline=WORLD_MAP_SPIRAL_CHECK_COLOR,
                width=WORLD_MAP_SPIRAL_CHECK_WIDTH,
            )

        blank_bounds = _world_map_preview_bounds(payload, 'blank')
        if blank_bounds is None:
            return
        self._draw_world_map_preview_rectangle(
            blank_bounds,
            outline=WORLD_MAP_SPIRAL_BLANK_COLOR,
            width=WORLD_MAP_SPIRAL_CHECK_WIDTH,
            dash=None,
            min_canvas_size=WORLD_MAP_SPIRAL_BLANK_MIN_CANVAS_SIZE,
        )

    def _draw_world_map_preview_rectangle(
        self,
        bounds: tuple[int, int, int, int],
        *,
        outline: str,
        width: int,
        dash: tuple[int, int] | None,
        min_canvas_size: int,
    ) -> None:
        min_x, max_x, min_z, max_z = bounds
        top_left_x, top_left_y = self.world_to_canvas((min_x, -min_z))
        bottom_right_x, bottom_right_y = self.world_to_canvas((max_x, -max_z))
        left = min(top_left_x, bottom_right_x)
        right = max(top_left_x, bottom_right_x)
        top = min(top_left_y, bottom_right_y)
        bottom = max(top_left_y, bottom_right_y)
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        if right - left < min_canvas_size:
            left = center_x - (min_canvas_size / 2)
            right = center_x + (min_canvas_size / 2)
        if bottom - top < min_canvas_size:
            top = center_y - (min_canvas_size / 2)
            bottom = center_y + (min_canvas_size / 2)
        if dash is None:
            self.canvas.create_rectangle(
                left,
                top,
                right,
                bottom,
                outline=outline,
                width=width,
            )
        else:
            self.canvas.create_rectangle(
                left,
                top,
                right,
                bottom,
                outline=outline,
                width=width,
                dash=dash,
            )

    def _draw_planning_circle(self) -> None:
        if not self.show_planning_circle_var.get():
            return

        planning_radius = _planning_radius_distance()
        if planning_radius <= 0:
            return

        center_stop = _blackport_stop()
        center_x, center_y = self.world_to_canvas(center_stop.plot_coordinates)
        _min_x, _max_x, _min_y, _max_y, scale = self._plot_transform()
        canvas_radius = planning_radius * scale * self.zoom
        if canvas_radius <= 0:
            return

        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, 'RGBA')
        draw.ellipse(
            (
                center_x - canvas_radius,
                center_y - canvas_radius,
                center_x + canvas_radius,
                center_y + canvas_radius,
            ),
            fill=CIRCLE_OVERLAY_RGBA,
        )
        self._draw_overlay_image(overlay)

    def _draw_alignment_reminders(self) -> None:
        if not self.show_alignment_reminders_var.get():
            return

        for reminder in ALIGNMENT_REMINDERS:
            if reminder.is_aligned:
                continue

            left, right, top, bottom = _alignment_reminder_bounds(
                reminder,
                self.world_to_canvas,
                zoom=self.zoom,
            )

            self.canvas.create_oval(
                left,
                top,
                right,
                bottom,
                fill='',
                outline=ALIGNMENT_REMINDER_OUTLINE,
                width=ALIGNMENT_REMINDER_WIDTH,
                dash=(8, 4),
            )
            self.canvas.create_text(
                (left + right) / 2,
                max(ALIGNMENT_REMINDER_LABEL_FONT_SIZE + 2, top - 4),
                text=reminder.debug_label,
                fill=ALIGNMENT_REMINDER_OUTLINE,
                font=('Helvetica', ALIGNMENT_REMINDER_LABEL_FONT_SIZE),
                anchor='s',
                justify='center',
                width=max(180, right - left),
            )

    def _draw_connected_area(self) -> None:
        if not self.show_connected_area_var.get():
            return

        area_loops = _connected_route_area_world_loops()
        if not area_loops:
            return

        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, 'RGBA')
        for area_loop in area_loops:
            polygon_points: list[tuple[float, float]] = []
            for point in area_loop:
                canvas_x, canvas_y = self.world_to_canvas(point)
                polygon_points.append((canvas_x, canvas_y))
            draw.polygon(polygon_points, fill=AREA_OVERLAY_RGBA)
        self._draw_overlay_image(overlay)

    def _draw_city_limits(self) -> None:
        active_stop_var = self.city_limits_edit_stop_var
        if not self.show_city_limits_var.get() and active_stop_var is None:
            return

        for stop in METRO_STOPS:
            world_points = _city_limit_world_points(stop)
            if not world_points:
                continue
            is_active = active_stop_var == stop.var
            if not self.show_city_limits_var.get() and not is_active:
                continue

            canvas_points = [self.world_to_canvas((point_x, -point_y)) for point_x, point_y in world_points]
            flat_points = [coordinate for point in canvas_points for coordinate in point]
            fill_color = CITY_LIMIT_ACTIVE_FILL if is_active else CITY_LIMIT_FILL
            outline_color = CITY_LIMIT_ACTIVE_OUTLINE if is_active else CITY_LIMIT_OUTLINE
            if len(canvas_points) >= 3:
                self.canvas.create_polygon(
                    *flat_points,
                    fill=fill_color,
                    outline=outline_color,
                    width=CITY_LIMIT_WIDTH,
                    stipple='gray25',
                )
            if len(canvas_points) >= 2:
                self.canvas.create_line(
                    *flat_points,
                    fill=outline_color,
                    width=CITY_LIMIT_WIDTH,
                    dash=CITY_LIMIT_DASH,
                    capstyle='round',
                    joinstyle='round',
                )
            for canvas_x, canvas_y in canvas_points:
                radius = 5 if is_active else 3
                self.canvas.create_oval(
                    canvas_x - radius,
                    canvas_y - radius,
                    canvas_x + radius,
                    canvas_y + radius,
                    fill=outline_color,
                    outline=BACKGROUND_COLOR,
                    width=1,
                )

    def _plot_points_to_canvas_line_points(
        self,
        plot_points: Sequence[tuple[float, float]],
    ) -> list[float]:
        line_points: list[float] = []
        for point in plot_points:
            canvas_x, canvas_y = self.world_to_canvas(point)
            line_points.extend((canvas_x, canvas_y))
        return line_points

    def _draw_plot_polyline(
        self,
        plot_points: Sequence[tuple[float, float]],
        *,
        fill: str,
        width: int,
        dash: tuple[int, int] | None = None,
    ) -> None:
        line_points = self._plot_points_to_canvas_line_points(plot_points)
        if len(line_points) < 4:
            return
        line_kwargs: dict[str, object] = {}
        if dash is not None:
            line_kwargs['dash'] = dash
        self.canvas.create_line(
            *line_points,
            fill=fill,
            width=width,
            capstyle='round',
            joinstyle='round',
            **line_kwargs,
        )

    def _draw_metro_lines(self, visible_line_names: set[str]) -> None:
        for segment in _all_metro_segments():
            if segment.line_name not in visible_line_names:
                continue
            width, dash = _metro_segment_style(segment)
            self._draw_plot_polyline(
                segment.plot_points,
                fill=LINE_COLORS[segment.line_name],
                width=width,
                dash=dash,
            )

    def _draw_railway_finish_highlights(self, visible_line_names: set[str]) -> None:
        for line_name in _railway_finish_line_names():
            if line_name not in visible_line_names:
                continue
            for start_distance, end_distance in _line_unfinished_connected_intervals(line_name):
                highlight_points = _polyline_slice_between_distances(
                    METRO_LINE_PLOT_PATHS[line_name],
                    start_distance,
                    end_distance,
                )
                self._draw_plot_polyline(
                    highlight_points,
                    fill=FINISHED_RAILWAY_HIGHLIGHT_OUTLINE,
                    width=FINISHED_RAILWAY_HIGHLIGHT_OUTLINE_WIDTH,
                )
                self._draw_plot_polyline(
                    highlight_points,
                    fill=LINE_COLORS[line_name],
                    width=FINISHED_RAILWAY_HIGHLIGHT_WIDTH,
                )

    def _draw_current_route(self) -> None:
        if self.current_route is None:
            return

        for step in self.current_route.steps:
            if not step.path_points:
                continue
            canvas_points: list[float] = []
            for point in step.path_points:
                canvas_x, canvas_y = self.world_to_canvas(point)
                canvas_points.extend((canvas_x, canvas_y))

            if len(canvas_points) < 4:
                continue

            self.canvas.create_line(
                *canvas_points,
                fill=ROUTE_HIGHLIGHT_OUTLINE,
                width=ROUTE_HIGHLIGHT_OUTLINE_WIDTH,
                capstyle='round',
                joinstyle='round',
            )
            self.canvas.create_line(
                *canvas_points,
                fill=_route_step_color(step),
                width=ROUTE_HIGHLIGHT_WIDTH,
                capstyle='round',
                joinstyle='round',
            )

    def _draw_path_nodes(self) -> None:
        label_font_size = max(10, _label_font_size(self.zoom) - 1)
        label_offset_x, label_offset_y = self._label_offset()
        for path_node in _all_path_nodes():
            canvas_x, canvas_y = self.world_to_canvas(path_node.plot_coordinates)
            self.path_node_canvas_positions[path_node.key] = (canvas_x, canvas_y)
            radius = SELECTED_PATH_NODE_RADIUS if path_node.key == self.selected_path_node_key else PATH_NODE_RADIUS
            outline_width = 2 if path_node.key == self.selected_path_node_key else 1
            if path_node.poi_kind == 'monument':
                self.canvas.create_polygon(
                    canvas_x,
                    canvas_y - radius,
                    canvas_x - radius,
                    canvas_y + radius,
                    canvas_x + radius,
                    canvas_y + radius,
                    fill=PATH_NODE_FILL,
                    outline=PATH_NODE_OUTLINE,
                    width=outline_width,
                )
            elif path_node.poi_kind == 'pillager_tower':
                self.canvas.create_rectangle(
                    canvas_x - max(3, radius // 2),
                    canvas_y - radius,
                    canvas_x + max(3, radius // 2),
                    canvas_y + radius,
                    fill=PATH_NODE_FILL,
                    outline=PATH_NODE_OUTLINE,
                    width=outline_width,
                )
            else:
                self.canvas.create_rectangle(
                    canvas_x - radius,
                    canvas_y - radius,
                    canvas_x + radius,
                    canvas_y + radius,
                    fill=PATH_NODE_FILL,
                    outline=PATH_NODE_OUTLINE,
                    width=outline_width,
                )
            if self.show_labels_var.get() and (path_node.label or path_node.poi_kind is not None):
                self.canvas.create_text(
                    canvas_x + label_offset_x,
                    canvas_y - label_offset_y,
                    anchor='sw',
                    angle=LABEL_ANGLE,
                    text=path_node.display_label,
                    fill=PATH_NODE_LABEL_COLOR,
                    font=('Helvetica', label_font_size),
                )

    def _draw_path_drag_preview(self) -> None:
        self._update_path_drag_preview()

    def _draw_extra_edges(self) -> None:
        for extra_edge in EXTRA_EDGES:
            canvas_points: list[float] = []
            for point in extra_edge.plot_points:
                canvas_x, canvas_y = self.world_to_canvas(point)
                canvas_points.extend((canvas_x, canvas_y))
            if len(canvas_points) < 4:
                continue
            line_kwargs: dict[str, object] = {}
            if extra_edge.kind == 'walk':
                line_kwargs['dash'] = (6, 4)
            if extra_edge.id == self.active_path_edge_id:
                self.canvas.create_line(
                    *canvas_points,
                    fill=ROUTE_HIGHLIGHT_OUTLINE,
                    width=PATH_EDIT_ACTIVE_OUTLINE_WIDTH,
                    capstyle='round',
                    joinstyle='round',
                    **line_kwargs,
                )
            self.canvas.create_line(
                *canvas_points,
                fill=CONNECTOR_ROUTE_COLOR if extra_edge.kind == 'connector' else WALK_ROUTE_COLOR,
                width=PATH_EDIT_ACTIVE_WIDTH if extra_edge.id == self.active_path_edge_id else 3,
                capstyle='round',
                joinstyle='round',
                **line_kwargs,
            )
            if extra_edge.id == self.active_path_edge_id and self.path_click_mode_var.get():
                for point in self._path_edit_points_for_edge(extra_edge)[1:-1]:
                    handle_x, handle_y = self.world_to_canvas((point[0], -point[1]))
                    self.canvas.create_oval(
                        handle_x - PATH_EDIT_HANDLE_RADIUS,
                        handle_y - PATH_EDIT_HANDLE_RADIUS,
                        handle_x + PATH_EDIT_HANDLE_RADIUS,
                        handle_y + PATH_EDIT_HANDLE_RADIUS,
                        fill=INFO_BOX_BACKGROUND,
                        outline=ROUTE_HIGHLIGHT_OUTLINE,
                        width=2,
                    )

    def _draw_frontier_highlights(self, visible_line_names: set[str]) -> None:
        if not self.show_frontier_highlights_var.get():
            return

        for line_name, frontier_var, target_var in _frontier_highlight_segments():
            if line_name not in visible_line_names:
                continue
            try:
                highlight_points = _line_segment_plot_points(line_name, frontier_var, target_var)
            except (KeyError, ValueError):
                continue
            canvas_points: list[float] = []
            for point in highlight_points:
                canvas_x, canvas_y = self.world_to_canvas(point)
                canvas_points.extend((canvas_x, canvas_y))
            if len(canvas_points) < 4:
                continue
            self.canvas.create_line(
                *canvas_points,
                fill=FRONTIER_HIGHLIGHT_OUTLINE,
                width=FRONTIER_SEGMENT_OUTLINE_WIDTH,
                capstyle='round',
                joinstyle='round',
            )
            self.canvas.create_line(
                *canvas_points,
                fill=LINE_COLORS[line_name],
                width=FRONTIER_SEGMENT_WIDTH,
                capstyle='round',
                joinstyle='round',
            )

    def zoom_at(self, anchor_x: float, anchor_y: float, factor: float) -> None:
        new_zoom = min(max(self.zoom * factor, self._minimum_zoom()), self._max_zoom())
        if new_zoom == self.zoom:
            return

        center_x = self.width / 2
        center_y = self.height / 2
        ratio = new_zoom / self.zoom
        self.pan_x = anchor_x - center_x - ((anchor_x - center_x - self.pan_x) * ratio)
        self.pan_y = anchor_y - center_y - ((anchor_y - center_y - self.pan_y) * ratio)
        self.zoom = new_zoom
        self._begin_viewport_interaction()
        self._scale_viewport_canvas_items(anchor_x, anchor_y, ratio)

    def _set_view_to_plot_bounds(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        *,
        min_zoom: float = DEFAULT_ZOOM,
        margin_ratio: float = 0.0,
        margin_pixels: float | None = None,
    ) -> None:
        min_x, max_x, min_y, max_y = self._plot_bounds_with_margin(
            min_x,
            max_x,
            min_y,
            max_y,
            margin_ratio=margin_ratio,
        )
        all_min_x, _all_max_x, all_min_y, _all_max_y, scale = self._plot_transform()
        target_zoom = self._target_zoom_for_plot_bounds(
            min_x,
            max_x,
            min_y,
            max_y,
            margin_ratio=0.0,
            margin_pixels=margin_pixels,
        )
        self.zoom = min(max(target_zoom, min_zoom), self._max_zoom())

        bounds_center = ((min_x + max_x) / 2, (min_y + max_y) / 2)
        base_center_x, base_center_y = self._world_to_base_canvas(bounds_center)
        canvas_center_x = self.width / 2
        canvas_center_y = self.height / 2
        self.pan_x = (canvas_center_x - base_center_x) * self.zoom
        self.pan_y = (canvas_center_y - base_center_y) * self.zoom
        self.redraw()

    def _plot_bounds_with_margin(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        *,
        margin_ratio: float,
    ) -> tuple[float, float, float, float]:
        if margin_ratio <= 0:
            return (min_x, max_x, min_y, max_y)
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        margin_x = span_x * margin_ratio
        margin_y = span_y * margin_ratio
        return (
            min_x - margin_x,
            max_x + margin_x,
            min_y - margin_y,
            max_y + margin_y,
        )

    def _target_zoom_for_plot_bounds(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        *,
        margin_ratio: float,
        margin_pixels: float | None = None,
    ) -> float:
        min_x, max_x, min_y, max_y = self._plot_bounds_with_margin(
            min_x,
            max_x,
            min_y,
            max_y,
            margin_ratio=margin_ratio,
        )
        _all_min_x, _all_max_x, _all_min_y, _all_max_y, scale = self._plot_transform()
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        fit_margin = self.padding if margin_pixels is None else max(0.0, float(margin_pixels))
        available_width = max(self.width - (fit_margin * 2), 1)
        available_height = max(self.height - (fit_margin * 2), 1)
        return min(
            available_width / (span_x * scale),
            available_height / (span_y * scale),
        )

    def show_whole_map_view(self) -> None:
        bounds = _plot_bounds(_all_plot_points())
        if bounds is None:
            self.zoom = DEFAULT_ZOOM
            self.pan_x = 0.0
            self.pan_y = 0.0
            self.redraw()
            return
        self._set_view_to_plot_bounds(*bounds)

    def show_connected_area_view(self) -> None:
        area_loops = _connected_route_area_world_loops()
        connected_points = [
            point
            for area_loop in area_loops
            for point in area_loop
        ]
        if not connected_points:
            connected_points = [
                point
                for route_path in _connected_route_plot_paths()
                for point in route_path
            ]
        if not connected_points:
            connected_points = [stop.plot_coordinates for stop in METRO_STOPS if stop.is_connected]
        bounds = _plot_bounds(connected_points)
        if bounds is None:
            self.show_whole_map_view()
            return
        self._set_view_to_plot_bounds(*bounds)

    def show_target_map_bounds_view(self) -> None:
        bounds = self._target_map_plot_bounds()
        if bounds is None:
            self.show_connected_area_view()
            return
        self._set_view_to_plot_bounds(
            *bounds,
            min_zoom=self._minimum_zoom(),
            margin_pixels=TARGET_MAP_VIEW_MARGIN_PIXELS,
        )

    def show_railway_finish_unfinished_view(self) -> None:
        bounds = _plot_bounds(_railway_finish_unfinished_plot_points())
        if bounds is None:
            self.show_connected_area_view()
            return
        self._set_view_to_plot_bounds(*bounds)

    def show_blackport_view(self) -> None:
        blackport = _blackport_stop()
        center_x, center_y = blackport.plot_coordinates
        self._set_view_to_plot_bounds(
            center_x - BLACKPORT_VIEW_RADIUS,
            center_x + BLACKPORT_VIEW_RADIUS,
            center_y - BLACKPORT_VIEW_RADIUS,
            center_y + BLACKPORT_VIEW_RADIUS,
        )

    def reset_view(self) -> None:
        self.show_target_map_bounds_view()

    def _on_configure(self, event: object) -> None:
        width = int(getattr(event, 'width', self.width))
        height = int(getattr(event, 'height', self.height))
        if width < 2 or height < 2:
            return
        self.width = width
        self.height = height
        self.redraw()

    def _on_sidebar_frame_configure(self, _event: object) -> None:
        self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox('all'))

    def _on_sidebar_canvas_configure(self, event: object) -> None:
        canvas_width = int(getattr(event, 'width', SIDEBAR_WIDTH))
        self.sidebar_canvas.itemconfigure(self.sidebar_window_id, width=canvas_width)

    def _widget_is_in_sidebar(self, widget: object) -> bool:
        current_widget = widget
        while isinstance(current_widget, tk.Misc):
            if current_widget is self.sidebar_canvas or current_widget is self.sidebar:
                return True
            parent_name = current_widget.winfo_parent()
            if not parent_name:
                break
            current_widget = current_widget.nametowidget(parent_name)
        return False

    def _widget_is_in_info_popup(self, widget: object) -> bool:
        if self.info_popup_frame is None:
            return False

        current_widget = widget
        while isinstance(current_widget, tk.Misc):
            if current_widget is self.info_popup_frame:
                return True
            parent_name = current_widget.winfo_parent()
            if not parent_name:
                break
            current_widget = current_widget.nametowidget(parent_name)
        return False

    def _scroll_sidebar_units(self, units: int) -> None:
        if units == 0:
            return
        self.sidebar_scroll_remaining += units * SIDEBAR_SCROLL_PIXELS
        if self.sidebar_scroll_after_id is None:
            self._run_sidebar_scroll_frame()

    def _run_sidebar_scroll_frame(self) -> None:
        self.sidebar_scroll_after_id = None
        if abs(self.sidebar_scroll_remaining) < 0.5:
            self.sidebar_scroll_remaining = 0.0
            return
        step = self.sidebar_scroll_remaining / SIDEBAR_SCROLL_FRAMES
        if abs(step) < 1:
            step = 1.0 if self.sidebar_scroll_remaining > 0 else -1.0
        self.sidebar_scroll_remaining -= step
        self._scroll_sidebar_pixels(step)
        if abs(self.sidebar_scroll_remaining) >= 0.5:
            self.sidebar_scroll_after_id = self.root.after(
                SIDEBAR_SCROLL_FRAME_DELAY_MS,
                self._run_sidebar_scroll_frame,
            )

    def _scroll_sidebar_pixels(self, pixels: float) -> None:
        bbox = self.sidebar_canvas.bbox('all')
        if bbox is None:
            return
        content_height = max(1.0, float(bbox[3] - bbox[1]))
        visible_height = max(1.0, float(self.sidebar_canvas.winfo_height()))
        if content_height <= visible_height:
            return
        max_top = max(0.0, 1.0 - (visible_height / content_height))
        current_top, _current_bottom = self.sidebar_canvas.yview()
        next_top = min(max_top, max(0.0, current_top + (pixels / content_height)))
        self.sidebar_canvas.yview_moveto(next_top)

    def _on_global_left_click_release(self, event: object) -> None:
        widget = getattr(event, 'widget', None)
        if isinstance(widget, (tk.Entry, tk.Text, tk.Listbox, tk.Menubutton, tk.Menu)):
            return
        if self._widget_is_in_sidebar(widget):
            return
        if self._widget_is_in_info_popup(widget):
            return
        self.root.after_idle(self.canvas.focus_set)

    def _on_global_mousewheel(self, event: object) -> None:
        widget = getattr(event, 'widget', None)
        if not self._widget_is_in_sidebar(widget):
            return
        delta = int(getattr(event, 'delta', 0))
        if delta == 0:
            return
        self._scroll_sidebar_units(-1 if delta > 0 else 1)

    def _on_global_mousewheel_linux_up(self, event: object) -> None:
        widget = getattr(event, 'widget', None)
        if not self._widget_is_in_sidebar(widget):
            return
        self._scroll_sidebar_units(-1)

    def _on_global_mousewheel_linux_down(self, event: object) -> None:
        widget = getattr(event, 'widget', None)
        if not self._widget_is_in_sidebar(widget):
            return
        self._scroll_sidebar_units(1)

    def _on_drag_start(self, event: object) -> None:
        if self._widget_is_in_info_popup(getattr(event, 'widget', None)):
            return
        self._hide_suggestion_popup()
        point = (int(getattr(event, 'x', 0)), int(getattr(event, 'y', 0)))
        self.drag_start = point
        self.drag_origin = point
        self.is_dragging = False
        self._clear_path_drag()
        if self.path_click_mode_var.get():
            start_endpoint = self._path_endpoint_hit_test(point[0], point[1])
            if start_endpoint is not None:
                self.path_drag_start_endpoint_key = start_endpoint.key
                self.path_drag_current_canvas_point = point

    def _on_drag(self, event: object) -> None:
        if self._widget_is_in_info_popup(getattr(event, 'widget', None)):
            return
        if self.drag_start is None:
            return
        current = (int(getattr(event, 'x', 0)), int(getattr(event, 'y', 0)))
        if self.path_click_mode_var.get() and self.path_drag_start_endpoint_key is not None:
            self.path_drag_current_canvas_point = current
            if not self.is_dragging and self.drag_origin is not None:
                if (
                    abs(current[0] - self.drag_origin[0]) < DRAG_THRESHOLD
                    and abs(current[1] - self.drag_origin[1]) < DRAG_THRESHOLD
                ):
                    return
                self.is_dragging = True
                self.hover_canvas_point = None
                self.cursor_readout_coordinates = None
                self.show_cursor_guides = False
            self._update_path_drag_preview()
            return

        if not self.is_dragging and self.drag_origin is not None:
            if (
                abs(current[0] - self.drag_origin[0]) < DRAG_THRESHOLD
                and abs(current[1] - self.drag_origin[1]) < DRAG_THRESHOLD
            ):
                return
            self.is_dragging = True
            self.hover_canvas_point = None
            self.cursor_readout_coordinates = None
            self.show_cursor_guides = False
        self.pan_x += current[0] - self.drag_start[0]
        self.pan_y += current[1] - self.drag_start[1]
        delta_x = current[0] - self.drag_start[0]
        delta_y = current[1] - self.drag_start[1]
        self.drag_start = current
        self._begin_viewport_interaction()
        self._move_viewport_canvas_items(delta_x, delta_y)

    def _on_drag_end(self, event: object) -> None:
        if self._widget_is_in_info_popup(getattr(event, 'widget', None)):
            self._finish_viewport_interaction()
            self.drag_start = None
            self.drag_origin = None
            self.is_dragging = False
            self._clear_path_drag()
            return
        release_x = int(getattr(event, 'x', 0))
        release_y = int(getattr(event, 'y', 0))
        self._cancel_scheduled_redraw()
        self._finish_viewport_interaction()
        if self.path_click_mode_var.get() and self.path_drag_start_endpoint_key is not None:
            was_path_dragging = self.is_dragging
            if was_path_dragging:
                self._finish_path_drag(release_x, release_y)
                self.drag_start = None
                self.drag_origin = None
                self.is_dragging = False
                self._clear_path_drag()
                return
            self._clear_path_drag()

        if not self.is_dragging:
            if self.city_limits_edit_stop_var is not None:
                selected_path_node = self._path_node_hit_test(release_x, release_y)
                if selected_path_node is not None:
                    self._toggle_city_limit_node(selected_path_node)
                else:
                    self.path_click_status_var.set('Click a path node to add or remove it from the active city limits.')
                    self.redraw()
                self.drag_start = None
                self.drag_origin = None
                self.is_dragging = False
                return
            if self._handle_path_click_edit(release_x, release_y):
                self.drag_start = None
                self.drag_origin = None
                self.is_dragging = False
                return
            selected_stop = self._station_hit_test(
                release_x,
                release_y,
            )
            if selected_stop is not None:
                self.selected_stop_var = selected_stop.var
                self.selected_path_node_key = None
                self._clear_metro_segment_selection()
                self.hover_canvas_point = None
                self.cursor_readout_coordinates = selected_stop.coordinates
                self.show_cursor_guides = False
            else:
                selected_path_node = self._path_node_hit_test(
                    release_x,
                    release_y,
                )
                self.selected_stop_var = None
                if selected_path_node is not None:
                    self.selected_path_node_key = selected_path_node.key
                    self._clear_metro_segment_selection()
                    self.hover_canvas_point = None
                    self.cursor_readout_coordinates = selected_path_node.coordinates
                    self.show_cursor_guides = False
                else:
                    selected_segment = self._metro_segment_hit_test(
                        release_x,
                        release_y,
                    )
                    self.selected_path_node_key = None
                    if selected_segment is not None:
                        self._select_metro_segment_from_event(selected_segment, event)
                        self.hover_canvas_point = None
                        self.cursor_readout_coordinates = self.canvas_to_world((float(release_x), float(release_y)))
                        self.show_cursor_guides = False
                    else:
                        self._clear_metro_segment_selection()
                        if (
                            self.show_cursor_guides
                            and self.hover_canvas_point is not None
                            and abs(self.hover_canvas_point[0] - float(release_x)) <= CURSOR_CROSSHAIR_RADIUS
                            and abs(self.hover_canvas_point[1] - float(release_y)) <= CURSOR_CROSSHAIR_RADIUS
                        ):
                            self.hover_canvas_point = None
                            self.cursor_readout_coordinates = None
                            self.show_cursor_guides = False
                        else:
                            self.hover_canvas_point = (float(release_x), float(release_y))
                            self.cursor_readout_coordinates = self.canvas_to_world((float(release_x), float(release_y)))
                            self.show_cursor_guides = True
            self.redraw()
        else:
            self.hover_canvas_point = None
            self.cursor_readout_coordinates = None
            self.show_cursor_guides = False
            self.redraw()
        self.drag_start = None
        self.drag_origin = None
        self.is_dragging = False

    def _on_mousewheel(self, event: object) -> None:
        delta = float(getattr(event, 'delta', 0))
        if delta == 0:
            return
        factor = ZOOM_STEP ** (delta / 120.0)
        anchor_x = float(getattr(event, 'x', self.width / 2))
        anchor_y = float(getattr(event, 'y', self.height / 2))
        self._hide_suggestion_popup()
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = None
        self.show_cursor_guides = False
        self.zoom_at(anchor_x, anchor_y, factor)

    def _on_zoom_in(self, event: object) -> None:
        anchor_x = float(getattr(event, 'x', self.width / 2))
        anchor_y = float(getattr(event, 'y', self.height / 2))
        self._hide_suggestion_popup()
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = None
        self.show_cursor_guides = False
        self.zoom_at(anchor_x, anchor_y, ZOOM_STEP)

    def _on_zoom_out(self, event: object) -> None:
        anchor_x = float(getattr(event, 'x', self.width / 2))
        anchor_y = float(getattr(event, 'y', self.height / 2))
        self._hide_suggestion_popup()
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = None
        self.show_cursor_guides = False
        self.zoom_at(anchor_x, anchor_y, 1 / ZOOM_STEP)

    def _on_reset_view(self, event: object) -> None:
        if not self._hotkeys_enabled():
            return
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = None
        self.show_cursor_guides = False
        self.reset_view()

    def _on_focus_connected_area_view(self, event: object) -> None:
        if not self._hotkeys_enabled():
            return
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = None
        self.show_cursor_guides = False
        self.show_connected_area_view()

    def _on_focus_blackport_view(self, event: object) -> None:
        if not self._hotkeys_enabled():
            return
        self.hover_canvas_point = None
        self.cursor_readout_coordinates = None
        self.show_cursor_guides = False
        self.show_blackport_view()

def plot_stops(
    width: int = PLOT_WIDTH,
    height: int = PLOT_HEIGHT,
    padding: int = PLOT_PADDING,
) -> None:
    MetroMapViewer(width=width, height=height, padding=padding).run()


def main() -> None:
    plot_stops()


METRO_STOPS: tuple[MetroStop, ...] = ()
STOPS_BY_VAR: dict[str, MetroStop] = {}
STOPS_BY_LBL: dict[str, MetroStop] = {}
LINE_COLORS: dict[str, str] = {}
WOOL_COLORS: dict[str, str] = {}
LINE_STOP_VARS: dict[str, tuple[str, ...]] = {}
STOP_LINE_NAMES: dict[str, tuple[str, ...]] = {}
METRO_LINES: dict[str, tuple[MetroStop, ...]] = {}
LINE_PATH_SPECS: dict[str, tuple[LinePathPointSpec, ...]] = {}
METRO_LINE_PATHS: dict[str, tuple[tuple[int, int], ...]] = {}
METRO_LINE_PLOT_PATHS: dict[str, tuple[tuple[int, int], ...]] = {}
RAILWAY_FINISH_PROGRESS: dict[str, PathPointRecord] = {}
PATH_NODES: tuple[PathNode, ...] = ()
PATH_NODES_BY_KEY: dict[str, PathNode] = {}
PATH_NODES_BY_ID: dict[str, PathNode] = {}
_ALL_PATH_NODES_CACHE_KEY: tuple[int, int] | None = None
_ALL_PATH_NODES_CACHE: tuple[PathNode, ...] = ()
_ALL_PATH_NODES_BY_KEY_CACHE: dict[str, PathNode] = {}
EXTRA_EDGES: tuple[ExtraEdgeDefinition, ...] = ()
ALIGNMENT_REMINDERS: tuple[AlignmentReminder, ...] = ()


def _line_letters(stop: MetroStop) -> tuple[str, ...]:
    return tuple(char for char in stop.var.removeprefix('P_') if char.isalpha())


def _validate_line_sequences() -> None:
    expected_members: dict[str, set[str]] = {line_name: set() for line_name in LINE_STOP_VARS}

    for stop in METRO_STOPS:
        for line_name in _line_letters(stop):
            expected_members.setdefault(line_name, set()).add(stop.var)

    if set(expected_members) != set(LINE_STOP_VARS):
        raise ValueError('LINE_STOP_VARS does not match the lines encoded in the stop variables.')

    for line_name, stop_vars in LINE_STOP_VARS.items():
        if len(stop_vars) != len(set(stop_vars)):
            raise ValueError(f'Line {line_name} has duplicate stop entries.')
        if set(stop_vars) != expected_members[line_name]:
            raise ValueError(
                f'Line {line_name} sequence does not match the stop variables. '
                f'Expected {sorted(expected_members[line_name])}, got {sorted(stop_vars)}.'
            )


def _validate_line_path_specs() -> None:
    if set(LINE_PATH_SPECS) != set(LINE_STOP_VARS):
        raise ValueError('LINE_PATH_SPECS does not match the defined metro lines.')

    for line_name, point_specs in LINE_PATH_SPECS.items():
        mentioned_vars = {spec.x_var for spec in point_specs} | {spec.y_var for spec in point_specs}
        missing_stops = set(LINE_STOP_VARS[line_name]) - mentioned_vars
        unknown_vars = mentioned_vars - set(STOPS_BY_VAR)

        if unknown_vars:
            raise ValueError(f'Line {line_name} path references unknown stops: {sorted(unknown_vars)}.')
        if missing_stops:
            raise ValueError(f'Line {line_name} path is missing stops: {sorted(missing_stops)}.')
        if len(point_specs) < 2:
            raise ValueError(f'Line {line_name} path needs at least two points.')


def _validate_line_colors() -> None:
    if set(LINE_COLORS) != set(LINE_STOP_VARS):
        raise ValueError('LINE_COLORS does not match the defined metro lines.')


def _validate_path_nodes() -> None:
    seen_ids: set[str] = set()
    seen_coordinates: set[tuple[int, int]] = set()
    stop_coordinates = {stop.coordinates for stop in METRO_STOPS}

    for path_node in PATH_NODES:
        if path_node.id in seen_ids:
            raise ValueError(f'Duplicate path node id: {path_node.id}')
        if path_node.coordinates in seen_coordinates:
            raise ValueError(f'Duplicate path node coordinates: {path_node.coordinates}')
        if path_node.coordinates in stop_coordinates:
            raise ValueError(f'Path node {path_node.id} overlaps a station coordinate.')
        seen_ids.add(path_node.id)
        seen_coordinates.add(path_node.coordinates)


def _validate_extra_edges() -> None:
    seen_ids: set[str] = set()
    for extra_edge in EXTRA_EDGES:
        if extra_edge.id in seen_ids:
            raise ValueError(f'Duplicate extra edge id: {extra_edge.id}')
        seen_ids.add(extra_edge.id)
        if extra_edge.from_endpoint.kind == 'stop' and extra_edge.from_endpoint.key not in STOPS_BY_VAR:
            raise ValueError(f'Extra edge {extra_edge.id} references unknown start stop.')
        if extra_edge.to_endpoint.kind == 'stop' and extra_edge.to_endpoint.key not in STOPS_BY_VAR:
            raise ValueError(f'Extra edge {extra_edge.id} references unknown end stop.')
        if extra_edge.from_endpoint.key == extra_edge.to_endpoint.key:
            raise ValueError(f'Extra edge {extra_edge.id} needs two different endpoints.')
        if extra_edge.path_points:
            if extra_edge.path_points[0] != extra_edge.from_endpoint.coordinates:
                raise ValueError(f'Extra edge {extra_edge.id} path must start at its first endpoint.')
            if extra_edge.path_points[-1] != extra_edge.to_endpoint.coordinates:
                raise ValueError(f'Extra edge {extra_edge.id} path must end at its second endpoint.')


def _validate_stop_line_names() -> None:
    for stop in METRO_STOPS:
        if stop.var not in STOP_LINE_NAMES:
            raise ValueError(f'Stop {stop.var} is missing line membership metadata.')


def _validate_stop_records(stops: tuple[MetroStop, ...]) -> None:
    if len({stop.var for stop in stops}) != len(stops):
        raise ValueError('Stop variables must be unique.')
    unique_required_labels = [
        stop.lbl
        for stop in stops
        if stop.lbl != UNASSOCIATED_STATION_LABEL
    ]
    if len(set(unique_required_labels)) != len(unique_required_labels):
        raise ValueError('Stop labels must be unique.')
    for stop in stops:
        if not stop.lbl.strip():
            raise ValueError(f'Stop {stop.var} must have a non-empty label.')


def _history_snapshot_paths() -> list[Path]:
    if not METRO_NETWORK_HISTORY_DIR.exists():
        return []
    return sorted(METRO_NETWORK_HISTORY_DIR.glob('*.json'))


def _record_history_snapshot(snapshot_text: str) -> None:
    if not snapshot_text:
        return

    METRO_NETWORK_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    latest_snapshot_paths = _history_snapshot_paths()
    if latest_snapshot_paths:
        latest_snapshot_text = latest_snapshot_paths[-1].read_text(encoding='utf-8')
        if latest_snapshot_text == snapshot_text:
            return

    snapshot_name = f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    snapshot_path = METRO_NETWORK_HISTORY_DIR / snapshot_name
    snapshot_path.write_text(snapshot_text, encoding='utf-8')

    history_paths = _history_snapshot_paths()
    if len(history_paths) <= MAX_HISTORY_SNAPSHOTS:
        return
    for stale_path in history_paths[:-MAX_HISTORY_SNAPSHOTS]:
        stale_path.unlink(missing_ok=True)


def _write_network_payload(payload: MetroNetworkPayload) -> None:
    serialized_payload = json.dumps(payload, indent=2) + '\n'
    current_payload_text = ''
    if METRO_NETWORK_PATH.exists():
        current_payload_text = METRO_NETWORK_PATH.read_text(encoding='utf-8')

    if current_payload_text and current_payload_text != serialized_payload:
        _record_history_snapshot(current_payload_text)
        METRO_NETWORK_BACKUP_PATH.write_text(current_payload_text, encoding='utf-8')

    METRO_NETWORK_PATH.write_text(serialized_payload, encoding='utf-8')


def _restore_last_network_snapshot() -> None:
    current_payload_text = METRO_NETWORK_PATH.read_text(encoding='utf-8')
    history_paths = _history_snapshot_paths()
    if history_paths:
        restore_path = history_paths[-1]
        restore_payload_text = restore_path.read_text(encoding='utf-8')
        restore_path.unlink(missing_ok=True)
        METRO_NETWORK_BACKUP_PATH.write_text(current_payload_text, encoding='utf-8')
        METRO_NETWORK_PATH.write_text(restore_payload_text, encoding='utf-8')
        _reload_network_data()
        return

    if not METRO_NETWORK_BACKUP_PATH.exists():
        raise ValueError('No previous saved network state is available yet.')

    backup_payload_text = METRO_NETWORK_BACKUP_PATH.read_text(encoding='utf-8')
    METRO_NETWORK_PATH.write_text(backup_payload_text, encoding='utf-8')
    METRO_NETWORK_BACKUP_PATH.write_text(current_payload_text, encoding='utf-8')
    _reload_network_data()


def _resolve_stop_var_in_payload(payload: MetroNetworkPayload, identifier: str) -> str | None:
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return None

    stop_vars = {
        str(stop_record['var']): str(stop_record['var'])
        for stop_record in payload['stops']
    }
    if normalized_identifier in stop_vars:
        return stop_vars[normalized_identifier]

    labels = {
        str(stop_record['lbl']): str(stop_record['var'])
        for stop_record in payload['stops']
    }
    return labels.get(normalized_identifier)


def _resolve_path_node_in_payload(payload: MetroNetworkPayload, identifier: str) -> PathNodeRecord | None:
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return None

    raw_path_nodes = payload.get('path_nodes', [])
    if not isinstance(raw_path_nodes, list):
        return None

    for raw_path_node in raw_path_nodes:
        if not isinstance(raw_path_node, dict):
            continue
        if str(raw_path_node.get('id', '')).strip() == normalized_identifier:
            return cast(PathNodeRecord, raw_path_node)
        if str(raw_path_node.get('label', '')).strip() == normalized_identifier:
            return cast(PathNodeRecord, raw_path_node)
    return None


def _normalize_path_endpoint_record(
    payload: MetroNetworkPayload,
    raw_endpoint: object,
    *,
    fallback_identifier: str | None = None,
) -> PathEndpointRecord | None:
    if isinstance(raw_endpoint, dict):
        raw_kind = str(raw_endpoint.get('kind', '')).strip().lower()
        if raw_kind == 'stop':
            stop_var = _resolve_stop_var_in_payload(payload, str(raw_endpoint.get('stop_var', '')))
            if stop_var is not None:
                return {'kind': 'stop', 'stop_var': stop_var}
            return None
        if raw_kind in {'coord', 'coordinate'}:
            endpoint_x = _coerce_int(raw_endpoint.get('x'))
            endpoint_y = _coerce_int(raw_endpoint.get('y'))
            if endpoint_x is None or endpoint_y is None:
                return None
            return {
                'kind': 'coord',
                'x': endpoint_x,
                'y': endpoint_y,
            }

    if fallback_identifier is None:
        return None
    return _path_endpoint_record_from_identifier(payload, fallback_identifier)


def _payload_endpoint_coordinates(
    payload: MetroNetworkPayload,
    endpoint_record: PathEndpointRecord,
) -> tuple[int, int]:
    if endpoint_record['kind'] == 'stop':
        stop_lookup = {
            str(stop_record['var']): stop_record
            for stop_record in payload['stops']
        }
        stop_record = stop_lookup[endpoint_record['stop_var']]
        station_entry_x = _coerce_int(stop_record.get('station_entry_x'))
        station_entry_y = _coerce_int(stop_record.get('station_entry_y'))
        if station_entry_x is not None and station_entry_y is not None:
            return (station_entry_x, station_entry_y)
        return (int(stop_record['x']), int(stop_record['y']))

    return (int(endpoint_record['x']), int(endpoint_record['y']))


def _normalize_path_nodes(payload: MetroNetworkPayload) -> bool:
    payload_changed = False
    raw_path_nodes = payload.get('path_nodes')
    if not isinstance(raw_path_nodes, list):
        payload['path_nodes'] = []
        return True

    stop_coordinates = {
        (int(stop_record['x']), int(stop_record['y']))
        for stop_record in payload['stops']
    }
    normalized_nodes: list[PathNodeRecord] = []
    seen_ids: set[str] = set()
    seen_coordinates: set[tuple[int, int]] = set()

    for index, raw_node in enumerate(raw_path_nodes, start=1):
        if not isinstance(raw_node, dict):
            payload_changed = True
            continue

        node_x = _coerce_int(raw_node.get('x'))
        node_y = _coerce_int(raw_node.get('y'))
        if node_x is None or node_y is None:
            payload_changed = True
            continue

        coordinates = (node_x, node_y)
        if coordinates in stop_coordinates or coordinates in seen_coordinates:
            payload_changed = True
            continue

        node_id = str(raw_node.get('id', '')).strip() or f'node_{index}'
        if node_id in seen_ids:
            node_id = f'{node_id}_{index}'
            payload_changed = True

        normalized_node: PathNodeRecord = {
            'id': node_id,
            'x': node_x,
            'y': node_y,
        }
        label = str(raw_node.get('label', '')).strip()
        if label:
            normalized_node['label'] = label
        poi_kind = str(raw_node.get('poi_kind', '')).strip().lower()
        if poi_kind in {'monument', 'pillager_tower'}:
            normalized_node['poi_kind'] = poi_kind
            category = str(raw_node.get('category', '')).strip()
            if category:
                normalized_node['category'] = category

        if raw_node != normalized_node:
            payload_changed = True
        normalized_nodes.append(normalized_node)
        seen_ids.add(node_id)
        seen_coordinates.add(coordinates)

    if raw_path_nodes != normalized_nodes:
        payload['path_nodes'] = normalized_nodes
        payload_changed = True

    return payload_changed


def _normalize_alignment_reminders(payload: MetroNetworkPayload) -> bool:
    payload_changed = False
    raw_alignment_reminders = payload.get('alignment_reminders')
    if not isinstance(raw_alignment_reminders, list):
        payload['alignment_reminders'] = []
        return True

    stop_lookup = {
        str(stop_record['var']): stop_record
        for stop_record in payload['stops']
    }
    normalized_reminders: list[AlignmentReminderRecord] = []
    seen_pairs: set[tuple[str, str, AlignmentAxis]] = set()

    for raw_reminder in raw_alignment_reminders:
        if not isinstance(raw_reminder, dict):
            payload_changed = True
            continue

        first_var = _resolve_stop_var_in_payload(payload, str(raw_reminder.get('first_var', '')))
        second_var = _resolve_stop_var_in_payload(payload, str(raw_reminder.get('second_var', '')))
        if first_var is None or second_var is None or first_var == second_var:
            payload_changed = True
            continue

        first_record = stop_lookup[first_var]
        second_record = stop_lookup[second_var]
        raw_axis = str(raw_reminder.get('axis', 'auto')).strip().lower()
        if raw_axis in ('x', 'y'):
            axis = cast(AlignmentAxis, raw_axis)
        else:
            axis = _infer_alignment_axis_from_coordinates(
                int(first_record['x']),
                int(first_record['y']),
                int(second_record['x']),
                int(second_record['y']),
            )
            payload_changed = True

        if axis == 'x':
            is_aligned = int(first_record['x']) == int(second_record['x'])
        else:
            is_aligned = int(first_record['y']) == int(second_record['y'])
        if is_aligned:
            payload_changed = True
            continue

        ordered_first_var, ordered_second_var = sorted((first_var, second_var))
        pair_key = (ordered_first_var, ordered_second_var, axis)
        if pair_key in seen_pairs:
            payload_changed = True
            continue
        seen_pairs.add(pair_key)

        normalized_reminder: AlignmentReminderRecord = {
            'first_var': ordered_first_var,
            'second_var': ordered_second_var,
            'axis': axis,
        }
        normalized_reminders.append(normalized_reminder)
        if raw_reminder != normalized_reminder:
            payload_changed = True

    if raw_alignment_reminders != normalized_reminders:
        payload['alignment_reminders'] = normalized_reminders
        payload_changed = True

    return payload_changed


def _normalize_extra_edges(payload: MetroNetworkPayload) -> bool:
    payload_changed = False
    raw_extra_edges = payload.get('extra_edges')
    if not isinstance(raw_extra_edges, list):
        payload['extra_edges'] = []
        return True

    normalized_edges: list[ExtraEdgeRecord] = []
    seen_ids: set[str] = set()

    for index, raw_edge in enumerate(raw_extra_edges, start=1):
        if not isinstance(raw_edge, dict):
            payload_changed = True
            continue

        edge_id = str(raw_edge.get('id', '')).strip() or f'edge_{index}'
        if edge_id in seen_ids:
            edge_id = f'{edge_id}_{index}'
            payload_changed = True
        seen_ids.add(edge_id)

        kind_value = str(raw_edge.get('kind', 'connector')).strip().lower()
        if kind_value not in {'connector', 'walk'}:
            kind_value = 'connector'
            payload_changed = True

        from_endpoint = _normalize_path_endpoint_record(
            payload,
            raw_edge.get('from_endpoint'),
            fallback_identifier=str(raw_edge.get('from_var', '')),
        )
        to_endpoint = _normalize_path_endpoint_record(
            payload,
            raw_edge.get('to_endpoint'),
            fallback_identifier=str(raw_edge.get('to_var', '')),
        )
        if from_endpoint is None or to_endpoint is None:
            payload_changed = True
            continue
        if from_endpoint == to_endpoint:
            payload_changed = True
            continue

        bidirectional = bool(raw_edge.get('bidirectional', True))
        normalized_path_points: list[PathPointRecord] = []
        raw_path_points = raw_edge.get('path_points', [])
        if not isinstance(raw_path_points, list):
            raw_path_points = []
            payload_changed = True

        if raw_path_points:
            for raw_point in raw_path_points:
                if not isinstance(raw_point, dict):
                    payload_changed = True
                    continue
                try:
                    normalized_path_points.append(
                        {
                            'x': int(raw_point.get('x')),
                            'y': int(raw_point.get('y')),
                        }
                    )
                except (TypeError, ValueError):
                    payload_changed = True
        else:
            raw_path_specs = raw_edge.get('path_specs', [])
            if not isinstance(raw_path_specs, list):
                raw_path_specs = []
                payload_changed = True
            for raw_spec in raw_path_specs:
                if not isinstance(raw_spec, dict):
                    payload_changed = True
                    continue
                x_var = _resolve_stop_var_in_payload(payload, str(raw_spec.get('x_var', '')))
                y_var = _resolve_stop_var_in_payload(payload, str(raw_spec.get('y_var', '')))
                if x_var is None or y_var is None:
                    payload_changed = True
                    continue
                try:
                    point_x = int(next(
                        stop_record['x']
                        for stop_record in payload['stops']
                        if str(stop_record['var']) == x_var
                    )) + int(raw_spec.get('dx', 0))
                    point_y = int(next(
                        stop_record['y']
                        for stop_record in payload['stops']
                        if str(stop_record['var']) == y_var
                    )) - int(raw_spec.get('dy', 0))
                except (StopIteration, TypeError, ValueError):
                    payload_changed = True
                    continue
                normalized_path_points.append({'x': point_x, 'y': point_y})

        if normalized_path_points:
            start_coordinates = _payload_endpoint_coordinates(payload, from_endpoint)
            end_coordinates = _payload_endpoint_coordinates(payload, to_endpoint)
            if (normalized_path_points[0]['x'], normalized_path_points[0]['y']) != start_coordinates:
                normalized_path_points.insert(
                    0,
                    {'x': start_coordinates[0], 'y': start_coordinates[1]},
                )
                payload_changed = True
            if (normalized_path_points[-1]['x'], normalized_path_points[-1]['y']) != end_coordinates:
                normalized_path_points.append(
                    {'x': end_coordinates[0], 'y': end_coordinates[1]},
                )
                payload_changed = True
            if len(normalized_path_points) == 2 and (
                (normalized_path_points[0]['x'], normalized_path_points[0]['y']) == start_coordinates
                and (normalized_path_points[1]['x'], normalized_path_points[1]['y']) == end_coordinates
            ):
                normalized_path_points = []
                payload_changed = True

        normalized_edge: ExtraEdgeRecord = {
            'id': edge_id,
            'kind': kind_value,
            'from_endpoint': from_endpoint,
            'to_endpoint': to_endpoint,
            'bidirectional': bidirectional,
            'path_points': normalized_path_points,
        }

        label = str(raw_edge.get('label', '')).strip()
        if label:
            normalized_edge['label'] = label

        raw_distance = raw_edge.get('distance')
        if raw_distance not in (None, ''):
            normalized_edge['distance'] = int(raw_distance)

        if raw_edge != normalized_edge:
            payload_changed = True
        normalized_edges.append(normalized_edge)

    if raw_extra_edges != normalized_edges:
        payload['extra_edges'] = normalized_edges
        payload_changed = True

    return payload_changed


def _path_node_keys_in_payload(payload: MetroNetworkPayload) -> set[str]:
    node_keys: set[str] = set()
    for raw_node in payload.get('path_nodes', []):
        if not isinstance(raw_node, dict):
            continue
        node_x = _coerce_int(raw_node.get('x'))
        node_y = _coerce_int(raw_node.get('y'))
        if node_x is None or node_y is None:
            continue
        node_keys.add(_coordinate_endpoint_key(node_x, node_y))

    for raw_edge in payload.get('extra_edges', []):
        if not isinstance(raw_edge, dict):
            continue
        for field_name in ('from_endpoint', 'to_endpoint'):
            raw_endpoint = raw_edge.get(field_name)
            if not isinstance(raw_endpoint, dict):
                continue
            endpoint = _normalize_path_endpoint_record(payload, raw_endpoint)
            if endpoint is None or endpoint['kind'] != 'coord':
                continue
            node_keys.add(_coordinate_endpoint_key(int(endpoint['x']), int(endpoint['y'])))
    return node_keys


def _normalize_city_limits(payload: MetroNetworkPayload) -> bool:
    payload_changed = False
    valid_node_keys = _path_node_keys_in_payload(payload)
    for stop_record in payload['stops']:
        raw_node_keys = stop_record.get('city_limit_node_keys')
        if raw_node_keys is None:
            continue
        if not isinstance(raw_node_keys, list):
            stop_record.pop('city_limit_node_keys', None)
            payload_changed = True
            continue

        normalized_node_keys: list[str] = []
        seen_node_keys: set[str] = set()
        for raw_node_key in raw_node_keys:
            node_key = str(raw_node_key).strip()
            if node_key not in valid_node_keys:
                coordinates = _parse_coordinate_text(node_key)
                if coordinates is not None:
                    node_key = _coordinate_endpoint_key(coordinates[0], coordinates[1])
            if node_key not in valid_node_keys or node_key in seen_node_keys:
                payload_changed = True
                continue
            normalized_node_keys.append(node_key)
            seen_node_keys.add(node_key)

        if normalized_node_keys:
            if raw_node_keys != normalized_node_keys:
                stop_record['city_limit_node_keys'] = normalized_node_keys
                payload_changed = True
        else:
            stop_record.pop('city_limit_node_keys', None)
            payload_changed = True

    return payload_changed


def _normalize_railway_finish_progress(payload: MetroNetworkPayload) -> bool:
    payload_changed = False
    had_progress_key = 'railway_finish_progress' in payload
    raw_progress = payload.get('railway_finish_progress')
    if not isinstance(raw_progress, dict):
        payload['railway_finish_progress'] = {}
        return had_progress_key

    normalized_progress: dict[str, PathPointRecord] = {}
    valid_line_names = {str(line_name) for line_name in payload['line_stop_vars']}
    for raw_line_name, raw_point in raw_progress.items():
        line_name = str(raw_line_name)
        if line_name not in valid_line_names or not isinstance(raw_point, dict):
            payload_changed = True
            continue

        point_x = _coerce_int(raw_point.get('x'))
        point_y = _coerce_int(raw_point.get('y'))
        if point_x is None or point_y is None:
            payload_changed = True
            continue
        normalized_progress[line_name] = {'x': point_x, 'y': point_y}

    if raw_progress != normalized_progress:
        payload['railway_finish_progress'] = normalized_progress
        payload_changed = True

    return payload_changed


def _payload_line_finish_origin_options(
    payload: MetroNetworkPayload,
    line_name: str,
) -> tuple[str, ...]:
    connected_stop_vars = tuple(
        str(stop_record['var'])
        for stop_record in payload['stops']
        if bool(stop_record.get('is_connected', False))
    )
    connected_stop_var_set = set(connected_stop_vars)
    line_connected_stop_vars = tuple(
        str(stop_var)
        for stop_var in payload['line_stop_vars'][line_name]
        if str(stop_var) in connected_stop_var_set
    )
    if not line_connected_stop_vars:
        return ()
    if len(line_connected_stop_vars) == 1:
        return (line_connected_stop_vars[0],)
    return (line_connected_stop_vars[0], line_connected_stop_vars[-1])


def _normalize_railway_finish_origins(payload: MetroNetworkPayload) -> bool:
    payload_changed = False
    had_origins_key = 'railway_finish_origins' in payload
    raw_origins = payload.get('railway_finish_origins')
    if not isinstance(raw_origins, dict):
        payload['railway_finish_origins'] = {}
        return had_origins_key

    normalized_origins: dict[str, str] = {}
    valid_line_names = {str(line_name) for line_name in payload['line_stop_vars']}
    for raw_line_name, raw_stop_var in raw_origins.items():
        line_name = str(raw_line_name)
        stop_var = str(raw_stop_var)
        if line_name not in valid_line_names:
            payload_changed = True
            continue
        if stop_var not in _payload_line_finish_origin_options(payload, line_name):
            payload_changed = True
            continue
        normalized_origins[line_name] = stop_var

    if raw_origins != normalized_origins:
        payload['railway_finish_origins'] = normalized_origins
        payload_changed = True

    return payload_changed


def _load_network_payload() -> MetroNetworkPayload:
    if not METRO_NETWORK_PATH.exists():
        raise FileNotFoundError(f'Network data file not found: {METRO_NETWORK_PATH}')

    payload = cast(MetroNetworkPayload, json.loads(METRO_NETWORK_PATH.read_text(encoding='utf-8')))
    payload_changed = False

    for stop_record in payload['stops']:
        for field_name in CHECKPOINT_FIELDS:
            raw_checkpoint_value = stop_record.get(field_name, False)
            normalized_value = bool(raw_checkpoint_value)
            if raw_checkpoint_value != normalized_value or field_name not in stop_record:
                stop_record[field_name] = normalized_value
                payload_changed = True

        station_entry_x = _coerce_int(stop_record.get('station_entry_x'))
        station_entry_y = _coerce_int(stop_record.get('station_entry_y'))
        if station_entry_x is None or station_entry_y is None:
            if 'station_entry_x' in stop_record or 'station_entry_y' in stop_record:
                stop_record.pop('station_entry_x', None)
                stop_record.pop('station_entry_y', None)
                payload_changed = True
        else:
            if stop_record.get('station_entry_x') != station_entry_x:
                stop_record['station_entry_x'] = station_entry_x
                payload_changed = True
            if stop_record.get('station_entry_y') != station_entry_y:
                stop_record['station_entry_y'] = station_entry_y
                payload_changed = True

        normalized_chime_directions = list(
            _normalized_chime_directions(stop_record.get('chime_directions', []))
        )
        if stop_record.get('chime_directions') != normalized_chime_directions:
            stop_record['chime_directions'] = normalized_chime_directions
            payload_changed = True

    if _normalize_path_nodes(payload):
        payload_changed = True
    if _normalize_alignment_reminders(payload):
        payload_changed = True
    if _normalize_extra_edges(payload):
        payload_changed = True
    if _normalize_city_limits(payload):
        payload_changed = True
    if _normalize_railway_finish_progress(payload):
        payload_changed = True
    if _normalize_railway_finish_origins(payload):
        payload_changed = True

    if payload_changed:
        _write_network_payload(payload)

    return payload


def _apply_network_payload(payload: MetroNetworkPayload) -> None:
    global METRO_STOPS
    global STOPS_BY_VAR
    global STOPS_BY_LBL
    global LINE_COLORS
    global WOOL_COLORS
    global LINE_STOP_VARS
    global STOP_LINE_NAMES
    global METRO_LINES
    global LINE_PATH_SPECS
    global METRO_LINE_PATHS
    global METRO_LINE_PLOT_PATHS
    global RAILWAY_FINISH_PROGRESS
    global RAILWAY_FINISH_ORIGINS
    global PATH_NODES
    global PATH_NODES_BY_KEY
    global PATH_NODES_BY_ID
    global _ALL_PATH_NODES_CACHE_KEY
    global _ALL_PATH_NODES_CACHE
    global _ALL_PATH_NODES_BY_KEY_CACHE
    global EXTRA_EDGES
    global ALIGNMENT_REMINDERS

    stops = tuple(
        MetroStop(
            var=str(stop_record['var']),
            lbl=str(stop_record['lbl']),
            x=int(stop_record['x']),
            y=int(stop_record['y']),
            has_connector=bool(stop_record.get('has_connector', False)),
            has_full_station=bool(stop_record.get('has_full_station', False)),
            has_walking_paths=bool(stop_record.get('has_walking_paths', False)),
            is_connected=bool(stop_record.get('is_connected', False)),
            has_finished_railway=bool(stop_record.get('has_finished_railway', False)),
            has_signs=bool(stop_record.get('has_signs', False)),
            chime_directions=_normalized_chime_directions(stop_record.get('chime_directions', [])),
            station_entry_x=_coerce_int(stop_record.get('station_entry_x')),
            station_entry_y=_coerce_int(stop_record.get('station_entry_y')),
            city_limit_node_keys=tuple(str(key) for key in stop_record.get('city_limit_node_keys', [])),
        )
        for stop_record in payload['stops']
    )
    _validate_stop_records(stops)

    METRO_STOPS = stops
    STOPS_BY_VAR = {stop.var: stop for stop in METRO_STOPS}
    STOPS_BY_LBL = {stop.lbl: stop for stop in METRO_STOPS}
    LINE_COLORS = {
        str(line_name): str(color)
        for line_name, color in payload['line_colors'].items()
    }
    WOOL_COLORS = {
        str(line_name): str(color_name)
        for line_name, color_name in payload.get('wool_colors', {}).items()
    }
    LINE_STOP_VARS = {
        str(line_name): tuple(str(var) for var in stop_vars)
        for line_name, stop_vars in payload['line_stop_vars'].items()
    }
    STOP_LINE_NAMES = {
        stop.var: tuple(
            line_name
            for line_name, stop_vars in LINE_STOP_VARS.items()
            if stop.var in stop_vars
        )
        for stop in METRO_STOPS
    }
    METRO_LINES = {
        line_name: tuple(STOPS_BY_VAR[var] for var in stop_vars)
        for line_name, stop_vars in LINE_STOP_VARS.items()
    }
    LINE_PATH_SPECS = {
        str(line_name): tuple(
            LinePathPointSpec(
                x_var=str(spec['x_var']),
                y_var=str(spec['y_var']),
                dx=int(spec.get('dx', 0)),
                dy=int(spec.get('dy', 0)),
            )
            for spec in specs
        )
        for line_name, specs in payload['line_path_specs'].items()
    }
    METRO_LINE_PATHS = {
        line_name: tuple(spec.coordinates for spec in point_specs)
        for line_name, point_specs in LINE_PATH_SPECS.items()
    }
    METRO_LINE_PLOT_PATHS = {
        line_name: tuple(spec.plot_coordinates for spec in point_specs)
        for line_name, point_specs in LINE_PATH_SPECS.items()
    }
    RAILWAY_FINISH_PROGRESS = {
        str(line_name): {
            'x': int(point['x']),
            'y': int(point['y']),
        }
        for line_name, point in payload.get('railway_finish_progress', {}).items()
        if str(line_name) in LINE_STOP_VARS
    }
    RAILWAY_FINISH_ORIGINS = {
        str(line_name): str(stop_var)
        for line_name, stop_var in payload.get('railway_finish_origins', {}).items()
        if str(line_name) in LINE_STOP_VARS
        and str(stop_var) in LINE_STOP_VARS[str(line_name)]
    }
    PATH_NODES = tuple(
        PathNode(
            id=str(path_node_record['id']),
            x=int(path_node_record['x']),
            y=int(path_node_record['y']),
            label=(
                str(path_node_record['label'])
                if 'label' in path_node_record and str(path_node_record['label']).strip()
                else None
            ),
            is_explicit=True,
            poi_kind=(
                str(path_node_record['poi_kind'])
                if str(path_node_record.get('poi_kind', '')).strip().lower() in {'monument', 'pillager_tower'}
                else None
            ),
            category=(
                str(path_node_record['category'])
                if 'category' in path_node_record and str(path_node_record['category']).strip()
                else None
            ),
        )
        for path_node_record in payload.get('path_nodes', [])
    )
    PATH_NODES_BY_KEY = {path_node.key: path_node for path_node in PATH_NODES}
    PATH_NODES_BY_ID = {path_node.id: path_node for path_node in PATH_NODES}
    EXTRA_EDGES = tuple(
        ExtraEdgeDefinition(
            id=str(extra_edge_record['id']),
            kind=cast(ExtraEdgeKind, str(extra_edge_record['kind'])),
            from_endpoint=_path_endpoint_from_record(
                _required_extra_edge_endpoint(extra_edge_record, 'from_endpoint')
            ),
            to_endpoint=_path_endpoint_from_record(
                _required_extra_edge_endpoint(extra_edge_record, 'to_endpoint')
            ),
            bidirectional=bool(extra_edge_record.get('bidirectional', True)),
            label=(
                str(extra_edge_record['label'])
                if 'label' in extra_edge_record and str(extra_edge_record['label']).strip()
                else None
            ),
            distance=(
                int(extra_edge_record['distance'])
                if 'distance' in extra_edge_record and extra_edge_record['distance'] is not None
                else None
            ),
            path_points=tuple(
                (int(point['x']), int(point['y']))
                for point in extra_edge_record.get('path_points', [])
            ),
        )
        for extra_edge_record in payload.get('extra_edges', [])
    )
    _ALL_PATH_NODES_CACHE_KEY = None
    _ALL_PATH_NODES_CACHE = ()
    _ALL_PATH_NODES_BY_KEY_CACHE = {}
    ALIGNMENT_REMINDERS = tuple(
        AlignmentReminder(
            first_var=str(reminder_record['first_var']),
            second_var=str(reminder_record['second_var']),
            axis=cast(AlignmentAxis, str(reminder_record['axis'])),
        )
        for reminder_record in payload.get('alignment_reminders', [])
    )

    _validate_line_sequences()
    _validate_line_path_specs()
    _validate_line_colors()
    _validate_path_nodes()
    _validate_extra_edges()
    _validate_stop_line_names()


def _reload_network_data() -> None:
    _apply_network_payload(_load_network_payload())


def _update_stop_record(
    stop_var: str,
    *,
    lbl: str | None = None,
    x: int | None = None,
    y: int | None = None,
    has_connector: bool | None = None,
    has_full_station: bool | None = None,
    has_walking_paths: bool | None = None,
    is_connected: bool | None = None,
    has_finished_railway: bool | None = None,
    has_signs: bool | None = None,
    chime_directions: Sequence[ChimeDirection] | None = None,
    station_entry: tuple[int, int] | None | Literal[False] = None,
) -> None:
    payload = _load_network_payload()

    for stop_record in payload['stops']:
        if str(stop_record['var']) != stop_var:
            continue
        if lbl is not None:
            stop_record['lbl'] = lbl
        if x is not None:
            stop_record['x'] = int(x)
        if y is not None:
            stop_record['y'] = int(y)
        if has_connector is not None:
            stop_record['has_connector'] = bool(has_connector)
        if has_full_station is not None:
            stop_record['has_full_station'] = bool(has_full_station)
        if has_walking_paths is not None:
            stop_record['has_walking_paths'] = bool(has_walking_paths)
        if is_connected is not None:
            stop_record['is_connected'] = bool(is_connected)
        if has_finished_railway is not None:
            stop_record['has_finished_railway'] = bool(has_finished_railway)
        if has_signs is not None:
            stop_record['has_signs'] = bool(has_signs)
        if chime_directions is not None:
            stop_record['chime_directions'] = list(_normalized_chime_directions(chime_directions))
        if station_entry is False:
            stop_record.pop('station_entry_x', None)
            stop_record.pop('station_entry_y', None)
        elif station_entry is not None:
            stop_record['station_entry_x'] = int(station_entry[0])
            stop_record['station_entry_y'] = int(station_entry[1])
        _normalize_alignment_reminders(payload)
        _normalize_extra_edges(payload)
        _write_network_payload(payload)
        _apply_network_payload(payload)
        return

    raise ValueError(f'Unknown stop: {stop_var}')


def _line_anchor_spec(stop_var: str) -> LinePathSpecRecord:
    return {'x_var': stop_var, 'y_var': stop_var, 'dx': 0, 'dy': 0}


def _station_line_membership_from_payload(
    payload: MetroNetworkPayload,
    stop_var: str,
) -> tuple[str, ...]:
    return tuple(
        str(line_name)
        for line_name, stop_vars in payload['line_stop_vars'].items()
        if stop_var in {str(candidate_var) for candidate_var in stop_vars}
    )


def _station_var_suffix(stop_var: str) -> str:
    return ''.join(char for char in stop_var.removeprefix('P_') if not char.isalpha())


def _unique_station_var_for_membership(
    payload: MetroNetworkPayload,
    line_names: Sequence[str],
    *,
    old_var: str,
) -> str:
    existing_vars = {
        str(stop_record['var'])
        for stop_record in payload['stops']
        if str(stop_record['var']) != old_var
    }
    suffix = _station_var_suffix(old_var)
    if line_names:
        base_candidate = f"P_{''.join(sorted(line_names))}{suffix}"
        candidate = base_candidate
    else:
        numeric_suffix = ''.join(char for char in suffix if char.isdigit()) or '0'
        base_candidate = f'P_{numeric_suffix}'
        candidate = base_candidate

    if candidate not in existing_vars:
        return candidate

    index = 2
    while f'{base_candidate}{index}' in existing_vars:
        index += 1
    return f'{base_candidate}{index}'


def _rename_stop_var_in_payload(
    payload: MetroNetworkPayload,
    old_var: str,
    new_var: str,
) -> str:
    if old_var == new_var:
        return old_var

    if any(str(stop_record['var']) == new_var for stop_record in payload['stops']):
        raise ValueError(f'Stop variable already exists: {new_var}')

    found_stop = False
    for stop_record in payload['stops']:
        if str(stop_record['var']) == old_var:
            stop_record['var'] = new_var
            found_stop = True
            break
    if not found_stop:
        raise ValueError(f'Unknown stop: {old_var}')

    for line_name, stop_vars in payload['line_stop_vars'].items():
        payload['line_stop_vars'][line_name] = [
            new_var if str(stop_var) == old_var else str(stop_var)
            for stop_var in stop_vars
        ]

    for specs in payload['line_path_specs'].values():
        for spec in specs:
            if str(spec['x_var']) == old_var:
                spec['x_var'] = new_var
            if str(spec['y_var']) == old_var:
                spec['y_var'] = new_var

    for extra_edge in payload.get('extra_edges', []):
        if not isinstance(extra_edge, dict):
            continue
        for endpoint_field in ('from_endpoint', 'to_endpoint'):
            endpoint = extra_edge.get(endpoint_field)
            if isinstance(endpoint, dict) and endpoint.get('kind') == 'stop' and endpoint.get('stop_var') == old_var:
                endpoint['stop_var'] = new_var
        if extra_edge.get('from_var') == old_var:
            extra_edge['from_var'] = new_var
        if extra_edge.get('to_var') == old_var:
            extra_edge['to_var'] = new_var

    for reminder in payload.get('alignment_reminders', []):
        if str(reminder.get('first_var')) == old_var:
            reminder['first_var'] = new_var
        if str(reminder.get('second_var')) == old_var:
            reminder['second_var'] = new_var

    railway_finish_origins = payload.get('railway_finish_origins')
    if isinstance(railway_finish_origins, dict):
        for line_name, origin_var in list(railway_finish_origins.items()):
            if str(origin_var) == old_var:
                railway_finish_origins[line_name] = new_var

    return new_var


def _remove_station_from_line_specs(
    payload: MetroNetworkPayload,
    line_name: str,
    station_var: str,
) -> None:
    stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][line_name]]
    if station_var not in stop_vars:
        raise ValueError(f'{station_var} is not on Line {line_name}.')

    remaining_stop_vars = [stop_var for stop_var in stop_vars if stop_var != station_var]
    anchors = _payload_line_anchor_index_map(payload, line_name)
    if not remaining_stop_vars:
        del payload['line_stop_vars'][line_name]
        payload['line_path_specs'].pop(line_name, None)
        payload['line_colors'].pop(line_name, None)
        payload.get('wool_colors', {}).pop(line_name, None)
        payload.get('railway_finish_progress', {}).pop(line_name, None)
        payload.get('railway_finish_origins', {}).pop(line_name, None)
        return

    payload['line_stop_vars'][line_name] = remaining_stop_vars

    if len(remaining_stop_vars) == 1:
        payload['line_path_specs'][line_name] = [
            _line_anchor_spec(remaining_stop_vars[0]),
            _line_anchor_spec(remaining_stop_vars[0]),
        ]
        return

    specs = list(payload['line_path_specs'].get(line_name, []))
    old_index = stop_vars.index(station_var)
    station_anchor = anchors.get(station_var)
    if station_anchor is None:
        payload['line_path_specs'][line_name] = [
            _line_anchor_spec(stop_var)
            for stop_var in remaining_stop_vars
        ]
        return

    if old_index == 0:
        next_anchor = anchors.get(stop_vars[1])
        if next_anchor is None:
            payload['line_path_specs'][line_name] = [_line_anchor_spec(stop_var) for stop_var in remaining_stop_vars]
            return
        del specs[station_anchor:next_anchor]
    elif old_index == len(stop_vars) - 1:
        previous_anchor = anchors.get(stop_vars[old_index - 1])
        if previous_anchor is None:
            payload['line_path_specs'][line_name] = [_line_anchor_spec(stop_var) for stop_var in remaining_stop_vars]
            return
        del specs[previous_anchor + 1:station_anchor + 1]
    else:
        previous_anchor = anchors.get(stop_vars[old_index - 1])
        next_anchor = anchors.get(stop_vars[old_index + 1])
        if previous_anchor is None or next_anchor is None:
            payload['line_path_specs'][line_name] = [_line_anchor_spec(stop_var) for stop_var in remaining_stop_vars]
            return
        del specs[previous_anchor + 1:next_anchor]

    payload['line_path_specs'][line_name] = specs


def _make_station_unassociated(stop_record: StopRecord) -> None:
    stop_record['lbl'] = UNASSOCIATED_STATION_LABEL
    stop_record['has_connector'] = False
    stop_record['has_full_station'] = False
    stop_record['has_walking_paths'] = False
    stop_record['is_connected'] = False
    stop_record['has_finished_railway'] = False
    stop_record['has_signs'] = False
    stop_record['chime_directions'] = []


def remove_station_from_line(stop_var: str, line_name: str) -> str:
    payload = _load_network_payload()
    if line_name not in payload['line_stop_vars']:
        raise ValueError(f'Unknown line: {line_name}')
    stop_lookup = {
        str(stop_record['var']): stop_record
        for stop_record in payload['stops']
    }
    if stop_var not in stop_lookup:
        raise ValueError(f'Unknown stop: {stop_var}')
    if stop_var not in {str(candidate_var) for candidate_var in payload['line_stop_vars'][line_name]}:
        raise ValueError(f'{stop_lookup[stop_var]["lbl"]} is not on Line {line_name}.')

    _remove_station_from_line_specs(payload, line_name, stop_var)
    remaining_line_names = _station_line_membership_from_payload(payload, stop_var)
    new_stop_var = _unique_station_var_for_membership(payload, remaining_line_names, old_var=stop_var)
    if not remaining_line_names:
        _make_station_unassociated(stop_lookup[stop_var])
    new_stop_var = _rename_stop_var_in_payload(payload, stop_var, new_stop_var)
    if remaining_line_names and _is_placeholder_station_label(str(stop_lookup[stop_var].get('lbl', ''))):
        stop_lookup[stop_var]['lbl'] = _auto_station_label_from_payload(payload, new_stop_var)

    _normalize_alignment_reminders(payload)
    _normalize_extra_edges(payload)
    _normalize_railway_finish_progress(payload)
    _normalize_railway_finish_origins(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)
    return new_stop_var


def set_metro_line_color(line_name: str, color_text: str) -> str:
    normalized_line_name = _normalize_line_name(line_name)
    if normalized_line_name not in LINE_STOP_VARS:
        raise ValueError(f'Unknown line: {line_name}')
    normalized_color = _normalize_line_color(color_text)
    payload = _load_network_payload()
    payload['line_colors'][normalized_line_name] = normalized_color
    _write_network_payload(payload)
    _apply_network_payload(payload)
    return normalized_color


def rename_metro_line(old_line_name: str, new_line_name: str) -> str:
    old_name = _normalize_line_name(old_line_name)
    new_name = _normalize_line_name(new_line_name)
    if old_name not in LINE_STOP_VARS:
        raise ValueError(f'Unknown line: {old_line_name}')
    if old_name == new_name:
        return old_name
    if new_name in LINE_STOP_VARS:
        raise ValueError(f'Line {new_name} already exists.')

    payload = _load_network_payload()
    if old_name not in payload['line_stop_vars']:
        raise ValueError(f'Unknown line: {old_line_name}')

    affected_stop_vars = tuple(str(stop_var) for stop_var in payload['line_stop_vars'][old_name])
    for field_name in ('line_stop_vars', 'line_path_specs', 'line_colors', 'wool_colors'):
        raw_mapping = payload.get(field_name)
        if not isinstance(raw_mapping, dict) or old_name not in raw_mapping:
            continue
        payload[field_name] = {
            (new_name if str(line_name) == old_name else str(line_name)): value
            for line_name, value in raw_mapping.items()
        }
    for field_name in ('railway_finish_progress', 'railway_finish_origins'):
        raw_mapping = payload.get(field_name)
        if not isinstance(raw_mapping, dict) or old_name not in raw_mapping:
            continue
        payload[field_name] = {
            (new_name if str(line_name) == old_name else str(line_name)): value
            for line_name, value in raw_mapping.items()
        }

    for old_stop_var in affected_stop_vars:
        if not any(str(stop_record['var']) == old_stop_var for stop_record in payload['stops']):
            continue
        membership = _station_line_membership_from_payload(payload, old_stop_var)
        new_stop_var = _unique_station_var_for_membership(payload, membership, old_var=old_stop_var)
        renamed_stop_var = _rename_stop_var_in_payload(payload, old_stop_var, new_stop_var)
        for stop_record in payload['stops']:
            if str(stop_record['var']) != renamed_stop_var:
                continue
            if _is_placeholder_station_label(str(stop_record.get('lbl', ''))):
                stop_record['lbl'] = _auto_station_label_from_payload(payload, renamed_stop_var)
            break

    _normalize_alignment_reminders(payload)
    _normalize_extra_edges(payload)
    _normalize_railway_finish_progress(payload)
    _normalize_railway_finish_origins(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)
    return new_name


def set_stop_city_limit_node_keys(stop_var: str, node_keys: Sequence[str]) -> None:
    payload = _load_network_payload()
    normalized_node_keys = list(dict.fromkeys(str(node_key) for node_key in node_keys))
    for stop_record in payload['stops']:
        if str(stop_record['var']) != stop_var:
            continue
        if normalized_node_keys:
            stop_record['city_limit_node_keys'] = normalized_node_keys
        else:
            stop_record.pop('city_limit_node_keys', None)
        _normalize_city_limits(payload)
        _write_network_payload(payload)
        _apply_network_payload(payload)
        return
    raise ValueError(f'Unknown stop: {stop_var}')


def set_railway_finish_progress(line_name: str, coordinates: tuple[int, int]) -> None:
    if line_name not in LINE_STOP_VARS:
        raise ValueError(f'Unknown line: {line_name}')
    if _line_finish_location_for_coordinates(line_name, coordinates) is None:
        raise ValueError(f'That coordinate is not on Line {line_name}. Try another coordinate.')

    stop_vars_to_mark = set(_line_finish_stop_vars_to_mark(line_name, coordinates))
    payload = _load_network_payload()
    railway_finish_progress = payload.setdefault('railway_finish_progress', {})
    railway_finish_progress[line_name] = {
        'x': int(coordinates[0]),
        'y': int(coordinates[1]),
    }
    for stop_record in payload['stops']:
        if str(stop_record['var']) in stop_vars_to_mark:
            stop_record['is_connected'] = True
            stop_record['has_finished_railway'] = True

    _normalize_railway_finish_progress(payload)
    _normalize_railway_finish_origins(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def switch_railway_finish_origin(line_name: str) -> str:
    if line_name not in LINE_STOP_VARS:
        raise ValueError(f'Unknown line: {line_name}')

    origin_options = _line_finish_origin_options(line_name)
    if len(origin_options) < 2:
        raise ValueError(f'Line {line_name} does not have another connected origin yet.')

    current_origin = _line_finish_origin_var(line_name)
    next_origin = origin_options[(origin_options.index(current_origin) + 1) % len(origin_options)]
    payload = _load_network_payload()
    railway_finish_origins = payload.setdefault('railway_finish_origins', {})
    railway_finish_origins[line_name] = next_origin
    _normalize_railway_finish_origins(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)
    return next_origin


def _payload_line_anchor_index_map(
    payload: MetroNetworkPayload,
    line_name: str,
) -> dict[str, int]:
    anchor_indices: dict[str, int] = {}
    line_stop_vars = {
        str(stop_var)
        for stop_var in payload['line_stop_vars'][line_name]
    }
    for index, spec in enumerate(payload['line_path_specs'][line_name]):
        x_var = str(spec['x_var'])
        y_var = str(spec['y_var'])
        if x_var == y_var and x_var in line_stop_vars:
            anchor_indices.setdefault(x_var, index)
    return anchor_indices


def _alignment_axis_for_pair(
    payload: MetroNetworkPayload,
    first_var: str,
    second_var: str,
) -> AlignmentAxis:
    stop_lookup = {
        str(stop_record['var']): stop_record
        for stop_record in payload['stops']
    }
    first_record = stop_lookup[first_var]
    second_record = stop_lookup[second_var]
    return _infer_alignment_axis_from_coordinates(
        int(first_record['x']),
        int(first_record['y']),
        int(second_record['x']),
        int(second_record['y']),
    )


def _remove_alignment_reminder_for_pair(
    payload: MetroNetworkPayload,
    first_var: str,
    second_var: str,
) -> None:
    ordered_first_var, ordered_second_var = sorted((first_var, second_var))
    axis = _alignment_axis_for_pair(payload, first_var, second_var)
    alignment_reminders = payload.get('alignment_reminders', [])
    payload['alignment_reminders'] = [
        reminder
        for reminder in alignment_reminders
        if not (
            str(reminder.get('first_var')) == ordered_first_var
            and str(reminder.get('second_var')) == ordered_second_var
            and str(reminder.get('axis')) == axis
        )
    ]


def _sync_direct_alignment_reminder_for_pair(
    payload: MetroNetworkPayload,
    first_var: str,
    second_var: str,
    *,
    is_direct: bool,
) -> None:
    _remove_alignment_reminder_for_pair(payload, first_var, second_var)
    if not is_direct:
        return

    axis = _alignment_axis_for_pair(payload, first_var, second_var)
    stop_lookup = {
        str(stop_record['var']): stop_record
        for stop_record in payload['stops']
    }
    first_record = stop_lookup[first_var]
    second_record = stop_lookup[second_var]
    if axis == 'x' and int(first_record['x']) == int(second_record['x']):
        return
    if axis == 'y' and int(first_record['y']) == int(second_record['y']):
        return

    payload.setdefault('alignment_reminders', [])
    payload['alignment_reminders'].append(
        {
            'first_var': first_var,
            'second_var': second_var,
            'axis': axis,
        }
    )


def _find_line_segment_specs_in_payload(
    payload: MetroNetworkPayload,
    line_name: str,
    start_var: str,
    end_var: str,
) -> tuple[int, int, tuple[LinePathSpecRecord, ...]]:
    anchor_indices = _payload_line_anchor_index_map(payload, line_name)
    start_index = anchor_indices[start_var]
    end_index = anchor_indices[end_var]
    segment_specs = tuple(
        cast(LinePathSpecRecord, spec)
        for spec in payload['line_path_specs'][line_name][start_index:end_index + 1]
    )
    return (start_index, end_index, segment_specs)


def _best_turn_variant_for_metro_segment_in_payload(
    payload: MetroNetworkPayload,
    line_name: str,
    start_var: str,
    end_var: str,
) -> int:
    start_index, end_index, current_segment_specs = _find_line_segment_specs_in_payload(
        payload,
        line_name,
        start_var,
        end_var,
    )
    start_anchor_spec = cast(LinePathSpecRecord, current_segment_specs[0])
    end_anchor_spec = cast(LinePathSpecRecord, current_segment_specs[-1])
    stop_vars = tuple(str(stop_var) for stop_var in payload['line_stop_vars'][line_name])

    previous_segment_specs: tuple[LinePathSpecRecord, ...] | None = None
    if start_index > 0:
        previous_start_var = stop_vars[stop_vars.index(start_var) - 1]
        _previous_start_index, _previous_end_index, previous_segment_specs = _find_line_segment_specs_in_payload(
            payload,
            line_name,
            previous_start_var,
            start_var,
        )

    next_segment_specs: tuple[LinePathSpecRecord, ...] | None = None
    if end_index < len(payload['line_path_specs'][line_name]) - 1 and stop_vars.index(end_var) < len(stop_vars) - 1:
        next_end_var = stop_vars[stop_vars.index(end_var) + 1]
        _next_start_index, _next_end_index, next_segment_specs = _find_line_segment_specs_in_payload(
            payload,
            line_name,
            end_var,
            next_end_var,
        )

    best_variant = 0
    best_score: tuple[int, int, int] | None = None
    for variant in (0, 1):
        bare_replacement_specs = _metro_segment_path_specs(
            start_anchor_spec,
            end_anchor_spec,
            start_var=start_var,
            shape='turn',
            turn_variant=variant,
            start_hook_spec=None,
        )
        start_hook_spec = _hook_spec_for_turn_start(
            start_var,
            previous_segment_specs,
            bare_replacement_specs,
        )
        replacement_specs = tuple(
            _metro_segment_path_specs(
                start_anchor_spec,
                end_anchor_spec,
                start_var=start_var,
                shape='turn',
                turn_variant=variant,
                start_hook_spec=start_hook_spec,
            )
        )
        local_points = _combined_spec_points(previous_segment_specs, replacement_specs, next_segment_specs)
        score = (
            _polyline_turn_count(local_points),
            _polyline_turn_count(_spec_points(replacement_specs)),
            variant,
        )
        if best_score is None or score < best_score:
            best_variant = variant
            best_score = score

    return best_variant


def _set_metro_line_segment_shape(
    line_name: str,
    start_var: str,
    end_var: str,
    *,
    shape: MetroSegmentShape,
    turn_variant: int | None = None,
) -> None:
    payload = _load_network_payload()
    stop_vars = tuple(str(stop_var) for stop_var in payload['line_stop_vars'][line_name])
    if start_var not in stop_vars or end_var not in stop_vars:
        raise ValueError(f'Unknown segment on Line {line_name}.')

    start_position = stop_vars.index(start_var)
    end_position = stop_vars.index(end_var)
    if end_position - start_position != 1:
        raise ValueError('Metro segment edits only support consecutive stops on a line.')

    start_index, end_index, current_segment_specs = _find_line_segment_specs_in_payload(
        payload,
        line_name,
        start_var,
        end_var,
    )
    start_anchor_spec = cast(LinePathSpecRecord, current_segment_specs[0])
    end_anchor_spec = cast(LinePathSpecRecord, current_segment_specs[-1])
    previous_segment_specs: tuple[LinePathSpecRecord, ...] | None = None
    if start_position > 0:
        previous_start_var = stop_vars[start_position - 1]
        _previous_start_index, _previous_end_index, previous_segment_specs = _find_line_segment_specs_in_payload(
            payload,
            line_name,
            previous_start_var,
            start_var,
        )

    bare_replacement_specs = _metro_segment_path_specs(
        start_anchor_spec,
        end_anchor_spec,
        start_var=start_var,
        shape=shape,
        turn_variant=turn_variant,
        start_hook_spec=None,
    )
    start_hook_spec = (
        _hook_spec_for_turn_start(
            start_var,
            previous_segment_specs,
            bare_replacement_specs,
        )
        if shape == 'turn'
        else None
    )
    replacement_specs = _metro_segment_path_specs(
        start_anchor_spec,
        end_anchor_spec,
        start_var=start_var,
        shape=shape,
        turn_variant=turn_variant,
        start_hook_spec=start_hook_spec,
    )
    payload['line_path_specs'][line_name][start_index:end_index + 1] = replacement_specs
    _sync_direct_alignment_reminder_for_pair(
        payload,
        start_var,
        end_var,
        is_direct=shape == 'direct',
    )
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def make_metro_line_segment_direct(line_name: str, start_var: str, end_var: str) -> None:
    _set_metro_line_segment_shape(
        line_name,
        start_var,
        end_var,
        shape='direct',
    )


def add_turn_to_metro_line_segment(line_name: str, start_var: str, end_var: str) -> None:
    start_stop = STOPS_BY_VAR[start_var]
    end_stop = STOPS_BY_VAR[end_var]
    if start_stop.x == end_stop.x or start_stop.y == end_stop.y:
        raise ValueError('This metro segment is already axis-aligned, so there is no turn to add.')

    payload = _load_network_payload()
    preferred_variant = _best_turn_variant_for_metro_segment_in_payload(
        payload,
        line_name,
        start_var,
        end_var,
    )

    _set_metro_line_segment_shape(
        line_name,
        start_var,
        end_var,
        shape='turn',
        turn_variant=preferred_variant,
    )


def flip_metro_line_segment_turn(line_name: str, start_var: str, end_var: str) -> None:
    segment = MetroLineSegment(
        line_name=line_name,
        start_var=start_var,
        end_var=end_var,
        specs=_line_segment_specs(line_name, start_var, end_var),
    )
    if segment.turn_variant is None:
        raise ValueError('This metro segment does not currently have a simple turn to flip.')

    _set_metro_line_segment_shape(
        line_name,
        start_var,
        end_var,
        shape='turn',
        turn_variant=1 - segment.turn_variant,
    )


def _direct_alignment_axis_for_edge_record(
    payload: MetroNetworkPayload,
    edge_record: ExtraEdgeRecord,
) -> AlignmentAxis:
    stop_pair = _edge_record_stop_pair(payload, edge_record)
    if stop_pair is None:
        raise ValueError('Alignment reminders only apply to stop-to-stop path edges.')
    return _alignment_axis_for_pair(
        payload,
        stop_pair[0],
        stop_pair[1],
    )


def _edge_record_stop_pair(
    payload: MetroNetworkPayload,
    edge_record: ExtraEdgeRecord,
) -> tuple[str, str] | None:
    from_endpoint = _normalize_path_endpoint_record(
        payload,
        edge_record.get('from_endpoint'),
        fallback_identifier=str(edge_record.get('from_var', '')),
    )
    to_endpoint = _normalize_path_endpoint_record(
        payload,
        edge_record.get('to_endpoint'),
        fallback_identifier=str(edge_record.get('to_var', '')),
    )
    if from_endpoint is None or to_endpoint is None:
        return None
    if from_endpoint['kind'] != 'stop' or to_endpoint['kind'] != 'stop':
        return None
    return (from_endpoint['stop_var'], to_endpoint['stop_var'])


def _remove_alignment_reminder_for_edge_record(
    payload: MetroNetworkPayload,
    edge_record: ExtraEdgeRecord,
) -> None:
    stop_pair = _edge_record_stop_pair(payload, edge_record)
    if stop_pair is None:
        return
    _remove_alignment_reminder_for_pair(
        payload,
        stop_pair[0],
        stop_pair[1],
    )


def _sync_alignment_reminder_for_edge_record(
    payload: MetroNetworkPayload,
    edge_record: ExtraEdgeRecord,
) -> None:
    stop_pair = _edge_record_stop_pair(payload, edge_record)
    if stop_pair is None:
        return
    _sync_direct_alignment_reminder_for_pair(
        payload,
        stop_pair[0],
        stop_pair[1],
        is_direct=not bool(edge_record.get('path_points')),
    )


def _find_extra_edge_record(payload: MetroNetworkPayload, edge_id: str) -> ExtraEdgeRecord:
    for extra_edge in payload.get('extra_edges', []):
        if str(extra_edge.get('id', '')).strip() == edge_id:
            return cast(ExtraEdgeRecord, extra_edge)
    raise ValueError(f'Unknown path edge: {edge_id}')


def add_path_node(identifier: str, *, label: str | None = None) -> None:
    payload = _load_network_payload()
    coordinates = _parse_coordinate_text(identifier)
    if coordinates is None:
        raise ValueError('Path nodes need Minecraft coordinates in the format x, y.')

    stop_coordinates = {
        (int(stop_record['x']), int(stop_record['y']))
        for stop_record in payload['stops']
    }
    if coordinates in stop_coordinates:
        raise ValueError('Path nodes cannot overlap a station coordinate.')

    existing_nodes = payload.get('path_nodes', [])
    if not isinstance(existing_nodes, list):
        payload['path_nodes'] = []
        existing_nodes = payload['path_nodes']

    for raw_node in existing_nodes:
        if not isinstance(raw_node, dict):
            continue
        if (int(raw_node.get('x', 0)), int(raw_node.get('y', 0))) == coordinates:
            raise ValueError('A path node already exists at those coordinates.')

    next_index = len(existing_nodes) + 1
    node_record: PathNodeRecord = {
        'id': f'node_{next_index}',
        'x': coordinates[0],
        'y': coordinates[1],
    }
    normalized_label = None if label is None else (label.strip() or None)
    if normalized_label is not None:
        node_record['label'] = normalized_label

    existing_nodes.append(node_record)
    _normalize_path_nodes(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def remove_path_node(identifier: str) -> None:
    payload = _load_network_payload()
    path_node = _resolve_path_node_in_payload(payload, identifier)
    if path_node is None:
        coordinates = _parse_coordinate_text(identifier)
        if coordinates is None:
            raise ValueError(f'Unknown path node: {identifier}')
    else:
        coordinates = (int(path_node['x']), int(path_node['y']))

    filtered_edges: list[ExtraEdgeRecord] = []
    for extra_edge in payload.get('extra_edges', []):
        if not isinstance(extra_edge, dict):
            continue
        from_endpoint = extra_edge.get('from_endpoint', {})
        to_endpoint = extra_edge.get('to_endpoint', {})
        uses_coordinates = (
            isinstance(from_endpoint, dict)
            and from_endpoint.get('kind') == 'coord'
            and (int(from_endpoint.get('x', 0)), int(from_endpoint.get('y', 0))) == coordinates
        ) or (
            isinstance(to_endpoint, dict)
            and to_endpoint.get('kind') == 'coord'
            and (int(to_endpoint.get('x', 0)), int(to_endpoint.get('y', 0))) == coordinates
        )
        if uses_coordinates:
            _remove_alignment_reminder_for_edge_record(payload, cast(ExtraEdgeRecord, extra_edge))
            continue
        filtered_edges.append(cast(ExtraEdgeRecord, extra_edge))

    payload['extra_edges'] = filtered_edges
    payload['path_nodes'] = [
        cast(PathNodeRecord, raw_node)
        for raw_node in payload.get('path_nodes', [])
        if isinstance(raw_node, dict)
        and (int(raw_node.get('x', 0)), int(raw_node.get('y', 0))) != coordinates
    ]
    _normalize_path_nodes(payload)
    _normalize_extra_edges(payload)
    _normalize_alignment_reminders(payload)
    _normalize_city_limits(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def move_path_node(identifier: str, coordinates: tuple[int, int]) -> None:
    payload = _load_network_payload()
    path_node = _resolve_path_node_in_payload(payload, identifier)
    if path_node is None:
        old_coordinates = _parse_coordinate_text(identifier)
        if old_coordinates is None:
            raise ValueError(f'Unknown path node: {identifier}')
    else:
        old_coordinates = (int(path_node['x']), int(path_node['y']))

    new_coordinates = (int(coordinates[0]), int(coordinates[1]))
    if new_coordinates == old_coordinates:
        return

    stop_coordinates = {
        (int(stop_record['x']), int(stop_record['y']))
        for stop_record in payload['stops']
    }
    if new_coordinates in stop_coordinates:
        raise ValueError('Path nodes cannot overlap a station coordinate.')

    old_key = _coordinate_endpoint_key(old_coordinates[0], old_coordinates[1])
    new_key = _coordinate_endpoint_key(new_coordinates[0], new_coordinates[1])
    occupied_keys = _path_node_keys_in_payload(payload)
    occupied_keys.discard(old_key)
    if new_key in occupied_keys:
        raise ValueError('A path node already exists at those coordinates.')

    moved_explicit_node = False
    for raw_node in payload.get('path_nodes', []):
        if not isinstance(raw_node, dict):
            continue
        if (int(raw_node.get('x', 0)), int(raw_node.get('y', 0))) != old_coordinates:
            continue
        raw_node['x'] = new_coordinates[0]
        raw_node['y'] = new_coordinates[1]
        moved_explicit_node = True
        break

    updated_endpoint = False
    for raw_edge in payload.get('extra_edges', []):
        if not isinstance(raw_edge, dict):
            continue

        for field_name, point_index in (('from_endpoint', 0), ('to_endpoint', -1)):
            raw_endpoint = raw_edge.get(field_name)
            if not isinstance(raw_endpoint, dict):
                continue
            endpoint = _normalize_path_endpoint_record(payload, raw_endpoint)
            if endpoint is None or endpoint['kind'] != 'coord':
                continue
            if (int(endpoint['x']), int(endpoint['y'])) != old_coordinates:
                continue

            raw_endpoint['kind'] = 'coord'
            raw_endpoint['x'] = new_coordinates[0]
            raw_endpoint['y'] = new_coordinates[1]
            updated_endpoint = True

            raw_path_points = raw_edge.get('path_points')
            if not isinstance(raw_path_points, list) or not raw_path_points:
                continue
            target_point = raw_path_points[point_index]
            if not isinstance(target_point, dict):
                continue
            if (
                _coerce_int(target_point.get('x')) == old_coordinates[0]
                and _coerce_int(target_point.get('y')) == old_coordinates[1]
            ):
                target_point['x'] = new_coordinates[0]
                target_point['y'] = new_coordinates[1]

    if not moved_explicit_node and not updated_endpoint:
        raise ValueError(f'Unknown path node: {identifier}')

    for stop_record in payload.get('stops', []):
        if not isinstance(stop_record, dict):
            continue
        raw_node_keys = stop_record.get('city_limit_node_keys')
        if not isinstance(raw_node_keys, list):
            continue
        stop_record['city_limit_node_keys'] = [
            new_key if str(node_key).strip() == old_key else str(node_key).strip()
            for node_key in raw_node_keys
        ]

    _normalize_path_nodes(payload)
    _normalize_extra_edges(payload)
    _normalize_city_limits(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def add_extra_edge(
    first_station: str,
    second_station: str,
    kind: ExtraEdgeKind = 'connector',
    *,
    label: str | None = None,
    bidirectional: bool = True,
) -> None:
    payload = _load_network_payload()
    first_endpoint = _path_endpoint_record_from_identifier(payload, first_station)
    second_endpoint = _path_endpoint_record_from_identifier(payload, second_station)
    if first_endpoint is None:
        raise ValueError(
            f'Unknown path endpoint: {first_station}. Use a station label / var or coordinates like x, y.'
        )
    if second_endpoint is None:
        raise ValueError(
            f'Unknown path endpoint: {second_station}. Use a station label / var or coordinates like x, y.'
        )
    if first_endpoint == second_endpoint:
        raise ValueError('Path edges need two different endpoints.')

    normalized_label = None if label is None else (label.strip() or None)
    first_endpoint_obj = _path_endpoint_from_record(first_endpoint)
    second_endpoint_obj = _path_endpoint_from_record(second_endpoint)
    edge_id = (
        f'{kind}_{first_endpoint_obj.key.replace(":", "_").replace(",", "_")}_'
        f'{second_endpoint_obj.key.replace(":", "_").replace(",", "_")}_{len(payload.get("extra_edges", [])) + 1}'
    )
    payload.setdefault('extra_edges', [])
    edge_record = cast(
        ExtraEdgeRecord,
        {
            'id': edge_id,
            'kind': kind,
            'from_endpoint': first_endpoint,
            'to_endpoint': second_endpoint,
            'bidirectional': bidirectional,
            'path_points': [],
            **({'label': normalized_label} if normalized_label is not None else {}),
        },
    )
    payload['extra_edges'].append(edge_record)
    _sync_alignment_reminder_for_edge_record(payload, edge_record)
    _normalize_extra_edges(payload)
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def set_extra_edge_path_points(
    edge_id: str,
    path_points: Sequence[tuple[int, int]],
) -> None:
    payload = _load_network_payload()
    edge_record = _find_extra_edge_record(payload, edge_id)

    normalized_points: list[PathPointRecord] = []
    previous_coordinates: tuple[int, int] | None = None
    for raw_x, raw_y in path_points:
        coordinates = (int(raw_x), int(raw_y))
        if coordinates == previous_coordinates:
            continue
        previous_coordinates = coordinates
        normalized_points.append({'x': coordinates[0], 'y': coordinates[1]})

    edge_record['path_points'] = normalized_points
    _normalize_extra_edges(payload)
    edge_record = _find_extra_edge_record(payload, edge_id)
    _sync_alignment_reminder_for_edge_record(payload, edge_record)
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def set_extra_edge_label(edge_id: str, label: str | None) -> None:
    payload = _load_network_payload()
    edge_record = _find_extra_edge_record(payload, edge_id)
    normalized_label = None if label is None else (label.strip() or None)
    if normalized_label is None:
        edge_record.pop('label', None)
    else:
        edge_record['label'] = normalized_label
    _normalize_extra_edges(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def make_extra_edge_direct(edge_id: str) -> None:
    payload = _load_network_payload()
    edge_record = _find_extra_edge_record(payload, edge_id)
    edge_record['path_points'] = []
    _sync_alignment_reminder_for_edge_record(payload, edge_record)
    _normalize_extra_edges(payload)
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def add_turn_to_extra_edge(edge_id: str) -> None:
    payload = _load_network_payload()
    edge_record = _find_extra_edge_record(payload, edge_id)
    from_endpoint = _required_extra_edge_endpoint(edge_record, 'from_endpoint')
    to_endpoint = _required_extra_edge_endpoint(edge_record, 'to_endpoint')
    first_coordinates = _payload_endpoint_coordinates(payload, from_endpoint)
    second_coordinates = _payload_endpoint_coordinates(payload, to_endpoint)
    if first_coordinates[0] == second_coordinates[0] or first_coordinates[1] == second_coordinates[1]:
        raise ValueError('This segment is already axis-aligned, so there is no turn to add.')
    if edge_record.get('path_points'):
        raise ValueError('This segment already has a turn. Use Flip Turn or Direct instead.')

    edge_record['path_points'] = _turn_path_points(
        first_coordinates,
        second_coordinates,
        variant=0,
    )
    _sync_alignment_reminder_for_edge_record(payload, edge_record)
    _normalize_extra_edges(payload)
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def flip_extra_edge_turn(edge_id: str) -> None:
    payload = _load_network_payload()
    edge_record = _find_extra_edge_record(payload, edge_id)
    from_endpoint = _required_extra_edge_endpoint(edge_record, 'from_endpoint')
    to_endpoint = _required_extra_edge_endpoint(edge_record, 'to_endpoint')
    first_coordinates = _payload_endpoint_coordinates(payload, from_endpoint)
    second_coordinates = _payload_endpoint_coordinates(payload, to_endpoint)
    current_variant = _extra_edge_turn_variant_from_points(
        tuple(
            (int(point['x']), int(point['y']))
            for point in cast(list[PathPointRecord], edge_record.get('path_points', []))
        ),
        from_coordinates=first_coordinates,
        to_coordinates=second_coordinates,
    )
    if current_variant is None:
        raise ValueError('This segment does not have a simple turn to flip.')

    edge_record['path_points'] = _turn_path_points(
        first_coordinates,
        second_coordinates,
        variant=1 - current_variant,
    )
    _sync_alignment_reminder_for_edge_record(payload, edge_record)
    _normalize_extra_edges(payload)
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def remove_extra_edge(edge_id: str) -> None:
    payload = _load_network_payload()
    edge_record = _find_extra_edge_record(payload, edge_id)
    _remove_alignment_reminder_for_edge_record(payload, edge_record)
    extra_edges = payload.get('extra_edges', [])
    filtered_edges = [
        extra_edge
        for extra_edge in extra_edges
        if str(extra_edge.get('id', '')).strip() != edge_id
    ]
    payload['extra_edges'] = filtered_edges
    _normalize_extra_edges(payload)
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def add_alignment_reminder(
    first_station: str,
    second_station: str,
    axis: AlignmentAxisInput = 'auto',
) -> None:
    payload = _load_network_payload()
    first_var = _resolve_stop_var_in_payload(payload, first_station)
    second_var = _resolve_stop_var_in_payload(payload, second_station)
    if first_var is None:
        raise ValueError(f'Unknown station: {first_station}')
    if second_var is None:
        raise ValueError(f'Unknown station: {second_station}')
    if first_var == second_var:
        raise ValueError('Alignment reminders need two different stations.')

    stop_lookup = {
        str(stop_record['var']): stop_record
        for stop_record in payload['stops']
    }
    first_record = stop_lookup[first_var]
    second_record = stop_lookup[second_var]
    resolved_axis: AlignmentAxis
    if axis == 'auto':
        resolved_axis = _infer_alignment_axis_from_coordinates(
            int(first_record['x']),
            int(first_record['y']),
            int(second_record['x']),
            int(second_record['y']),
        )
    else:
        resolved_axis = axis

    if resolved_axis == 'x' and int(first_record['x']) == int(second_record['x']):
        _normalize_alignment_reminders(payload)
        _write_network_payload(payload)
        _apply_network_payload(payload)
        return
    if resolved_axis == 'y' and int(first_record['y']) == int(second_record['y']):
        _normalize_alignment_reminders(payload)
        _write_network_payload(payload)
        _apply_network_payload(payload)
        return

    payload.setdefault('alignment_reminders', [])
    payload['alignment_reminders'].append(
        {
            'first_var': first_var,
            'second_var': second_var,
            'axis': resolved_axis,
        }
    )
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def remove_alignment_reminder(
    first_station: str,
    second_station: str,
    axis: AlignmentAxis | None = None,
) -> None:
    payload = _load_network_payload()
    first_var = _resolve_stop_var_in_payload(payload, first_station)
    second_var = _resolve_stop_var_in_payload(payload, second_station)
    if first_var is None:
        raise ValueError(f'Unknown station: {first_station}')
    if second_var is None:
        raise ValueError(f'Unknown station: {second_station}')

    ordered_first_var, ordered_second_var = sorted((first_var, second_var))
    alignment_reminders = payload.get('alignment_reminders', [])
    filtered_reminders = [
        reminder
        for reminder in alignment_reminders
        if not (
            str(reminder.get('first_var')) == ordered_first_var
            and str(reminder.get('second_var')) == ordered_second_var
            and (axis is None or str(reminder.get('axis')) == axis)
        )
    ]
    payload['alignment_reminders'] = filtered_reminders
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)


def clear_alignment_reminders_for_stop(station: str) -> None:
    payload = _load_network_payload()
    stop_var = _resolve_stop_var_in_payload(payload, station)
    if stop_var is None:
        raise ValueError(f'Unknown station: {station}')

    alignment_reminders = payload.get('alignment_reminders', [])
    filtered_reminders = [
        reminder
        for reminder in alignment_reminders
        if stop_var not in (
            str(reminder.get('first_var')),
            str(reminder.get('second_var')),
        )
    ]
    if len(filtered_reminders) == len(alignment_reminders):
        return

    payload['alignment_reminders'] = filtered_reminders
    _normalize_alignment_reminders(payload)
    _write_network_payload(payload)
    _apply_network_payload(payload)

_reload_network_data()


if __name__ == '__main__':
    main()
