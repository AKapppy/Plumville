from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_FILE = 'worldgen_config.toml'
DEFAULT_COMPOSE_FILE = 'docker-compose.worldgen.yml'
RUNTIME_DIR_NAME = '.worldgen'
ENV_FILE_NAME = 'bedrock.env'
WORLD_CACHE_FILE_NAME = 'world_cache.json'
RENDER_PLAN_FILE_NAME = 'render_plan.json'
RENDER_CACHE_FILE_NAME = 'render_cache.json'
RENDER_IMAGE_FILE_NAME = 'blackport_topdown.png'
DOCS_ASSETS_DIR_NAME = 'assets'
DOCS_DIR_NAME = 'docs'


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    repo_root: Path
    config_path: Path
    compose_path: Path
    runtime_dir: Path
    env_file: Path
    data_dir: Path
    cache_dir: Path
    output_dir: Path
    world_cache_path: Path
    render_plan_path: Path
    render_cache_path: Path
    render_image_path: Path
    docs_assets_dir: Path
    docs_render_image_path: Path

    def ensure_runtime_dirs(self) -> None:
        for directory in (
            self.runtime_dir,
            self.data_dir,
            self.cache_dir,
            self.output_dir,
            self.docs_assets_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_config_path() -> Path:
    return repo_root() / DEFAULT_CONFIG_FILE


def default_compose_path() -> Path:
    return repo_root() / DEFAULT_COMPOSE_FILE


def resolve_repo_path(base_dir: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()
