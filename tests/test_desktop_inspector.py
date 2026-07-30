from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest import mock

import legacy_core as base
from plumville.desktop import inspector


class FakeWidget:
    def __init__(self, master: object | None = None, **kwargs: object) -> None:
        self.master = master
        self.kwargs = dict(kwargs)
        self.children: list[FakeWidget] = []
        self.pack_calls: list[dict[str, object]] = []
        self.bindings: dict[str, object] = {}
        self.destroyed = False
        if isinstance(master, FakeWidget):
            master.children.append(self)

    def configure(self, **kwargs: object) -> None:
        self.kwargs.update(kwargs)

    def pack(self, **kwargs: object) -> None:
        self.pack_calls.append(kwargs)

    def bind(self, event: str, callback: object) -> None:
        self.bindings[event] = callback

    def winfo_children(self) -> list["FakeWidget"]:
        return list(self.children)

    def destroy(self) -> None:
        self.destroyed = True
        if isinstance(self.master, FakeWidget) and self in self.master.children:
            self.master.children.remove(self)


class FakeCanvas(FakeWidget):
    def __init__(self, master: object | None = None, **kwargs: object) -> None:
        super().__init__(master, **kwargs)
        self.draw_calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def create_polygon(self, *args: object, **kwargs: object) -> None:
        self.draw_calls.append(("polygon", args, kwargs))

    def create_oval(self, *args: object, **kwargs: object) -> None:
        self.draw_calls.append(("oval", args, kwargs))

    def create_text(self, *args: object, **kwargs: object) -> None:
        self.draw_calls.append(("text", args, kwargs))


class FakeStringVar:
    def __init__(self, *_args: object, value: str = "", **_kwargs: object) -> None:
        self.value = value
        self.traces: list[tuple[str, object]] = []

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value

    def trace_add(self, mode: str, callback: object) -> str:
        self.traces.append((mode, callback))
        return f"trace-{len(self.traces)}"


def _widget_texts(widget: FakeWidget) -> list[str]:
    texts: list[str] = []
    text = widget.kwargs.get("text")
    if isinstance(text, str):
        texts.append(text)
    for child in widget.children:
        texts.extend(_widget_texts(child))
    return texts


def _find_widget_by_text(widget: FakeWidget, text: str) -> FakeWidget | None:
    if widget.kwargs.get("text") == text:
        return widget
    for child in widget.children:
        match = _find_widget_by_text(child, text)
        if match is not None:
            return match
    return None


class DesktopInspectorTests(unittest.TestCase):
    def _shell(self) -> SimpleNamespace:
        return SimpleNamespace(
            inspector_body=FakeWidget(),
            inspector_header_label=FakeWidget(text="Inspector"),
        )

    def _viewer(self) -> SimpleNamespace:
        shell = self._shell()
        viewer = SimpleNamespace(
            _desktop_workspace_shell=shell,
            selected_stop_var=None,
            city_limits_edit_stop_var=None,
            info_popup_variables=[],
            root=object(),
        )

        def make_button(parent: FakeWidget, *, text: str, command: object) -> FakeWidget:
            return FakeWidget(parent, text=text, command=command, kind="button")

        def make_sidebar_button(parent: FakeWidget, *, text: str, command: object) -> FakeWidget:
            return FakeWidget(parent, text=text, command=command, kind="sidebar_button")

        def make_entry(parent: FakeWidget, variable: object) -> FakeWidget:
            return FakeWidget(parent, variable=variable, kind="entry")

        def make_checkbox(parent: FakeWidget, *, text: str, checked: bool, **kwargs: object) -> FakeWidget:
            return FakeWidget(parent, text=text, checked=checked, kind="checkbox", **kwargs)

        viewer._make_info_button = make_button
        viewer._make_sidebar_button = make_sidebar_button
        viewer._make_sidebar_entry = make_entry
        viewer._make_info_checkbox = make_checkbox
        viewer._draw_station_signage_panel = lambda parent, _stop: FakeWidget(parent, kind="signage")
        viewer._edit_selected_coordinates = mock.Mock()
        viewer._edit_selected_label = mock.Mock()
        viewer._edit_selected_station_entry = mock.Mock()
        viewer._manage_selected_alignments = mock.Mock()
        viewer._toggle_selected_city_limits_edit = mock.Mock()
        viewer._clear_selected_city_limits = mock.Mock()
        viewer._update_selected_checkpoint = mock.Mock()
        viewer._update_selected_chime_direction = mock.Mock()
        viewer._remove_selected_station_from_line = mock.Mock()
        return viewer

    def test_sync_inspector_renders_empty_state_without_selected_station(self) -> None:
        viewer = self._viewer()

        with (
            mock.patch.object(inspector.tk, "Frame", FakeWidget),
            mock.patch.object(inspector.tk, "Label", FakeWidget),
            mock.patch.object(inspector.tk, "Canvas", FakeCanvas),
        ):
            inspector.sync_inspector(viewer)

        self.assertEqual(
            viewer._desktop_workspace_shell.inspector_header_label.kwargs["text"],
            "Inspector",
        )
        self.assertGreater(len(viewer._desktop_workspace_shell.inspector_body.children), 0)

    def test_sync_inspector_renders_selected_station_details(self) -> None:
        viewer = self._viewer()
        stop = base.MetroStop(
            var="P_A",
            lbl="Alpha",
            x=12,
            y=34,
            has_connector=True,
            has_full_station=True,
            has_walking_paths=True,
            is_connected=True,
            has_finished_railway=True,
            has_signs=True,
            station_entry_x=22,
            station_entry_y=44,
        )
        previous_stops_by_var = base.STOPS_BY_VAR
        previous_stop_line_names = base.STOP_LINE_NAMES
        previous_line_colors = base.LINE_COLORS
        try:
            base.STOPS_BY_VAR = {stop.var: stop}
            base.STOP_LINE_NAMES = {stop.var: ("A", "B")}
            base.LINE_COLORS = {"A": "#72c9ec", "B": "#de5750"}
            viewer.selected_stop_var = stop.var

            with (
                mock.patch.object(inspector.tk, "Frame", FakeWidget),
                mock.patch.object(inspector.tk, "Label", FakeWidget),
                mock.patch.object(inspector.tk, "Canvas", FakeCanvas),
                mock.patch.object(base, "_alignment_reminders_for_stop", return_value=()),
                mock.patch.object(base, "_station_chime_outlet_directions", return_value=()),
                mock.patch.object(base, "_station_completed_chime_count", return_value=0),
                mock.patch.object(base, "_station_max_chime_count", return_value=0),
                mock.patch.object(base, "_station_signs_available", return_value=True),
            ):
                inspector.sync_inspector(viewer)
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var
            base.STOP_LINE_NAMES = previous_stop_line_names
            base.LINE_COLORS = previous_line_colors

        self.assertEqual(
            viewer._desktop_workspace_shell.inspector_header_label.kwargs["text"],
            "Station Inspector",
        )
        self.assertEqual(viewer.info_popup_variables, [])
        self.assertGreaterEqual(len(viewer._desktop_workspace_shell.inspector_body.children), 4)

    def test_sync_inspector_renders_selected_metro_segment(self) -> None:
        viewer = self._viewer()
        alpha = base.MetroStop("P_A", "Alpha", 0, 0)
        beta = base.MetroStop("P_B", "Beta", 10, 10)
        segment = base.MetroLineSegment(
            "A",
            "P_A",
            "P_B",
            (
                base.LinePathPointSpec("P_A", "P_A"),
                base.LinePathPointSpec("P_B", "P_B"),
            ),
        )
        previous_stops_by_var = base.STOPS_BY_VAR
        previous_line_colors = base.LINE_COLORS
        try:
            base.STOPS_BY_VAR = {alpha.var: alpha, beta.var: beta}
            base.LINE_COLORS = {"A": "#72c9ec"}
            viewer._selected_metro_segment = mock.Mock(return_value=segment)
            viewer._selected_metro_segments = mock.Mock(return_value=(segment,))

            with (
                mock.patch.object(inspector.tk, "Frame", FakeWidget),
                mock.patch.object(inspector.tk, "Label", FakeWidget),
                mock.patch.object(inspector.tk, "Canvas", FakeCanvas),
            ):
                inspector.sync_inspector(viewer)
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var
            base.LINE_COLORS = previous_line_colors

        shell = viewer._desktop_workspace_shell
        self.assertEqual(shell.inspector_header_label.kwargs["text"], "Segment Inspector")
        self.assertIn("Line A", _widget_texts(shell.inspector_body))
        self.assertIn("Add Turn", _widget_texts(shell.inspector_body))
        self.assertIn("Edit Endpoints", _widget_texts(shell.inspector_body))

    def test_sync_inspector_preserves_active_task_view(self) -> None:
        viewer = self._viewer()
        shell = viewer._desktop_workspace_shell
        shell.inspector_header_label.configure(text="Segment Editor")
        existing = FakeWidget(shell.inspector_body, text="Save Turn")
        viewer._desktop_inspector_task_active = True

        inspector.sync_inspector(viewer)

        self.assertEqual(shell.inspector_header_label.kwargs["text"], "Segment Editor")
        self.assertIn(existing, shell.inspector_body.children)

    def test_metro_turn_editor_mounts_reachable_save_action_in_inspector(self) -> None:
        viewer = self._viewer()
        alpha = base.MetroStop("P_A", "Alpha", 0, 0)
        beta = base.MetroStop("P_B", "Beta", 10, 10)
        segment = base.MetroLineSegment(
            "A",
            "P_A",
            "P_B",
            (
                base.LinePathPointSpec("P_A", "P_A"),
                base.LinePathPointSpec("P_B", "P_B"),
            ),
        )
        viewer.preview_points = None
        viewer._set_metro_segment_preview = lambda points: setattr(viewer, "preview_points", points)
        viewer._clear_metro_segment_preview = lambda: setattr(viewer, "preview_points", None)
        viewer._refresh_after_path_edit = mock.Mock()
        viewer._selected_metro_segment = mock.Mock(return_value=segment)

        previous_stops_by_var = base.STOPS_BY_VAR
        try:
            base.STOPS_BY_VAR = {alpha.var: alpha, beta.var: beta}
            with (
                mock.patch.object(inspector.tk, "Frame", FakeWidget),
                mock.patch.object(inspector.tk, "Label", FakeWidget),
                mock.patch.object(inspector.tk, "Canvas", FakeCanvas),
                mock.patch.object(inspector.tk, "Radiobutton", FakeWidget),
                mock.patch.object(inspector.tk, "StringVar", FakeStringVar),
                mock.patch.object(base, "_load_network_payload", return_value={}),
                mock.patch.object(
                    base,
                    "_default_turn_coordinate_options_for_metro_segment_in_payload",
                    return_value=(((0, 10),), ((10, 0),)),
                ),
            ):
                handled = inspector.show_metro_turn_editor(viewer, segment)
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var

        shell = viewer._desktop_workspace_shell
        self.assertTrue(handled)
        self.assertTrue(viewer._desktop_inspector_task_active)
        self.assertEqual(shell.inspector_header_label.kwargs["text"], "Segment Editor")
        self.assertIn("Save Turn", _widget_texts(shell.inspector_body))
        self.assertIn("Cancel", _widget_texts(shell.inspector_body))
        self.assertEqual(viewer.preview_points, ((0, 0), (0, -10), (10, -10)))
        save_button = _find_widget_by_text(shell.inspector_body, "Save Turn")
        self.assertIsNotNone(save_button)

        with mock.patch.object(base, "set_metro_line_segment_turn_variant") as save_turn:
            save_button.kwargs["command"]()

        save_turn.assert_called_once_with("A", "P_A", "P_B", 0)
        viewer._refresh_after_path_edit.assert_called_once_with()
        self.assertFalse(viewer._desktop_inspector_task_active)

    def test_metro_endpoint_editor_mounts_reachable_save_action_in_inspector(self) -> None:
        viewer = self._viewer()
        alpha = base.MetroStop("P_A", "Alpha", 0, 0)
        beta = base.MetroStop("P_B", "Beta", 10, 10)
        segment = base.MetroLineSegment(
            "A",
            "P_A",
            "P_B",
            (
                base.LinePathPointSpec("P_A", "P_A"),
                base.LinePathPointSpec("P_A", "P_A", 4, -2),
                base.LinePathPointSpec("P_B", "P_B"),
            ),
        )
        viewer.preview_points = None
        viewer._set_metro_segment_preview = lambda points: setattr(viewer, "preview_points", points)
        viewer._clear_metro_segment_preview = lambda: setattr(viewer, "preview_points", None)
        viewer._refresh_after_path_edit = mock.Mock()
        viewer._selected_metro_segment = mock.Mock(return_value=segment)

        previous_stops_by_var = base.STOPS_BY_VAR
        try:
            base.STOPS_BY_VAR = {alpha.var: alpha, beta.var: beta}
            with (
                mock.patch.object(inspector.tk, "Frame", FakeWidget),
                mock.patch.object(inspector.tk, "Label", FakeWidget),
                mock.patch.object(inspector.tk, "Canvas", FakeCanvas),
                mock.patch.object(inspector.tk, "StringVar", FakeStringVar),
            ):
                handled = inspector.show_metro_endpoint_editor(viewer, segment)
        finally:
            base.STOPS_BY_VAR = previous_stops_by_var

        shell = viewer._desktop_workspace_shell
        self.assertTrue(handled)
        self.assertTrue(viewer._desktop_inspector_task_active)
        self.assertEqual(shell.inspector_header_label.kwargs["text"], "Segment Editor")
        self.assertIn("Save Endpoints", _widget_texts(shell.inspector_body))
        self.assertIn("Cancel", _widget_texts(shell.inspector_body))
        self.assertEqual(viewer.preview_points, ((0, 0), (4, -2), (10, -10)))
        save_button = _find_widget_by_text(shell.inspector_body, "Save Endpoints")
        self.assertIsNotNone(save_button)

        with mock.patch.object(
            base,
            "set_metro_line_segment_endpoint_coordinates",
        ) as save_endpoints:
            save_button.kwargs["command"]()

        save_endpoints.assert_called_once_with(
            "A",
            "P_A",
            "P_B",
            start_coordinates=(0, 0),
            end_coordinates=(10, 10),
        )
        viewer._refresh_after_path_edit.assert_called_once_with()
        self.assertFalse(viewer._desktop_inspector_task_active)
