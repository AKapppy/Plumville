from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
import unittest
from unittest import mock

from plumville.desktop import workspace


class FakeVar:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def set(self, value: object) -> None:
        self.value = value


class FakeWidget:
    def __init__(self, master: object | None = None, **kwargs: object) -> None:
        self.master = master
        self.kwargs = dict(kwargs)
        self.children: list[FakeWidget] = []
        self.grid_calls: list[dict[str, object]] = []
        self.pack_calls: list[dict[str, object]] = []
        self.created_windows: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.bindings: dict[str, object] = {}
        self.idle_callbacks: list[object] = []
        self.hidden = False
        if isinstance(master, FakeWidget):
            master.children.append(self)

    def configure(self, **kwargs: object) -> None:
        self.kwargs.update(kwargs)

    def cget(self, key: str) -> object:
        return self.kwargs[key]

    def grid(self, **kwargs: object) -> None:
        self.grid_calls.append(kwargs)
        self.hidden = False

    def grid_remove(self) -> None:
        self.hidden = True

    def pack(self, **kwargs: object) -> None:
        self.pack_calls.append(kwargs)
        self.hidden = False

    def bind(self, event: str, callback: object) -> None:
        self.bindings[event] = callback

    def create_window(self, *args: object, **kwargs: object) -> int:
        self.created_windows.append((args, kwargs))
        return len(self.created_windows)

    def itemconfigure(self, *_args: object, **_kwargs: object) -> None:
        return None

    def bbox(self, *_args: object) -> tuple[int, int, int, int]:
        return (0, 0, 300, 600)

    def yview(self, *_args: object) -> tuple[float, float]:
        return (0.0, 1.0)

    def yview_scroll(self, *_args: object) -> None:
        return None

    def set(self, *_args: object) -> None:
        return None

    def after_idle(self, callback: object) -> str:
        self.idle_callbacks.append(callback)
        return f"after-{len(self.idle_callbacks)}"

    def update_idletasks(self) -> None:
        return None

    def grid_rowconfigure(self, *_args: object, **_kwargs: object) -> None:
        return None

    def grid_columnconfigure(self, *_args: object, **_kwargs: object) -> None:
        return None

    def grid_propagate(self, *_args: object, **_kwargs: object) -> None:
        return None

    def pack_propagate(self, *_args: object, **_kwargs: object) -> None:
        return None

    def delete(self, *_args: object) -> None:
        return None

    def add_command(self, **_kwargs: object) -> None:
        return None


class FakeMenu(FakeWidget):
    def __init__(self, master: object | None = None, **kwargs: object) -> None:
        super().__init__(master, **kwargs)
        self.labels: list[str] = []
        self.commands: list[object] = []
        self.delete_calls: list[tuple[object, ...]] = []

    def delete(self, *args: object) -> None:
        self.delete_calls.append(args)
        self.labels.clear()
        self.commands.clear()

    def add_command(self, *, label: str, command: object) -> None:
        self.labels.append(label)
        self.commands.append(command)


class FakeCanvas(FakeWidget):
    def __init__(
        self,
        master: object | None = None,
        *,
        width_value: int = 300,
        height_value: int = 200,
        **kwargs: object,
    ) -> None:
        super().__init__(master, **kwargs)
        self.width_value = width_value
        self.height_value = height_value

    def winfo_width(self) -> int:
        return self.width_value

    def winfo_height(self) -> int:
        return self.height_value


@dataclass(frozen=True)
class FakeMode:
    key: str
    label: str
    description: str


class DesktopWorkspaceTests(unittest.TestCase):
    def _viewer(self) -> SimpleNamespace:
        return SimpleNamespace(
            root=FakeWidget(),
            stats_summary_var=FakeVar("173 stations · 25 open"),
            route_summary_var=FakeVar("Choose two stations or coordinates."),
            world_map_status_var=FakeVar("World map ready"),
            path_click_mode_var=FakeVar(False),
            path_click_status_var=FakeVar(""),
            desktop_mode_key="all",
        )

    def _modes(self) -> tuple[FakeMode, ...]:
        return (
            FakeMode("all", "All", "Show all"),
            FakeMode("directions", "Directions", "Plan routes"),
            FakeMode("world", "World", "Render world"),
        )

    def test_configure_workspace_hosts_creates_regions_once(self) -> None:
        viewer = self._viewer()

        with (
            mock.patch.object(workspace.tk, "Frame", FakeWidget),
            mock.patch.object(workspace.tk, "Label", FakeWidget),
            mock.patch.object(workspace.tk, "Canvas", FakeCanvas),
            mock.patch.object(workspace.tk, "Menubutton", FakeWidget),
            mock.patch.object(workspace.tk, "Menu", FakeMenu),
            mock.patch.object(workspace.tk, "Scrollbar", FakeWidget),
        ):
            workspace._configure_workspace_hosts(viewer)
            first_shell = viewer._desktop_workspace_shell
            workspace.install_mode_rail(
                viewer,
                modes=self._modes(),
                on_mode_select=lambda _label: None,
            )
            workspace.install_mode_rail(
                viewer,
                modes=self._modes(),
                on_mode_select=lambda _label: None,
            )
            workspace._configure_workspace_hosts(viewer)

        self.assertIs(viewer._desktop_workspace_shell, first_shell)
        self.assertIs(viewer.workspace_secondary_parent, first_shell.secondary_body)
        self.assertIs(viewer.workspace_map_parent, first_shell.map_shell)
        self.assertTrue(first_shell.mode_rail.hidden)
        self.assertEqual(
            first_shell.topbar_mode_menu.labels,
            ["All", "Directions", "World"],
        )
        self.assertEqual(
            tuple(first_shell.mode_buttons),
            ("all", "directions", "world"),
        )

    def test_sync_workspace_updates_mode_panels_and_status_strip(self) -> None:
        viewer = self._viewer()
        viewer.route_summary_var = FakeVar("Blackport to Dicton\n11.7 km")
        viewer.desktop_mode_key = "directions"

        with (
            mock.patch.object(workspace.tk, "Frame", FakeWidget),
            mock.patch.object(workspace.tk, "Label", FakeWidget),
            mock.patch.object(workspace.tk, "Canvas", FakeCanvas),
            mock.patch.object(workspace.tk, "Menubutton", FakeWidget),
            mock.patch.object(workspace.tk, "Menu", FakeMenu),
            mock.patch.object(workspace.tk, "Scrollbar", FakeWidget),
        ):
            workspace._configure_workspace_hosts(viewer)
            workspace.install_mode_rail(
                viewer,
                modes=self._modes(),
                on_mode_select=lambda _label: None,
            )
            workspace.sync_workspace(
                viewer,
                modes=self._modes(),
                active_mode_key="directions",
            )

        shell = viewer._desktop_workspace_shell
        self.assertEqual(
            shell.secondary_title_label.kwargs["text"],
            "Directions Mode",
        )
        self.assertEqual(shell.topbar_mode_label.kwargs["text"], "Directions ▾")
        self.assertEqual(
            shell.status_label.kwargs["text"],
            "Blackport to Dicton",
        )
        self.assertFalse(shell.status_strip.hidden)
        self.assertEqual(
            shell.mode_buttons["directions"].kwargs["fg"],
            workspace.ACCENT,
        )

    def test_set_inspector_visible_hides_and_restores_inspector(self) -> None:
        viewer = self._viewer()

        with (
            mock.patch.object(workspace.tk, "Frame", FakeWidget),
            mock.patch.object(workspace.tk, "Label", FakeWidget),
            mock.patch.object(workspace.tk, "Canvas", FakeCanvas),
            mock.patch.object(workspace.tk, "Menubutton", FakeWidget),
            mock.patch.object(workspace.tk, "Menu", FakeMenu),
            mock.patch.object(workspace.tk, "Scrollbar", FakeWidget),
        ):
            workspace._configure_workspace_hosts(viewer)
            viewer._desktop_inspector_visible = True
            viewer._desktop_workspace_shell.inspector_shell.hidden = False
            workspace.set_inspector_visible(viewer, False)
            self.assertTrue(viewer._desktop_workspace_shell.inspector_shell.hidden)
            self.assertEqual(
                viewer._desktop_workspace_shell.inspector_toggle_button.kwargs["text"],
                "Show Inspector",
            )
            workspace.set_inspector_visible(viewer, True)

        self.assertFalse(viewer._desktop_workspace_shell.inspector_shell.hidden)
        self.assertEqual(
            viewer._desktop_workspace_shell.inspector_header_button.kwargs["text"],
            "Hide",
        )

    def test_hidden_inspector_reopens_for_new_task_only(self) -> None:
        viewer = self._viewer()

        with (
            mock.patch.object(workspace.tk, "Frame", FakeWidget),
            mock.patch.object(workspace.tk, "Label", FakeWidget),
            mock.patch.object(workspace.tk, "Canvas", FakeCanvas),
            mock.patch.object(workspace.tk, "Menubutton", FakeWidget),
            mock.patch.object(workspace.tk, "Menu", FakeMenu),
            mock.patch.object(workspace.tk, "Scrollbar", FakeWidget),
        ):
            workspace._configure_workspace_hosts(viewer)
            shell = viewer._desktop_workspace_shell
            self.assertTrue(shell.inspector_shell.hidden)

            workspace.show_inspector_for_task(viewer, ("station", "P_A"))
            self.assertFalse(shell.inspector_shell.hidden)

            workspace.set_inspector_visible(viewer, False)
            self.assertTrue(shell.inspector_shell.hidden)

            workspace.show_inspector_for_task(viewer, ("station", "P_A"))
            self.assertTrue(shell.inspector_shell.hidden)

            workspace.show_inspector_for_task(viewer, ("station", "P_B"))
            self.assertFalse(shell.inspector_shell.hidden)

    def test_set_inspector_visible_preserves_previous_map_center_after_resize(self) -> None:
        viewer = self._viewer()
        viewer.width = 800
        viewer.height = 600
        viewer.selected_stop_var = None
        viewer.canvas_to_world = mock.Mock(return_value=(123, -456))
        viewer._center_on_world_point = mock.Mock()
        viewer.redraw = mock.Mock()

        with (
            mock.patch.object(workspace.tk, "Frame", FakeWidget),
            mock.patch.object(workspace.tk, "Label", FakeWidget),
            mock.patch.object(workspace.tk, "Canvas", FakeCanvas),
            mock.patch.object(workspace.tk, "Menubutton", FakeWidget),
            mock.patch.object(workspace.tk, "Menu", FakeMenu),
            mock.patch.object(workspace.tk, "Scrollbar", FakeWidget),
        ):
            workspace._configure_workspace_hosts(viewer)
            viewer._desktop_inspector_visible = True
            viewer._desktop_workspace_shell.inspector_shell.hidden = False
            workspace.set_inspector_visible(viewer, False)

        self.assertEqual(len(viewer.root.idle_callbacks), 1)
        viewer.root.idle_callbacks[0]()

        viewer.canvas_to_world.assert_called_once_with((400.0, 300.0))
        viewer._center_on_world_point.assert_called_once_with((123.0, 456.0))
        viewer.redraw.assert_called_once_with()

    def test_set_inspector_visible_keeps_selected_station_center_after_resize(self) -> None:
        viewer = self._viewer()
        stop = workspace.base.MetroStop("P_A", "Alpha", 10, 20)
        viewer.selected_stop_var = stop.var
        viewer.width = 800
        viewer.height = 600
        viewer.canvas_to_world = mock.Mock(return_value=(10, 20))
        viewer._center_on_world_point = mock.Mock()
        viewer.redraw = mock.Mock()

        with (
            mock.patch.object(workspace.tk, "Frame", FakeWidget),
            mock.patch.object(workspace.tk, "Label", FakeWidget),
            mock.patch.object(workspace.tk, "Canvas", FakeCanvas),
            mock.patch.object(workspace.tk, "Menubutton", FakeWidget),
            mock.patch.object(workspace.tk, "Menu", FakeMenu),
            mock.patch.object(workspace.tk, "Scrollbar", FakeWidget),
            mock.patch.object(workspace.base, "STOPS_BY_VAR", {stop.var: stop}),
        ):
            workspace._configure_workspace_hosts(viewer)
            viewer._desktop_inspector_visible = True
            viewer._desktop_workspace_shell.inspector_shell.hidden = False
            workspace.set_inspector_visible(viewer, False)
            self.assertEqual(len(viewer.root.idle_callbacks), 1)
            viewer.root.idle_callbacks[0]()

        viewer._center_on_world_point.assert_called_once_with((10.0, -20.0))
