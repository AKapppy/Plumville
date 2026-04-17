from __future__ import annotations

import json
import math
import shutil
import struct
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator


SUBCHUNK_PREFIX_TAG = 0x2F
OVERWORLD_DIMENSION_ID = 0
SUBCHUNK_BLOCK_COUNT = 16 * 16 * 16
SUPPORTED_BITS_PER_BLOCK = frozenset((0, 1, 2, 3, 4, 5, 6, 8, 16))
AIR_BLOCK_NAMES = frozenset((
    'air',
    'cave_air',
    'void_air',
    'minecraft:air',
    'minecraft:cave_air',
    'minecraft:void_air',
    'minecraft:light_block',
    'minecraft:structure_void',
))


class BedrockChunkError(RuntimeError):
    pass


class LevelDbDependencyError(BedrockChunkError):
    pass


class LevelDbReadError(BedrockChunkError):
    pass


class ChunkDecodeError(BedrockChunkError):
    pass


@dataclass(frozen=True, slots=True)
class BlockInfo:
    name: str
    storage_index: int
    palette_index: int
    runtime_id: int | None
    bits_per_block: int
    palette_size: int
    storage_header_byte: int | None = None
    palette_entry: BlockPaletteEntry | None = None


@dataclass(frozen=True, slots=True)
class BlockPaletteEntry:
    block_name: str
    raw_bytes: bytes
    decoded_payload: Any
    decoded_states: Any | None = None
    runtime_id: int | None = None
    decode_error: str | None = None


@dataclass(frozen=True, slots=True)
class SubchunkRecord:
    chunk_x: int
    chunk_z: int
    subchunk_y: int
    payload: bytes
    uses_runtime_palette: bool = False
    raw_key: bytes | None = None
    dimension_id: int | None = OVERWORLD_DIMENSION_ID
    record_source: str = 'leveldb'


@dataclass(frozen=True, slots=True)
class BlockStorage:
    header_byte: int
    bits_per_block: int
    words: tuple[int, ...]
    palette: tuple[str, ...]
    runtime_ids: tuple[int | None, ...] = ()
    palette_entries: tuple[BlockPaletteEntry, ...] = ()
    raw_bytes: bytes = b''

    def raw_palette_index_for_block(self, block_index: int) -> int | None:
        if block_index < 0 or block_index >= SUBCHUNK_BLOCK_COUNT or not self.palette:
            return None
        if self.bits_per_block == 0:
            return 0

        entries_per_word = 32 // self.bits_per_block
        word_index = block_index // entries_per_word
        if word_index >= len(self.words):
            return None

        return (
            self.words[word_index] >> ((block_index % entries_per_word) * self.bits_per_block)
        ) & ((1 << self.bits_per_block) - 1)

    def palette_index_for_block(self, block_index: int) -> int | None:
        palette_index = self.raw_palette_index_for_block(block_index)
        if palette_index is None:
            return None
        if palette_index >= len(self.palette):
            return None
        return palette_index

    def block_name(self, block_index: int) -> str | None:
        palette_index = self.palette_index_for_block(block_index)
        if palette_index is None:
            return None
        return self.palette[palette_index]

    def block_info(self, block_index: int, *, storage_index: int) -> BlockInfo | None:
        palette_index = self.palette_index_for_block(block_index)
        if palette_index is None:
            return None
        runtime_id = (
            self.runtime_ids[palette_index]
            if palette_index < len(self.runtime_ids)
            else None
        )
        return BlockInfo(
            name=self.palette[palette_index],
            storage_index=storage_index,
            palette_index=palette_index,
            runtime_id=runtime_id,
            bits_per_block=self.bits_per_block,
            palette_size=len(self.palette),
            storage_header_byte=self.header_byte,
            palette_entry=(
                self.palette_entries[palette_index]
                if palette_index < len(self.palette_entries)
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class DecodedSubchunk:
    chunk_x: int
    chunk_z: int
    subchunk_y: int
    storages: tuple[BlockStorage, ...]
    uses_runtime_palette: bool = False
    subchunk_version: int | None = None
    storage_count: int | None = None
    raw_key: bytes | None = None
    raw_payload: bytes = b''
    dimension_id: int | None = OVERWORLD_DIMENSION_ID
    record_source: str = 'leveldb'

    @property
    def min_y(self) -> int:
        return self.subchunk_y * 16

    @property
    def max_y(self) -> int:
        return self.min_y + 15

    def visible_block_name(self, local_x: int, local_y: int, local_z: int) -> str | None:
        block_info = self.visible_block_info(local_x, local_y, local_z)
        if block_info is None:
            return None
        return block_info.name

    def visible_block_info(self, local_x: int, local_y: int, local_z: int) -> BlockInfo | None:
        block_index = (local_x << 8) | (local_z << 4) | local_y
        for storage_index, storage in enumerate(self.storages):
            block_info = storage.block_info(block_index, storage_index=storage_index)
            if block_info is not None and is_visible_block(block_info.name):
                return block_info
        return None


def is_visible_block(block_name: str) -> bool:
    return block_name.strip().lower() not in AIR_BLOCK_NAMES


def iter_subchunk_records(
    world_path: Path,
    *,
    min_chunk_x: int,
    max_chunk_x: int,
    min_chunk_z: int,
    max_chunk_z: int,
) -> Iterator[SubchunkRecord]:
    db_path = world_path / 'db'
    if not db_path.exists():
        raise FileNotFoundError(f'Bedrock LevelDB folder not found: {db_path}')

    try:
        import plyvel  # type: ignore[import-not-found]
    except ImportError as exc:
        raise LevelDbDependencyError(
            'Reading Bedrock chunk data requires the optional Python package `plyvel`. '
            'On macOS, install LevelDB first with `brew install leveldb`, then run '
            '`python3 -m pip install plyvel`.'
        ) from exc

    try:
        yield from _iter_leveldb_subchunk_records(
            plyvel,
            db_path,
            min_chunk_x=min_chunk_x,
            max_chunk_x=max_chunk_x,
            min_chunk_z=min_chunk_z,
            max_chunk_z=max_chunk_z,
        )
    except LevelDbReadError:
        yield from _iter_repaired_leveldb_subchunk_records(
            plyvel,
            db_path,
            min_chunk_x=min_chunk_x,
            max_chunk_x=max_chunk_x,
            min_chunk_z=min_chunk_z,
            max_chunk_z=max_chunk_z,
        )

    lost_dir = db_path / 'lost'
    if lost_dir.exists():
        yield from _iter_repaired_lost_subchunk_records(
            plyvel,
            lost_dir,
            min_chunk_x=min_chunk_x,
            max_chunk_x=max_chunk_x,
            min_chunk_z=min_chunk_z,
            max_chunk_z=max_chunk_z,
        )


def _iter_leveldb_subchunk_records(
    plyvel: Any,
    db_path: Path,
    *,
    min_chunk_x: int,
    max_chunk_x: int,
    min_chunk_z: int,
    max_chunk_z: int,
    record_source: str = 'leveldb',
) -> Iterator[SubchunkRecord]:
    db = None
    try:
        db = plyvel.DB(str(db_path), create_if_missing=False)
        for key, payload in db:
            key_parts = _parse_subchunk_key(key)
            if key_parts is None:
                continue
            chunk_x, chunk_z, dimension_id, subchunk_y = key_parts
            if not (min_chunk_x <= chunk_x <= max_chunk_x):
                continue
            if not (min_chunk_z <= chunk_z <= max_chunk_z):
                continue
            yield SubchunkRecord(
                chunk_x=chunk_x,
                chunk_z=chunk_z,
                subchunk_y=subchunk_y,
                payload=bytes(payload),
                raw_key=bytes(key),
                dimension_id=dimension_id,
                record_source=record_source,
            )
    except Exception as exc:
        raise LevelDbReadError(
            'Could not read Bedrock LevelDB chunk data. If the Bedrock server is stopped '
            'and this started after loading chunks, run `python3 -m worldgen repair-db` '
            'to back up and repair the LevelDB folder, then render again.'
        ) from exc
    finally:
        if db is not None:
            db.close()


def _iter_repaired_lost_subchunk_records(
    plyvel: Any,
    lost_dir: Path,
    *,
    min_chunk_x: int,
    max_chunk_x: int,
    min_chunk_z: int,
    max_chunk_z: int,
) -> Iterator[SubchunkRecord]:
    table_paths = tuple(sorted((*lost_dir.glob('*.ldb'), *lost_dir.glob('*.sst'))))
    if not table_paths:
        return

    with tempfile.TemporaryDirectory(prefix='metro-worldgen-lost-leveldb-') as tmp_dir:
        tmp_db_path = Path(tmp_dir)
        for table_path in table_paths:
            shutil.copy2(table_path, tmp_db_path / table_path.name)
        try:
            plyvel.repair_db(str(tmp_db_path))
        except Exception:
            return
        yield from _iter_leveldb_subchunk_records(
            plyvel,
            tmp_db_path,
            min_chunk_x=min_chunk_x,
            max_chunk_x=max_chunk_x,
            min_chunk_z=min_chunk_z,
            max_chunk_z=max_chunk_z,
            record_source='leveldb-lost-table-repair',
        )


def _iter_repaired_leveldb_subchunk_records(
    plyvel: Any,
    db_path: Path,
    *,
    min_chunk_x: int,
    max_chunk_x: int,
    min_chunk_z: int,
    max_chunk_z: int,
) -> Iterator[SubchunkRecord]:
    with tempfile.TemporaryDirectory(prefix='metro-worldgen-leveldb-repair-') as tmp_dir:
        tmp_db_path = Path(tmp_dir)
        for source_path in db_path.iterdir():
            if source_path.is_file():
                shutil.copy2(source_path, tmp_db_path / source_path.name)
        try:
            plyvel.repair_db(str(tmp_db_path))
        except Exception as exc:
            raise LevelDbReadError(
                'Could not read or repair a temporary copy of the Bedrock LevelDB chunk data.'
            ) from exc
        yield from _iter_leveldb_subchunk_records(
            plyvel,
            tmp_db_path,
            min_chunk_x=min_chunk_x,
            max_chunk_x=max_chunk_x,
            min_chunk_z=min_chunk_z,
            max_chunk_z=max_chunk_z,
            record_source='leveldb-repaired-copy',
        )


def decode_subchunk(record: SubchunkRecord) -> DecodedSubchunk:
    reader = _BinaryReader(record.payload)
    try:
        return _read_decoded_subchunk(
            reader,
            chunk_x=record.chunk_x,
            chunk_z=record.chunk_z,
            fallback_subchunk_y=record.subchunk_y,
            uses_runtime_palette=record.uses_runtime_palette,
            raw_key=record.raw_key,
            dimension_id=record.dimension_id,
            record_source=record.record_source,
        )
    except (IndexError, struct.error, ValueError) as exc:
        raise ChunkDecodeError(
            f'Could not decode subchunk {record.chunk_x}, {record.chunk_z}, {record.subchunk_y}.'
        ) from exc


def iter_packet_subchunk_records(
    *,
    chunk_x: int,
    chunk_z: int,
    sub_chunk_count: int,
    payload: bytes,
) -> Iterator[SubchunkRecord]:
    if sub_chunk_count <= 0 or not payload:
        return

    reader = _BinaryReader(payload)
    for fallback_subchunk_y in range(sub_chunk_count):
        payload_start = reader.offset
        try:
            decoded_subchunk = _read_decoded_subchunk(
                reader,
                chunk_x=chunk_x,
                chunk_z=chunk_z,
                fallback_subchunk_y=fallback_subchunk_y,
                uses_runtime_palette=True,
                raw_key=None,
                dimension_id=OVERWORLD_DIMENSION_ID,
                record_source='network-level-chunk',
            )
        except (IndexError, struct.error, ValueError) as exc:
            raise ChunkDecodeError(
                f'Could not decode network chunk {chunk_x}, {chunk_z}, subchunk {fallback_subchunk_y}.'
            ) from exc
        payload_end = reader.offset
        yield SubchunkRecord(
            chunk_x=chunk_x,
            chunk_z=chunk_z,
            subchunk_y=decoded_subchunk.subchunk_y,
            payload=payload[payload_start:payload_end],
            uses_runtime_palette=True,
            dimension_id=OVERWORLD_DIMENSION_ID,
            record_source='network-level-chunk',
        )


def _read_decoded_subchunk(
    reader: _BinaryReader,
    *,
    chunk_x: int,
    chunk_z: int,
    fallback_subchunk_y: int,
    uses_runtime_palette: bool,
    raw_key: bytes | None,
    dimension_id: int | None,
    record_source: str,
) -> DecodedSubchunk:
    version = reader.read_u8()
    subchunk_y = fallback_subchunk_y

    if version == 9:
        storage_count = reader.read_u8()
        subchunk_y = reader.read_i8()
    elif version == 8:
        storage_count = reader.read_u8()
    elif version == 1:
        storage_count = 1
    else:
        raise ChunkDecodeError(f'Unsupported subchunk version {version}.')

    if storage_count < 1 or storage_count > 4:
        raise ChunkDecodeError(f'Unexpected subchunk storage count {storage_count}.')

    storages = tuple(
        _read_block_storage(reader, uses_runtime_palette=uses_runtime_palette)
        for _index in range(storage_count)
    )

    return DecodedSubchunk(
        chunk_x=chunk_x,
        chunk_z=chunk_z,
        subchunk_y=subchunk_y,
        storages=storages,
        uses_runtime_palette=uses_runtime_palette,
        subchunk_version=version,
        storage_count=storage_count,
        raw_key=raw_key,
        raw_payload=reader.data,
        dimension_id=dimension_id,
        record_source=record_source,
    )


def _parse_subchunk_key(key: bytes) -> tuple[int, int, int, int] | None:
    if len(key) == 10 and key[8] == SUBCHUNK_PREFIX_TAG:
        return (
            struct.unpack_from('<i', key, 0)[0],
            struct.unpack_from('<i', key, 4)[0],
            OVERWORLD_DIMENSION_ID,
            struct.unpack_from('<b', key, 9)[0],
        )
    if len(key) == 14 and key[12] == SUBCHUNK_PREFIX_TAG:
        dimension_id = struct.unpack_from('<i', key, 8)[0]
        if dimension_id != OVERWORLD_DIMENSION_ID:
            return None
        return (
            struct.unpack_from('<i', key, 0)[0],
            struct.unpack_from('<i', key, 4)[0],
            dimension_id,
            struct.unpack_from('<b', key, 13)[0],
        )
    return None


def _read_block_storage(reader: _BinaryReader, *, uses_runtime_palette: bool) -> BlockStorage:
    storage_start_offset = reader.offset
    header = reader.read_u8()
    bits_per_block = header >> 1
    if bits_per_block not in SUPPORTED_BITS_PER_BLOCK:
        raise ChunkDecodeError(f'Unsupported bits-per-block value {bits_per_block}.')

    if bits_per_block == 0:
        words: tuple[int, ...] = ()
    else:
        entries_per_word = 32 // bits_per_block
        word_count = math.ceil(SUBCHUNK_BLOCK_COUNT / entries_per_word)
        words = tuple(reader.read_u32() for _index in range(word_count))

    if uses_runtime_palette:
        # Network/runtime palettes pack the entry count into the upper bits of the
        # varint, leaving the low bit for palette-format flags.
        palette_count = reader.read_varint() >> 1
        if palette_count < 1 or palette_count > SUBCHUNK_BLOCK_COUNT:
            raise ChunkDecodeError(f'Unexpected runtime palette count {palette_count}.')
        runtime_entry_values = tuple(
            reader.read_varint_with_bytes() for _index in range(palette_count)
        )
        runtime_ids = tuple(runtime_id for runtime_id, _raw_bytes in runtime_entry_values)
        palette = tuple(_runtime_block_name(runtime_id) for runtime_id in runtime_ids)
        palette_entries = tuple(
            BlockPaletteEntry(
                block_name=palette[index],
                raw_bytes=raw_bytes,
                decoded_payload={'runtime_id': runtime_id},
                runtime_id=runtime_id,
            )
            for index, (runtime_id, raw_bytes) in enumerate(runtime_entry_values)
        )
    else:
        palette_count = reader.read_i32()
        if palette_count < 1 or palette_count > SUBCHUNK_BLOCK_COUNT:
            raise ChunkDecodeError(f'Unexpected palette count {palette_count}.')
        palette_entries = tuple(_read_palette_entry(reader) for _index in range(palette_count))
        palette = tuple(entry.block_name for entry in palette_entries)
        runtime_ids = tuple(None for _index in range(palette_count))
    return BlockStorage(
        header_byte=header,
        bits_per_block=bits_per_block,
        words=words,
        palette=palette,
        runtime_ids=runtime_ids,
        palette_entries=palette_entries,
        raw_bytes=reader.data[storage_start_offset:reader.offset],
    )


def _runtime_block_name(runtime_id: int) -> str:
    runtime_names = _runtime_block_names()
    if 0 <= runtime_id < len(runtime_names):
        return runtime_names[runtime_id]
    return f'minecraft:unknown_runtime_{runtime_id}'


@lru_cache(maxsize=1)
def _runtime_block_names() -> tuple[str, ...]:
    names: list[str] = []
    for block_state in _runtime_block_states():
        name = block_state.get('name') if isinstance(block_state, dict) else None
        if not isinstance(name, str) or not name:
            names.append('minecraft:unknown')
        elif name.startswith('minecraft:'):
            names.append(name)
        else:
            names.append(f'minecraft:{name}')
    return tuple(names)


@lru_cache(maxsize=1)
def _runtime_block_states() -> tuple[dict[str, Any], ...]:
    block_states_path = (
        Path(__file__).resolve().parent.parent
        / 'node_modules'
        / 'minecraft-data'
        / 'minecraft-data'
        / 'data'
        / 'bedrock'
        / '1.21.0'
        / 'blockStates.json'
    )
    try:
        block_states = json.loads(block_states_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(block_states, list):
        return ()
    return tuple(item for item in block_states if isinstance(item, dict))


def lookup_runtime_block_state(runtime_id: int | None) -> dict[str, Any]:
    lookup: dict[str, Any] = {
        'dataset': 'minecraft-data bedrock 1.21.0 blockStates.json',
        'input': {'runtime_id': runtime_id},
        'entry_count': len(_runtime_block_states()),
        'matched': False,
        'result': None,
    }
    if runtime_id is None:
        return lookup
    block_states = _runtime_block_states()
    if 0 <= runtime_id < len(block_states):
        lookup['matched'] = True
        lookup['result'] = block_states[runtime_id]
    return lookup


def lookup_persistent_block_state(block_name: str | None, states: Any) -> dict[str, Any]:
    lookup_input = {
        'name': _normalize_block_name(block_name) if block_name else block_name,
        'states': _normalize_nbt_for_lookup(states),
    }
    lookup: dict[str, Any] = {
        'dataset': 'minecraft-data bedrock 1.21.0 blockStates.json',
        'input': lookup_input,
        'entry_count': len(_runtime_block_states()),
        'matched': False,
        'runtime_id': None,
        'result': None,
    }
    name = lookup_input['name']
    if not isinstance(name, str):
        return lookup
    key = (
        name,
        json.dumps(lookup_input['states'] or {}, sort_keys=True, separators=(',', ':')),
    )
    match = _persistent_block_state_lookup().get(key)
    if match is None:
        return lookup
    runtime_id, block_state = match
    lookup['matched'] = True
    lookup['runtime_id'] = runtime_id
    lookup['result'] = block_state
    return lookup


@lru_cache(maxsize=1)
def _persistent_block_state_lookup() -> dict[tuple[str, str], tuple[int, dict[str, Any]]]:
    lookup: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
    for runtime_id, block_state in enumerate(_runtime_block_states()):
        name = block_state.get('name')
        if not isinstance(name, str):
            continue
        normalized_name = _normalize_block_name(name)
        if normalized_name is None:
            continue
        states = block_state.get('states')
        key = (
            normalized_name,
            json.dumps(_normalize_nbt_for_lookup(states or {}), sort_keys=True, separators=(',', ':')),
        )
        lookup.setdefault(key, (runtime_id, block_state))
    return lookup


def _read_palette_entry(reader: _BinaryReader) -> BlockPaletteEntry:
    start_offset = reader.offset
    payload = _read_nbt_root_compound(reader)
    block_name = payload.get('name') or payload.get('Name')
    if not isinstance(block_name, str) or not block_name:
        block_name = 'minecraft:unknown'
    states = payload.get('states')
    if states is None:
        states = payload.get('States')
    return BlockPaletteEntry(
        block_name=block_name,
        raw_bytes=reader.data[start_offset:reader.offset],
        decoded_payload=payload,
        decoded_states=states,
    )


def _normalize_block_name(block_name: str | None) -> str | None:
    if block_name is None:
        return None
    return block_name if block_name.startswith('minecraft:') else f'minecraft:{block_name}'


def _normalize_nbt_for_lookup(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize_nbt_for_lookup(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalize_nbt_for_lookup(item) for item in value]
    if isinstance(value, bytes):
        return list(value)
    return value


def _read_nbt_root_compound(reader: _BinaryReader) -> dict[str, Any]:
    tag_id = reader.read_u8()
    if tag_id != 10:
        raise ChunkDecodeError(f'Expected root NBT compound, found tag {tag_id}.')
    reader.read_string()
    return _read_nbt_compound_payload(reader)


def _read_nbt_compound_payload(reader: _BinaryReader) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    while True:
        tag_id = reader.read_u8()
        if tag_id == 0:
            return payload
        name = reader.read_string()
        payload[name] = _read_nbt_payload(reader, tag_id)


def _read_nbt_payload(reader: _BinaryReader, tag_id: int) -> Any:
    if tag_id == 1:
        return reader.read_i8()
    if tag_id == 2:
        return reader.read_i16()
    if tag_id == 3:
        return reader.read_i32()
    if tag_id == 4:
        return reader.read_i64()
    if tag_id == 5:
        return reader.read_f32()
    if tag_id == 6:
        return reader.read_f64()
    if tag_id == 7:
        return reader.read_bytes(_read_nonnegative_length(reader))
    if tag_id == 8:
        return reader.read_string()
    if tag_id == 9:
        child_tag_id = reader.read_u8()
        length = _read_nonnegative_length(reader)
        return tuple(_read_nbt_payload(reader, child_tag_id) for _index in range(length))
    if tag_id == 10:
        return _read_nbt_compound_payload(reader)
    if tag_id == 11:
        return tuple(reader.read_i32() for _index in range(_read_nonnegative_length(reader)))
    if tag_id == 12:
        return tuple(reader.read_i64() for _index in range(_read_nonnegative_length(reader)))
    raise ChunkDecodeError(f'Unsupported NBT tag {tag_id}.')


def _read_nonnegative_length(reader: _BinaryReader) -> int:
    length = reader.read_i32()
    if length < 0:
        raise ChunkDecodeError(f'Negative NBT length {length}.')
    return length


class _BinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def read_bytes(self, size: int) -> bytes:
        if size < 0 or self.offset + size > len(self.data):
            raise IndexError('Read past end of chunk data.')
        value = self.data[self.offset:self.offset + size]
        self.offset += size
        return value

    def read_u8(self) -> int:
        return self._unpack('<B', 1)

    def read_i8(self) -> int:
        return self._unpack('<b', 1)

    def read_i16(self) -> int:
        return self._unpack('<h', 2)

    def read_i32(self) -> int:
        return self._unpack('<i', 4)

    def read_i64(self) -> int:
        return self._unpack('<q', 8)

    def read_u32(self) -> int:
        return self._unpack('<I', 4)

    def read_f32(self) -> float:
        return self._unpack('<f', 4)

    def read_f64(self) -> float:
        return self._unpack('<d', 8)

    def read_string(self) -> str:
        size = self._unpack('<H', 2)
        return self.read_bytes(size).decode('utf-8')

    def read_varint(self) -> int:
        value = 0
        shift = 0
        for _index in range(5):
            byte = self.read_u8()
            value |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                if value & (1 << 31):
                    value -= 1 << 32
                return value
            shift += 7
        raise ChunkDecodeError('VarInt is too long.')

    def read_varint_with_bytes(self) -> tuple[int, bytes]:
        start_offset = self.offset
        value = self.read_varint()
        return value, self.data[start_offset:self.offset]

    def _unpack(self, fmt: str, size: int) -> Any:
        if self.offset + size > len(self.data):
            raise IndexError('Read past end of chunk data.')
        value = struct.unpack_from(fmt, self.data, self.offset)[0]
        self.offset += size
        return value
