from __future__ import annotations

from math import dist
from typing import Sequence


def polyline_distance(points: Sequence[tuple[int, int]]) -> int:
    return sum(round(dist(start_point, end_point)) for start_point, end_point in zip(points, points[1:]))


def polyline_distance_float(points: Sequence[tuple[float, float]]) -> float:
    return sum(dist(start_point, end_point) for start_point, end_point in zip(points, points[1:]))


def point_to_segment_distance_sq(
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


def point_to_polyline_distance_sq(
    point: tuple[float, float],
    polyline_points: Sequence[tuple[float, float]],
) -> float | None:
    if len(polyline_points) < 2:
        return None

    best_distance_sq: float | None = None
    for start_point, end_point in zip(polyline_points, polyline_points[1:]):
        distance_sq = point_to_segment_distance_sq(point, start_point, end_point)
        if best_distance_sq is None or distance_sq < best_distance_sq:
            best_distance_sq = distance_sq
    return best_distance_sq


def polyline_midpoint(points: Sequence[tuple[float, float]]) -> tuple[float, float]:
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


def cumulative_distances(points: Sequence[tuple[float, float]]) -> tuple[float, ...]:
    values = [0.0]
    for start_point, end_point in zip(points, points[1:]):
        values.append(values[-1] + dist(start_point, end_point))
    return tuple(values)
