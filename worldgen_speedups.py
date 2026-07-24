from __future__ import annotations

import threading
from typing import Any, Callable, cast

import legacy_core as base


_APPLIED = False

_ORIGINAL_RENDER_MAP = None
_ORIGINAL_RENDER_LOADED_TARGET_MAP = None
_ORIGINAL_RENDER_CACHED_BLANK_PIXEL_BATCH = None
_ORIGINAL_AUTO_FILL_STEP_TEXT = None
_ORIGINAL_FINISH_AUTO_FILL_WORLD_MAP = None


def _blank_target_pixel_keys(config: Any, image_path: Any, target: tuple[int, int]) -> set[tuple[int, int]]:
    import worldgen.generator as generator

    pixel_keys = generator._teleport_target_pixel_keys(config, target)
    if not pixel_keys:
        return set()

    try:
        from PIL import Image

        with Image.open(image_path) as source_image:
            alpha = source_image.convert('RGBA').getchannel('A')
            alpha_pixels = alpha.load()
            if alpha_pixels is None:
                return pixel_keys
            return {
                (pixel_x, pixel_z)
                for pixel_x, pixel_z in pixel_keys
                if alpha_pixels[pixel_x, pixel_z] == 0
            }
    except Exception:
        return pixel_keys


def _essential_render_lines(
    render_result: Any,
    *,
    step_label: str,
    pixels_filled: int,
    render_target: tuple[int, int] | None = None,
    load_passes: int | None = None,
) -> list[str]:
    lines = [
        f'{step_label} finished.',
        base._world_map_completion_text_from_result(render_result),
        f'Pixels filled: {pixels_filled}',
    ]
    if render_target is not None:
        lines.append(f'Target: {render_target[0]},{render_target[1]}')
    if load_passes is not None:
        lines.append(f'Load passes: {load_passes}')
    if render_result.unfinished_group_count:
        lines.append(f'Unfinished groups: {render_result.unfinished_group_count}')
    if render_result.uncolored_block_occurrences:
        lines.append(f'Uncolored blocks: {render_result.uncolored_block_occurrences}')
    if render_result.subchunk_decode_errors:
        lines.append(f'Subchunk decode errors: {render_result.subchunk_decode_errors}')
    lines.append('Ready for the next step.')
    return lines


def _patched_render_map(
    self,
    *,
    diagnose_unknown_blocks: bool = False,
    prefer_persistent_bedrock: bool = False,
    mode_key: str | None = None,
    image_progress_callback: Callable[[int], None] | None = None,
    image_progress_interval: int = 0,
    pixel_keys: set[tuple[int, int]] | None = None,
):
    import worldgen.generator as generator
    from worldgen.modes import worldgen_mode

    assert _ORIGINAL_RENDER_MAP is not None
    mode = worldgen_mode(mode_key)
    if mode.is_lan:
        return _ORIGINAL_RENDER_MAP(
            self,
            diagnose_unknown_blocks=diagnose_unknown_blocks,
            prefer_persistent_bedrock=prefer_persistent_bedrock,
            mode_key=mode_key,
            image_progress_callback=image_progress_callback,
            image_progress_interval=image_progress_interval,
            pixel_keys=pixel_keys,
        )

    self.paths.ensure_runtime_dirs()
    world_path = self._resolve_existing_world_folder()
    self.write_render_plan(world_path)
    result = generator.render_topdown_map(
        self.config,
        world_path,
        image_path=self.paths.render_image_path,
        metadata_path=self.paths.render_cache_path,
        diagnose_unknown_blocks=diagnose_unknown_blocks,
        prefer_persistent_bedrock=prefer_persistent_bedrock,
        packet_cache_paths=self._local_render_packet_cache_paths(),
        preserve_existing_image=True,
        image_progress_callback=image_progress_callback,
        image_progress_interval=image_progress_interval,
        pixel_keys=pixel_keys,
        compact_packet_cache=False,
    )
    generator._copy_file_best_effort(self.paths.render_image_path, self.paths.docs_render_image_path)
    generator._copy_file_best_effort(
        self.paths.render_cache_path,
        generator._docs_render_metadata_path(self.paths.docs_render_image_path),
    )
    return result


def _patched_render_loaded_target_map(
    self,
    target: tuple[int, int],
    *,
    image_progress_callback: Callable[[int], None] | None = None,
    image_progress_interval: int = 0,
):
    import worldgen.generator as generator

    pixel_keys = _blank_target_pixel_keys(self.config, self.paths.render_image_path, target)
    if not pixel_keys:
        pixel_keys = generator._teleport_target_pixel_keys(self.config, target)
    if not pixel_keys:
        return _patched_render_map(
            self,
            image_progress_callback=image_progress_callback,
            image_progress_interval=image_progress_interval,
        )

    packet_cache_paths = self._incremental_render_packet_cache_paths()
    if not packet_cache_paths:
        assert _ORIGINAL_RENDER_LOADED_TARGET_MAP is not None
        return _ORIGINAL_RENDER_LOADED_TARGET_MAP(
            self,
            target,
            image_progress_callback=image_progress_callback,
            image_progress_interval=image_progress_interval,
        )

    self.paths.ensure_runtime_dirs()
    result = generator.render_topdown_map(
        self.config,
        None,
        image_path=self.paths.render_image_path,
        metadata_path=self.paths.render_cache_path,
        packet_cache_paths=packet_cache_paths,
        read_persistent_bedrock=False,
        preserve_existing_image=True,
        pixel_keys=pixel_keys,
        compact_packet_cache=False,
        image_progress_callback=image_progress_callback,
        image_progress_interval=image_progress_interval,
    )
    generator._copy_file_best_effort(self.paths.render_image_path, self.paths.docs_render_image_path)
    generator._copy_file_best_effort(
        self.paths.render_cache_path,
        generator._docs_render_metadata_path(self.paths.docs_render_image_path),
    )
    return result


def _patched_render_cached_blank_pixel_batch(self, *, batch_size=None):
    import worldgen.generator as generator

    assert _ORIGINAL_RENDER_CACHED_BLANK_PIXEL_BATCH is not None
    effective_batch_size = batch_size
    if effective_batch_size is None:
        effective_batch_size = max(generator.INCREMENTAL_RENDER_BATCH_PIXELS, 100_000)
    else:
        effective_batch_size = max(int(effective_batch_size), generator.INCREMENTAL_RENDER_BATCH_PIXELS)
    return _ORIGINAL_RENDER_CACHED_BLANK_PIXEL_BATCH(self, batch_size=effective_batch_size)


def _patched_auto_fill_step_text_for_generator(
    generator: Any,
    *,
    step_number: int | None = None,
    progress_callback: Callable[[str, bool], None] | None = None,
) -> str:
    step_label = f'Auto fill step {step_number}' if step_number is not None else 'Auto fill step'
    cached_pixel_result = generator.render_cached_blank_pixel_batch()
    if cached_pixel_result is not None and cached_pixel_result.colored_pixels_added > 0:
        render_result = cached_pixel_result.render_result
        lines = _essential_render_lines(
            render_result,
            step_label=step_label,
            pixels_filled=cached_pixel_result.colored_pixels_added,
        )
        lines.insert(1, 'Used recent cached chunks.')
        return '\n'.join(lines)

    if cached_pixel_result is not None and progress_callback is not None:
        progress_callback(
            (
                f'{step_label} checked a large cached-pixel batch around Blackport.\n\n'
                f'Pixels checked: {cached_pixel_result.scanned_pixels}\n'
                f'Blank pixels sampled: {cached_pixel_result.blank_pixels_selected}\n'
                'No cached pixels could be filled from that batch, so Auto Fill is loading more terrain.'
            ),
            True,
        )

    before_load_colored_pixels = (
        generator.cached_colored_pixel_count()
        if hasattr(generator, 'cached_colored_pixel_count')
        else 0
    )

    def post_active_target_progress(target: tuple[int, int]) -> None:
        base._post_world_map_active_target_progress(
            progress_callback,
            f'{step_label} is loading a target square',
            target,
        )

    load_results = [
        generator.load_chunks_headless(
            stop_after=False,
            restart_existing=False,
            active_target_callback=post_active_target_progress,
        )
        for _index in range(base.WORLD_MAP_AUTO_LOAD_PASSES)
    ]
    render_target: tuple[int, int] | None = None

    def post_render_progress(new_pixels_added: int) -> None:
        if progress_callback is None:
            return
        progress_callback(
            (
                f'{step_label} is painting the loaded target.\n\n'
                f'Pixels filled so far in this render: {new_pixels_added}\n'
                'This pass is using the recent packet cache only for speed.'
            ),
            False,
        )

    for load_result in load_results:
        for target_text in load_result.teleport_targets:
            try:
                target_x_text, target_z_text = target_text.split(',', 1)
                render_target = (int(target_x_text), int(target_z_text))
                break
            except ValueError:
                continue
        if render_target is not None:
            break

    if render_target is not None and hasattr(generator, 'render_loaded_target_map'):
        render_result = generator.render_loaded_target_map(
            render_target,
            image_progress_callback=post_render_progress,
            image_progress_interval=base.WORLD_MAP_RENDER_PROGRESS_PIXEL_INTERVAL,
        )
    else:
        render_result = generator.render_map(
            image_progress_callback=post_render_progress,
            image_progress_interval=base.WORLD_MAP_RENDER_PROGRESS_PIXEL_INTERVAL,
        )

    colored_pixels_added = max(0, render_result.colored_pixels - before_load_colored_pixels)
    if render_target is not None and hasattr(generator, 'mark_headless_loader_target_progress'):
        generator.mark_headless_loader_target_progress(
            render_target,
            pixels_added=colored_pixels_added,
        )

    for index, load_result in enumerate(load_results, start=1):
        if load_result.returncode != 0:
            lines = [f'{step_label} loader pass {index} exited with code {load_result.returncode}.']
            if load_result.output:
                lines.append(load_result.output)
            return '\n'.join(lines)

    lines = _essential_render_lines(
        render_result,
        step_label=step_label,
        pixels_filled=colored_pixels_added,
        render_target=render_target,
        load_passes=len(load_results),
    )
    if colored_pixels_added == 0 and any(load_result.chunks_received > 0 for load_result in load_results):
        lines.append(
            'Chunks loaded, but this target did not add newly colored pixels. '
            'The next step will skip ahead.'
        )
    return '\n'.join(lines)


def _stop_generator_after_auto_fill() -> None:
    try:
        from worldgen.config import load_config
        from worldgen.generator import BedrockWorldGenerator

        BedrockWorldGenerator(load_config()).stop()
    except Exception:
        return


def _patched_finish_auto_fill_world_map(self, _succeeded: bool, _message: str) -> None:
    assert _ORIGINAL_FINISH_AUTO_FILL_WORLD_MAP is not None
    _ORIGINAL_FINISH_AUTO_FILL_WORLD_MAP(self, _succeeded, _message)
    threading.Thread(target=_stop_generator_after_auto_fill, daemon=True).start()


def apply() -> None:
    global _APPLIED
    global _ORIGINAL_RENDER_MAP
    global _ORIGINAL_RENDER_LOADED_TARGET_MAP
    global _ORIGINAL_RENDER_CACHED_BLANK_PIXEL_BATCH
    global _ORIGINAL_AUTO_FILL_STEP_TEXT
    global _ORIGINAL_FINISH_AUTO_FILL_WORLD_MAP

    if _APPLIED:
        return

    import worldgen.generator as generator

    _ORIGINAL_RENDER_MAP = generator.BedrockWorldGenerator.render_map
    _ORIGINAL_RENDER_LOADED_TARGET_MAP = generator.BedrockWorldGenerator.render_loaded_target_map
    _ORIGINAL_RENDER_CACHED_BLANK_PIXEL_BATCH = generator.BedrockWorldGenerator.render_cached_blank_pixel_batch
    _ORIGINAL_AUTO_FILL_STEP_TEXT = base._world_map_auto_fill_step_text_for_generator
    _ORIGINAL_FINISH_AUTO_FILL_WORLD_MAP = base.MetroMapViewer._finish_auto_fill_world_map

    generator.BedrockWorldGenerator.render_map = cast(Any, _patched_render_map)
    generator.BedrockWorldGenerator.render_loaded_target_map = cast(Any, _patched_render_loaded_target_map)
    generator.BedrockWorldGenerator.render_cached_blank_pixel_batch = cast(Any, _patched_render_cached_blank_pixel_batch)
    base._world_map_auto_fill_step_text_for_generator = cast(Any, _patched_auto_fill_step_text_for_generator)
    base.MetroMapViewer._finish_auto_fill_world_map = cast(Any, _patched_finish_auto_fill_world_map)

    generator.INCREMENTAL_RENDER_BATCH_PIXELS = max(generator.INCREMENTAL_RENDER_BATCH_PIXELS, 100_000)
    generator.INCREMENTAL_RENDER_MAX_SCAN_PIXELS = max(generator.INCREMENTAL_RENDER_MAX_SCAN_PIXELS, 15_000_000)
    generator.HEADLESS_LOADER_CONNECT_SETTLE_SECONDS = min(generator.HEADLESS_LOADER_CONNECT_SETTLE_SECONDS, 2.0)
    generator.HEADLESS_LOADER_FIRST_TELEPORT_DELAY_SECONDS = min(generator.HEADLESS_LOADER_FIRST_TELEPORT_DELAY_SECONDS, 0.5)
    generator.HEADLESS_LOADER_SETTLE_AFTER_LAST_TELEPORT_SECONDS = min(
        generator.HEADLESS_LOADER_SETTLE_AFTER_LAST_TELEPORT_SECONDS,
        6.0,
    )

    _APPLIED = True
