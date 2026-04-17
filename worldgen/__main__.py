from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .config import load_config
from .generator import BedrockWorldGenerator


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        generator = BedrockWorldGenerator(config)

        if args.command == 'status':
            return _handle_status(generator)
        if args.command == 'start':
            generator.start()
            print(f'Started Bedrock worldgen container using {config.compose_path}')
            return 0
        if args.command == 'wait':
            world_path = generator.wait_until_ready(args.timeout)
            print(world_path)
            return 0
        if args.command == 'prepare':
            world_path, render_plan_path = generator.prepare()
            print(f'World ready: {world_path}')
            print(f'Render plan: {render_plan_path}')
            return 0
        if args.command == 'stop':
            generator.stop()
            print('Stopped Bedrock worldgen container.')
            return 0
        if args.command == 'world-path':
            print(generator.locate_world_folder(require_exists=True))
            return 0
        if args.command == 'render-plan':
            render_plan_path = generator.write_render_plan()
            print(render_plan_path)
            return 0
        if args.command == 'render':
            result = generator.render_map(
                diagnose_unknown_blocks=args.diagnose_unknown_blocks or args.prefer_persistent_bedrock,
                prefer_persistent_bedrock=args.prefer_persistent_bedrock,
            )
            print(f'Rendered map: {result.image_path}')
            print(f'Render metadata: {result.metadata_path}')
            print(f'Uncolored block report: {result.uncolored_blocks_report_path}')
            if result.unknown_block_diagnostics_path:
                print(f'Unknown block diagnostics: {result.unknown_block_diagnostics_path}')
            if result.unknown_block_occurrences_csv_path:
                print(f'Unknown block CSV: {result.unknown_block_occurrences_csv_path}')
            if result.unknown_block_summary_path:
                print(f'Unknown block summary: {result.unknown_block_summary_path}')
            if result.unknown_block_persistent_candidates_path:
                print(
                    'Unknown block persistent candidates: '
                    f'{result.unknown_block_persistent_candidates_path}'
                )
            print(f'Colored pixels: {result.colored_pixels}/{result.total_pixels}')
            print(f'Uncolored block occurrences: {result.uncolored_block_occurrences}')
            print(f'Chunk columns read: {result.chunk_columns_read}/{result.chunk_columns_requested}')
            if result.chunk_columns_read == 0:
                print('No generated chunk columns were found in the requested render area yet.')
                print('Run `python3 -m worldgen load-chunks`, then render again.')
            if result.subchunk_decode_errors:
                print(f'Subchunk decode errors: {result.subchunk_decode_errors}')
            return 0
        if args.command == 'repair-db':
            result = generator.repair_world_db()
            print(f'Bedrock LevelDB folder left in place: {result.db_path}')
            print(f'Backup written: {result.backup_path}')
            print(f'Repaired copy written: {result.repaired_copy_path}')
            return 0
        if args.command == 'load-chunks':
            result = generator.load_chunks_headless(
                wait_seconds=args.seconds,
                stop_after=not args.keep_running,
            )
            print('Headless chunk loader finished.')
            print(f'World: {result.world_path}')
            print(f'Result metadata: {result.result_path}')
            print(f'Chunks received: {result.chunks_received}')
            print(f'Chunk columns received: {result.unique_chunk_columns}')
            print(f'Load attempts: {result.load_attempts}')
            print(f'Teleport commands sent: {result.teleport_commands_sent}')
            print(f'Teleport targets this pass: {", ".join(result.teleport_targets) or "none"}')
            print(
                f'Next teleport target: {result.teleport_next_index + 1}/{result.teleport_target_count}'
            )
            print(f'Server stopped: {result.server_stopped}')
            if result.output:
                print('Loader output:')
                print(result.output)
            if result.returncode != 0:
                print(f'Headless loader exited with code {result.returncode}.', file=sys.stderr)
            return 0 if result.returncode == 0 else 1
    except Exception as exc:
        print(f'worldgen error: {exc}', file=sys.stderr)
        return 1

    parser.error('No command selected.')
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Bedrock world generation helper for the metro map repo.')
    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to a worldgen TOML config file. Defaults to worldgen_config.toml in the repo root.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('status', help='Show config, cache, and Docker status.')
    subparsers.add_parser('start', help='Start the Bedrock container.')

    wait_parser = subparsers.add_parser('wait', help='Wait for startup completion and cache the world path.')
    wait_parser.add_argument('--timeout', type=int, default=None, help='Optional startup timeout override in seconds.')

    subparsers.add_parser('prepare', help='Start, wait, cache the world path, and write the render plan.')
    subparsers.add_parser('stop', help='Stop the Bedrock container.')
    subparsers.add_parser('world-path', help='Print the resolved world path if it exists.')
    subparsers.add_parser('render-plan', help='Write the current Blackport-centered render plan JSON.')
    render_parser = subparsers.add_parser(
        'render',
        help='Render generated Bedrock chunks into a first-pass top-down PNG.',
    )
    render_parser.add_argument(
        '--diagnose-unknown-blocks',
        '--dump-unknown-bedrock',
        action='store_true',
        help='Export raw Bedrock palette diagnostics for unresolved/unknown block entries.',
    )
    render_parser.add_argument(
        '--prefer-persistent-bedrock',
        action='store_true',
        help='Resolve packet-cache unknowns through saved LevelDB subchunk palettes when available.',
    )
    subparsers.add_parser(
        'repair-db',
        help='Back up and repair the saved Bedrock LevelDB folder after a render-read corruption error.',
    )

    load_chunks_parser = subparsers.add_parser(
        'load-chunks',
        help='Use a local headless Bedrock bot to load and save chunks near the render center.',
    )
    load_chunks_parser.add_argument(
        '--seconds',
        type=int,
        default=None,
        help='Optional bot wait time override in seconds.',
    )
    load_chunks_parser.add_argument(
        '--keep-running',
        action='store_true',
        help='Leave the Bedrock server running after the bot exits.',
    )
    return parser


def _handle_status(generator: BedrockWorldGenerator) -> int:
    status = generator.status()
    config = generator.config
    payload = {
        'config_path': str(config.config_path),
        'compose_path': str(config.compose_path),
        'data_dir': str(generator.paths.data_dir),
        'cache_file': str(generator.paths.world_cache_path),
        'render_plan_file': str(generator.paths.render_plan_path),
        'docker_available': status.docker_available,
        'service_running': status.service_running,
        'expected_world_path': str(status.expected_world_path),
        'expected_world_exists': status.expected_world_exists,
        'cached_world_path': str(status.cached_world_path) if status.cached_world_path else None,
        'cached_world_exists': status.cached_world_exists,
        'render_area': asdict(config.render),
        'headless_loader': asdict(config.headless_loader),
        'render_image_file': str(status.render_image_path),
        'render_image_exists': status.render_image_exists,
        'docs_render_image_file': str(status.docs_render_image_path),
        'docs_render_image_exists': status.docs_render_image_exists,
        'render_cache_file': str(status.render_cache_path),
        'render_cache_exists': status.render_cache_exists,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
