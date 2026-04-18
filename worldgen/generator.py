from __future__ import annotations

import errno
import json
import math
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .bedrock_chunks import iter_subchunk_records
from .cache import WorldCacheRecord, load_world_cache, save_world_cache, utc_now_iso
from .config import WorldgenConfig
from .docker_compose import ComposeError, build_compose_command, docker_available, run_compose
from .modes import DEFAULT_WORLDGEN_MODE, worldgen_mode
from .render import RenderPlan, RenderResult, build_render_plan, render_topdown_map, save_render_plan


BEDROCK_SERVICE_NAME = 'bedrock'
HEADLESS_LOADER_RESULT_FILE_NAME = 'headless_loader_result.json'
HEADLESS_LOADER_CHUNK_PACKET_FILE_NAME = 'headless_chunk_packets.jsonl'
HEADLESS_LOADER_RECENT_CHUNK_PACKET_FILE_NAME = 'headless_chunk_packets_recent.jsonl'
HEADLESS_LOADER_PROGRESS_FILE_NAME = 'headless_loader_progress.json'
HEADLESS_LOADER_MAX_ATTEMPTS = 3
HEADLESS_LOADER_RETRY_DELAY_SECONDS = 5
HEADLESS_LOADER_STARTUP_TIMEOUT_SECONDS = 300
HEADLESS_LOADER_STOP_GRACE_SECONDS = 10
HEADLESS_LOADER_STOP_COMMAND_TIMEOUT_SECONDS = 25
HEADLESS_LOADER_CONNECT_SETTLE_SECONDS = 4.0
HEADLESS_LOADER_FIRST_TELEPORT_DELAY_SECONDS = 1.0
HEADLESS_LOADER_SETTLE_AFTER_LAST_TELEPORT_SECONDS = 12.0
TELEPORT_TARGET_COVERAGE_THRESHOLD = 0.85
TELEPORT_TARGET_PLANNER_VERSION = 'blank-pixel-radial-tangent-v1'
CHUNK_TOUCH_BLOCK = 'bedrock'
CHUNK_TOUCH_Y = -64
CHUNK_TOUCH_MAX_BLOCKS = 30_000
TARGET_LOAD_MIN_X = -8000
TARGET_LOAD_MAX_X = 8000
TARGET_LOAD_MIN_Z = -6000
TARGET_LOAD_MAX_Z = 6000
BEDROCK_NATIVE_CRASH_MARKERS = (
    'free(): invalid next size',
)


@dataclass(frozen=True, slots=True)
class GeneratorStatus:
    docker_available: bool
    service_running: bool | None
    cached_world_path: Path | None
    cached_world_exists: bool
    expected_world_path: Path
    expected_world_exists: bool
    render_plan_path: Path
    render_image_path: Path
    render_image_exists: bool
    docs_render_image_path: Path
    docs_render_image_exists: bool
    render_cache_path: Path
    render_cache_exists: bool


@dataclass(frozen=True, slots=True)
class HeadlessChunkLoadResult:
    world_path: Path
    result_path: Path
    returncode: int
    chunks_received: int
    unique_chunk_columns: int
    load_attempts: int
    teleport_commands_sent: int
    teleport_target_count: int
    teleport_next_index: int
    teleport_targets: tuple[str, ...]
    server_stopped: bool
    output: str


@dataclass(frozen=True, slots=True)
class WorldgenModePaths:
    mode_key: str
    render_plan_path: Path
    render_cache_path: Path
    render_image_path: Path
    docs_render_image_path: Path
    headless_result_path: Path
    headless_chunk_packet_path: Path
    headless_start_game_path: Path
    headless_progress_path: Path


@dataclass(frozen=True, slots=True)
class HeadlessLoaderTargetPreview:
    target_x: int
    target_z: int
    target_index: int
    target_count: int
    min_x: int
    max_x: int
    min_z: int
    max_z: int
    coverage: float | None


@dataclass(frozen=True, slots=True)
class LevelDbRepairResult:
    db_path: Path
    repaired_copy_path: Path
    backup_path: Path


@dataclass(frozen=True, slots=True)
class _HeadlessChunkLoadAttempt:
    world_path: Path
    returncode: int
    chunks_received: int
    unique_chunk_columns: int
    teleport_commands_sent: int
    target_squares_completed: int
    teleport_targets: tuple[str, ...]
    fatal_server_crash: bool
    output: str


@dataclass(frozen=True, slots=True)
class _BlankRenderCoverage:
    image_path: Path
    image_stat: tuple[str, int, int]
    blank_pixels_by_chunk: dict[tuple[int, int], int]
    blank_pixel_count: int
    total_pixels: int


class BedrockWorldGenerator:
    def __init__(self, config: WorldgenConfig):
        self.config = config
        self.paths = config.paths

    def paths_for_mode(self, mode_key: str | None = None) -> WorldgenModePaths:
        mode = worldgen_mode(mode_key)
        if mode.key == DEFAULT_WORLDGEN_MODE:
            return WorldgenModePaths(
                mode_key=mode.key,
                render_plan_path=self.paths.render_plan_path,
                render_cache_path=self.paths.render_cache_path,
                render_image_path=self.paths.render_image_path,
                docs_render_image_path=self.paths.docs_render_image_path,
                headless_result_path=self.paths.cache_dir / HEADLESS_LOADER_RESULT_FILE_NAME,
                headless_chunk_packet_path=(
                    self.paths.cache_dir / HEADLESS_LOADER_RECENT_CHUNK_PACKET_FILE_NAME
                ),
                headless_start_game_path=self.paths.cache_dir / 'headless_start_game.json',
                headless_progress_path=self.paths.cache_dir / HEADLESS_LOADER_PROGRESS_FILE_NAME,
            )

        render_stem = f'blackport_{mode.key}'
        return WorldgenModePaths(
            mode_key=mode.key,
            render_plan_path=self.paths.cache_dir / f'render_plan_{mode.key}.json',
            render_cache_path=self.paths.cache_dir / f'render_cache_{mode.key}.json',
            render_image_path=self.paths.output_dir / f'{render_stem}.png',
            docs_render_image_path=self.paths.docs_assets_dir / f'{render_stem}.png',
            headless_result_path=self.paths.cache_dir / 'lan_headless_loader_result.json',
            headless_chunk_packet_path=self.paths.cache_dir / 'lan_headless_chunk_packets.jsonl',
            headless_start_game_path=self.paths.cache_dir / 'lan_headless_start_game.json',
            headless_progress_path=self.paths.cache_dir / 'lan_headless_loader_progress.json',
        )

    def ensure_layout(self) -> None:
        self.paths.ensure_runtime_dirs()
        if not self.config.compose_path.exists():
            raise FileNotFoundError(f'Compose file not found: {self.config.compose_path}')
        self.write_env_file()

    def write_env_file(self) -> Path:
        self.paths.ensure_runtime_dirs()
        env_lines = [
            f'BEDROCK_IMAGE={self.config.world.image}',
            f'BEDROCK_SERVER_VERSION={self.config.world.server_version}',
            f'BEDROCK_DIRECT_DOWNLOAD_URL={self.config.world.direct_download_url}',
            f'BEDROCK_EULA={self.config.world.eula}',
            f'BEDROCK_LEVEL_NAME={self.config.world.level_name}',
            f'BEDROCK_LEVEL_SEED={self.config.world.seed}',
            f'BEDROCK_PORT={self.config.world.port}',
            f'BEDROCK_DATA_DIR={self.paths.data_dir}',
            f'BEDROCK_ONLINE_MODE={self.config.world.online_mode}',
            f'BEDROCK_ALLOW_CHEATS={self.config.world.allow_cheats}',
            f'BEDROCK_GAMEMODE={self.config.world.gamemode}',
            (
                'BEDROCK_DEFAULT_PLAYER_PERMISSION_LEVEL='
                f'{self.config.world.default_player_permission_level}'
            ),
            f'BEDROCK_VIEW_DISTANCE={self.config.world.view_distance}',
            f'BEDROCK_TICK_DISTANCE={self.config.world.tick_distance}',
            f'BEDROCK_PLAYER_IDLE_TIMEOUT={self.config.world.player_idle_timeout}',
            f'BEDROCK_LOADER_USERNAME={self.config.headless_loader.username}',
            f'BEDROCK_LOADER_CLIENT_VERSION={self.config.headless_loader.client_version}',
            f'BEDROCK_LOADER_RAKNET_BACKEND={self.config.headless_loader.raknet_backend}',
            f'BEDROCK_LOADER_WAIT_MS={self.config.headless_loader.wait_seconds * 1000}',
            f'BEDROCK_LOADER_CHUNK_RADIUS={self.config.headless_loader.chunk_radius}',
            'BEDROCK_LOADER_RESULT_FILE=/app/worldgen_data/cache/headless_loader_result.json',
        ]
        self.paths.env_file.write_text('\n'.join(env_lines) + '\n', encoding='utf-8')
        return self.paths.env_file

    def start(self) -> None:
        self.ensure_layout()
        run_compose(
            project_name=self.config.project_name,
            compose_path=self.config.compose_path,
            env_file=self.paths.env_file,
            args=['up', '-d', BEDROCK_SERVICE_NAME],
        )

    def wait_until_ready(
        self,
        timeout_seconds: int | None = None,
        poll_seconds: float = 2.0,
        *,
        since: str | None = None,
    ) -> Path:
        self.ensure_layout()
        timeout = timeout_seconds or self.config.world.startup_timeout_seconds
        deadline = time.monotonic() + timeout
        last_output = ''
        while time.monotonic() < deadline:
            logs_output = self.logs(since=since)
            last_output = logs_output or last_output
            world_path = self.locate_world_folder(require_exists=False)
            if self.config.world.startup_text in logs_output and world_path.exists():
                self.write_cache(world_path)
                self.write_render_plan(world_path)
                return world_path
            if logs_output and not self.is_service_running():
                tail = _tail_lines(logs_output, 25)
                hint = _bedrock_startup_failure_hint(tail)
                raise RuntimeError(
                    'Bedrock server exited before startup completed.\n'
                    f'Last logs:\n{tail}'
                    f'{hint}'
                )
            time.sleep(poll_seconds)

        tail = _tail_lines(last_output, 25)
        raise TimeoutError(
            f'Bedrock startup did not reach "{self.config.world.startup_text}" within {timeout} seconds.\n'
            f'Last logs:\n{tail}'
        )

    def stop(
        self,
        *,
        grace_seconds: int | None = None,
        command_timeout_seconds: int | None = None,
    ) -> None:
        self.ensure_layout()
        grace = grace_seconds or self.config.world.stop_timeout_seconds
        timeout = command_timeout_seconds or (grace + 15)
        result = run_compose(
            project_name=self.config.project_name,
            compose_path=self.config.compose_path,
            env_file=self.paths.env_file,
            args=['stop', '--timeout', str(grace), BEDROCK_SERVICE_NAME],
            check=False,
            timeout_seconds=timeout,
        )
        if result.returncode == -124:
            run_compose(
                project_name=self.config.project_name,
                compose_path=self.config.compose_path,
                env_file=self.paths.env_file,
                args=['kill', BEDROCK_SERVICE_NAME],
                check=False,
                timeout_seconds=20,
            )

    def logs(self, *, since: str | None = None) -> str:
        self.ensure_layout()
        args = ['logs', '--no-color']
        if since is not None:
            args.extend(('--since', since))
        args.append(BEDROCK_SERVICE_NAME)
        result = run_compose(
            project_name=self.config.project_name,
            compose_path=self.config.compose_path,
            env_file=self.paths.env_file,
            args=args,
            check=False,
            timeout_seconds=20,
        )
        return result.combined_output

    def send_command(self, command: str, *, check: bool = True) -> str:
        self.ensure_layout()
        result = run_compose(
            project_name=self.config.project_name,
            compose_path=self.config.compose_path,
            env_file=self.paths.env_file,
            args=['exec', '-T', BEDROCK_SERVICE_NAME, 'send-command', command],
            check=check,
            timeout_seconds=20,
        )
        return result.combined_output

    def is_service_running(self) -> bool | None:
        self.ensure_layout()
        try:
            result = run_compose(
                project_name=self.config.project_name,
                compose_path=self.config.compose_path,
                env_file=self.paths.env_file,
                args=['ps', '--services', '--status', 'running'],
                check=False,
                timeout_seconds=10,
            )
        except ComposeError:
            return None
        if result.returncode != 0:
            return None
        services = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        return BEDROCK_SERVICE_NAME in services

    def locate_world_folder(self, require_exists: bool = True) -> Path:
        direct_path = self.paths.data_dir / 'worlds' / self.config.world.level_name
        if direct_path.exists() or not require_exists:
            return direct_path

        worlds_dir = self.paths.data_dir / 'worlds'
        if worlds_dir.exists():
            subdirs = [path for path in worlds_dir.iterdir() if path.is_dir()]
            if len(subdirs) == 1:
                return subdirs[0]
        raise FileNotFoundError(f'World folder not found under {worlds_dir}')

    def write_cache(self, world_path: Path) -> Path:
        record = WorldCacheRecord(
            project_name=self.config.project_name,
            image=self.config.world.image,
            seed=self.config.world.seed,
            level_name=self.config.world.level_name,
            world_path=str(world_path.resolve()),
            data_dir=str(self.paths.data_dir.resolve()),
            prepared_at=utc_now_iso(),
            render_center_label=self.config.render.center_label,
            render_center_x=self.config.render.center_x,
            render_center_z=self.config.render.center_z,
            render_radius=self.config.render.radius,
            render_sample_step=self.config.render.sample_step,
        )
        save_world_cache(self.paths.world_cache_path, record)
        return self.paths.world_cache_path

    def write_render_plan(self, world_path: Path | None = None) -> Path:
        if world_path is None:
            try:
                world_path = self.locate_world_folder(require_exists=True)
            except FileNotFoundError:
                cache_record = load_world_cache(self.paths.world_cache_path)
                if cache_record:
                    cached_world_path = Path(cache_record.world_path)
                    if cached_world_path.exists():
                        world_path = cached_world_path
        plan = build_render_plan(self.config, world_path)
        save_render_plan(self.paths.render_plan_path, plan)
        return self.paths.render_plan_path

    def prepare(self, *, startup_timeout_seconds: int | None = None) -> tuple[Path, Path]:
        service_was_running = self.is_service_running()
        started_at = None if service_was_running else utc_now_iso()
        self.start()
        world_path = self.wait_until_ready(timeout_seconds=startup_timeout_seconds, since=started_at)
        return (world_path, self.paths.render_plan_path)

    def load_chunks_headless(
        self,
        *,
        wait_seconds: int | None = None,
        stop_after: bool = True,
        restart_existing: bool = True,
    ) -> HeadlessChunkLoadResult:
        loader_config = self.config.headless_loader
        effective_wait_seconds = wait_seconds or loader_config.wait_seconds
        result_path = self.paths.cache_dir / HEADLESS_LOADER_RESULT_FILE_NAME
        chunk_packet_path = self.paths.cache_dir / HEADLESS_LOADER_RECENT_CHUNK_PACKET_FILE_NAME
        progress_path = self.paths.cache_dir / HEADLESS_LOADER_PROGRESS_FILE_NAME
        coverage_world_path = self._world_folder_for_coverage_scan()
        blank_coverage = _load_blank_render_coverage(self.config, self.paths.render_image_path)
        teleport_points = _render_area_teleport_points(
            self.config,
            world_path=coverage_world_path,
            blank_coverage=blank_coverage,
        )
        if not teleport_points:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            output = (
                'Rendered map already has no blank pixels.'
                if blank_coverage is not None and blank_coverage.blank_pixel_count == 0
                else 'Render area already has no blank chunk columns.'
            )
            return HeadlessChunkLoadResult(
                world_path=coverage_world_path or self.locate_world_folder(require_exists=False),
                result_path=result_path,
                returncode=0,
                chunks_received=0,
                unique_chunk_columns=0,
                load_attempts=0,
                teleport_commands_sent=0,
                teleport_target_count=0,
                teleport_next_index=0,
                teleport_targets=(),
                server_stopped=False,
                output=output,
            )
        planner_context = _teleport_planner_context(blank_coverage)
        teleport_start_index = _load_headless_loader_progress(
            progress_path,
            config=self.config,
            teleport_points=teleport_points,
            planner_context=planner_context,
        )
        teleport_start_index = _next_undercovered_teleport_index(
            self.config,
            teleport_points,
            start_index=teleport_start_index,
            world_path=coverage_world_path,
            blank_coverage=blank_coverage,
        )
        current_teleport_index = teleport_start_index
        result_path.parent.mkdir(parents=True, exist_ok=True)
        if chunk_packet_path.exists():
            chunk_packet_path.unlink()
        container_result_path = _container_repo_path(self.config.repo_root, result_path)
        container_chunk_packet_path = _container_repo_path(self.config.repo_root, chunk_packet_path)
        container_start_game_path = _container_repo_path(
            self.config.repo_root,
            self.paths.cache_dir / 'headless_start_game.json',
        )

        attempts: list[_HeadlessChunkLoadAttempt] = []
        for attempt_number in range(1, HEADLESS_LOADER_MAX_ATTEMPTS + 1):
            if restart_existing and self.is_service_running():
                self.stop(
                    grace_seconds=HEADLESS_LOADER_STOP_GRACE_SECONDS,
                    command_timeout_seconds=HEADLESS_LOADER_STOP_COMMAND_TIMEOUT_SECONDS,
                )
                time.sleep(2)

            self._prepare_db_for_headless_loader()
            attempt = self._load_chunks_headless_once(
                wait_seconds=effective_wait_seconds,
                result_path=result_path,
                container_result_path=container_result_path,
                container_chunk_packet_path=container_chunk_packet_path,
                container_start_game_path=container_start_game_path,
                teleport_points=teleport_points,
                teleport_start_index=current_teleport_index,
                blank_coverage=blank_coverage,
                loader_username=_headless_loader_username(attempt_number),
            )
            attempts.append(attempt)

            if attempt.chunks_received > 0:
                current_teleport_index = _advance_teleport_index(
                    current_teleport_index,
                    attempt.target_squares_completed,
                    len(teleport_points),
                )
                break
            if attempt_number < HEADLESS_LOADER_MAX_ATTEMPTS:
                if attempt.fatal_server_crash or not self.is_service_running():
                    self.stop(
                        grace_seconds=HEADLESS_LOADER_STOP_GRACE_SECONDS,
                        command_timeout_seconds=HEADLESS_LOADER_STOP_COMMAND_TIMEOUT_SECONDS,
                    )
                time.sleep(HEADLESS_LOADER_RETRY_DELAY_SECONDS)

        last_attempt = attempts[-1]
        teleport_next_index = current_teleport_index
        _save_headless_loader_progress(
            progress_path,
            config=self.config,
            teleport_points=teleport_points,
            next_index=teleport_next_index,
            planner_context=planner_context,
        )

        server_stopped = False
        if stop_after:
            time.sleep(2)
            self.stop(
                grace_seconds=HEADLESS_LOADER_STOP_GRACE_SECONDS,
                command_timeout_seconds=HEADLESS_LOADER_STOP_COMMAND_TIMEOUT_SECONDS,
            )
            server_stopped = True

        return HeadlessChunkLoadResult(
            world_path=last_attempt.world_path,
            result_path=result_path,
            returncode=0 if last_attempt.chunks_received > 0 else last_attempt.returncode,
            chunks_received=last_attempt.chunks_received,
            unique_chunk_columns=last_attempt.unique_chunk_columns,
            load_attempts=len(attempts),
            teleport_commands_sent=sum(attempt.teleport_commands_sent for attempt in attempts),
            teleport_target_count=len(teleport_points),
            teleport_next_index=teleport_next_index,
            teleport_targets=tuple(
                target
                for attempt in attempts
                for target in attempt.teleport_targets
            ),
            server_stopped=server_stopped,
            output=_format_loader_attempt_outputs(attempts),
        )

    def load_lan_chunks_headless(
        self,
        mode_key: str,
        *,
        wait_seconds: int | None = None,
    ) -> HeadlessChunkLoadResult:
        mode = worldgen_mode(mode_key)
        if not mode.is_lan:
            return self.load_chunks_headless(wait_seconds=wait_seconds)
        if not self.config.lan.enabled:
            raise RuntimeError(
                'LAN world map loading is disabled. Set [lan] enabled = true in '
                'worldgen_config.toml after confirming the host and port.'
            )

        self.ensure_layout()
        lan_config = self.config.lan
        mode_paths = self.paths_for_mode(mode.key)
        result_path = mode_paths.headless_result_path
        chunk_packet_path = mode_paths.headless_chunk_packet_path
        start_game_path = mode_paths.headless_start_game_path
        result_path.parent.mkdir(parents=True, exist_ok=True)
        if result_path.exists():
            result_path.unlink()

        container_result_path = _container_repo_path(self.config.repo_root, result_path)
        container_chunk_packet_path = _container_repo_path(self.config.repo_root, chunk_packet_path)
        container_start_game_path = _container_repo_path(self.config.repo_root, start_game_path)
        effective_wait_seconds = wait_seconds or lan_config.wait_seconds

        command = build_compose_command(
            project_name=self.config.project_name,
            compose_path=self.config.compose_path,
            env_file=self.paths.env_file,
            args=[
                'run',
                '--rm',
                '--no-deps',
                '-e',
                f'BEDROCK_HOST={lan_config.host}',
                '-e',
                f'BEDROCK_PORT={lan_config.port}',
                '-e',
                f'BEDROCK_USERNAME={lan_config.username}',
                '-e',
                f'BEDROCK_VERSION={lan_config.client_version}',
                '-e',
                f'BEDROCK_RAKNET_BACKEND={lan_config.raknet_backend}',
                '-e',
                f'BEDROCK_CONNECT_TIMEOUT_MS={lan_config.connect_timeout_ms}',
                '-e',
                f'BEDROCK_WAIT_MS={effective_wait_seconds * 1000}',
                '-e',
                f'BEDROCK_CHUNK_RADIUS={lan_config.chunk_radius}',
                '-e',
                f'BEDROCK_LOADER_RESULT_FILE={container_result_path}',
                '-e',
                f'BEDROCK_CHUNK_PACKET_FILE={container_chunk_packet_path}',
                '-e',
                f'BEDROCK_START_GAME_METADATA_FILE={container_start_game_path}',
                'chunk-loader',
            ],
        )
        result = subprocess.run(
            command,
            cwd=str(self.config.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=effective_wait_seconds + 240,
        )
        loader_payload = _load_loader_result_payload(result_path)
        chunks_received = _payload_int(loader_payload, 'chunks_received')
        unique_chunk_columns = _payload_int(loader_payload, 'unique_chunk_columns')
        return HeadlessChunkLoadResult(
            world_path=chunk_packet_path,
            result_path=result_path,
            returncode=result.returncode,
            chunks_received=chunks_received,
            unique_chunk_columns=unique_chunk_columns,
            load_attempts=1,
            teleport_commands_sent=0,
            teleport_target_count=0,
            teleport_next_index=0,
            teleport_targets=(),
            server_stopped=False,
            output=(result.stdout or '').strip(),
        )

    def _load_chunks_headless_once(
        self,
        *,
        wait_seconds: int,
        result_path: Path,
        container_result_path: str,
        container_chunk_packet_path: str,
        container_start_game_path: str,
        teleport_points: tuple[tuple[int, int], ...],
        teleport_start_index: int,
        blank_coverage: _BlankRenderCoverage | None,
        loader_username: str,
    ) -> _HeadlessChunkLoadAttempt:
        attempt_started_at = utc_now_iso()
        world_path, _render_plan_path = self.prepare(
            startup_timeout_seconds=HEADLESS_LOADER_STARTUP_TIMEOUT_SECONDS
        )
        loader_config = self.config.headless_loader
        if result_path.exists():
            result_path.unlink()

        server_command_outputs: list[str] = []
        for server_command in (
            'gamerule spawnRadius 0',
            (
                f'setworldspawn {self.config.render.center_x} '
                f'{loader_config.teleport_y} {self.config.render.center_z}'
            ),
        ):
            server_command_outputs.append(
                _format_server_command_output(
                    server_command,
                    self.send_command(server_command, check=False),
                )
            )

        time.sleep(HEADLESS_LOADER_CONNECT_SETTLE_SECONDS)

        command = build_compose_command(
            project_name=self.config.project_name,
            compose_path=self.config.compose_path,
            env_file=self.paths.env_file,
            args=[
                'run',
                '--rm',
                '-e',
                f'BEDROCK_USERNAME={loader_username}',
                '-e',
                f'BEDROCK_WAIT_MS={wait_seconds * 1000}',
                '-e',
                f'BEDROCK_LOADER_RESULT_FILE={container_result_path}',
                '-e',
                f'BEDROCK_CHUNK_PACKET_FILE={container_chunk_packet_path}',
                '-e',
                f'BEDROCK_START_GAME_METADATA_FILE={container_start_game_path}',
                'chunk-loader',
            ],
        )
        process = subprocess.Popen(
            command,
            cwd=str(self.config.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        output_lines: list[str] = []

        def read_process_output() -> None:
            if process.stdout is None:
                return
            for line in process.stdout:
                output_lines.append(line.rstrip())

        output_thread = threading.Thread(target=read_process_output, daemon=True)
        output_thread.start()

        teleport_commands_sent = 0
        target_squares_started = 0
        target_squares_completed = 0
        teleport_targets: list[tuple[int, int]] = []
        active_target: tuple[int, int] | None = None
        active_loader_points: list[tuple[int, int]] = []
        touched_targets: set[tuple[int, int]] = set()
        simulated_saved_columns = _existing_columns_for_touch_fill(
            self.config,
            world_path,
            blank_coverage=blank_coverage,
        )
        per_target_teleport_count = len(_target_square_loader_points(self.config, teleport_points[0]))
        target_squares_to_load = max(
            1,
            loader_config.teleport_attempts // max(1, per_target_teleport_count),
        )
        teleport_command_budget = target_squares_to_load * per_target_teleport_count
        last_teleport_sent_at: float | None = None
        kicked_after_target_batch = False
        next_teleport_at = time.monotonic() + min(
            loader_config.teleport_delay_seconds,
            HEADLESS_LOADER_FIRST_TELEPORT_DELAY_SECONDS,
        )
        hard_deadline = (
            time.monotonic()
            + wait_seconds
            + loader_config.teleport_delay_seconds
            + (loader_config.teleport_retry_seconds * teleport_command_budget)
            + 240
        )

        while process.poll() is None:
            now = time.monotonic()
            if now > hard_deadline:
                process.kill()
                server_command_outputs.append('Killed headless loader after it exceeded its hard timeout.')
                break
            if (
                teleport_commands_sent < teleport_command_budget
                and _headless_loader_ready_for_teleport(output_lines)
                and now >= next_teleport_at
            ):
                if not active_loader_points:
                    if target_squares_started >= target_squares_to_load:
                        next_teleport_at = now + 0.25
                        time.sleep(0.25)
                        continue
                    active_target = teleport_points[
                        (teleport_start_index + target_squares_started) % len(teleport_points)
                    ]
                    target_squares_started += 1
                    teleport_targets.append(active_target)
                    active_loader_points = list(_target_square_loader_points(self.config, active_target))
                target_x, target_z = active_loader_points.pop(0)
                teleport_command = (
                    f'tp {loader_username} '
                    f'{target_x} {loader_config.teleport_y} {target_z}'
                )
                command_output = self.send_command(teleport_command, check=False)
                server_command_outputs.append(
                    _format_server_command_output(teleport_command, command_output)
                )
                if active_target is not None and active_target not in touched_targets:
                    touched_targets.add(active_target)
                    target_columns = _teleport_point_chunk_columns(
                        self.config,
                        active_target,
                    )
                    touch_commands = _chunk_touch_fill_commands(
                        self.config,
                        active_target,
                        existing_columns=simulated_saved_columns,
                    )
                    for touch_command in touch_commands:
                        self.send_command(touch_command, check=False)
                    simulated_saved_columns.update(target_columns)
                    server_command_outputs.append(
                        (
                            f'$ touch loaded chunks under {active_target[0]},{active_target[1]}\n'
                            f'{len(touch_commands)} blank-space bottom fill commands at y={CHUNK_TOUCH_Y}'
                        )
                    )
                teleport_commands_sent += 1
                if not active_loader_points:
                    target_squares_completed += 1
                    active_target = None
                last_teleport_sent_at = now
                next_teleport_at = now + loader_config.teleport_retry_seconds
            if (
                not kicked_after_target_batch
                and target_squares_completed >= target_squares_to_load
                and last_teleport_sent_at is not None
                and _headless_loader_has_chunks(output_lines)
                and now >= last_teleport_sent_at + HEADLESS_LOADER_SETTLE_AFTER_LAST_TELEPORT_SECONDS
            ):
                kick_command = f'kick {loader_username} Auto fill target batch complete'
                server_command_outputs.append(
                    _format_server_command_output(
                        kick_command,
                        self.send_command(kick_command, check=False),
                    )
                )
                kicked_after_target_batch = True
            time.sleep(0.25)

        returncode = process.wait()
        output_thread.join(timeout=2)

        loader_payload = _load_loader_result_payload(result_path)
        chunks_received = _payload_int(loader_payload, 'chunks_received')
        unique_chunk_columns = _payload_int(loader_payload, 'unique_chunk_columns')
        output = '\n'.join(line for line in output_lines if line).strip()
        if server_command_outputs:
            command_output = '\n'.join(server_command_outputs).strip()
            output = f'{output}\n\nServer commands:\n{command_output}'.strip()
        server_log_output = self.logs(since=attempt_started_at)
        fatal_server_crash = _bedrock_server_crashed(server_log_output)
        if fatal_server_crash:
            server_tail = _tail_lines(server_log_output, 20)
            crash_note = (
                'Bedrock server crashed while the headless loader was connecting.\n'
                f'Server logs:\n{server_tail}'
            )
            output = f'{output}\n\n{crash_note}'.strip()

        return _HeadlessChunkLoadAttempt(
            world_path=world_path,
            returncode=returncode,
            chunks_received=chunks_received,
            unique_chunk_columns=unique_chunk_columns,
            teleport_commands_sent=teleport_commands_sent,
            target_squares_completed=target_squares_completed,
            teleport_targets=tuple(
                f'{target_x},{target_z}' for target_x, target_z in teleport_targets
            ),
            fatal_server_crash=fatal_server_crash,
            output=output,
        )

    def render_map(
        self,
        *,
        diagnose_unknown_blocks: bool = False,
        prefer_persistent_bedrock: bool = False,
        mode_key: str | None = None,
    ) -> RenderResult:
        mode = worldgen_mode(mode_key)
        if mode.is_lan:
            return self.render_lan_map(mode.key)

        self.paths.ensure_runtime_dirs()
        world_path = self._resolve_existing_world_folder()
        self.write_render_plan(world_path)
        result = render_topdown_map(
            self.config,
            world_path,
            image_path=self.paths.render_image_path,
            metadata_path=self.paths.render_cache_path,
            diagnose_unknown_blocks=diagnose_unknown_blocks,
            prefer_persistent_bedrock=prefer_persistent_bedrock,
            packet_cache_paths=(
                self.paths.cache_dir / HEADLESS_LOADER_CHUNK_PACKET_FILE_NAME,
                self.paths.cache_dir / HEADLESS_LOADER_RECENT_CHUNK_PACKET_FILE_NAME,
            ),
            preserve_existing_image=True,
        )
        shutil.copy2(self.paths.render_image_path, self.paths.docs_render_image_path)
        return result

    def render_lan_map(self, mode_key: str) -> RenderResult:
        mode = worldgen_mode(mode_key)
        if not mode.is_lan:
            return self.render_map()

        self.paths.ensure_runtime_dirs()
        mode_paths = self.paths_for_mode(mode.key)
        plan = build_render_plan(self.config, None)
        save_render_plan(mode_paths.render_plan_path, plan)
        result = render_topdown_map(
            self.config,
            None,
            image_path=mode_paths.render_image_path,
            metadata_path=mode_paths.render_cache_path,
            packet_cache_path=mode_paths.headless_chunk_packet_path,
            read_persistent_bedrock=False,
            fixed_y=mode.fixed_y,
        )
        shutil.copy2(mode_paths.render_image_path, mode_paths.docs_render_image_path)
        return result

    def _prepare_db_for_headless_loader(self) -> None:
        return

    def repair_world_db(self) -> LevelDbRepairResult:
        if self.is_service_running():
            raise RuntimeError('Stop the Bedrock worldgen container before repairing the LevelDB folder.')

        try:
            import plyvel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                'Repairing Bedrock LevelDB data requires `plyvel`. Install it with '
                '`python3 -m pip install plyvel`.'
            ) from exc

        world_path = self._resolve_existing_world_folder()
        db_path = world_path / 'db'
        if not db_path.exists():
            raise FileNotFoundError(f'Bedrock LevelDB folder not found: {db_path}')

        timestamp = utc_now_iso().replace(":", "").replace("+", "_")
        backup_path = (
            self.paths.cache_dir
            / 'leveldb_backups'
            / f'db_{timestamp}'
        )
        repaired_copy_path = (
            self.paths.cache_dir
            / 'leveldb_repaired_copies'
            / f'db_{timestamp}'
        )
        shutil.copytree(db_path, backup_path)
        shutil.copytree(db_path, repaired_copy_path)
        plyvel.repair_db(str(repaired_copy_path))
        return LevelDbRepairResult(
            db_path=db_path,
            repaired_copy_path=repaired_copy_path,
            backup_path=backup_path,
        )

    def status(self) -> GeneratorStatus:
        cache_record = load_world_cache(self.paths.world_cache_path)
        cached_world_path = Path(cache_record.world_path) if cache_record else None
        expected_world_path = self.locate_world_folder(require_exists=False)
        return GeneratorStatus(
            docker_available=docker_available(),
            service_running=self.is_service_running(),
            cached_world_path=cached_world_path,
            cached_world_exists=bool(cached_world_path and cached_world_path.exists()),
            expected_world_path=expected_world_path,
            expected_world_exists=expected_world_path.exists(),
            render_plan_path=self.paths.render_plan_path,
            render_image_path=self.paths.render_image_path,
            render_image_exists=self.paths.render_image_path.exists(),
            docs_render_image_path=self.paths.docs_render_image_path,
            docs_render_image_exists=self.paths.docs_render_image_path.exists(),
            render_cache_path=self.paths.render_cache_path,
            render_cache_exists=self.paths.render_cache_path.exists(),
        )

    def load_render_plan(self) -> RenderPlan:
        world_path = None
        try:
            world_path = self.locate_world_folder(require_exists=True)
        except FileNotFoundError:
            pass
        return build_render_plan(self.config, world_path)

    def _resolve_existing_world_folder(self) -> Path:
        try:
            return self.locate_world_folder(require_exists=True)
        except FileNotFoundError:
            cache_record = load_world_cache(self.paths.world_cache_path)
            if cache_record:
                cached_world_path = Path(cache_record.world_path)
                if cached_world_path.exists():
                    return cached_world_path
            raise

    def _world_folder_for_coverage_scan(self) -> Path | None:
        try:
            return self._resolve_existing_world_folder()
        except FileNotFoundError:
            return None

    def next_headless_loader_target_preview(self) -> HeadlessLoaderTargetPreview | None:
        progress_path = self.paths.cache_dir / HEADLESS_LOADER_PROGRESS_FILE_NAME
        world_path = self._world_folder_for_coverage_scan()
        blank_coverage = _load_blank_render_coverage(self.config, self.paths.render_image_path)
        teleport_points = _render_area_teleport_points(
            self.config,
            world_path=world_path,
            blank_coverage=blank_coverage,
        )
        if not teleport_points:
            return None
        progress_index = _load_headless_loader_progress(
            progress_path,
            config=self.config,
            teleport_points=teleport_points,
            planner_context=_teleport_planner_context(blank_coverage),
        )
        target_index = _next_undercovered_teleport_index(
            self.config,
            teleport_points,
            start_index=progress_index,
            world_path=world_path,
            blank_coverage=blank_coverage,
        )
        target = teleport_points[target_index]
        coverage = None
        if blank_coverage is not None:
            coverage = _teleport_point_pixel_coverage(self.config, target, blank_coverage)
        elif world_path is not None and world_path.exists():
            saved_columns = _saved_render_chunk_columns(self.config, world_path)
            coverage = _teleport_point_chunk_coverage(self.config, target, saved_columns)
        min_x, max_x, min_z, max_z = _teleport_target_world_bounds(self.config, target)
        return HeadlessLoaderTargetPreview(
            target_x=target[0],
            target_z=target[1],
            target_index=target_index,
            target_count=len(teleport_points),
            min_x=min_x,
            max_x=max_x,
            min_z=min_z,
            max_z=max_z,
            coverage=coverage,
        )

    def render_area_coverage_complete(self) -> bool:
        blank_coverage = _load_blank_render_coverage(self.config, self.paths.render_image_path)
        if blank_coverage is not None:
            return blank_coverage.blank_pixel_count == 0

        world_path = self._world_folder_for_coverage_scan()
        if world_path is None or not world_path.exists():
            return False

        saved_columns = _saved_render_chunk_columns(self.config, world_path)
        if not saved_columns:
            return False

        return not _missing_render_chunk_columns(self.config, saved_columns)


def _tail_lines(text: str, limit: int) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return '\n'.join(lines[-limit:]) if lines else '(no logs captured)'


def _bedrock_server_crashed(logs_output: str) -> bool:
    return any(marker in logs_output for marker in BEDROCK_NATIVE_CRASH_MARKERS)


def _bedrock_startup_failure_hint(logs_tail: str) -> str:
    lowered = logs_tail.lower()
    if 'resource deadlock avoided' in lowered:
        return (
            '\n\nHint: Docker hit a filesystem deadlock while reading or writing '
            'Bedrock server files. Keep [storage] data_dir outside iCloud Drive or '
            'other cloud-synced folders, then start worldgen again.'
        )
    if 'failed to lookup bedrock version and download url' not in lowered:
        return ''
    return (
        '\n\nHint: the Bedrock Docker image could not resolve a download link for '
        'the configured VERSION. Set [world] direct_download_url in '
        'worldgen_config.toml to a known-good bedrock-server zip URL, or use '
        'server_version = "LATEST" if matching the headless protocol is not needed.'
    )



def _advance_teleport_index(current_index: int, teleports_used: int, target_count: int) -> int:
    if target_count <= 0:
        return 0
    return (current_index + max(0, teleports_used)) % target_count


def _next_undercovered_teleport_index(
    config: WorldgenConfig,
    teleport_points: tuple[tuple[int, int], ...],
    *,
    start_index: int,
    world_path: Path | None,
    blank_coverage: _BlankRenderCoverage | None = None,
) -> int:
    if not teleport_points:
        return 0

    normalized_start_index = start_index % len(teleport_points)
    if blank_coverage is not None:
        for offset in range(len(teleport_points)):
            index = (normalized_start_index + offset) % len(teleport_points)
            point = teleport_points[index]
            if _teleport_point_missing_pixel_count(config, point, blank_coverage) > 0:
                return index
        return normalized_start_index

    if world_path is None or not world_path.exists():
        return start_index % len(teleport_points)

    saved_columns = _saved_render_chunk_columns(config, world_path)
    if not saved_columns:
        return start_index % len(teleport_points)

    for offset in range(len(teleport_points)):
        index = (normalized_start_index + offset) % len(teleport_points)
        point = teleport_points[index]
        if _teleport_point_missing_chunk_count(config, point, saved_columns) > 0:
            return index
    return normalized_start_index


def _load_headless_loader_progress(
    path: Path,
    *,
    config: WorldgenConfig,
    teleport_points: tuple[tuple[int, int], ...],
    planner_context: dict[str, object] | None = None,
) -> int:
    if not teleport_points:
        return 0
    try:
        progress_text = _read_text_with_retry(path)
    except FileNotFoundError:
        return 0
    except OSError:
        return 0
    try:
        payload = json.loads(progress_text)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    expected_signature = _headless_loader_progress_signature(
        config,
        len(teleport_points),
        planner_context=planner_context,
    )
    if payload.get('signature') != expected_signature:
        return 0
    next_index = payload.get('next_index')
    if not isinstance(next_index, int):
        return 0
    return next_index % len(teleport_points)


def _save_headless_loader_progress(
    path: Path,
    *,
    config: WorldgenConfig,
    teleport_points: tuple[tuple[int, int], ...],
    next_index: int,
    planner_context: dict[str, object] | None = None,
) -> None:
    if not teleport_points:
        return
    payload = {
        'signature': _headless_loader_progress_signature(
            config,
            len(teleport_points),
            planner_context=planner_context,
        ),
        'next_index': next_index % len(teleport_points),
        'target_count': len(teleport_points),
        'updated_at': utc_now_iso(),
    }
    _write_text_atomically_with_retry(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + '\n',
    )


def _read_text_with_retry(
    path: Path,
    *,
    attempts: int = 5,
    retry_delay_seconds: float = 0.2,
) -> str:
    retryable_errnos = {errno.EDEADLK, errno.EAGAIN}
    last_error: OSError | None = None
    for attempt in range(attempts):
        try:
            return path.read_text(encoding='utf-8')
        except OSError as exc:
            last_error = exc
            if exc.errno not in retryable_errnos or attempt == attempts - 1:
                raise
            time.sleep(retry_delay_seconds * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise FileNotFoundError(path)


def _write_text_atomically_with_retry(
    path: Path,
    text: str,
    *,
    attempts: int = 8,
    retry_delay_seconds: float = 0.25,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    retryable_errnos = {errno.EDEADLK, errno.EAGAIN}
    last_error: OSError | None = None
    for attempt in range(attempts):
        temporary_path = path.with_name(f'.{path.name}.{os.getpid()}.{attempt}.tmp')
        try:
            temporary_path.write_text(text, encoding='utf-8')
            temporary_path.replace(path)
            return
        except OSError as exc:
            last_error = exc
            try:
                temporary_path.unlink()
            except OSError:
                pass
            if exc.errno not in retryable_errnos or attempt == attempts - 1:
                raise
            time.sleep(retry_delay_seconds * (attempt + 1))
    if last_error is not None:
        raise last_error


def _headless_loader_progress_signature(
    config: WorldgenConfig,
    target_count: int,
    *,
    planner_context: dict[str, object] | None = None,
) -> dict[str, object]:
    signature: dict[str, object] = {
        'center_x': config.render.center_x,
        'center_z': config.render.center_z,
        'render_radius': config.render.radius,
        'render_min_x': config.render.min_x,
        'render_max_x': config.render.max_x,
        'render_min_z': config.render.min_z,
        'render_max_z': config.render.max_z,
        'chunk_radius': config.headless_loader.chunk_radius,
        'target_outset_blocks': config.headless_loader.target_outset_blocks,
        'target_overlap_blocks': config.headless_loader.target_overlap_blocks,
        'teleport_y': config.headless_loader.teleport_y,
        'planner_version': TELEPORT_TARGET_PLANNER_VERSION,
    }
    if planner_context is not None:
        signature['planner_context'] = planner_context
    return signature


def _load_loader_result_payload(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _payload_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, int):
        return value
    return 0


def _format_server_command_output(command: str, output: str) -> str:
    if output.strip():
        return f'$ {command}\n{output.strip()}'
    return f'$ {command}'


def _format_loader_attempt_outputs(attempts: list[_HeadlessChunkLoadAttempt]) -> str:
    if len(attempts) == 1:
        return attempts[0].output

    output_blocks: list[str] = []
    total_attempts = len(attempts)
    for index, attempt in enumerate(attempts, start=1):
        header = (
            f'Attempt {index}/{total_attempts}: '
            f'exit={attempt.returncode}, chunks={attempt.chunks_received}, '
            f'chunk_columns={attempt.unique_chunk_columns}'
        )
        if attempt.fatal_server_crash:
            header = f'{header}, bedrock_crash=yes'
        if attempt.output:
            output_blocks.append(f'{header}\n{attempt.output}')
        else:
            output_blocks.append(header)
    return '\n\n'.join(output_blocks)


def _headless_loader_ready_for_teleport(output_lines: list[str]) -> bool:
    return any('spawned' in line for line in output_lines)


def _headless_loader_has_chunks(output_lines: list[str]) -> bool:
    return any('chunk packets' in line or 'chunk_columns=' in line for line in output_lines)


def _headless_loader_username(attempt_number: int) -> str:
    unique_number = int(time.time() * 1000) % 1_000_000
    return f'MetroBot{unique_number:06d}{attempt_number}'


def _render_area_teleport_points(
    config: WorldgenConfig,
    *,
    world_path: Path | None = None,
    blank_coverage: _BlankRenderCoverage | None = None,
) -> tuple[tuple[int, int], ...]:
    if blank_coverage is not None:
        return _blank_pixel_fill_teleport_points(config, blank_coverage.blank_pixels_by_chunk)

    saved_columns: set[tuple[int, int]] = set()
    if world_path is not None and world_path.exists():
        saved_columns = _saved_render_chunk_columns(config, world_path)
    return _blank_space_fill_teleport_points(config, saved_columns)


def _teleport_planner_context(
    blank_coverage: _BlankRenderCoverage | None,
) -> dict[str, object] | None:
    if blank_coverage is None:
        return None
    return {
        'coverage_source': 'render_pixels',
        'render_image_path': str(blank_coverage.image_path.resolve()),
        'total_pixels': blank_coverage.total_pixels,
    }


def _load_blank_render_coverage(
    config: WorldgenConfig,
    image_path: Path,
) -> _BlankRenderCoverage | None:
    image_stat = _file_stat_tuple(image_path)
    if image_stat is None:
        return None

    try:
        from PIL import Image
    except ImportError:
        return None
    Image.MAX_IMAGE_PIXELS = None

    render = config.render
    expected_width = _sampled_axis_size(render.min_x, render.max_x, render.sample_step)
    expected_height = _sampled_axis_size(render.min_z, render.max_z, render.sample_step)

    try:
        with Image.open(image_path) as source_image:
            alpha = source_image.convert('RGBA').getchannel('A')
    except OSError:
        return None

    if alpha.size != (expected_width, expected_height):
        return None

    histogram = alpha.histogram()
    blank_pixel_count = histogram[0]
    total_pixels = expected_width * expected_height
    if blank_pixel_count == 0:
        return _BlankRenderCoverage(
            image_path=image_path,
            image_stat=image_stat,
            blank_pixels_by_chunk={},
            blank_pixel_count=0,
            total_pixels=total_pixels,
        )

    chunk_x_by_pixel = tuple(
        (render.min_x + (pixel_x * render.sample_step)) // 16
        for pixel_x in range(expected_width)
    )
    chunk_z_by_pixel = tuple(
        (render.min_z + (pixel_z * render.sample_step)) // 16
        for pixel_z in range(expected_height)
    )
    alpha_values = alpha.getdata()
    blank_pixels_by_chunk: dict[tuple[int, int], int] = {}
    offset = 0
    for pixel_z in range(expected_height):
        chunk_z = chunk_z_by_pixel[pixel_z]
        for pixel_x in range(expected_width):
            if alpha_values[offset] == 0:
                column = (chunk_x_by_pixel[pixel_x], chunk_z)
                blank_pixels_by_chunk[column] = blank_pixels_by_chunk.get(column, 0) + 1
            offset += 1

    return _BlankRenderCoverage(
        image_path=image_path,
        image_stat=image_stat,
        blank_pixels_by_chunk=blank_pixels_by_chunk,
        blank_pixel_count=blank_pixel_count,
        total_pixels=total_pixels,
    )


def _file_stat_tuple(path: Path) -> tuple[str, int, int] | None:
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return (str(path.resolve()), stat_result.st_mtime_ns, stat_result.st_size)


def _sampled_axis_size(min_value: int, max_value: int, sample_step: int) -> int:
    return ((max_value - min_value) // sample_step) + 1


def _target_stride_chunks(config: WorldgenConfig) -> int:
    radius = config.headless_loader.chunk_radius
    target_width_chunks = (radius * 2) + 1
    overlap_chunks = min(radius * 2, math.ceil(config.headless_loader.target_overlap_blocks / 16))
    return max(1, target_width_chunks - overlap_chunks)


def _chunk_center_world(chunk_coordinate: int) -> int:
    return (chunk_coordinate * 16) + 8


def _blank_pixel_fill_teleport_points(
    config: WorldgenConfig,
    blank_pixels_by_chunk: dict[tuple[int, int], int],
) -> tuple[tuple[int, int], ...]:
    return tuple(
        _chunk_center_world_pair(center_chunk)
        for center_chunk in _radial_tangent_target_center_chunks(config)
        if _teleport_center_blank_pixel_count(
            config,
            center_chunk[0],
            center_chunk[1],
            blank_pixels_by_chunk,
        ) > 0
    )


def _teleport_center_blank_pixel_count(
    config: WorldgenConfig,
    center_chunk_x: int,
    center_chunk_z: int,
    blank_pixels_by_chunk: dict[tuple[int, int], int],
) -> int:
    return sum(
        blank_pixels_by_chunk.get(column, 0)
        for column in _teleport_center_chunk_columns(config, center_chunk_x, center_chunk_z)
    )


def _blank_space_fill_teleport_points(
    config: WorldgenConfig,
    saved_columns: set[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    missing_columns = _missing_render_chunk_columns(config, saved_columns)
    return tuple(
        _chunk_center_world_pair(center_chunk)
        for center_chunk in _radial_tangent_target_center_chunks(config)
        if any(
            column in missing_columns
            for column in _teleport_center_chunk_columns(
                config,
                center_chunk[0],
                center_chunk[1],
            )
        )
    )


def _chunk_center_world_pair(center_chunk: tuple[int, int]) -> tuple[int, int]:
    return (
        _chunk_center_world(center_chunk[0]),
        _chunk_center_world(center_chunk[1]),
    )


def _radial_tangent_target_center_chunks(config: WorldgenConfig) -> tuple[tuple[int, int], ...]:
    min_chunk_x, max_chunk_x, min_chunk_z, max_chunk_z = _render_area_chunk_bounds(config)
    target_width_chunks = (config.headless_loader.chunk_radius * 2) + 1
    center_chunk_x = config.render.center_x // 16
    center_chunk_z = config.render.center_z // 16
    center_chunks_x = _tangent_target_axis_center_chunks(
        min_chunk_x,
        max_chunk_x,
        center_chunk_x,
        target_width_chunks,
    )
    center_chunks_z = _tangent_target_axis_center_chunks(
        min_chunk_z,
        max_chunk_z,
        center_chunk_z,
        target_width_chunks,
    )
    centers = [
        (chunk_x, chunk_z)
        for chunk_z in center_chunks_z
        for chunk_x in center_chunks_x
    ]
    return tuple(sorted(centers, key=lambda center: _target_center_radial_sort_key(config, center)))


def _tangent_target_axis_center_chunks(
    min_chunk: int,
    max_chunk: int,
    center_chunk: int,
    target_width_chunks: int,
) -> tuple[int, ...]:
    radius = target_width_chunks // 2
    first_center = center_chunk
    while first_center - radius > min_chunk:
        first_center -= target_width_chunks

    values: list[int] = []
    current_center = first_center
    while current_center - radius <= max_chunk:
        values.append(current_center)
        current_center += target_width_chunks
    return tuple(values)


def _target_center_radial_sort_key(
    config: WorldgenConfig,
    center_chunk: tuple[int, int],
) -> tuple[int, float, float, int, int]:
    center_world = _chunk_center_world_pair(center_chunk)
    delta_x = center_world[0] - config.render.center_x
    delta_z = center_world[1] - config.render.center_z
    target_width_blocks = ((config.headless_loader.chunk_radius * 2) + 1) * 16
    ring = round(math.hypot(delta_x, delta_z) / target_width_blocks)
    return (
        ring,
        abs(math.hypot(delta_x, delta_z) - (ring * target_width_blocks)),
        math.atan2(delta_z, delta_x),
        center_chunk[1],
        center_chunk[0],
    )


def _render_area_chunk_bounds(config: WorldgenConfig) -> tuple[int, int, int, int]:
    render = config.render
    return (
        render.min_x // 16,
        render.max_x // 16,
        render.min_z // 16,
        render.max_z // 16,
    )


def _render_area_chunk_columns(config: WorldgenConfig) -> set[tuple[int, int]]:
    min_chunk_x, max_chunk_x, min_chunk_z, max_chunk_z = _render_area_chunk_bounds(config)
    return {
        (chunk_x, chunk_z)
        for chunk_z in range(min_chunk_z, max_chunk_z + 1)
        for chunk_x in range(min_chunk_x, max_chunk_x + 1)
    }


def _missing_render_chunk_columns(
    config: WorldgenConfig,
    saved_columns: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    return _render_area_chunk_columns(config).difference(saved_columns)


def _teleport_point_chunk_columns(
    config: WorldgenConfig,
    point: tuple[int, int],
) -> set[tuple[int, int]]:
    return _teleport_center_chunk_columns(config, point[0] // 16, point[1] // 16)


def _target_square_loader_points(
    config: WorldgenConfig,
    point: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    radius = config.headless_loader.chunk_radius
    if radius <= 0:
        return (point,)

    center_chunk_x = point[0] // 16
    center_chunk_z = point[1] // 16
    offset = max(1, math.ceil(radius / 2))
    min_chunk_x, max_chunk_x, min_chunk_z, max_chunk_z = _target_load_chunk_bounds()
    loader_chunks = (
        (
            _clamp_int(center_chunk_x - offset, min_chunk_x, max_chunk_x),
            _clamp_int(center_chunk_z - offset, min_chunk_z, max_chunk_z),
        ),
        (
            _clamp_int(center_chunk_x + offset, min_chunk_x, max_chunk_x),
            _clamp_int(center_chunk_z - offset, min_chunk_z, max_chunk_z),
        ),
        (
            _clamp_int(center_chunk_x - offset, min_chunk_x, max_chunk_x),
            _clamp_int(center_chunk_z + offset, min_chunk_z, max_chunk_z),
        ),
        (
            _clamp_int(center_chunk_x + offset, min_chunk_x, max_chunk_x),
            _clamp_int(center_chunk_z + offset, min_chunk_z, max_chunk_z),
        ),
    )
    return tuple(dict.fromkeys(_chunk_center_world_pair(chunk) for chunk in loader_chunks))


def _teleport_center_chunk_columns(
    config: WorldgenConfig,
    center_chunk_x: int,
    center_chunk_z: int,
) -> set[tuple[int, int]]:
    radius = config.headless_loader.chunk_radius
    min_chunk_x, max_chunk_x, min_chunk_z, max_chunk_z = _target_load_chunk_bounds()
    return {
        (chunk_x, chunk_z)
        for chunk_z in range(center_chunk_z - radius, center_chunk_z + radius + 1)
        if min_chunk_z <= chunk_z <= max_chunk_z
        for chunk_x in range(center_chunk_x - radius, center_chunk_x + radius + 1)
        if min_chunk_x <= chunk_x <= max_chunk_x
    }


def _teleport_point_missing_chunk_count(
    config: WorldgenConfig,
    point: tuple[int, int],
    saved_columns: set[tuple[int, int]],
) -> int:
    return sum(
        1
        for column in _teleport_point_chunk_columns(config, point)
        if column not in saved_columns
    )


def _teleport_point_missing_pixel_count(
    config: WorldgenConfig,
    point: tuple[int, int],
    blank_coverage: _BlankRenderCoverage,
) -> int:
    return sum(
        blank_coverage.blank_pixels_by_chunk.get(column, 0)
        for column in _teleport_point_chunk_columns(config, point)
    )


def _teleport_point_pixel_coverage(
    config: WorldgenConfig,
    point: tuple[int, int],
    blank_coverage: _BlankRenderCoverage,
) -> float:
    target_pixel_count = _teleport_point_sampled_pixel_count(config, point)
    if target_pixel_count <= 0:
        return 1.0
    missing_pixels = _teleport_point_missing_pixel_count(config, point, blank_coverage)
    return max(0.0, min(1.0, 1.0 - (missing_pixels / target_pixel_count)))


def _teleport_point_sampled_pixel_count(
    config: WorldgenConfig,
    point: tuple[int, int],
) -> int:
    min_x, max_x, min_z, max_z = _teleport_target_world_bounds(config, point)
    render = config.render
    clipped_min_x = max(min_x, render.min_x)
    clipped_max_x = min(max_x, render.max_x)
    clipped_min_z = max(min_z, render.min_z)
    clipped_max_z = min(max_z, render.max_z)
    if clipped_min_x > clipped_max_x or clipped_min_z > clipped_max_z:
        return 0
    x_count = _sampled_value_count_in_range(
        clipped_min_x,
        clipped_max_x,
        origin=render.min_x,
        sample_step=render.sample_step,
    )
    z_count = _sampled_value_count_in_range(
        clipped_min_z,
        clipped_max_z,
        origin=render.min_z,
        sample_step=render.sample_step,
    )
    return x_count * z_count


def _sampled_value_count_in_range(
    min_value: int,
    max_value: int,
    *,
    origin: int,
    sample_step: int,
) -> int:
    first_offset = max(0, math.ceil((min_value - origin) / sample_step))
    last_offset = math.floor((max_value - origin) / sample_step)
    if first_offset > last_offset:
        return 0
    return (last_offset - first_offset) + 1


def _existing_columns_for_touch_fill(
    config: WorldgenConfig,
    world_path: Path,
    *,
    blank_coverage: _BlankRenderCoverage | None,
) -> set[tuple[int, int]]:
    if blank_coverage is not None:
        return _render_area_chunk_columns(config).difference(blank_coverage.blank_pixels_by_chunk)
    return _saved_render_chunk_columns(config, world_path)


def _progressive_box_teleport_points(
    config: WorldgenConfig,
    points: list[tuple[int, int]] | tuple[tuple[int, int], ...],
    step: int,
) -> tuple[tuple[int, int], ...]:
    return tuple(sorted(points, key=lambda point: _box_fill_teleport_sort_key(config, point, step)))


def _undercovered_box_teleport_points(
    config: WorldgenConfig,
    points: list[tuple[int, int]] | tuple[tuple[int, int], ...],
    step: int,
    saved_columns: set[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    return tuple(
        sorted(
            points,
            key=lambda point: (
                _teleport_point_chunk_coverage(config, point, saved_columns),
                _box_fill_teleport_sort_key(config, point, step),
            ),
        )
    )


def _saved_render_chunk_columns(
    config: WorldgenConfig,
    world_path: Path,
    *,
    include_packet_cache: bool = False,
    packet_cache_path: Path | None = None,
) -> set[tuple[int, int]]:
    render = config.render
    min_chunk_x = render.min_x // 16
    max_chunk_x = render.max_x // 16
    min_chunk_z = render.min_z // 16
    max_chunk_z = render.max_z // 16
    columns: set[tuple[int, int]] = set()
    try:
        columns.update({
            (record.chunk_x, record.chunk_z)
            for record in iter_subchunk_records(
                world_path,
                min_chunk_x=min_chunk_x,
                max_chunk_x=max_chunk_x,
                min_chunk_z=min_chunk_z,
                max_chunk_z=max_chunk_z,
            )
        })
    except Exception:
        pass
    if include_packet_cache:
        columns.update(
            _cached_packet_chunk_columns(
                packet_cache_path or config.storage.cache_dir / HEADLESS_LOADER_CHUNK_PACKET_FILE_NAME,
                min_chunk_x=min_chunk_x,
                max_chunk_x=max_chunk_x,
                min_chunk_z=min_chunk_z,
                max_chunk_z=max_chunk_z,
            )
        )
    return columns


def _cached_packet_chunk_columns(
    packet_cache_path: Path,
    *,
    min_chunk_x: int,
    max_chunk_x: int,
    min_chunk_z: int,
    max_chunk_z: int,
) -> set[tuple[int, int]]:
    if not packet_cache_path.exists():
        return set()
    columns: set[tuple[int, int]] = set()
    try:
        lines = packet_cache_path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return set()
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        chunk_x = payload.get('x')
        chunk_z = payload.get('z')
        dimension = payload.get('dimension')
        if not isinstance(chunk_x, int) or not isinstance(chunk_z, int):
            continue
        if dimension not in (None, 0):
            continue
        if min_chunk_x <= chunk_x <= max_chunk_x and min_chunk_z <= chunk_z <= max_chunk_z:
            columns.add((chunk_x, chunk_z))
    return columns


def _teleport_point_chunk_coverage(
    config: WorldgenConfig,
    point: tuple[int, int],
    saved_columns: set[tuple[int, int]],
) -> float:
    requested_columns = _teleport_point_chunk_columns(config, point)
    if not requested_columns:
        return 1.0

    saved_count = sum(
        1
        for column in requested_columns
        if column in saved_columns
    )
    return saved_count / len(requested_columns)

def _chunk_touch_fill_commands(
    config: WorldgenConfig,
    point: tuple[int, int],
    *,
    existing_columns: set[tuple[int, int]] | None = None,
) -> tuple[str, ...]:
    radius = config.headless_loader.chunk_radius
    center_chunk_x = point[0] // 16
    center_chunk_z = point[1] // 16
    filled_columns = existing_columns or set()
    min_chunk_x, max_chunk_x, min_chunk_z, max_chunk_z = _target_load_chunk_bounds()

    row_spans: list[tuple[int, int, int]] = []
    for chunk_z in range(center_chunk_z - radius, center_chunk_z + radius + 1):
        if not min_chunk_z <= chunk_z <= max_chunk_z:
            continue
        eligible_chunk_x = [
            chunk_x
            for chunk_x in range(center_chunk_x - radius, center_chunk_x + radius + 1)
            if (
                min_chunk_x <= chunk_x <= max_chunk_x
                and (chunk_x, chunk_z) not in filled_columns
            )
        ]
        if not eligible_chunk_x:
            continue

        start_chunk_x = eligible_chunk_x[0]
        previous_chunk_x = eligible_chunk_x[0]
        for chunk_x in eligible_chunk_x[1:]:
            if chunk_x == previous_chunk_x + 1:
                previous_chunk_x = chunk_x
                continue
            row_spans.append((start_chunk_x, previous_chunk_x, chunk_z))
            start_chunk_x = chunk_x
            previous_chunk_x = chunk_x

        row_spans.append((start_chunk_x, previous_chunk_x, chunk_z))

    return _merged_chunk_touch_fill_commands(row_spans)


def _merged_chunk_touch_fill_commands(row_spans: list[tuple[int, int, int]]) -> tuple[str, ...]:
    commands: list[str] = []
    active_start_x: int | None = None
    active_end_x: int | None = None
    active_start_z: int | None = None
    active_end_z: int | None = None

    def flush_active() -> None:
        nonlocal active_start_x, active_end_x, active_start_z, active_end_z
        if (
            active_start_x is not None
            and active_end_x is not None
            and active_start_z is not None
            and active_end_z is not None
        ):
            commands.append(
                _chunk_touch_fill_command_for_span(
                    active_start_x,
                    active_end_x,
                    active_start_z,
                    active_end_z,
                )
            )
        active_start_x = None
        active_end_x = None
        active_start_z = None
        active_end_z = None

    for start_x, end_x, chunk_z in row_spans:
        if active_start_x is None:
            active_start_x = start_x
            active_end_x = end_x
            active_start_z = chunk_z
            active_end_z = chunk_z
            continue

        can_extend = (
            start_x == active_start_x
            and end_x == active_end_x
            and active_start_z is not None
            and active_end_z is not None
            and chunk_z == active_end_z + 1
            and _chunk_touch_fill_block_count(start_x, end_x, active_start_z, chunk_z)
            <= CHUNK_TOUCH_MAX_BLOCKS
        )
        if can_extend:
            active_end_z = chunk_z
            continue

        flush_active()
        active_start_x = start_x
        active_end_x = end_x
        active_start_z = chunk_z
        active_end_z = chunk_z

    flush_active()
    return tuple(commands)


def _chunk_touch_fill_block_count(
    start_chunk_x: int,
    end_chunk_x: int,
    start_chunk_z: int,
    end_chunk_z: int,
) -> int:
    x_blocks = ((end_chunk_x - start_chunk_x) + 1) * 16
    z_blocks = ((end_chunk_z - start_chunk_z) + 1) * 16
    return x_blocks * z_blocks


def _teleport_target_world_bounds(
    config: WorldgenConfig,
    point: tuple[int, int],
) -> tuple[int, int, int, int]:
    radius = config.headless_loader.chunk_radius
    center_chunk_x = point[0] // 16
    center_chunk_z = point[1] // 16
    min_chunk_x = center_chunk_x - radius
    max_chunk_x = center_chunk_x + radius
    min_chunk_z = center_chunk_z - radius
    max_chunk_z = center_chunk_z + radius
    return (
        max(TARGET_LOAD_MIN_X, min_chunk_x * 16),
        min(TARGET_LOAD_MAX_X, (max_chunk_x * 16) + 15),
        max(TARGET_LOAD_MIN_Z, min_chunk_z * 16),
        min(TARGET_LOAD_MAX_Z, (max_chunk_z * 16) + 15),
    )


def _target_load_chunk_bounds() -> tuple[int, int, int, int]:
    return (
        math.ceil((TARGET_LOAD_MIN_X - 8) / 16),
        math.floor((TARGET_LOAD_MAX_X - 8) / 16),
        math.ceil((TARGET_LOAD_MIN_Z - 8) / 16),
        math.floor((TARGET_LOAD_MAX_Z - 8) / 16),
    )


def _chunk_column_in_render_radius(
    config: WorldgenConfig,
    chunk_x: int,
    chunk_z: int,
) -> bool:
    point = ((chunk_x * 16) + 8, (chunk_z * 16) + 8)
    return (
        config.render.min_x - 16 <= point[0] <= config.render.max_x + 16
        and config.render.min_z - 16 <= point[1] <= config.render.max_z + 16
    )


def _chunk_touch_fill_command_for_span(
    start_chunk_x: int,
    end_chunk_x: int,
    start_chunk_z: int,
    end_chunk_z: int,
) -> str:
    min_x = start_chunk_x * 16
    max_x = (end_chunk_x * 16) + 15
    min_z = start_chunk_z * 16
    max_z = (end_chunk_z * 16) + 15
    return (
        f'fill {min_x} {CHUNK_TOUCH_Y} {min_z} '
        f'{max_x} {CHUNK_TOUCH_Y} {max_z} {CHUNK_TOUCH_BLOCK}'
    )


def _box_fill_teleport_ring(
    config: WorldgenConfig,
    point: tuple[int, int],
    step: int,
) -> int:
    delta_x = point[0] - config.render.center_x
    delta_z = point[1] - config.render.center_z
    return round(math.hypot(delta_x, delta_z) / step)


def _box_fill_teleport_sort_key(
    config: WorldgenConfig,
    point: tuple[int, int],
    step: int,
) -> tuple[int, float, float, float, float]:
    delta_x = point[0] - config.render.center_x
    delta_z = point[1] - config.render.center_z
    distance = math.hypot(delta_x, delta_z)
    ring = _box_fill_teleport_ring(config, point, step)
    return (
        ring,
        abs(distance - (ring * step)),
        math.atan2(delta_z, delta_x),
        distance,
        point[0],
    )


def _render_axis_teleport_chunk_values(
    min_chunk: int,
    max_chunk: int,
    center_chunk: int,
    config: WorldgenConfig,
) -> tuple[int, ...]:
    radius = config.headless_loader.chunk_radius
    min_center_chunk = min_chunk + radius
    max_center_chunk = max_chunk - radius
    if min_center_chunk > max_center_chunk:
        return (_clamp_int(center_chunk, min_chunk, max_chunk),)

    stride = _target_stride_chunks(config)
    requested_chunks = (max_chunk - min_chunk) + 1
    target_width_chunks = (radius * 2) + 1
    target_count = max(2, math.ceil((requested_chunks - target_width_chunks) / stride) + 1)
    center_span = max_center_chunk - min_center_chunk
    values = {
        round(min_center_chunk + ((center_span * index) / (target_count - 1)))
        for index in range(target_count)
    }
    return tuple(sorted(values))


def _clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


def _container_repo_path(repo_root: Path, host_path: Path) -> str:
    return '/app/' + host_path.resolve().relative_to(repo_root.resolve()).as_posix()
