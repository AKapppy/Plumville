from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .bedrock_chunks import (
    SUBCHUNK_BLOCK_COUNT,
    BlockPaletteEntry,
    BlockStorage,
    ChunkDecodeError,
    DecodedSubchunk,
    SubchunkRecord,
    lookup_persistent_block_state,
    lookup_runtime_block_state,
)


MAX_UNKNOWN_SAMPLES_PER_CASE = 10
PERSISTENT_SUBCHUNK_KEY = tuple[int | None, int, int, int]
GROUPED_JSON_SAMPLE_LIMIT = 20


@dataclass(slots=True)
class UnknownCase:
    payload: dict[str, Any]
    chunks: set[tuple[int, int]] = field(default_factory=set)
    subchunk_versions: set[int] = field(default_factory=set)
    record_sources: set[str] = field(default_factory=set)
    raw_subchunk_keys: set[str] = field(default_factory=set)


class UnknownBlockDiagnostics:
    def __init__(
        self,
        *,
        world_path: Path,
        generated_at: str,
        persistent_subchunks: dict[PERSISTENT_SUBCHUNK_KEY, DecodedSubchunk] | None = None,
    ):
        self.world_path = world_path
        self.generated_at = generated_at
        self._cases: dict[str, UnknownCase] = {}
        self._persistent_subchunks = persistent_subchunks or {}

    def collect_subchunk(self, subchunk: DecodedSubchunk) -> None:
        for storage_index, storage in enumerate(subchunk.storages):
            unresolved_palette_indexes = {
                palette_index
                for palette_index, block_name in enumerate(storage.palette)
                if is_unresolved_block_name(block_name)
            }
            palette_counts, palette_samples = _palette_counts_and_samples(
                subchunk,
                storage,
                storage_index=storage_index,
                unresolved_palette_indexes=unresolved_palette_indexes,
            )

            for palette_index, occurrence_count in palette_counts.items():
                if palette_index >= len(storage.palette):
                    self._record_invalid_palette_index(
                        subchunk,
                        storage,
                        storage_index=storage_index,
                        palette_index=palette_index,
                        occurrence_count=occurrence_count,
                        samples=palette_samples.get(palette_index, []),
                    )
                    continue

                if palette_index not in unresolved_palette_indexes:
                    continue
                block_name = storage.palette[palette_index]
                palette_entry = (
                    storage.palette_entries[palette_index]
                    if palette_index < len(storage.palette_entries)
                    else None
                )
                self._record_unknown_block(
                    subchunk,
                    storage,
                    palette_entry,
                    storage_index=storage_index,
                    palette_index=palette_index,
                    block_name=block_name,
                    occurrence_count=occurrence_count,
                    samples=palette_samples.get(palette_index, []),
                )

    def record_decode_error(self, record: SubchunkRecord, error: ChunkDecodeError) -> None:
        problem_category = _decode_error_category(str(error))
        raw_key_hex = record.raw_key.hex() if record.raw_key is not None else None
        source = _decoding_source(record.uses_runtime_palette)
        unknown_label = f'decode_error:{problem_category}'
        case_key = _stable_case_key(
            {
                'unknown_label': unknown_label,
                'problem_category': problem_category,
                'source': source,
                'dimension_id': record.dimension_id,
                'chunk_x': record.chunk_x,
                'chunk_z': record.chunk_z,
                'subchunk_y': record.subchunk_y,
                'error': str(error),
                'raw_key_hex': raw_key_hex,
            }
        )
        case = self._cases.get(case_key)
        if case is None:
            case = UnknownCase(
                payload={
                    'unknown_label': unknown_label,
                    'world_path': str(self.world_path.resolve()),
                    'dimension': _dimension_label(record.dimension_id),
                    'dimension_id': record.dimension_id,
                    'chunk_x': record.chunk_x,
                    'chunk_z': record.chunk_z,
                    'subchunk_y': record.subchunk_y,
                    'subchunk_version': None,
                    'storage_index': None,
                    'storage_header_byte': None,
                    'storage_header_byte_hex': None,
                    'bits_per_block': None,
                    'palette_size': None,
                    'palette_index': None,
                    'unresolved_runtime_id': None,
                    'decoding_source': source,
                    'problem_category': problem_category,
                    'raw_palette_entry_bytes_hex': None,
                    'decoded_palette_entry': None,
                    'decoded_block_name': None,
                    'decoded_block_states': None,
                    'block_entity_data': None,
                    'block_entity_note': 'Block entity records are not decoded by this scanner.',
                    'lookup': None,
                    'decode_error': str(error),
                    'decode_failure_assessment': [_decode_error_assessment(str(error))],
                    'subchunk_debug': {
                        'raw_subchunk_key': raw_key_hex,
                        'raw_subchunk_key_bytes_hex': raw_key_hex,
                        'record_source': record.record_source,
                        'storage_count': None,
                        'is_version_8_or_9_paletted_storage': None,
                        'has_extra_block_layer': None,
                        'may_have_failed_due_to': [_decode_error_assessment(str(error))],
                    },
                    'samples': [],
                    'total_occurrence_count': 0,
                    'unique_chunk_count': 0,
                }
            )
            self._cases[case_key] = case
        self._increment_case(
            case,
            occurrence_count=1,
            chunk_x=record.chunk_x,
            chunk_z=record.chunk_z,
            subchunk_version=None,
            record_source=record.record_source,
            raw_subchunk_key=raw_key_hex,
            sample={
                'world_x': None,
                'world_y': None,
                'world_z': None,
                'chunk_x': record.chunk_x,
                'chunk_z': record.chunk_z,
                'subchunk_y': record.subchunk_y,
                'local_x': None,
                'local_y': None,
                'local_z': None,
            },
        )

    def _record_unknown_block(
        self,
        subchunk: DecodedSubchunk,
        storage: BlockStorage,
        palette_entry: BlockPaletteEntry | None,
        *,
        storage_index: int,
        palette_index: int,
        block_name: str,
        occurrence_count: int,
        samples: list[dict[str, Any]],
    ) -> None:
        source = _decoding_source(subchunk.uses_runtime_palette)
        runtime_id = palette_entry.runtime_id if palette_entry is not None else None
        problem_category = (
            'unknown_runtime_mapping'
            if subchunk.uses_runtime_palette
            else 'unknown_raw_persistent_block_name_or_states'
        )
        decoded_states = palette_entry.decoded_states if palette_entry is not None else None
        lookup = (
            lookup_runtime_block_state(runtime_id)
            if subchunk.uses_runtime_palette
            else lookup_persistent_block_state(block_name, decoded_states)
        )
        runtime_resolution = _runtime_resolution_payload(runtime_id, lookup, subchunk.uses_runtime_palette)
        persistent_resolution = self._persistent_resolution_payload(
            subchunk=subchunk,
            storage_index=storage_index,
            samples=samples,
        )
        layer_heuristic = _layer_heuristic_payload(
            subchunk=subchunk,
            storage=storage,
            storage_index=storage_index,
            palette_index=palette_index,
            occurrence_count=occurrence_count,
        )
        identification_status = _identification_status(
            persistent_resolution,
            runtime_resolution,
            layer_heuristic,
        )
        raw_entry_hex = palette_entry.raw_bytes.hex() if palette_entry is not None else None
        decoded_payload = palette_entry.decoded_payload if palette_entry is not None else None
        raw_key_hex = subchunk.raw_key.hex() if subchunk.raw_key is not None else None
        case_key = _stable_case_key(
            {
                'unknown_label': block_name,
                'dimension_id': subchunk.dimension_id,
                'source': source,
                'storage_index': storage_index,
                'storage_header_byte': storage.header_byte,
                'bits_per_block': storage.bits_per_block,
                'palette_size': len(storage.palette),
                'palette_index': palette_index,
                'runtime_id': runtime_id,
                'raw_entry_hex': raw_entry_hex,
                'decoded_payload': _jsonable(decoded_payload),
                'persistent_signature': persistent_resolution.get('persistent_signature'),
                'identification_status': identification_status,
            }
        )
        case = self._cases.get(case_key)
        if case is None:
            case = UnknownCase(
                payload={
                    'unknown_label': block_name,
                    'world_path': str(self.world_path.resolve()),
                    'dimension': _dimension_label(subchunk.dimension_id),
                    'dimension_id': subchunk.dimension_id,
                    'chunk_x': subchunk.chunk_x,
                    'chunk_z': subchunk.chunk_z,
                    'subchunk_y': subchunk.subchunk_y,
                    'subchunk_version': subchunk.subchunk_version,
                    'storage_index': storage_index,
                    'storage_header_byte': storage.header_byte,
                    'storage_header_byte_hex': f'0x{storage.header_byte:02x}',
                    'bits_per_block': storage.bits_per_block,
                    'palette_size': len(storage.palette),
                    'palette_index': palette_index,
                    'unresolved_runtime_id': runtime_id,
                    'decoding_source': source,
                    'problem_category': problem_category,
                    'raw_palette_entry_bytes_hex': raw_entry_hex,
                    'decoded_palette_entry': _jsonable(decoded_payload),
                    'decoded_block_name': (
                        palette_entry.block_name if palette_entry is not None else block_name
                    ),
                    'decoded_block_states': _jsonable(decoded_states),
                    'persistent_palette_entry_bytes_hex': (
                        persistent_resolution.get('persistent_palette_entry_bytes_hex')
                    ),
                    'persistent_palette_entry_decoded': (
                        persistent_resolution.get('persistent_palette_entry_decoded')
                    ),
                    'persistent_block_name': persistent_resolution.get('persistent_block_name'),
                    'persistent_block_states': persistent_resolution.get('persistent_block_states'),
                    'persistent_legacy_val': persistent_resolution.get('persistent_legacy_val'),
                    'persistent_block_storage_payload_bytes_hex': (
                        persistent_resolution.get('persistent_block_storage_payload_bytes_hex')
                    ),
                    'persistent_subchunk_payload_bytes_hex': (
                        persistent_resolution.get('persistent_subchunk_payload_bytes_hex')
                    ),
                    'persistent_match': persistent_resolution,
                    'runtime_palette_source': runtime_resolution.get('runtime_palette_source'),
                    'runtime_palette_entry_count': runtime_resolution.get(
                        'runtime_palette_entry_count'
                    ),
                    'runtime_palette_missing': runtime_resolution.get('runtime_palette_missing'),
                    'resolved_runtime_block_name': runtime_resolution.get(
                        'resolved_runtime_block_name'
                    ),
                    'resolved_runtime_block_states': runtime_resolution.get(
                        'resolved_runtime_block_states'
                    ),
                    'identification_status': identification_status,
                    'likely_block_name': layer_heuristic.get('likely_block_name'),
                    'confidence_note': layer_heuristic.get('confidence_note'),
                    'layer_heuristic': layer_heuristic,
                    'block_entity_data': None,
                    'block_entity_note': 'Block entity records are not decoded by this scanner.',
                    'lookup': _jsonable(lookup),
                    'decode_error': None,
                    'decode_failure_assessment': _unknown_assessment(subchunk.uses_runtime_palette),
                    'subchunk_debug': _subchunk_debug_payload(subchunk, storage),
                    'samples': [],
                    'total_occurrence_count': 0,
                    'unique_chunk_count': 0,
                }
            )
            self._cases[case_key] = case
        self._increment_case(
            case,
            occurrence_count=occurrence_count,
            chunk_x=subchunk.chunk_x,
            chunk_z=subchunk.chunk_z,
            subchunk_version=subchunk.subchunk_version,
            record_source=subchunk.record_source,
            raw_subchunk_key=raw_key_hex,
            samples=samples,
        )

    def _persistent_resolution_payload(
        self,
        *,
        subchunk: DecodedSubchunk,
        storage_index: int,
        samples: list[dict[str, Any]],
    ) -> dict[str, Any]:
        base_payload: dict[str, Any] = {
            'attempted': bool(subchunk.uses_runtime_palette),
            'matched': False,
            'persistent_signature': None,
            'persistent_palette_entry_bytes_hex': None,
            'persistent_palette_entry_decoded': None,
            'persistent_block_name': None,
            'persistent_block_states': None,
            'persistent_legacy_val': None,
            'persistent_block_storage_payload_bytes_hex': None,
            'persistent_subchunk_payload_bytes_hex': None,
            'persistent_subchunk_key_bytes_hex': None,
            'persistent_record_source': None,
            'persistent_match_status': 'not_attempted',
            'persistent_match_method': None,
        }
        if not subchunk.uses_runtime_palette:
            return base_payload

        persistent_subchunk = self._persistent_subchunks.get(
            (subchunk.dimension_id, subchunk.chunk_x, subchunk.chunk_z, subchunk.subchunk_y)
        )
        if persistent_subchunk is None and subchunk.dimension_id is not None:
            persistent_subchunk = self._persistent_subchunks.get(
                (None, subchunk.chunk_x, subchunk.chunk_z, subchunk.subchunk_y)
            )
        if persistent_subchunk is None:
            base_payload['persistent_match_status'] = 'no_persistent_subchunk_record_found'
            return base_payload

        base_payload.update(
            {
                'persistent_subchunk_key_bytes_hex': (
                    persistent_subchunk.raw_key.hex()
                    if persistent_subchunk.raw_key is not None
                    else None
                ),
                'persistent_record_source': persistent_subchunk.record_source,
            }
        )

        if storage_index >= len(persistent_subchunk.storages):
            base_payload['persistent_match_status'] = 'persistent_storage_index_missing'
            return base_payload

        persistent_storage = persistent_subchunk.storages[storage_index]
        base_payload['persistent_block_storage_payload_bytes_hex'] = persistent_storage.raw_bytes.hex()
        persistent_palette_indexes: Counter[int] = Counter()
        for sample in samples:
            block_index = _sample_block_index(sample)
            if block_index is None:
                continue
            persistent_palette_index = persistent_storage.palette_index_for_block(block_index)
            if persistent_palette_index is not None:
                persistent_palette_indexes[persistent_palette_index] += 1

        if not persistent_palette_indexes:
            base_payload['persistent_match_status'] = 'no_sample_coordinate_match'
            return base_payload

        persistent_palette_index, match_count = persistent_palette_indexes.most_common(1)[0]
        if persistent_palette_index >= len(persistent_storage.palette_entries):
            base_payload['persistent_match_status'] = 'persistent_palette_entry_missing'
            return base_payload

        entry = persistent_storage.palette_entries[persistent_palette_index]
        decoded = _jsonable(entry.decoded_payload)
        states = _jsonable(entry.decoded_states)
        block_name = entry.block_name
        legacy_val = (
            entry.decoded_payload.get('val')
            if isinstance(entry.decoded_payload, dict)
            else None
        )
        signature = _stable_case_key(
            {
                'block_name': block_name,
                'states': states,
                'legacy_val': legacy_val,
                'entry_bytes': entry.raw_bytes.hex(),
            }
        )
        base_payload.update(
            {
                'matched': True,
                'persistent_signature': signature,
                'persistent_palette_entry_bytes_hex': entry.raw_bytes.hex(),
                'persistent_palette_entry_decoded': decoded,
                'persistent_block_name': block_name,
                'persistent_block_states': states,
                'persistent_legacy_val': legacy_val,
                'persistent_palette_index': persistent_palette_index,
                'persistent_sample_match_count': match_count,
                'persistent_sample_match_total': sum(persistent_palette_indexes.values()),
                'persistent_match_status': 'matched_from_sample_coordinates',
                'persistent_match_method': 'same_chunk_subchunk_storage_sample_coordinates',
            }
        )
        return base_payload

    def _record_invalid_palette_index(
        self,
        subchunk: DecodedSubchunk,
        storage: BlockStorage,
        *,
        storage_index: int,
        palette_index: int,
        occurrence_count: int,
        samples: list[dict[str, Any]],
    ) -> None:
        source = _decoding_source(subchunk.uses_runtime_palette)
        raw_key_hex = subchunk.raw_key.hex() if subchunk.raw_key is not None else None
        unknown_label = f'invalid_palette_index:{palette_index}'
        problem_category = 'invalid_palette_index'
        case_key = _stable_case_key(
            {
                'unknown_label': unknown_label,
                'dimension_id': subchunk.dimension_id,
                'source': source,
                'storage_index': storage_index,
                'storage_header_byte': storage.header_byte,
                'bits_per_block': storage.bits_per_block,
                'palette_size': len(storage.palette),
                'palette_index': palette_index,
            }
        )
        case = self._cases.get(case_key)
        if case is None:
            case = UnknownCase(
                payload={
                    'unknown_label': unknown_label,
                    'world_path': str(self.world_path.resolve()),
                    'dimension': _dimension_label(subchunk.dimension_id),
                    'dimension_id': subchunk.dimension_id,
                    'chunk_x': subchunk.chunk_x,
                    'chunk_z': subchunk.chunk_z,
                    'subchunk_y': subchunk.subchunk_y,
                    'subchunk_version': subchunk.subchunk_version,
                    'storage_index': storage_index,
                    'storage_header_byte': storage.header_byte,
                    'storage_header_byte_hex': f'0x{storage.header_byte:02x}',
                    'bits_per_block': storage.bits_per_block,
                    'palette_size': len(storage.palette),
                    'palette_index': palette_index,
                    'unresolved_runtime_id': None,
                    'decoding_source': source,
                    'problem_category': problem_category,
                    'raw_palette_entry_bytes_hex': None,
                    'decoded_palette_entry': None,
                    'decoded_block_name': None,
                    'decoded_block_states': None,
                    'block_entity_data': None,
                    'block_entity_note': 'Block entity records are not decoded by this scanner.',
                    'lookup': None,
                    'decode_error': None,
                    'decode_failure_assessment': [
                        'Palette index read from packed block data is outside the decoded palette.'
                    ],
                    'subchunk_debug': _subchunk_debug_payload(subchunk, storage),
                    'samples': [],
                    'total_occurrence_count': 0,
                    'unique_chunk_count': 0,
                }
            )
            self._cases[case_key] = case
        self._increment_case(
            case,
            occurrence_count=occurrence_count,
            chunk_x=subchunk.chunk_x,
            chunk_z=subchunk.chunk_z,
            subchunk_version=subchunk.subchunk_version,
            record_source=subchunk.record_source,
            raw_subchunk_key=raw_key_hex,
            samples=samples,
        )

    def _increment_case(
        self,
        case: UnknownCase,
        *,
        occurrence_count: int,
        chunk_x: int,
        chunk_z: int,
        subchunk_version: int | None,
        record_source: str,
        raw_subchunk_key: str | None,
        samples: list[dict[str, Any]] | None = None,
        sample: dict[str, Any] | None = None,
    ) -> None:
        case.payload['total_occurrence_count'] += occurrence_count
        case.chunks.add((chunk_x, chunk_z))
        case.payload['unique_chunk_count'] = len(case.chunks)
        if subchunk_version is not None:
            case.subchunk_versions.add(subchunk_version)
        case.record_sources.add(record_source)
        if raw_subchunk_key is not None:
            case.raw_subchunk_keys.add(raw_subchunk_key)
        sample_payloads = samples if samples is not None else ([sample] if sample is not None else [])
        for sample_payload in sample_payloads:
            if len(case.payload['samples']) >= MAX_UNKNOWN_SAMPLES_PER_CASE:
                break
            case.payload['samples'].append(sample_payload)

    def cases(self) -> list[dict[str, Any]]:
        rendered: list[dict[str, Any]] = []
        for case in self._cases.values():
            payload = dict(case.payload)
            payload['subchunk_versions_seen'] = sorted(case.subchunk_versions)
            payload['record_sources_seen'] = sorted(case.record_sources)
            payload['raw_subchunk_keys_seen'] = sorted(case.raw_subchunk_keys)[:20]
            rendered.append(payload)
        return sorted(
            rendered,
            key=lambda item: (
                -int(item.get('total_occurrence_count') or 0),
                str(item.get('unknown_label') or ''),
            ),
        )

    def write_reports(
        self,
        *,
        json_path: Path,
        csv_path: Path,
        summary_path: Path,
        persistent_candidates_path: Path | None = None,
    ) -> None:
        cases = self.cases()
        grouped_cases = self.grouped_runtime_cases()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(grouped_cases, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        _write_csv(csv_path, cases)
        _write_summary(
            summary_path,
            cases,
            generated_at=self.generated_at,
            world_path=self.world_path,
        )
        if persistent_candidates_path is not None:
            persistent_candidates = [
                case
                for case in cases
                if (
                    case.get('decoding_source') == 'runtime_decoding'
                    and case.get('identification_status') == 'identified_from_persistent_palette'
                )
            ]
            persistent_candidates_path.parent.mkdir(parents=True, exist_ok=True)
            persistent_candidates_path.write_text(
                json.dumps(persistent_candidates, indent=2, sort_keys=True) + '\n',
                encoding='utf-8',
            )

    def grouped_runtime_cases(self) -> list[dict[str, Any]]:
        groups: dict[tuple[str, Any], dict[str, Any]] = {}
        chunk_sets: dict[tuple[str, Any], set[tuple[int, int]]] = {}
        placement_sets: dict[tuple[str, Any], set[tuple[int, int]]] = {}
        subchunk_y_sets: dict[tuple[str, Any], set[int]] = {}

        for case in self._cases.values():
            payload = case.payload
            runtime_id = payload.get('unresolved_runtime_id')
            group_key = _runtime_group_key(payload)
            group = groups.get(group_key)
            if group is None:
                group = _compact_runtime_group_seed(payload, runtime_id)
                groups[group_key] = group
                chunk_sets[group_key] = set()
                placement_sets[group_key] = set()
                subchunk_y_sets[group_key] = set()

            group['total_occurrence_count'] += int(payload.get('total_occurrence_count') or 0)
            _append_unique(
                group['unknown_labels_seen'],
                payload.get('unknown_label'),
            )
            _append_unique(
                group['problem_categories_seen'],
                payload.get('problem_category'),
            )
            _append_unique(
                group['identification_statuses_seen'],
                payload.get('identification_status'),
            )
            _append_unique(
                group['decoding_sources_seen'],
                payload.get('decoding_source'),
            )
            _append_unique(
                group['raw_palette_entry_bytes_seen'],
                payload.get('raw_palette_entry_bytes_hex'),
            )
            _append_unique(
                group['decoded_block_names_seen'],
                payload.get('decoded_block_name'),
            )
            _append_unique(
                group['persistent_block_names_seen'],
                payload.get('persistent_block_name'),
            )
            _append_unique_jsonable(
                group['persistent_block_states_seen'],
                payload.get('persistent_block_states'),
            )
            _append_unique_jsonable(
                group['resolved_runtime_block_states_seen'],
                payload.get('resolved_runtime_block_states'),
            )
            _append_unique(
                group['likely_block_names_seen'],
                payload.get('likely_block_name'),
            )
            _append_unique(
                group['storage_indexes_seen'],
                payload.get('storage_index'),
            )
            _append_unique(
                group['palette_indexes_seen'],
                payload.get('palette_index'),
            )
            _append_unique(
                group['bits_per_block_seen'],
                payload.get('bits_per_block'),
            )
            _append_unique(
                group['palette_sizes_seen'],
                payload.get('palette_size'),
            )
            _append_unique(
                group['storage_header_bytes_seen'],
                payload.get('storage_header_byte'),
            )
            _extend_limited_unique(
                group['record_sources_seen'],
                case.record_sources,
            )
            _extend_limited_unique(
                group['subchunk_versions_seen'],
                case.subchunk_versions,
            )
            _extend_limited_unique(
                group['raw_subchunk_keys_seen'],
                case.raw_subchunk_keys,
                limit=20,
            )

            chunk_sets[group_key].update(case.chunks)
            placement_sets[group_key].update(case.chunks)
            subchunk_y = payload.get('subchunk_y')
            if isinstance(subchunk_y, int):
                subchunk_y_sets[group_key].add(subchunk_y)

            for sample in payload.get('samples') or ():
                _append_sample_coordinate(group['sample_coordinates'], sample)

        rendered: list[dict[str, Any]] = []
        for group_key, group in groups.items():
            group['unique_chunk_count'] = len(chunk_sets[group_key])
            group['placement_coordinate_format'] = ['chunk_x', 'chunk_z']
            group['placements'] = [
                [chunk_x, chunk_z]
                for chunk_x, chunk_z in sorted(placement_sets[group_key])
            ]
            group['subchunk_ys_seen'] = sorted(subchunk_y_sets[group_key])
            for key in (
                'unknown_labels_seen',
                'problem_categories_seen',
                'identification_statuses_seen',
                'decoding_sources_seen',
                'raw_palette_entry_bytes_seen',
                'decoded_block_names_seen',
                'persistent_block_names_seen',
                'persistent_block_states_seen',
                'resolved_runtime_block_states_seen',
                'likely_block_names_seen',
                'storage_indexes_seen',
                'palette_indexes_seen',
                'bits_per_block_seen',
                'palette_sizes_seen',
                'storage_header_bytes_seen',
                'record_sources_seen',
                'subchunk_versions_seen',
                'raw_subchunk_keys_seen',
            ):
                group[key] = sorted(
                    group[key],
                    key=lambda value: json.dumps(_jsonable(value), sort_keys=True),
                )
            rendered.append(group)

        return sorted(
            rendered,
            key=lambda item: (
                -int(item.get('total_occurrence_count') or 0),
                str(item.get('runtime_id') if item.get('runtime_id') is not None else item.get('group_key')),
            ),
        )


def is_unresolved_block_name(block_name: str) -> bool:
    name = block_name.strip().lower()
    if name in ('unknown', 'minecraft:unknown'):
        return True
    return name.startswith('unknown_runtime_') or name.startswith('minecraft:unknown_runtime_')


def _runtime_group_key(case: dict[str, Any]) -> tuple[str, Any]:
    runtime_id = case.get('unresolved_runtime_id')
    if runtime_id is not None:
        return ('runtime_id', runtime_id)
    return (
        'case',
        _stable_case_key(
            {
                'unknown_label': case.get('unknown_label'),
                'problem_category': case.get('problem_category'),
                'dimension_id': case.get('dimension_id'),
                'decoding_source': case.get('decoding_source'),
                'decode_error': case.get('decode_error'),
            }
        ),
    )


def _compact_runtime_group_seed(
    case: dict[str, Any],
    runtime_id: Any,
) -> dict[str, Any]:
    lookup = case.get('lookup') if isinstance(case.get('lookup'), dict) else None
    persistent_match = (
        _compact_persistent_match(case.get('persistent_match'))
        if isinstance(case.get('persistent_match'), dict)
        else None
    )
    return {
        'group_key': str(runtime_id) if runtime_id is not None else _runtime_group_key(case)[1],
        'runtime_id': runtime_id,
        'unknown_label': case.get('unknown_label'),
        'world_path': case.get('world_path'),
        'dimension': case.get('dimension'),
        'dimension_id': case.get('dimension_id'),
        'problem_category': case.get('problem_category'),
        'decoding_source': case.get('decoding_source'),
        'decoded_palette_entry': case.get('decoded_palette_entry'),
        'decoded_block_name': case.get('decoded_block_name'),
        'decoded_block_states': case.get('decoded_block_states'),
        'lookup': lookup,
        'persistent_match': persistent_match,
        'runtime_palette_source': case.get('runtime_palette_source'),
        'runtime_palette_entry_count': case.get('runtime_palette_entry_count'),
        'runtime_palette_missing': case.get('runtime_palette_missing'),
        'resolved_runtime_block_name': case.get('resolved_runtime_block_name'),
        'identification_status': case.get('identification_status'),
        'likely_block_name': case.get('likely_block_name'),
        'confidence_note': case.get('confidence_note'),
        'decode_error': case.get('decode_error'),
        'decode_failure_assessment': case.get('decode_failure_assessment'),
        'total_occurrence_count': 0,
        'unique_chunk_count': 0,
        'unknown_labels_seen': [],
        'problem_categories_seen': [],
        'identification_statuses_seen': [],
        'decoding_sources_seen': [],
        'raw_palette_entry_bytes_seen': [],
        'decoded_block_names_seen': [],
        'persistent_block_names_seen': [],
        'persistent_block_states_seen': [],
        'resolved_runtime_block_states_seen': [],
        'likely_block_names_seen': [],
        'storage_indexes_seen': [],
        'palette_indexes_seen': [],
        'bits_per_block_seen': [],
        'palette_sizes_seen': [],
        'storage_header_bytes_seen': [],
        'subchunk_versions_seen': [],
        'record_sources_seen': [],
        'raw_subchunk_keys_seen': [],
        'sample_coordinate_format': ['world_x', 'world_y', 'world_z'],
        'sample_coordinates': [],
        'placement_coordinate_format': ['chunk_x', 'chunk_z'],
        'placements': [],
        'subchunk_ys_seen': [],
        'notes': [
            (
                'Grouped by unresolved_runtime_id. placements are unique chunk coordinate '
                'pairs that contained this runtime ID; sample_coordinates are compact '
                'world-coordinate examples.'
            )
        ],
    }


def _compact_persistent_match(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    heavy_fields = {
        'persistent_block_storage_payload_bytes_hex',
        'persistent_subchunk_payload_bytes_hex',
    }
    return {
        key: item
        for key, item in value.items()
        if key not in heavy_fields and not key.endswith('_payload_bytes_hex')
    }


def _append_unique(target: list[Any], value: Any) -> None:
    if value is None or value in target:
        return
    target.append(value)


def _append_unique_jsonable(target: list[Any], value: Any) -> None:
    if value is None:
        return
    jsonable_value = _jsonable(value)
    key = _stable_case_key({'value': jsonable_value})
    seen = {_stable_case_key({'value': existing}) for existing in target}
    if key not in seen:
        target.append(jsonable_value)


def _extend_limited_unique(
    target: list[Any],
    values: set[Any],
    *,
    limit: int | None = None,
) -> None:
    for value in values:
        if value is None or value in target:
            continue
        if limit is not None and len(target) >= limit:
            return
        target.append(value)


def _append_sample_coordinate(target: list[list[int]], sample: Any) -> None:
    if len(target) >= GROUPED_JSON_SAMPLE_LIMIT or not isinstance(sample, dict):
        return
    world_x = sample.get('world_x')
    world_y = sample.get('world_y')
    world_z = sample.get('world_z')
    if not all(isinstance(value, int) for value in (world_x, world_y, world_z)):
        return
    coordinate = [world_x, world_y, world_z]
    if coordinate not in target:
        target.append(coordinate)


def _write_csv(path: Path, cases: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'unknown_label',
        'problem_category',
        'total_occurrence_count',
        'unique_chunk_count',
        'world_path',
        'dimension',
        'dimension_id',
        'chunk_x',
        'chunk_z',
        'subchunk_y',
        'subchunk_version',
        'storage_index',
        'storage_header_byte_hex',
        'bits_per_block',
        'palette_size',
        'palette_index',
        'unresolved_runtime_id',
        'decoding_source',
        'raw_palette_entry_bytes_hex',
        'decoded_block_name',
        'decoded_block_states_json',
        'persistent_block_name',
        'persistent_block_states_json',
        'persistent_match_status',
        'identification_status',
        'likely_block_name',
        'confidence_note',
        'runtime_palette_source',
        'runtime_palette_entry_count',
        'runtime_palette_missing',
        'resolved_runtime_block_name',
        'resolved_runtime_block_states_json',
        'lookup_matched',
        'lookup_runtime_id',
        'sample_coordinates',
        'record_sources_seen',
        'raw_subchunk_keys_seen',
        'decode_error',
    ]
    with path.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            lookup = case.get('lookup') if isinstance(case.get('lookup'), dict) else {}
            writer.writerow(
                {
                    'unknown_label': case.get('unknown_label'),
                    'problem_category': case.get('problem_category'),
                    'total_occurrence_count': case.get('total_occurrence_count'),
                    'unique_chunk_count': case.get('unique_chunk_count'),
                    'world_path': case.get('world_path'),
                    'dimension': case.get('dimension'),
                    'dimension_id': case.get('dimension_id'),
                    'chunk_x': case.get('chunk_x'),
                    'chunk_z': case.get('chunk_z'),
                    'subchunk_y': case.get('subchunk_y'),
                    'subchunk_version': case.get('subchunk_version'),
                    'storage_index': case.get('storage_index'),
                    'storage_header_byte_hex': case.get('storage_header_byte_hex'),
                    'bits_per_block': case.get('bits_per_block'),
                    'palette_size': case.get('palette_size'),
                    'palette_index': case.get('palette_index'),
                    'unresolved_runtime_id': case.get('unresolved_runtime_id'),
                    'decoding_source': case.get('decoding_source'),
                    'raw_palette_entry_bytes_hex': case.get('raw_palette_entry_bytes_hex'),
                    'decoded_block_name': case.get('decoded_block_name'),
                    'decoded_block_states_json': json.dumps(
                        case.get('decoded_block_states'), sort_keys=True
                    ),
                    'persistent_block_name': case.get('persistent_block_name'),
                    'persistent_block_states_json': json.dumps(
                        case.get('persistent_block_states'), sort_keys=True
                    ),
                    'persistent_match_status': (
                        (case.get('persistent_match') or {}).get('persistent_match_status')
                        if isinstance(case.get('persistent_match'), dict)
                        else None
                    ),
                    'identification_status': case.get('identification_status'),
                    'likely_block_name': case.get('likely_block_name'),
                    'confidence_note': case.get('confidence_note'),
                    'runtime_palette_source': case.get('runtime_palette_source'),
                    'runtime_palette_entry_count': case.get('runtime_palette_entry_count'),
                    'runtime_palette_missing': case.get('runtime_palette_missing'),
                    'resolved_runtime_block_name': case.get('resolved_runtime_block_name'),
                    'resolved_runtime_block_states_json': json.dumps(
                        case.get('resolved_runtime_block_states'), sort_keys=True
                    ),
                    'lookup_matched': lookup.get('matched'),
                    'lookup_runtime_id': lookup.get('runtime_id'),
                    'sample_coordinates': _format_sample_coordinates(case.get('samples')),
                    'record_sources_seen': ';'.join(case.get('record_sources_seen') or ()),
                    'raw_subchunk_keys_seen': ';'.join(case.get('raw_subchunk_keys_seen') or ()),
                    'decode_error': case.get('decode_error'),
                }
            )


def _write_summary(
    path: Path,
    cases: list[dict[str, Any]],
    *,
    generated_at: str,
    world_path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = sum(int(case.get('total_occurrence_count') or 0) for case in cases)
    lines = [
        'Unknown Bedrock Block Diagnostics',
        '=================================',
        '',
        f'Generated: {generated_at}',
        f'World: {world_path.resolve()}',
        f'Unique unknown cases: {len(cases)}',
        f'Total unknown occurrences: {total}',
    ]
    if not cases:
        lines.extend(['', 'No unknown or unresolved block cases were encountered.'])
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return

    lines.extend(['', 'Top unknowns by occurrence count:'])
    for index, case in enumerate(cases[:30], start=1):
        samples = _format_sample_coordinates(case.get('samples'))
        lines.extend(
            [
                '',
                (
                    f'{index}. {case.get("unknown_label")} '
                    f'({case.get("total_occurrence_count")} occurrences, '
                    f'{case.get("unique_chunk_count")} chunks)'
                ),
                f'   Category: {case.get("problem_category")}',
                (
                    f'   Source: {case.get("decoding_source")}; '
                    f'bits={case.get("bits_per_block")}; '
                    f'palette_size={case.get("palette_size")}; '
                    f'palette_index={case.get("palette_index")}'
                ),
                f'   Raw palette entry bytes: {case.get("raw_palette_entry_bytes_hex") or "none"}',
                f'   Identification: {case.get("identification_status") or "unknown"}',
                (
                    f'   Persistent: {case.get("persistent_block_name") or "none"} '
                    f'{json.dumps(case.get("persistent_block_states"), sort_keys=True)}'
                ),
                f'   Samples: {samples or "none"}',
            ]
        )
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _palette_counts_and_samples(
    subchunk: DecodedSubchunk,
    storage: BlockStorage,
    *,
    storage_index: int,
    unresolved_palette_indexes: set[int],
) -> tuple[Counter[int], dict[int, list[dict[str, Any]]]]:
    palette_counts: Counter[int] = Counter()
    palette_samples: dict[int, list[dict[str, Any]]] = {}
    if storage.bits_per_block == 0:
        palette_counts[0] = SUBCHUNK_BLOCK_COUNT
        if 0 in unresolved_palette_indexes or 0 >= len(storage.palette):
            palette_samples[0] = [
                _sample_payload(
                    subchunk,
                    storage_index=storage_index,
                    palette_index=0,
                    world_x=subchunk.chunk_x * 16,
                    world_y=subchunk.min_y,
                    world_z=subchunk.chunk_z * 16,
                    local_x=0,
                    local_y=0,
                    local_z=0,
                )
            ]
        return palette_counts, palette_samples

    entries_per_word = 32 // storage.bits_per_block
    mask = (1 << storage.bits_per_block) - 1
    block_index = 0
    for word in storage.words:
        for word_entry_index in range(entries_per_word):
            if block_index >= SUBCHUNK_BLOCK_COUNT:
                return palette_counts, palette_samples
            palette_index = (word >> (word_entry_index * storage.bits_per_block)) & mask
            palette_counts[palette_index] += 1
            if (
                palette_index >= len(storage.palette)
                or palette_index in unresolved_palette_indexes
            ):
                samples = palette_samples.setdefault(palette_index, [])
                if len(samples) < MAX_UNKNOWN_SAMPLES_PER_CASE:
                    local_x = block_index & 15
                    local_z = (block_index >> 4) & 15
                    local_y = (block_index >> 8) & 15
                    samples.append(
                        _sample_payload(
                            subchunk,
                            storage_index=storage_index,
                            palette_index=palette_index,
                            world_x=(subchunk.chunk_x * 16) + local_x,
                            world_y=subchunk.min_y + local_y,
                            world_z=(subchunk.chunk_z * 16) + local_z,
                            local_x=local_x,
                            local_y=local_y,
                            local_z=local_z,
                        )
                    )
            block_index += 1
    return palette_counts, palette_samples


def _sample_payload(
    subchunk: DecodedSubchunk,
    *,
    storage_index: int,
    palette_index: int,
    world_x: int,
    world_y: int,
    world_z: int,
    local_x: int,
    local_y: int,
    local_z: int,
) -> dict[str, Any]:
    return {
        'world_x': world_x,
        'world_y': world_y,
        'world_z': world_z,
        'chunk_x': subchunk.chunk_x,
        'chunk_z': subchunk.chunk_z,
        'subchunk_y': subchunk.subchunk_y,
        'local_x': local_x,
        'local_y': local_y,
        'local_z': local_z,
        'storage_index': storage_index,
        'palette_index': palette_index,
    }


def _subchunk_debug_payload(subchunk: DecodedSubchunk, storage: BlockStorage) -> dict[str, Any]:
    raw_key_hex = subchunk.raw_key.hex() if subchunk.raw_key is not None else None
    return {
        'raw_subchunk_key': raw_key_hex,
        'raw_subchunk_key_bytes_hex': raw_key_hex,
        'record_source': subchunk.record_source,
        'storage_count': subchunk.storage_count,
        'is_version_8_or_9_paletted_storage': subchunk.subchunk_version in (8, 9),
        'has_extra_block_layer': (subchunk.storage_count or 0) > 1,
        'storage_header_byte': storage.header_byte,
        'storage_header_byte_hex': f'0x{storage.header_byte:02x}',
        'may_have_failed_due_to': [],
    }


def _runtime_resolution_payload(
    runtime_id: int | None,
    lookup: dict[str, Any],
    uses_runtime_palette: bool,
) -> dict[str, Any]:
    if not uses_runtime_palette:
        return {
            'runtime_palette_source': None,
            'runtime_palette_entry_count': None,
            'runtime_palette_missing': False,
            'resolved_runtime_block_name': None,
            'resolved_runtime_block_states': None,
        }
    runtime_entry_count = _runtime_palette_entry_count(lookup)
    result = lookup.get('result') if isinstance(lookup, dict) else None
    if isinstance(result, dict):
        return {
            'runtime_palette_source': lookup.get('dataset'),
            'runtime_palette_entry_count': runtime_entry_count,
            'runtime_palette_missing': False,
            'resolved_runtime_block_name': result.get('name'),
            'resolved_runtime_block_states': _jsonable(result.get('states')),
        }
    return {
        'runtime_palette_source': None,
        'runtime_palette_entry_count': None,
        'runtime_palette_missing': True,
        'resolved_runtime_block_name': None,
        'resolved_runtime_block_states': None,
        'runtime_palette_note': (
            'The packet cache contains runtime IDs only. The session start-game metadata '
            'does not include a runtime palette table for hashed network IDs.'
        ),
        'runtime_id': runtime_id,
    }


def _runtime_palette_entry_count(lookup: dict[str, Any]) -> int | None:
    entry_count = lookup.get('entry_count') if isinstance(lookup, dict) else None
    return entry_count if isinstance(entry_count, int) else None


def _identification_status(
    persistent_resolution: dict[str, Any],
    runtime_resolution: dict[str, Any],
    layer_heuristic: dict[str, Any],
) -> str:
    if persistent_resolution.get('matched'):
        return 'identified_from_persistent_palette'
    if runtime_resolution.get('resolved_runtime_block_name'):
        return 'identified_from_runtime_palette'
    if (
        runtime_resolution.get('runtime_palette_missing')
        and persistent_resolution.get('persistent_match_status')
        == 'no_persistent_subchunk_record_found'
    ):
        return 'unresolved'
    if layer_heuristic.get('applies'):
        return 'inferred_from_layer_heuristic'
    return 'unresolved'


def _layer_heuristic_payload(
    *,
    subchunk: DecodedSubchunk,
    storage: BlockStorage,
    storage_index: int,
    palette_index: int,
    occurrence_count: int,
) -> dict[str, Any]:
    has_extra_block_layer = (subchunk.storage_count or 0) > 1
    dominance_ratio = occurrence_count / SUBCHUNK_BLOCK_COUNT
    applies = (
        storage_index == 1
        and has_extra_block_layer
        and len(storage.palette) <= 2
        and dominance_ratio >= 0.90
    )
    if not applies:
        return {
            'applies': False,
            'dominance_ratio': dominance_ratio,
            'dominant_palette_index': palette_index,
            'has_extra_block_layer': has_extra_block_layer,
        }
    return {
        'applies': True,
        'dominance_ratio': dominance_ratio,
        'dominant_palette_index': palette_index,
        'has_extra_block_layer': has_extra_block_layer,
        'likely_block_name': 'minecraft:air',
        'confidence_note': (
            'Heuristic only: this is storage_index=1 on an extra block layer with a tiny '
            'palette and an overwhelmingly dominant entry. Bedrock often uses this layer '
            'for waterlogging/extra blocks where the dominant entry is air. This is not '
            'treated as final identity unless persistent palette data backs it.'
        ),
    }


def _sample_block_index(sample: dict[str, Any]) -> int | None:
    local_x = sample.get('local_x')
    local_y = sample.get('local_y')
    local_z = sample.get('local_z')
    if not all(isinstance(value, int) for value in (local_x, local_y, local_z)):
        return None
    if not (0 <= local_x < 16 and 0 <= local_y < 16 and 0 <= local_z < 16):
        return None
    return (local_y << 8) | (local_z << 4) | local_x


def _stable_case_key(payload: dict[str, Any]) -> str:
    return json.dumps(_jsonable(payload), sort_keys=True, separators=(',', ':'))


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, bytes):
        return value.hex()
    return value


def _decoding_source(uses_runtime_palette: bool) -> str:
    return 'runtime_decoding' if uses_runtime_palette else 'persistent_palette_decoding'


def _dimension_label(dimension_id: int | None) -> str:
    if dimension_id == 0:
        return 'overworld'
    if dimension_id == 1:
        return 'nether'
    if dimension_id == 2:
        return 'the_end'
    if dimension_id is None:
        return 'unknown'
    return f'dimension_{dimension_id}'


def _decode_error_category(message: str) -> str:
    lowered = message.lower()
    if 'unsupported subchunk version' in lowered:
        return 'unsupported_subchunk_version'
    if 'unsupported bits-per-block' in lowered or 'bits-per-block' in lowered:
        return 'malformed_subchunk_bit_packing'
    if 'palette count' in lowered or 'read past end' in lowered or 'varint' in lowered:
        return 'malformed_subchunk_bit_packing'
    return 'other_decoding_error'


def _decode_error_assessment(message: str) -> str:
    category = _decode_error_category(message)
    if category == 'unsupported_subchunk_version':
        return 'unsupported subchunk version'
    if category == 'malformed_subchunk_bit_packing':
        return 'bit packing, padding, endianness, or palette-count decoding may be wrong for this payload'
    return 'other decoding error'


def _unknown_assessment(uses_runtime_palette: bool) -> list[str]:
    if uses_runtime_palette:
        return [
            'runtime ID was not found in the bundled minecraft-data Bedrock blockStates list',
            'cached network/runtime palettes do not contain persistent NBT palette entries',
        ]
    return [
        'persistent palette entry decoded, but the block name/states are unresolved or unknown',
    ]


def _format_sample_coordinates(samples: Any) -> str:
    if not isinstance(samples, list):
        return ''
    coords: list[str] = []
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        world_x = sample.get('world_x')
        world_y = sample.get('world_y')
        world_z = sample.get('world_z')
        if world_x is None or world_y is None or world_z is None:
            coords.append(
                f'chunk=({sample.get("chunk_x")},{sample.get("chunk_z")}),'
                f'subchunk_y={sample.get("subchunk_y")}'
            )
        else:
            coords.append(f'({world_x},{world_y},{world_z})')
    return '; '.join(coords)
