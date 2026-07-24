# Plumville File Classification - 2026-07-24

This inventory classifies files and directories for cleanup planning. It recommends actions only; nothing should be deleted without explicit approval.

## Definitely Active: Retain

- `.gitignore`
- `README.md`
- `requirements.txt`
- `package.json`
- `package-lock.json`
- `docker-compose.worldgen.yml`
- `legacy_core.py`
- `metro_stops.py`
- `plumville_app.py`
- `metro_lines.txt`
- `priority_list.csv`
- `docs/`
- `tests/`
- `scripts/smoke_tk_sidebar.py`
- `scripts/validate_public_export.py`
- `scripts/performance_probe.py`
- `tools/bedrock_lan_discover.mjs`
- `worldgen/`
- `worldgen_config.toml`
- `plumville/`

Reasoning:
- `metro_stops.py` is the desktop entry point and imports `legacy_core.py` plus `ui_extensions.py`.
- `plumville_app.py` imports `metro_stops.py`.
- `docs/` is the public viewer and canonical public network location.
- `worldgen/` is the canonical package used by `python3 -m worldgen`.
- `plumville/` now contains tested core modules used by `legacy_core.py` and public export validation.

## Active Transitional Modules: Retain, Then Consolidate

These are active runtime patch or helper modules. They should not be deleted now.

- `ui_extensions.py`
- `metro_station_extensions.py`
- `path_detection.py`
- `path_rendering.py`
- `poi_extensions.py`
- `world_map_overrides.py`
- `worldgen_speedups.py`
- `worldgen_target_fix.py`
- `walking_suggestions.py`
- `world_map_analysis.py`

Recommended action:
- Retain during cleanup.
- Add focused tests where missing.
- Move behavior into canonical modules in small slices.
- Remove patch wrappers only after canonical replacements are covered and `metro_stops.py` no longer depends on them.

Suggested consolidation order:
1. `worldgen_target_fix.py` into canonical worldgen target planning.
2. `worldgen_speedups.py` into `worldgen/generator.py` or focused worldgen modules.
3. `world_map_overrides.py` into desktop world-map rendering/export modules.
4. `path_rendering.py` and `path_detection.py` into desktop path modules plus worldgen/path analysis helpers.
5. `poi_extensions.py`, `metro_station_extensions.py`, and `ui_extensions.py` after their patched methods have stable homes.

## Public Assets: Retain, Validate Before Publishing

- `docs/index.html`
- `docs/app.js`
- `docs/styles.css`
- `docs/smoke_test.js`
- `docs/metro_network.json`
- `docs/assets/blackport_topdown.png`
- `docs/assets/blackport_topdown.render.json`
- `docs/assets/blackport_lan_surface.png`

Recommended action:
- Retain.
- Validate with `npm test` before publishing.
- Keep local/cache/private fields out of `docs/`.

## Generated or Local Runtime Data: Keep Ignored, Do Not Publish

- `.pytest_cache/`
- `.worldgen/`
- `__pycache__/`
- `docs/.DS_Store`
- `.DS_Store`
- `worldgen/.DS_Store`
- `node_modules/`
- `exports/`
- `metro_network.history/`
- `metro_network.last.json`
- `worldgen_data/`
- `worldgen_output/`
- `path_detection_state.json`

Recommended action:
- Keep ignored.
- Do not publish.
- Do not delete without explicit approval because several items may contain useful local state or generated outputs.
- Later, consider moving local runtime state into a single ignored directory such as `.plumville/`.

Approximate local sizes observed:

- `worldgen_data/`: 3.1G
- `node_modules/`: 491M
- `metro_network.history/`: 44M
- `exports/`: 30M
- `docs/`: 21M
- `worldgen_output/`: 5.3M
- `__pycache__/`: 1.6M

## Reports and Planning Artifacts: Retain During Cleanup

- `notes.txt`
- `ARCHITECTURE_AUDIT_2026-07-24.md`
- `FILE_CLASSIFICATION_2026-07-24.md`

Recommended action:
- Retain until the cleanup plan is complete.
- Use `notes.txt` as the active queue.
- Keep audit/classification reports outside `docs/`.

## Near-Term Cleanup Candidates: Approval Required

These are candidates only, not automatic deletion targets.

- `.DS_Store` files: safe to delete if approved.
- `__pycache__/` and test caches: safe to delete if approved.
- Old SVGs under `exports/`: review before deleting.
- Old snapshots under `metro_network.history/`: review retention policy before pruning.
- Duplicate-looking terrain outputs under `worldgen_output/`: review against `docs/assets/` before deleting.

## Do Not Delete Yet

- Any `*_extensions.py` module.
- `worldgen_speedups.py`.
- `worldgen_target_fix.py`.
- `world_map_overrides.py`.
- `walking_suggestions.py`.
- `world_map_analysis.py`.
- `docs/metro_network.json`.
- `docs/assets/*`.
- `worldgen_data/`.
- `worldgen_output/`.

These are either active, transitional, canonical public output, or local state that needs explicit review.
