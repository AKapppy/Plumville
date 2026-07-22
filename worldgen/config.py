from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .paths import (
    DOCS_ASSETS_DIR_NAME,
    DOCS_DIR_NAME,
    ENV_FILE_NAME,
    ProjectPaths,
    RENDER_CACHE_FILE_NAME,
    RENDER_IMAGE_FILE_NAME,
    RENDER_PLAN_FILE_NAME,
    RUNTIME_DIR_NAME,
    WORLD_CACHE_FILE_NAME,
    default_config_path,
    default_compose_path,
    resolve_repo_path,
)


@dataclass(frozen=True, slots=True)
class WorldConfig:
    image: str
    server_version: str
    direct_download_url: str
    seed: str
    level_name: str
    eula: str
    port: int
    online_mode: str
    allow_cheats: str
    gamemode: str
    default_player_permission_level: str
    view_distance: int
    tick_distance: int
    player_idle_timeout: int
    startup_text: str
    startup_timeout_seconds: int
    stop_timeout_seconds: int


@dataclass(frozen=True, slots=True)
class HeadlessLoaderConfig:
    username: str
    client_version: str
    raknet_backend: str
    wait_seconds: int
    teleport_y: int
    teleport_delay_seconds: int
    teleport_retry_seconds: int
    teleport_attempts: int
    chunk_radius: int
    target_outset_blocks: int
    target_overlap_blocks: int


@dataclass(frozen=True, slots=True)
class LanConfig:
    enabled: bool
    world_name: str
    host: str
    port: int
    username: str
    client_version: str
    raknet_backend: str
    wait_seconds: int
    chunk_radius: int
    connect_timeout_ms: int


@dataclass(frozen=True, slots=True)
class StorageConfig:
    data_dir: Path
    cache_dir: Path
    output_dir: Path


@dataclass(frozen=True, slots=True)
class RenderAreaConfig:
    center_label: str
    center_x: int
    center_z: int
    radius: int
    sample_step: int
    bounds_min_x: int | None = None
    bounds_max_x: int | None = None
    bounds_min_z: int | None = None
    bounds_max_z: int | None = None

    @property
    def min_x(self) -> int:
        return self.bounds_min_x if self.bounds_min_x is not None else self.center_x - self.radius

    @property
    def max_x(self) -> int:
        return self.bounds_max_x if self.bounds_max_x is not None else self.center_x + self.radius

    @property
    def min_z(self) -> int:
        return self.bounds_min_z if self.bounds_min_z is not None else self.center_z - self.radius

    @property
    def max_z(self) -> int:
        return self.bounds_max_z if self.bounds_max_z is not None else self.center_z + self.radius


@dataclass(frozen=True, slots=True)
class WorldgenConfig:
    config_path: Path
    project_name: str
    compose_path: Path
    world: WorldConfig
    headless_loader: HeadlessLoaderConfig
    lan: LanConfig
    storage: StorageConfig
    render: RenderAreaConfig

    @property
    def repo_root(self) -> Path:
        return self.config_path.parent.resolve()

    @property
    def paths(self) -> ProjectPaths:
        runtime_dir = self.repo_root / RUNTIME_DIR_NAME
        docs_assets_dir = self.repo_root / DOCS_DIR_NAME / DOCS_ASSETS_DIR_NAME
        return ProjectPaths(
            repo_root=self.repo_root,
            config_path=self.config_path,
            compose_path=self.compose_path,
            runtime_dir=runtime_dir,
            env_file=runtime_dir / ENV_FILE_NAME,
            data_dir=self.storage.data_dir,
            cache_dir=self.storage.cache_dir,
            output_dir=self.storage.output_dir,
            world_cache_path=self.storage.cache_dir / WORLD_CACHE_FILE_NAME,
            render_plan_path=self.storage.cache_dir / RENDER_PLAN_FILE_NAME,
            render_cache_path=self.storage.cache_dir / RENDER_CACHE_FILE_NAME,
            render_image_path=self.storage.output_dir / RENDER_IMAGE_FILE_NAME,
            docs_assets_dir=docs_assets_dir,
            docs_render_image_path=docs_assets_dir / RENDER_IMAGE_FILE_NAME,
        )


def load_config(config_path: Path | None = None) -> WorldgenConfig:
    resolved_config_path = (config_path or default_config_path()).resolve()
    config_data = tomllib.loads(resolved_config_path.read_text(encoding='utf-8'))
    base_dir = resolved_config_path.parent.resolve()

    project_table = _require_table(config_data, 'project')
    world_table = _require_table(config_data, 'world')
    headless_loader_table = _optional_table(config_data, 'headless_loader')
    lan_table = _optional_table(config_data, 'lan')
    storage_table = _require_table(config_data, 'storage')
    render_table = _require_table(config_data, 'render')

    compose_path_raw = _optional_str(project_table, 'compose_file') or str(default_compose_path())
    compose_path = resolve_repo_path(base_dir, compose_path_raw)

    world = WorldConfig(
        image=_require_str(world_table, 'image'),
        server_version=_optional_str(world_table, 'server_version') or 'LATEST',
        direct_download_url=_optional_str(world_table, 'direct_download_url') or '',
        seed=_require_str(world_table, 'seed'),
        level_name=_require_str(world_table, 'level_name'),
        eula=_require_str(world_table, 'eula'),
        port=_require_positive_int(world_table, 'port'),
        online_mode=_server_bool_property(_optional_str(world_table, 'online_mode'), 'true'),
        allow_cheats=_server_bool_property(_optional_str(world_table, 'allow_cheats'), 'false'),
        gamemode=_optional_str(world_table, 'gamemode') or 'survival',
        default_player_permission_level=(
            _optional_str(world_table, 'default_player_permission_level') or 'member'
        ),
        view_distance=_optional_positive_int(world_table, 'view_distance') or 32,
        tick_distance=_optional_positive_int(world_table, 'tick_distance') or 4,
        player_idle_timeout=_optional_int_default(
            _optional_nonnegative_int(world_table, 'player_idle_timeout'),
            30,
        ),
        startup_text=_require_str(world_table, 'startup_text'),
        startup_timeout_seconds=_require_positive_int(world_table, 'startup_timeout_seconds'),
        stop_timeout_seconds=_require_positive_int(world_table, 'stop_timeout_seconds'),
    )

    headless_loader = HeadlessLoaderConfig(
        username=_optional_str(headless_loader_table, 'username') or 'MetroChunkLoader',
        client_version=_optional_str(headless_loader_table, 'client_version') or '26.10',
        raknet_backend=_optional_str(headless_loader_table, 'raknet_backend') or 'raknet-node',
        wait_seconds=_optional_positive_int(headless_loader_table, 'wait_seconds') or 45,
        teleport_y=_optional_int(headless_loader_table, 'teleport_y') or 96,
        teleport_delay_seconds=(
            _optional_positive_int(headless_loader_table, 'teleport_delay_seconds') or 8
        ),
        teleport_retry_seconds=(
            _optional_positive_int(headless_loader_table, 'teleport_retry_seconds') or 5
        ),
        teleport_attempts=_optional_int_default(
            _optional_nonnegative_int(headless_loader_table, 'teleport_attempts'),
            4,
        ),
        chunk_radius=_optional_positive_int(headless_loader_table, 'chunk_radius') or 12,
        target_outset_blocks=_optional_int_default(
            _optional_nonnegative_int(headless_loader_table, 'target_outset_blocks'),
            0,
        ),
        target_overlap_blocks=_optional_int_default(
            _optional_nonnegative_int(headless_loader_table, 'target_overlap_blocks'),
            64,
        ),
    )

    lan = LanConfig(
        enabled=_optional_bool(lan_table, 'enabled', False),
        world_name=_optional_str(lan_table, 'world_name') or 'Plumville',
        host=_optional_str(lan_table, 'host') or 'host.docker.internal',
        port=_optional_positive_int(lan_table, 'port') or 19132,
        username=_optional_str(lan_table, 'username') or 'PlumvilleMapper',
        client_version=_optional_str(lan_table, 'client_version') or headless_loader.client_version,
        raknet_backend=_optional_str(lan_table, 'raknet_backend') or headless_loader.raknet_backend,
        wait_seconds=_optional_positive_int(lan_table, 'wait_seconds') or headless_loader.wait_seconds,
        chunk_radius=_optional_positive_int(lan_table, 'chunk_radius') or headless_loader.chunk_radius,
        connect_timeout_ms=_optional_positive_int(lan_table, 'connect_timeout_ms') or 20000,
    )

    storage = StorageConfig(
        data_dir=resolve_repo_path(base_dir, _require_str(storage_table, 'data_dir')),
        cache_dir=resolve_repo_path(base_dir, _require_str(storage_table, 'cache_dir')),
        output_dir=resolve_repo_path(base_dir, _require_str(storage_table, 'output_dir')),
    )

    bounds_min_x = _optional_int(render_table, 'min_x')
    bounds_max_x = _optional_int(render_table, 'max_x')
    bounds_min_z = _optional_int(render_table, 'min_z')
    bounds_max_z = _optional_int(render_table, 'max_z')
    explicit_bounds = (bounds_min_x, bounds_max_x, bounds_min_z, bounds_max_z)
    if any(value is not None for value in explicit_bounds) and not all(
        value is not None for value in explicit_bounds
    ):
        raise ValueError(
            '[render] min_x, max_x, min_z, and max_z must be provided together.'
        )
    if all(value is None for value in explicit_bounds):
        village_margin = _optional_int_default(
            _optional_nonnegative_int(render_table, 'village_margin'),
            0,
        )
        village_bounds = _load_village_render_bounds(base_dir, village_margin)
        if village_bounds is not None:
            bounds_min_x, bounds_max_x, bounds_min_z, bounds_max_z = village_bounds

    render = RenderAreaConfig(
        center_label=_require_str(render_table, 'center_label'),
        center_x=_require_int(render_table, 'center_x'),
        center_z=_require_int(render_table, 'center_z'),
        radius=_require_positive_int(render_table, 'radius'),
        sample_step=_require_positive_int(render_table, 'sample_step'),
        bounds_min_x=bounds_min_x,
        bounds_max_x=bounds_max_x,
        bounds_min_z=bounds_min_z,
        bounds_max_z=bounds_max_z,
    )
    if render.min_x > render.max_x:
        raise ValueError('[render] min_x must be less than or equal to max_x.')
    if render.min_z > render.max_z:
        raise ValueError('[render] min_z must be less than or equal to max_z.')

    return WorldgenConfig(
        config_path=resolved_config_path,
        project_name=_require_str(project_table, 'name'),
        compose_path=compose_path,
        world=world,
        headless_loader=headless_loader,
        lan=lan,
        storage=storage,
        render=render,
    )


def _require_table(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f'Expected [{key}] table in config.')
    return value


def _optional_table(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f'Expected [{key}] table when provided.')
    return value


def _require_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Expected "{key}" to be a non-empty string.')
    return value


def _require_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f'Expected "{key}" to be an integer.')
    return value


def _require_positive_int(data: dict[str, object], key: str) -> int:
    value = _require_int(data, key)
    if value <= 0:
        raise ValueError(f'Expected "{key}" to be greater than zero.')
    return value


def _require_nonnegative_int(data: dict[str, object], key: str) -> int:
    value = _require_int(data, key)
    if value < 0:
        raise ValueError(f'Expected "{key}" to be zero or greater.')
    return value


def _optional_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Expected "{key}" to be a non-empty string when provided.')
    return value


def _optional_bool(data: dict[str, object], key: str, default: bool) -> bool:
    value = data.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'true', 'yes', '1', 'on'}:
            return True
        if normalized in {'false', 'no', '0', 'off'}:
            return False
    raise ValueError(f'Expected "{key}" to be a boolean.')


def _optional_int(data: dict[str, object], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f'Expected "{key}" to be an integer when provided.')
    return value


def _optional_positive_int(data: dict[str, object], key: str) -> int | None:
    if key not in data:
        return None
    return _require_positive_int(data, key)


def _optional_nonnegative_int(data: dict[str, object], key: str) -> int | None:
    if key not in data:
        return None
    return _require_nonnegative_int(data, key)


def _optional_int_default(value: int | None, default: int) -> int:
    return default if value is None else value


def _load_village_render_bounds(base_dir: Path, margin: int) -> tuple[int, int, int, int] | None:
    network_path = base_dir / 'docs' / 'metro_network.json'
    if not network_path.exists():
        return None
    payload = json.loads(network_path.read_text(encoding='utf-8'))
    stops = payload.get('stops') if isinstance(payload, dict) else None
    if not isinstance(stops, list):
        raise ValueError('Expected metro_network.json to contain a "stops" list.')

    coordinates: list[tuple[int, int]] = []
    for index, stop in enumerate(stops):
        if not isinstance(stop, dict):
            raise ValueError(f'Expected stop {index} in metro_network.json to be an object.')
        x = stop.get('x')
        y = stop.get('y')
        if not isinstance(x, int) or isinstance(x, bool):
            raise ValueError(f'Expected stop {index} in metro_network.json to have an integer "x".')
        if not isinstance(y, int) or isinstance(y, bool):
            raise ValueError(f'Expected stop {index} in metro_network.json to have an integer "y".')
        coordinates.append((x, y))

    if not coordinates:
        return None

    xs = [x for x, _ in coordinates]
    ys = [y for _, y in coordinates]
    return min(xs) - margin, max(xs) + margin, min(ys) - margin, max(ys) + margin


def _server_bool_property(value: str | None, default: str) -> str:
    raw_value = value or default
    normalized = raw_value.strip().lower()
    if normalized not in {'true', 'false'}:
        raise ValueError(f'Expected server boolean property to be "true" or "false", got {raw_value!r}.')
    return normalized
