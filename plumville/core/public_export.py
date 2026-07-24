from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


FORBIDDEN_PUBLIC_TEXT_FRAGMENTS: tuple[str, ...] = (
    "/Users/",
    "Library/Application Support",
    "worldgen/cache",
    "worldgen/output",
    "headless_chunk_packets",
    "bedrock-data",
    "credentials",
    "backup_path",
    "backups",
    "permissions.json",
    "allowlist.json",
    "private notes",
    "internal diagnostic",
)

FORBIDDEN_PUBLIC_JSON_KEYS: frozenset[str] = frozenset({
    "private_notes",
    "internal_notes",
    "editing_state",
    "undo_data",
    "history",
    "error_logs",
    "cache_path",
    "backup_path",
    "docker_path",
    "credentials",
})

PUBLIC_TEXT_PATHS: tuple[Path, ...] = (
    Path("index.html"),
    Path("styles.css"),
    Path("app.js"),
    Path("metro_network.json"),
    Path("assets/blackport_topdown.render.json"),
)

PUBLIC_JSON_PATHS: tuple[Path, ...] = (
    Path("metro_network.json"),
    Path("assets/blackport_topdown.render.json"),
)


def validate_public_text(
    text: str,
    *,
    forbidden_fragments: Iterable[str] = FORBIDDEN_PUBLIC_TEXT_FRAGMENTS,
) -> None:
    for fragment in forbidden_fragments:
        if fragment in text:
            raise ValueError(f"Public output contains private/local text fragment: {fragment}")


def validate_public_json_keys(
    value: object,
    *,
    forbidden_keys: frozenset[str] = FORBIDDEN_PUBLIC_JSON_KEYS,
    path: tuple[str, ...] = (),
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text in forbidden_keys:
                location = ".".join((*path, key_text))
                raise ValueError(f"Public JSON contains private field: {location}")
            validate_public_json_keys(child, forbidden_keys=forbidden_keys, path=(*path, key_text))
        return

    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_public_json_keys(child, forbidden_keys=forbidden_keys, path=(*path, str(index)))


def validate_public_docs(
    docs_root: Path,
    *,
    text_paths: tuple[Path, ...] = PUBLIC_TEXT_PATHS,
    json_paths: tuple[Path, ...] = PUBLIC_JSON_PATHS,
) -> None:
    for relative_path in text_paths:
        path = docs_root / relative_path
        validate_public_text(path.read_text(encoding="utf-8"))

    for relative_path in json_paths:
        path = docs_root / relative_path
        validate_public_json_keys(json.loads(path.read_text(encoding="utf-8")), path=(str(relative_path),))


def format_byte_size(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} B"
    kibibytes = byte_count / 1024
    if kibibytes < 1024:
        return f"{kibibytes:.1f} KB"
    return f"{(kibibytes / 1024):.1f} MB"
