from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Literal

import legacy_core as base


PoiKind = Literal['monument', 'pillager_tower']


@dataclass(frozen=True, slots=True)
class AddedPoi:
    kind: PoiKind
    label: str
    coordinates: tuple[int, int]
    node_key: str


def add_custom_point_of_interest(
    coordinates: tuple[int, int],
    *,
    kind: PoiKind,
    label: str | None = None,
    category: str | None = None,
) -> AddedPoi:
    payload = base._load_network_payload()
    if any((int(stop_record['x']), int(stop_record['y'])) == coordinates for stop_record in payload['stops']):
        raise ValueError('A station already exists at those coordinates.')

    raw_nodes = payload.setdefault('path_nodes', [])
    for node in raw_nodes:
        if not isinstance(node, dict):
            continue
        if (int(node.get('x', 0)), int(node.get('y', 0))) == coordinates:
            raise ValueError('A node or PoI already exists at those coordinates.')

    normalized_category = None if category is None else (category.strip() or None)
    normalized_label = None if label is None else (label.strip() or None)
    if kind == 'monument' and normalized_label is None:
        normalized_label = f'Unnamed {normalized_category or "Monument"}'
    if kind == 'pillager_tower' and normalized_label is None:
        normalized_label = 'Pillager Tower'

    node_id_prefix = 'monument' if kind == 'monument' else 'pillager_tower'
    node_record: base.PathNodeRecord = {
        'id': f'{node_id_prefix}_{len(raw_nodes) + 1}',
        'x': int(coordinates[0]),
        'y': int(coordinates[1]),
        'poi_kind': kind,
    }
    if normalized_label:
        node_record['label'] = normalized_label
    if normalized_category:
        node_record['category'] = normalized_category

    raw_nodes.append(node_record)
    base._normalize_path_nodes(payload)
    base._write_network_payload(payload)
    base._apply_network_payload(payload)
    return AddedPoi(
        kind=kind,
        label=normalized_label or node_record['id'],
        coordinates=coordinates,
        node_key=base._coordinate_endpoint_key(coordinates[0], coordinates[1]),
    )


def _poi_categories() -> tuple[str, ...]:
    categories: list[str] = []
    for path_node in base.PATH_NODES:
        if path_node.poi_kind == 'monument' and path_node.category:
            categories.append(path_node.category)
    return tuple(dict.fromkeys(sorted(categories, key=str.lower)))


def _center_dialog(dialog: tk.Toplevel, root: tk.Tk) -> None:
    dialog.update_idletasks()
    width = max(dialog.winfo_reqwidth(), dialog.winfo_width())
    height = max(dialog.winfo_reqheight(), dialog.winfo_height())
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    left = max(0, round((screen_width - width) / 2))
    top = max(0, round((screen_height - height) / 2))
    dialog.geometry(f'{width}x{height}+{left}+{top}')


def _refresh_viewer_after_add(viewer: base.MetroMapViewer, added: AddedPoi) -> None:
    viewer.route_controls_dirty = True
    viewer.route_dirty = True
    viewer.priority_dirty = True
    viewer.path_edge_list_dirty = True
    viewer.selected_stop_var = None
    viewer.selected_path_node_key = added.node_key
    viewer.selected_metro_segment_key = None
    viewer.cursor_readout_coordinates = added.coordinates
    viewer.show_cursor_guides = False
    viewer.redraw()


def show_add_poi_dialog(viewer: base.MetroMapViewer) -> None:
    from tkinter import messagebox

    dialog = tk.Toplevel(viewer.root)
    dialog.title('Add PoI')
    dialog.configure(bg=base.BACKGROUND_COLOR)
    dialog.transient(viewer.root)
    dialog.grab_set()

    container = tk.Frame(dialog, bg=base.BACKGROUND_COLOR)
    container.pack(fill='both', expand=True, padx=16, pady=16)

    coordinates_var = tk.StringVar(master=dialog)
    if viewer.cursor_readout_coordinates is not None:
        coordinates_var.set(f'{viewer.cursor_readout_coordinates[0]}, {viewer.cursor_readout_coordinates[1]}')
    kind_var = tk.StringVar(master=dialog, value='Monument')
    monument_name_var = tk.StringVar(master=dialog)
    monument_category_var = tk.StringVar(master=dialog)
    current_coordinates = {'value': (0, 0)}

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
            wraplength=420,
        )

    def button(parent: tk.Misc, text: str, command: Callable[[], None]) -> tk.Label:
        return viewer._make_sidebar_button(parent, text=text, command=command)

    def row() -> tk.Frame:
        frame = tk.Frame(container, bg=base.BACKGROUND_COLOR)
        frame.pack(fill='x', pady=(8, 0))
        return frame

    def validate_coordinates() -> tuple[int, int] | None:
        coordinates = base._parse_coordinate_text(coordinates_var.get())
        if coordinates is None:
            messagebox.showerror('Invalid Coordinates', 'Enter coordinates in the format: x, y', parent=dialog)
            return None
        current_coordinates['value'] = coordinates
        return coordinates

    def show_start() -> None:
        clear()
        label('Add PoI', bold=True).pack(anchor='w')
        label('Coordinates').pack(anchor='w', pady=(12, 4))
        viewer._make_sidebar_entry(container, coordinates_var).pack(fill='x')
        label('Type').pack(anchor='w', pady=(12, 4))
        kind_menu = viewer._make_sidebar_option_menu(container, kind_var)
        kind_menu.pack(fill='x')
        viewer._populate_option_menu(kind_menu, kind_var, ('Monument', 'Pillager Tower'))
        actions = row()
        button(actions, 'Continue', continue_from_start).pack(side='left')
        button(actions, 'Cancel', dialog.destroy).pack(side='left', padx=(8, 0))
        _center_dialog(dialog, viewer.root)

    def continue_from_start() -> None:
        if validate_coordinates() is None:
            return
        if kind_var.get() == 'Monument':
            show_monument()
        else:
            show_pillager_confirm()

    def show_monument() -> None:
        clear()
        coordinates = current_coordinates['value']
        label('Monument', bold=True).pack(anchor='w')
        label(f'Coords: {coordinates[0]}, {coordinates[1]}').pack(anchor='w', pady=(4, 8))
        label('Name').pack(anchor='w')
        viewer._make_sidebar_entry(container, monument_name_var).pack(fill='x', pady=(4, 8))
        label('Category').pack(anchor='w')
        viewer._make_sidebar_entry(container, monument_category_var).pack(fill='x', pady=(4, 8))
        categories = _poi_categories()
        if categories:
            label('Previous categories').pack(anchor='w', pady=(0, 4))
            shortcut_row = row()
            for category in categories[:6]:
                button(shortcut_row, category, lambda value=category: monument_category_var.set(value)).pack(
                    side='left',
                    padx=(0, 6),
                )
        actions = row()
        button(actions, 'Back', show_start).pack(side='left')
        button(actions, 'Review', show_monument_confirm).pack(side='left', padx=(8, 0))
        _center_dialog(dialog, viewer.root)

    def show_monument_confirm() -> None:
        category = monument_category_var.get().strip()
        if not category:
            messagebox.showerror('Missing Category', 'Enter a monument category.', parent=dialog)
            return
        coordinates = current_coordinates['value']
        name = monument_name_var.get().strip() or f'Unnamed {category}'
        clear()
        label('Confirm Monument', bold=True).pack(anchor='w')
        label(f'Name: {name}\nCategory: {category}\nCoords: {coordinates[0]}, {coordinates[1]}').pack(
            anchor='w',
            pady=(8, 8),
        )
        actions = row()
        button(actions, 'Back', show_monument).pack(side='left')
        button(actions, 'Add Monument', save_monument).pack(side='left', padx=(8, 0))
        _center_dialog(dialog, viewer.root)

    def save_monument() -> None:
        coordinates = current_coordinates['value']
        try:
            added = add_custom_point_of_interest(
                coordinates,
                kind='monument',
                label=monument_name_var.get(),
                category=monument_category_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror('Could Not Add Monument', str(exc), parent=dialog)
            return
        dialog.destroy()
        _refresh_viewer_after_add(viewer, added)

    def show_pillager_confirm() -> None:
        coordinates = current_coordinates['value']
        clear()
        label('Confirm Pillager Tower', bold=True).pack(anchor='w')
        label(f'Coords: {coordinates[0]}, {coordinates[1]}').pack(anchor='w', pady=(8, 8))
        actions = row()
        button(actions, 'Back', show_start).pack(side='left')
        button(actions, 'Add Tower', save_pillager).pack(side='left', padx=(8, 0))
        _center_dialog(dialog, viewer.root)

    def save_pillager() -> None:
        coordinates = current_coordinates['value']
        try:
            added = add_custom_point_of_interest(coordinates, kind='pillager_tower')
        except ValueError as exc:
            messagebox.showerror('Could Not Add Pillager Tower', str(exc), parent=dialog)
            return
        dialog.destroy()
        _refresh_viewer_after_add(viewer, added)

    show_start()
    _center_dialog(dialog, viewer.root)


def apply() -> None:
    base.MetroMapViewer._show_add_poi_dialog = show_add_poi_dialog  # type: ignore[attr-defined, method-assign]
