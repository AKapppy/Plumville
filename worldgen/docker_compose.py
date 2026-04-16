from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ComposeError(RuntimeError):
    pass


DOCKER_CLI_CANDIDATES = (
    Path('/Applications/Docker.app/Contents/Resources/bin/docker'),
    Path('/usr/local/bin/docker'),
    Path('/opt/homebrew/bin/docker'),
    Path.home() / '.docker/bin/docker',
)
COMPOSE_CLI_CANDIDATES = (
    Path('/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose'),
    Path('/usr/local/bin/docker-compose'),
    Path('/opt/homebrew/bin/docker-compose'),
    Path('/usr/local/lib/docker/cli-plugins/docker-compose'),
    Path('/opt/homebrew/lib/docker/cli-plugins/docker-compose'),
)


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
    return compose_command_prefix() is not None


def docker_executable() -> str | None:
    docker_path = shutil.which('docker')
    if docker_path:
        return docker_path
    for candidate in DOCKER_CLI_CANDIDATES:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def compose_command_prefix() -> tuple[str, ...] | None:
    compose_path = shutil.which('docker-compose')
    if compose_path:
        return (compose_path,)
    for candidate in COMPOSE_CLI_CANDIDATES:
        if candidate.exists() and candidate.is_file():
            return (str(candidate),)

    docker_path = docker_executable()
    if docker_path:
        return (docker_path, 'compose')
    return None


def build_compose_command(
    *,
    project_name: str,
    compose_path: Path,
    env_file: Path,
    args: list[str],
) -> list[str]:
    command_prefix = compose_command_prefix() or ('docker', 'compose')
    return [
        *command_prefix,
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
        raise ComposeError(
            'Docker Compose was not found on PATH or in the Docker Desktop app bundle.'
        ) from exc
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
        raise ComposeError(_friendly_compose_error(result))
    return result


def _friendly_compose_error(result: ComposeResult) -> str:
    output = result.combined_output or 'docker compose command failed.'
    lower_output = output.lower()
    if 'cannot connect to the docker daemon' in lower_output:
        return '\n'.join(
            (
                'Docker Desktop is installed, but the Docker daemon is not running.',
                'Open Docker Desktop and wait until it is fully started, then try Auto Fill Step again.',
                '',
                'Original Docker output:',
                output,
            )
        )
    return output
