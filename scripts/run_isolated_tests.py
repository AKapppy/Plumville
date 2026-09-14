"""Run checks in a disposable source/public-fixture copy, never private runtime.

Examples (run from the repository root):
    python3 scripts/run_isolated_tests.py
    python3 scripts/run_isolated_tests.py -- npm test
    python3 scripts/run_isolated_tests.py -- python3 -m unittest tests.test_core_network
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ('plumville', 'worldgen', 'tests', 'scripts', 'docs', 'tools')
SOURCE_SUFFIXES = {'.py', '.js', '.mjs', '.json', '.html', '.css', '.png', '.toml'}
TEST_CONFIG = '''[project]
name = "plumville-test"
compose_file = "docker-compose.worldgen.yml"
[world]
image = "test-only"
seed = "0"
level_name = "test-world"
eula = "FALSE"
port = 19132
startup_text = "test-ready"
startup_timeout_seconds = 1
stop_timeout_seconds = 1
[storage]
data_dir = "worldgen_data"
cache_dir = "worldgen_data/cache"
output_dir = "worldgen_output"
[render]
center_label = "Test"
center_x = 0
center_z = 0
radius = 16
sample_step = 1
'''


def copy_test_checkout(destination: Path) -> None:
    """Allowlist source/public assets; never copy config, history or ignored data."""
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=SOURCE_ROOT,
    ).decode().split('\0')
    files = []
    for name in names:
        if not name:
            continue
        relative = Path(name)
        if (
            len(relative.parts) == 1 and relative.suffix == '.py'
            or name in {'package.json', 'package-lock.json', 'docker-compose.worldgen.yml'}
            or relative.parts[0] in SOURCE_DIRS and relative.suffix in SOURCE_SUFFIXES
        ):
            files.append(SOURCE_ROOT / relative)
    for source in files:
        if source.is_symlink():
            raise ValueError(f'Test source must not be a symlink: {source.name}')
        target = destination / source.relative_to(SOURCE_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    # No personal world configuration, LAN address or discovered world path.
    (destination / 'worldgen_config.toml').write_text(TEST_CONFIG, encoding='utf-8')
    (destination / 'sitecustomize.py').write_text(
        'from scripts.test_io_guard import install\ninstall()\n', encoding='utf-8',
    )


def main() -> int:
    command = sys.argv[1:]
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']
    with tempfile.TemporaryDirectory(prefix='plumville-tests-') as temporary:
        root = Path(temporary).resolve()
        checkout = root / 'source'
        checkout.mkdir()
        copy_test_checkout(checkout)
        temp_dir = root / 'tmp'
        temp_dir.mkdir()
        env = dict(os.environ)
        env.update(
            PYTHONDONTWRITEBYTECODE='1',
            PYTHONPATH=str(checkout),
            PLUMVILLE_TEST_SANDBOX=str(root),
            PLUMVILLE_TEST_SOURCE_ROOT=str(SOURCE_ROOT),
            TMPDIR=str(temp_dir),
            npm_config_cache=str(root / 'npm-cache'),
        )
        print('Running in isolated source/public fixtures; private runtime excluded.', flush=True)
        return subprocess.run(command, cwd=checkout, env=env).returncode


if __name__ == '__main__':
    raise SystemExit(main())
