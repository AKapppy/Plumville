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
        self.bindings: dict[str, object] = {}
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

    def grid_rowconfigure(self, *_args: object, **_kwargs: object) -> None:
        return None

    def grid_columnconfigure(self, *_args: object, **_kwargs: object) -> None:
        return None

    def grid_propagate(self, *_args: object, **_kwargs: object) -> None:
        return None

    def pack_propagate(self, *_args: object, **_kwargs: object) -> None:
        return None


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
        ):
            workspace._configure_workspace_hosts(viewer)
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
