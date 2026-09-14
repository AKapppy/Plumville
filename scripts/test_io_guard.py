"""Fail accidental host-data access in isolated Python test processes.

A regression guard for trusted tests, not a security sandbox for arbitrary code.
Python children inherit it through the isolated checkout's sitecustomize module.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys


def install() -> None:
    sandbox = Path(os.environ['PLUMVILLE_TEST_SANDBOX']).resolve()
    source = Path(os.environ['PLUMVILLE_TEST_SOURCE_ROOT']).resolve()

    def check_path(raw: object, *, writing: bool) -> None:
        if isinstance(raw, int) or raw is None:
            return
        path = Path(os.fsdecode(raw)).resolve()
        if path == Path(os.devnull):
            return
        if path.is_relative_to(sandbox):
            return
        private_parts = {
            'Application Support', '.worldgen', 'worldgen_data',
            'worldgen_output', 'metro_network.history', 'exports',
            'metro_network.last.json', 'path_detection_state.json',
        }
        if writing or path.is_relative_to(source) or private_parts.intersection(path.parts):
            raise PermissionError('Isolated tests attempted host filesystem access')

    def audit(event: str, args: tuple[object, ...]) -> None:
        if event == 'open':
            mode, flags = args[1:3]
            writing = (
                isinstance(mode, str) and any(char in mode for char in 'wax+')
            ) or (
                isinstance(flags, int)
                and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            )
            check_path(args[0], writing=bool(writing))
        elif event in {'os.remove', 'os.rmdir', 'os.mkdir', 'os.chmod', 'os.utime'}:
            check_path(args[0], writing=True)
        elif event in {'os.rename', 'os.link', 'os.symlink'}:
            check_path(args[0], writing=True)
            check_path(args[1], writing=True)
        elif event in {'os.listdir', 'os.scandir'}:
            check_path(args[0], writing=False)
        elif event == 'subprocess.Popen':
            executable = Path(os.fsdecode(args[0])).name
            if not executable.startswith(('python', 'node', 'npm')):
                raise PermissionError('Isolated tests may not launch runtime services')
        elif event == 'socket.connect':
            raise PermissionError('Isolated tests may not contact runtime services')

    sys.addaudithook(audit)
