from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

import legacy_core as base

from plumville.desktop import workspace


SECTION_GAP = 12


def has_docked_inspector(viewer: "base.MetroMapViewer") -> bool:
    shell = getattr(viewer, "_desktop_workspace_shell", None)
    return bool(shell is not None and getattr(shell, "inspector_body", None) is not None)


def sync_inspector(viewer: "base.MetroMapViewer") -> None:
    if not has_docked_inspector(viewer):
        return
    if bool(getattr(viewer, "_desktop_inspector_task_active", False)):
        return

    stop_var = getattr(viewer, "selected_stop_var", None)
    if stop_var in base.STOPS_BY_VAR:
        workspace.show_inspector_for_task(viewer, ("station", stop_var))
        _render_selected_stop(viewer, base.STOPS_BY_VAR[stop_var])
        return

    path_node_getter = getattr(viewer, "_selected_path_node", None)
    path_node = path_node_getter() if callable(path_node_getter) else None
    if path_node is not None:
        workspace.show_inspector_for_task(viewer, ("path_node", path_node.key))
        _render_selected_path_node(viewer, path_node)
        return

    segment_getter = getattr(viewer, "_selected_metro_segment", None)
    segment = segment_getter() if callable(segment_getter) else None
    if segment is not None:
        workspace.show_inspector_for_task(
            viewer,
            (
                "metro_segment",
                segment.line_name,
                segment.start_var,
                segment.end_var,
            ),
        )
        _render_selected_metro_segment(viewer, segment)
        return

    path_click_mode_var = getattr(viewer, "path_click_mode_var", None)
    if path_click_mode_var is not None and bool(path_click_mode_var.get()):
        context_stop = _pathing_context_stop(viewer)
        task_key = (
            "pathing",
            None if context_stop is None else context_stop.var,
        )
        workspace.show_inspector_for_task(viewer, task_key)
        _render_pathing_context(viewer, context_stop=context_stop)
        return

    viewer._desktop_inspector_task_key = None
    _render_empty_state(viewer)


def _render_empty_state(viewer: "base.MetroMapViewer") -> None:
    shell = viewer._desktop_workspace_shell
    _clear_inspector_body(viewer)
    shell.inspector_header_label.configure(text="Inspector")

    container = tk.Frame(
        shell.inspector_body,
        bg=workspace.PANEL_BG,
    )
    container.pack(fill="both", expand=True)

    tk.Label(
        container,
        text="◆",
        bg=workspace.PANEL_BG,
        fg=workspace.ACCENT,
        font=("Courier", 34, "bold"),
        anchor="center",
    ).pack(pady=(18, 10))
    tk.Label(
        container,
        text="No station selected",
        bg=workspace.PANEL_BG,
        fg=workspace.TEXT,
        font=("Helvetica", 16, "bold"),
        anchor="center",
        justify="center",
    ).pack()
    tk.Label(
        container,
        text=(
            "Click a named station or frontier station on the map to inspect "
            "its status, lines, signage, and editing actions."
        ),
        bg=workspace.PANEL_BG,
        fg=workspace.MUTED,
        font=("Helvetica", 11),
        anchor="center",
        justify="center",
        wraplength=workspace.INSPECTOR_WIDTH - 72,
    ).pack(padx=18, pady=(10, 0))


def _render_selected_stop(
    viewer: "base.MetroMapViewer",
    stop: base.MetroStop,
) -> None:
    shell = viewer._desktop_workspace_shell
    _clear_inspector_body(viewer)
    shell.inspector_header_label.configure(text="Station Inspector")
    viewer.info_popup_variables = []

    header = tk.Frame(
        shell.inspector_body,
        bg=workspace.PANEL_RAISED,
        highlightbackground=workspace.BORDER,
        highlightthickness=1,
        bd=0,
        padx=14,
        pady=14,
    )
    header.pack(fill="x")

    header.grid_columnconfigure(0, weight=1)
    abbreviation = base._stop_abbreviation(stop)
    tk.Label(
        header,
        text=abbreviation,
        bg=workspace.PANEL_RAISED,
        fg=workspace.ACCENT,
        font=("Helvetica", 17, "bold"),
        anchor="w",
        justify="left",
    ).grid(row=0, column=0, sticky="w")
    line_badges = tk.Frame(header, bg=workspace.PANEL_RAISED)
    line_badges.grid(row=0, column=1, sticky="e")
    for line_name in sorted(base.STOP_LINE_NAMES.get(stop.var, ())):
        _make_line_diamond(
            line_badges,
            line_name=line_name,
            line_color=base.LINE_COLORS.get(line_name, workspace.PANEL_ALT_BG),
        ).pack(side="left", padx=(6, 0))

    title_row = tk.Frame(header, bg=workspace.PANEL_RAISED)
    title_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    title_row.grid_columnconfigure(0, weight=1)
    tk.Label(
        title_row,
        text=base._display_label(stop.lbl),
        bg=workspace.PANEL_RAISED,
        fg=workspace.TEXT,
        font=("Helvetica", 18, "bold"),
        anchor="w",
        justify="left",
        wraplength=210,
    ).grid(row=0, column=0, sticky="w")
    tk.Label(
        title_row,
        text=f"({stop.x},{stop.y})",
        bg=workspace.PANEL_RAISED,
        fg=workspace.MUTED,
        font=("Helvetica", 11, "bold"),
        anchor="e",
        justify="left",
    ).grid(row=0, column=1, sticky="e", padx=(10, 0))

    status_lines = _status_lines(stop)
    if status_lines:
        summary = tk.Frame(
            shell.inspector_body,
            bg=workspace.PANEL_BG,
            padx=2,
            pady=12,
        )
        summary.pack(fill="x")
        _make_detail_block(
            summary,
            title="Status",
            lines=status_lines,
        ).pack(fill="x")

    path_click_mode_var = getattr(viewer, "path_click_mode_var", None)
    if path_click_mode_var is not None and bool(path_click_mode_var.get()):
        _render_pathing_town_section(viewer, shell.inspector_body, stop)

    construction_section = _make_section(shell.inspector_body, title="Construction")
    construction_section.pack(fill="x", pady=(0, SECTION_GAP))
    _populate_checkpoint_section(viewer, construction_section, stop)

    signage_section = _make_section(shell.inspector_body, title="Signs")
    signage_section.pack(fill="x", pady=(0, SECTION_GAP))
    viewer._draw_station_signage_panel(signage_section, stop)

    actions_section = _make_section(shell.inspector_body, title="Actions")
    actions_section.pack(fill="x", pady=(0, SECTION_GAP))
    _action_section(
        viewer,
        actions_section,
        title="Edit",
        actions=[
            ("Name", viewer._edit_selected_label),
            ("Coords", viewer._edit_selected_coordinates),
            ("Station Entry", viewer._edit_selected_station_entry),
        ],
    )
    manage_actions: list[tuple[str, Callable[[], None]]] = [
        ("Lines", lambda active_stop_var=stop.var: _prompt_selected_stop_line_action(viewer, active_stop_var)),
        ("Paths", lambda active_stop_var=stop.var: viewer._activate_station_pathing(active_stop_var)),
        ("Alignments", viewer._manage_selected_alignments),
    ]
    if viewer.city_limits_edit_stop_var == stop.var:
        manage_actions.append(("Clear", viewer._clear_selected_city_limits))
    _action_section(
        viewer,
        actions_section,
        title="Manage",
        actions=manage_actions,
    )

    reminders = base._alignment_reminders_for_stop(stop.var)
    if reminders:
        reminders_section = _make_section(shell.inspector_body, title="Alignment Reminders")
        reminders_section.pack(fill="x", pady=(0, SECTION_GAP))
        for reminder in reminders:
            tk.Label(
                reminders_section,
                text=reminder.debug_label,
                bg=workspace.PANEL_BG,
                fg=workspace.TEXT,
                font=("Helvetica", 10),
                anchor="w",
                justify="left",
                wraplength=workspace.INSPECTOR_WIDTH - 78,
            ).pack(anchor="w", pady=(0, 6))


def _render_selected_metro_segment(
    viewer: "base.MetroMapViewer",
    segment: base.MetroLineSegment,
) -> None:
    shell = viewer._desktop_workspace_shell
    _clear_inspector_body(viewer)
    shell.inspector_header_label.configure(text="Segment Inspector")

    header = tk.Frame(
        shell.inspector_body,
        bg=workspace.PANEL_RAISED,
        highlightbackground=workspace.BORDER,
        highlightthickness=1,
        bd=0,
        padx=14,
        pady=14,
    )
    header.pack(fill="x")
    _make_line_badge(
        header,
        line_name=segment.line_name,
        line_color=base.LINE_COLORS.get(segment.line_name, workspace.PANEL_ALT_BG),
    ).pack(side="right", anchor="ne")
    tk.Label(
        header,
        text=f"Line {segment.line_name}",
        bg=workspace.PANEL_RAISED,
        fg=workspace.ACCENT,
        font=("Courier", 12, "bold"),
        anchor="w",
        justify="left",
    ).pack(anchor="w")
    tk.Label(
        header,
        text=(
            f"{base._display_label(segment.start_stop.lbl)} to "
            f"{base._display_label(segment.end_stop.lbl)}"
        ),
        bg=workspace.PANEL_RAISED,
        fg=workspace.TEXT,
        font=("Helvetica", 15, "bold"),
        anchor="w",
        justify="left",
        wraplength=workspace.INSPECTOR_WIDTH - 92,
    ).pack(anchor="w", pady=(8, 0))

    details = _make_section(shell.inspector_body, title="Track")
    details.pack(fill="x", pady=(SECTION_GAP, SECTION_GAP))
    selected_segments = viewer._selected_metro_segments()
    lines = [
        f"Shape: {segment.shape_label}",
        f"Distance: {base._format_distance_and_time(base._polyline_distance(segment.plot_points))}",
    ]
    if len(selected_segments) > 1:
        selected_distance = sum(
            base._polyline_distance(active_segment.plot_points)
            for active_segment in selected_segments
        )
        lines.append(f"Selected legs: {len(selected_segments)}")
        lines.append(
            f"Selected total: {base._format_distance_and_time(selected_distance)}"
        )
    for line in lines:
        tk.Label(
            details,
            text=line,
            bg=workspace.PANEL_BG,
            fg=workspace.TEXT,
            font=("Helvetica", 10),
            anchor="w",
            justify="left",
            wraplength=workspace.INSPECTOR_WIDTH - 78,
        ).pack(anchor="w", pady=(0, 4))

    actions = _make_section(shell.inspector_body, title="Actions")
    actions.pack(fill="x")
    _metro_segment_action_buttons(viewer, actions, segment)


def _render_selected_path_node(
    viewer: "base.MetroMapViewer",
    path_node: base.PathNode,
) -> None:
    shell = viewer._desktop_workspace_shell
    _clear_inspector_body(viewer)
    shell.inspector_header_label.configure(text="Map Pathing")
    viewer.info_popup_variables = []

    extra_edges = base._extra_edges_for_endpoint_key(path_node.key)
    detail_lines = (
        f"Current node: {path_node.display_label}",
        f"Coords: ({path_node.x}, {path_node.y})",
        f"Type: {base._path_node_type_label(path_node)}",
        f"Path edges: {len(extra_edges)}",
    )
    _make_detail_block(
        shell.inspector_body,
        title="Node",
        lines=detail_lines,
    ).pack(fill="x", pady=(0, SECTION_GAP))

    town = _pathing_context_stop(viewer)
    _render_pathing_town_section(viewer, shell.inspector_body, town)

    actions = _make_section(shell.inspector_body, title="Actions")
    actions.pack(fill="x")
    action_items = [
        ("Connect", lambda: viewer._add_path_for_selected_node("walk")),
        ("Edit", viewer._edit_selected_path_node_coordinates),
        ("Remove", viewer._remove_selected_path_node),
    ]
    _action_section(
        viewer,
        actions,
        title="Node",
        actions=action_items,
    )

    if extra_edges:
        edges = _make_section(shell.inspector_body, title="Path Edges")
        edges.pack(fill="x", pady=(SECTION_GAP, 0))
        for extra_edge in extra_edges:
            edge_row = tk.Frame(edges, bg=workspace.PANEL_BG)
            edge_row.pack(fill="x", pady=(0, 6))
            tk.Label(
                edge_row,
                text=base._extra_edge_full_summary(extra_edge),
                bg=workspace.PANEL_BG,
                fg=workspace.TEXT,
                font=("Helvetica", 10),
                anchor="w",
                justify="left",
                wraplength=workspace.INSPECTOR_WIDTH - 132,
            ).pack(side="left", fill="x", expand=True)
            viewer._make_info_button(
                edge_row,
                text="Remove",
                command=lambda edge=extra_edge: viewer._remove_path_edge(edge),
            ).pack(side="right", padx=(8, 0))


def _render_pathing_context(
    viewer: "base.MetroMapViewer",
    *,
    context_stop: base.MetroStop | None = None,
) -> None:
    shell = viewer._desktop_workspace_shell
    _clear_inspector_body(viewer)
    shell.inspector_header_label.configure(text="Map Pathing")

    town = context_stop if context_stop is not None else _pathing_context_stop(viewer)
    if town is None:
        container = _make_section(shell.inspector_body, title="Town")
        container.pack(fill="x")
        tk.Label(
            container,
            text=(
                "Zoom closer to the town you are mapping, or select a station "
                "so Plumville can attach new nodes and city limits to the right place."
            ),
            bg=workspace.PANEL_BG,
            fg=workspace.TEXT,
            font=("Helvetica", 10),
            anchor="w",
            justify="left",
            wraplength=workspace.INSPECTOR_WIDTH - 78,
        ).pack(anchor="w", pady=(0, 8))
        viewer._make_info_button(
            container,
            text="Choose Town",
            command=viewer._edit_pathing_town_context,
        ).pack(anchor="w")
        return

    _render_pathing_town_section(viewer, shell.inspector_body, town)

    guide = _make_section(shell.inspector_body, title="Map")
    guide.pack(fill="x", pady=(SECTION_GAP, 0))
    for line in (
        "Click empty map space to add a node.",
        "Drag from a station or node to another station or node to add a path.",
        str(viewer.path_click_status_var.get()),
    ):
        tk.Label(
            guide,
            text=line,
            bg=workspace.PANEL_BG,
            fg=workspace.TEXT if line != str(viewer.path_click_status_var.get()) else workspace.MUTED,
            font=("Helvetica", 10),
            anchor="w",
            justify="left",
            wraplength=workspace.INSPECTOR_WIDTH - 78,
        ).pack(anchor="w", pady=(0, 4))


def _pathing_context_stop(
    viewer: "base.MetroMapViewer",
) -> base.MetroStop | None:
    context_getter = getattr(viewer, "_pathing_context_stop", None)
    if not callable(context_getter):
        return None
    return context_getter()


def _render_pathing_town_section(
    viewer: "base.MetroMapViewer",
    parent: tk.Misc,
    town: base.MetroStop | None,
) -> None:
    if town is None:
        return

    owned_keys = viewer._suggested_city_limit_node_keys_for_stop(town.var)
    town_section = _make_section(parent, title="Town")
    town_section.pack(fill="x", pady=(0, SECTION_GAP))
    for line in (
        f"Detected town: {base._station_display_name(town)}",
        f"Town nodes: {len(owned_keys)}",
    ):
        tk.Label(
            town_section,
            text=line,
            bg=workspace.PANEL_BG,
            fg=workspace.TEXT,
            font=("Helvetica", 10),
            anchor="w",
            justify="left",
            wraplength=workspace.INSPECTOR_WIDTH - 78,
        ).pack(anchor="w", pady=(0, 4))
    viewer._make_info_button(
        town_section,
        text="Change Town",
        command=viewer._edit_pathing_town_context,
    ).pack(anchor="w", pady=(0, 8))
    _render_city_limit_controls(viewer, town_section, town, owned_keys)


def _render_city_limit_controls(
    viewer: "base.MetroMapViewer",
    parent: tk.Misc,
    town: base.MetroStop,
    owned_node_keys: tuple[str, ...],
) -> None:
    is_editing = getattr(viewer, "city_limits_edit_stop_var", None) == town.var
    pending_keys = tuple(getattr(viewer, "city_limits_pending_node_keys", ()))
    saved_count = len(town.city_limit_node_keys)
    suggested_count = len(owned_node_keys)
    active_count = len(pending_keys) if is_editing else saved_count

    lines: list[str] = []
    if is_editing:
        lines.append(f"Selected boundary nodes: {active_count}")
        lines.append("Click any town node to add or remove it. The polygon order is handled automatically.")
    elif saved_count:
        lines.append(f"Saved boundary nodes: {saved_count}")
    elif suggested_count:
        lines.append(f"Suggested boundary nodes: {suggested_count}")
    else:
        lines.append("No town nodes are available for a city-limit suggestion yet.")

    tk.Label(
        parent,
        text="City Limits",
        bg=workspace.PANEL_BG,
        fg=workspace.ACCENT,
        font=("Courier", 10, "bold"),
        anchor="w",
    ).pack(anchor="w", pady=(4, 6))
    for line in lines:
        tk.Label(
            parent,
            text=line,
            bg=workspace.PANEL_BG,
            fg=workspace.TEXT,
            font=("Helvetica", 10),
            anchor="w",
            justify="left",
            wraplength=workspace.INSPECTOR_WIDTH - 78,
        ).pack(anchor="w", pady=(0, 4))

    actions: list[tuple[str, Callable[[], None]]] = []
    if is_editing:
        actions.extend(
            [
                ("Confirm", viewer._confirm_city_limits_edit),
                ("Cancel", viewer._cancel_city_limits_edit),
            ]
        )
        if saved_count:
            actions.append(("Clear", viewer._clear_selected_city_limits))
    elif saved_count:
        actions.append(("Edit", lambda active_stop_var=town.var: viewer._start_city_limits_edit(active_stop_var)))
        actions.append(("Clear", viewer._clear_selected_city_limits))
    elif suggested_count:
        actions.append(("Review", lambda active_stop_var=town.var: viewer._start_city_limits_edit(active_stop_var)))

    if actions:
        _action_section(
            viewer,
            parent,
            title="Limits",
            actions=actions,
        )


def _metro_segment_action_buttons(
    viewer: "base.MetroMapViewer",
    parent: tk.Misc,
    segment: base.MetroLineSegment,
) -> None:
    row = tk.Frame(parent, bg=workspace.PANEL_BG)
    row.pack(anchor="w", fill="x")
    buttons: list[tuple[str, Callable[[], None]]] = []
    if segment.can_turn:
        buttons.append(
            (
                "Add Turn" if segment.shape_label == "direct" else "Edit Turn",
                lambda active_segment=segment: viewer._add_turn_to_metro_segment(active_segment),
            )
        )
    buttons.append(
        (
            "Edit Endpoints",
            lambda active_segment=segment: viewer._edit_metro_segment_endpoints(active_segment),
        )
    )
    if segment.shape_label != "direct":
        buttons.append(
            (
                "Direct",
                lambda active_segment=segment: viewer._make_metro_segment_direct(active_segment),
            )
        )
        if segment.can_turn and segment.turn_variant is not None:
            buttons.append(
                (
                    "Flip Turn",
                    lambda active_segment=segment: viewer._flip_metro_segment_turn(active_segment),
                )
            )
    for index, (text, command) in enumerate(buttons):
        viewer._make_info_button(row, text=text, command=command).pack(
            side="left",
            padx=(0, 6 if index < len(buttons) - 1 else 0),
        )


def _clear_inspector_body(viewer: "base.MetroMapViewer") -> None:
    shell = viewer._desktop_workspace_shell
    for child in shell.inspector_body.winfo_children():
        child.destroy()


def show_metro_turn_editor(
    viewer: "base.MetroMapViewer",
    segment: base.MetroLineSegment,
) -> bool:
    if not has_docked_inspector(viewer):
        return False

    payload = base._load_network_payload()
    default_options = base._default_turn_coordinate_options_for_metro_segment_in_payload(
        payload,
        segment.line_name,
        segment.start_var,
        segment.end_var,
    )
    current_custom_coordinates = tuple(
        (point[0], -point[1]) for point in segment.plot_points[1:-1]
    )
    current_variant = segment.turn_variant

    container = _begin_task_view(
        viewer,
        header="Segment Editor",
        title=(
            f"{base._display_label(segment.start_stop.lbl)} to "
            f"{base._display_label(segment.end_stop.lbl)}"
        ),
        caption="Choose a default corner turn or enter custom multi-turn coordinates.",
    )
    mode_var = tk.StringVar(
        master=container,
        value=(
            "default-1"
            if current_variant == 1
            else ("custom" if segment.shape_label == "custom" else "default-0")
        ),
    )
    custom_coordinates_var = tk.StringVar(
        master=container,
        value=" | ".join(f"{x}, {y}" for x, y in current_custom_coordinates)
        if segment.shape_label == "custom"
        else "",
    )
    preview_var = tk.StringVar(master=container, value="")

    actions = tk.Frame(container, bg=workspace.PANEL_BG)
    actions.pack(fill="x", pady=(0, 12))

    def cancel() -> None:
        _finish_task_view(viewer)

    def save() -> None:
        try:
            if mode_var.get() == "custom":
                parsed_coordinates = base._parse_coordinate_sequence_text(
                    custom_coordinates_var.get()
                )
                if parsed_coordinates is None:
                    raise ValueError("Enter custom coordinates in the format x, y | x, y.")
                base.set_metro_line_segment_custom_points(
                    segment.line_name,
                    segment.start_var,
                    segment.end_var,
                    parsed_coordinates,
                )
            else:
                variant = 0 if mode_var.get() == "default-0" else 1
                base.set_metro_line_segment_turn_variant(
                    segment.line_name,
                    segment.start_var,
                    segment.end_var,
                    variant,
                )
        except ValueError as exc:
            messagebox.showerror("Could Not Save Metro Turn", str(exc), parent=viewer.root)
            return
        _finish_task_view(viewer, refresh_after_path_edit=True)

    viewer._make_sidebar_button(actions, text="Save Turn", command=save).pack(side="left")
    viewer._make_sidebar_button(actions, text="Cancel", command=cancel).pack(
        side="left",
        padx=(8, 0),
    )

    options = _make_section(container, title="Turn Shape")
    options.pack(fill="x", pady=(0, SECTION_GAP))
    option_texts = (
        (
            "default-0",
            f"{base._default_turn_direction_label(segment.start_stop.coordinates, segment.end_stop.coordinates, default_options[0])}: "
            f"{base._format_coordinate_list(default_options[0])}",
        ),
        (
            "default-1",
            f"{base._default_turn_direction_label(segment.start_stop.coordinates, segment.end_stop.coordinates, default_options[1])}: "
            f"{base._format_coordinate_list(default_options[1])}",
        ),
        ("custom", "Custom coordinates"),
    )
    for option_value, option_text in option_texts:
        tk.Radiobutton(
            options,
            text=option_text,
            value=option_value,
            variable=mode_var,
            bg=workspace.PANEL_BG,
            fg=workspace.TEXT,
            selectcolor=workspace.PANEL_ALT_BG,
            activebackground=workspace.PANEL_BG,
            activeforeground=workspace.TEXT,
            anchor="w",
            justify="left",
            font=("Helvetica", 10),
            wraplength=workspace.INSPECTOR_WIDTH - 78,
        ).pack(anchor="w", pady=(0, 6))

    custom = _make_section(container, title="Custom")
    custom.pack(fill="x", pady=(0, SECTION_GAP))
    viewer._make_sidebar_entry(custom, custom_coordinates_var).pack(fill="x")
    tk.Label(
        custom,
        text="Separate coordinates with |, ;, or new lines.",
        bg=workspace.PANEL_BG,
        fg=workspace.MUTED,
        font=("Helvetica", 10),
        anchor="w",
        justify="left",
        wraplength=workspace.INSPECTOR_WIDTH - 78,
    ).pack(anchor="w", pady=(6, 0))

    preview = _make_section(container, title="Preview")
    preview.pack(fill="x")
    tk.Label(
        preview,
        textvariable=preview_var,
        bg=workspace.PANEL_BG,
        fg=workspace.TEXT,
        font=("Helvetica", 10),
        anchor="w",
        justify="left",
        wraplength=workspace.INSPECTOR_WIDTH - 78,
    ).pack(anchor="w")

    def refresh_preview(*_args: object) -> None:
        mode = mode_var.get()
        if mode == "custom":
            parsed_coordinates = base._parse_coordinate_sequence_text(
                custom_coordinates_var.get()
            )
            if parsed_coordinates is None:
                preview_var.set("Enter coordinates as x, y values.")
                viewer._clear_metro_segment_preview()
                return
            normalized_coordinates = base._normalize_segment_via_coordinates(
                segment.start_stop.coordinates,
                segment.end_stop.coordinates,
                parsed_coordinates,
            )
            preview_var.set(base._format_coordinate_list(normalized_coordinates))
            viewer._set_metro_segment_preview(
                base._segment_preview_plot_points(
                    segment.start_stop.coordinates,
                    segment.end_stop.coordinates,
                    normalized_coordinates,
                )
            )
            return
        variant = 0 if mode == "default-0" else 1
        preview_var.set(base._format_coordinate_list(default_options[variant]))
        viewer._set_metro_segment_preview(
            base._segment_preview_plot_points(
                segment.start_stop.coordinates,
                segment.end_stop.coordinates,
                default_options[variant],
            )
        )

    for variable in (mode_var, custom_coordinates_var):
        variable.trace_add("write", refresh_preview)
    refresh_preview()
    return True


def show_metro_endpoint_editor(
    viewer: "base.MetroMapViewer",
    segment: base.MetroLineSegment,
) -> bool:
    if not has_docked_inspector(viewer):
        return False

    container = _begin_task_view(
        viewer,
        header="Segment Editor",
        title=(
            f"{base._display_label(segment.start_stop.lbl)} to "
            f"{base._display_label(segment.end_stop.lbl)}"
        ),
        caption="Edit segment endpoints for junction offsets while preserving middle turn points.",
    )
    start_coordinates = (segment.plot_points[0][0], -segment.plot_points[0][1])
    end_coordinates = (segment.plot_points[-1][0], -segment.plot_points[-1][1])
    start_var = tk.StringVar(
        master=container,
        value=f"{start_coordinates[0]}, {start_coordinates[1]}",
    )
    end_var = tk.StringVar(
        master=container,
        value=f"{end_coordinates[0]}, {end_coordinates[1]}",
    )
    preview_var = tk.StringVar(master=container, value="")
    middle_coordinates = tuple(
        (point[0], -point[1]) for point in segment.plot_points[1:-1]
    )

    actions = tk.Frame(container, bg=workspace.PANEL_BG)
    actions.pack(fill="x", pady=(0, 12))

    def cancel() -> None:
        _finish_task_view(viewer)

    def save() -> None:
        parsed_start = base._parse_coordinate_text(start_var.get())
        parsed_end = base._parse_coordinate_text(end_var.get())
        if parsed_start is None or parsed_end is None:
            messagebox.showerror(
                "Could Not Save Endpoints",
                "Enter coordinates in the format x, y.",
                parent=viewer.root,
            )
            return
        try:
            base.set_metro_line_segment_endpoint_coordinates(
                segment.line_name,
                segment.start_var,
                segment.end_var,
                start_coordinates=parsed_start,
                end_coordinates=parsed_end,
            )
        except ValueError as exc:
            messagebox.showerror("Could Not Save Endpoints", str(exc), parent=viewer.root)
            return
        _finish_task_view(viewer, refresh_after_path_edit=True)

    viewer._make_sidebar_button(actions, text="Save Endpoints", command=save).pack(
        side="left"
    )
    viewer._make_sidebar_button(actions, text="Cancel", command=cancel).pack(
        side="left",
        padx=(8, 0),
    )

    fields = _make_section(container, title="Endpoint Coordinates")
    fields.pack(fill="x", pady=(0, SECTION_GAP))
    _field_row(viewer, fields, label="Start", variable=start_var)
    _field_row(viewer, fields, label="End", variable=end_var)
    tk.Label(
        fields,
        text="Use x, y coordinates. Middle turn/custom points are kept.",
        bg=workspace.PANEL_BG,
        fg=workspace.MUTED,
        font=("Helvetica", 10),
        anchor="w",
        justify="left",
        wraplength=workspace.INSPECTOR_WIDTH - 78,
    ).pack(anchor="w", pady=(6, 0))

    preview = _make_section(container, title="Preview")
    preview.pack(fill="x")
    tk.Label(
        preview,
        textvariable=preview_var,
        bg=workspace.PANEL_BG,
        fg=workspace.TEXT,
        font=("Helvetica", 10),
        anchor="w",
        justify="left",
        wraplength=workspace.INSPECTOR_WIDTH - 78,
    ).pack(anchor="w")

    def refresh_preview(*_args: object) -> None:
        parsed_start = base._parse_coordinate_text(start_var.get())
        parsed_end = base._parse_coordinate_text(end_var.get())
        if parsed_start is None or parsed_end is None:
            preview_var.set("Enter both endpoints as x, y.")
            viewer._clear_metro_segment_preview()
            return
        preview_var.set(
            f"Start ({parsed_start[0]}, {parsed_start[1]}) -> "
            f"{base._format_coordinate_list(middle_coordinates)} -> "
            f"End ({parsed_end[0]}, {parsed_end[1]})"
        )
        viewer._set_metro_segment_preview(
            base._segment_preview_plot_points(parsed_start, parsed_end, middle_coordinates)
        )

    for variable in (start_var, end_var):
        variable.trace_add("write", refresh_preview)
    refresh_preview()
    return True


def _begin_task_view(
    viewer: "base.MetroMapViewer",
    *,
    header: str,
    title: str,
    caption: str,
) -> tk.Frame:
    shell = viewer._desktop_workspace_shell
    viewer._desktop_inspector_task_active = True
    _clear_inspector_body(viewer)
    shell.inspector_header_label.configure(text=header)
    container = tk.Frame(shell.inspector_body, bg=workspace.PANEL_BG)
    container.pack(fill="both", expand=True)
    tk.Label(
        container,
        text=title,
        bg=workspace.PANEL_BG,
        fg=workspace.TEXT,
        font=("Helvetica", 15, "bold"),
        anchor="w",
        justify="left",
        wraplength=workspace.INSPECTOR_WIDTH - 54,
    ).pack(anchor="w")
    tk.Label(
        container,
        text=caption,
        bg=workspace.PANEL_BG,
        fg=workspace.MUTED,
        font=("Helvetica", 10),
        anchor="w",
        justify="left",
        wraplength=workspace.INSPECTOR_WIDTH - 54,
    ).pack(anchor="w", pady=(6, 12))
    return container


def _finish_task_view(
    viewer: "base.MetroMapViewer",
    *,
    refresh_after_path_edit: bool = False,
) -> None:
    viewer._desktop_inspector_task_active = False
    viewer._clear_metro_segment_preview()
    if refresh_after_path_edit:
        viewer._refresh_after_path_edit()
    else:
        sync_inspector(viewer)


def _field_row(
    viewer: "base.MetroMapViewer",
    parent: tk.Misc,
    *,
    label: str,
    variable: tk.StringVar,
) -> None:
    row = tk.Frame(parent, bg=workspace.PANEL_BG)
    row.pack(fill="x", pady=(0, 8))
    tk.Label(
        row,
        text=label,
        bg=workspace.PANEL_BG,
        fg=workspace.MUTED,
        font=("Courier", 10, "bold"),
        width=6,
        anchor="w",
    ).pack(side="left")
    viewer._make_sidebar_entry(row, variable).pack(side="left", fill="x", expand=True)


def _status_lines(stop: base.MetroStop) -> tuple[str, ...]:
    missing_tasks = base._missing_station_tasks(stop)
    lines: list[str] = (
        [f"Needs: {base._join_priority_tasks(missing_tasks)}"]
        if missing_tasks
        else []
    )
    reminders = base._alignment_reminders_for_stop(stop.var)
    if reminders:
        lines.append(f"Alignments: {len(reminders)} active")
    if stop.is_connected:
        completed_chime_count = base._station_completed_chime_count(stop)
        max_chime_count = base._station_max_chime_count(stop)
        if max_chime_count > 0 and completed_chime_count < max_chime_count:
            lines.append(f"Chimes: {completed_chime_count}/{max_chime_count}")
    return tuple(lines)


def _populate_checkpoint_section(
    viewer: "base.MetroMapViewer",
    parent: tk.Misc,
    stop: base.MetroStop,
) -> None:
    viewer._make_info_checkbox(
        parent,
        text="Has Name",
        checked=stop.has_name,
        enabled=False,
    ).pack(anchor="w")
    viewer._make_info_checkbox(
        parent,
        text="Façade",
        checked=stop.has_connector,
        on_toggle=lambda value: viewer._update_selected_checkpoint("has_connector", value),
    ).pack(anchor="w")
    if stop.has_connector:
        viewer._make_info_checkbox(
            parent,
            text="Station Entry",
            checked=stop.station_entry_coordinates is not None,
            enabled=False,
        ).pack(anchor="w")
    viewer._make_info_checkbox(
        parent,
        text="Station",
        checked=stop.has_full_station,
        on_toggle=lambda value: viewer._update_selected_checkpoint("has_full_station", value),
    ).pack(anchor="w")
    viewer._make_info_checkbox(
        parent,
        text="Walking Paths",
        checked=stop.has_walking_paths,
        on_toggle=lambda value: viewer._update_selected_checkpoint("has_walking_paths", value),
    ).pack(anchor="w")
    if stop.has_walking_paths:
        viewer._make_info_checkbox(
            parent,
            text="City Limits",
            checked=bool(stop.city_limit_node_keys),
            enabled=False,
        ).pack(anchor="w")
    viewer._make_info_checkbox(
        parent,
        text="Tunneled",
        checked=stop.is_tunneled,
        on_toggle=lambda value: viewer._update_selected_checkpoint("is_tunneled", value),
    ).pack(anchor="w")
    if stop.is_tunneled:
        viewer._make_info_checkbox(
            parent,
            text="Connected",
            checked=stop.is_connected,
            on_toggle=lambda value: viewer._update_selected_checkpoint("is_connected", value),
        ).pack(anchor="w")
    if stop.is_connected and base.SHOW_RAILWAY_FINISHING_UI:
        viewer._make_info_checkbox(
            parent,
            text="Finished Railway",
            checked=stop.has_finished_railway,
            on_toggle=lambda value: viewer._update_selected_checkpoint("has_finished_railway", value),
        ).pack(anchor="w")
    if base._station_signs_available(stop):
        viewer._make_info_checkbox(
            parent,
            text="Signs",
            checked=stop.has_signs,
            on_toggle=lambda value: viewer._update_selected_checkpoint("has_signs", value),
        ).pack(anchor="w")
    if stop.is_connected:
        chime_outlet_directions = base._station_chime_outlet_directions(stop.var)
        if chime_outlet_directions:
            tk.Label(
                parent,
                text="Chimes",
                bg=workspace.PANEL_BG,
                fg=workspace.TEXT,
                font=("Helvetica", 10, "bold"),
                anchor="w",
                justify="left",
            ).pack(anchor="w", pady=(8, 0))
            for direction in chime_outlet_directions:
                viewer._make_info_checkbox(
                    parent,
                    text=f"{base.CHIME_DIRECTION_LABELS[direction]} Chime",
                    checked=direction in stop.chime_directions,
                    on_toggle=lambda value, chime_direction=direction: viewer._update_selected_chime_direction(
                        chime_direction,
                        value,
                    ),
                ).pack(anchor="w")


def _make_station_diamond(
    parent: tk.Misc,
    *,
    stop_var: str,
) -> tk.Canvas:
    size = 48
    radius = 18 if len(base.STOP_LINE_NAMES.get(stop_var, ())) >= 2 else 15
    diamond = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=workspace.PANEL_RAISED,
        highlightthickness=0,
        bd=0,
    )
    diamond.create_polygon(
        (
            size / 2,
            size / 2 - radius,
            size / 2 + radius,
            size / 2,
            size / 2,
            size / 2 + radius,
            size / 2 - radius,
            size / 2,
        ),
        fill=workspace.ACCENT,
        outline=workspace.TEXT,
        width=2,
    )
    if len(base.STOP_LINE_NAMES.get(stop_var, ())) >= 2:
        inner_radius = radius - 6
        diamond.create_polygon(
            (
                size / 2,
                size / 2 - inner_radius,
                size / 2 + inner_radius,
                size / 2,
                size / 2,
                size / 2 + inner_radius,
                size / 2 - inner_radius,
                size / 2,
            ),
            fill="",
            outline=workspace.TEXT,
            width=1,
        )
    return diamond


def _make_line_diamond(
    parent: tk.Misc,
    *,
    line_name: str,
    line_color: str,
) -> tk.Canvas:
    size = 32
    radius = 13
    foreground = workspace.TEXT
    diamond = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=workspace.PANEL_RAISED,
        highlightthickness=0,
        bd=0,
    )
    diamond.create_polygon(
        (
            size / 2,
            size / 2 - radius,
            size / 2 + radius,
            size / 2,
            size / 2,
            size / 2 + radius,
            size / 2 - radius,
            size / 2,
        ),
        fill=line_color,
        outline=foreground,
        width=2,
    )
    diamond.create_text(
        size / 2,
        size / 2,
        text=line_name,
        fill=foreground,
        font=("Courier", 10, "bold"),
    )
    return diamond


def _make_line_badge(
    parent: tk.Misc,
    *,
    line_name: str,
    line_color: str,
) -> tk.Canvas:
    size = 28
    foreground = _line_badge_foreground(line_color)
    badge = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=workspace.PANEL_RAISED,
        highlightthickness=0,
        bd=0,
    )
    badge.create_oval(
        2,
        2,
        size - 2,
        size - 2,
        fill=line_color,
        outline=foreground,
        width=2,
    )
    badge.create_text(
        size / 2,
        size / 2,
        text=line_name,
        fill=foreground,
        font=("Courier", 10, "bold"),
    )
    return badge


def _line_badge_foreground(line_color: str) -> str:
    if len(line_color) != 7 or not line_color.startswith("#"):
        return workspace.TEXT
    try:
        red = int(line_color[1:3], 16)
        green = int(line_color[3:5], 16)
        blue = int(line_color[5:7], 16)
    except ValueError:
        return workspace.TEXT
    brightness = (red * 299) + (green * 587) + (blue * 114)
    return "#091117" if brightness >= 140000 else workspace.TEXT


def _make_section(
    parent: tk.Misc,
    *,
    title: str,
) -> tk.Frame:
    container = tk.Frame(
        parent,
        bg=workspace.PANEL_BG,
        highlightbackground=workspace.BORDER,
        highlightthickness=1,
        bd=0,
        padx=12,
        pady=10,
    )
    tk.Label(
        container,
        text=title,
        bg=workspace.PANEL_BG,
        fg=workspace.ACCENT,
        font=("Courier", 11, "bold"),
        anchor="w",
    ).pack(anchor="w", pady=(0, 8))
    return container


def _make_detail_block(
    parent: tk.Misc,
    *,
    title: str,
    lines: tuple[str, ...],
) -> tk.Frame:
    block = _make_section(parent, title=title)
    for line in lines:
        tk.Label(
            block,
            text=line,
            bg=workspace.PANEL_BG,
            fg=workspace.TEXT,
            font=("Helvetica", 10),
            anchor="w",
            justify="left",
            wraplength=workspace.INSPECTOR_WIDTH - 78,
        ).pack(anchor="w", pady=(0, 4))
    return block


def _action_section(
    viewer: "base.MetroMapViewer",
    parent: tk.Misc,
    *,
    title: str,
    actions: list[tuple[str, Callable[[], None]]],
) -> None:
    row = tk.Frame(parent, bg=workspace.PANEL_BG)
    row.pack(fill="x", pady=(0, 8))
    tk.Label(
        row,
        text=title,
        bg=workspace.PANEL_BG,
        fg=workspace.MUTED,
        font=("Courier", 10, "bold"),
        width=8,
        anchor="w",
        justify="left",
    ).pack(side="left")
    strip = tk.Frame(row, bg=workspace.PANEL_BG)
    strip.pack(side="left", fill="x", expand=True)
    for index, (text, command) in enumerate(actions):
        viewer._make_info_button(
            strip,
            text=text,
            command=command,
        ).pack(side="left", padx=(0, 6 if index < len(actions) - 1 else 0))


def _available_selected_stop_line_actions(
    stop_var: str,
    metro_ext: object | None,
) -> tuple[str, ...]:
    current_line_names = tuple(base.STOP_LINE_NAMES.get(stop_var, ()))
    actions: list[str] = []
    if metro_ext is not None and base.LINE_STOP_VARS:
        default_addable_line = getattr(metro_ext, "_default_addable_line", None)
        if callable(default_addable_line) and default_addable_line(stop_var):
            actions.append("Add")
        switchable_target_lines = getattr(metro_ext, "_switchable_target_lines", None)
        if current_line_names and callable(switchable_target_lines) and switchable_target_lines(stop_var):
            actions.append("Switch")
    if current_line_names:
        actions.append("Remove")
    return tuple(actions)


def _show_choice_dialog(
    viewer: "base.MetroMapViewer",
    *,
    title: str,
    message: str,
    choices: list[tuple[str, Callable[[], None]]],
) -> None:
    dialog = tk.Toplevel(viewer.root)
    dialog.title(title)
    dialog.transient(viewer.root)
    dialog.resizable(False, False)

    container = tk.Frame(
        dialog,
        bg=workspace.PANEL_BG,
        padx=18,
        pady=16,
    )
    container.pack(fill="both", expand=True)
    tk.Label(
        container,
        text=message,
        bg=workspace.PANEL_BG,
        fg=workspace.TEXT,
        font=("Helvetica", 12, "bold"),
        anchor="w",
        justify="left",
        wraplength=520,
    ).pack(anchor="w")

    row = tk.Frame(container, bg=workspace.PANEL_BG)
    row.pack(anchor="w", fill="x", pady=(12, 0))

    def run_choice(callback: Callable[[], None]) -> None:
        try:
            dialog.grab_release()
        except tk.TclError:
            pass
        dialog.destroy()
        callback()

    for index, (label, callback) in enumerate(choices):
        viewer._make_info_button(
            row,
            text=label,
            command=lambda active_callback=callback: run_choice(active_callback),
        ).pack(side="left", padx=(0, 6 if index < len(choices) - 1 else 0))
    viewer._make_info_button(
        row,
        text="Cancel",
        command=dialog.destroy,
    ).pack(side="left", padx=(6 if choices else 0, 0))

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.update_idletasks()
    base._center_dialog(dialog, viewer.root)
    dialog.grab_set()
    dialog.focus_force()


def _prompt_remove_selected_stop_from_line(
    viewer: "base.MetroMapViewer",
    stop_var: str,
) -> None:
    stop = base.STOPS_BY_VAR.get(stop_var)
    if stop is None:
        return
    line_names = tuple(base.STOP_LINE_NAMES.get(stop_var, ()))
    if not line_names:
        messagebox.showinfo(
            "Remove From Line",
            f"{base._display_label(stop.lbl)} is not on a metro line yet.",
            parent=viewer.root,
        )
        return
    _show_choice_dialog(
        viewer,
        title="Remove From Line",
        message=f"Remove {base._display_label(stop.lbl)} from which line?",
        choices=[
            (
                line_name,
                lambda active_line=line_name: viewer._remove_selected_station_from_line(active_line),
            )
            for line_name in line_names
        ],
    )


def _prompt_selected_stop_line_action(
    viewer: "base.MetroMapViewer",
    stop_var: str,
) -> None:
    stop = base.STOPS_BY_VAR.get(stop_var)
    if stop is None:
        return
    try:
        import metro_station_extensions as metro_ext
    except Exception:
        metro_ext = None

    action_names = _available_selected_stop_line_actions(stop_var, metro_ext)
    if not action_names:
        messagebox.showinfo(
            "Lines",
            "There are no line actions available for this station.",
            parent=viewer.root,
        )
        return

    actions: list[tuple[str, Callable[[], None]]] = []
    if "Add" in action_names and metro_ext is not None:
        actions.append(
            (
                "Add",
                lambda active_stop_var=stop_var: metro_ext._show_add_selected_station_to_line_dialog(
                    viewer,
                    active_stop_var,
                ),
            )
        )
    if "Remove" in action_names:
        actions.append(
            (
                "Remove",
                lambda active_stop_var=stop_var: _prompt_remove_selected_stop_from_line(
                    viewer,
                    active_stop_var,
                ),
            )
        )
    if "Switch" in action_names and metro_ext is not None:
        actions.append(
            (
                "Switch",
                lambda active_stop_var=stop_var: metro_ext.show_switch_station_line_dialog(
                    viewer,
                    active_stop_var,
                ),
            )
        )
    _show_choice_dialog(
        viewer,
        title="Station Lines",
        message=(
            f"What would you like to do with the lines for "
            f"{base._display_label(stop.lbl)}?"
        ),
        choices=actions,
    )
