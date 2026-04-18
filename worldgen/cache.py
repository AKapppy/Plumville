from __future__ import annotations

import errno
import json
import os
import time
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
    payload = json.loads(_read_text_with_retry(path))
    return WorldCacheRecord(**payload)


def save_world_cache(path: Path, record: WorldCacheRecord) -> None:
    _write_text_atomically_with_retry(
        path,
        json.dumps(asdict(record), indent=2, sort_keys=True) + '\n',
    )


def _read_text_with_retry(
    path: Path,
    *,
    attempts: int = 5,
    retry_delay_seconds: float = 0.2,
) -> str:
    retryable_errnos = {errno.EDEADLK, errno.EAGAIN, errno.EBUSY}
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
    attempts: int = 5,
    retry_delay_seconds: float = 0.2,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    retryable_errnos = {errno.EDEADLK, errno.EAGAIN, errno.EBUSY}
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
