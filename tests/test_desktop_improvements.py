from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest import mock

import desktop_improvements
import legacy_core as base


class FakeRoot:
    def __init__(self) -> None:
        self.idle_callbacks: list[object] = []
        self.cancelled: list[object] = []

    def after_idle(self, callback: object) -> str:
        self.idle_callbacks.append(callback)
        return f"after-{len(self.idle_callbacks)}"

    def after_cancel(self, after_id: object) -> None:
        self.cancelled.append(after_id)


class FakeStringVar:
    def __init__(
        self,
        master: object | None = None,
        value: str = "",
    ) -> None:
        if isinstance(master, str) and not value:
            value = master
            master = None
        self.master = master
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class FakeMarkerCanvas:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def delete(self, tag: str) -> None:
        self.calls.append(("delete", (tag,), {}))

    def create_polygon(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("polygon", args, kwargs))

    def create_line(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("line", args, kwargs))

    def tag_raise(self, tag: str) -> None:
        self.calls.append(("raise", (tag,), {}))


class FakeRouteViewer:
    def __init__(self) -> None:
        self.root = FakeRoot()
        self.route_request: tuple[str, str] | None = None
        self.current_route: base.RouteResult | None = None
        self.route_start_var = FakeStringVar("Blackport")
        self.route_end_var = FakeStringVar("Dicton")
        self.route_controls_updating = False
        self.route_controls_dirty = False
        self.fit_calls: list[
            tuple[tuple[float, float, float, float], dict[str, object]]
        ] = []

    def _minimum_zoom(self) -> float:
        return 1.25

    def _set_view_to_plot_bounds(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        **kwargs: object,
    ) -> None:
        self.fit_calls.append(
            ((min_x, max_x, min_y, max_y), kwargs)
        )


class FakePackedWidget:
    def __init__(self, name: str) -> None:
        self.name = name
        self.managed = True
        self.pack_calls: list[dict[str, object]] = []
        self.forgotten = False

    def winfo_manager(self) -> str:
        return "pack" if self.managed else ""

    def pack_forget(self) -> None:
        self.managed = False
        self.forgotten = True

    def pack(self, **kwargs: object) -> None:
        self.managed = True
        self.pack_calls.append(kwargs)


class FakeSectionBody:
    def __init__(self) -> None:
        self.expanded_states: list[bool] = []
        self._desktop_set_expanded = self.expanded_states.append


class FakeSidebarCanvas:
    def __init__(self) -> None:
        self.configure_calls: list[dict[str, object]] = []

    def bbox(self, _tag: object) -> tuple[int, int, int, int]:
        return (0, 0, 100, 200)

    def configure(self, **kwargs: object) -> None:
        self.configure_calls.append(kwargs)


class FakeWorldgenViewer:
    def __init__(self) -> None:
        mode_row = FakePackedWidget("mode")
        hint = FakePackedWidget("hint")
        auto_row = FakePackedWidget("auto")
        banner = FakePackedWidget("banner")
        self._worldgen_generation_widget_records = [
            desktop_improvements.PackedWidgetRecord(
                mode_row,
                {"fill": "x"},
                hint,
            ),
            desktop_improvements.PackedWidgetRecord(
                hint,
                {"anchor": "w"},
                auto_row,
            ),
            desktop_improvements.PackedWidgetRecord(
                auto_row,
                {"side": "left"},
                None,
            ),
        ]
        self.generation_widgets = (mode_row, hint, auto_row)
        self._worldgen_completion_banner = banner
        self.banner = banner
        self._worldgen_generation_controls_hidden = False
        self.sidebar_canvas = FakeSidebarCanvas()


class FakeAdvancedViewer:
    def __init__(self) -> None:
        self.sections: list[tuple[str, bool]] = []
        self.hints: list[str] = []
        self.buttons: list[tuple[str, object]] = []

    def _make_collapsible_sidebar_section(
        self,
        title: str,
        *,
        expanded: bool,
    ) -> "FakeAdvancedViewer":
        self.sections.append((title, expanded))
        return self

    def _make_sidebar_hint(
        self,
        text: str,
        *,
        parent: object,
    ) -> "FakePackable":
        self.hints.append(text)
        return FakePackable()

    def _make_sidebar_button(
        self,
        parent: object,
        *,
        text: str,
        command: object,
    ) -> "FakePackable":
        self.buttons.append((text, command))
        return FakePackable()


class FakePackable:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs
        self.pack_calls: list[dict[str, object]] = []

    def pack(self, **kwargs: object) -> None:
        self.pack_calls.append(kwargs)


class FakeMenu:
    def __init__(self) -> None:
        self.labels: list[str] = []
        self.commands: list[object] = []
        self.delete_calls: list[tuple[object, object]] = []

    def delete(self, first: object, last: object = None) -> None:
        self.delete_calls.append((first, last))
        self.labels = []
        self.commands = []

    def add_command(self, *, label: str, command: object) -> None:
        self.labels.append(label)
        self.commands.append(command)


class FakeOptionMenu(FakePackable):
    def __init__(self) -> None:
        super().__init__()
        self.menu = FakeMenu()


class FakeModeViewer:
    def __init__(self) -> None:
        self.root = object()
        self.sidebar = object()
        self.captions: list[str] = []
        self.option_menu = FakeOptionMenu()

    def _make_sidebar_caption(
        self,
        text: str,
        *,
        parent: object | None = None,
    ) -> "FakePackable":
        self.captions.append(text)
        return FakePackable()

    def _make_sidebar_option_menu(
        self,
        parent: object,
        variable: object,
    ) -> FakeOptionMenu:
        self.option_variable = variable
        return self.option_menu

    def _option_menu_widget(
        self,
        option_menu: FakeOptionMenu,
    ) -> FakeMenu:
        return option_menu.menu


class FakeBuildPanelViewer:
    def __init__(self) -> None:
        self.sections: list[tuple[str, bool]] = []

    def _make_collapsible_sidebar_section(
        self,
        title: str,
        *,
        expanded: bool,
    ) -> object:
        self.sections.append((title, expanded))
        return object()


class FakeRouteStepsText:
    def __init__(
        self,
        *,
        count_result: object = ("3",),
        raise_keyword_type_error: bool = False,
        width: int = 30,
    ) -> None:
        self.count_result = count_result
        self.raise_keyword_type_error = raise_keyword_type_error
        self.width = width
        self.count_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def update_idletasks(self) -> None:
        return None

    def count(self, *args: object, **kwargs: object) -> object:
        self.count_calls.append((args, kwargs))
        if self.raise_keyword_type_error and "return_ints" in kwargs:
            raise TypeError("unexpected keyword argument 'return_ints'")
        return self.count_result

    def cget(self, key: str) -> int:
        if key != "width":
            raise KeyError(key)
        return self.width


class FakeRouteStepsViewer:
    def __init__(self, route_steps_text: FakeRouteStepsText) -> None:
        self.route_steps_text = route_steps_text


def _sample_route() -> base.RouteResult:
    return base.RouteResult(
        start_key=base.BLACKPORT_VAR,
        end_key="P_B2",
        total_distance=10,
        total_interchanges=0,
        steps=(
            base.RouteStep(
                kind="ride",
                start_key=base.BLACKPORT_VAR,
                end_key="P_B2",
                distance=10,
                path_points=((100, 200), (140, 240)),
                line_name="B",
                stop_vars=(base.BLACKPORT_VAR, "P_B2"),
            ),
        ),
    )


class DesktopModeShellTests(unittest.TestCase):
    def test_mode_model_has_expected_order(self) -> None:
        self.assertEqual(
            desktop_improvements._desktop_mode_labels(),
            [
                "All",
                "Explore",
                "Directions",
                "Construction",
                "Edit",
                "World",
                "Advanced",
            ],
        )

    def test_desktop_mode_defaults_to_all(self) -> None:
        viewer = FakeModeViewer()

        with mock.patch.object(
            desktop_improvements.tk,
            "StringVar",
            FakeStringVar,
        ):
            desktop_improvements._ensure_desktop_mode_state(viewer)

        self.assertEqual(viewer.desktop_mode_key, "all")
        self.assertEqual(viewer.desktop_mode_var.get(), "All")
        self.assertIn(
            "Show all",
            viewer.desktop_mode_status_var.get(),
        )

    def test_invalid_mode_label_falls_back_to_all(self) -> None:
        mode = desktop_improvements._desktop_mode_by_label("Not a mode")

        self.assertEqual(mode.key, "all")

    def test_directions_mode_focuses_directions_section(self) -> None:
        viewer = mock.Mock(
            desktop_mode_key="directions",
            sidebar_canvas=None,
        )
        directions_card = FakePackedWidget("directions")
        show_hide_card = FakePackedWidget("show-hide")
        checklist_card = FakePackedWidget("checklist")
        directions_body = FakeSectionBody()
        show_hide_body = FakeSectionBody()
        checklist_body = FakeSectionBody()
        viewer._desktop_section_records = [
            desktop_improvements.PackedSectionRecord(
                title="Directions",
                widget=directions_card,
                pack_options={"fill": "x"},
                next_sibling=None,
                body_widget=directions_body,
            ),
            desktop_improvements.PackedSectionRecord(
                title="Show/Hide",
                widget=show_hide_card,
                pack_options={"fill": "x"},
                next_sibling=None,
                body_widget=show_hide_body,
            ),
            desktop_improvements.PackedSectionRecord(
                title="Checklist",
                widget=checklist_card,
                pack_options={"fill": "x"},
                next_sibling=None,
                body_widget=checklist_body,
            ),
        ]

        desktop_improvements._apply_desktop_mode_visibility(viewer)

        self.assertTrue(directions_card.managed)
        self.assertTrue(show_hide_card.managed)
        self.assertFalse(checklist_card.managed)
        self.assertEqual(directions_body.expanded_states[-1], True)
        self.assertEqual(show_hide_body.expanded_states[-1], False)

    def test_remaining_modes_focus_their_primary_sections(self) -> None:
        cases = (
            (
                "construction",
                {
                    "Checklist": (True, False),
                    "Priority List": (True, False),
                    "Railways": (True, True),
                    "Show/Hide": (False, None),
                },
            ),
            (
                "edit",
                {
                    "Pathing": (True, True),
                    "Railways": (True, False),
                    "Show/Hide": (True, False),
                    "Checklist": (False, None),
                },
            ),
            (
                "world",
                {
                    "World Map": (True, True),
                    "Show/Hide": (True, False),
                    "Directions": (False, None),
                },
            ),
            (
                "advanced",
                {
                    "Advanced / Experimental": (True, True),
                    "World Map": (True, False),
                    "Directions": (False, None),
                },
            ),
        )

        for mode_key, expectations in cases:
            with self.subTest(mode_key=mode_key):
                viewer = mock.Mock(
                    desktop_mode_key=mode_key,
                    sidebar_canvas=None,
                )
                records: list[desktop_improvements.PackedSectionRecord] = []
                widgets: dict[str, FakePackedWidget] = {}
                bodies: dict[str, FakeSectionBody] = {}
                for title in (
                    "Checklist",
                    "Priority List",
                    "Railways",
                    "Pathing",
                    "Show/Hide",
                    "World Map",
                    "Advanced / Experimental",
                    "Directions",
                ):
                    widget = FakePackedWidget(title)
                    body = FakeSectionBody()
                    widgets[title] = widget
                    bodies[title] = body
                    records.append(
                        desktop_improvements.PackedSectionRecord(
                            title=title,
                            widget=widget,
                            pack_options={"fill": "x"},
                            next_sibling=None,
                            body_widget=body,
                        )
                    )
                viewer._desktop_section_records = records

                desktop_improvements._apply_desktop_mode_visibility(viewer)

                for title, (is_visible, is_expanded) in expectations.items():
                    self.assertEqual(widgets[title].managed, is_visible)
                    if is_expanded is not None:
                        self.assertEqual(
                            bodies[title].expanded_states[-1],
                            is_expanded,
                        )

    def test_mode_shell_installs_workspace_mode_rail(self) -> None:
        viewer = FakeModeViewer()

        with (
            mock.patch.object(
                desktop_improvements.tk,
                "StringVar",
                FakeStringVar,
            ),
            mock.patch.object(
                desktop_improvements.tk,
                "StringVar",
                FakeStringVar,
            ),
            mock.patch.object(
                desktop_improvements.workspace,
                "install_mode_rail",
            ) as install_mode_rail,
            mock.patch.object(
                desktop_improvements.workspace,
                "sync_workspace",
            ),
        ):
            desktop_improvements._append_desktop_mode_shell(viewer)

        install_mode_rail.assert_called_once()
        self.assertEqual(
            install_mode_rail.call_args.kwargs["modes"],
            desktop_improvements.DESKTOP_MODES,
        )

    def test_build_panel_starts_sections_collapsed(self) -> None:
        viewer = FakeBuildPanelViewer()
        original_build = desktop_improvements._ORIGINAL_BUILD_ROUTE_PANEL

        def build_panel(viewer_arg: FakeBuildPanelViewer) -> None:
            viewer_arg._make_collapsible_sidebar_section(
                "Checklist",
                expanded=True,
            )
            viewer_arg._make_collapsible_sidebar_section(
                "Show/Hide",
                expanded=True,
            )
            viewer_arg._make_collapsible_sidebar_section(
                "Priority List",
                expanded=False,
            )

        try:
            desktop_improvements._ORIGINAL_BUILD_ROUTE_PANEL = build_panel
            with (
                mock.patch.object(
                    desktop_improvements,
                    "_append_desktop_mode_shell",
                ),
                mock.patch.object(
                    desktop_improvements,
                    "_append_fit_route_controls",
                ),
                mock.patch.object(
                    desktop_improvements,
                    "_capture_generation_widgets",
                ),
                mock.patch.object(
                    desktop_improvements,
                    "_append_advanced_section",
                ),
            ):
                desktop_improvements._patched_build_route_panel(viewer)
        finally:
            desktop_improvements._ORIGINAL_BUILD_ROUTE_PANEL = original_build

        self.assertEqual(
            viewer.sections,
            [
                ("Checklist", False),
                ("Show/Hide", False),
                ("Priority List", False),
            ],
        )


class DesktopMmcpVisualTests(unittest.TestCase):
    def test_station_marker_uses_double_diamond_for_junctions(self) -> None:
        self.assertEqual(
            desktop_improvements._station_marker_text(
                base.BLACKPORT_VAR
            ),
            desktop_improvements.MMCP_SYMBOL_JUNCTION,
        )
        self.assertEqual(
            desktop_improvements._station_marker_text("not-a-stop"),
            desktop_improvements.MMCP_SYMBOL_STATION,
        )

    def test_diamond_marker_points_trace_rotated_square(self) -> None:
        self.assertEqual(
            desktop_improvements._diamond_marker_points(
                10.0,
                20.0,
                4.0,
            ),
            (10.0, 16.0, 14.0, 20.0, 10.0, 24.0, 6.0, 20.0),
        )

    def test_home_marker_uses_fixed_coordinate_not_station_position(
        self,
    ) -> None:
        phosphagos = base.MetroStop(
            "P_E6",
            "Mt. Phosphagos",
            -2555,
            1325,
        )
        canvas = FakeMarkerCanvas()
        viewer = SimpleNamespace(
            canvas=canvas,
            station_canvas_positions={phosphagos.var: (10.0, 20.0)},
            selected_stop_var=None,
            world_to_canvas=mock.Mock(return_value=(33.0, 44.0)),
            _visible_line_names=mock.Mock(return_value={"E"}),
            _stop_visible_line_names=mock.Mock(return_value=("E",)),
            _stop_fill_for_visible_lines=mock.Mock(return_value="#7a4eb2"),
        )

        with (
            mock.patch.object(desktop_improvements.tk, "Canvas", FakeMarkerCanvas),
            mock.patch.object(base, "METRO_STOPS", (phosphagos,)),
            mock.patch.object(
                base,
                "STOP_LINE_NAMES",
                {phosphagos.var: ("E",)},
            ),
        ):
            desktop_improvements._overlay_web_station_markers(viewer)

        viewer.world_to_canvas.assert_called_once_with((-2556, -1340))
        home_polygons = [
            args
            for kind, args, kwargs in canvas.calls
            if kind == "polygon"
            and kwargs.get("tags") == ("desktop_home_marker",)
        ]
        self.assertEqual(
            home_polygons,
            [
                (
                    (
                        33.0,
                        30.0,
                        47.0,
                        44.0,
                        33.0,
                        58.0,
                        19.0,
                        44.0,
                    ),
                )
            ],
        )
        self.assertIn(("raise", ("desktop_home_marker",), {}), canvas.calls)

    def test_button_palette_matches_web_action_tiers(self) -> None:
        self.assertEqual(
            desktop_improvements._mmcp_button_palette(
                "Route"
            ).background,
            "#397b49",
        )
        self.assertEqual(
            desktop_improvements._mmcp_button_palette(
                "Go"
            ).border,
            "#4f8e5c",
        )
        self.assertEqual(
            desktop_improvements._mmcp_button_palette(
                "Fit Route"
            ).foreground,
            desktop_improvements.WEB_DIAMOND,
        )
        self.assertEqual(
            desktop_improvements._mmcp_button_palette(
                "Clear City Limits"
            ).background,
            desktop_improvements.WEB_PANEL_RAISED,
        )

    def test_mode_change_triggers_visibility_update(self) -> None:
        viewer = mock.Mock(
            desktop_mode_var=FakeStringVar(value="Explore"),
            desktop_mode_status_var=FakeStringVar(value=""),
        )

        with mock.patch.object(
            desktop_improvements,
            "_apply_desktop_mode_visibility",
        ) as apply_visibility:
            desktop_improvements._set_desktop_mode_label(
                viewer,
                "World",
            )

        self.assertEqual(viewer.desktop_mode_key, "world")
        self.assertEqual(viewer.desktop_mode_var.get(), "World")
        apply_visibility.assert_called_once_with(viewer)

    def test_priority_entries_helper_keeps_named_and_frontier_only(self) -> None:
        named = base.MetroStop("P_TMP", "Named", 0, 0)
        unnamed = base.MetroStop("P_TMP2", "TMP2", 0, 0, has_full_station=True)
        frontier = base.MetroStop("P_FRONTIER", "TMP2", 0, 0)
        entries = [
            (named.var, "Named: needs signs"),
            (unnamed.var, "TMP: needs station"),
            (frontier.var, "TMP2: next on Line A after Blackport."),
        ]

        with mock.patch.object(
            base,
            "STOPS_BY_VAR",
            {
                named.var: named,
                unnamed.var: unnamed,
                frontier.var: frontier,
            },
        ):
            filtered = desktop_improvements._priority_entries_named_or_frontier(
                entries
            )

        self.assertEqual(
            [stop_var for stop_var, _text in filtered],
            [named.var, frontier.var],
        )

    def test_station_display_name_includes_abbreviation_when_present(self) -> None:
        stop = base.MetroStop("P_BKP", "Blackport", 0, 0, abbr="BKP")

        self.assertEqual(
            base._station_display_name(stop),
            "Blackport (BKP)",
        )

    def test_available_selected_stop_line_actions_prefers_add_switch_remove_order(self) -> None:
        metro_ext = mock.Mock()
        metro_ext._default_addable_line.return_value = "C"
        metro_ext._switchable_target_lines.return_value = ("C",)

        with (
            mock.patch.object(base, "LINE_STOP_VARS", {"A": ("P1",), "C": ("P1",)}),
            mock.patch.object(base, "STOP_LINE_NAMES", {"P1": ("A",)}),
        ):
            actions = desktop_improvements._available_selected_stop_line_actions(
                "P1",
                metro_ext,
            )

        self.assertEqual(actions, ("Add", "Switch", "Remove"))

    def test_available_selected_stop_line_actions_hides_switch_without_current_line(self) -> None:
        metro_ext = mock.Mock()
        metro_ext._default_addable_line.return_value = "A"
        metro_ext._switchable_target_lines.return_value = ("A",)

        with (
            mock.patch.object(base, "LINE_STOP_VARS", {"A": ("P1",)}),
            mock.patch.object(base, "STOP_LINE_NAMES", {"P1": ()}),
        ):
            actions = desktop_improvements._available_selected_stop_line_actions(
                "P1",
                metro_ext,
            )

        self.assertEqual(actions, ("Add",))

    def test_search_matches_abbreviation_before_station_code(self) -> None:
        abbreviation_stop = base.MetroStop("P_BK1", "Blackport", 0, 0, abbr="BKP")
        code_stop = base.MetroStop("P_BKP2", "BKP2", 0, 0)

        with mock.patch.object(base, "METRO_STOPS", (abbreviation_stop, code_stop)):
            matches = base.MetroMapViewer._search_matches(object(), "BKP")

        self.assertEqual(
            [stop.var for stop in matches[:2]],
            [abbreviation_stop.var, code_stop.var],
        )

    def test_resolve_stop_var_runtime_accepts_abbreviation(self) -> None:
        stop = base.MetroStop("P_BK1", "Blackport", 0, 0, abbr="BKP")

        with (
            mock.patch.object(base, "METRO_STOPS", (stop,)),
            mock.patch.object(base, "STOPS_BY_VAR", {stop.var: stop}),
            mock.patch.object(base, "STOPS_BY_LBL", {stop.lbl: stop}),
        ):
            self.assertEqual(
                base._resolve_stop_var_runtime("BKP"),
                stop.var,
            )

    def test_blank_search_status_has_no_instruction_text(self) -> None:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.search_var = FakeStringVar("")
        viewer.search_status_var = FakeStringVar("old")
        viewer.search_match_stop_vars = ["P_A"]

        base.MetroMapViewer._refresh_search_results(viewer)

        self.assertEqual(viewer.search_status_var.get(), "")
        self.assertEqual(viewer.search_match_stop_vars, [])

    def test_coordinate_search_places_cursor_crosshair_when_no_station_matches(self) -> None:
        viewer = base.MetroMapViewer.__new__(base.MetroMapViewer)
        viewer.search_var = FakeStringVar("123, -456")
        viewer.search_status_var = FakeStringVar("")
        viewer.search_match_stop_vars = []
        viewer.width = 800
        viewer.height = 600
        viewer._hide_suggestion_popup = mock.Mock()
        viewer._clear_metro_segment_selection = mock.Mock()
        viewer._center_on_world_point = mock.Mock()
        viewer.redraw = mock.Mock()
        viewer.selected_stop_var = "P_A"
        viewer.selected_path_node_key = "node:a"
        viewer.cursor_readout_coordinates = None
        viewer.show_cursor_guides = False
        viewer.hover_canvas_point = None

        with mock.patch.object(base, "METRO_STOPS", ()):
            base.MetroMapViewer._jump_to_first_search_result(viewer)

        self.assertEqual(viewer.cursor_readout_coordinates, (123, -456))
        self.assertTrue(viewer.show_cursor_guides)
        self.assertEqual(viewer.hover_canvas_point, (400.0, 300.0))
        self.assertIsNone(viewer.selected_stop_var)
        self.assertIsNone(viewer.selected_path_node_key)
        viewer._center_on_world_point.assert_called_once_with((123, -456))
        viewer.redraw.assert_called_once_with()


class DesktopRouteFitTests(unittest.TestCase):
    def test_route_steps_display_line_count_falls_back_without_return_ints(self) -> None:
        route_steps_text = FakeRouteStepsText(
            count_result=("4",),
            raise_keyword_type_error=True,
        )
        viewer = FakeRouteStepsViewer(route_steps_text)

        display_lines = base.MetroMapViewer._route_steps_display_line_count(
            viewer,
            "Route text",
        )

        self.assertEqual(display_lines, 4)
        self.assertEqual(len(route_steps_text.count_calls), 2)
        _first_args, first_kwargs = route_steps_text.count_calls[0]
        _second_args, second_kwargs = route_steps_text.count_calls[1]
        self.assertEqual(first_kwargs, {"return_ints": True})
        self.assertEqual(second_kwargs, {})

    def test_short_route_bounds_keep_minimum_span(self) -> None:
        bounds = desktop_improvements._route_fit_bounds_for_points(
            [(10.0, 20.0), (20.0, 30.0)]
        )

        self.assertEqual(bounds, (-435.0, 465.0, -425.0, 475.0))

    def test_route_plot_points_include_endpoints_and_step_points(self) -> None:
        viewer = FakeRouteViewer()
        viewer.route_request = (base.BLACKPORT_VAR, "P_B2")
        viewer.current_route = _sample_route()

        points = desktop_improvements._route_plot_points(viewer)

        self.assertIn((319, -339), points)
        self.assertIn((776, -115), points)
        self.assertIn((100.0, 200.0), points)
        self.assertIn((140.0, 240.0), points)
        self.assertGreaterEqual(len(points), 4)

    def test_refresh_current_route_does_not_schedule_auto_fit(self) -> None:
        viewer = FakeRouteViewer()
        original_refresh = (
            desktop_improvements._ORIGINAL_REFRESH_CURRENT_ROUTE
        )

        def refresh(viewer_arg: FakeRouteViewer) -> None:
            viewer_arg.route_request = (base.BLACKPORT_VAR, "P_B2")
            viewer_arg.current_route = _sample_route()

        try:
            desktop_improvements._ORIGINAL_REFRESH_CURRENT_ROUTE = refresh
            desktop_improvements._patched_refresh_current_route(viewer)
        finally:
            desktop_improvements._ORIGINAL_REFRESH_CURRENT_ROUTE = (
                original_refresh
            )

        self.assertEqual(viewer.root.idle_callbacks, [])

    def test_plan_route_schedules_fit_after_route_is_ready(self) -> None:
        viewer = FakeRouteViewer()
        original_plan = desktop_improvements._ORIGINAL_PLAN_ROUTE

        def plan_route(viewer_arg: FakeRouteViewer) -> None:
            viewer_arg.route_request = (base.BLACKPORT_VAR, "P_B2")
            viewer_arg.current_route = _sample_route()

        try:
            desktop_improvements._ORIGINAL_PLAN_ROUTE = plan_route
            desktop_improvements._patched_plan_route(viewer)
        finally:
            desktop_improvements._ORIGINAL_PLAN_ROUTE = original_plan

        self.assertEqual(len(viewer.root.idle_callbacks), 1)
        callback = viewer.root.idle_callbacks[0]
        assert callable(callback)
        callback()
        self.assertEqual(len(viewer.fit_calls), 1)
        _bounds, kwargs = viewer.fit_calls[0]
        self.assertEqual(kwargs["min_zoom"], 1.25)
        self.assertEqual(
            kwargs["margin_pixels"],
            desktop_improvements.ROUTE_FIT_MARGIN_PIXELS,
        )

    def test_route_option_change_schedules_refit(self) -> None:
        viewer = FakeRouteViewer()
        original_options_changed = (
            desktop_improvements._ORIGINAL_ON_ROUTE_OPTIONS_CHANGED
        )

        def options_changed(viewer_arg: FakeRouteViewer) -> None:
            viewer_arg.route_request = (base.BLACKPORT_VAR, "P_B2")
            viewer_arg.current_route = _sample_route()

        try:
            desktop_improvements._ORIGINAL_ON_ROUTE_OPTIONS_CHANGED = (
                options_changed
            )
            desktop_improvements._patched_on_route_options_changed(viewer)
        finally:
            desktop_improvements._ORIGINAL_ON_ROUTE_OPTIONS_CHANGED = (
                original_options_changed
            )

        self.assertEqual(len(viewer.root.idle_callbacks), 1)

    def test_swap_schedules_refit_through_plan_route(self) -> None:
        viewer = FakeRouteViewer()
        original_plan = desktop_improvements._ORIGINAL_PLAN_ROUTE

        def plan_route(viewer_arg: FakeRouteViewer) -> None:
            viewer_arg.route_request = (base.BLACKPORT_VAR, "P_B2")
            viewer_arg.current_route = _sample_route()

        try:
            desktop_improvements._ORIGINAL_PLAN_ROUTE = plan_route
            viewer._plan_route = (
                lambda: desktop_improvements._patched_plan_route(
                    viewer
                )
            )
            base.MetroMapViewer._swap_route_endpoints(viewer)
        finally:
            desktop_improvements._ORIGINAL_PLAN_ROUTE = original_plan

        self.assertEqual(viewer.route_start_var.get(), "Dicton")
        self.assertEqual(viewer.route_end_var.get(), "Blackport")
        self.assertTrue(viewer.route_controls_dirty)
        self.assertEqual(len(viewer.root.idle_callbacks), 1)

    def test_failed_plan_route_cancels_pending_fit(self) -> None:
        viewer = FakeRouteViewer()
        viewer._desktop_route_fit_after_id = "after-old"
        original_plan = desktop_improvements._ORIGINAL_PLAN_ROUTE

        def plan_route(viewer_arg: FakeRouteViewer) -> None:
            viewer_arg.route_request = None
            viewer_arg.current_route = None

        try:
            desktop_improvements._ORIGINAL_PLAN_ROUTE = plan_route
            desktop_improvements._patched_plan_route(viewer)
        finally:
            desktop_improvements._ORIGINAL_PLAN_ROUTE = original_plan

        self.assertEqual(viewer.root.cancelled, ["after-old"])
        self.assertEqual(viewer.root.idle_callbacks, [])

    def test_fit_route_without_route_shows_non_destructive_message(self) -> None:
        viewer = FakeRouteViewer()

        with mock.patch.object(
            desktop_improvements.messagebox,
            "showinfo",
        ) as showinfo:
            fitted = desktop_improvements._fit_current_route_view(
                viewer,
                show_message=True,
            )

        self.assertFalse(fitted)
        showinfo.assert_called_once_with(
            "Fit Route",
            "Calculate a route before fitting the route view.",
            parent=viewer.root,
        )
        self.assertEqual(viewer.fit_calls, [])


class DesktopPathDetectionTests(unittest.TestCase):
    def test_advanced_section_defaults_collapsed_and_labels_tool(self) -> None:
        viewer = FakeAdvancedViewer()

        desktop_improvements._append_advanced_section(viewer)

        self.assertEqual(
            viewer.sections,
            [("Advanced / Experimental", False)],
        )
        self.assertEqual(
            viewer.buttons[0][0],
            "Detect Paths for Selected Station",
        )
        self.assertIn("unsupported", viewer.hints[0].lower())

    def test_experimental_path_detection_requires_selected_station(self) -> None:
        viewer = mock.Mock(root=object(), selected_stop_var=None)

        with (
            mock.patch.object(
                desktop_improvements.messagebox,
                "showinfo",
            ) as showinfo,
            mock.patch.object(
                desktop_improvements.path_detection,
                "detect_paths_for_stop",
            ) as detect_paths,
        ):
            desktop_improvements._run_experimental_path_detection(
                viewer
            )

        detect_paths.assert_not_called()
        showinfo.assert_called_once()

    def test_experimental_path_detection_requires_confirmation(self) -> None:
        viewer = mock.Mock(
            root=object(),
            selected_stop_var=base.BLACKPORT_VAR,
        )

        with (
            mock.patch.object(
                desktop_improvements.messagebox,
                "askyesno",
                return_value=False,
            ) as askyesno,
            mock.patch.object(
                desktop_improvements.path_detection,
                "detect_paths_for_stop",
            ) as detect_paths,
        ):
            desktop_improvements._run_experimental_path_detection(
                viewer
            )

        askyesno.assert_called_once()
        detect_paths.assert_not_called()

    def test_experimental_path_detection_runs_existing_workflow(self) -> None:
        viewer = mock.Mock(
            root=object(),
            selected_stop_var=base.BLACKPORT_VAR,
        )

        with (
            mock.patch.object(
                desktop_improvements.messagebox,
                "askyesno",
                return_value=True,
            ),
            mock.patch.object(
                desktop_improvements.path_detection,
                "detect_paths_for_stop",
            ) as detect_paths,
        ):
            desktop_improvements._run_experimental_path_detection(
                viewer
            )

        detect_paths.assert_called_once_with(viewer, base.BLACKPORT_VAR)

    def test_normal_popup_draws_without_detection_wrapper(self) -> None:
        viewer = mock.Mock(
            _path_detection_hide_selected_popup=False,
            _desktop_workspace_shell=None,
        )
        original_draw = desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO
        normal_draw = mock.Mock()

        try:
            desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO = normal_draw
            desktop_improvements._draw_selected_stop_info_without_detection_button(
                viewer
            )
        finally:
            desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO = (
                original_draw
            )

        normal_draw.assert_called_once_with(viewer)

    def test_normal_popup_receives_mmcp_decoration(self) -> None:
        viewer = mock.Mock(
            _path_detection_hide_selected_popup=False,
            _desktop_workspace_shell=None,
        )
        original_draw = desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO
        normal_draw = mock.Mock()

        try:
            desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO = normal_draw
            with mock.patch.object(
                desktop_improvements,
                "_decorate_selected_stop_popup",
            ) as decorate:
                desktop_improvements._draw_selected_stop_info_without_detection_button(
                    viewer
                )
        finally:
            desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO = (
                original_draw
            )

        normal_draw.assert_called_once_with(viewer)
        decorate.assert_called_once_with(viewer)

    def test_docked_inspector_suppresses_persistent_station_popup(self) -> None:
        viewer = mock.Mock(
            _path_detection_hide_selected_popup=False,
            _desktop_workspace_shell=None,
        )
        original_draw = desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO
        normal_draw = mock.Mock()

        try:
            desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO = normal_draw
            with mock.patch.object(
                desktop_improvements.inspector,
                "has_docked_inspector",
                return_value=True,
            ):
                desktop_improvements._draw_selected_stop_info_without_detection_button(
                    viewer
                )
        finally:
            desktop_improvements._NORMAL_DRAW_SELECTED_STOP_INFO = original_draw

        viewer._clear_info_popup.assert_called_once_with()
        normal_draw.assert_not_called()

    def test_docked_inspector_suppresses_persistent_segment_popup(self) -> None:
        viewer = mock.Mock(_desktop_workspace_shell=None)
        original_draw = (
            desktop_improvements._ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO
        )
        normal_draw = mock.Mock()

        try:
            desktop_improvements._ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO = (
                normal_draw
            )
            with mock.patch.object(
                desktop_improvements.inspector,
                "has_docked_inspector",
                return_value=True,
            ):
                desktop_improvements._draw_selected_metro_segment_info_without_docked_popup(
                    viewer
                )
        finally:
            desktop_improvements._ORIGINAL_DRAW_SELECTED_METRO_SEGMENT_INFO = (
                original_draw
            )

        viewer._clear_info_popup.assert_called_once_with()
        normal_draw.assert_not_called()

    def test_docked_inspector_suppresses_persistent_path_node_popup(self) -> None:
        viewer = mock.Mock(_desktop_workspace_shell=None)
        original_draw = (
            desktop_improvements._ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO
        )
        normal_draw = mock.Mock()

        try:
            desktop_improvements._ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO = (
                normal_draw
            )
            with mock.patch.object(
                desktop_improvements.inspector,
                "has_docked_inspector",
                return_value=True,
            ):
                desktop_improvements._draw_selected_path_node_info_without_docked_popup(
                    viewer
                )
        finally:
            desktop_improvements._ORIGINAL_DRAW_SELECTED_PATH_NODE_INFO = (
                original_draw
            )

        viewer._clear_info_popup.assert_called_once_with()
        normal_draw.assert_not_called()


class DesktopWorldgenCompletionTests(unittest.TestCase):
    def test_completed_worldgen_hides_internal_void_checkbox(self) -> None:
        self.assertTrue(
            desktop_improvements._hide_widget_when_worldgen_complete(
                ["Circle internal voids"],
                is_frame=False,
            )
        )
        self.assertFalse(
            desktop_improvements._hide_widget_when_worldgen_complete(
                ["World Map Analysis"],
                is_frame=False,
            )
        )
        self.assertFalse(
            desktop_improvements._hide_widget_when_worldgen_complete(
                ["Export Block PNG"],
                is_frame=False,
            )
        )

    def test_completion_payload_requires_full_coverage_zero_unfinished_and_bounds(
        self,
    ) -> None:
        payload = {
            "colored_pixels": 25,
            "total_pixels": 25,
            "unfinished_point_count": 0,
            "min_x": 1,
            "max_x": 2,
            "min_z": 3,
            "max_z": 4,
        }

        self.assertTrue(
            desktop_improvements._worldgen_completion_payload_is_verified(
                payload,
                (1, 2, 3, 4),
            )
        )

    def test_completion_payload_rejects_rounded_or_uncertain_completion(
        self,
    ) -> None:
        base_payload = {
            "colored_pixels": 99,
            "total_pixels": 100,
            "unfinished_point_count": 0,
            "min_x": 1,
            "max_x": 2,
            "min_z": 3,
            "max_z": 4,
        }

        cases = [
            base_payload,
            {**base_payload, "colored_pixels": 100, "total_pixels": 0},
            {
                **base_payload,
                "colored_pixels": 100,
                "unfinished_point_count": 1,
            },
            {
                **base_payload,
                "colored_pixels": 100,
                "unfinished_point_count": None,
            },
            {**base_payload, "colored_pixels": 100, "max_z": 5},
        ]

        for payload in cases:
            with self.subTest(payload=payload):
                self.assertFalse(
                    desktop_improvements
                    ._worldgen_completion_payload_is_verified(
                        payload,
                        (1, 2, 3, 4),
                    )
                )

    def test_completion_controls_hide_and_restore(self) -> None:
        viewer = FakeWorldgenViewer()

        with mock.patch.object(
            desktop_improvements,
            "_worldgen_completion_is_verified",
            return_value=True,
        ):
            desktop_improvements._refresh_worldgen_control_visibility(
                viewer
            )

        self.assertTrue(viewer._worldgen_generation_controls_hidden)
        self.assertTrue(all(widget.forgotten for widget in viewer.generation_widgets))
        self.assertTrue(viewer.banner.managed)
        self.assertTrue(viewer.sidebar_canvas.configure_calls)

        with mock.patch.object(
            desktop_improvements,
            "_worldgen_completion_is_verified",
            return_value=False,
        ):
            desktop_improvements._refresh_worldgen_control_visibility(
                viewer
            )

        self.assertFalse(viewer._worldgen_generation_controls_hidden)
        self.assertFalse(viewer.banner.managed)
        self.assertTrue(all(widget.managed for widget in viewer.generation_widgets))


if __name__ == "__main__":
    unittest.main()
