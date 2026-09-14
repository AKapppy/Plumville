from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from plumville.core import network


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def fixture_payload() -> dict:
    # Deliberately differs from alphabetical order and needs in-memory defaults.
    return {
        'stops': [
            {'var': 'P_A1', 'lbl': 'Alpha', 'x': 0, 'y': 0, 'is_connected': True},
            {'var': 'P_A2', 'lbl': 'Beta', 'x': 20, 'y': 0},
            {'var': 'P_A3', 'lbl': 'Gamma', 'x': 40, 'y': 0},
        ],
        'line_colors': {'A': '#abcdef'},
        'line_stop_vars': {'A': ['P_A3', 'P_A1', 'P_A2']},
        'line_path_specs': {'A': [
            {'x_var': key, 'y_var': key} for key in ['P_A3', 'P_A1', 'P_A2']
        ]},
        'line_tunneled_stop_vars': {'A': ['P_A2', 'P_A3']},
    }


def snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): (
            path.stat().st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        )
        for path in root.rglob('*')
    }


class ReadOnlyPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copyfile(SOURCE_ROOT / 'legacy_core.py', self.root / 'legacy_core.py')
        (self.root / 'docs').mkdir()
        self.canonical = self.root / 'docs/metro_network.json'
        self.canonical.write_text(json.dumps(fixture_payload()), encoding='utf-8')
        (self.root / 'metro_network.last.json').write_text('backup sentinel\n')
        self.history = self.root / 'metro_network.history'
        self.history.mkdir()
        (self.history / '20000101-000000-000000.json').write_text('history sentinel\n')
        (self.root / 'priority_list.csv').write_text('CSV sentinel\n')

    def child(self, code: str, *, seed: str = '1') -> str:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED=seed)
        env['PYTHONPATH'] = str(SOURCE_ROOT)
        result = subprocess.run(
            [sys.executable, '-B', '-c', code], cwd=self.root, env=env,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_entrypoint_imports_and_extension_application_do_not_write(self) -> None:
        before = snapshot(self.root)
        self.child('''
import plumville_app
import metro_stops
metro_stops._apply_extensions_once()
metro_stops._apply_extensions_once()
assert metro_stops.base.METRO_NETWORK_PATH.parent.name == 'docs'
assert metro_stops.base.METRO_NETWORK_PATH.parent.parent == __import__('pathlib').Path.cwd()
''')
        self.assertEqual(snapshot(self.root), before)

    def test_load_normalizes_in_memory_without_touching_files(self) -> None:
        before = snapshot(self.root)
        self.child('''
import legacy_core as base
payload = base._load_network_payload()
assert payload['line_tunneled_stop_vars']['A'] == ['P_A3', 'P_A1', 'P_A2']
assert payload['stops'][0]['is_tunneled'] is True
assert payload['path_nodes'] == []
assert base.LINE_TUNNELED_STOP_VARS['A'] == frozenset(('P_A1', 'P_A2', 'P_A3'))
''')
        self.assertEqual(snapshot(self.root), before)

    def test_repeated_reads_reload_and_validation_do_not_rotate_full_history(self) -> None:
        for index in range(105):
            (self.history / f'19990101-000000-{index:06d}.json').write_text(f'{index}\n')
        before = snapshot(self.root)
        self.child('''
import importlib
import legacy_core as base
for _ in range(5):
    payload = base._load_network_payload()
    base.network.validate_network_payload(payload, unassociated_station_label=base.UNASSOCIATED_STATION_LABEL)
    base._reload_network_data()
    importlib.reload(base)
''')
        self.assertEqual(snapshot(self.root), before)

    def test_import_does_not_create_absent_backup_or_history(self) -> None:
        shutil.rmtree(self.history)
        (self.root / 'metro_network.last.json').unlink()
        before = snapshot(self.root)
        self.child('import plumville_app; import legacy_core; legacy_core._load_network_payload()')
        self.assertEqual(snapshot(self.root), before)

    def test_explicit_mutation_saves_and_preserves_prior_bytes_in_history(self) -> None:
        original = self.canonical.read_bytes()
        self.child('''
import legacy_core as base
base._update_stop_record('P_A2', lbl='Beta edited')
assert base.STOPS_BY_VAR['P_A2'].lbl == 'Beta edited'
''')
        saved = json.loads(self.canonical.read_bytes())
        self.assertEqual(saved['stops'][1]['lbl'], 'Beta edited')
        self.assertEqual(saved['line_tunneled_stop_vars']['A'], ['P_A3', 'P_A1', 'P_A2'])
        self.assertEqual((self.root / 'metro_network.last.json').read_bytes(), original)
        history = sorted(self.history.glob('*.json'))
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1].read_bytes(), original)
        self.assertEqual((self.root / 'priority_list.csv').read_text(), 'CSV sentinel\n')
        self.assertFalse(list(self.root.rglob('*.tmp')))
        before = snapshot(self.root)
        self.child('import legacy_core as base; base._write_network_payload(base._load_network_payload())')
        self.assertEqual(snapshot(self.root), before, 'An unchanged explicit save must be a no-op')

    def test_tunneled_membership_serialization_is_stable_across_hash_seeds_and_orders(self) -> None:
        code = '''
import json
import legacy_core as base
payload = base._load_network_payload()
outputs = []
for members in (['P_A2', 'P_A3'], ['P_A3', 'P_A2'], set(('P_A2', 'P_A3')), frozenset(('P_A3', 'P_A2'))):
    payload['line_tunneled_stop_vars'] = {'A': members}
    base._normalize_network_payload(payload)
    outputs.append(base.network.serialize_network_payload(payload))
assert len(set(outputs)) == 1
assert payload['line_tunneled_stop_vars']['A'] == payload['line_stop_vars']['A']
print(outputs[0], end='')
'''
        before = snapshot(self.root)
        outputs = [self.child(code, seed=str(seed)) for seed in (1, 7, 31, 123)]
        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(snapshot(self.root), before)

    def test_invalid_explicit_save_does_not_write_or_install_globals(self) -> None:
        before = snapshot(self.root)
        self.child('''
import legacy_core as base
payload = base._load_network_payload()
payload['stops'][1]['lbl'] = 'Alpha'
try:
    base._write_network_payload(payload)
except ValueError:
    pass
else:
    raise AssertionError('Expected duplicate-label validation failure')
assert base.STOPS_BY_VAR['P_A2'].lbl == 'Beta'
''')
        self.assertEqual(snapshot(self.root), before)

    def test_staging_failure_leaves_canonical_backup_and_history_unchanged(self) -> None:
        before = snapshot(self.root)
        # A temporary file may change directory mtime even after cleanup.
        with mock.patch.object(network.os, 'fsync', side_effect=OSError('stage failure')):
            with self.assertRaisesRegex(OSError, 'stage failure'):
                network.write_network_payload(
                    {'stops': []}, network_path=self.canonical,
                    backup_path=self.root / 'metro_network.last.json',
                    history_dir=self.history, max_history_snapshots=100,
                )
        after = snapshot(self.root)
        self.assertEqual(set(after), set(before))
        for name, state in before.items():
            if state[1] is not None:
                self.assertEqual(after[name], state)

    def test_atomic_replace_failure_leaves_canonical_file_intact(self) -> None:
        original = self.canonical.read_bytes()
        with mock.patch.object(Path, 'replace', side_effect=OSError('replace failure')):
            with self.assertRaisesRegex(OSError, 'replace failure'):
                network.write_network_payload(
                    {'stops': []}, network_path=self.canonical,
                    backup_path=self.root / 'metro_network.last.json',
                    history_dir=self.history, max_history_snapshots=100,
                )
        self.assertEqual(self.canonical.read_bytes(), original)
        self.assertFalse(list(self.root.rglob('*.tmp')))

    def test_priority_refresh_is_read_only_and_export_is_explicit(self) -> None:
        before = snapshot(self.root)
        self.child('''
from types import SimpleNamespace
from unittest.mock import Mock, patch
import legacy_core as base
import desktop_improvements as desktop
entries = [('P_A2', 'Finish station')]
viewer = SimpleNamespace(
    _priority_origin_key=lambda: 'P_A1', _route_graph_options=lambda: {},
    priority_summary_var=Mock(), _refresh_priority_filter_menu=Mock(),
    _refresh_priority_line_filter_menu=Mock(), _populate_priority_list=Mock(),
    _priority_filter_entries=lambda value: value,
)
with patch.object(base, '_priority_list_entries', return_value=entries):
    base.MetroMapViewer._refresh_priority_list(viewer)
    desktop._patched_refresh_priority_list(viewer)
    assert base.PRIORITY_LIST_CSV_PATH.read_text() == 'CSV sentinel\\n'
    viewer._refresh_priority_list = lambda: desktop._patched_refresh_priority_list(viewer)
    base.MetroMapViewer._export_priority_list_csv(viewer)
assert 'Beta' in base.PRIORITY_LIST_CSV_PATH.read_text()
''')
        after = snapshot(self.root)
        for name, state in before.items():
            if name != 'priority_list.csv':
                self.assertEqual(after[name], state)
        self.assertNotEqual(after['priority_list.csv'], before['priority_list.csv'])

    def test_cached_startup_status_does_not_initialize_worldgen(self) -> None:
        from scripts.run_isolated_tests import TEST_CONFIG
        config_path = self.root / 'worldgen_config.toml'
        config_path.write_text(TEST_CONFIG, encoding='utf-8')
        before = snapshot(self.root)
        self.child("""
from pathlib import Path
from unittest.mock import patch
import legacy_core as base
from worldgen.config import load_config
from worldgen.generator import BedrockWorldGenerator
config = load_config(Path('worldgen_config.toml'))
with patch('worldgen.config.load_config', return_value=config), patch.object(
    BedrockWorldGenerator, 'ensure_layout', side_effect=AssertionError('Read initialized worldgen'),
):
    status = base._world_map_cached_status_text()
assert 'World map cache' in status
assert 'unavailable' not in status
""")
        self.assertEqual(snapshot(self.root), before)

    def test_isolation_guard_rejects_host_access(self) -> None:
        # Exercise the guard in a child even when this test is run directly.
        self.child("""
import os
from pathlib import Path
from scripts.test_io_guard import install
os.environ['PLUMVILLE_TEST_SANDBOX'] = str(Path.cwd())
os.environ['PLUMVILLE_TEST_SOURCE_ROOT'] = str(Path.cwd().parent / 'host-source')
install()
for operation in (
    lambda: (Path.cwd().parent / 'host-source' / 'private.json').read_bytes(),
    lambda: (Path.cwd().parent / 'Application Support' / 'world.json').read_bytes(),
    lambda: (Path.cwd().parent / 'must-not-be-created').write_text('blocked'),
):
    try:
        operation()
    except PermissionError:
        pass
    else:
        raise AssertionError('Host access was allowed')
""")

    def test_terrain_preview_is_cached_in_memory_without_disk_output(self) -> None:
        self.child('''
from pathlib import Path
from queue import SimpleQueue
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image
import legacy_core as base
source = Path('source.png')
Image.new('RGBA', (12, 6), 'green').save(source)
preview = Path('absent-cache/preview.png')
stat = base._file_stat_key(source)
viewer = SimpleNamespace(
    world_map_preview_build_key=None, world_map_preview_queue=SimpleQueue(),
    _schedule_world_map_preview_poll=Mock(),
    _invalidate_world_map_render_cache=Mock(), redraw=Mock(),
    _world_map_preview_path_for=lambda *_: preview,
)
with patch.object(base, 'WORLD_MAP_PREVIEW_MAX_DIMENSION', 4), patch.object(base.threading, 'Thread') as thread:
    thread.side_effect = lambda **kw: SimpleNamespace(start=kw['target'])
    base.MetroMapViewer._ensure_world_map_preview_async(viewer, source, preview, stat)
    base.MetroMapViewer._poll_world_map_preview_queue(viewer)
    assert viewer._world_map_memory_preview[2].size == (4, 2)
    assert base.MetroMapViewer._world_map_display_image_path(viewer, source, preview) == (source, stat)
    viewer.redraw.assert_called_once()
assert not preview.parent.exists()
assert sorted(path.name for path in Path('.').glob('*.png')) == ['source.png']
''')
