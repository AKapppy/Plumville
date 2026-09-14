# Plumville migration inventory — M01

Local checkout audit, 2026-09-14; initial branch `main`, commit `b6c26cf`, clean
status. No GitHub lookup. This describes the current Python application, not an
implemented Swift design. M01 does not create an Xcode project or change schemas.
See `M01_AUDIT_REPORT.md` for measurements, cleanup evidence, tests, and limitations.

## 1. Domain Models

Source coordinates use `x,y` for the horizontal Minecraft `x,z` plane. Plot
coordinates negate the second component. Preserve that distinction explicitly.
Record IDs, labels, abbreviations, and coordinates have different meanings.

| Concept | Current owner | Persistence and relationships | Swift concept? |
| --- | --- | --- | --- |
| World | `worldgen/config.py:WorldConfig`, `WorldgenConfig`; legacy module globals | TOML configuration, separate terrain/cache files and network JSON; no general account-owned World aggregate | Yes: explicit world identity and scoped repositories, later |
| Station | `legacy_core.py:MetroStop`, `StopRecord` | `stops[]`: `var`, `lbl`, `abbr`, coordinates, checkpoints; joins ordered line memberships by `var` | Yes |
| Metro Line / Segment | legacy `MetroLineSegment`, `LinePathPointSpec`; core network | `line_stop_vars`, `line_colors`, `wool_colors`, `line_path_specs`; ordered stop references plus turn/offset geometry | Yes; do not infer ordering from station names |
| Station Entrance | `MetroStop.station_entry_coordinates`, `walking_coordinates` | Optional `station_entry_x/y` on stop; walking endpoint falls back to station | Yes |
| Path Node / PoI | legacy `PathNode`, `AddedPoi`; core `normalize_path_nodes` | `path_nodes[]`, positive numeric `node_<number>` IDs, labels/categories separate; coordinate endpoints and city-limit references | Yes |
| Walking Path / Connector | legacy `ExtraEdgeDefinition`, `PathEndpoint` | `extra_edges[]`: kind, endpoints, bidirectionality, path points; connects stations and coordinates | Yes; preserve connector distinction |
| Alignment | legacy `AlignmentReminder`; core normalizer | `alignment_reminders[]`: first/second station references and axis; line traversal determines included stations | Yes |
| City Limit | legacy polygon/pathing helpers; core `normalize_city_limits` | Stop `city_limit_node_keys`; polygon references saved path nodes; routing can anchor into city boundary | Yes |
| Signage | legacy `_station_signage_label`, `_station_signage_direction_stop_vars`; inspector | Derived line-direction lists and junction suffixes; stop signs/chimes checkpoint fields; no independent sign-document aggregate | Yes; navigation and completion are separate concerns |
| Construction State | legacy `RailwaySegmentConstructionStatus`, checkpoint helpers | Stop booleans/chime directions, `line_tunneled_stop_vars`, railway finish progress/origins; connected implies tunneled | Yes; keep per-line tunneling distinct at shared stations |
| Priority Item | legacy `_priority_list_entries`, desktop filter wrapper | Derived route/work/frontier ranking; CSV and public export are projections, not separate mutable station records | Yes |
| Route | core routing dataclasses | Derived graph edges/steps/results, request endpoints and options held in UI | Yes |
| Suggested Path | `walking_suggestions.py:SuggestedSegment`, `TerrainGrid` | Derived tree/frontier routes; public `suggested_walking_segments` projection; distinct from saved edges | Yes |

## 2. Domain Logic

| Responsibility | Current implementation | Boundary and disposition |
| --- | --- | --- |
| Distance, projection, midpoint | `plumville/core/geometry.py` | PORT ALGORITHM/LOGIC TO SWIFT; preserve integer rounding and float variants |
| Parsing / identity | core `network.parse_coordinate_text`, `text` | PORT ALGORITHM/LOGIC TO SWIFT; keep placeholder labels, abbreviations and normalization behavior |
| Network normalization / validation | core `network.py` | Portable JSON rules; Python dict/TypedDict mechanics are implementation details |
| Routing | core `routing.build_route_graph`, `shortest_route_edges`, `route_costs_from_nodes`; legacy `_build_route_graph`, `_find_preferred_route` | Port algorithms and deterministic ranking; legacy adds current-world globals, city anchors and mode/flying fallback |
| Path mutation | legacy `add_path_node`, `move_path_node`, edge mutation functions near file end | Port splitting, merging, lowest-free IDs, deduplication and connector preservation after extracting a repository-independent transaction boundary |
| Walking suggestions | `walking_suggestions.py:build_suggested_segments` | Port terrain cost, connected components, frontier tree, shared trunks/stems and Minecraft-buildable slopes; Pillow sampling and `base/viewer` adapters need replacement |
| Detected village paths | `worldgen/village_paths.py` | Python/NumPy thinning, connected components and simplification are portable algorithms; Bedrock scanning can stay backend-side |
| Line traversal / turns | legacy `_line_segment_specs`, `_metro_segment_path_specs`, `_line_anchor_distances`; station extension reorder helpers | Port explicit sequence/geometry rules; preserve references when memberships change |
| Snapping / crosshair | legacy `_aligned_active_path_node_coordinates:1059`, `_on_cursor_nudge_key:15106` | Port snap decision; recreate focus/key event handling |
| Construction / priority | legacy checkpoint helpers around 4133–5787; desktop `_priority_entries_named_or_frontier` | Portable rules mixed with globals/UI; extract later with synthetic fixtures |
| City limits | legacy convex hull, polygon intersection, boundary anchors and confirm-to-save mutation | Port geometry/validation; recreate pending selection and task controls |
| Route fit / completion decisions | desktop `_route_fit_bounds_for_points:1176`, `_worldgen_completion_payload_is_verified:1493` | Portable decisions misplaced in UI module; event scheduling and widgets stay desktop-specific |

All six core modules are free of Tk imports. `network.py` is **not entirely
pure**: its bottom section reads/writes files and prunes/restores history.
`public_export.py` mixes portable content validation with filesystem traversal.
The symbol appendix below inventories every top-level core function/class.

## 3. Persistence

| Store / representation | Owner and role | Migration treatment |
| --- | --- | --- |
| `docs/metro_network.json` | `legacy_core.py:36,15486,15520`; current desktop canonical network AND public viewer data | KEEP AS DATA FORMAT; preserve current authority until a separately tested migration |
| JSON serialization / validation | `plumville/core/network.py:1119` onward, legacy adapters around 15333 | Preserve fields, optional defaults and normalization semantics; separate read, normalize and explicit commit |
| Backup and snapshots | `metro_network.last.json`, `metro_network.history/`; core `write_network_payload`, `record_history_snapshot`, `restore_last_network_snapshot` | Private, preserve; future transaction/undo repository, not UI globals |
| Priority CSV | `priority_list.csv`, legacy `_write_priority_list_csv` via explicit Export Priority CSV | Derived export; refresh/filtering now computes rows only |
| Line text | `metro_lines.txt` | Retain as reference; active runtime loads JSON, do not promote text into canonical data |
| Local world settings | `worldgen_config.toml`; `worldgen/config.py`, `paths.py` | Keep configuration contract; separate user configuration from shareable world model |
| Runtime caches / detection state | `.worldgen/`, worldgen data/output, `path_detection_state.json` | Private device/backend state; never bundle into public exports or Swift fixtures |
| PNG / SVG and public render metadata | legacy export builders; `worldgen/render.py`; `docs/assets/` | KEEP AS DATA FORMAT; preserve bounds, sample step, dimensions and coordinate convention |
| UI state | viewer variables, selection/task state and camera | Recreate scoped view state; not an existing account/cloud schema |

**M02 persistence update (2026-09-14):** importing still calls
`_reload_network_data()`, but `_load_network_payload()` now parses and normalizes
only in memory. Both tunneled-membership paths use semantic `line_stop_vars`
sequence order. Explicit `_write_network_payload()` normalizes, validates without
installing globals, then stages the canonical file, retains backup/history and
atomically replaces the destination. An unchanged save touches no files. Backup,
history and canonical replacement are not a multi-file transaction.

Priority refresh no longer writes CSV; the explicit Export Priority CSV action
retains that output. Generated terrain display previews now live in memory;
existing disk previews remain readable. Use `scripts/run_isolated_tests.py` for
source/public fixtures, synthetic config and guarded temporary persistence.
See `M02_PERSISTENCE_REPORT.md` for regression evidence and limits. M01's data
incident remains historical; no recovery was attempted. Worldgen live/CLI status
still writes through `ensure_layout` and is deferred to M03.

## 4. Desktop UI

| Surface | Actual owner | Swift disposition |
| --- | --- | --- |
| Entrypoints | `plumville_app.py` → `metro_stops.py` → legacy `main` / `plot_stops` | RECREATE IN SWIFT; keep Python entrypoints during development |
| Workspace shell | `plumville/desktop/workspace.py:WorkspaceShell`, `_configure_workspace_hosts`, `sync_workspace` | RECREATE IN SWIFT: top bar/mode dropdown, sidebar host, canvas host, scrollable inspector, visibility/center preservation |
| Sidebar / menus | legacy `MetroMapViewer` builders; UI extension capture; desktop mode filtering/styling | RECREATE IN SWIFT, preserving all reachable controls |
| Inspector | `plumville/desktop/inspector.py:sync_inspector` | RECREATE IN SWIFT: station, metro segment, path node, connection choices, pathing town/city-limit context |
| Task editors | inspector `show_metro_turn_editor`, `show_metro_endpoint_editor` | RECREATE IN SWIFT; keep Save/Cancel, temporary preview state and fallback dialogs |
| Station / line dialogs | `metro_station_extensions.py:897–1750`; legacy editors | RECREATE IN SWIFT; port mutation/validation independently |
| Components / theme | constants and builders in desktop improvements, workspace and inspector | No separate theme/components modules exist yet; recreate visual system, do not translate Tk styling wrappers |
| Mouse input | legacy `_on_drag_start:14930`, `_on_drag`, `_on_drag_end`, popup-release suppression | RECREATE IN SWIFT; preserve empty-click node creation, node-to-node connection, non-node pan and click suppression |
| Keyboard / search | legacy suggestion/search handlers, cursor nudge, reset/fit hotkeys | RECREATE IN SWIFT; preserve coordinate search, focus rules, arrow movement and line fit |
| Connect editing | legacy connect state + inspector `_render_path_node_connect_choices` | Original source remains fixed across target clicks; empty clicks create no nodes while connecting |
| Undo / exports | legacy `_undo_last_saved_change:12684`, export dialogs/builders | Recreate UI; port transaction and rendering contracts |

`plumville/desktop/__init__.py` is the package marker. Workspace and inspector
are the only implementation modules in that directory. Both still depend on
`legacy_core`; inspector invokes viewer helpers and station extension actions.

### Extension order and compatibility

`ui_extensions.apply()` guards both module and viewer class. Its order is:
worldgen speedups → metro station extensions → PoI shim → route-panel capture
wrapper → path rendering shim → path detection → world-map shim → desktop
improvements (which installs workspace hooks). Desktop must run after detection:
it deliberately retains detection's original station renderer for normal popup
fallback, omitting detection controls there. Docked inspector rendering is routed
through desktop redraw. Metro station preview redraw remains underneath it.

`ui_extensions.py` still constructs Add/Editing Mode, suggestion and world-map
analysis/export controls; it is mostly orchestration but not implementation-free.
No extension reorder or installer removal was performed. Existing reapplication
and UI/desktop module reload tests pass. This does not establish reload safety for
every extension; path detection stores original methods only in module globals.

`path_rendering.py`, `poi_extensions.py`, `world_map_overrides.py`,
`worldgen_speedups.py`, `worldgen_target_fix.py` are tiny compatibility shims.
The first four have orchestration callers; tests also import old boundaries.
Their implementation lives in legacy/core/worldgen. Keep these public import
boundaries until external usage is known. The standalone target-fix shim needs a
separate external-caller check before deletion.

## 5. Rendering

| Layer | Owner | Migration disposition |
| --- | --- | --- |
| Camera / transforms / hit testing | legacy `_plot_transform`, `world_to_canvas`, viewport and input helpers | PORT ALGORITHM/LOGIC TO SWIFT; explicit world/canvas units |
| World map underlay | legacy image-source, crop/resample and photo-cache helpers around 3178–3640 | RECREATE IN SWIFT with native image/canvas API; retain metadata contract |
| Terrain generation | worldgen render / Bedrock decoder | POSSIBLE SERVER/BACKEND RESPONSIBILITY |
| Stations / line geometry / labels | legacy `redraw:13406`, label layout, metro style; desktop `_overlay_web_station_markers:2268` | Recreate renderer; port collision, priority, abbreviation and construction semantics |
| Walking / connector / detected paths | legacy `_draw_extra_edges`, `_draw_path_nodes`; detection preview hooks | Recreate drawing; retain saved path geometry and detection previews |
| Suggested paths | legacy `_draw_suggested_walking_paths:14551`, shared suggestions | Port algorithm or consume derived data; preserve yellow unsmoothed segments |
| City / alignment / frontier / route overlays | legacy drawing helpers and `world_map_analysis.py` | Port geometry; recreate canvas layers |
| PNG export | legacy `_build_visible_block_png_export_bytes:12884`, `_draw_block_png_export_overlays:12930` | Native raster implementation; preserve block-native pixel scale and selected overlays |
| SVG export | legacy `_build_map_svg:2307` and validation | KEEP AS DATA FORMAT where consumed; recreate serialization/rendering adapter |

## 6. Worldgen

| Component | Current role | Disposition |
| --- | --- | --- |
| `__main__.py` | CLI parser: status, start, wait, prepare, stop, world-path, render-plan, render, repair-db, load-chunks | Retain CLI/backend API; Swift should call a service boundary |
| `config.py`, `paths.py`, `modes.py` | TOML models, bounds, filesystem layout, surface/LAN modes | Keep format; recreate local settings adapter |
| `generator.py` | Bedrock lifecycle, readiness, target selection, loader orchestration, coverage and render coordination | POSSIBLE SERVER/BACKEND RESPONSIBILITY |
| `docker_compose.py`, root compose YAML | Docker executable discovery and subprocess commands; Bedrock/loader services | Backend/development infrastructure |
| `headless_loader.js` | `bedrock-protocol` client, chunk loading/packet collection | Keep Node subsystem or backend; not Tk code |
| `tools/bedrock_lan_discover.mjs` | LAN discovery helper | Device/backend network adapter |
| `bedrock_chunks.py` | LevelDB/subchunk/block-storage decoding | Backend candidate, binary format compatibility tests required |
| `cache.py` | World-cache records, JSON reads and atomic retry writes | Private backend/device state |
| `render.py` | Render plan/result, block palette, topdown/fixed-Y raster generation, coverage and unknown reports | Backend candidate; PNG/metadata retained |
| `unknown_diagnostics.py` | Unknown block/palette analysis and diagnostic JSON/CSV | Backend/development tool; exclude private diagnostics from public data |
| `village_paths.py` | Surface scan, seed component, NumPy skeletonization and path simplification | Port algorithm if native needed; scanning can stay Python |
| `world_map_analysis.py` | Internal blank-region detection and asynchronous viewer drawing | Split analysis from Tk scheduling in later run |

Python requirements declare Pillow and plyvel. Village-path implementation also
imports NumPy; dependency completeness should be checked in a clean environment
before claiming reproducible setup. Do not remove Node: package scripts run public
smoke/validation/preview and Python path tests, while `bedrock-protocol` supports
the loader. `package-lock.json` pins that dependency graph; it is development and
worldgen infrastructure, not an unnecessary desktop bundle.

## 7. Public Viewer

`docs/index.html`, `styles.css`, and `app.js` are an active read-only web product.
JS loads shared network JSON and terrain assets, handles URL/share state, search,
routing, overlays, checklist/priority views, station detail and viewport resize.
Preserve public abbreviations and share links. No web redesign occurred in M01.

Parallel algorithms exist in JS and Python: graph building/route costs,
construction/frontier checks, station identity and label priority, geometry,
distance/time formatting and alignment/city-limit interpretation. These are
platform implementations, not safe deletions. Shared JSON and generated
`suggested_walking_segments` already avoid independently generating suggestions
in the browser. Future parity fixtures should compare Python/JS/Swift on the same
synthetic worlds. Do not use private runtime snapshots as fixtures.

`docs/smoke_test.js` verifies asset/data contracts with Node; Python public
validation and preview checks check export safety. They do not establish live
browser or Tk interaction correctness.

## 8. Future Swift disposition

| Subsystem | Label | First safe boundary |
| --- | --- | --- |
| Domain models, geometry, normalization, routing, construction, priority, snapping | PORT ALGORITHM/LOGIC TO SWIFT | Typed world/network values plus synthetic parity fixtures |
| Workspace, inspector, dialogs, gestures, menus, shortcuts | RECREATE IN SWIFT | View state and explicit domain commands |
| JSON/CSV, PNG/render metadata, optional SVG | KEEP AS DATA FORMAT | Read/write round-trip contract; preserve IDs/coordinates |
| Bedrock, Docker, terrain/packet processing, diagnostics | POSSIBLE SERVER/BACKEND RESPONSIBILITY | Job request/status/result interface |
| Tk wrappers, global mutable registries, recursive styling, compatibility installers | LEGACY / DO NOT PORT LITERALLY | Retain in Python until replacement is independently usable |
| Public viewer | KEEP AS DATA FORMAT for shared inputs; retain separate web implementation | Explicit public projection, share-link compatibility |
| Accounts, cloud worlds, Owner/Admin/Editor-Customizer/Viewer | Future architecture only | Authentication, world-scoped authorization and revision/conflict policy need separate design |

A later native app should own explicit world/repository/session boundaries. No
current Python record is evidence of implemented cloud ownership or permissions.

## Appendix: complete core symbol inventory

Each row is ACTIVE. Ranges are grouped by module for review. No core code was
changed. File operations require a repository adapter; Python typing/dataclasses,
heap queues and exceptions are mechanisms rather than Swift APIs to translate.

### `plumville/core/__init__.py`

Package marker; no functions or classes.

### `plumville/core/geometry.py`

| Symbol / source line | Portability and boundary |
| --- | --- |
| `polyline_distance`:7 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `polyline_distance_float`:11 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `point_to_segment_distance_sq`:15 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `point_to_polyline_distance_sq`:38 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `polyline_midpoint`:53 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `cumulative_distances`:84 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |

### `plumville/core/network.py`

| Symbol / source line | Portability and boundary |
| --- | --- |
| `coordinate_endpoint_key`:15 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `parse_coordinate_text`:19 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `coerce_int`:26 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalized_ordered_values`:43 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_stop_metadata`:58 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `line_finish_origin_options`:119 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_railway_finish_progress`:147 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_railway_finish_origins`:178 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_path_nodes`:207 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `_path_node_embedded_number`:314 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `_first_available_node_number`:319 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `next_path_node_id`:326 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `_referenced_path_node_coordinates`:340 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `resolve_stop_key`:375 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `resolve_path_node`:400 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `path_endpoint_record_from_identifier`:419 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_path_endpoint_record`:441 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `payload_endpoint_coordinates`:470 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_extra_edges`:490 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `path_node_keys`:633 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_city_limits`:658 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `infer_alignment_axis`:701 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_alignment_reminders`:714 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `line_colors_from_payload`:785 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `wool_colors_from_payload`:795 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `line_stop_vars_from_payload`:805 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `stop_line_names`:816 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `railway_finish_progress_from_payload`:830 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `railway_finish_origins_from_payload`:847 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `line_path_spec_records_from_payload`:862 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `line_path_plot_paths_from_specs`:882 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `line_path_coordinate_paths_from_plot_paths`:898 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `path_node_records_from_payload`:907 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `extra_edge_records_from_payload`:937 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `alignment_reminder_records_from_payload`:972 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `line_letters`:987 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_line_sequences`:991 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_line_path_specs`:1014 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_line_colors`:1035 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_path_nodes`:1043 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_extra_edges`:1063 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_stop_line_names`:1091 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_stop_records`:1100 | Portable JSON/network rule; KEEP AS DATA FORMAT and PORT ALGORITHM/LOGIC TO SWIFT |
| `validate_network_payload` (M02) | Portable aggregate validation before explicit save; no global installation or filesystem access |
| `serialize_network_payload`:1119 | JSON serialization contract; KEEP AS DATA FORMAT |
| `history_snapshot_paths`:1123 | Filesystem/history adapter; preserve semantics, replace Python Path I/O; possible backend responsibility |
| `record_history_snapshot`:1129 | Filesystem/history adapter; preserve semantics, replace Python Path I/O; possible backend responsibility |
| `write_network_payload`:1157 | Filesystem/history adapter; preserve semantics, replace Python Path I/O; possible backend responsibility |
| `restore_last_network_snapshot`:1183 | Filesystem/history adapter; preserve semantics, replace Python Path I/O; possible backend responsibility |

### `plumville/core/public_export.py`

| Symbol / source line | Portability and boundary |
| --- | --- |
| `validate_public_text`:51 | Public/web export validation rule; portable, possible backend responsibility |
| `validate_public_json_keys`:61 | Public/web export validation rule; portable, possible backend responsibility |
| `validate_public_docs`:81 | Filesystem public-export validation adapter; possible backend responsibility |
| `format_byte_size`:96 | Portable display formatting; localize native UI later |

### `plumville/core/routing.py`

| Symbol / source line | Portability and boundary |
| --- | --- |
| `RouteEdge`:13 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `RouteStep`:25 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `RouteResult`:51 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `RouteSearchResult`:60 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `RouteGraphStop`:67 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `RouteGraphLineSegment`:73 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `RouteGraphEndpointEdge`:82 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `append_route_step`:95 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `unfinished_route_line_names`:179 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `format_line_name_list`:193 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `format_route_instructions`:203 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `append_graph_edge`:282 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `ensure_graph_nodes`:289 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `add_transfer_edges`:297 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `add_bidirectional_ride_edges`:331 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `add_endpoint_edges`:368 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `build_route_graph`:409 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `standard_graph_nodes_for_endpoint`:461 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `graph_nodes_for_endpoint`:475 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `shortest_route_edges`:507 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `route_costs_from_nodes`:566 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |

### `plumville/core/text.py`

| Symbol / source line | Portability and boundary |
| --- | --- |
| `display_label`:8 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `is_placeholder_station_label`:15 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_stop_identity`:19 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_line_color`:23 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `normalize_line_name`:34 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |

### `plumville/core/travel_time.py`

| Symbol / source line | Portability and boundary |
| --- | --- |
| `format_track_distance`:6 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `travel_time_seconds`:14 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `format_travel_time`:18 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `format_travel_time_for_distance`:33 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
| `format_distance_and_time`:37 | Portable algorithm/value or formatting; PORT ALGORITHM/LOGIC TO SWIFT |
