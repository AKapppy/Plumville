from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import legacy_core as base
import worldgen_speedups
from worldgen import generator


class WorldgenSpeedupConsolidationTests(unittest.TestCase):
    def _generator_instance(self, *, render_image_path: Path | None = None) -> generator.BedrockWorldGenerator:
        paths = SimpleNamespace(
            cache_dir=Path("cache"),
            render_image_path=render_image_path or Path("render.png"),
            render_cache_path=Path("render_cache.json"),
            docs_render_image_path=Path("docs/assets/render.png"),
            ensure_runtime_dirs=mock.Mock(),
        )
        instance = object.__new__(generator.BedrockWorldGenerator)
        instance.config = SimpleNamespace()
        instance.paths = paths
        instance._resolve_existing_world_folder = mock.Mock(return_value=Path("world"))
        instance.write_render_plan = mock.Mock()
        instance._local_render_packet_cache_paths = mock.Mock(return_value=(Path("packets.jsonl"),))
        instance._incremental_render_packet_cache_paths = mock.Mock(return_value=(Path("recent.jsonl"),))
        instance._write_spiral_check_preview = mock.Mock()
        return instance

    def test_speedup_constants_are_canonical(self) -> None:
        self.assertEqual(generator.INCREMENTAL_RENDER_BATCH_PIXELS, 100_000)
        self.assertEqual(generator.INCREMENTAL_RENDER_MAX_SCAN_PIXELS, 15_000_000)
        self.assertEqual(generator.HEADLESS_LOADER_CONNECT_SETTLE_SECONDS, 2.0)
        self.assertEqual(generator.HEADLESS_LOADER_FIRST_TELEPORT_DELAY_SECONDS, 0.5)
        self.assertEqual(generator.HEADLESS_LOADER_SETTLE_AFTER_LAST_TELEPORT_SECONDS, 6.0)

    def test_render_map_disables_packet_cache_compaction(self) -> None:
        instance = self._generator_instance()
        render_result = object()

        with (
            mock.patch.object(generator, "render_topdown_map", return_value=render_result) as render_topdown_map,
            mock.patch.object(generator, "_copy_file_best_effort"),
        ):
            result = instance.render_map()

        self.assertIs(result, render_result)
        self.assertFalse(render_topdown_map.call_args.kwargs["compact_packet_cache"])

    def test_render_loaded_target_map_uses_recent_packet_cache_and_blank_pixels(self) -> None:
        instance = self._generator_instance()
        render_result = object()

        with (
            mock.patch.object(generator, "_blank_target_pixel_keys", return_value={(3, 4)}),
            mock.patch.object(generator, "render_topdown_map", return_value=render_result) as render_topdown_map,
            mock.patch.object(generator, "_copy_file_best_effort"),
        ):
            result = instance.render_loaded_target_map((128, 256))

        self.assertIs(result, render_result)
        self.assertIsNone(render_topdown_map.call_args.args[1])
        self.assertEqual(render_topdown_map.call_args.kwargs["packet_cache_paths"], (Path("recent.jsonl"),))
        self.assertFalse(render_topdown_map.call_args.kwargs["read_persistent_bedrock"])
        self.assertFalse(render_topdown_map.call_args.kwargs["compact_packet_cache"])
        self.assertEqual(render_topdown_map.call_args.kwargs["pixel_keys"], {(3, 4)})

    def test_cached_blank_pixel_batch_uses_minimum_batch_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            render_image_path = Path(temporary_dir) / "render.png"
            render_image_path.touch()
            instance = self._generator_instance(render_image_path=render_image_path)

            with mock.patch.object(
                generator,
                "_blank_pixel_spiral_batch",
                return_value=SimpleNamespace(pixel_keys=set(), scanned_pixels=0),
            ) as blank_pixel_spiral_batch:
                result = instance.render_cached_blank_pixel_batch(batch_size=1)

        self.assertIsNone(result)
        self.assertEqual(blank_pixel_spiral_batch.call_args.kwargs["batch_size"], 100_000)
        self.assertEqual(blank_pixel_spiral_batch.call_args.kwargs["max_scan_pixels"], 15_000_000)

    def test_auto_fill_step_uses_speedup_flow_canonically(self) -> None:
        fake_generator = mock.Mock()
        fake_generator.render_cached_blank_pixel_batch.return_value = None
        fake_generator.cached_colored_pixel_count.return_value = 10
        fake_generator.load_chunks_headless.return_value = SimpleNamespace(
            returncode=0,
            chunks_received=3,
            teleport_targets=("128,256",),
            output="",
        )
        fake_generator.render_loaded_target_map.return_value = SimpleNamespace(
            colored_pixels=15,
            total_pixels=20,
            unfinished_group_count=0,
            uncolored_block_occurrences=0,
            subchunk_decode_errors=0,
        )

        message = base._world_map_auto_fill_step_text_for_generator(
            fake_generator,
            step_number=2,
        )

        fake_generator.load_chunks_headless.assert_called_once()
        self.assertFalse(fake_generator.load_chunks_headless.call_args.kwargs["stop_after"])
        fake_generator.render_loaded_target_map.assert_called_once_with(
            (128, 256),
            image_progress_callback=mock.ANY,
            image_progress_interval=base.WORLD_MAP_RENDER_PROGRESS_PIXEL_INTERVAL,
        )
        fake_generator.mark_headless_loader_target_progress.assert_called_once_with(
            (128, 256),
            pixels_added=5,
        )
        self.assertIn("Auto fill step 2 finished.", message)
        self.assertIn("Pixels filled: 5", message)
        self.assertIn("Target: 128,256", message)
        self.assertIn("Load passes: 1", message)
        self.assertIn("Ready for the next step.", message)

    def test_auto_fill_cached_pixel_success_uses_essential_summary(self) -> None:
        render_result = SimpleNamespace(
            colored_pixels=15,
            total_pixels=20,
            unfinished_group_count=0,
            uncolored_block_occurrences=0,
            subchunk_decode_errors=0,
        )
        fake_generator = mock.Mock()
        fake_generator.render_cached_blank_pixel_batch.return_value = SimpleNamespace(
            render_result=render_result,
            colored_pixels_added=5,
        )

        message = base._world_map_auto_fill_step_text_for_generator(fake_generator)

        fake_generator.load_chunks_headless.assert_not_called()
        self.assertIn("Used recent cached chunks.", message)
        self.assertIn("Pixels filled: 5", message)
        self.assertIn("Ready for the next step.", message)

    def test_finish_auto_fill_stops_worldgen_in_background(self) -> None:
        viewer = SimpleNamespace(
            world_map_auto_fill_stop_event=object(),
            world_map_auto_fill_running=True,
            world_map_auto_fill_stop_requested=True,
            _set_world_map_auto_fill_button=mock.Mock(),
            redraw=mock.Mock(),
        )

        with mock.patch.object(base.threading, "Thread") as thread_class:
            thread_instance = mock.Mock()
            thread_class.return_value = thread_instance
            base.MetroMapViewer._finish_auto_fill_world_map(viewer, True, "done")

        self.assertIsNone(viewer.world_map_auto_fill_stop_event)
        self.assertFalse(viewer.world_map_auto_fill_running)
        self.assertFalse(viewer.world_map_auto_fill_stop_requested)
        viewer._set_world_map_auto_fill_button.assert_called_once_with("idle")
        viewer.redraw.assert_called_once()
        thread_class.assert_called_once_with(target=base._stop_worldgen_after_auto_fill, daemon=True)
        thread_instance.start.assert_called_once()

    def test_speedups_apply_is_compatibility_noop(self) -> None:
        before_render_map = generator.BedrockWorldGenerator.render_map
        before_render_loaded_target_map = generator.BedrockWorldGenerator.render_loaded_target_map
        before_render_cached_blank_pixel_batch = generator.BedrockWorldGenerator.render_cached_blank_pixel_batch
        before_auto_fill_step_text = base._world_map_auto_fill_step_text_for_generator
        before_finish_auto_fill = base.MetroMapViewer._finish_auto_fill_world_map

        original_applied = worldgen_speedups._APPLIED
        applied_after_call = False
        try:
            worldgen_speedups._APPLIED = False
            worldgen_speedups.apply()
            applied_after_call = worldgen_speedups._APPLIED
        finally:
            worldgen_speedups._APPLIED = original_applied

        self.assertTrue(applied_after_call)
        self.assertIs(generator.BedrockWorldGenerator.render_map, before_render_map)
        self.assertIs(generator.BedrockWorldGenerator.render_loaded_target_map, before_render_loaded_target_map)
        self.assertIs(generator.BedrockWorldGenerator.render_cached_blank_pixel_batch, before_render_cached_blank_pixel_batch)
        self.assertIs(base._world_map_auto_fill_step_text_for_generator, before_auto_fill_step_text)
        self.assertIs(base.MetroMapViewer._finish_auto_fill_world_map, before_finish_auto_fill)


if __name__ == "__main__":
    unittest.main()
