from __future__ import annotations

MINECART_SPEED_MPS: float = 8.0


def format_track_distance(distance_meters: int) -> str:
    if distance_meters < 1000:
        return f"{distance_meters:,} m"
    distance_km = distance_meters / 1000
    formatted_km = f"{distance_km:,.1f}".rstrip("0").rstrip(".")
    return f"{formatted_km} km"


def travel_time_seconds(distance_meters: int | float) -> int:
    return max(0, round(float(distance_meters) / MINECART_SPEED_MPS))


def format_travel_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes < 60:
        if remaining_seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {remaining_seconds}s"
    hours, remaining_minutes = divmod(minutes, 60)
    if remaining_minutes == 0:
        return f"{hours}h"
    return f"{hours}h {remaining_minutes}m"


def format_travel_time_for_distance(distance_meters: int | float) -> str:
    return format_travel_time(travel_time_seconds(distance_meters))


def format_distance_and_time(distance_meters: int | float) -> str:
    rounded_distance = round(float(distance_meters))
    return (
        f"{format_track_distance(rounded_distance)} / "
        f"{format_travel_time_for_distance(rounded_distance)}"
    )
