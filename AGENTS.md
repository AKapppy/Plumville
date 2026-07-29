# AGENTS.md — Plumville Codex Instructions

These instructions apply to the entire repository.

## Read first

Before changing code, read:

1. `notes.txt`
2. `file_priority.txt`
3. `CODEX_TASK.md`

The checklist at the top of `notes.txt` is authoritative.

## Source of truth

Treat the current checkout as the source of truth.

Do not apply old generated updater scripts.

The latest repository already contains `desktop_improvements.py` and an
`ui_extensions.py` that imports and applies it. Audit that implementation
instead of assuming the earlier updater did or did not run.

## Git safety

Do not commit.

Do not push.

Do not create or move branches unless the user explicitly asks.

Do not run:

- `git reset --hard`
- `git clean`
- destructive checkout/restore commands
- force pushes

Preserve all existing user changes.

Always show `git status --short` at the end of a run.

## Data safety

Never delete, expose, rewrite, or commit private runtime data.

Preserve:

- worldgen caches and output
- Bedrock world data
- history and snapshots
- ignored files
- path-detection state
- local configuration
- private exports

Do not modify real runtime data merely to make a test pass.

## Scope discipline

Work on one coherent implementation slice per run.

The current priority is Desktop Stabilization Run D01.

Do not begin the mode redesign, inspector, canonical-data migration, or
construction dashboard before D01 is stable.

Phone/mobile-specific public work is on hold.

Desktop-browser public regressions may be fixed through localhost testing.

## Existing behavior

Preserve current functionality unless the checklist explicitly changes it.

In particular, preserve:

- station and coordinate search
- route planning
- editing
- undo/history
- exports
- path rendering and saved path data
- world-map rendering
- public abbreviations
- public share links

## Architecture

Avoid blind whole-file replacements.

`legacy_core.py` is high risk. Patch it only when a small stable hook is safer
than another monkey patch.

Keep orchestration in `ui_extensions.py`.

Keep substantial desktop behavior in a dedicated desktop module.

Make `.apply()` functions idempotent.

Avoid recursive method wrappers and duplicate UI construction.

## Coding style

Keep lines reasonably short.

Use descriptive names.

Add type hints where useful.

Prefer pure helper functions for decisions that can be unit tested.

Add comments for extension-order or monkey-patching constraints.

Do not add dependencies without a concrete need.

## Required workflow

For each run:

1. Read the current instructions and checklist.
2. Record branch and `git status --short`.
3. Run baseline tests.
4. Reproduce the actual issue.
5. Mark the active checklist item `[~]`.
6. Make the smallest complete fix.
7. Add or update tests.
8. Run targeted tests.
9. Run broader tests.
10. Inspect the diff.
11. Update `notes.txt`.
12. Update `file_priority.txt`.
13. Leave user verification boxes unchecked.
14. Provide a numbered user-check list.
15. Stop before starting the next major slice.

## Checklist editing

Use these statuses:

- `[ ]` not started
- `[~]` in progress
- `[x]` implemented and supported by passing automated checks
- `[verify]` implemented but needs user verification
- `[blocked]` blocked
- `[hold]` paused
- `[deferred]` postponed
- `[info]` reference

Do not mark interactive user checks `[x]`.

## Testing

Run relevant commands from the repository root.

At minimum for desktop work:

```bash
python3 -m py_compile \
  ui_extensions.py \
  desktop_improvements.py \
  path_detection.py \
  metro_station_extensions.py

python3 -m unittest discover -s tests
npm run test:paths
npm test
git diff --check
```

Run the Tk smoke test when a display is available:

```bash
PLUMVILLE_RUN_TK_SMOKE=1 npm run smoke:tk
```

Launch the private app when interactive execution is available:

```bash
python3 plumville_app.py
```

Report every PASS, FAIL, and SKIP honestly.

## End-of-run response

Always provide:

- run name and scope;
- checklist statuses changed;
- changed files;
- exact tests and results;
- numbered manual checks for the user;
- known issues and risks;
- `git status --short`;
- confirmation that no commit or push occurred.
