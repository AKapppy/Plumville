from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Sequence


JsonObject = dict[str, Any]


def coordinate_endpoint_key(x: int, y: int) -> str:
    return f"coord:{x},{y}"


def parse_coordinate_text(text: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?", text.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def coerce_int(value: object) -> int | None:
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


def normalized_ordered_values(values: object, valid_values: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(values, list | tuple | set | frozenset):
        return ()

    valid_value_set = set(valid_values)
    seen_values: set[str] = set()
    for value in values:
        normalized_value = str(value).strip().lower()
        if normalized_value not in valid_value_set:
            continue
        seen_values.add(normalized_value)

    return tuple(value for value in valid_values if value in seen_values)


def normalize_stop_metadata(
    payload: JsonObject,
    *,
    checkpoint_fields: Sequence[str],
    chime_directions: Sequence[str],
) -> bool:
    payload_changed = False
    raw_stops = payload.get("stops")
    if not isinstance(raw_stops, list):
        return False

    for raw_stop_record in raw_stops:
        if not isinstance(raw_stop_record, dict):
            continue
        stop_record = raw_stop_record
        for field_name in checkpoint_fields:
            raw_checkpoint_value = stop_record.get(field_name, False)
            normalized_value = bool(raw_checkpoint_value)
            if raw_checkpoint_value != normalized_value or field_name not in stop_record:
                stop_record[field_name] = normalized_value
                payload_changed = True

        station_entry_x = coerce_int(stop_record.get("station_entry_x"))
        station_entry_y = coerce_int(stop_record.get("station_entry_y"))
        if station_entry_x is None or station_entry_y is None:
            if "station_entry_x" in stop_record or "station_entry_y" in stop_record:
                stop_record.pop("station_entry_x", None)
                stop_record.pop("station_entry_y", None)
                payload_changed = True
        else:
            if stop_record.get("station_entry_x") != station_entry_x:
                stop_record["station_entry_x"] = station_entry_x
                payload_changed = True
            if stop_record.get("station_entry_y") != station_entry_y:
                stop_record["station_entry_y"] = station_entry_y
                payload_changed = True

        normalized_chime_directions = list(
            normalized_ordered_values(stop_record.get("chime_directions", []), chime_directions)
        )
        if stop_record.get("chime_directions") != normalized_chime_directions:
            stop_record["chime_directions"] = normalized_chime_directions
            payload_changed = True

    return payload_changed


def line_finish_origin_options(payload: JsonObject, line_name: str) -> tuple[str, ...]:
    raw_stops = payload.get("stops", [])
    raw_line_stop_vars = payload.get("line_stop_vars", {})
    if not isinstance(raw_stops, list) or not isinstance(raw_line_stop_vars, dict):
        return ()

    connected_stop_keys = {
        str(stop_record["var"])
        for stop_record in raw_stops
        if isinstance(stop_record, dict)
        and "var" in stop_record
        and bool(stop_record.get("is_connected", False))
    }
    raw_stop_vars = raw_line_stop_vars.get(line_name, [])
    if not isinstance(raw_stop_vars, list | tuple):
        return ()
    connected_line_stop_keys = tuple(
        str(stop_key)
        for stop_key in raw_stop_vars
        if str(stop_key) in connected_stop_keys
    )
    if not connected_line_stop_keys:
        return ()
    if len(connected_line_stop_keys) == 1:
        return (connected_line_stop_keys[0],)
    return (connected_line_stop_keys[0], connected_line_stop_keys[-1])


def normalize_railway_finish_progress(payload: JsonObject) -> bool:
    payload_changed = False
    had_progress_key = "railway_finish_progress" in payload
    raw_progress = payload.get("railway_finish_progress")
    if not isinstance(raw_progress, dict):
        payload["railway_finish_progress"] = {}
        return had_progress_key

    raw_line_stop_vars = payload.get("line_stop_vars", {})
    valid_line_names = {str(line_name) for line_name in raw_line_stop_vars} if isinstance(raw_line_stop_vars, dict) else set()
    normalized_progress: dict[str, JsonObject] = {}
    for raw_line_name, raw_point in raw_progress.items():
        line_name = str(raw_line_name)
        if line_name not in valid_line_names or not isinstance(raw_point, dict):
            payload_changed = True
            continue

        point_x = coerce_int(raw_point.get("x"))
        point_y = coerce_int(raw_point.get("y"))
        if point_x is None or point_y is None:
            payload_changed = True
            continue
        normalized_progress[line_name] = {"x": point_x, "y": point_y}

    if raw_progress != normalized_progress:
        payload["railway_finish_progress"] = normalized_progress
        payload_changed = True

    return payload_changed


def normalize_railway_finish_origins(payload: JsonObject) -> bool:
    payload_changed = False
    had_origins_key = "railway_finish_origins" in payload
    raw_origins = payload.get("railway_finish_origins")
    if not isinstance(raw_origins, dict):
        payload["railway_finish_origins"] = {}
        return had_origins_key

    raw_line_stop_vars = payload.get("line_stop_vars", {})
    valid_line_names = {str(line_name) for line_name in raw_line_stop_vars} if isinstance(raw_line_stop_vars, dict) else set()
    normalized_origins: dict[str, str] = {}
    for raw_line_name, raw_stop_key in raw_origins.items():
        line_name = str(raw_line_name)
        stop_key = str(raw_stop_key)
        if line_name not in valid_line_names:
            payload_changed = True
            continue
        if stop_key not in line_finish_origin_options(payload, line_name):
            payload_changed = True
            continue
        normalized_origins[line_name] = stop_key

    if raw_origins != normalized_origins:
        payload["railway_finish_origins"] = normalized_origins
        payload_changed = True

    return payload_changed


def normalize_path_nodes(payload: JsonObject) -> bool:
    payload_changed = False
    raw_path_nodes = payload.get("path_nodes")
    if not isinstance(raw_path_nodes, list):
        payload["path_nodes"] = []
        return True

    raw_stops = payload.get("stops", [])
    stop_coordinates = {
        (int(stop_record["x"]), int(stop_record["y"]))
        for stop_record in raw_stops
        if isinstance(stop_record, dict)
        and "x" in stop_record
        and "y" in stop_record
    }
    normalized_nodes: list[JsonObject] = []
    seen_ids: set[str] = set()
    seen_coordinates: set[tuple[int, int]] = set()

    for index, raw_node in enumerate(raw_path_nodes, start=1):
        if not isinstance(raw_node, dict):
            payload_changed = True
            continue

        node_x = coerce_int(raw_node.get("x"))
        node_y = coerce_int(raw_node.get("y"))
        if node_x is None or node_y is None:
            payload_changed = True
            continue

        coordinates = (node_x, node_y)
        if coordinates in stop_coordinates or coordinates in seen_coordinates:
            payload_changed = True
            continue

        node_id = str(raw_node.get("id", "")).strip() or f"node_{index}"
        if node_id in seen_ids:
            node_id = f"{node_id}_{index}"
            payload_changed = True

        normalized_node: JsonObject = {
            "id": node_id,
            "x": node_x,
            "y": node_y,
        }
        label = str(raw_node.get("label", "")).strip()
        if label:
            normalized_node["label"] = label
        poi_kind = str(raw_node.get("poi_kind", "")).strip().lower()
        if poi_kind in {"monument", "pillager_tower"}:
            normalized_node["poi_kind"] = poi_kind
            category = str(raw_node.get("category", "")).strip()
            if category:
                normalized_node["category"] = category

        if raw_node != normalized_node:
            payload_changed = True
        normalized_nodes.append(normalized_node)
        seen_ids.add(node_id)
        seen_coordinates.add(coordinates)

    if raw_path_nodes != normalized_nodes:
        payload["path_nodes"] = normalized_nodes
        payload_changed = True

    return payload_changed


def resolve_stop_key(payload: JsonObject, identifier: str) -> str | None:
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return None

    raw_stops = payload.get("stops", [])
    if not isinstance(raw_stops, list):
        return None

    stop_keys = {
        str(stop_record["var"]): str(stop_record["var"])
        for stop_record in raw_stops
        if isinstance(stop_record, dict) and "var" in stop_record
    }
    if normalized_identifier in stop_keys:
        return stop_keys[normalized_identifier]

    labels = {
        str(stop_record["lbl"]): str(stop_record["var"])
        for stop_record in raw_stops
        if isinstance(stop_record, dict) and "var" in stop_record and "lbl" in stop_record
    }
    return labels.get(normalized_identifier)


def resolve_path_node(payload: JsonObject, identifier: str) -> JsonObject | None:
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return None

    raw_path_nodes = payload.get("path_nodes", [])
    if not isinstance(raw_path_nodes, list):
        return None

    for raw_path_node in raw_path_nodes:
        if not isinstance(raw_path_node, dict):
            continue
        if str(raw_path_node.get("id", "")).strip() == normalized_identifier:
            return raw_path_node
        if str(raw_path_node.get("label", "")).strip() == normalized_identifier:
            return raw_path_node
    return None


def path_endpoint_record_from_identifier(
    payload: JsonObject,
    identifier: str,
) -> JsonObject | None:
    stop_key = resolve_stop_key(payload, identifier)
    if stop_key is not None:
        return {"kind": "stop", "stop_var": stop_key}

    path_node = resolve_path_node(payload, identifier)
    if path_node is not None:
        return {
            "kind": "coord",
            "x": int(path_node["x"]),
            "y": int(path_node["y"]),
        }

    coordinates = parse_coordinate_text(identifier)
    if coordinates is None:
        return None
    return {"kind": "coord", "x": coordinates[0], "y": coordinates[1]}


def normalize_path_endpoint_record(
    payload: JsonObject,
    raw_endpoint: object,
    *,
    fallback_identifier: str | None = None,
) -> JsonObject | None:
    if isinstance(raw_endpoint, dict):
        raw_kind = str(raw_endpoint.get("kind", "")).strip().lower()
        if raw_kind == "stop":
            stop_key = resolve_stop_key(payload, str(raw_endpoint.get("stop_var", "")))
            if stop_key is not None:
                return {"kind": "stop", "stop_var": stop_key}
            return None
        if raw_kind in {"coord", "coordinate"}:
            endpoint_x = coerce_int(raw_endpoint.get("x"))
            endpoint_y = coerce_int(raw_endpoint.get("y"))
            if endpoint_x is None or endpoint_y is None:
                return None
            return {
                "kind": "coord",
                "x": endpoint_x,
                "y": endpoint_y,
            }

    if fallback_identifier is None:
        return None
    return path_endpoint_record_from_identifier(payload, fallback_identifier)


def payload_endpoint_coordinates(
    payload: JsonObject,
    endpoint_record: JsonObject,
) -> tuple[int, int]:
    if endpoint_record["kind"] == "stop":
        stop_lookup = {
            str(stop_record["var"]): stop_record
            for stop_record in payload.get("stops", [])
            if isinstance(stop_record, dict) and "var" in stop_record
        }
        stop_record = stop_lookup[str(endpoint_record["stop_var"])]
        station_entry_x = coerce_int(stop_record.get("station_entry_x"))
        station_entry_y = coerce_int(stop_record.get("station_entry_y"))
        if station_entry_x is not None and station_entry_y is not None:
            return (station_entry_x, station_entry_y)
        return (int(stop_record["x"]), int(stop_record["y"]))

    return (int(endpoint_record["x"]), int(endpoint_record["y"]))


def normalize_extra_edges(payload: JsonObject) -> bool:
    payload_changed = False
    raw_extra_edges = payload.get("extra_edges")
    if not isinstance(raw_extra_edges, list):
        payload["extra_edges"] = []
        return True

    normalized_edges: list[JsonObject] = []
    seen_ids: set[str] = set()

    for index, raw_edge in enumerate(raw_extra_edges, start=1):
        if not isinstance(raw_edge, dict):
            payload_changed = True
            continue

        edge_id = str(raw_edge.get("id", "")).strip() or f"edge_{index}"
        if edge_id in seen_ids:
            edge_id = f"{edge_id}_{index}"
            payload_changed = True
        seen_ids.add(edge_id)

        kind_value = str(raw_edge.get("kind", "connector")).strip().lower()
        if kind_value not in {"connector", "walk"}:
            kind_value = "connector"
            payload_changed = True

        from_endpoint = normalize_path_endpoint_record(
            payload,
            raw_edge.get("from_endpoint"),
            fallback_identifier=str(raw_edge.get("from_var", "")),
        )
        to_endpoint = normalize_path_endpoint_record(
            payload,
            raw_edge.get("to_endpoint"),
            fallback_identifier=str(raw_edge.get("to_var", "")),
        )
        if from_endpoint is None or to_endpoint is None:
            payload_changed = True
            continue
        if from_endpoint == to_endpoint:
            payload_changed = True
            continue

        bidirectional = bool(raw_edge.get("bidirectional", True))
        normalized_path_points: list[JsonObject] = []
        raw_path_points = raw_edge.get("path_points", [])
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
                            "x": int(raw_point.get("x")),
                            "y": int(raw_point.get("y")),
                        }
                    )
                except (TypeError, ValueError):
                    payload_changed = True
        else:
            raw_path_specs = raw_edge.get("path_specs", [])
            if not isinstance(raw_path_specs, list):
                raw_path_specs = []
                payload_changed = True
            for raw_spec in raw_path_specs:
                if not isinstance(raw_spec, dict):
                    payload_changed = True
                    continue
                x_var = resolve_stop_key(payload, str(raw_spec.get("x_var", "")))
                y_var = resolve_stop_key(payload, str(raw_spec.get("y_var", "")))
                if x_var is None or y_var is None:
                    payload_changed = True
                    continue
                try:
                    point_x = int(next(
                        stop_record["x"]
                        for stop_record in payload["stops"]
                        if str(stop_record["var"]) == x_var
                    )) + int(raw_spec.get("dx", 0))
                    point_y = int(next(
                        stop_record["y"]
                        for stop_record in payload["stops"]
                        if str(stop_record["var"]) == y_var
                    )) - int(raw_spec.get("dy", 0))
                except (StopIteration, TypeError, ValueError):
                    payload_changed = True
                    continue
                normalized_path_points.append({"x": point_x, "y": point_y})

        if normalized_path_points:
            start_coordinates = payload_endpoint_coordinates(payload, from_endpoint)
            end_coordinates = payload_endpoint_coordinates(payload, to_endpoint)
            if (normalized_path_points[0]["x"], normalized_path_points[0]["y"]) != start_coordinates:
                normalized_path_points.insert(
                    0,
                    {"x": start_coordinates[0], "y": start_coordinates[1]},
                )
                payload_changed = True
            if (normalized_path_points[-1]["x"], normalized_path_points[-1]["y"]) != end_coordinates:
                normalized_path_points.append(
                    {"x": end_coordinates[0], "y": end_coordinates[1]},
                )
                payload_changed = True
            if len(normalized_path_points) == 2 and (
                (normalized_path_points[0]["x"], normalized_path_points[0]["y"]) == start_coordinates
                and (normalized_path_points[1]["x"], normalized_path_points[1]["y"]) == end_coordinates
            ):
                normalized_path_points = []
                payload_changed = True

        normalized_edge: JsonObject = {
            "id": edge_id,
            "kind": kind_value,
            "from_endpoint": from_endpoint,
            "to_endpoint": to_endpoint,
            "bidirectional": bidirectional,
            "path_points": normalized_path_points,
        }

        label = str(raw_edge.get("label", "")).strip()
        if label:
            normalized_edge["label"] = label

        raw_distance = raw_edge.get("distance")
        if raw_distance not in (None, ""):
            normalized_edge["distance"] = int(raw_distance)

        if raw_edge != normalized_edge:
            payload_changed = True
        normalized_edges.append(normalized_edge)

    if raw_extra_edges != normalized_edges:
        payload["extra_edges"] = normalized_edges
        payload_changed = True

    return payload_changed


def path_node_keys(payload: JsonObject) -> set[str]:
    node_keys: set[str] = set()
    for raw_node in payload.get("path_nodes", []):
        if not isinstance(raw_node, dict):
            continue
        node_x = coerce_int(raw_node.get("x"))
        node_y = coerce_int(raw_node.get("y"))
        if node_x is None or node_y is None:
            continue
        node_keys.add(coordinate_endpoint_key(node_x, node_y))

    for raw_edge in payload.get("extra_edges", []):
        if not isinstance(raw_edge, dict):
            continue
        for field_name in ("from_endpoint", "to_endpoint"):
            raw_endpoint = raw_edge.get(field_name)
            if not isinstance(raw_endpoint, dict):
                continue
            endpoint = normalize_path_endpoint_record(payload, raw_endpoint)
            if endpoint is None or endpoint["kind"] != "coord":
                continue
            node_keys.add(coordinate_endpoint_key(int(endpoint["x"]), int(endpoint["y"])))
    return node_keys


def normalize_city_limits(payload: JsonObject) -> bool:
    payload_changed = False
    valid_node_keys = path_node_keys(payload)
    raw_stops = payload.get("stops", [])
    if not isinstance(raw_stops, list):
        return False

    for raw_stop_record in raw_stops:
        if not isinstance(raw_stop_record, dict):
            continue
        raw_node_keys = raw_stop_record.get("city_limit_node_keys")
        if raw_node_keys is None:
            continue
        if not isinstance(raw_node_keys, list):
            raw_stop_record.pop("city_limit_node_keys", None)
            payload_changed = True
            continue

        normalized_node_keys: list[str] = []
        seen_node_keys: set[str] = set()
        for raw_node_key in raw_node_keys:
            node_key = str(raw_node_key).strip()
            if node_key not in valid_node_keys:
                coordinates = parse_coordinate_text(node_key)
                if coordinates is not None:
                    node_key = coordinate_endpoint_key(coordinates[0], coordinates[1])
            if node_key not in valid_node_keys or node_key in seen_node_keys:
                payload_changed = True
                continue
            normalized_node_keys.append(node_key)
            seen_node_keys.add(node_key)

        if normalized_node_keys:
            if raw_node_keys != normalized_node_keys:
                raw_stop_record["city_limit_node_keys"] = normalized_node_keys
                payload_changed = True
        else:
            raw_stop_record.pop("city_limit_node_keys", None)
            payload_changed = True

    return payload_changed


def infer_alignment_axis(
    first_x: int,
    first_y: int,
    second_x: int,
    second_y: int,
) -> str:
    if first_x == second_x and first_y != second_y:
        return "x"
    if first_y == second_y and first_x != second_x:
        return "y"
    return "x" if abs(first_x - second_x) <= abs(first_y - second_y) else "y"


def normalize_alignment_reminders(payload: JsonObject) -> bool:
    payload_changed = False
    raw_alignment_reminders = payload.get("alignment_reminders")
    if not isinstance(raw_alignment_reminders, list):
        payload["alignment_reminders"] = []
        return True

    stop_lookup = {
        str(stop_record["var"]): stop_record
        for stop_record in payload.get("stops", [])
        if isinstance(stop_record, dict) and "var" in stop_record
    }
    normalized_reminders: list[JsonObject] = []
    seen_pairs: set[tuple[str, str, str]] = set()

    for raw_reminder in raw_alignment_reminders:
        if not isinstance(raw_reminder, dict):
            payload_changed = True
            continue

        first_var = resolve_stop_key(payload, str(raw_reminder.get("first_var", "")))
        second_var = resolve_stop_key(payload, str(raw_reminder.get("second_var", "")))
        if first_var is None or second_var is None or first_var == second_var:
            payload_changed = True
            continue

        first_record = stop_lookup[first_var]
        second_record = stop_lookup[second_var]
        raw_axis = str(raw_reminder.get("axis", "auto")).strip().lower()
        if raw_axis in ("x", "y"):
            axis = raw_axis
        else:
            axis = infer_alignment_axis(
                int(first_record["x"]),
                int(first_record["y"]),
                int(second_record["x"]),
                int(second_record["y"]),
            )
            payload_changed = True

        if axis == "x":
            is_aligned = int(first_record["x"]) == int(second_record["x"])
        else:
            is_aligned = int(first_record["y"]) == int(second_record["y"])
        if is_aligned:
            payload_changed = True
            continue

        ordered_first_var, ordered_second_var = sorted((first_var, second_var))
        pair_key = (ordered_first_var, ordered_second_var, axis)
        if pair_key in seen_pairs:
            payload_changed = True
            continue
        seen_pairs.add(pair_key)

        normalized_reminder: JsonObject = {
            "first_var": ordered_first_var,
            "second_var": ordered_second_var,
            "axis": axis,
        }
        normalized_reminders.append(normalized_reminder)
        if raw_reminder != normalized_reminder:
            payload_changed = True

    if raw_alignment_reminders != normalized_reminders:
        payload["alignment_reminders"] = normalized_reminders
        payload_changed = True

    return payload_changed


def line_colors_from_payload(payload: JsonObject) -> dict[str, str]:
    raw_line_colors = payload.get("line_colors", {})
    if not isinstance(raw_line_colors, dict):
        return {}
    return {
        str(line_name): str(color)
        for line_name, color in raw_line_colors.items()
    }


def wool_colors_from_payload(payload: JsonObject) -> dict[str, str]:
    raw_wool_colors = payload.get("wool_colors", {})
    if not isinstance(raw_wool_colors, dict):
        return {}
    return {
        str(line_name): str(color_name)
        for line_name, color_name in raw_wool_colors.items()
    }


def line_stop_vars_from_payload(payload: JsonObject) -> dict[str, tuple[str, ...]]:
    raw_line_stop_vars = payload.get("line_stop_vars", {})
    if not isinstance(raw_line_stop_vars, dict):
        return {}
    return {
        str(line_name): tuple(str(stop_key) for stop_key in stop_keys)
        for line_name, stop_keys in raw_line_stop_vars.items()
        if isinstance(stop_keys, list | tuple)
    }


def stop_line_names(
    stop_keys: Sequence[str],
    line_stop_vars: dict[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    return {
        stop_key: tuple(
            line_name
            for line_name, candidate_stop_keys in line_stop_vars.items()
            if stop_key in candidate_stop_keys
        )
        for stop_key in stop_keys
    }


def railway_finish_progress_from_payload(
    payload: JsonObject,
    line_stop_vars: dict[str, tuple[str, ...]],
) -> dict[str, JsonObject]:
    raw_progress = payload.get("railway_finish_progress", {})
    if not isinstance(raw_progress, dict):
        return {}
    return {
        str(line_name): {
            "x": int(point["x"]),
            "y": int(point["y"]),
        }
        for line_name, point in raw_progress.items()
        if str(line_name) in line_stop_vars and isinstance(point, dict)
    }


def railway_finish_origins_from_payload(
    payload: JsonObject,
    line_stop_vars: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    raw_origins = payload.get("railway_finish_origins", {})
    if not isinstance(raw_origins, dict):
        return {}
    return {
        str(line_name): str(stop_key)
        for line_name, stop_key in raw_origins.items()
        if str(line_name) in line_stop_vars
        and str(stop_key) in line_stop_vars[str(line_name)]
    }


def line_path_spec_records_from_payload(payload: JsonObject) -> dict[str, tuple[JsonObject, ...]]:
    raw_line_path_specs = payload.get("line_path_specs", {})
    if not isinstance(raw_line_path_specs, dict):
        return {}
    return {
        str(line_name): tuple(
            {
                "x_var": str(spec["x_var"]),
                "y_var": str(spec["y_var"]),
                "dx": int(spec.get("dx", 0)),
                "dy": int(spec.get("dy", 0)),
            }
            for spec in specs
            if isinstance(spec, dict)
        )
        for line_name, specs in raw_line_path_specs.items()
        if isinstance(specs, list | tuple)
    }


def line_path_plot_paths_from_specs(
    line_path_specs: dict[str, tuple[JsonObject, ...]],
    stop_coordinates: dict[str, tuple[int, int]],
) -> dict[str, tuple[tuple[int, int], ...]]:
    return {
        line_name: tuple(
            (
                stop_coordinates[str(spec["x_var"])][0] + int(spec.get("dx", 0)),
                -stop_coordinates[str(spec["y_var"])][1] + int(spec.get("dy", 0)),
            )
            for spec in specs
        )
        for line_name, specs in line_path_specs.items()
    }


def line_path_coordinate_paths_from_plot_paths(
    line_plot_paths: dict[str, tuple[tuple[int, int], ...]],
) -> dict[str, tuple[tuple[int, int], ...]]:
    return {
        line_name: tuple((point_x, -point_y) for point_x, point_y in plot_path)
        for line_name, plot_path in line_plot_paths.items()
    }


def path_node_records_from_payload(payload: JsonObject) -> tuple[JsonObject, ...]:
    raw_path_nodes = payload.get("path_nodes", [])
    if not isinstance(raw_path_nodes, list):
        return ()
    return tuple(
        {
            "id": str(path_node_record["id"]),
            "x": int(path_node_record["x"]),
            "y": int(path_node_record["y"]),
            **(
                {"label": str(path_node_record["label"])}
                if "label" in path_node_record and str(path_node_record["label"]).strip()
                else {}
            ),
            **(
                {"poi_kind": str(path_node_record["poi_kind"])}
                if str(path_node_record.get("poi_kind", "")).strip().lower() in {"monument", "pillager_tower"}
                else {}
            ),
            **(
                {"category": str(path_node_record["category"])}
                if "category" in path_node_record and str(path_node_record["category"]).strip()
                else {}
            ),
        }
        for path_node_record in raw_path_nodes
        if isinstance(path_node_record, dict)
    )


def extra_edge_records_from_payload(payload: JsonObject) -> tuple[JsonObject, ...]:
    raw_extra_edges = payload.get("extra_edges", [])
    if not isinstance(raw_extra_edges, list):
        return ()
    return tuple(
        {
            "id": str(extra_edge_record["id"]),
            "kind": str(extra_edge_record["kind"]),
            "from_endpoint": extra_edge_record["from_endpoint"],
            "to_endpoint": extra_edge_record["to_endpoint"],
            "bidirectional": bool(extra_edge_record.get("bidirectional", True)),
            **(
                {"label": str(extra_edge_record["label"])}
                if "label" in extra_edge_record and str(extra_edge_record["label"]).strip()
                else {}
            ),
            **(
                {"distance": int(extra_edge_record["distance"])}
                if "distance" in extra_edge_record and extra_edge_record["distance"] is not None
                else {}
            ),
            "path_points": [
                {
                    "x": int(point["x"]),
                    "y": int(point["y"]),
                }
                for point in extra_edge_record.get("path_points", [])
                if isinstance(point, dict)
            ],
        }
        for extra_edge_record in raw_extra_edges
        if isinstance(extra_edge_record, dict)
    )


def alignment_reminder_records_from_payload(payload: JsonObject) -> tuple[JsonObject, ...]:
    raw_alignment_reminders = payload.get("alignment_reminders", [])
    if not isinstance(raw_alignment_reminders, list):
        return ()
    return tuple(
        {
            "first_var": str(reminder_record["first_var"]),
            "second_var": str(reminder_record["second_var"]),
            "axis": str(reminder_record["axis"]),
        }
        for reminder_record in raw_alignment_reminders
        if isinstance(reminder_record, dict)
    )


def line_letters(stop_key: str) -> tuple[str, ...]:
    return tuple(char for char in stop_key.removeprefix("P_") if char.isalpha())


def validate_line_sequences(
    stop_keys: Sequence[str],
    line_stop_vars: dict[str, tuple[str, ...]],
) -> None:
    expected_members: dict[str, set[str]] = {line_name: set() for line_name in line_stop_vars}

    for stop_key in stop_keys:
        for line_name in line_letters(stop_key):
            expected_members.setdefault(line_name, set()).add(stop_key)

    if set(expected_members) != set(line_stop_vars):
        raise ValueError("LINE_STOP_VARS does not match the lines encoded in the stop variables.")

    for line_name, stop_vars in line_stop_vars.items():
        if len(stop_vars) != len(set(stop_vars)):
            raise ValueError(f"Line {line_name} has duplicate stop entries.")
        if set(stop_vars) != expected_members[line_name]:
            raise ValueError(
                f"Line {line_name} sequence does not match the stop variables. "
                f"Expected {sorted(expected_members[line_name])}, got {sorted(stop_vars)}."
            )


def validate_line_path_specs(
    line_path_specs: dict[str, tuple[JsonObject, ...]],
    line_stop_vars: dict[str, tuple[str, ...]],
    stop_keys: set[str],
) -> None:
    if set(line_path_specs) != set(line_stop_vars):
        raise ValueError("LINE_PATH_SPECS does not match the defined metro lines.")

    for line_name, point_specs in line_path_specs.items():
        mentioned_vars = {str(spec["x_var"]) for spec in point_specs} | {str(spec["y_var"]) for spec in point_specs}
        missing_stops = set(line_stop_vars[line_name]) - mentioned_vars
        unknown_vars = mentioned_vars - stop_keys

        if unknown_vars:
            raise ValueError(f"Line {line_name} path references unknown stops: {sorted(unknown_vars)}.")
        if missing_stops:
            raise ValueError(f"Line {line_name} path is missing stops: {sorted(missing_stops)}.")
        if len(point_specs) < 2:
            raise ValueError(f"Line {line_name} path needs at least two points.")


def validate_line_colors(
    line_colors: dict[str, str],
    line_stop_vars: dict[str, tuple[str, ...]],
) -> None:
    if set(line_colors) != set(line_stop_vars):
        raise ValueError("LINE_COLORS does not match the defined metro lines.")


def validate_path_nodes(
    path_nodes: Sequence[JsonObject],
    stop_coordinates: set[tuple[int, int]],
) -> None:
    seen_ids: set[str] = set()
    seen_coordinates: set[tuple[int, int]] = set()

    for path_node in path_nodes:
        node_id = str(path_node["id"])
        coordinates = (int(path_node["x"]), int(path_node["y"]))
        if node_id in seen_ids:
            raise ValueError(f"Duplicate path node id: {node_id}")
        if coordinates in seen_coordinates:
            raise ValueError(f"Duplicate path node coordinates: {coordinates}")
        if coordinates in stop_coordinates:
            raise ValueError(f"Path node {node_id} overlaps a station coordinate.")
        seen_ids.add(node_id)
        seen_coordinates.add(coordinates)


def validate_extra_edges(
    extra_edges: Sequence[JsonObject],
    stop_keys: set[str],
) -> None:
    seen_ids: set[str] = set()
    for extra_edge in extra_edges:
        edge_id = str(extra_edge["id"])
        if edge_id in seen_ids:
            raise ValueError(f"Duplicate extra edge id: {edge_id}")
        seen_ids.add(edge_id)

        from_endpoint = extra_edge["from_endpoint"]
        to_endpoint = extra_edge["to_endpoint"]
        if from_endpoint["kind"] == "stop" and from_endpoint["key"] not in stop_keys:
            raise ValueError(f"Extra edge {edge_id} references unknown start stop.")
        if to_endpoint["kind"] == "stop" and to_endpoint["key"] not in stop_keys:
            raise ValueError(f"Extra edge {edge_id} references unknown end stop.")
        if from_endpoint["key"] == to_endpoint["key"]:
            raise ValueError(f"Extra edge {edge_id} needs two different endpoints.")

        path_points = extra_edge.get("path_points", ())
        if path_points:
            if path_points[0] != from_endpoint["coordinates"]:
                raise ValueError(f"Extra edge {edge_id} path must start at its first endpoint.")
            if path_points[-1] != to_endpoint["coordinates"]:
                raise ValueError(f"Extra edge {edge_id} path must end at its second endpoint.")


def validate_stop_line_names(
    stop_keys: Sequence[str],
    stop_line_names_by_stop: dict[str, tuple[str, ...]],
) -> None:
    for stop_key in stop_keys:
        if stop_key not in stop_line_names_by_stop:
            raise ValueError(f"Stop {stop_key} is missing line membership metadata.")


def validate_stop_records(
    stop_records: Sequence[JsonObject],
    *,
    unassociated_station_label: str,
) -> None:
    if len({str(stop["var"]) for stop in stop_records}) != len(stop_records):
        raise ValueError("Stop variables must be unique.")
    unique_required_labels = [
        str(stop["lbl"])
        for stop in stop_records
        if str(stop["lbl"]) != unassociated_station_label
    ]
    if len(set(unique_required_labels)) != len(unique_required_labels):
        raise ValueError("Stop labels must be unique.")
    for stop in stop_records:
        if not str(stop["lbl"]).strip():
            raise ValueError(f"Stop {stop['var']} must have a non-empty label.")


def serialize_network_payload(payload: JsonObject) -> str:
    return json.dumps(payload, indent=2) + "\n"


def history_snapshot_paths(history_dir: Path) -> list[Path]:
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob("*.json"))


def record_history_snapshot(
    snapshot_text: str,
    *,
    history_dir: Path,
    max_history_snapshots: int,
    now: Callable[[], datetime] = datetime.now,
) -> None:
    if not snapshot_text:
        return

    history_dir.mkdir(parents=True, exist_ok=True)
    latest_snapshot_paths = history_snapshot_paths(history_dir)
    if latest_snapshot_paths:
        latest_snapshot_text = latest_snapshot_paths[-1].read_text(encoding="utf-8")
        if latest_snapshot_text == snapshot_text:
            return

    snapshot_name = f"{now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    snapshot_path = history_dir / snapshot_name
    snapshot_path.write_text(snapshot_text, encoding="utf-8")

    all_history_paths = history_snapshot_paths(history_dir)
    if len(all_history_paths) <= max_history_snapshots:
        return
    for stale_path in all_history_paths[:-max_history_snapshots]:
        stale_path.unlink(missing_ok=True)


def write_network_payload(
    payload: JsonObject,
    *,
    network_path: Path,
    backup_path: Path,
    history_dir: Path,
    max_history_snapshots: int,
    now: Callable[[], datetime] = datetime.now,
) -> None:
    serialized_payload = serialize_network_payload(payload)
    current_payload_text = ""
    if network_path.exists():
        current_payload_text = network_path.read_text(encoding="utf-8")

    if current_payload_text and current_payload_text != serialized_payload:
        record_history_snapshot(
            current_payload_text,
            history_dir=history_dir,
            max_history_snapshots=max_history_snapshots,
            now=now,
        )
        backup_path.write_text(current_payload_text, encoding="utf-8")

    network_path.write_text(serialized_payload, encoding="utf-8")


def restore_last_network_snapshot(
    *,
    network_path: Path,
    backup_path: Path,
    history_dir: Path,
) -> None:
    current_payload_text = network_path.read_text(encoding="utf-8")
    snapshot_paths = history_snapshot_paths(history_dir)
    if snapshot_paths:
        restore_path = snapshot_paths[-1]
        restore_payload_text = restore_path.read_text(encoding="utf-8")
        restore_path.unlink(missing_ok=True)
        backup_path.write_text(current_payload_text, encoding="utf-8")
        network_path.write_text(restore_payload_text, encoding="utf-8")
        return

    if not backup_path.exists():
        raise ValueError("No previous saved network state is available yet.")

    backup_payload_text = backup_path.read_text(encoding="utf-8")
    network_path.write_text(backup_payload_text, encoding="utf-8")
    backup_path.write_text(current_payload_text, encoding="utf-8")
