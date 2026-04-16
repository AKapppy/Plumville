from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ComposeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ComposeResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def combined_output(self) -> str:
        parts = [part.strip() for part in (self.stdout, self.stderr) if part.strip()]
        return '\n'.join(parts)


def docker_available() -> bool:
    return shutil.which('docker') is not None


def build_compose_command(
    *,
    project_name: str,
    compose_path: Path,
    env_file: Path,
    args: list[str],
) -> list[str]:
    return [
        'docker',
        'compose',
        '-p',
        project_name,
        '-f',
        str(compose_path),
        '--env-file',
        str(env_file),
        *args,
    ]


def run_compose(
    *,
    project_name: str,
    compose_path: Path,
    env_file: Path,
    args: list[str],
    check: bool = True,
    timeout_seconds: float | None = None,
) -> ComposeResult:
    command = build_compose_command(
        project_name=project_name,
        compose_path=compose_path,
        env_file=env_file,
        args=args,
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise ComposeError('docker is not installed or is not on PATH.') from exc
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ''
        stderr = exc.stderr if isinstance(exc.stderr, str) else ''
        timeout_message = f'docker compose command timed out after {timeout_seconds} seconds.'
        result = ComposeResult(
            args=tuple(command),
            returncode=-124,
            stdout=stdout,
            stderr='\n'.join(part for part in (stderr, timeout_message) if part),
        )
        if check:
            raise ComposeError(result.combined_output or timeout_message) from exc
        return result

    result = ComposeResult(
        args=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if check and completed.returncode != 0:
        raise ComposeError(result.combined_output or 'docker compose command failed.')
    return result
