from __future__ import annotations

import colorsys
import random
import re
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Sequence

import legacy_core as base


_APPLIED = False
_ORIGINAL_REDRAW = None
_ORIGINAL_DRAW_SELECTED_STOP_INFO = None
_LINE_COLOR_PALETTE = (
    '#e84f4f',
    '#34b96f',
    '#3f7fe8',
    '#e6c13a',
    '#b65edb',
    '#28bdb2',
    '#eb8f31',
    '#55c9e8',
    '#d84f92',
    '#75c943',
    '#8a72ec',
    '#e0df4a',
)


@dataclass(frozen=True, slots=True)
class AddedStation:
    label: str
    coordinates: tuple[int, int]
    stop_var: str


@dataclass(frozen=True, slots=True)
class MetroStationPreview:
    points: tuple[tuple[int, int], ...]
    color: str
    station_coordinates: tuple[int, int]
    station_label: str
    line_name: str


def _copy_anchor_spec(stop_var: str) -> base.LinePathSpecRecord:
    return {'x_var': stop_var, 'y_var': stop_var, 'dx': 0, 'dy': 0}


def _line_letters_for_var(stop_var: str) -> tuple[str, ...]:
    return tuple(char for char in stop_var.removeprefix('P_') if char.isalpha())


def _line_key(line_names: Sequence[str]) -> str:
    return ''.join(sorted(dict.fromkeys(line_names)))


def _station_var_for_lines(line_names: Sequence[str], *, suffix: str = '') -> str:
    clean_suffix = re.sub(r'[^0-9]', '', suffix)
    return f'P_{_line_key(line_names)}{clean_suffix}'


def _line_membership_by_stop(payload: base.MetroNetworkPayload) -> dict[str, tuple[str, ...]]:
    membership: dict[str, list[str]] = {}
    for line_name, stop_vars in payload['line_stop_vars'].items():
        for stop_var in stop_vars:
            membership.setdefault(str(stop_var), []).append(str(line_name))
    return {
        stop_var: tuple(sorted(line_names))
        for stop_var, line_names in membership.items()
    }


def _line_index_label(line_name: str, index: int) -> str:
    return f'{line_name}_{index}'


def _auto_station_label(
    stop_var: str,
    membership: dict[str, tuple[str, ...]],
    line_stop_vars: dict[str, list[str]],
) -> str:
    line_names = membership.get(stop_var, ())
    if len(line_names) != 1:
        line_key = ''.join(line_names)
        if not line_key:
            return stop_var.removeprefix('P_')
        matching_stop_vars = [
            candidate_var
            for candidate_var, candidate_line_names in membership.items()
            if candidate_line_names == line_names
        ]
        if len(matching_stop_vars) <= 1:
            return line_key
        suffix = ''.join(char for char in stop_var.removeprefix('P_') if not char.isalpha())
        return f'{line_key}_{suffix}' if suffix else f'{line_key}_{sorted(matching_stop_vars).index(stop_var) + 1}'
    line_name = line_names[0]
    try:
        line_index = [str(var) for var in line_stop_vars[line_name]].index(stop_var) + 1
    except (KeyError, ValueError):
        line_index = 1
    return _line_index_label(line_name, line_index)


def _renumber_placeholder_station_labels(payload: base.MetroNetworkPayload) -> None:
    membership = _line_membership_by_stop(payload)
    for stop_record in payload['stops']:
        current_label = str(stop_record.get('lbl', '')).strip()
        if not base._is_placeholder_station_label(current_label):
            continue
        stop_var = str(stop_record['var'])
        stop_record['lbl'] = _auto_station_label(stop_var, membership, payload['line_stop_vars'])


def _unique_station_var(
    payload: base.MetroNetworkPayload,
    line_names: Sequence[str],
    *,
    label_hint: str,
) -> str:
    existing_vars = {str(stop_record['var']) for stop_record in payload['stops']}
    suffix_match = re.search(r'(\d+)$', label_hint)
    suffix = suffix_match.group(1) if suffix_match else ''
    candidate = _station_var_for_lines(line_names, suffix=suffix)
    if candidate not in existing_vars:
        return candidate

    index = 2
    while True:
        candidate = _station_var_for_lines(line_names, suffix=str(index))
        if candidate not in existing_vars:
            return candidate
        index += 1


def _find_stop_var_at_coordinates(
    payload: base.MetroNetworkPayload,
    coordinates: tuple[int, int],
) -> str | None:
    for stop_record in payload['stops']:
        if (int(stop_record['x']), int(stop_record['y'])) == coordinates:
            return str(stop_record['var'])
    return None


def _rename_stop_var_in_payload(
    payload: base.MetroNetworkPayload,
    old_var: str,
    new_var: str,
) -> str:
    if old_var == new_var:
        return old_var
    if any(str(stop_record['var']) == new_var for stop_record in payload['stops']):
        index = 2
        base_candidate = new_var
        while any(str(stop_record['var']) == f'{base_candidate}{index}' for stop_record in payload['stops']):
            index += 1
        new_var = f'{base_candidate}{index}'

    for stop_record in payload['stops']:
        if str(stop_record['var']) == old_var:
            stop_record['var'] = new_var

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

    for edge in payload.get('extra_edges', []):
        for field_name in ('from_endpoint', 'to_endpoint'):
            endpoint = edge.get(field_name)
            if (
                isinstance(endpoint, dict)
                and endpoint.get('kind') == 'stop'
                and endpoint.get('stop_var') == old_var
            ):
                endpoint['stop_var'] = new_var

    for reminder in payload.get('alignment_reminders', []):
        if str(reminder.get('first_var')) == old_var:
            reminder['first_var'] = new_var
        if str(reminder.get('second_var')) == old_var:
            reminder['second_var'] = new_var

    origins = payload.get('railway_finish_origins')
    if isinstance(origins, dict):
        for line_name, stop_var in list(origins.items()):
            if str(stop_var) == old_var:
                origins[line_name] = new_var

    return new_var


def _var_with_added_lines(
    payload: base.MetroNetworkPayload,
    stop_var: str,
    added_line_names: Sequence[str],
) -> str:
    current_lines = set(_line_letters_for_var(stop_var))
    merged_lines = sorted(current_lines.union(str(line_name) for line_name in added_line_names))
    suffix = ''.join(char for char in stop_var.removeprefix('P_') if not char.isalpha())
    return _station_var_for_lines(merged_lines, suffix=suffix)


def _ensure_stop_on_lines(
    payload: base.MetroNetworkPayload,
    stop_var: str,
    line_names: Sequence[str],
) -> str:
    added_lines = [line_name for line_name in line_names if line_name not in _line_letters_for_var(stop_var)]
    if not added_lines:
        return stop_var
    return _rename_stop_var_in_payload(payload, stop_var, _var_with_added_lines(payload, stop_var, added_lines))


def _new_station_record(
    payload: base.MetroNetworkPayload,
    coordinates: tuple[int, int],
    line_names: Sequence[str],
    *,
    label_hint: str,
) -> str:
    stop_var = _unique_station_var(payload, line_names, label_hint=label_hint)
    payload['stops'].append(
        {
            'var': stop_var,
            'lbl': label_hint,
            'x': int(coordinates[0]),
            'y': int(coordinates[1]),
            'has_connector': False,
            'has_full_station': False,
            'has_walking_paths': False,
            'is_connected': False,
            'has_finished_railway': False,
            'has_signs': False,
            'chime_directions': [],
        }
    )
    return stop_var


def _anchor_indices(specs: list[base.LinePathSpecRecord]) -> dict[str, int]:
    anchors: dict[str, int] = {}
    for index, spec in enumerate(specs):
        x_var = str(spec['x_var'])
        y_var = str(spec['y_var'])
        if x_var == y_var:
            anchors.setdefault(x_var, index)
    return anchors


def _remove_station_from_line_specs(
    payload: base.MetroNetworkPayload,
    line_name: str,
    station_var: str,
) -> None:
    stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][line_name]]
    if station_var not in stop_vars:
        return
    specs = payload['line_path_specs'][line_name]
    anchors = _anchor_indices(specs)
    old_index = stop_vars.index(station_var)
    station_anchor = anchors.get(station_var)
    if station_anchor is None:
        return

    if len(stop_vars) == 1:
        payload['line_path_specs'][line_name] = []
    elif old_index == 0:
        next_anchor = anchors[stop_vars[1]]
        del specs[:next_anchor]
    elif old_index == len(stop_vars) - 1:
        del specs[station_anchor:]
    else:
        previous_anchor = anchors[stop_vars[old_index - 1]]
        next_anchor = anchors[stop_vars[old_index + 1]]
        del specs[previous_anchor + 1:next_anchor]


def _insert_station_after(
    payload: base.MetroNetworkPayload,
    line_name: str,
    station_var: str,
    after_stop_var: str,
) -> None:
    stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][line_name]]
    if station_var in stop_vars:
        _remove_station_from_line_specs(payload, line_name, station_var)
        stop_vars.remove(station_var)
    if after_stop_var not in stop_vars:
        raise ValueError(f'{after_stop_var} is not on Line {line_name}.')

    insert_index = stop_vars.index(after_stop_var) + 1
    if insert_index >= len(stop_vars):
        stop_vars.append(station_var)
        payload['line_stop_vars'][line_name] = stop_vars
        specs = payload['line_path_specs'].setdefault(line_name, [])
        if not specs:
            specs.append(_copy_anchor_spec(after_stop_var))
        specs.append(_copy_anchor_spec(station_var))
        return

    next_stop_var = stop_vars[insert_index]
    stop_vars.insert(insert_index, station_var)
    payload['line_stop_vars'][line_name] = stop_vars

    specs = payload['line_path_specs'][line_name]
    anchors = _anchor_indices(specs)
    start_anchor = anchors[after_stop_var]
    end_anchor = anchors[next_stop_var]
    specs[start_anchor:end_anchor + 1] = [
        dict(specs[start_anchor]),
        _copy_anchor_spec(station_var),
        dict(specs[end_anchor]),
    ]


def _insert_station_at_index(
    payload: base.MetroNetworkPayload,
    line_name: str,
    station_var: str,
    insert_index: int,
) -> None:
    stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][line_name]]
    if station_var in stop_vars:
        _remove_station_from_line_specs(payload, line_name, station_var)
        stop_vars.remove(station_var)

    bounded_index = max(0, min(int(insert_index), len(stop_vars)))
    specs = payload['line_path_specs'].setdefault(line_name, [])
    if not stop_vars:
        payload['line_stop_vars'][line_name] = [station_var]
        payload['line_path_specs'][line_name] = [_copy_anchor_spec(station_var), _copy_anchor_spec(station_var)]
        return

    if not specs:
        specs.extend(_copy_anchor_spec(stop_var) for stop_var in stop_vars)

    if bounded_index == 0:
        stop_vars.insert(0, station_var)
        payload['line_stop_vars'][line_name] = stop_vars
        specs.insert(0, _copy_anchor_spec(station_var))
        return

    if bounded_index >= len(stop_vars):
        stop_vars.append(station_var)
        payload['line_stop_vars'][line_name] = stop_vars
        specs.append(_copy_anchor_spec(station_var))
        return

    previous_stop_var = stop_vars[bounded_index - 1]
    next_stop_var = stop_vars[bounded_index]
    stop_vars.insert(bounded_index, station_var)
    payload['line_stop_vars'][line_name] = stop_vars

    anchors = _anchor_indices(specs)
    previous_anchor = anchors[previous_stop_var]
    next_anchor = anchors[next_stop_var]
    specs[previous_anchor:next_anchor + 1] = [
        dict(specs[previous_anchor]),
        _copy_anchor_spec(station_var),
        dict(specs[next_anchor]),
    ]


def _line_specs_for_sequence(stop_vars: Sequence[str]) -> list[base.LinePathSpecRecord]:
    specs = [_copy_anchor_spec(stop_var) for stop_var in stop_vars]
    if len(specs) == 1:
        specs.append(dict(specs[0]))
    return specs


def _line_specs_for_reordered_sequence(
    payload: base.MetroNetworkPayload,
    line_name: str,
    ordered_stop_vars: Sequence[str],
) -> list[base.LinePathSpecRecord]:
    stop_vars = [str(stop_var) for stop_var in ordered_stop_vars]
    if not stop_vars:
        return []
    if len(stop_vars) == 1:
        return [_copy_anchor_spec(stop_vars[0]), _copy_anchor_spec(stop_vars[0])]

    original_stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][line_name]]
    original_indices = {stop_var: index for index, stop_var in enumerate(original_stop_vars)}
    original_specs = payload['line_path_specs'].get(line_name, [])
    original_anchors = _anchor_indices(original_specs)

    def segment_specs(start_var: str, end_var: str) -> list[base.LinePathSpecRecord]:
        if abs(original_indices[start_var] - original_indices[end_var]) != 1:
            return [_copy_anchor_spec(start_var), _copy_anchor_spec(end_var)]
        start_anchor = original_anchors.get(start_var)
        end_anchor = original_anchors.get(end_var)
        if start_anchor is None or end_anchor is None:
            return [_copy_anchor_spec(start_var), _copy_anchor_spec(end_var)]
        if start_anchor <= end_anchor:
            return [dict(spec) for spec in original_specs[start_anchor:end_anchor + 1]]
        return [dict(spec) for spec in reversed(original_specs[end_anchor:start_anchor + 1])]

    reordered_specs = [_copy_anchor_spec(stop_vars[0])]
    for start_var, end_var in zip(stop_vars, stop_vars[1:]):
        segment = segment_specs(start_var, end_var)
        reordered_specs.extend(segment[1:])
    return reordered_specs


def _resolve_station_sequence(
    payload: base.MetroNetworkPayload,
    station_var: str,
    station_tokens: Sequence[str],
) -> list[str]:
    sequence: list[str] = []
    saw_new = False
    for raw_token in station_tokens:
        token = raw_token.strip()
        if not token:
            continue
        if token.lower() in {'[new]', 'new', 'this'}:
            if not saw_new:
                sequence.append(station_var)
                saw_new = True
            continue
        resolved = base._resolve_stop_var_in_payload(payload, token)
        if resolved is None:
            raise ValueError(f'Unknown station for new line: {token}')
        sequence.append(resolved)
    if not saw_new:
        sequence.append(station_var)
    sequence = list(dict.fromkeys(sequence))
    if len(sequence) < 2:
        raise ValueError('New lines need at least one existing station in addition to the added station.')
    return sequence


def _parse_station_tokens(text: str) -> tuple[str, ...]:
    return tuple(token.strip() for token in re.split(r'[\n,]+', text) if token.strip())


def _normalize_line_name(line_name: str) -> str:
    normalized = line_name.strip().upper()
    if re.fullmatch(r'[A-Z]', normalized) is None:
        raise ValueError('Metro line names must be one uppercase letter.')
    return normalized


def _validate_hex_color(color: str) -> str:
    normalized = color.strip()
    if not normalized:
        return ''
    if not normalized.startswith('#'):
        normalized = f'#{normalized}'
    if re.fullmatch(r'#[0-9A-Fa-f]{6}', normalized) is None:
        raise ValueError('Line colors must be hex colors like #2fc8bd.')
    return normalized.lower()


def _random_line_color() -> str:
    existing_colors = {color.lower() for color in base.LINE_COLORS.values()}
    unused = [color for color in _LINE_COLOR_PALETTE if color.lower() not in existing_colors]
    if unused:
        return random.choice(unused)
    for _attempt in range(100):
        hue = random.random()
        saturation = random.uniform(0.68, 0.86)
        value = random.uniform(0.78, 0.94)
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
        color = f'#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}'
        if color not in existing_colors:
            return color
    return '#55c9e8'


def _center_dialog(dialog: tk.Toplevel, root: tk.Tk) -> None:
    dialog.update_idletasks()
    width = max(dialog.winfo_reqwidth(), dialog.winfo_width())
    height = max(dialog.winfo_reqheight(), dialog.winfo_height())
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    left = max(0, round((screen_width - width) / 2))
    top = max(0, round((screen_height - height) / 2))
    dialog.geometry(f'{width}x{height}+{left}+{top}')


def _existing_line_preview(
    *,
    coordinates: tuple[int, int],
    line_name: str,
    ordered_stop_vars: Sequence[str],
) -> MetroStationPreview | None:
    if line_name not in base.LINE_STOP_VARS:
        return None

    world_points: list[tuple[int, int]] = []
    for stop_var in ordered_stop_vars:
        if stop_var == '[new]':
            world_points.append(coordinates)
            continue
        if stop_var in base.STOPS_BY_VAR:
            world_points.append(base.STOPS_BY_VAR[stop_var].coordinates)
    if coordinates not in world_points:
        world_points.append(coordinates)
    try:
        station_index = list(ordered_stop_vars).index('[new]') + 1
    except ValueError:
        station_index = len(world_points)
    return MetroStationPreview(
        points=tuple(world_points),
        color=base.LINE_COLORS.get(line_name, '#ffffff'),
        station_coordinates=coordinates,
        station_label=(
            base._display_label(existing_stop.lbl)
            if (existing_stop := next((stop for stop in base.METRO_STOPS if stop.coordinates == coordinates), None))
            is not None
            else _line_index_label(line_name, station_index)
        ),
        line_name=line_name,
    )


def _new_line_preview(
    *,
    coordinates: tuple[int, int],
    line_name: str,
    color: str,
    station_tokens: Sequence[str],
) -> MetroStationPreview | None:
    normalized_line = line_name.strip().upper() or '?'
    world_points: list[tuple[int, int]] = []
    saw_new = False
    for token in station_tokens:
        if token.lower() in {'[new]', 'new', 'this'}:
            if not saw_new:
                world_points.append(coordinates)
                saw_new = True
            continue
        stop_var = base._resolve_stop_var_runtime(token)
        if stop_var is None:
            continue
        world_points.append(base.STOPS_BY_VAR[stop_var].coordinates)
    if not saw_new:
        world_points.append(coordinates)
    if len(world_points) < 2:
        return MetroStationPreview(
            points=(coordinates,),
            color=color,
            station_coordinates=coordinates,
            station_label=_line_index_label(normalized_line, 1) if len(normalized_line) == 1 else 'New',
            line_name=normalized_line,
        )
    return MetroStationPreview(
        points=tuple(world_points),
        color=color,
        station_coordinates=coordinates,
        station_label=_line_index_label(normalized_line, world_points.index(coordinates) + 1)
        if len(normalized_line) == 1
        else 'New',
        line_name=normalized_line,
    )


def _set_preview(viewer: base.MetroMapViewer, preview: MetroStationPreview | None) -> None:
    viewer._metro_station_preview = preview  # type: ignore[attr-defined]
    viewer.redraw()


def _clear_preview(viewer: base.MetroMapViewer) -> None:
    if hasattr(viewer, '_metro_station_preview'):
        viewer._metro_station_preview = None  # type: ignore[attr-defined]
    viewer.redraw()


def _draw_map_preview(viewer: base.MetroMapViewer) -> None:
    preview = getattr(viewer, '_metro_station_preview', None)
    if preview is None:
        return
    if not isinstance(preview, MetroStationPreview):
        return

    canvas_points = [viewer.world_to_canvas((point_x, -point_y)) for point_x, point_y in preview.points]
    if len(canvas_points) >= 2:
        flat_points = [coordinate for point in canvas_points for coordinate in point]
        viewer.canvas.create_line(
            *flat_points,
            fill=base.ROUTE_HIGHLIGHT_OUTLINE,
            width=base.ROUTE_HIGHLIGHT_OUTLINE_WIDTH,
            capstyle='round',
            joinstyle='round',
            dash=(12, 7),
        )
        viewer.canvas.create_line(
            *flat_points,
            fill=preview.color,
            width=base.ROUTE_HIGHLIGHT_WIDTH,
            capstyle='round',
            joinstyle='round',
            dash=(12, 7),
        )

    station_x, station_y = viewer.world_to_canvas(
        (preview.station_coordinates[0], -preview.station_coordinates[1])
    )
    radius = max(base.STATION_RADIUS + 5, 9)
    viewer.canvas.create_oval(
        station_x - radius,
        station_y - radius,
        station_x + radius,
        station_y + radius,
        fill=preview.color,
        outline=base.ROUTE_HIGHLIGHT_OUTLINE,
        width=3,
    )
    label_x, label_y = station_x + 12, station_y - 12
    viewer.canvas.create_text(
        label_x - 1,
        label_y,
        anchor='sw',
        text=f'{preview.station_label} preview',
        fill=base.LABEL_CASING_COLOR,
        font=('Helvetica', max(12, base.BASE_LABEL_FONT_SIZE), 'bold'),
    )
    viewer.canvas.create_text(
        label_x,
        label_y,
        anchor='sw',
        text=f'{preview.station_label} preview',
        fill=preview.color,
        font=('Helvetica', max(12, base.BASE_LABEL_FONT_SIZE), 'bold'),
    )


def _patched_redraw(self: base.MetroMapViewer) -> None:
    assert _ORIGINAL_REDRAW is not None
    _ORIGINAL_REDRAW(self)
    _draw_map_preview(self)


def _save_payload(payload: base.MetroNetworkPayload) -> None:
    _renumber_placeholder_station_labels(payload)
    base._normalize_extra_edges(payload)
    base._normalize_alignment_reminders(payload)
    base._normalize_railway_finish_origins(payload)
    base._write_network_payload(payload)
    base._apply_network_payload(payload)


def add_station_to_existing_line(
    coordinates: tuple[int, int],
    *,
    line_name: str,
    ordered_stop_vars: Sequence[str],
) -> AddedStation:
    payload = base._load_network_payload()
    normalized_line = _normalize_line_name(line_name)
    if normalized_line not in payload['line_stop_vars']:
        raise ValueError(f'Unknown line: {normalized_line}')

    station_var = _find_stop_var_at_coordinates(payload, coordinates)
    if station_var is None:
        next_index = len(payload['line_stop_vars'][normalized_line]) + 1
        station_var = _new_station_record(
            payload,
            coordinates,
            (normalized_line,),
            label_hint=_line_index_label(normalized_line, next_index),
        )
    else:
        station_var = _ensure_stop_on_lines(payload, station_var, (normalized_line,))
        if station_var in payload['line_stop_vars'][normalized_line]:
            raise ValueError('That station is already on the selected line.')

    normalized_order = [str(stop_var) for stop_var in ordered_stop_vars]
    if '[new]' not in normalized_order:
        normalized_order.append('[new]')
    insert_index = normalized_order.index('[new]')
    existing_stop_vars = [stop_var for stop_var in normalized_order if stop_var != '[new]']
    current_stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][normalized_line]]
    if set(existing_stop_vars) != set(current_stop_vars):
        raise ValueError('The station order list no longer matches the selected line.')

    _insert_station_at_index(payload, normalized_line, station_var, insert_index)
    _save_payload(payload)
    return AddedStation(
        label=base.STOPS_BY_VAR[station_var].lbl,
        coordinates=coordinates,
        stop_var=station_var,
    )


def add_station_to_new_line(
    coordinates: tuple[int, int],
    *,
    line_name: str,
    station_tokens: Sequence[str],
    color: str = '',
) -> AddedStation:
    payload = base._load_network_payload()
    normalized_line = _normalize_line_name(line_name)
    if normalized_line in payload['line_stop_vars']:
        raise ValueError(f'Line {normalized_line} already exists.')

    chosen_color = _validate_hex_color(color) or _random_line_color()
    station_var = _find_stop_var_at_coordinates(payload, coordinates)
    if station_var is None:
        station_var = _new_station_record(
            payload,
            coordinates,
            (normalized_line,),
            label_hint=f'{normalized_line}_1',
        )
    else:
        station_var = _ensure_stop_on_lines(payload, station_var, (normalized_line,))

    sequence = _resolve_station_sequence(payload, station_var, station_tokens)
    renamed_sequence: list[str] = []
    for stop_var in sequence:
        if stop_var == station_var:
            renamed_sequence.append(station_var)
            continue
        renamed_sequence.append(_ensure_stop_on_lines(payload, stop_var, (normalized_line,)))

    payload['line_stop_vars'][normalized_line] = renamed_sequence
    payload['line_path_specs'][normalized_line] = _line_specs_for_sequence(renamed_sequence)
    payload['line_colors'][normalized_line] = chosen_color
    payload.setdefault('wool_colors', {})[normalized_line] = 'Unassigned'
    _save_payload(payload)
    return AddedStation(
        label=base.STOPS_BY_VAR[station_var].lbl,
        coordinates=coordinates,
        stop_var=station_var,
    )


def _line_membership_from_payload(
    payload: base.MetroNetworkPayload,
    stop_var: str,
) -> tuple[str, ...]:
    return tuple(
        str(line_name)
        for line_name, stop_vars in payload['line_stop_vars'].items()
        if stop_var in {str(candidate_var) for candidate_var in stop_vars}
    )


def switch_station_line(
    station_var: str,
    *,
    from_line_name: str,
    to_line_name: str,
    ordered_target_stop_vars: Sequence[str],
) -> AddedStation:
    payload = base._load_network_payload()
    normalized_from_line = _normalize_line_name(from_line_name)
    normalized_to_line = _normalize_line_name(to_line_name)
    if normalized_from_line == normalized_to_line:
        raise ValueError('Choose two different lines.')
    if normalized_from_line not in payload['line_stop_vars']:
        raise ValueError(f'Unknown source line: {normalized_from_line}')
    if normalized_to_line not in payload['line_stop_vars']:
        raise ValueError(f'Unknown target line: {normalized_to_line}')
    if station_var not in {str(stop_var) for stop_var in payload['line_stop_vars'][normalized_from_line]}:
        raise ValueError(f'{station_var} is not on Line {normalized_from_line}.')
    if station_var in {str(stop_var) for stop_var in payload['line_stop_vars'][normalized_to_line]}:
        raise ValueError(f'{station_var} is already on Line {normalized_to_line}.')

    stop_record = next((stop for stop in payload['stops'] if str(stop['var']) == station_var), None)
    if stop_record is None:
        raise ValueError(f'Unknown station: {station_var}')
    coordinates = (int(stop_record['x']), int(stop_record['y']))

    normalized_order = [str(stop_var) for stop_var in ordered_target_stop_vars]
    if '[new]' not in normalized_order:
        normalized_order.append('[new]')
    insert_index = normalized_order.index('[new]')
    existing_target_stop_vars = [stop_var for stop_var in normalized_order if stop_var != '[new]']
    current_target_stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][normalized_to_line]]
    if set(existing_target_stop_vars) != set(current_target_stop_vars):
        raise ValueError('The station order list no longer matches the target line.')

    base._remove_station_from_line_specs(payload, normalized_from_line, station_var)
    switched_membership = tuple(
        sorted(set(_line_membership_from_payload(payload, station_var)).union({normalized_to_line}))
    )
    new_station_var = base._unique_station_var_for_membership(
        payload,
        switched_membership,
        old_var=station_var,
    )
    new_station_var = base._rename_stop_var_in_payload(payload, station_var, new_station_var)
    _insert_station_at_index(payload, normalized_to_line, new_station_var, insert_index)

    _save_payload(payload)
    return AddedStation(
        label=base.STOPS_BY_VAR[new_station_var].lbl,
        coordinates=coordinates,
        stop_var=new_station_var,
    )


def reorder_line_stations(line_name: str, ordered_stop_vars: Sequence[str]) -> str:
    payload = base._load_network_payload()
    normalized_line = _normalize_line_name(line_name)
    if normalized_line not in payload['line_stop_vars']:
        raise ValueError(f'Unknown line: {normalized_line}')

    current_stop_vars = [str(stop_var) for stop_var in payload['line_stop_vars'][normalized_line]]
    normalized_order = [str(stop_var) for stop_var in ordered_stop_vars]
    if len(normalized_order) != len(set(normalized_order)):
        raise ValueError('Each station can only appear once in the line order.')
    if set(normalized_order) != set(current_stop_vars):
        raise ValueError('The station order list no longer matches the selected line.')

    payload['line_path_specs'][normalized_line] = _line_specs_for_reordered_sequence(
        payload,
        normalized_line,
        normalized_order,
    )
    payload['line_stop_vars'][normalized_line] = normalized_order
    _save_payload(payload)
    return normalized_line


def move_station_after(line_name: str, station_var: str, after_stop_var: str) -> None:
    payload = base._load_network_payload()
    normalized_line = _normalize_line_name(line_name)
    if station_var not in payload['line_stop_vars'].get(normalized_line, []):
        raise ValueError(f'{station_var} is not on Line {normalized_line}.')
    if after_stop_var == station_var:
        raise ValueError('A station cannot be placed after itself.')
    stop_record = next(stop for stop in payload['stops'] if str(stop['var']) == station_var)
    _insert_station_after(
        payload,
        normalized_line,
        station_var,
        after_stop_var,
    )
    stop_record['x'] = int(stop_record['x'])
    stop_record['y'] = int(stop_record['y'])
    _save_payload(payload)


def _nearest_terminal_stop_var(line_name: str, coordinates: tuple[int, int]) -> str:
    stop_vars = base.LINE_STOP_VARS[line_name]
    first_stop = base.STOPS_BY_VAR[stop_vars[0]]
    last_stop = base.STOPS_BY_VAR[stop_vars[-1]]

    def distance_sq(stop: base.MetroStop) -> int:
        return ((stop.x - coordinates[0]) ** 2) + ((stop.y - coordinates[1]) ** 2)

    return last_stop.var if distance_sq(last_stop) <= distance_sq(first_stop) else first_stop.var


def _refresh_viewer_after_add(viewer: base.MetroMapViewer, added: AddedStation) -> None:
    viewer.route_controls_dirty = True
    viewer.route_dirty = True
    viewer.priority_dirty = True
    viewer.stats_dirty = True
    viewer.railway_finish_dirty = True
    viewer.path_edge_list_dirty = True
    viewer.selected_stop_var = added.stop_var
    viewer.selected_path_node_key = None
    viewer.selected_metro_segment_key = None
    viewer.cursor_readout_coordinates = added.coordinates
    viewer.show_cursor_guides = False
    viewer.redraw()


def _show_add_error(messagebox: object, dialog: tk.Toplevel, title: str, exc: Exception) -> None:
    message = str(exc).strip() or exc.__class__.__name__
    if not isinstance(exc, ValueError):
        message = f'{exc.__class__.__name__}: {message}'
    messagebox.showerror(title, message, parent=dialog)


def _default_addable_line(stop_var: str) -> str | None:
    current_line_names = set(base.STOP_LINE_NAMES.get(stop_var, ()))
    for line_name in sorted(base.LINE_STOP_VARS):
        if line_name not in current_line_names:
            return line_name
    return None


def _switchable_target_lines(stop_var: str) -> tuple[str, ...]:
    current_line_names = set(base.STOP_LINE_NAMES.get(stop_var, ()))
    return tuple(line_name for line_name in sorted(base.LINE_STOP_VARS) if line_name not in current_line_names)


def _show_add_selected_station_to_line_dialog(viewer: base.MetroMapViewer, stop_var: str) -> None:
    stop = base.STOPS_BY_VAR.get(stop_var)
    if stop is None:
        return
    initial_line = _default_addable_line(stop_var)
    if initial_line is None:
        from tkinter import messagebox

        messagebox.showinfo(
            'Already On Every Line',
            f'{base._display_label(stop.lbl)} is already on every metro line.',
            parent=viewer.root,
        )
        return
    show_add_metro_station_dialog(
        viewer,
        coordinates=stop.coordinates,
        initial_mode='Existing Line',
        initial_line=initial_line,
    )


def show_switch_station_line_dialog(viewer: base.MetroMapViewer, station_var: str) -> None:
    from tkinter import messagebox

    stop = base.STOPS_BY_VAR.get(station_var)
    if stop is None:
        return
    source_line_names = tuple(base.STOP_LINE_NAMES.get(station_var, ()))
    target_line_names = _switchable_target_lines(station_var)
    if not source_line_names:
        messagebox.showinfo(
            'Switch Line',
            f'{base._display_label(stop.lbl)} is not on a metro line yet.',
            parent=viewer.root,
        )
        return
    if not target_line_names:
        messagebox.showinfo(
            'Switch Line',
            f'{base._display_label(stop.lbl)} is already on every metro line.',
            parent=viewer.root,
        )
        return

    dialog = tk.Toplevel(viewer.root)
    dialog.title('Switch Station Line')
    dialog.configure(bg=base.BACKGROUND_COLOR)
    dialog.transient(viewer.root)
    dialog.grab_set()

    container = tk.Frame(dialog, bg=base.BACKGROUND_COLOR)
    container.pack(fill='both', expand=True, padx=16, pady=16)

    from_line_var = tk.StringVar(master=dialog, value=source_line_names[0])
    to_line_var = tk.StringVar(master=dialog, value=target_line_names[0])
    target_order: list[str] = []
    active_token: dict[str, object | None] = {'value': object()}

    def close_dialog() -> None:
        if dialog.winfo_exists():
            dialog.destroy()
        _clear_preview(viewer)

    dialog.protocol('WM_DELETE_WINDOW', close_dialog)

    def label(text: str, *, bold: bool = False) -> tk.Label:
        return tk.Label(
            container,
            text=text,
            bg=base.BACKGROUND_COLOR,
            fg=base.TEXT_COLOR,
            font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE, 'bold' if bold else 'normal'),
            anchor='w',
            justify='left',
            wraplength=460,
        )

    def row() -> tk.Frame:
        frame = tk.Frame(container, bg=base.BACKGROUND_COLOR)
        frame.pack(fill='x', pady=(8, 0))
        return frame

    def button(parent: tk.Misc, text: str, command: Callable[[], None]) -> tk.Label:
        return viewer._make_sidebar_button(parent, text=text, command=command)

    label(f'Switch {base._display_label(stop.lbl)}', bold=True).pack(anchor='w')
    label(f'Coords: {stop.x}, {stop.y}').pack(anchor='w', pady=(4, 8))

    line_row = row()
    tk.Label(
        line_row,
        text='From',
        bg=base.BACKGROUND_COLOR,
        fg=base.TEXT_COLOR,
        font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
        width=6,
        anchor='w',
    ).pack(side='left')
    from_menu = viewer._make_sidebar_option_menu(line_row, from_line_var)
    from_menu.pack(side='left', fill='x', expand=True, padx=(0, 10))
    viewer._populate_option_menu(from_menu, from_line_var, list(source_line_names))
    tk.Label(
        line_row,
        text='To',
        bg=base.BACKGROUND_COLOR,
        fg=base.TEXT_COLOR,
        font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
        width=3,
        anchor='w',
    ).pack(side='left')
    to_menu = viewer._make_sidebar_option_menu(line_row, to_line_var)
    to_menu.pack(side='left', fill='x', expand=True)
    viewer._populate_option_menu(to_menu, to_line_var, list(target_line_names))

    label('Move [station] into the target line order. The dashed preview is shown on the map.').pack(
        anchor='w',
        pady=(10, 8),
    )
    order_frame = tk.Frame(
        container,
        bg=base.INFO_BOX_BACKGROUND,
        highlightthickness=1,
        highlightbackground=base.INFO_BOX_BORDER,
    )
    order_frame.pack(fill='x')
    order_listbox = tk.Listbox(
        order_frame,
        height=10,
        bg=base.SIDEBAR_INPUT_BACKGROUND,
        fg=base.TEXT_COLOR,
        selectbackground=base.SIDEBAR_INPUT_ACTIVE_BACKGROUND,
        selectforeground=base.TEXT_COLOR,
        relief='flat',
        bd=0,
        highlightthickness=0,
        font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
        activestyle='none',
        exportselection=False,
    )
    order_listbox.pack(side='left', fill='both', expand=True, padx=8, pady=8)
    order_scrollbar = tk.Scrollbar(order_frame, orient='vertical', command=order_listbox.yview)
    order_scrollbar.pack(side='right', fill='y')
    order_listbox.configure(yscrollcommand=order_scrollbar.set)

    def selected_station_index() -> int:
        try:
            return target_order.index('[new]')
        except ValueError:
            target_order.append('[new]')
            return len(target_order) - 1

    def order_label(stop_var: str, index: int) -> str:
        if stop_var == '[new]':
            return f'{index + 1}. [{base._display_label(stop.lbl)}]'
        target_stop = base.STOPS_BY_VAR[stop_var]
        return f'{index + 1}. {base._display_label(target_stop.lbl)}'

    def reset_order_for_target_line(line_name: str) -> None:
        target_order.clear()
        stop_vars = list(base.LINE_STOP_VARS[line_name])
        default_stop_var = _nearest_terminal_stop_var(line_name, stop.coordinates)
        insert_index = stop_vars.index(default_stop_var) + 1
        target_order.extend(stop_vars[:insert_index])
        target_order.append('[new]')
        target_order.extend(stop_vars[insert_index:])

    def refresh_preview() -> None:
        if active_token['value'] is None:
            return
        _set_preview(
            viewer,
            _existing_line_preview(
                coordinates=stop.coordinates,
                line_name=to_line_var.get(),
                ordered_stop_vars=target_order,
            ),
        )

    def refresh_order_listbox() -> None:
        order_listbox.delete(0, 'end')
        for index, stop_var in enumerate(target_order):
            order_listbox.insert('end', order_label(stop_var, index))
        station_index = selected_station_index()
        order_listbox.selection_clear(0, 'end')
        order_listbox.selection_set(station_index)
        order_listbox.activate(station_index)
        order_listbox.see(station_index)
        refresh_preview()

    def move_station(delta: int) -> None:
        old_index = selected_station_index()
        new_index = max(0, min(len(target_order) - 1, old_index + delta))
        if new_index == old_index:
            return
        target_order.pop(old_index)
        target_order.insert(new_index, '[new]')
        refresh_order_listbox()

    def on_target_line_changed(*_args: object) -> None:
        line_name = to_line_var.get()
        if line_name not in base.LINE_STOP_VARS:
            return
        reset_order_for_target_line(line_name)
        refresh_order_listbox()

    def center_preview() -> None:
        viewer._center_on_world_point(stop.coordinates)
        refresh_preview()

    def save_switch() -> None:
        try:
            added = switch_station_line(
                station_var,
                from_line_name=from_line_var.get(),
                to_line_name=to_line_var.get(),
                ordered_target_stop_vars=target_order,
            )
        except Exception as exc:
            _show_add_error(messagebox, dialog, 'Could Not Switch Line', exc)
            return
        if dialog.winfo_exists():
            dialog.destroy()
        viewer._metro_station_preview = None  # type: ignore[attr-defined]
        _refresh_viewer_after_add(viewer, added)

    reset_order_for_target_line(to_line_var.get())
    refresh_order_listbox()
    to_line_var.trace_add('write', on_target_line_changed)

    actions = row()
    button(actions, 'Move Up', lambda: move_station(-1)).pack(side='left')
    button(actions, 'Move Down', lambda: move_station(1)).pack(side='left', padx=(8, 0))
    button(actions, 'Center Preview', center_preview).pack(side='left', padx=(8, 0))
    button(actions, 'Switch Line', save_switch).pack(side='left', padx=(8, 0))
    button(actions, 'Cancel', close_dialog).pack(side='left', padx=(8, 0))
    _center_dialog(dialog, viewer.root)


def _patched_draw_selected_stop_info(self: base.MetroMapViewer) -> None:
    assert _ORIGINAL_DRAW_SELECTED_STOP_INFO is not None
    _ORIGINAL_DRAW_SELECTED_STOP_INFO(self)
    stop_var = getattr(self, 'selected_stop_var', None)
    frame = getattr(self, 'info_popup_frame', None)
    if stop_var is None or frame is None or stop_var not in base.STOPS_BY_VAR:
        return
    if not base.LINE_STOP_VARS:
        return

    line_button_row = tk.Frame(frame, bg=base.INFO_BOX_BACKGROUND)
    line_button_row.pack(anchor='w', padx=base.INFO_BOX_PAD_X, pady=(0, base.INFO_BOX_SECTION_GAP))
    self._make_info_button(
        line_button_row,
        text='Add to Line',
        command=lambda active_stop_var=stop_var: _show_add_selected_station_to_line_dialog(self, active_stop_var),
    ).pack(side='left', padx=(0, base.INFO_BOX_SECTION_GAP))
    if base.STOP_LINE_NAMES.get(stop_var) and _switchable_target_lines(stop_var):
        self._make_info_button(
            line_button_row,
            text='Switch Line',
            command=lambda active_stop_var=stop_var: show_switch_station_line_dialog(self, active_stop_var),
        ).pack(side='left', padx=(0, base.INFO_BOX_SECTION_GAP))


def _line_reorder_preview(
    *,
    line_name: str,
    ordered_stop_vars: Sequence[str],
    selected_stop_var: str | None = None,
) -> MetroStationPreview | None:
    if line_name not in base.LINE_STOP_VARS:
        return None
    world_points = tuple(
        base.STOPS_BY_VAR[stop_var].coordinates
        for stop_var in ordered_stop_vars
        if stop_var in base.STOPS_BY_VAR
    )
    if not world_points:
        return None
    selected_coordinates = (
        base.STOPS_BY_VAR[selected_stop_var].coordinates
        if selected_stop_var in base.STOPS_BY_VAR
        else world_points[0]
    )
    return MetroStationPreview(
        points=world_points,
        color=base.LINE_COLORS.get(line_name, '#ffffff'),
        station_coordinates=selected_coordinates,
        station_label=f'Line {line_name} order',
        line_name=line_name,
    )


def _refresh_viewer_after_line_reorder(viewer: base.MetroMapViewer, line_name: str) -> None:
    viewer.route_controls_dirty = True
    viewer.route_dirty = True
    viewer.priority_dirty = True
    viewer.stats_dirty = True
    viewer.railway_finish_dirty = True
    viewer.path_edge_list_dirty = True
    viewer.selected_metro_segment_key = None
    viewer.show_cursor_guides = False
    viewer.redraw()


def show_reorder_metro_line_dialog(
    viewer: base.MetroMapViewer,
    line_name: str | None = None,
    *,
    on_saved: Callable[[str], None] | None = None,
) -> None:
    from tkinter import messagebox

    if not base.LINE_STOP_VARS:
        messagebox.showinfo('Reorder Stations', 'No metro lines are defined yet.', parent=viewer.root)
        return

    dialog = tk.Toplevel(viewer.root)
    dialog.title('Reorder Line Stations')
    dialog.configure(bg=base.BACKGROUND_COLOR)
    dialog.transient(viewer.root)
    dialog.grab_set()

    container = tk.Frame(dialog, bg=base.BACKGROUND_COLOR)
    container.pack(fill='both', expand=True, padx=16, pady=16)

    line_names = sorted(base.LINE_STOP_VARS)
    initial_line = line_name if line_name in base.LINE_STOP_VARS else line_names[0]
    selected_line_var = tk.StringVar(master=dialog, value=initial_line)
    current_order: list[str] = []
    active_page_token: dict[str, object | None] = {'value': object()}

    def close_dialog() -> None:
        if dialog.winfo_exists():
            dialog.destroy()
        _clear_preview(viewer)

    dialog.protocol('WM_DELETE_WINDOW', close_dialog)

    def label(text: str, *, bold: bool = False) -> tk.Label:
        return tk.Label(
            container,
            text=text,
            bg=base.BACKGROUND_COLOR,
            fg=base.TEXT_COLOR,
            font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE, 'bold' if bold else 'normal'),
            anchor='w',
            justify='left',
            wraplength=460,
        )

    def row() -> tk.Frame:
        frame = tk.Frame(container, bg=base.BACKGROUND_COLOR)
        frame.pack(fill='x', pady=(8, 0))
        return frame

    def button(parent: tk.Misc, text: str, command: Callable[[], None]) -> tk.Label:
        return viewer._make_sidebar_button(parent, text=text, command=command)

    label('Reorder Line Stations', bold=True).pack(anchor='w')

    line_row = row()
    tk.Label(
        line_row,
        text='Line',
        bg=base.BACKGROUND_COLOR,
        fg=base.TEXT_COLOR,
        font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
        width=8,
        anchor='w',
    ).pack(side='left')
    line_menu = viewer._make_sidebar_option_menu(line_row, selected_line_var)
    line_menu.pack(side='left', fill='x', expand=True)
    viewer._populate_option_menu(line_menu, selected_line_var, line_names)

    label('Select a station, then move it within the line order. The dashed preview is shown on the map.').pack(
        anchor='w',
        pady=(10, 8),
    )
    order_frame = tk.Frame(
        container,
        bg=base.INFO_BOX_BACKGROUND,
        highlightthickness=1,
        highlightbackground=base.INFO_BOX_BORDER,
    )
    order_frame.pack(fill='x')
    order_listbox = tk.Listbox(
        order_frame,
        height=12,
        bg=base.SIDEBAR_INPUT_BACKGROUND,
        fg=base.TEXT_COLOR,
        selectbackground=base.SIDEBAR_INPUT_ACTIVE_BACKGROUND,
        selectforeground=base.TEXT_COLOR,
        relief='flat',
        bd=0,
        highlightthickness=0,
        font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
        activestyle='none',
        exportselection=False,
    )
    order_listbox.pack(side='left', fill='both', expand=True, padx=8, pady=8)
    order_scrollbar = tk.Scrollbar(order_frame, orient='vertical', command=order_listbox.yview)
    order_scrollbar.pack(side='right', fill='y')
    order_listbox.configure(yscrollcommand=order_scrollbar.set)

    def selected_index() -> int:
        selection = order_listbox.curselection()
        if selection:
            return int(selection[0])
        return 0

    def order_label(stop_var: str, index: int) -> str:
        stop = base.STOPS_BY_VAR[stop_var]
        return f'{index + 1}. {base._display_label(stop.lbl)}'

    def reset_order_for_line(line: str) -> None:
        current_order.clear()
        current_order.extend(str(stop_var) for stop_var in base.LINE_STOP_VARS[line])

    def refresh_preview() -> None:
        if active_page_token['value'] is None:
            return
        selected_stop_var = current_order[selected_index()] if current_order else None
        _set_preview(
            viewer,
            _line_reorder_preview(
                line_name=selected_line_var.get(),
                ordered_stop_vars=current_order,
                selected_stop_var=selected_stop_var,
            ),
        )

    def refresh_order_listbox(select_index: int | None = None) -> None:
        order_listbox.delete(0, 'end')
        for index, stop_var in enumerate(current_order):
            order_listbox.insert('end', order_label(stop_var, index))
        if current_order:
            bounded_index = max(0, min(select_index if select_index is not None else selected_index(), len(current_order) - 1))
            order_listbox.selection_clear(0, 'end')
            order_listbox.selection_set(bounded_index)
            order_listbox.activate(bounded_index)
            order_listbox.see(bounded_index)
        refresh_preview()

    def move_selected_station(delta: int) -> None:
        if not current_order:
            return
        old_index = selected_index()
        new_index = max(0, min(len(current_order) - 1, old_index + delta))
        if new_index == old_index:
            return
        stop_var = current_order.pop(old_index)
        current_order.insert(new_index, stop_var)
        refresh_order_listbox(new_index)

    def on_line_changed(*_args: object) -> None:
        line = selected_line_var.get()
        if line not in base.LINE_STOP_VARS:
            return
        reset_order_for_line(line)
        refresh_order_listbox(0)

    def center_selected_station() -> None:
        if not current_order:
            return
        stop_var = current_order[selected_index()]
        viewer._center_on_world_point(base.STOPS_BY_VAR[stop_var].coordinates)
        refresh_preview()

    def save_order() -> None:
        try:
            saved_line = reorder_line_stations(selected_line_var.get(), current_order)
        except Exception as exc:
            _show_add_error(messagebox, dialog, 'Could Not Reorder Stations', exc)
            return
        if dialog.winfo_exists():
            dialog.destroy()
        viewer._metro_station_preview = None  # type: ignore[attr-defined]
        _refresh_viewer_after_line_reorder(viewer, saved_line)
        if on_saved is not None:
            on_saved(saved_line)

    selected_line_var.trace_add('write', on_line_changed)
    order_listbox.bind('<<ListboxSelect>>', lambda _event: refresh_preview())
    reset_order_for_line(initial_line)
    refresh_order_listbox(0)

    actions = row()
    button(actions, 'Move Up', lambda: move_selected_station(-1)).pack(side='left')
    button(actions, 'Move Down', lambda: move_selected_station(1)).pack(side='left', padx=(8, 0))
    button(actions, 'Center Preview', center_selected_station).pack(side='left', padx=(8, 0))
    button(actions, 'Save Order', save_order).pack(side='left', padx=(8, 0))
    button(actions, 'Cancel', close_dialog).pack(side='left', padx=(8, 0))
    _center_dialog(dialog, viewer.root)


def show_add_metro_station_dialog(
    viewer: base.MetroMapViewer,
    *,
    coordinates: tuple[int, int] | None = None,
    initial_mode: str = 'Existing Line',
    initial_line: str | None = None,
) -> None:
    from tkinter import colorchooser, messagebox

    dialog = tk.Toplevel(viewer.root)
    dialog.title('Add Metro Station')
    dialog.configure(bg=base.BACKGROUND_COLOR)
    dialog.transient(viewer.root)
    dialog.grab_set()

    container = tk.Frame(dialog, bg=base.BACKGROUND_COLOR)
    container.pack(fill='both', expand=True, padx=16, pady=16)

    coordinates_var = tk.StringVar(master=dialog)
    initial_coordinates = coordinates if coordinates is not None else viewer.cursor_readout_coordinates
    if initial_coordinates is not None:
        coordinates_var.set(f'{initial_coordinates[0]}, {initial_coordinates[1]}')
    mode_var = tk.StringVar(master=dialog, value=initial_mode if initial_mode in {'Existing Line', 'New Line'} else 'Existing Line')
    default_line = initial_line if initial_line in base.LINE_STOP_VARS else sorted(base.LINE_STOP_VARS)[0]
    existing_line_var = tk.StringVar(master=dialog, value=default_line)
    new_line_name_var = tk.StringVar(master=dialog)
    new_line_color_var = tk.StringVar(master=dialog)
    new_line_stations_var = tk.StringVar(master=dialog)
    current_coordinates = {'value': (0, 0)}
    active_page_token: dict[str, object | None] = {'value': None}
    existing_line_order: list[str] = []

    def close_dialog() -> None:
        if dialog.winfo_exists():
            dialog.destroy()
        _clear_preview(viewer)

    dialog.protocol('WM_DELETE_WINDOW', close_dialog)

    def clear() -> None:
        for child in container.winfo_children():
            child.destroy()

    def label(text: str, *, bold: bool = False) -> tk.Label:
        return tk.Label(
            container,
            text=text,
            bg=base.BACKGROUND_COLOR,
            fg=base.TEXT_COLOR,
            font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE, 'bold' if bold else 'normal'),
            anchor='w',
            justify='left',
            wraplength=460,
        )

    def row() -> tk.Frame:
        frame = tk.Frame(container, bg=base.BACKGROUND_COLOR)
        frame.pack(fill='x', pady=(8, 0))
        return frame

    def button(parent: tk.Misc, text: str, command: Callable[[], None]) -> tk.Label:
        return viewer._make_sidebar_button(parent, text=text, command=command)

    def validate_coordinates() -> tuple[int, int] | None:
        coordinates = base._parse_coordinate_text(coordinates_var.get())
        if coordinates is None:
            messagebox.showerror('Invalid Coordinates', 'Enter coordinates in the format: x, y', parent=dialog)
            return None
        current_coordinates['value'] = coordinates
        return coordinates

    def show_start() -> None:
        active_page_token['value'] = object()
        _set_preview(viewer, None)
        clear()
        label('Add Metro Station', bold=True).pack(anchor='w')
        label('Coordinates').pack(anchor='w', pady=(12, 4))
        viewer._make_sidebar_entry(container, coordinates_var).pack(fill='x')
        label('Metro action').pack(anchor='w', pady=(12, 4))
        mode_menu = viewer._make_sidebar_option_menu(container, mode_var)
        mode_menu.pack(fill='x')
        viewer._populate_option_menu(mode_menu, mode_var, ('Existing Line', 'New Line'))
        actions = row()
        button(actions, 'Continue', continue_from_start).pack(side='left')
        button(actions, 'Cancel', close_dialog).pack(side='left', padx=(8, 0))
        _center_dialog(dialog, viewer.root)

    def continue_from_start() -> None:
        if validate_coordinates() is None:
            return
        if mode_var.get() == 'New Line':
            show_new_line()
        else:
            show_existing_line()

    def show_existing_line() -> None:
        page_token = object()
        active_page_token['value'] = page_token
        clear()
        coordinates = current_coordinates['value']
        label('Existing Line', bold=True).pack(anchor='w')
        label(f'Coords: {coordinates[0]}, {coordinates[1]}').pack(anchor='w', pady=(4, 8))

        line_row = row()
        tk.Label(
            line_row,
            text='Line',
            bg=base.BACKGROUND_COLOR,
            fg=base.TEXT_COLOR,
            font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
            width=8,
            anchor='w',
        ).pack(side='left')
        line_menu = viewer._make_sidebar_option_menu(line_row, existing_line_var)
        line_menu.pack(side='left', fill='x', expand=True)
        viewer._populate_option_menu(line_menu, existing_line_var, sorted(base.LINE_STOP_VARS))

        label('Move [new station] into the line order. The dashed preview is shown on the map.').pack(
            anchor='w',
            pady=(10, 8),
        )
        order_frame = tk.Frame(
            container,
            bg=base.INFO_BOX_BACKGROUND,
            highlightthickness=1,
            highlightbackground=base.INFO_BOX_BORDER,
        )
        order_frame.pack(fill='x')
        order_listbox = tk.Listbox(
            order_frame,
            height=10,
            bg=base.SIDEBAR_INPUT_BACKGROUND,
            fg=base.TEXT_COLOR,
            selectbackground=base.SIDEBAR_INPUT_ACTIVE_BACKGROUND,
            selectforeground=base.TEXT_COLOR,
            relief='flat',
            bd=0,
            highlightthickness=0,
            font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
            activestyle='none',
            exportselection=False,
        )
        order_listbox.pack(side='left', fill='both', expand=True, padx=8, pady=8)
        order_scrollbar = tk.Scrollbar(order_frame, orient='vertical', command=order_listbox.yview)
        order_scrollbar.pack(side='right', fill='y')
        order_listbox.configure(yscrollcommand=order_scrollbar.set)

        def order_label(stop_var: str, index: int) -> str:
            if stop_var == '[new]':
                return f'{index + 1}. [new station]'
            stop = base.STOPS_BY_VAR[stop_var]
            return f'{index + 1}. {base._display_label(stop.lbl)}'

        def reset_order_for_line(line_name: str) -> None:
            existing_line_order.clear()
            stop_vars = list(base.LINE_STOP_VARS[line_name])
            default_stop_var = _nearest_terminal_stop_var(line_name, coordinates)
            insert_index = stop_vars.index(default_stop_var) + 1
            existing_line_order.extend(stop_vars[:insert_index])
            existing_line_order.append('[new]')
            existing_line_order.extend(stop_vars[insert_index:])

        def selected_new_index() -> int:
            try:
                return existing_line_order.index('[new]')
            except ValueError:
                existing_line_order.append('[new]')
                return len(existing_line_order) - 1

        def refresh_order_listbox() -> None:
            order_listbox.delete(0, 'end')
            for index, stop_var in enumerate(existing_line_order):
                order_listbox.insert('end', order_label(stop_var, index))
            new_index = selected_new_index()
            order_listbox.selection_clear(0, 'end')
            order_listbox.selection_set(new_index)
            order_listbox.activate(new_index)
            order_listbox.see(new_index)

        def refresh_preview(*_args: object) -> None:
            if active_page_token['value'] is not page_token:
                return
            line_name = existing_line_var.get()
            if line_name in base.LINE_STOP_VARS:
                _set_preview(
                    viewer,
                    _existing_line_preview(
                        coordinates=coordinates,
                        line_name=line_name,
                        ordered_stop_vars=existing_line_order,
                    ),
                )

        def refresh_order_and_preview() -> None:
            refresh_order_listbox()
            refresh_preview()

        def move_new_station(delta: int) -> None:
            new_index = selected_new_index()
            target_index = max(0, min(len(existing_line_order) - 1, new_index + delta))
            if target_index == new_index:
                return
            existing_line_order.pop(new_index)
            existing_line_order.insert(target_index, '[new]')
            refresh_order_and_preview()

        def on_line_changed(*_args: object) -> None:
            if active_page_token['value'] is not page_token:
                return
            line_name = existing_line_var.get()
            if line_name not in base.LINE_STOP_VARS:
                return
            reset_order_for_line(line_name)
            refresh_order_and_preview()

        def recenter_on_preview(*_args: object) -> None:
            if active_page_token['value'] is not page_token:
                return
            viewer._center_on_world_point(coordinates)
            refresh_preview()

        reset_order_for_line(existing_line_var.get())
        refresh_order_and_preview()
        existing_line_var.trace_add('write', on_line_changed)

        actions = row()
        button(actions, 'Back', show_start).pack(side='left')
        button(actions, 'Move Up', lambda: move_new_station(-1)).pack(side='left', padx=(8, 0))
        button(actions, 'Move Down', lambda: move_new_station(1)).pack(side='left', padx=(8, 0))
        button(actions, 'Center Preview', recenter_on_preview).pack(side='left', padx=(8, 0))
        button(actions, 'Add Station', save_existing_line).pack(side='left', padx=(8, 0))
        _center_dialog(dialog, viewer.root)

    def save_existing_line() -> None:
        try:
            added = add_station_to_existing_line(
                current_coordinates['value'],
                line_name=existing_line_var.get(),
                ordered_stop_vars=existing_line_order,
            )
        except Exception as exc:
            _show_add_error(messagebox, dialog, 'Could Not Add Station', exc)
            return
        if dialog.winfo_exists():
            dialog.destroy()
        viewer._metro_station_preview = None  # type: ignore[attr-defined]
        _refresh_viewer_after_add(viewer, added)

    def choose_color() -> None:
        selected_color, selected_hex = colorchooser.askcolor(
            color=new_line_color_var.get().strip() or None,
            title='Choose Line Color',
            parent=dialog,
        )
        if selected_hex:
            new_line_color_var.set(selected_hex)

    def show_new_line() -> None:
        page_token = object()
        active_page_token['value'] = page_token
        clear()
        coordinates = current_coordinates['value']
        if not new_line_color_var.get().strip():
            new_line_color_var.set(_random_line_color())
        label('New Line', bold=True).pack(anchor='w')
        label(f'Coords: {coordinates[0]}, {coordinates[1]}').pack(anchor='w', pady=(4, 8))

        name_row = row()
        tk.Label(
            name_row,
            text='Line',
            bg=base.BACKGROUND_COLOR,
            fg=base.TEXT_COLOR,
            font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
            width=8,
            anchor='w',
        ).pack(side='left')
        viewer._make_sidebar_entry(name_row, new_line_name_var).pack(side='left', fill='x', expand=True)

        color_row = row()
        tk.Label(
            color_row,
            text='Color',
            bg=base.BACKGROUND_COLOR,
            fg=base.TEXT_COLOR,
            font=('Helvetica', base.SIDEBAR_TEXT_FONT_SIZE),
            width=8,
            anchor='w',
        ).pack(side='left')
        viewer._make_sidebar_entry(color_row, new_line_color_var).pack(side='left', fill='x', expand=True)
        button(color_row, 'Pick', choose_color).pack(side='left', padx=(8, 0))
        button(color_row, 'Random', lambda: new_line_color_var.set(_random_line_color())).pack(side='left', padx=(8, 0))

        swatch_row = row()
        for color in _LINE_COLOR_PALETTE[:8]:
            swatch = tk.Label(swatch_row, text='  ', bg=color, cursor='hand2', relief='solid', bd=1)
            swatch.pack(side='left', padx=(0, 6))
            swatch.bind('<Button-1>', lambda _event, value=color: new_line_color_var.set(value))

        label('Stations, in order. Use [new] where this station belongs.').pack(anchor='w', pady=(12, 4))
        viewer._make_sidebar_entry(container, new_line_stations_var).pack(fill='x')
        label('Example: Blackport, [new], Dicton').pack(anchor='w', pady=(3, 4))
        label('The in-progress line is shown directly on the map.').pack(anchor='w', pady=(0, 8))

        def refresh_new_line_preview(*_args: object) -> None:
            if active_page_token['value'] is not page_token:
                return
            try:
                preview_color = (
                    _validate_hex_color(new_line_color_var.get())
                    if new_line_color_var.get().strip()
                    else _random_line_color()
                )
            except ValueError:
                preview_color = '#ffffff'
            _set_preview(
                viewer,
                _new_line_preview(
                    coordinates=coordinates,
                    line_name=new_line_name_var.get(),
                    color=preview_color,
                    station_tokens=_parse_station_tokens(new_line_stations_var.get()),
                ),
            )

        for variable in (new_line_name_var, new_line_color_var, new_line_stations_var):
            variable.trace_add('write', refresh_new_line_preview)
        refresh_new_line_preview()

        actions = row()
        button(actions, 'Back', show_start).pack(side='left')
        button(actions, 'Center Preview', lambda: (viewer._center_on_world_point(coordinates), refresh_new_line_preview())).pack(
            side='left',
            padx=(8, 0),
        )
        button(actions, 'Add Line', save_new_line).pack(side='left', padx=(8, 0))
        _center_dialog(dialog, viewer.root)

    def save_new_line() -> None:
        try:
            added = add_station_to_new_line(
                current_coordinates['value'],
                line_name=new_line_name_var.get(),
                station_tokens=_parse_station_tokens(new_line_stations_var.get()),
                color=new_line_color_var.get(),
            )
        except Exception as exc:
            _show_add_error(messagebox, dialog, 'Could Not Add Line', exc)
            return
        if dialog.winfo_exists():
            dialog.destroy()
        viewer._metro_station_preview = None  # type: ignore[attr-defined]
        _refresh_viewer_after_add(viewer, added)

    show_start()
    _center_dialog(dialog, viewer.root)


def apply() -> None:
    global _APPLIED
    global _ORIGINAL_REDRAW
    global _ORIGINAL_DRAW_SELECTED_STOP_INFO

    if _APPLIED:
        return

    _ORIGINAL_REDRAW = base.MetroMapViewer.redraw
    _ORIGINAL_DRAW_SELECTED_STOP_INFO = base.MetroMapViewer._draw_selected_stop_info
    base.MetroMapViewer.redraw = _patched_redraw  # type: ignore[method-assign]
    base.MetroMapViewer._draw_selected_stop_info = _patched_draw_selected_stop_info  # type: ignore[method-assign]
    base.MetroMapViewer._show_add_metro_station_dialog = show_add_metro_station_dialog  # type: ignore[attr-defined, method-assign]
    base.MetroMapViewer._show_reorder_metro_line_dialog = show_reorder_metro_line_dialog  # type: ignore[attr-defined, method-assign]
    _APPLIED = True
