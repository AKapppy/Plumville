from __future__ import annotations

import json
from pathlib import Path
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

import legacy_core as base
from worldgen import village_paths


PATH_DETECTION_STATE_PATH = Path(__file__).with_name("path_detection_state.json")
PATH_PREVIEW_OUTLINE = "#ffffff"
PATH_PREVIEW_COLOR = "#7df9ff"
PATH_PREVIEW_NODE_FILL = "#ffffff"
PATH_PREVIEW_NODE_OUTLINE = "#7df9ff"
SEED_MARKER_FILL = "#ffea00"
SEED_MARKER_OUTLINE = "#ffffff"
VILLAGE_ZOOM_RADIUS = 96
DIALOG_BG = "#111315"
DIALOG_FG = "#f5f7fa"
DIALOG_MUTED = "#c9d1d9"

_ORIGINAL_DRAW_EXTRA_EDGES = None
_ORIGINAL_DRAW_PATH_NODES = None
_ORIGINAL_DRAW_SELECTED_STOP_INFO = None
_ORIGINAL_REFRESH_STATION_STATS = None


class SeedDetectionSession:
    def __init__(self, viewer: "base.MetroMapViewer", stop_var: str) -> None:
        self.viewer = viewer
        self.stop_var = stop_var
        self.seed_points: list[tuple[int, int]] = []
        self.preview: village_paths.DetectedVillagePreview | None = None
        self.running = False
        self.awaiting_map_click = False

        self.dialog = tk.Toplevel(viewer.root)
        self.dialog.title("Detect Village Paths")
        self.dialog.transient(viewer.root)
        self.dialog.resizable(False, False)
        self.dialog.attributes("-topmost", True)
        self.dialog.configure(bg=DIALOG_BG)

        viewer.root.update_idletasks()
        root_x = viewer.root.winfo_rootx()
        root_y = viewer.root.winfo_rooty()
        root_width = viewer.root.winfo_width()
        dialog_width = 430
        dialog_height = 300
        self.dialog.geometry(
            f"{dialog_width}x{dialog_height}+{root_x + max(12, root_width - dialog_width - 24)}+{root_y + 48}"
        )

        body = tk.Frame(self.dialog, bg=DIALOG_BG)
        body.pack(fill="both", expand=True, padx=16, pady=16)

        stop = base.STOPS_BY_VAR.get(stop_var)
        title_text = f"Detect Paths: {base._display_label(stop.lbl) if stop is not None else stop_var}"
        tk.Label(
            body,
            text=title_text,
            bg=DIALOG_BG,
            fg=DIALOG_FG,
            font=("Helvetica", 16, "bold"),
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        self.status_var = tk.StringVar(
            master=self.dialog,
            value=(
                "1. Zoomed to the village.\n"
                "2. Add a seed by clicking the map or entering coordinates.\n"
                "3. Add more seeds if needed.\n"
                "4. Save when the preview looks right."
            ),
        )
        tk.Label(
            body,
            textvariable=self.status_var,
            bg=DIALOG_BG,
            fg=DIALOG_FG,
            font=("Helvetica", 11),
            justify="left",
            anchor="w",
        ).pack(anchor="w", fill="x")

        coord_row = tk.Frame(body, bg=DIALOG_BG)
        coord_row.pack(anchor="w", fill="x", pady=(14, 8))

        tk.Label(coord_row, text="X:", bg=DIALOG_BG, fg=DIALOG_FG, font=("Helvetica", 11)).pack(side="left")
        self.x_entry = tk.Entry(coord_row, width=10)
        self.x_entry.pack(side="left", padx=(4, 10))

        tk.Label(coord_row, text="Z:", bg=DIALOG_BG, fg=DIALOG_FG, font=("Helvetica", 11)).pack(side="left")
        self.z_entry = tk.Entry(coord_row, width=10)
        self.z_entry.pack(side="left", padx=(4, 10))

        self.add_coords_button = tk.Button(
            coord_row,
            text="Add Seed by Coordinates",
            command=self.add_seed_from_entries,
        )
        self.add_coords_button.pack(side="left")

        action_row = tk.Frame(body, bg=DIALOG_BG)
        action_row.pack(anchor="w", fill="x", pady=(0, 10))

        self.click_button = tk.Button(action_row, text="Click Seed on Map", command=self.enable_map_click)
        self.click_button.pack(side="left")

        self.clear_last_button = tk.Button(action_row, text="Remove Last Seed", command=self.remove_last_seed, state="disabled")
        self.clear_last_button.pack(side="left", padx=(8, 0))

        self.save_button = tk.Button(action_row, text="Save Paths", command=self.save_paths, state="disabled")
        self.save_button.pack(side="right")
        self.cancel_button = tk.Button(action_row, text="Cancel", command=self.cancel)
        self.cancel_button.pack(side="right", padx=(0, 8))

        self.seed_list_var = tk.StringVar(master=self.dialog, value="Seeds: none yet")
        tk.Label(
            body,
            textvariable=self.seed_list_var,
            bg=DIALOG_BG,
            fg=DIALOG_MUTED,
            font=("Helvetica", 10),
            justify="left",
            anchor="w",
        ).pack(anchor="w", fill="x")

        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)

    def update_seed_label(self) -> None:
        if not self.seed_points:
            self.seed_list_var.set("Seeds: none yet")
            self.clear_last_button.configure(state="disabled")
            return
        preview = ", ".join(f"({seed_x}, {seed_z})" for seed_x, seed_z in self.seed_points[-4:])
        if len(self.seed_points) > 4:
            preview = f"..., {preview}"
        self.seed_list_var.set(f"Seeds ({len(self.seed_points)}): {preview}")
        self.clear_last_button.configure(state="normal")

    def set_running(self, value: bool) -> None:
        self.running = value
        state = "disabled" if value else "normal"
        self.add_coords_button.configure(state=state)
        self.click_button.configure(state=state)
        self.cancel_button.configure(state="normal")
        self.clear_last_button.configure(state=("disabled" if value or not self.seed_points else "normal"))
        self.save_button.configure(state=("disabled" if value or self.preview is None else "normal"))

    def add_seed_from_entries(self) -> None:
        x_text = self.x_entry.get().strip()
        z_text = self.z_entry.get().strip()
        try:
            seed_x = int(x_text)
            seed_z = int(z_text)
        except ValueError:
            messagebox.showerror("Invalid Coordinates", "Enter integer X and Z coordinates.", parent=self.dialog)
            return
        self.add_seed((seed_x, seed_z))
        self.x_entry.delete(0, "end")
        self.z_entry.delete(0, "end")

    def enable_map_click(self) -> None:
        self.awaiting_map_click = True
        self.viewer.canvas.configure(cursor="crosshair")
        self.status_var.set(
            "Map click mode is active.\n"
            "Release the mouse over a road block in the village area to add a seed."
        )
        self.click_button.configure(text="Waiting for Map Click...")

    def consume_map_click(self) -> None:
        self.awaiting_map_click = False
        self.viewer.canvas.configure(cursor="")
        self.click_button.configure(text="Click Seed on Map")

    def add_seed(self, seed_point: tuple[int, int]) -> None:
        self.seed_points.append(seed_point)
        self.update_seed_label()
        self.run_detection()

    def remove_last_seed(self) -> None:
        if not self.seed_points or self.running:
            return
        self.seed_points.pop()
        self.update_seed_label()
        if not self.seed_points:
            self.preview = None
            self.viewer._path_detection_preview = None
            self.status_var.set(
                "All seeds removed.\n"
                "Add a new seed by clicking the map or entering coordinates."
            )
            self.save_button.configure(state="disabled")
            self.viewer.redraw()
            return
        self.run_detection()

    def run_detection(self) -> None:
        if self.running:
            return
        self.set_running(True)
        self.viewer._path_detection_preview = None
        self.viewer.redraw()

        outcome: dict[str, Any] = {"done": False}

        render_underlay = _current_render_payload(self.viewer)
        if render_underlay is None:
            self.set_running(False)
            messagebox.showerror(
                "Path Detection Unavailable",
                "Render the world map first. Village path detection only works inside rendered terrain.",
                parent=self.dialog,
            )
            return
        payload, _image = render_underlay
        stop = base.STOPS_BY_VAR.get(self.stop_var)

        def worker() -> None:
            try:
                outcome["preview"] = village_paths.build_preview_from_seeds(
                    stop_var=self.stop_var,
                    stop_coordinates=stop.coordinates,
                    seed_points=list(self.seed_points),
                    render_payload=payload,
                )
            except Exception as exc:  # noqa: BLE001
                outcome["error"] = str(exc)
            finally:
                outcome["done"] = True

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        dot_state = {"count": 0}

        def poll() -> None:
            if outcome.get("done"):
                self.finish_detection(outcome)
                return
            dot_state["count"] = (dot_state["count"] + 1) % 4
            dots = "." * dot_state["count"]
            self.status_var.set(f"Building preview from real chunk data{dots}")
            self.viewer.root.after(120, poll)

        self.viewer.root.after(120, poll)

    def finish_detection(self, outcome: dict[str, Any]) -> None:
        self.set_running(False)
        error_text = outcome.get("error")
        preview = outcome.get("preview")

        if error_text:
            self.status_var.set(f"Detection failed:\n{error_text}")
            messagebox.showerror("Village Path Detection Failed", str(error_text), parent=self.dialog)
            self.viewer._path_detection_preview = None
            self.viewer.redraw()
            return

        self.preview = preview
        self.viewer._path_detection_preview = preview
        _fit_preview_bounds(self.viewer, preview.bounds)
        self.viewer.redraw()

        snapped = ", ".join(f"({seed_x}, {seed_z})" for seed_x, seed_z in preview.snapped_seed_points) or "none"
        self.status_var.set(
            f"Preview ready.\n"
            f"Segments: {len(preview.edges)}\n"
            f"Snapped seeds: {snapped}\n"
            "Add another seed if it missed part of the village, or Save Paths."
        )
        self.save_button.configure(state="normal")

    def save_paths(self) -> None:
        if self.preview is None:
            return
        _commit_preview(self.stop_var, self.preview)
        self.viewer.priority_dirty = True
        self.viewer.route_dirty = True
        self.viewer.route_controls_dirty = True
        self.viewer.stats_dirty = True
        self.close()

    def cancel(self) -> None:
        self.close()

    def close(self) -> None:
        self.viewer.canvas.configure(cursor="")
        self.viewer._path_detection_preview = None
        self.viewer._path_detection_hide_selected_popup = False
        self.viewer._path_detection_session = None
        try:
            self.dialog.destroy()
        except tk.TclError:
            pass
        self.viewer.redraw()


def _current_render_payload(viewer: "base.MetroMapViewer") -> tuple[dict[str, Any], Any] | None:
    if not hasattr(viewer, "_current_world_map_render_underlay"):
        return None
    return viewer._current_world_map_render_underlay()


def _current_visible_bounds(viewer: "base.MetroMapViewer") -> tuple[int, int, int, int] | None:
    render_underlay = _current_render_payload(viewer)
    if render_underlay is None:
        return None
    payload, _source_image = render_underlay
    if hasattr(base, "_world_map_visible_render_bounds_from_payload"):
        bounds = base._world_map_visible_render_bounds_from_payload(payload)
        if bounds is not None:
            return bounds
    try:
        return (
            int(payload["min_x"]),
            int(payload["max_x"]),
            int(payload["min_z"]),
            int(payload["max_z"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _load_state() -> dict[str, Any]:
    if not PATH_DETECTION_STATE_PATH.exists():
        return {"villages": {}}
    try:
        payload = json.loads(PATH_DETECTION_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"villages": {}}
    if not isinstance(payload, dict):
        return {"villages": {}}
    villages = payload.get("villages")
    if not isinstance(villages, dict):
        villages = {}
    return {"villages": villages}


def _save_state(payload: dict[str, Any]) -> None:
    PATH_DETECTION_STATE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _village_state(stop_var: str) -> dict[str, Any] | None:
    villages = _load_state().get("villages", {})
    if not isinstance(villages, dict):
        return None
    record = villages.get(stop_var)
    return record if isinstance(record, dict) else None


def _set_village_state(stop_var: str, record: dict[str, Any] | None) -> None:
    payload = _load_state()
    villages = payload.setdefault("villages", {})
    if record is None:
        villages.pop(stop_var, None)
    else:
        villages[stop_var] = record
    _save_state(payload)


def _remove_existing_detection(payload: dict[str, Any], stop_var: str) -> None:
    record = _village_state(stop_var)
    if record is None:
        return

    edge_ids = record.get("edge_ids", [])
    edge_id_set = {str(edge_id) for edge_id in edge_ids if isinstance(edge_id, str)}
    if edge_id_set:
        payload["extra_edges"] = [
            edge_record
            for edge_record in payload.get("extra_edges", [])
            if str(edge_record.get("id", "")) not in edge_id_set
        ]

    node_coordinates = record.get("node_coordinates", [])
    coordinates_to_remove = {
        (int(coordinates[0]), int(coordinates[1]))
        for coordinates in node_coordinates
        if isinstance(coordinates, list) and len(coordinates) == 2
    }
    if coordinates_to_remove:
        payload["path_nodes"] = [
            path_node
            for path_node in payload.get("path_nodes", [])
            if (int(path_node.get("x", 0)), int(path_node.get("y", 0))) not in coordinates_to_remove
        ]

    _set_village_state(stop_var, None)


def _existing_path_node_coordinates(payload: dict[str, Any]) -> set[tuple[int, int]]:
    coordinates = set()
    for path_node in payload.get("path_nodes", []):
        if not isinstance(path_node, dict):
            continue
        coordinates.add((int(path_node.get("x", 0)), int(path_node.get("y", 0))))
    return coordinates


def _stop_coordinate_map(payload: dict[str, Any]) -> dict[tuple[int, int], str]:
    mapping = {}
    for stop_record in payload.get("stops", []):
        if not isinstance(stop_record, dict):
            continue
        mapping[(int(stop_record.get("x", 0)), int(stop_record.get("y", 0)))] = str(stop_record.get("var", ""))
    return mapping


def _path_endpoint_record_for_coordinate(
    coordinate: tuple[int, int],
    *,
    stop_coordinate_map: dict[tuple[int, int], str],
) -> dict[str, Any]:
    stop_var = stop_coordinate_map.get(coordinate)
    if stop_var:
        return {"kind": "stop", "stop_var": stop_var}
    return {"kind": "coord", "x": int(coordinate[0]), "y": int(coordinate[1])}


def _edge_exists(payload: dict[str, Any], endpoint_a: dict[str, Any], endpoint_b: dict[str, Any]) -> bool:
    def normalized_endpoint(endpoint: dict[str, Any]) -> tuple[str, tuple[int, int] | str]:
        if endpoint.get("kind") == "stop":
            return ("stop", str(endpoint.get("stop_var", "")))
        return ("coord", (int(endpoint.get("x", 0)), int(endpoint.get("y", 0))))

    target_pair = {normalized_endpoint(endpoint_a), normalized_endpoint(endpoint_b)}
    for edge_record in payload.get("extra_edges", []):
        if not isinstance(edge_record, dict):
            continue
        if str(edge_record.get("kind", "")) != "walk":
            continue
        from_endpoint = edge_record.get("from_endpoint")
        to_endpoint = edge_record.get("to_endpoint")
        if not isinstance(from_endpoint, dict) or not isinstance(to_endpoint, dict):
            continue
        candidate_pair = {normalized_endpoint(from_endpoint), normalized_endpoint(to_endpoint)}
        if candidate_pair == target_pair:
            return True
    return False


def _commit_preview(stop_var: str, preview: village_paths.DetectedVillagePreview) -> None:
    payload = base._load_network_payload()
    _remove_existing_detection(payload, stop_var)

    existing_node_coordinates = _existing_path_node_coordinates(payload)
    stop_coordinate_map = _stop_coordinate_map(payload)

    added_node_coordinates: list[list[int]] = []
    added_edge_ids: list[str] = []

    stop_slug = stop_var.lower().replace(":", "_")
    node_id_index = 1
    for coordinate in preview.node_coordinates:
        if coordinate in stop_coordinate_map:
            continue
        if coordinate in existing_node_coordinates:
            continue
        is_pier_node = coordinate in preview.pier_node_coordinates
        node_record = {
            "id": f"det_{stop_slug}_{'pier_node' if is_pier_node else 'node'}_{node_id_index}",
            "x": int(coordinate[0]),
            "y": int(coordinate[1]),
            "explicit": True,
            "is_explicit": True,
        }
        if is_pier_node:
            node_record["label"] = "Pier"
        node_id_index += 1
        payload.setdefault("path_nodes", []).append(node_record)
        existing_node_coordinates.add(coordinate)
        added_node_coordinates.append([int(coordinate[0]), int(coordinate[1])])

    edge_index = 1
    for preview_edge in preview.edges:
        endpoint_a = _path_endpoint_record_for_coordinate(
            preview_edge.endpoint_a,
            stop_coordinate_map=stop_coordinate_map,
        )
        endpoint_b = _path_endpoint_record_for_coordinate(
            preview_edge.endpoint_b,
            stop_coordinate_map=stop_coordinate_map,
        )
        if endpoint_a == endpoint_b:
            continue
        if _edge_exists(payload, endpoint_a, endpoint_b):
            continue
        edge_id = f"det_{stop_slug}_edge_{edge_index}"
        edge_index += 1
        edge_record = {
            "id": edge_id,
            "kind": "walk",
            "from_endpoint": endpoint_a,
            "to_endpoint": endpoint_b,
            "bidirectional": True,
            "path_points": [
                {"x": int(point_x), "y": int(point_y)}
                for point_x, point_y in preview_edge.path_points
            ],
            "label": "Village pier" if preview_edge.is_pier else "Village path",
        }
        payload.setdefault("extra_edges", []).append(edge_record)
        added_edge_ids.append(edge_id)

    base._normalize_path_nodes(payload)
    base._normalize_extra_edges(payload)
    base._normalize_alignment_reminders(payload)
    base._write_network_payload(payload)
    base._apply_network_payload(payload)
    _set_village_state(
        stop_var,
        {
            "edge_ids": added_edge_ids,
            "node_coordinates": added_node_coordinates,
        },
    )


def _path_detection_progress_text(viewer: "base.MetroMapViewer") -> str:
    visible_bounds = _current_visible_bounds(viewer)
    if visible_bounds is None:
        return "Paths Detected: 0/0"
    min_x, max_x, min_z, max_z = visible_bounds
    villages_inside = [
        stop
        for stop in base.METRO_STOPS
        if min_x <= stop.x <= max_x and min_z <= stop.y <= max_z
    ]
    detected_count = sum(1 for stop in villages_inside if _village_state(stop.var) is not None)
    return f"Paths Detected: {detected_count}/{len(villages_inside)}"


def _fit_preview_bounds(viewer: "base.MetroMapViewer", bounds: tuple[int, int, int, int]) -> None:
    min_x, max_x, min_z, max_z = bounds
    viewer._set_view_to_plot_bounds(min_x, max_x, -max_z, -min_z)


def _zoom_to_village(viewer: "base.MetroMapViewer", stop_coordinates: tuple[int, int]) -> None:
    stop_x, stop_z = stop_coordinates
    _fit_preview_bounds(
        viewer,
        (
            stop_x - VILLAGE_ZOOM_RADIUS,
            stop_x + VILLAGE_ZOOM_RADIUS,
            stop_z - VILLAGE_ZOOM_RADIUS,
            stop_z + VILLAGE_ZOOM_RADIUS,
        ),
    )


def _canvas_to_world(viewer: "base.MetroMapViewer", canvas_x: float, canvas_y: float) -> tuple[int, int]:
    origin_x, origin_y = viewer.world_to_canvas((0, 0))
    x1, _ = viewer.world_to_canvas((1, 0))
    _, y1 = viewer.world_to_canvas((0, 1))

    scale_x = x1 - origin_x
    scale_y = y1 - origin_y
    if abs(scale_x) < 1e-9 or abs(scale_y) < 1e-9:
        raise RuntimeError("Could not convert canvas coordinates to world coordinates.")

    plot_x = (canvas_x - origin_x) / scale_x
    plot_y = (canvas_y - origin_y) / scale_y
    return (round(plot_x), round(-plot_y))


def _ensure_click_binding(viewer: "base.MetroMapViewer") -> None:
    if getattr(viewer, "_path_detection_click_bound", False):
        return

    def handle_release(event: Any) -> str | None:
        session = getattr(viewer, "_path_detection_session", None)
        if session is None or not session.awaiting_map_click:
            return None
        session.consume_map_click()
        try:
            seed_point = _canvas_to_world(viewer, event.x, event.y)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Map Click Failed", str(exc), parent=viewer.root)
            return "break"
        session.add_seed(seed_point)
        return "break"

    viewer.canvas.bind("<ButtonRelease-1>", handle_release, add="+")
    viewer._path_detection_click_bound = True


def detect_paths_for_stop(viewer: "base.MetroMapViewer", stop_var: str) -> None:
    if getattr(viewer, "_path_detection_session", None) is not None:
        viewer._path_detection_session.close()

    stop = base.STOPS_BY_VAR.get(stop_var)
    if stop is None:
        return

    render_underlay = _current_render_payload(viewer)
    if render_underlay is None:
        messagebox.showerror(
            "Path Detection Unavailable",
            "Render the world map first. Village path detection only works inside rendered terrain.",
            parent=viewer.root,
        )
        return
    payload, _image = render_underlay
    mode_key = village_paths.infer_mode_key_from_render_payload(payload)
    if mode_key == "lan_y40":
        messagebox.showerror(
            "Path Detection Unavailable",
            "Village path detection only works from a surface render, not LAN Y=40.",
            parent=viewer.root,
        )
        return

    viewer._path_detection_hide_selected_popup = True
    _ensure_click_binding(viewer)
    _zoom_to_village(viewer, stop.coordinates)
    session = SeedDetectionSession(viewer, stop_var)
    viewer._path_detection_session = session
    viewer.redraw()


def _draw_preview_edges(self: "base.MetroMapViewer") -> None:
    preview = getattr(self, "_path_detection_preview", None)
    if preview is None:
        return
    for preview_edge in preview.edges:
        canvas_points: list[float] = []
        for point_x, point_y in preview_edge.path_points:
            canvas_x, canvas_y = self.world_to_canvas((point_x, -point_y))
            canvas_points.extend((canvas_x, canvas_y))
        if len(canvas_points) < 4:
            continue
        self.canvas.create_line(
            *canvas_points,
            fill=PATH_PREVIEW_OUTLINE,
            width=7,
            capstyle="round",
            joinstyle="round",
        )
        self.canvas.create_line(
            *canvas_points,
            fill=PATH_PREVIEW_COLOR,
            width=3,
            dash=(6, 4),
            capstyle="round",
            joinstyle="round",
            smooth=True,
        )

    for seed_x, seed_z in preview.snapped_seed_points:
        canvas_x, canvas_y = self.world_to_canvas((seed_x, -seed_z))
        self.canvas.create_oval(
            canvas_x - 5,
            canvas_y - 5,
            canvas_x + 5,
            canvas_y + 5,
            fill=SEED_MARKER_FILL,
            outline=SEED_MARKER_OUTLINE,
            width=2,
        )


def _draw_preview_nodes(self: "base.MetroMapViewer") -> None:
    preview = getattr(self, "_path_detection_preview", None)
    if preview is None:
        return
    for point_x, point_y in preview.node_coordinates:
        canvas_x, canvas_y = self.world_to_canvas((point_x, -point_y))
        self.canvas.create_oval(
            canvas_x - 4,
            canvas_y - 4,
            canvas_x + 4,
            canvas_y + 4,
            fill=PATH_PREVIEW_NODE_FILL,
            outline=PATH_PREVIEW_NODE_OUTLINE,
            width=2,
        )


def _patched_draw_extra_edges(self: "base.MetroMapViewer") -> None:
    _ORIGINAL_DRAW_EXTRA_EDGES(self)
    _draw_preview_edges(self)


def _patched_draw_path_nodes(self: "base.MetroMapViewer") -> None:
    _ORIGINAL_DRAW_PATH_NODES(self)
    _draw_preview_nodes(self)


def _patched_refresh_station_stats(self: "base.MetroMapViewer") -> None:
    _ORIGINAL_REFRESH_STATION_STATS(self)
    summary_lines = [
        line
        for line in self.stats_summary_var.get().splitlines()
        if not line.startswith("Paths Detected:")
    ]
    summary_text = "\n".join(summary_lines).rstrip()
    extra = _path_detection_progress_text(self)
    self.stats_summary_var.set(f"{summary_text}\n{extra}" if summary_text else extra)


def _patched_draw_selected_stop_info(self: "base.MetroMapViewer") -> None:
    if getattr(self, "_path_detection_hide_selected_popup", False):
        return

    _ORIGINAL_DRAW_SELECTED_STOP_INFO(self)
    stop_var = getattr(self, "selected_stop_var", None)
    frame = getattr(self, "info_popup_frame", None)
    if stop_var is None or frame is None or stop_var not in base.STOPS_BY_VAR:
        return

    control_row = tk.Frame(frame, bg=base.INFO_BOX_BACKGROUND)
    control_row.pack(anchor="w", padx=base.INFO_BOX_PAD_X, pady=(0, base.INFO_BOX_PAD_Y))
    detected = _village_state(stop_var) is not None
    session = getattr(self, "_path_detection_session", None)
    button_text = "Detecting..." if session is not None else ("Redetect Village Paths" if detected else "Detect Village Paths")
    self._make_info_button(
        control_row,
        text=button_text,
        command=lambda active_stop_var=stop_var: detect_paths_for_stop(self, active_stop_var),
    ).pack(side="left")
    status_text = "saved" if detected else "not saved"
    tk.Label(
        control_row,
        text=f"Village paths: {status_text}",
        bg=base.INFO_BOX_BACKGROUND,
        fg=base.TEXT_COLOR,
        font=("Helvetica", base.INFO_TEXT_FONT_SIZE),
        anchor="w",
        justify="left",
    ).pack(side="left", padx=(base.INFO_BOX_SECTION_GAP, 0))


def apply() -> None:
    global _ORIGINAL_DRAW_EXTRA_EDGES
    global _ORIGINAL_DRAW_PATH_NODES
    global _ORIGINAL_DRAW_SELECTED_STOP_INFO
    global _ORIGINAL_REFRESH_STATION_STATS

    if getattr(base.MetroMapViewer, "_path_detection_applied", False):
        return

    _ORIGINAL_DRAW_EXTRA_EDGES = base.MetroMapViewer._draw_extra_edges
    _ORIGINAL_DRAW_PATH_NODES = base.MetroMapViewer._draw_path_nodes
    _ORIGINAL_DRAW_SELECTED_STOP_INFO = base.MetroMapViewer._draw_selected_stop_info
    _ORIGINAL_REFRESH_STATION_STATS = base.MetroMapViewer._refresh_station_stats

    base.MetroMapViewer._draw_extra_edges = _patched_draw_extra_edges
    base.MetroMapViewer._draw_path_nodes = _patched_draw_path_nodes
    base.MetroMapViewer._draw_selected_stop_info = _patched_draw_selected_stop_info
    base.MetroMapViewer._refresh_station_stats = _patched_refresh_station_stats
    base.MetroMapViewer._path_detection_applied = True
