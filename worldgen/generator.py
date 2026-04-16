from __future__ import annotations

import json
import math
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
from .render import RenderPlan, RenderResult, build_render_plan, render_topdown_map, save_render_plan


BEDROCK_SERVICE_NAME = 'bedrock'
HEADLESS_LOADER_RESULT_FILE_NAME = 'headless_loader_result.json'
HEADLESS_LOADER_CHUNK_PACKET_FILE_NAME = 'headless_chunk_packets.jsonl'
HEADLESS_LOADER_MAX_ATTEMPTS = 3
HEADLESS_LOADER_RETRY_DELAY_SECONDS = 5
HEADLESS_LOADER_STARTUP_TIMEOUT_SECONDS = 300
HEADLESS_LOADER_STOP_GRACE_SECONDS = 10
HEADLESS_LOADER_STOP_COMMAND_TIMEOUT_SECONDS = 25
HEADLESS_LOADER_FIRST_TELEPORT_DELAY_SECONDS = 1.0
TELEPORT_TARGET_COVERAGE_THRESHOLD = 0.85
CHUNK_TOUCH_BLOCK = 'bedrock'
CHUNK_TOUCH_Y = -64
CHUNK_TOUCH_MAX_BLOCKS = 30_000
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
    teleport_targets: tuple[str, ...]
    fatal_server_crash: bool
    output: str


class BedrockWorldGenerator:
    def __init__(self, config: WorldgenConfig):
        self.config = config
        self.paths = config.paths

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
    ) -> HeadlessChunkLoadResult:
        loader_config = self.config.headless_loader
        effective_wait_seconds = wait_seconds or loader_config.wait_seconds
        result_path = self.paths.cache_dir / HEADLESS_LOADER_RESULT_FILE_NAME
        chunk_packet_path = self.paths.cache_dir / HEADLESS_LOADER_CHUNK_PACKET_FILE_NAME
        coverage_world_path = self._world_folder_for_coverage_scan()
        teleport_points = _render_area_teleport_points(self.config, world_path=coverage_world_path)
        teleport_start_index = 0
        result_path.parent.mkdir(parents=True, exist_ok=True)
        container_result_path = _container_repo_path(self.config.repo_root, result_path)
        container_chunk_packet_path = _container_repo_path(self.config.repo_root, chunk_packet_path)

        attempts: list[_HeadlessChunkLoadAttempt] = []
        for attempt_number in range(1, HEADLESS_LOADER_MAX_ATTEMPTS + 1):
            if self.is_service_running():
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
                teleport_points=teleport_points,
                teleport_start_index=teleport_start_index,
                loader_username=_headless_loader_username(attempt_number),
            )
            attempts.append(attempt)

            if attempt.chunks_received > 0:
                break
            if attempt_number < HEADLESS_LOADER_MAX_ATTEMPTS:
                self.stop(
                    grace_seconds=HEADLESS_LOADER_STOP_GRACE_SECONDS,
                    command_timeout_seconds=HEADLESS_LOADER_STOP_COMMAND_TIMEOUT_SECONDS,
                )
                time.sleep(HEADLESS_LOADER_RETRY_DELAY_SECONDS)

        last_attempt = attempts[-1]
        successful_attempt = last_attempt if last_attempt.chunks_received > 0 else None
        teleport_next_index = teleport_start_index
        if successful_attempt is not None:
            teleport_next_index = successful_attempt.teleport_commands_sent % len(teleport_points)

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

    def _load_chunks_headless_once(
        self,
        *,
        wait_seconds: int,
        result_path: Path,
        container_result_path: str,
        container_chunk_packet_path: str,
        teleport_points: tuple[tuple[int, int], ...],
        teleport_start_index: int,
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
        teleport_targets: list[tuple[int, int]] = []
        touched_targets: set[tuple[int, int]] = set()
        next_teleport_at = time.monotonic() + min(
            loader_config.teleport_delay_seconds,
            HEADLESS_LOADER_FIRST_TELEPORT_DELAY_SECONDS,
        )
        hard_deadline = (
            time.monotonic()
            + wait_seconds
            + loader_config.teleport_delay_seconds
            + (loader_config.teleport_retry_seconds * loader_config.teleport_attempts)
            + 240
        )

        while process.poll() is None:
            now = time.monotonic()
            if now > hard_deadline:
                process.kill()
                server_command_outputs.append('Killed headless loader after it exceeded its hard timeout.')
                break
            if (
                teleport_commands_sent < loader_config.teleport_attempts
                and _headless_loader_ready_for_teleport(output_lines)
                and now >= next_teleport_at
            ):
                target_x, target_z = teleport_points[
                    (teleport_start_index + teleport_commands_sent) % len(teleport_points)
                ]
                teleport_targets.append((target_x, target_z))
                teleport_command = (
                    f'tp {loader_username} '
                    f'{target_x} {loader_config.teleport_y} {target_z}'
                )
                command_output = self.send_command(teleport_command, check=False)
                server_command_outputs.append(
                    _format_server_command_output(teleport_command, command_output)
                )
                if (target_x, target_z) not in touched_targets:
                    touched_targets.add((target_x, target_z))
                    touch_commands = _chunk_touch_fill_commands(self.config, (target_x, target_z))
                    for touch_command in touch_commands:
                        self.send_command(touch_command, check=False)
                    server_command_outputs.append(
                        (
                            f'$ touch loaded chunks under {target_x},{target_z}\n'
                            f'{len(touch_commands)} bottom fill commands at y={CHUNK_TOUCH_Y}'
                        )
                    )
                teleport_commands_sent += 1
                next_teleport_at = now + loader_config.teleport_retry_seconds
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
    ) -> RenderResult:
        self.paths.ensure_runtime_dirs()
        world_path = self._resolve_existing_world_folder()
        self.write_render_plan(world_path)
        return render_topdown_map(
            self.config,
            world_path,
            image_path=self.paths.render_image_path,
            metadata_path=self.paths.render_cache_path,
            diagnose_unknown_blocks=diagnose_unknown_blocks,
            prefer_persistent_bedrock=prefer_persistent_bedrock,
        )

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


def _tail_lines(text: str, limit: int) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return '\n'.join(lines[-limit:]) if lines else '(no logs captured)'


def _bedrock_server_crashed(logs_output: str) -> bool:
    return any(marker in logs_output for marker in BEDROCK_NATIVE_CRASH_MARKERS)


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


def _headless_loader_username(attempt_number: int) -> str:
    unique_number = int(time.time() * 1000) % 1_000_000
    return f'MetroBot{unique_number:06d}{attempt_number}'


def _render_area_teleport_points(
    config: WorldgenConfig,
    *,
    world_path: Path | None = None,
) -> tuple[tuple[int, int], ...]:
    step = max(16, config.headless_loader.chunk_radius * 16 * 2)
    x_values = _render_axis_teleport_values(
        config.render.min_x,
        config.render.max_x,
        config.render.center_x,
        step,
    )
    z_values = _render_axis_teleport_values(
        config.render.min_z,
        config.render.max_z,
        config.render.center_z,
        step,
    )
    points = [(x, z) for z in z_values for x in x_values]
    if world_path is not None and world_path.exists():
        saved_columns = _saved_render_chunk_columns(config, world_path)
        if saved_columns:
            return _undercovered_box_teleport_points(config, points, step, saved_columns)
        return _first_box_teleport_points(config, points, step)
    points.sort(key=lambda point: _box_fill_teleport_sort_key(config, point, step))
    return tuple(points)


def _first_box_teleport_points(
    config: WorldgenConfig,
    points: list[tuple[int, int]],
    step: int,
) -> tuple[tuple[int, int], ...]:
    first_ring = min(_box_fill_teleport_ring(config, point, step) for point in points)
    return tuple(
        sorted(
            (point for point in points if _box_fill_teleport_ring(config, point, step) == first_ring),
            key=lambda point: _box_fill_teleport_sort_key(config, point, step),
        )
    )


def _undercovered_box_teleport_points(
    config: WorldgenConfig,
    points: list[tuple[int, int]],
    step: int,
    saved_columns: set[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    coverages = {
        point: _teleport_point_chunk_coverage(config, point, saved_columns)
        for point in points
    }
    rings = sorted({_box_fill_teleport_ring(config, point, step) for point in points})
    for ring in rings:
        box_points = [
            point
            for point in points
            if _box_fill_teleport_ring(config, point, step) <= ring
        ]
        undercovered_points = [
            point
            for point in box_points
            if coverages[point] < TELEPORT_TARGET_COVERAGE_THRESHOLD
        ]
        if undercovered_points:
            return tuple(
                sorted(
                    undercovered_points,
                    key=lambda point: (
                        coverages[point],
                        _box_fill_teleport_sort_key(config, point, step),
                    ),
                )
            )
    return tuple(
        sorted(
            points,
            key=lambda point: (
                coverages[point],
                _box_fill_teleport_sort_key(config, point, step),
            ),
        )
    )


def _saved_render_chunk_columns(
    config: WorldgenConfig,
    world_path: Path,
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
    columns.update(
        _cached_packet_chunk_columns(
            config.storage.cache_dir / HEADLESS_LOADER_CHUNK_PACKET_FILE_NAME,
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
    render = config.render
    radius = config.headless_loader.chunk_radius
    center_chunk_x = point[0] // 16
    center_chunk_z = point[1] // 16
    min_chunk_x = max(render.min_x // 16, center_chunk_x - radius)
    max_chunk_x = min(render.max_x // 16, center_chunk_x + radius)
    min_chunk_z = max(render.min_z // 16, center_chunk_z - radius)
    max_chunk_z = min(render.max_z // 16, center_chunk_z + radius)
    requested_count = (
        (max_chunk_x - min_chunk_x + 1)
        * (max_chunk_z - min_chunk_z + 1)
    )
    if requested_count <= 0:
        return 1.0
    saved_count = sum(
        1
        for chunk_x in range(min_chunk_x, max_chunk_x + 1)
        for chunk_z in range(min_chunk_z, max_chunk_z + 1)
        if (chunk_x, chunk_z) in saved_columns
    )
    return saved_count / requested_count


def _chunk_touch_fill_commands(
    config: WorldgenConfig,
    point: tuple[int, int],
) -> tuple[str, ...]:
    render = config.render
    radius = config.headless_loader.chunk_radius
    center_chunk_x = point[0] // 16
    center_chunk_z = point[1] // 16
    min_chunk_x = max(render.min_x // 16, center_chunk_x - radius)
    max_chunk_x = min(render.max_x // 16, center_chunk_x + radius)
    min_chunk_z = max(render.min_z // 16, center_chunk_z - radius)
    max_chunk_z = min(render.max_z // 16, center_chunk_z + radius)
    min_x = min_chunk_x * 16
    max_x = (max_chunk_x * 16) + 15
    min_z = min_chunk_z * 16
    max_z = (max_chunk_z * 16) + 15
    width = max_x - min_x + 1
    if width <= 0 or max_z < min_z:
        return ()

    max_depth = max(1, CHUNK_TOUCH_MAX_BLOCKS // width)
    commands: list[str] = []
    z_start = min_z
    while z_start <= max_z:
        z_end = min(max_z, z_start + max_depth - 1)
        commands.append(
            (
                f'fill {min_x} {CHUNK_TOUCH_Y} {z_start} '
                f'{max_x} {CHUNK_TOUCH_Y} {z_end} {CHUNK_TOUCH_BLOCK}'
            )
        )
        z_start = z_end + 1
    return tuple(commands)


def _box_fill_teleport_ring(
    config: WorldgenConfig,
    point: tuple[int, int],
    step: int,
) -> int:
    delta_x = point[0] - config.render.center_x
    delta_z = point[1] - config.render.center_z
    return round(max(abs(delta_x), abs(delta_z)) / step)


def _box_fill_teleport_sort_key(
    config: WorldgenConfig,
    point: tuple[int, int],
    step: int,
) -> tuple[int, int, float, float, float]:
    delta_x = point[0] - config.render.center_x
    delta_z = point[1] - config.render.center_z
    ring = _box_fill_teleport_ring(config, point, step)
    is_box_edge = int(max(abs(delta_x), abs(delta_z)) != ring * step)
    return (
        ring,
        is_box_edge,
        math.atan2(delta_z, delta_x),
        math.hypot(delta_x, delta_z),
        point[0],
    )


def _render_axis_teleport_values(
    min_value: int,
    max_value: int,
    center_value: int,
    step: int,
) -> tuple[int, ...]:
    values = {center_value, min_value, max_value}
    offset = step
    while center_value - offset >= min_value:
        values.add(center_value - offset)
        offset += step
    offset = step
    while center_value + offset <= max_value:
        values.add(center_value + offset)
        offset += step
    return tuple(sorted(values))


def _container_repo_path(repo_root: Path, host_path: Path) -> str:
    return '/app/' + host_path.resolve().relative_to(repo_root.resolve()).as_posix()
