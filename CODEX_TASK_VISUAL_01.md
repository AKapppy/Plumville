# CODEX_TASK_VISUAL_01.md

## Run

Desktop Visual Run V01 — Workspace Shell

## Objective

Build the structural desktop workspace shell shown in the Plumville mockups.

This run is about layout hierarchy, not feature expansion and not final visual
polish.

## Read first

- AGENTS.md
- notes.txt
- file_priority.txt
- VISUAL_TARGET.md
- all three PNG files in data/mockups/

Also inspect the current live desktop UI before editing. Save a screenshot or
record its visible structure for comparison.

## Current reality

The repository already has:

- functional desktop route fitting;
- hidden/experimental path detection;
- completed-worldgen UI logic;
- a mode model;
- first-pass MMCP tokens;
- styled sidebar controls;
- selected-station popup decorations;
- many tests.

The current implementation still uses one old sidebar and a floating selected
station popup. The next step is structural.

## Scope

Create:

1. top application bar;
2. compact left mode rail;
3. secondary mode panel host;
4. flexible center map host;
5. right inspector host with empty state;
6. optional compact status region only when useful.

Mount or preserve current controls. Do not implement full inspector content in
this run.

## Production-file limit

Normal target:

- one new workspace module;
- one small legacy hook file;
- one coordinator/compatibility file if necessary;
- tests.

Do not edit more production files without explaining why before doing so.

## Recommended architecture

Prefer:

- plumville/desktop/workspace.py
- a minimal hook in legacy_core.py
- a small installation call in ui_extensions.py or desktop_improvements.py
- tests/test_desktop_workspace.py

Do not put the complete shell implementation into legacy_core.py.

## Acceptance criteria

Automated:

- workspace regions are created exactly once;
- applying extensions twice does not duplicate regions;
- mode changes update the secondary panel host;
- map widget remains mounted and usable;
- inspector can collapse or hide;
- existing entry points remain valid;
- current Python and npm suites pass;
- git diff --check passes.

Manual, leave unchecked:

- app opens;
- top bar is visible;
- left mode rail is visible without scrolling;
- map remains dominant;
- right inspector is visible and can collapse;
- existing tools remain reachable;
- resizing remains usable;
- screenshot is visibly closer to the mockups.

## Explicit non-goals

Do not:

- build inspector tabs;
- migrate station actions;
- redesign dialogs;
- change route algorithms;
- add new editing features;
- change public/mobile UI;
- migrate network data;
- add construction calculations;
- rewrite legacy_core.py broadly;
- commit or push.

## Checklist behavior

Before editing:

- mark V01 active items [~].

After editing:

- mark only automated implementation items [x] when tests pass;
- mark visually implemented items [verify];
- leave Andrew's user checks [ ];
- update notes.txt;
- update file_priority.txt.

## End-of-run report

Include:

- exact changed files;
- exact test commands and results;
- diff stat;
- numbered manual checks;
- known gaps;
- confirmation that no commit or push occurred.

Stop after V01.
