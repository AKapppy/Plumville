# M01 — Migration Readiness Cleanup and Architecture Inventory

Result: **PARTIAL**. Architecture inventory and a small verified code cleanup are
complete. Live GUI verification is unavailable; baseline signage tests remain red.
A data-safety incident during baseline probes prevents a claim that all runtime
files were preserved unchanged. No Swift, Xcode, accounts or cloud work was begun.

## Local baseline and method

Initial branch `main`; commit `b6c26cf update`; initial `git status --short` empty.
Read AGENTS.md, notes.txt, file_priority.txt and CODEX_TASK.md. The explicit M01
request supersedes the older D01 scope for this run. No network/GitHub inspection.
Python 3.13.7, Node v24.11.1, npm 11.6.2.

Size audit traversed the full local tree, including ignored/untracked files,
without following directory symlinks. Logical file lengths, not allocated disk
blocks, are reported; sparse files, compression and cloud storage can differ.
Git tracking/ignore metadata classified each file. Private member names/content
are omitted. The first measurement followed baseline execution and preceded code
changes; it is not a pre-test runtime snapshot. No nonignored untracked files
existed then. Tracked source listings include active data/assets/development files.

## Cleanup performed and proof

| File | Change | Safety evidence | Size effect |
| --- | --- | --- | --- |
| `path_detection.py` | Remove `_patched_refresh_station_stats`, its original-method global and installer assignments | Entire wrapper only asserted/called original; repository search found all references confined to its own declaration/installation; no side effects, extra arguments or return-value handling. Statistics stay on original viewer method. Drawing and station-detection hooks remain installed in the same order. | 461 bytes removed |
| `tests/test_entrypoints_and_public_output.py` | Add subprocess regression for repeated detection apply, statistics identity and exactly-once statistics/edge/node calls | Test fails before cleanup and passes afterward; mocks avoid GUI and suppress legacy import-time persistence | Development coverage added |
| `MIGRATION_INVENTORY.md` | Models, logic, persistence, UI, rendering, worldgen, web, disposition and every core top-level symbol | Static source ownership inventory, no data export | Documentation added |
| `M01_AUDIT_REPORT.md` | Measurements, audit findings, test results, safety incident and manual checks | Reviewable local report, private details redacted | Documentation added |
| `notes.txt`, `file_priority.txt` | M01 scope/status and future priority | Preserve earlier visual checkboxes and history | Documentation added |

No files deleted, no ignored/runtime cleanup, no dependency removals or schema
changes. No claimed material speed improvement: removing a wrapper reduces
indirection, not the large cost of rendering. Net project source size grows from
useful documentation/tests. An unused `Any` import in core public export was
identified but left outside the coherent path-hook cleanup.

## Safety incident and limits

Baseline tests/imports and GUI launch probes exercised legacy import-time loading.
`_normalize_line_tunneled_stop_vars` serializes frozensets in nondeterministic
order; `_load_network_payload` persists that normalization on import. It updated
the tracked network JSON, private last-snapshot file and rotating history.

The tracked JSON was restored byte-for-byte to the initial clean HEAD version
ONLY after comparing every JSON field and verifying the sole difference was
ordering within per-line tunneled memberships. No user edits existed initially.
No destructive Git restore/reset/checkout command was used.

A metadata comparison against the post-baseline size scan found the private
last-snapshot file changed and **four pre-existing history files missing**. The
normal history writer prunes past 100 entries; the probes can trigger this. The
scan was after initial tests, so it cannot establish the total pre-test impact.
Original private contents were not backed up by this audit and cannot be safely
reconstructed from metadata. No further private-history edits were attempted.
Recovery of those history entries requires an existing external backup, if any.

One `.worldgen` file also changed: `status()` calls `is_service_running()`, which
calls `ensure_layout()` and writes the environment file. Thus status exits zero
but is not fully read-only. Twelve dependency files had metadata changes; their
cause was not established, and no dependency deletion/install was performed.
No observed size/mtime changes in worldgen data/output at the later comparison.
This is metadata evidence, not a content-hash guarantee for private world data.

All subsequent executable Python checks ran in a temporary copy of tracked source
at `/tmp/plumville-m01/isolated`, with no private data copied. That keeps any
existing import normalization confined to disposable test files. The added
regression itself uses mocks and a child interpreter, and suppresses the legacy
persistence writer during import so it cannot save real network data. No more live-data probes
are warranted until read-only loading and isolated test discovery are addressed.

## Architecture responsibility audit

Classification is multi-axis: ACTIVE code can also be DOMAIN LOGIC, TK/UI or
COMPATIBILITY. Similarity alone never establishes DEAD code.

| `legacy_core.py` area | Responsibilities | Classification / action |
| --- | --- | --- |
| 273–995 | Typed records, stations, endpoints, nodes, PoIs, alignments, segments, construction | ACTIVE / DOMAIN LOGIC with globals; PoI dialogs mixed in; preserve |
| 1006–1930 | Coordinate parsing, runtime lookup, snapping, turn geometry, alignment traversal | ACTIVE / DOMAIN LOGIC and COMPATIBILITY adapters to core |
| 1930–2658 | Map transforms, label/signage rules, SVG structures and renderer | ACTIVE / DOMAIN LOGIC + rendering adapter; signage baseline broken |
| 2658–2812 | Edge indexing, geometry/time wrappers | ACTIVE / COMPATIBILITY; core owns reusable math/formatting |
| 2841–4115 | World-map status, image/cache selection, generation jobs and render/export primitives | ACTIVE / adapter + rendering + backend orchestration |
| 4133–5787 | Station needs, priority CSV/ranking, frontier, construction intervals/chimes/railway progress | ACTIVE / DOMAIN LOGIC; split calculation from writes/UI later |
| 5863–6500 | Route graph adapters, city anchors, shortest/preferred routes, hull/intersection | ACTIVE / DOMAIN LOGIC; core route engine remains canonical |
| `MetroMapViewer` through 15204 | Tk root, panels, inspector callbacks, menus/dialogs, search/routes, edit state, export, redraw, mouse/keyboard | ACTIVE / TK/UI mixed with mutation/rendering; do not port literally |
| 15333–15690 | Persistence adapters, normalizers, loading, global network projection/validation | ACTIVE / COMPATIBILITY + persistence; import writes are high risk |
| 15711–end | Station/line/path/alignment/city mutations and import-time `_reload_network_data()` | ACTIVE / DOMAIN LOGIC coupled to persistence; high-risk extraction |

No legacy body removed. The responsibility map establishes likely future seams,
not a proof that every branch has been exercised.

| `desktop_improvements.py` area | Audit finding |
| --- | --- |
| Constants/models through 358 | Active palette/modes/marker geometry, some aliases; future theme consolidation |
| 359–972 | Active button/sidebar/dialog styling; recursive style traversal and legacy palette mutation; repeated visual tokens across desktop files |
| 973–1152 | Active mode state/filtering; shell construction delegated to workspace; `install_mode_rail` name survives although visible control is a dropdown |
| 1153–1337 | Active route fitting and scheduled wrappers; bounds helper is portable; scheduling/cancel guards preserve unrelated redraw behavior |
| 1338–1639 | Active priority filtering and worldgen completion/visibility; domain decisions mixed with widgets; priority wrapper replaces legacy body |
| 1640–2168 | Active docked-inspector bridges AND popup fallback styling/actions; similar inspector actions do not make fallback unreachable |
| 2169–2267 | Active experimental path-detection entry and sidebar section capture |
| 2268–2390 | Active decorative station overlay, redraw/inspector sync and route-panel construction bridge; potential duplicate render work |
| 2391–end | Active installer, saved original methods, class/module idempotency and reload recovery; preserve extension order |

`metro_station_extensions.py` owns membership/ID renaming and validation (48–482),
map previews (494–646), save/mutation operations (647–850), and station/line
chooser/reorder/add dialogs through 1750. `apply` installs preview redraw and
station actions; inspector uses these operations. `_center_dialog` matches legacy
but is dynamically rebound by desktop styling. `_line_membership_from_payload`
matches legacy; both have active mutation callers. Extracting either requires
preserving patch/validation contracts, so neither was removed.

The inventory covers every current desktop/core/worldgen module. Package marker
files and old import shims remain. No obsolete module was proven safely removable.

## Redundancy search and deferred cleanup

AST scan covered tracked Python imports and top-level exact function bodies;
repository reference searches covered wrappers and entrypoints. Dynamic callbacks,
monkey patches and public import names prevent treating single references or
unused-import scanner results as deletion proof. There was no broad dead-code
scanner-driven purge, no confirmed tracked temporary artifact to delete, and no
reason to remove active image assets.

| Priority | Opportunity / evidence | Why deferred |
| --- | --- | --- |
| HIGH VALUE | Read-only load and deterministic tunneled-list serialization (`legacy_core.py:15473,15486`, final module call); isolated entrypoint/test fixtures | Proven data-safety prerequisite; needs focused persistence regression coverage and private-data protection |
| HIGH VALUE | Separate legacy domain commands from global payload writes, then provide world-scoped repository | Largest maintenance/migration seam; broad refactor prohibited in M01 |
| HIGH VALUE | Make requirements reproducible: NumPy imported by village paths but missing from requirements; audit clean install | Existing environment passes imports; dependency change needs separate concrete setup validation |
| MEDIUM VALUE | Exact retry I/O bodies in `worldgen/cache.py:46,67`, `generator.py:1585,1606`, `render.py:1325` | Same text, but monkey-patched tests/global dependencies and retry semantics need contract tests |
| MEDIUM VALUE | Duplicate popup/inspector action discovery (`desktop_improvements.py:1777`, inspector:1336), theme tokens and badge contrast helpers | Both docked and fallback UI paths remain active |
| MEDIUM VALUE | Station membership helpers (legacy:15789, station extension:743), anchor record helpers (15785 / 48), dialog centering (656 / 483) | Different consumers and dynamic rebinding; extract later |
| MEDIUM VALUE | GUI smoke expects `Add Path` while actual control is `Editing Mode`; inspect live section visibility before updating | Environment aborts before assertions; this mismatch is static evidence, not a newly observed GUI failure |
| LOW VALUE | Duplicate line-distance aliases (legacy:2825 / 5703), metadata-path helpers (legacy:3287 / generator:1665), sampled-axis helpers (generator:2056 / render:1469) | Tiny byte savings; preserve callers until focused consolidation |
| LOW VALUE | Unused `Any` import in core public export; symbol aliases and no-op shim modules | Small maintenance savings; worldgen `__init__` imports are intentional API re-exports |
| LOW VALUE | Local Python caches and Node dependencies are regeneratable | Explicitly protected ignored files; no deletion authorized by being regeneratable |

## Performance observations

Static hypotheses except where observed; no end-to-end speed benchmarks claimed.
Existing `scripts/performance_probe.py` should run only against isolated source.

| Rank | Source | Finding / measurement recommended |
| --- | --- | --- |
| HIGH IMPACT | legacy:15473–15517; core network:1129–1180 | Import-triggered order churn reparses/writes large JSON and rotates history. Reproduce across hash seeds on synthetic fixture; fix correctness first |
| HIGH IMPACT | legacy `redraw:13406`; desktop `_patched_redraw:2330`; inspector `_render_selected_stop:112` | Canvas delete-all and redraw, station decoration and inspector body destruction/rebuild cascade. Measure frame and widget counts for unchanged selection; existing dirty/deferred-layer flags mitigate some work |
| HIGH IMPACT | walking suggestions `TerrainGrid._populate_grid:99`, `build_suggested_segments:1672`; legacy `_draw_suggested_walking_paths:14551` | Cold terrain grid scans image pixels; route candidate tree may run during drawing. Existing terrain/suggestion caches avoid some repeats; profile cold vs warm before adding workers |
| MEDIUM IMPACT | legacy `_priority_list_entries:4262`, `_route_costs_from_endpoint_key:6281`; desktop priority wrapper:1619 | Route/frontier recomputation and CSV serialization on priority refresh. Inspect invalidation/coalesce refreshes; do not remove exports silently |
| MEDIUM IMPACT | legacy underlay helpers:3391–3640, PNG export:12884 | Large image decoding/cropping/resizing/export; caches exist. Profile peak memory and cache misses; retain block-level quality |
| MEDIUM IMPACT | desktop `_style_dialog_widget_tree:496`; inspector `_clear_inspector_body:633` | Recursive style traversal and repeated widget construction; explicit native component lifecycle later |
| MEDIUM IMPACT | generator `status:1255`, `is_service_running:357`, `ensure_layout:217` | Status performs filesystem writes and Docker checks; separate read-only status from setup |
| LOW IMPACT | removed path-detection statistics wrapper | One redundant Python call eliminated; negligible wall-clock benefit |

## Tests and entrypoints

Baseline ran from the real repository root as requested. Post-cleanup Python/npm
checks ran from the root of the isolated tracked-source copy after discovering
import writes. Commands are unchanged; this location difference is material.

| Exact command | Baseline | After cleanup |
| --- | --- | --- |
| `python3 -m py_compile ui_extensions.py desktop_improvements.py path_detection.py metro_station_extensions.py` | PASS | PASS |
| `python3 -m unittest discover -s tests` | FAIL: 290 tests, 2 failures + 2 errors | FAIL: 291 tests, identical 2 failures + 2 errors |
| `npm run test:paths` | PASS: 5 tests | PASS: 5 tests |
| `npm test` | PASS: smoke:docs, validate:public, preview:public:check | PASS: same three checks |
| `git diff --check` | PASS | PASS in actual repository |
| `PLUMVILLE_RUN_TK_SMOKE=1 npm run smoke:tk` | Environment-limited FAIL: SIGABRT, subprocess return -6 (shell 134) | SKIP repeat; no interactive display validation |
| `python3 plumville_app.py` | Environment-limited FAIL: SIGABRT, return -6, no application traceback | SKIP repeat; live-data import unsafe |
| `python3 metro_stops.py` | Environment-limited FAIL: SIGABRT, return -6, no application traceback | SKIP repeat; live-data import unsafe |
| `python3 -m worldgen status` | PASS exit 0; status has environment-file write side effect | SKIP repeat against private runtime |
| `python3 -m unittest tests.test_entrypoints_and_public_output.EntrypointAndPublicOutputTests.test_path_detection_preserves_statistics_and_draw_hooks` | Expected FAIL with old wrapper (new test) | Covered by passing targeted suite |
| `python3 -m unittest tests.test_entrypoints_and_public_output tests.test_desktop_improvements tests.test_village_paths` | Not run as a separate baseline group | PASS: 64 tests |

Unchanged signage cases in `tests/test_station_signage.py`:

- ERROR `test_corrected_line_c_junctions_remain_in_path_specs`: missing `P_CU5`.
- ERROR `test_placeholder_junction_labels_do_not_get_repeated_suffixes`: missing `P_GHI`.
- FAIL `test_direction_lists_can_be_flipped`: actual direction list differs from fixture.
- FAIL `test_triarchidia_default_direction_lists_match_example_layout`: same list mismatch.

Tests were not weakened and runtime data was not edited to satisfy assertions.
Baseline executable probes nevertheless caused the side effects documented above.

## User checks — leave unchecked

Use a backed-up/disposable world copy until import safety is fixed.

1. Launch desktop; verify Priority List All needs / Line B wrapping and resizing.
2. Verify path Editing Mode: empty click adds node, node drag connects, non-node
   drag pans, inspector/popup clicks do not create underlying nodes.
3. Verify Active Coordinates/snap and arrow crosshair movement; Connect via typed
   endpoint and Click to Select retains original source and suppresses empty clicks.
4. Verify station inspector statistics, signs/directional navigation, station and
   metro editing, city limits, route/search, undo and PNG export on disposable data.
5. Review migration inventory and available external backups for history recovery.

## Checklist and next run

M01 audit and hook cleanup moved `[~]` → `[x]` for written inventory and passing
focused checks only. A separate `[blocked]` safety acceptance records that runtime
preservation cannot be claimed. Existing visual `[verify]` items and all manual
boxes remain unchanged/unchecked. Swift/accounts/cloud work remains `[hold]`.
Next recommended run: read-only loading and isolated-test safety, then baseline
signage fixture investigation. No next implementation slice begun.

## Git safety

No commit, push, pull, branch change or history rewrite. No private content copied
into these reports. The final status and size snapshot are appended below.

## Measured size report

Decimal MB/GB; bytes below are authoritative. After snapshot includes reports
as written at measurement time; final report/checklist append adds a few KB.
Ignored totals are **not all disposable generated data**. Private world data,
history, local state and dependencies are included.

| Category | Before bytes | After snapshot bytes |
| --- | ---: | ---: |
| tracked | 29,827,359 | 29,831,659 |
| ignored | 3,836,272,970 | 3,836,351,380 |
| git | 312,334,017 | 312,334,017 |
| untracked | 0 | 47,314 |
| Total folder logical size | 4,178,434,346 | 4,178,564,370 |

Tracked files initially total **29.83 MB**, ignored files **3.836 GB**,
Git **312.33 MB**, total **4.178 GB**. Production code reduction: **461
bytes**. No disk-space reduction target was pursued. Net source/docs grow.

### Largest local directory categories (before)

| Root | Bytes | Classification / retained reason |
| --- | ---: | --- |
| `worldgen_data` | 3,245,327,667 | REQUIRED AT RUNTIME / UNKNOWN private members; Bedrock and cache data protected |
| `node_modules` | 497,095,145 | REQUIRED FOR DEVELOPMENT and worldgen; REGENERATABLE but protected |
| `.git` | 312,334,017 | REQUIRED FOR DEVELOPMENT: history, retained |
| `metro_network.history` | 63,982,485 | REQUIRED AT RUNTIME: private undo/history; protected |
| `docs` | 21,860,737 | REQUIRED AT RUNTIME: active public product |
| `exports` | 21,458,989 | Private exports; protected, not disposable |
| `data` | 5,989,823 | HISTORICAL/REFERENCE mockups, retained |
| `worldgen_output` | 5,585,154 | REGENERATABLE outputs / REQUIRED AT RUNTIME when consumed; protected |
| `__pycache__` | 1,100,678 | REGENERATABLE Python cache; retained |

All Python cache directories currently total 2,185,225 bytes. No build/dist,
pytest cache or nonignored untracked directory was present in the initial tree.
Docker source is root compose YAML (1,953 bytes), worldgen helpers and Node
loader; actual worldgen storage dominates, not orchestration source. Temporary
probe output was written outside the repository.

### Largest tracked files

| File | Bytes | Classification |
| --- | ---: | --- |
| `docs/assets/blackport_topdown.png` | 20,954,842 | REQUIRED AT RUNTIME; generated terrain asset, regeneration is not deletion proof |
| `data/mockups/ChatGPT Image Jul 25, 2026 at 02_28_32 PM (2).png` | 2,130,389 | HISTORICAL/REFERENCE; current visual checklist still cites it |
| `data/mockups/ChatGPT Image Jul 25, 2026 at 02_28_32 PM (1).png` | 2,009,697 | HISTORICAL/REFERENCE; current visual checklist still cites it |
| `data/mockups/ChatGPT Image Jul 25, 2026 at 02_28_32 PM (3).png` | 1,848,522 | HISTORICAL/REFERENCE; current visual checklist still cites it |
| `legacy_core.py` | 667,244 | REQUIRED AT RUNTIME (source) |
| `docs/metro_network.json` | 646,168 | REQUIRED AT RUNTIME; canonical data, not a disposable export |
| `docs/app.js` | 145,612 | REQUIRED AT RUNTIME (source) |
| `worldgen/generator.py` | 114,390 | REQUIRED AT RUNTIME (source) |
| `notes.txt` | 80,788 | REQUIRED FOR DEVELOPMENT |
| `desktop_improvements.py` | 74,599 | REQUIRED AT RUNTIME (source) |
| `docs/assets/blackport_lan_surface.png` | 72,961 | REQUIRED AT RUNTIME; generated terrain asset, regeneration is not deletion proof |
| `worldgen/render.py` | 71,660 | REQUIRED AT RUNTIME (source) |
| `metro_station_extensions.py` | 66,236 | REQUIRED AT RUNTIME (source) |
| `walking_suggestions.py` | 64,563 | REQUIRED AT RUNTIME (source) |
| `package-lock.json` | 61,284 | REQUIRED FOR DEVELOPMENT |
| `tests/test_desktop_improvements.py` | 55,619 | REQUIRED FOR DEVELOPMENT |
| `worldgen/unknown_diagnostics.py` | 54,513 | REQUIRED AT RUNTIME (source) |
| `plumville/desktop/inspector.py` | 48,499 | REQUIRED AT RUNTIME (source) |
| `plumville/core/network.py` | 44,179 | REQUIRED AT RUNTIME (source) |
| `tests/test_walking_suggestions.py` | 41,711 | REQUIRED FOR DEVELOPMENT |
| `tests/test_core_network.py` | 41,662 | REQUIRED FOR DEVELOPMENT |
| `path_detection.py` | 35,091 | REQUIRED AT RUNTIME (source) |
| `worldgen/village_paths.py` | 32,346 | REQUIRED AT RUNTIME (source) |
| `worldgen/bedrock_chunks.py` | 25,352 | REQUIRED AT RUNTIME (source) |
| `tests/test_desktop_inspector.py` | 24,054 | REQUIRED FOR DEVELOPMENT |

### Tracked directory totals

- `docs`: 21,860,737 bytes.
- `data`: 5,989,823 bytes.
- `(root files)`: 1,119,330 bytes.
- `tests`: 357,668 bytes.
- `worldgen`: 343,476 bytes.
- `plumville`: 140,578 bytes.
- `scripts`: 12,590 bytes.
- `tools`: 3,157 bytes.

### Largest local files and history

The two largest local files are protected worldgen members of 1,303,160,889
and 1,082,062,114 bytes; member names omitted. Additional worldgen members
are 213,421,632 and 213,391,792 bytes. A private export is 21,452,841 bytes.
These are not classified SAFE TO REMOVE. Dependency files are regeneratable
but no individual dependency was proven unused. No duplicate private contents
were read or hashed for deletion decisions.

Git count-objects: 93 loose objects, 2,020 KiB; 1,376 packed objects in two
packs, 303,114 KiB; zero garbage. Metadata-only reachable-blob enumeration
found repeated historical versions of the public topdown PNG: 20,954,842,
14,315,775, 10,146,469, 8,779,271 and 6,211,664 bytes among the largest.
Historical image revisions are significant; uncompressed blob lengths must
not be summed as packed disk savings because Git compression/deltas differ.
No repack/prune or history rewrite performed.

### Final changed-file status

```text
 M file_priority.txt
 M notes.txt
 M path_detection.py
 M tests/test_entrypoints_and_public_output.py
?? M01_AUDIT_REPORT.md
?? MIGRATION_INVENTORY.md
```

Tracked public network data has no remaining diff. This status does not show
ignored backup/history/environment changes; see the safety incident above.
