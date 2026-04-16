from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass(frozen=True, slots=True)
class WorldCacheRecord:
    project_name: str
    image: str
    seed: str
    level_name: str
    world_path: str
    data_dir: str
    prepared_at: str
    render_center_label: str
    render_center_x: int
    render_center_z: int
    render_radius: int
    render_sample_step: int


def load_world_cache(path: Path) -> WorldCacheRecord | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding='utf-8'))
    return WorldCacheRecord(**payload)


def save_world_cache(path: Path, record: WorldCacheRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + '\n', encoding='utf-8')
