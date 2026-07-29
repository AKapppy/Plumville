# CODEX_TASK.md — Desktop Stabilization Run D01

## Goal

Stabilize the desktop improvements that are already present in the latest
repository, then prepare them for user verification.

The prior generated updater reported errors. The latest GitHub main nonetheless
contains:

- `desktop_improvements.py`
- `ui_extensions.py` importing and applying it
- public desktop resize changes in `docs/app.js`
- a desktop-width viewport block in `docs/styles.css`

Therefore, audit the actual current code. Do not reapply an old updater and do
not assume the draft works.

## First run: D01-A

Work only on baseline audit and startup/extension stability.

### Required actions

1. Read `AGENTS.md`, `notes.txt`, and `file_priority.txt`.
2. Record:
   - current branch;
   - `git status --short`;
   - Python version;
   - Node version;
   - npm version.
3. Run baseline checks:
   - Python compilation;
   - unit tests;
   - `npm run test:paths`;
   - `npm test`;
   - Tk smoke when possible.
4. Launch `python3 plumville_app.py`.
5. Capture the complete traceback or exact broken behavior.
6. Audit:
   - `metro_stops._apply_extensions_once()`;
   - `ui_extensions.apply()`;
   - every relevant `.apply()` order;
   - `_build_route_panel` wrappers;
   - `_draw_selected_stop_info` wrappers;
   - `_refresh_current_route` wrappers;
   - repeat application/idempotence.
7. Fix the smallest root cause.
8. Add regression coverage.
9. Re-run relevant checks.
10. Update `notes.txt` and `file_priority.txt`.
11. Give the user a numbered manual-check list.
12. Stop before starting route-fit, path-detection, or worldgen refinements when
    they are not required to fix startup.

## Subsequent D01 sub-runs

After D01-A is stable, continue one slice at a time.

### D01-B — Route auto-fit

Acceptance criteria:

- new routes auto-fit;
- Swap and route recalculation refit;
- unrelated redraws do not refit;
- no redraw/after_idle loop;
- short routes keep a reasonable zoom;
- Fit Route remains available;
- route instructions and highlights remain intact;
- tests are added where practical.

### D01-C — Path detection relocation

Acceptance criteria:

- no detection button in normal station popup;
- existing path rendering and state remain intact;
- Advanced / Experimental defaults collapsed;
- selected station and confirmation are required;
- existing detection workflow still opens;
- no algorithm redesign or data migration.

### D01-D — Completed worldgen UI

Acceptance criteria:

- completion is determined from trustworthy coverage and matching bounds;
- generation controls hide only when completion is verified;
- visibility/status/analysis/export controls remain;
- controls return if completion becomes uncertain;
- no production cache/config mutation;
- pure helper tests cover completion decisions.

## Public desktop browser

The current public resize and named/unnamed fixes are secondary.

Only change `docs/app.js` or `docs/styles.css` when:

- the desktop-width issue is reproduced; or
- a concrete defect is demonstrated by a test.

Do not change phone/mobile-specific behavior.

## Out of scope

- commit or push;
- mobile UI changes;
- canonical/public data migration;
- desktop mode redesign;
- docked inspector;
- construction dashboard;
- path-detection algorithm repair;
- water/coastline work;
- broad `legacy_core.py` refactor.

## Required final response

Use `QA_REPORT_TEMPLATE.txt`.

Do not say “done” without:

- exact passing tests;
- updated checklist;
- changed-file list;
- numbered user checks;
- git status;
- confirmation of no commit/push.
