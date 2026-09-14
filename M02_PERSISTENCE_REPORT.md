# M02 — Read-Only Loading and Test Isolation

Result: **PASS for automated M02 acceptance**. GUI verification remains unchecked.
The full suite retains the documented two signage failures and two signage errors.
Worldgen live status is explicitly deferred to M03; it is not read-only yet.

Initial local checkout: `main`, `309f8b9a9805d021aeeffb473e8a85c330e0c5c2`,
clean `git status --short`. No remote access, commit, push, pull, branch change or
history rewrite. M01 history recovery was not attempted.

## Root cause and write-path trace

Before M02:

```text
import plumville_app → metro_stops → legacy_core (module initialization)
  → _reload_network_data → _load_network_payload
    → normalizers report changes
      → _write_network_payload → core.network.write_network_payload
        → record_history_snapshot → create snapshot / prune oldest above 100
        → overwrite last-snapshot backup → overwrite canonical JSON
```

`_line_tunneled_stop_vars_from_payload()` returns frozensets for membership tests.
Converting those sets directly to lists made normalized JSON depend on Python's
hash seed. Identical memberships could therefore cause apparent changes on every
import. Both the load normalizer and the explicit tunneling mutation initializer
had this conversion. They now traverse `line_stop_vars` and filter by membership:
line traversal order is preserved rather than alphabetically sorting station IDs.

Additional automatic writes traced:

| Path | Before | M02 disposition |
| --- | --- | --- |
| Constructor/redraw → legacy and desktop Priority List refresh | `_write_priority_list_csv` wrote derived CSV on viewing/filter/route refresh | Refresh stores rows in memory; explicit **Export Priority CSV** action writes the same unfiltered export rows |
| World-map underlay → display image → async preview worker | Worker created cache directory and wrote a thumbnail PNG | Worker queues a Pillow image; Tk thread retains the generated preview in memory; existing disk previews may still be read |
| World-map startup cached status | Loads config/cache and formats text | Already read-only; regression proves no `ensure_layout` call and no new files |
| Worldgen live status / CLI status → `is_service_running` → `ensure_layout` | Creates directories and rewrites environment state | **M03 candidate — read-only worldgen status**; not executed against real data in M02 |
| Path detection `_load_state` | Reads JSON/defaults only | Unchanged; saving detected paths/block classifications remains an explicit operation |
| Public validation / preview check / JS smoke | Reads assets, parses and validates | Unchanged; isolated npm checks pass |
| Network editing / station extension save / detected path commit | Explicit mutation calls shared network writer | Preserved, now deterministic/validated with atomic canonical replacement |
| Undo | Explicit restore updates canonical/backup and consumes a history entry | Preserved; existing temporary-fixture history tests pass |
| PNG export / worldgen generate/render/load/repair | Explicit output/runtime actions | Preserved; no such real-world action was executed in M02 |
| Performance probe | Reads/calculates; optional explicit output; temporary asset-copy measurement | Imports now read-only; use isolated runner because worldgen planning can inspect configured runtime |

Search covered all Python write/mkdir/unlink/save calls in the network/desktop
load path, root extensions, core persistence, analysis/suggestions, test suite and
scripts, plus module initialization and worldgen status reachability. No other
network or history writer remains reachable from load/import/validation. Explicit
worldgen jobs remain separate from the canonical network persistence boundary.

## New persistence flow

```text
read → parse → _normalize_network_payload (memory only) → use/validate

explicit edit/save
  → deterministic in-memory normalization
  → validate_network_payload (does not install globals)
  → serialize and compare to current bytes
      identical: return without touching files
      changed: stage UTF-8 file beside canonical file, flush/fsync
        → existing history retention and backup behavior
        → atomic filesystem replace of canonical JSON
```

The writer preserves existing canonical file permissions. Failed staging leaves
canonical/backup/history untouched. Failed final replacement leaves canonical
bytes intact and removes the staging file. Backup/history may already have been
updated at that point: this is atomic replacement of **one canonical file**, not a
multi-file transaction or concurrent-writer protocol. Undo's existing write path
was not redesigned. These limits require a later transactional design if worlds
become shared by multiple processes.

The canonical JSON format, IDs, coordinate conventions, backup/history names,
and explicit save/undo features are unchanged. On the next genuine save,
normalization may persist defaults/order changes that were formerly written on
read. No migration or normalization of real data was performed during M02.

## Changed files

| File | Why |
| --- | --- |
| `legacy_core.py` | Shared memory-only normalizer, read/write separation, line-sequence membership ordering in both paths; explicit CSV export; memory-only terrain preview |
| `plumville/core/network.py` | Pure aggregate save validation using existing validators; staged atomic canonical write and unchanged-save no-op |
| `desktop_improvements.py` | Remove CSV output from active desktop Priority List refresh; retain export rows in memory |
| `scripts/run_isolated_tests.py` | Reproducible disposable source/public-fixture runner, synthetic worldgen config, temporary caches |
| `scripts/test_io_guard.py` | Python audit guard blocks host repository reads, out-of-fixture writes and runtime-service connections/launches in isolated checks |
| `tests/test_read_only_persistence.py` | Thirteen synthetic persistence, import, hash-seed, failure-path and isolation regressions |
| `MIGRATION_INVENTORY.md` | Narrow update to actual persistence, CSV and preview behavior; M01 history remains historical |
| `notes.txt`, `file_priority.txt` | M02 acceptance and safe testing workflow; worldgen status becomes next priority |
| `M02_PERSISTENCE_REPORT.md` | Root cause, call graph, exact verification, limits and manual checks |

## Test isolation

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_isolated_tests.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_isolated_tests.py -- python3 -m unittest tests.test_read_only_persistence
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_isolated_tests.py -- npm run test:paths
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_isolated_tests.py -- npm test
```

The runner obtains tracked/nonignored source candidates from local Git metadata,
then allowlists source/public files. It excludes private history, backups,
worldgen data/output, exports, dependencies, ignored caches and personal config.
It never follows source symlinks. It uses a synthetic worldgen TOML with no real
world paths, LAN address, credentials or personal settings. The public JSON is
copied as a read-only reference fixture; mutation regressions construct their own
small synthetic network. Existing mutation tests already inject temporary network,
backup and history paths or mock the writer; those tests were retained.

Python bytecode and npm caches are confined/disabled for these checks. `TMPDIR`
points inside the disposable sandbox. Python child processes inherit a
`sitecustomize` audit guard. It rejects host-repository reads, writes outside the
sandbox, network connections and runtime-service subprocesses. It is a regression
guard for trusted tests, not a security sandbox against arbitrary native code.
Node public checks were inspected as read-only; Python hooks do not intercept
Node filesystem operations. No Node installation was performed.

Direct legacy loading now has no persistence side effects. The runner is still
the supported way to run the full suite without discovering local configuration
or runtime merely because tests happen to execute on a developer's Mac. Test
bodies that mutate existing files remain confined to temporary fixtures. No
production environment-variable path override or test mode was added to the app.

## Regression evidence

Every test below is in `tests/test_read_only_persistence.py` and passes:

1. `test_entrypoint_imports_and_extension_application_do_not_write`: imports real
   entrypoint/extension code with a temporary synthetic legacy data root; compares
   hashes, mtimes and tree membership; repeated apply remains safe.
2. `test_load_normalizes_in_memory_without_touching_files`: canonical disk bytes
   remain raw while returned values include normalized defaults/memberships.
3. `test_repeated_reads_reload_and_validation_do_not_rotate_full_history`: repeated
   load, reload, validation and module reload preserve 106 sentinel history files,
   intentionally exceeding retention limit.
4. `test_import_does_not_create_absent_backup_or_history`: no persistence files or
   directories are created where none existed.
5. `test_explicit_mutation_saves_and_preserves_prior_bytes_in_history`: edits a
   station; canonical data changes, prior bytes enter backup and one new snapshot;
   repeated unchanged explicit save leaves hashes and mtimes alone.
6. `test_tunneled_membership_serialization_is_stable_across_hash_seeds_and_orders`:
   reversed lists, sets and frozensets yield the same serialized output under
   `PYTHONHASHSEED` 1, 7, 31 and 123; nonalphabetical line order is retained.
7. `test_invalid_explicit_save_does_not_write_or_install_globals`: validation
   precedes persistence and leaves active station state unchanged.
8. `test_staging_failure_leaves_canonical_backup_and_history_unchanged`: injected
   fsync error leaves original files and history intact; no staging file remains.
9. `test_atomic_replace_failure_leaves_canonical_file_intact`: injected replacement
   failure cannot truncate canonical data; temporary file is cleaned up.
10. `test_priority_refresh_is_read_only_and_export_is_explicit`: legacy/desktop
    refresh leave CSV intact; explicit export writes it.
11. `test_terrain_preview_is_cached_in_memory_without_disk_output`: executes the
    preview worker/poll with synthetic pixels; no cache directory/PNG is created.
12. `test_cached_startup_status_does_not_initialize_worldgen`: synthetic cached
    status makes no files and does not invoke runtime initialization.
13. `test_isolation_guard_rejects_host_access`: child attempts to read host data
    and write outside its fixture are rejected before touching disk.

Five selected read/import/hash-seed/CSV/preview tests were also run against an
untouched temporary copy of M01 production code: **5 expected failures**. They
pass against M02. Existing core tests continue to prove first-save behavior,
duplicate-snapshot suppression, retention on genuine saves, and both undo paths.

## Exact checks and baseline comparison

Baseline used a temporary copy of tracked source before edits, not real runtime.
Post-change commands used the isolated runner above; no application imports or
executable tests ran against real data. Versions: Python 3.13.7, Node v24.11.1,
npm 11.6.2 (same local executables as M01).

| Command inside isolated source root | Baseline | Final |
| --- | --- | --- |
| `python3 -m py_compile ui_extensions.py desktop_improvements.py path_detection.py metro_station_extensions.py` | PASS | PASS; also compiled legacy/core writer, both runner modules and regression tests |
| `python3 -m unittest tests.test_read_only_persistence tests.test_core_network tests.test_entrypoints_and_public_output` | New tests absent | PASS: 54 tests |
| `python3 -m unittest discover -s tests` | FAIL: 291 tests, 2 failures + 2 errors | FAIL: 304 tests, same 2 failures + 2 errors |
| `npm run test:paths` | PASS: 5 tests | PASS: 5 tests |
| `npm test` | PASS | PASS: docs smoke, public validation, preview check |
| `git diff --check` (actual repository) | Initial clean tree | PASS |
| `PLUMVILLE_RUN_TK_SMOKE=1 npm run smoke:tk` | SKIP | SKIP: no live-data GUI launch; existing display limitation is not a persistence failure |
| `python3 plumville_app.py`, `python3 metro_stops.py` | SKIP GUI | Entry imports/reapply proven with synthetic data; interactive GUI remains unverified |
| `python3 -m worldgen status` | SKIP | SKIP: known write-through-layout path deferred to M03 |

Unchanged `test_station_signage` cases:

- ERROR `test_corrected_line_c_junctions_remain_in_path_specs` (`P_CU5`).
- ERROR `test_placeholder_junction_labels_do_not_get_repeated_suffixes` (`P_GHI`).
- FAIL `test_direction_lists_can_be_flipped`.
- FAIL `test_triarchidia_default_direction_lists_match_example_layout`.

No signage assertions were changed. No new full-suite regressions occurred.

## Data safety and acceptance

No real/private runtime data changed during M02. All executable probes used
isolated source/synthetic files. Initial/final ignored-file metadata comparisons
show zero changed, removed or added files. Tracked data/config/assets are checked
against initial SHA-256 digests; they remain unchanged. Metadata comparisons are
not a cryptographic content audit of private world files; no private contents or
filenames were exposed. No history deletion/recovery was attempted in the real
workspace. Test-only retention tests intentionally operate on disposable history.

All nine M02 automated acceptance criteria are satisfied by the checks above.
M02 implementation/test checklist items move `[~]` → `[x]`. Manual GUI checks
stay `[ ]`; M01's historical incident is not retroactively marked resolved.

## User verification and next run

On disposable test data:

1. Open/read/reload and change route/priority filters; verify JSON, backup,
   history and CSV stay unchanged. Displaying terrain should create no disk preview.
2. Make a station edit and save; verify canonical change, previous-state backup
   and history; verify Undo still restores it.
3. Use **Export Priority CSV** and check that `priority_list.csv` updates only
   then, with the same export columns and unfiltered priority rows.

Recommend **M03 — worldgen read-only/status safety** before the Swift interchange
contract. The CLI/live-status path still writes environment state through
`ensure_layout`; it is a separate subsystem and was not refactored in M02.
