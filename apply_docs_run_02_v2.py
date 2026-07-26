#!/usr/bin/env python3
# Apply Plumville public-viewer implementation run 02, corrected updater.
# Changes only docs/app.js, docs/styles.css, and docs/metro_network.json.
# The script does not commit, push, pull, or touch ignored runtime/world data.

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys


STYLES_CSS = ':root {\n  color-scheme: dark;\n  --bg: #080b0d;\n  --panel: #101417;\n  --panel-raised: #151b1f;\n  --panel-inset: #090c0e;\n  --panel-hover: #20282d;\n  --ink: #f5f7f2;\n  --muted: #9aa59f;\n  --faint: #68736d;\n  --line: #2b3439;\n  --border-light: #465159;\n  --border-dark: #050708;\n  --field: #090c0e;\n  --field-active: #12181c;\n  --emerald: #55b86a;\n  --gold: #f0c75e;\n  --redstone: #de5750;\n  --diamond: #72c9ec;\n  --focus-ring: rgba(114, 201, 236, 0.34);\n  --shadow: rgba(0, 0, 0, 0.42);\n  --panel-width: 356px;\n  --safe-top: env(safe-area-inset-top, 0px);\n  --safe-right: env(safe-area-inset-right, 0px);\n  --safe-bottom: env(safe-area-inset-bottom, 0px);\n  --safe-left: env(safe-area-inset-left, 0px);\n}\n\n* {\n  box-sizing: border-box;\n}\n\nhtml,\nbody {\n  height: 100%;\n}\n\nhtml {\n  background: var(--bg);\n}\n\nbody {\n  margin: 0;\n  background:\n    linear-gradient(rgba(255, 255, 255, 0.012) 1px, transparent 1px),\n    linear-gradient(90deg, rgba(255, 255, 255, 0.012) 1px, transparent 1px),\n    var(--bg);\n  background-size: 16px 16px;\n  color: var(--ink);\n  font-family:\n    Inter,\n    ui-sans-serif,\n    -apple-system,\n    BlinkMacSystemFont,\n    "Segoe UI",\n    Helvetica,\n    Arial,\n    sans-serif;\n}\n\nbutton,\ninput {\n  font: inherit;\n}\n\nbutton,\ninput,\nsummary {\n  -webkit-tap-highlight-color: transparent;\n}\n\n.viewer-shell {\n  display: grid;\n  grid-template-columns: var(--panel-width) minmax(0, 1fr);\n  min-height: 100vh;\n  min-height: 100svh;\n}\n\n.side-panel {\n  position: relative;\n  z-index: 4;\n  display: flex;\n  flex-direction: column;\n  gap: 12px;\n  width: var(--panel-width);\n  min-height: 100vh;\n  min-height: 100svh;\n  max-height: 100vh;\n  max-height: 100svh;\n  padding:\n    calc(14px + var(--safe-top))\n    14px\n    calc(18px + var(--safe-bottom))\n    calc(14px + var(--safe-left));\n  background:\n    linear-gradient(180deg, rgba(255, 255, 255, 0.018), transparent 180px),\n    var(--panel);\n  border-right: 1px solid var(--border-light);\n  box-shadow:\n    inset -1px 0 var(--border-dark),\n    10px 0 28px rgba(0, 0, 0, 0.2);\n  overflow-y: auto;\n  scrollbar-color: var(--border-light) var(--panel-inset);\n}\n\n.map-stage {\n  position: relative;\n  min-height: 100vh;\n  min-height: 100svh;\n  background: var(--bg);\n  overflow: hidden;\n  isolation: isolate;\n}\n\n#metroCanvas {\n  display: block;\n  width: 100%;\n  height: 100%;\n  min-height: 100vh;\n  min-height: 100svh;\n  cursor: grab;\n  touch-action: none;\n}\n\n#metroCanvas.dragging {\n  cursor: grabbing;\n}\n\n.map-controls {\n  position: absolute;\n  top: calc(14px + var(--safe-top));\n  right: calc(14px + var(--safe-right));\n  z-index: 2;\n  display: grid;\n  gap: 7px;\n}\n\n.map-controls button {\n  width: 42px;\n  min-height: 42px;\n  padding: 0;\n  border-color: var(--border-light);\n  background: rgba(16, 20, 23, 0.93);\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.08),\n    inset -2px -2px var(--border-dark),\n    0 8px 24px var(--shadow);\n  backdrop-filter: blur(8px);\n}\n\n.map-controls #mapFitButton {\n  width: 50px;\n  color: var(--diamond);\n}\n\nh1,\nh2,\np,\npre {\n  margin: 0;\n}\n\nh1,\nh2,\n.section-heading,\n.collapsible-section > summary {\n  font-family:\n    "SFMono-Regular",\n    "Cascadia Mono",\n    Menlo,\n    Consolas,\n    monospace;\n}\n\nh1 {\n  font-size: 21px;\n  line-height: 1.15;\n}\n\nh2 {\n  font-size: 22px;\n  line-height: 1.15;\n}\n\n.control-section,\n.collapsible-section,\n.text-panel {\n  border: 1px solid var(--border-light);\n  background: var(--panel-raised);\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.05),\n    inset -2px -2px var(--border-dark),\n    0 5px 16px rgba(0, 0, 0, 0.14);\n}\n\n.control-section {\n  display: grid;\n  gap: 8px;\n  padding: 11px;\n}\n\n.section-heading,\n.collapsible-section > summary {\n  color: var(--ink);\n  font-size: 15px;\n  font-weight: 800;\n  line-height: 1.2;\n  text-transform: uppercase;\n}\n\n.collapsible-section {\n  display: grid;\n  gap: 0;\n}\n\n.collapsible-section > summary {\n  position: relative;\n  min-height: 44px;\n  padding: 13px 38px 11px 12px;\n  cursor: pointer;\n  list-style: none;\n  user-select: none;\n}\n\n.collapsible-section > summary::-webkit-details-marker {\n  display: none;\n}\n\n.collapsible-section > summary::after {\n  content: "+";\n  position: absolute;\n  top: 50%;\n  right: 13px;\n  width: 20px;\n  height: 20px;\n  border: 1px solid var(--border-light);\n  background: var(--panel-inset);\n  color: var(--diamond);\n  font-family: monospace;\n  font-size: 17px;\n  line-height: 17px;\n  text-align: center;\n  transform: translateY(-50%);\n}\n\n.collapsible-section[open] > summary::after {\n  content: "−";\n}\n\n.collapsible-section > .control-section,\n.collapsible-section > .summary,\n.collapsible-section > .text-panel {\n  margin: 0 10px 10px;\n}\n\n.collapsible-section > .control-section {\n  border-color: var(--line);\n  background: var(--panel-inset);\n}\n\n.summary,\n.hint,\n.text-panel,\n.info-popup p {\n  color: var(--ink);\n  font-size: 12px;\n  line-height: 1.45;\n  white-space: pre-line;\n}\n\n.summary {\n  color: #c9d1cc;\n}\n\n.hint {\n  color: var(--muted);\n  font-size: 11px;\n}\n\n.field-label {\n  display: block;\n  color: var(--ink);\n  font-size: 12px;\n  font-weight: 800;\n}\n\n.field-label.spaced {\n  margin-top: 5px;\n}\n\n.input-row {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) auto;\n  gap: 8px;\n}\n\n.sidebar-input {\n  width: 100%;\n  min-height: 38px;\n  padding: 8px 10px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: var(--field);\n  color: var(--ink);\n  outline: none;\n  box-shadow:\n    inset 2px 2px var(--border-dark),\n    inset -1px -1px rgba(255, 255, 255, 0.035);\n}\n\n.sidebar-input::placeholder {\n  color: var(--faint);\n}\n\n.sidebar-input:focus {\n  background: var(--field-active);\n  border-color: var(--diamond);\n  box-shadow:\n    0 0 0 3px var(--focus-ring),\n    inset 2px 2px var(--border-dark);\n}\n\n.actions {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 8px;\n}\n\nbutton {\n  min-height: 36px;\n  padding: 7px 11px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: var(--panel-raised);\n  color: var(--ink);\n  font-size: 11px;\n  font-weight: 800;\n  cursor: pointer;\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.08),\n    inset -2px -2px var(--border-dark);\n}\n\nbutton:hover {\n  border-color: #69767e;\n  background: var(--panel-hover);\n}\n\nbutton:focus-visible {\n  border-color: var(--diamond);\n  outline: 3px solid var(--focus-ring);\n  outline-offset: 1px;\n}\n\nbutton:active {\n  transform: translateY(1px);\n  box-shadow:\n    inset 2px 2px var(--border-dark),\n    inset -1px -1px rgba(255, 255, 255, 0.04);\n}\n\n#routeButton,\n#searchButton {\n  border-color: #4f8e5c;\n  background: linear-gradient(180deg, #397b49, #2a6338);\n}\n\n.check-row {\n  display: flex;\n  align-items: center;\n  gap: 9px;\n  min-height: 30px;\n  color: var(--ink);\n  font-size: 12px;\n  cursor: pointer;\n}\n\n.check-row input {\n  width: 16px;\n  height: 16px;\n  margin: 0;\n  accent-color: var(--emerald);\n}\n\n.line-legend {\n  display: grid;\n  grid-template-columns: repeat(auto-fill, minmax(86px, 1fr));\n  gap: 7px;\n  margin-top: 7px;\n}\n\n.line-toggle {\n  display: inline-flex;\n  align-items: center;\n  gap: 7px;\n  min-height: 36px;\n  padding: 5px 7px;\n  border: 1px solid var(--line);\n  border-radius: 2px;\n  background: var(--panel-inset);\n  color: var(--ink);\n  font-size: 11px;\n  font-weight: 800;\n  cursor: pointer;\n}\n\n.line-toggle:hover {\n  border-color: var(--border-light);\n  background: var(--panel-hover);\n}\n\n.line-toggle input {\n  width: 13px;\n  height: 13px;\n  margin: 0;\n  accent-color: var(--emerald);\n}\n\n.line-swatch,\n.line-badge {\n  display: inline-grid;\n  place-items: center;\n  flex: 0 0 auto;\n  border-radius: 50%;\n  background: var(--line-color, var(--panel-hover));\n  font-family:\n    "SFMono-Regular",\n    Menlo,\n    Consolas,\n    monospace;\n  font-weight: 900;\n  line-height: 1;\n}\n\n.line-swatch {\n  width: 22px;\n  height: 22px;\n  border: 2px solid currentColor;\n  color: var(--ink);\n  font-size: 11px;\n}\n\n.line-badges {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 6px;\n  margin-top: 5px;\n}\n\n.line-badge {\n  width: 25px;\n  height: 25px;\n  min-height: 25px;\n  padding: 0;\n  border: 2px solid var(--line-ink, var(--ink));\n  color: var(--line-ink, var(--ink));\n  font-size: 11px;\n}\n\n.line-badge.muted {\n  width: auto;\n  min-width: 42px;\n  padding: 0 8px;\n  border-radius: 2px;\n  border-color: var(--border-light);\n  background: var(--panel-inset);\n  color: var(--muted);\n}\n\n.text-panel {\n  height: auto;\n  min-height: 0;\n  max-height: none;\n  padding: 11px 12px;\n  overflow: visible;\n}\n\n#routeSummary {\n  margin-bottom: 9px;\n  color: var(--gold);\n  font-weight: 800;\n}\n\n#routeSteps {\n  height: auto;\n  min-height: 0;\n  max-height: none;\n  overflow: visible;\n  white-space: pre-wrap;\n  color: var(--ink);\n  font-size: 12px;\n  line-height: 1.45;\n  font-family: inherit;\n}\n\n.tooltip {\n  position: absolute;\n  z-index: 3;\n  max-width: min(300px, calc(100vw - 40px));\n  padding: 9px 11px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: rgba(16, 20, 23, 0.96);\n  color: var(--ink);\n  box-shadow: 0 8px 24px var(--shadow);\n  pointer-events: none;\n}\n\n.tooltip strong {\n  display: block;\n  margin-bottom: 3px;\n  font-size: 12px;\n}\n\n.tooltip span {\n  color: var(--muted);\n  font-size: 12px;\n}\n\n.info-popup {\n  position: absolute;\n  z-index: 2;\n  width: max-content;\n  max-width: min(340px, calc(100vw - 40px));\n  padding: 11px 12px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: rgba(16, 20, 23, 0.97);\n  color: var(--ink);\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.045),\n    inset -2px -2px var(--border-dark),\n    0 12px 34px var(--shadow);\n}\n\n.info-popup h2 {\n  display: flex;\n  flex-wrap: wrap;\n  align-items: baseline;\n  gap: 8px;\n  margin-bottom: 7px;\n}\n\n.station-abbr {\n  display: inline-block;\n  padding: 2px 5px;\n  border: 1px solid #8c743a;\n  border-radius: 2px;\n  background: #2a2415;\n  color: var(--gold);\n  font-family:\n    "SFMono-Regular",\n    Menlo,\n    Consolas,\n    monospace;\n  font-size: 11px;\n  font-weight: 900;\n}\n\n.info-popup .section-label {\n  margin-top: 9px;\n  color: var(--muted);\n  font-size: 10px;\n  font-weight: 900;\n  letter-spacing: 0.08em;\n  text-transform: uppercase;\n}\n\n@media (max-width: 860px) {\n  .viewer-shell {\n    grid-template-columns: 1fr;\n    grid-template-rows: minmax(60svh, 1fr) auto;\n  }\n\n  .map-stage,\n  #metroCanvas {\n    min-height: 60svh;\n  }\n\n  .map-stage {\n    grid-row: 1;\n    border-bottom: 1px solid var(--border-light);\n  }\n\n  .side-panel {\n    grid-row: 2;\n    width: auto;\n    min-height: auto;\n    max-height: none;\n    padding:\n      12px\n      calc(12px + var(--safe-right))\n      calc(18px + var(--safe-bottom))\n      calc(12px + var(--safe-left));\n    border-top: 1px solid var(--border-dark);\n    border-right: 0;\n    box-shadow: none;\n    overflow: visible;\n  }\n\n  .map-controls button,\n  button,\n  .sidebar-input {\n    min-height: 44px;\n  }\n\n  .map-controls button {\n    width: 46px;\n  }\n\n  .map-controls #mapFitButton {\n    width: 56px;\n  }\n\n  .line-toggle {\n    min-height: 42px;\n  }\n}\n\n@media (max-width: 560px) {\n  .viewer-shell {\n    grid-template-rows: minmax(58svh, 1fr) auto;\n  }\n\n  .map-stage,\n  #metroCanvas {\n    min-height: 58svh;\n  }\n\n  .side-panel {\n    gap: 9px;\n    padding-inline:\n      calc(9px + var(--safe-left))\n      calc(9px + var(--safe-right));\n  }\n\n  .line-legend {\n    grid-template-columns: repeat(3, minmax(0, 1fr));\n  }\n\n  .actions {\n    display: grid;\n    grid-template-columns: repeat(2, minmax(0, 1fr));\n  }\n\n  .actions button {\n    width: 100%;\n  }\n\n  .input-row {\n    grid-template-columns: minmax(0, 1fr) 56px;\n  }\n\n  .info-popup {\n    width: min(330px, calc(100vw - 18px));\n    max-width: none;\n  }\n}\n\n@media (prefers-reduced-motion: reduce) {\n  *,\n  *::before,\n  *::after {\n    transition-duration: 0.001ms !important;\n  }\n}\n'
STATION_ABBREVIATIONS = {'Blackport': 'BKP', 'Cherry Hill': 'CHI', 'Arrow Falls': 'ARF', 'Minas Rojas': 'MNR', 'New Eden': 'NED', 'Holihill': 'HLH', 'Cherry Hole': 'CHO', 'Glacier Cherry': 'GCH', 'Isle of Whales': 'IWH', 'Dicton': 'DIC', 'Hidden Valley Ranch': 'HVR', 'Pinkerton': 'PNK', 'Caverndeau': 'CVD', 'Clifton': 'CLF', 'T-t-t-town': 'TTT', 'Slimin': 'SLI', 'Toot’n’Cummin': 'TNC', 'Ridgewater': 'RGW', 'Triarchidia': 'TRI', 'Everly': 'EVL', 'Amortay': 'AMR', 'Neamegapolis': 'NMG', 'Pinto Peak': 'PNT', 'Prumpvatn': 'PRM', 'Peapod': 'PPD', 'Aldinhöfn': 'ALD', 'Timberville': 'TMB', 'Green Arch': 'GRN', 'Nujeau': 'NUJ', 'Pumpland': 'PMP', 'East Arendel': 'EAR', 'West Arendel': 'WAR', 'Hollow Bluffs': 'HBF', 'Northbulge': 'NBG', 'Alexandropol': 'ALX', 'The Edge': 'EDG', 'Isthmopol': 'IST', 'Mt. Phosphagos': 'MTP', 'Kelp City': 'KLP', 'Castle Crossing': 'CSX', 'Stilton': 'STL', 'West Stilton': 'WST', 'Langland': 'LNG', 'Volbura': 'VLB', 'Cameltoe': 'CML', 'Østligste': 'OST', 'Aesopia': 'ASP', 'Mycopolis': 'MYC', 'Glacier Bay': 'GCB', 'White Pines': 'WTP', 'Rack City': 'RCK', 'Michael': 'MCL', 'Krimnos': 'KRM'}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one matching block, found {count}."
        )
    return text.replace(old, new, 1)


def replace_regex_once(
    text: str,
    pattern: str,
    replacement: str,
    label: str,
) -> str:
    updated, count = re.subn(
        pattern,
        replacement,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one matching block, found {count}."
        )
    return updated


def replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker was not found.")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker was not found.")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def atomic_write(path: Path, content: str) -> None:
    temp_path = path.with_name(f".{path.name}.plumville-tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def transform_app(app: str) -> str:
    app = replace_once(
        app,
        "  blackportViewRadius: 2000,\n};",
        '''  blackportViewRadius: 2000,
  routeFitPadding: 72,
  routeFitMinSpan: 900,
  routeFitMaxScale: 7,
  stationOutline: '#f7f7f7',
  stationDarkOutline: '#050505',
  stationSelectedOutline: '#8ad4ff',
  phosphagosOutline: '#f0c75e',
  lineMarkerRadius: 8,
};''',
        "public map constants",
    )

    app = replace_once(
        app,
        '''    const swatch = document.createElement('span');
    swatch.className = 'line-swatch';
    swatch.style.backgroundColor = colorForLine(lineName);

    const text = document.createElement('span');
    text.textContent = lineName;''',
        '''    const swatch = document.createElement('span');
    const lineColor = colorForLine(lineName);
    swatch.className = 'line-swatch';
    swatch.style.setProperty('--line-color', lineColor);
    swatch.style.color = contrastingTextColor(lineColor);
    swatch.textContent = lineName;
    swatch.setAttribute('aria-hidden', 'true');

    const text = document.createElement('span');
    text.textContent = `Line ${lineName}`;''',
        "line legend circles",
    )

    app = replace_once(
        app,
        "    for (const value of [displayLabel(stop.lbl), stop.var, stop.var.replace(/^P_/, '')]) {",
        '''    for (const value of [
      displayLabel(stop.lbl),
      stationAbbreviation(stop),
      stop.var,
      stop.var.replace(/^P_/, ''),
    ]) {''',
        "station abbreviation suggestions",
    )

    app = replace_once(
        app,
        '''  mapFitButton?.addEventListener('click', () => {
    fitToMap();
    render();
  });''',
        "  mapFitButton?.addEventListener('click', fitPrimaryView);",
        "contextual map fit action",
    )

    route_helpers = '''function routePlotPoints(route) {
  if (!route) {
    return [];
  }
  const points = [];
  const start = state.stopsByVar.get(route.startVar);
  const end = state.stopsByVar.get(route.endVar);
  if (start) {
    points.push(stationPlotPoint(start));
  }
  for (const step of route.steps || []) {
    for (const point of step.pathPoints || []) {
      if (Number.isFinite(point?.x) && Number.isFinite(point?.y)) {
        points.push(point);
      }
    }
  }
  if (end) {
    points.push(stationPlotPoint(end));
  }
  return points;
}

function routePlotBounds(route) {
  const points = routePlotPoints(route);
  if (!points.length) {
    return null;
  }
  const bounds = boundsForPoints(points);
  if (!validBounds(bounds)) {
    return null;
  }
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  const spanX = Math.max(bounds.maxX - bounds.minX, 0);
  const spanY = Math.max(bounds.maxY - bounds.minY, 0);
  const halfWidth = Math.max(spanX, CONSTANTS.routeFitMinSpan) / 2;
  const halfHeight = Math.max(spanY, CONSTANTS.routeFitMinSpan) / 2;
  return {
    minX: centerX - halfWidth,
    minY: centerY - halfHeight,
    maxX: centerX + halfWidth,
    maxY: centerY + halfHeight,
  };
}

function fitCurrentRoute(options = {}) {
  const bounds = routePlotBounds(state.currentRoute);
  if (!bounds || !cameraHasWorld()) {
    return false;
  }
  setViewToPlotBounds(bounds, {
    padding: CONSTANTS.routeFitPadding,
    maxZoom: state.camera.minZoom * CONSTANTS.routeFitMaxScale,
  });
  if (options.render !== false) {
    render();
  }
  return true;
}

function fitPrimaryView() {
  if (!fitCurrentRoute()) {
    fitToMap();
    render();
  }
}
'''
    app = replace_once(
        app,
        "function setViewToPlotBounds(bounds) {",
        route_helpers + "\nfunction setViewToPlotBounds(bounds, options = {}) {",
        "route-fit helper insertion",
    )

    app = replace_once(
        app,
        '''  const spanX = Math.max(worldBounds.maxX - worldBounds.minX, 1);
  const spanY = Math.max(worldBounds.maxY - worldBounds.minY, 1);
  const availableWidth = Math.max(state.camera.viewportWidth - (CONSTANTS.padding * 2), 1);
  const availableHeight = Math.max(state.camera.viewportHeight - (CONSTANTS.padding * 2), 1);
  state.camera.zoom = clamp(
    Math.min(availableWidth / spanX, availableHeight / spanY),
    state.camera.minZoom,
    state.camera.maxZoom,
  );''',
        '''  const spanX = Math.max(worldBounds.maxX - worldBounds.minX, 1);
  const spanY = Math.max(worldBounds.maxY - worldBounds.minY, 1);
  const padding = Number.isFinite(options.padding)
    ? Math.max(0, options.padding)
    : CONSTANTS.padding;
  const availableWidth = Math.max(
    state.camera.viewportWidth - (padding * 2),
    1,
  );
  const availableHeight = Math.max(
    state.camera.viewportHeight - (padding * 2),
    1,
  );
  const maxZoom = Number.isFinite(options.maxZoom)
    ? Math.min(
      state.camera.maxZoom,
      Math.max(state.camera.minZoom, options.maxZoom),
    )
    : state.camera.maxZoom;
  state.camera.zoom = clamp(
    Math.min(availableWidth / spanX, availableHeight / spanY),
    state.camera.minZoom,
    maxZoom,
  );''',
        "configurable fit padding and maximum zoom",
    )

    draw_block = '''function drawStations() {
  ctx.save();
  const labelFontSize = labelFontSizeForZoom();
  ctx.font = `${labelFontSize}px Helvetica, Arial, sans-serif`;
  ctx.textBaseline = 'alphabetic';
  const visibleStops = state.data.stops.filter((stop) => stopHasVisibleLine(stop));
  const stationRects = visibleStops.map((stop) => {
    const point = plotToCanvas(stationPlotPoint(stop));
    const radius = stationMarkerSize(stop);
    return {
      stop,
      point,
      rect: {
        minX: point.x - radius - 3,
        maxX: point.x + radius + 3,
        minY: point.y - radius - 3,
        maxY: point.y + radius + 3,
      },
    };
  });
  const labelLayout = showLabelsInput.checked
    ? placeStationLabels(stationRects, labelFontSize)
    : new Map();

  for (const item of stationRects) {
    drawStationMarker(item.stop, item.point);
    drawStationLineMarkers(item.stop, item.point);
    if (showLabelsInput.checked) {
      const label = labelLayout.get(item.stop.var);
      if (label) {
        drawRotatedLabel(
          label.text,
          label.x,
          label.y,
          stationLabelColor(item.stop),
          labelFontSize,
          stationLabelPriority(item.stop) <= 4,
        );
      }
    }
  }
  ctx.restore();
}

function drawStationMarker(stop, point) {
  const size = stationMarkerSize(stop);
  const selected = state.selectedStop?.var === stop.var;
  const phosphagos = isPhosphagos(stop);
  const junction = isJunctionStop(stop);

  ctx.save();
  ctx.setLineDash([]);
  if (selected) {
    drawDiamondPath(point, size + 5);
    ctx.strokeStyle = CONSTANTS.stationSelectedOutline;
    ctx.lineWidth = 3;
    ctx.stroke();
  }

  drawDiamondPath(point, size);
  ctx.fillStyle = stationColor(stop);
  ctx.fill();
  ctx.strokeStyle = phosphagos
    ? CONSTANTS.phosphagosOutline
    : CONSTANTS.stationDarkOutline;
  ctx.lineWidth = phosphagos ? 4 : 2;
  ctx.stroke();

  if (junction && !phosphagos) {
    drawDiamondPath(point, Math.max(3, size - 3));
    ctx.strokeStyle = CONSTANTS.stationOutline;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  if (phosphagos) {
    drawHomeGlyph(point, size);
  }
  ctx.restore();
}

function drawDiamondPath(point, radius) {
  ctx.beginPath();
  ctx.moveTo(point.x, point.y - radius);
  ctx.lineTo(point.x + radius, point.y);
  ctx.lineTo(point.x, point.y + radius);
  ctx.lineTo(point.x - radius, point.y);
  ctx.closePath();
}

function drawHomeGlyph(point, size) {
  const scale = Math.max(4, size - 3);
  ctx.save();
  ctx.strokeStyle = CONSTANTS.stationDarkOutline;
  ctx.lineWidth = 1.6;
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(point.x - scale, point.y);
  ctx.lineTo(point.x, point.y - scale + 1);
  ctx.lineTo(point.x + scale, point.y);
  ctx.moveTo(point.x - scale + 2, point.y - 1);
  ctx.lineTo(point.x - scale + 2, point.y + scale - 2);
  ctx.lineTo(point.x + scale - 2, point.y + scale - 2);
  ctx.lineTo(point.x + scale - 2, point.y - 1);
  ctx.stroke();
  ctx.restore();
}

function drawStationLineMarkers(stop, point) {
  const lineNames = markerLineNamesForStop(stop);
  if (!lineNames.length) {
    return;
  }
  const markerRadius = CONSTANTS.lineMarkerRadius;
  const distance = stationMarkerSize(stop) + markerRadius + 5;
  const offsets = [
    { x: distance, y: 0 },
    { x: 0, y: distance },
    { x: -distance, y: 0 },
    { x: 0, y: -distance },
  ];
  lineNames.slice(0, offsets.length).forEach((lineName, index) => {
    const offset = offsets[index];
    drawLineCircle(
      { x: point.x + offset.x, y: point.y + offset.y },
      lineName,
      markerRadius,
    );
  });
}

function drawLineCircle(point, lineName, radius) {
  const color = colorForLine(lineName);
  ctx.save();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = contrastingTextColor(color);
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.fillStyle = contrastingTextColor(color);
  ctx.font = `900 ${Math.max(9, radius + 2)}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(lineName, point.x, point.y + 0.5);
  ctx.restore();
}

function placeStationLabels(stationItems, fontSize) {
  const mapRect = currentMapScreenRect();
  const linePaths = visibleLineCanvasPaths();
  const occupiedRects = stationItems.map((item) => item.rect);
  const labels = new Map();
  const orderedItems = [...stationItems].sort((a, b) => (
    stationLabelPriority(a.stop) - stationLabelPriority(b.stop)
    || distanceToRectEdge(a.point, mapRect) - distanceToRectEdge(b.point, mapRect)
  ));

  for (const item of orderedItems) {
    if (!shouldAttemptStationLabel(item.stop)) {
      continue;
    }
    let best = null;
    for (const text of stationLabelTextOptions(item.stop)) {
      for (const candidate of labelCandidatesForStation(
        item.point,
        text,
        fontSize,
      )) {
        const placed = clampLabelCandidate(
          candidate,
          text,
          fontSize,
          mapRect,
        );
        const score = labelPlacementScore(
          placed.rect,
          occupiedRects,
          linePaths,
          mapRect,
        ) + candidate.preference;
        if (!best || score < best.score) {
          best = { ...placed, score, text };
        }
        if (score === 0) {
          break;
        }
      }
      if (best?.score === 0) {
        break;
      }
    }
    if (!best) {
      continue;
    }
    const priority = stationLabelPriority(item.stop);
    if (priority > 4 && best.score > stationLabelScoreLimit()) {
      continue;
    }
    labels.set(item.stop.var, best);
    occupiedRects.push(expandRect(best.rect, 2));
  }
  return labels;
}

function labelCandidatesForStation(point, text, fontSize) {
  const width = ctx.measureText(text).width;
  const textCenter = rotatedVector(
    width / 2,
    -fontSize / 2,
    CONSTANTS.labelAngle,
  );
  const baseOffset = labelOffset();
  const candidates = [
    {
      x: point.x + baseOffset,
      y: point.y - baseOffset,
      preference: 0,
    },
  ];
  const distances = [
    CONSTANTS.stationRadius
      + Math.max(16, fontSize)
      + (Math.min(width, 90) / 2),
    CONSTANTS.stationRadius + Math.max(30, fontSize * 2),
    CONSTANTS.stationRadius + Math.max(48, fontSize * 3),
    CONSTANTS.stationRadius + Math.max(70, fontSize * 4),
  ];
  const angles = [
    -45,
    45,
    -135,
    135,
    -90,
    90,
    0,
    180,
    -30,
    30,
    -120,
    120,
  ];
  for (
    let distanceIndex = 0;
    distanceIndex < distances.length;
    distanceIndex += 1
  ) {
    const distance = distances[distanceIndex];
    for (
      let angleIndex = 0;
      angleIndex < angles.length;
      angleIndex += 1
    ) {
      const radians = angles[angleIndex] * Math.PI / 180;
      const center = {
        x: point.x + (Math.cos(radians) * distance),
        y: point.y + (Math.sin(radians) * distance),
      };
      candidates.push({
        x: center.x - textCenter.x,
        y: center.y - textCenter.y,
        preference: 1 + (distanceIndex * 2) + (angleIndex / 100),
      });
    }
  }
  return candidates;
}
'''
    app = replace_between(
        app,
        "function drawStations() {",
        "function clampLabelCandidate(",
        draw_block,
        "station symbols and semantic labels",
    )

    app = replace_once(
        app,
        "    tooltip.innerHTML = `<strong>${escapeHtml(displayLabel(stop.lbl))}</strong><span>${stop.x}, ${stop.y} · ${lines.join(', ')}</span>`;",
        '''    const abbr = stationAbbreviation(stop);
    const abbrText = abbr ? ` · ${escapeHtml(abbr)}` : '';
    tooltip.innerHTML = `<strong>${escapeHtml(displayLabel(stop.lbl))}${abbrText}</strong><span>${stop.x}, ${stop.y} · ${lines.join(', ')}</span>`;''',
        "station tooltip abbreviation",
    )

    app = replace_once(
        app,
        '''  infoPopup.innerHTML = `
    <h2>${escapeHtml(displayLabel(stop.lbl))}</h2>
    <p>Coords: (${stop.x}, ${stop.y})<br>Status: ${statusText}<br>${railwayText}</p>''',
        '''  const abbreviation = stationAbbreviation(stop);
  const abbreviationHtml = abbreviation
    ? `<span class="station-abbr">${escapeHtml(abbreviation)}</span>`
    : '';
  infoPopup.innerHTML = `
    <h2>${escapeHtml(displayLabel(stop.lbl))} ${abbreviationHtml}</h2>
    <p>Coords: (${stop.x}, ${stop.y})<br>Status: ${statusText}<br>${railwayText}</p>''',
        "station popup abbreviation",
    )

    app = replace_once(
        app,
        '''  return lineNames.map((lineName) => (
    `<span class="line-badge" style="--line-color: ${escapeHtml(colorForLine(lineName))}">${escapeHtml(lineName)}</span>`
  )).join('');''',
        '''  return lineNames.map((lineName) => {
    const lineColor = colorForLine(lineName);
    const lineInk = contrastingTextColor(lineColor);
    return `<span class="line-badge" style="--line-color: ${escapeHtml(lineColor)}; --line-ink: ${escapeHtml(lineInk)}">${escapeHtml(lineName)}</span>`;
  }).join('');''',
        "circular line badges",
    )

    search_block = '''function searchMatches(query) {
  const normalizedQuery = normalizeIdentity(query);
  if (!normalizedQuery) {
    return [];
  }
  const ranked = [];
  for (const stop of state.data.stops) {
    const normalizedLabel = normalizeIdentity(stop.lbl);
    const normalizedDisplay = normalizeIdentity(displayLabel(stop.lbl));
    const normalizedAbbr = normalizeIdentity(stationAbbreviation(stop));
    const normalizedVar = normalizeIdentity(stop.var.replace(/^P_/, ''));
    const labelCandidates = [normalizedLabel, normalizedDisplay];
    let rank = null;
    if (labelCandidates.includes(normalizedQuery)) {
      rank = [0, stop.lbl.length, stop.lbl.toLowerCase()];
    } else if (normalizedAbbr && normalizedQuery === normalizedAbbr) {
      rank = [1, stationAbbreviation(stop).length, stop.lbl.toLowerCase()];
    } else if (normalizedQuery === normalizedVar) {
      rank = [2, stop.var.length, stop.lbl.toLowerCase()];
    } else if (
      labelCandidates.some((candidate) => candidate.startsWith(normalizedQuery))
    ) {
      rank = [3, stop.lbl.length, stop.lbl.toLowerCase()];
    } else if (
      normalizedAbbr
      && normalizedAbbr.startsWith(normalizedQuery)
    ) {
      rank = [4, stationAbbreviation(stop).length, stop.lbl.toLowerCase()];
    } else if (normalizedVar.startsWith(normalizedQuery)) {
      rank = [5, stop.var.length, stop.lbl.toLowerCase()];
    } else if (
      labelCandidates.some((candidate) => candidate.includes(normalizedQuery))
    ) {
      rank = [6, stop.lbl.length, stop.lbl.toLowerCase()];
    } else if (
      normalizedAbbr
      && normalizedAbbr.includes(normalizedQuery)
    ) {
      rank = [7, stationAbbreviation(stop).length, stop.lbl.toLowerCase()];
    } else if (normalizedVar.includes(normalizedQuery)) {
      rank = [8, stop.var.length, stop.lbl.toLowerCase()];
    }
    if (rank) {
      ranked.push({ rank, stop });
    }
  }
  ranked.sort((a, b) => compareRank(a.rank, b.rank));
  return ranked.map((item) => item.stop);
}
'''
    app = replace_between(
        app,
        "function searchMatches(query) {",
        "function coordinateQueryPoint(",
        search_block,
        "abbreviation-aware search",
    )

    if "fitCurrentRoute({ render: false });" not in app:
        app = replace_regex_once(
            app,
            r"^([ \t]*)routeSteps\.textContent"
            r"\s*=\s*routeInstructions\(route\);[ \t]*$",
            r"\1routeSteps.textContent = routeInstructions(route);"
            "\n"
            r"\1fitCurrentRoute({ render: false });",
            "automatic route fitting",
        )

    app = replace_once(
        app,
        '''  return state.data.stops.find((stop) => normalizeIdentity(stop.lbl) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(displayLabel(stop.lbl)) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(stop.var) === normalized)''',
        '''  return state.data.stops.find((stop) => normalizeIdentity(stop.lbl) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(displayLabel(stop.lbl)) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(stationAbbreviation(stop)) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(stop.var) === normalized)''',
        "abbreviation-aware route resolution",
    )

    helper_block = '''function stationAbbreviation(stop) {
  return String(stop?.abbr || '').trim();
}

function isPlaceholderStop(stop) {
  return /^[A-Z]{1,3}\\d+(?:_\\d+)?$/.test(displayLabel(stop.lbl));
}

function isPhosphagos(stop) {
  return normalizeIdentity(displayLabel(stop.lbl))
    === normalizeIdentity('Mt. Phosphagos');
}

function isJunctionStop(stop) {
  return linesForStop(stop).filter(
    (lineName) => state.visibleLines.has(lineName),
  ).length > 1;
}

function terminalLineNames(stop) {
  const terminalLines = [];
  for (const [lineName, stopVars] of Object.entries(
    state.data.line_stop_vars || {},
  )) {
    if (!state.visibleLines.has(lineName) || !stopVars.length) {
      continue;
    }
    if (
      stopVars[0] === stop.var
      || stopVars[stopVars.length - 1] === stop.var
    ) {
      terminalLines.push(lineName);
    }
  }
  return terminalLines;
}

function markerLineNamesForStop(stop) {
  const terminalLines = terminalLineNames(stop);
  if (isJunctionStop(stop) && labelZoomMode() !== 'world') {
    return [...new Set([
      ...terminalLines,
      ...linesForStop(stop).filter(
        (lineName) => state.visibleLines.has(lineName),
      ),
    ])];
  }
  return terminalLines;
}

function stationMarkerSize(stop) {
  if (isPhosphagos(stop)) {
    return 11;
  }
  if (isJunctionStop(stop)) {
    return 9;
  }
  return 7;
}

function labelZoomMode() {
  const scale = cameraStyleScale();
  if (scale < 2.15) {
    return 'world';
  }
  if (scale < 5.25) {
    return 'regional';
  }
  return 'close';
}

function stationIsRouteEndpoint(stop) {
  return state.currentRoute
    && (
      state.currentRoute.startVar === stop.var
      || state.currentRoute.endVar === stop.var
    );
}

function stationLabelPriority(stop) {
  if (isPhosphagos(stop)) return 0;
  if (state.selectedStop?.var === stop.var) return 1;
  if (stationIsRouteEndpoint(stop)) return 2;
  if (isJunctionStop(stop)) return 3;
  if (terminalLineNames(stop).length) return 4;
  if (stop.is_connected) return 5;
  return 6;
}

function shouldAttemptStationLabel(stop) {
  if (labelZoomMode() === 'close') {
    return true;
  }
  if (labelZoomMode() === 'world' && isPlaceholderStop(stop)) {
    return stationLabelPriority(stop) <= 4;
  }
  return true;
}

function stationLabelTextOptions(stop) {
  const fullLabel = displayLabel(stop.lbl);
  const abbreviation = stationAbbreviation(stop);
  if (labelZoomMode() === 'close' || !abbreviation) {
    return [fullLabel];
  }
  return abbreviation === fullLabel
    ? [fullLabel]
    : [fullLabel, abbreviation];
}

function stationLabelScoreLimit() {
  if (labelZoomMode() === 'world') {
    return 60000;
  }
  if (labelZoomMode() === 'regional') {
    return 125000;
  }
  return Number.POSITIVE_INFINITY;
}

function contrastingTextColor(color) {
  const match = /^#?([0-9a-f]{6})$/i.exec(
    String(color || '').trim(),
  );
  if (!match) {
    return CONSTANTS.textColor;
  }
  const value = match[1];
  const red = parseInt(value.slice(0, 2), 16);
  const green = parseInt(value.slice(2, 4), 16);
  const blue = parseInt(value.slice(4, 6), 16);
  const luminance = (
    (red * 0.299)
    + (green * 0.587)
    + (blue * 0.114)
  ) / 255;
  return luminance > 0.58
    ? CONSTANTS.stationDarkOutline
    : CONSTANTS.textColor;
}
'''
    app = replace_once(
        app,
        "function stationColor(stop) {",
        helper_block + "\nfunction stationColor(stop) {",
        "station marker and semantic-zoom helpers",
    )

    required = [
        "function fitCurrentRoute(",
        "function stationAbbreviation(",
        "function drawStationMarker(",
        "function labelZoomMode(",
        "station-abbr",
    ]
    missing = [item for item in required if item not in app]
    if missing:
        raise RuntimeError(f"Transformed app.js is missing: {missing}")
    return app


def enrich_network(network_text: str) -> tuple[str, list[str]]:
    payload = json.loads(network_text)
    stops = payload.get("stops")
    if not isinstance(stops, list):
        raise RuntimeError("docs/metro_network.json has no stops list.")

    found: set[str] = set()
    for stop in stops:
        if not isinstance(stop, dict):
            continue
        label = str(stop.get("lbl", ""))
        if label in STATION_ABBREVIATIONS:
            stop["abbr"] = STATION_ABBREVIATIONS[label]
            found.add(label)

    missing = sorted(set(STATION_ABBREVIATIONS) - found)
    return (
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        missing,
    )


def validate_javascript(path: Path) -> str:
    node = shutil.which("node")
    if not node:
        return "Node.js was not found; JavaScript syntax check was skipped."
    result = subprocess.run(
        [node, "--check", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "node --check failed:\n"
            + (result.stdout or "")
            + (result.stderr or "")
        )
    return "node --check passed."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Path to the Plumville repository root.",
    )
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    docs = repo / "docs"
    paths = {
        "app": docs / "app.js",
        "styles": docs / "styles.css",
        "network": docs / "metro_network.json",
    }
    for path in paths.values():
        if not path.is_file():
            raise RuntimeError(f"Required file not found: {path}")

    originals = {
        key: path.read_bytes()
        for key, path in paths.items()
    }

    try:
        transformed_app = transform_app(
            originals["app"].decode("utf-8")
        )
        transformed_network, missing = enrich_network(
            originals["network"].decode("utf-8")
        )

        atomic_write(paths["app"], transformed_app)
        atomic_write(paths["styles"], STYLES_CSS.rstrip() + "\n")
        atomic_write(paths["network"], transformed_network)

        json.loads(paths["network"].read_text(encoding="utf-8"))
        syntax_result = validate_javascript(paths["app"])

        print("Updated:")
        for path in paths.values():
            print(f"- {path.relative_to(repo)}")
        print(syntax_result)
        if missing:
            print(
                "Warning: abbreviations were not matched for: "
                + ", ".join(missing)
            )
        else:
            print(
                f"Added or refreshed {len(STATION_ABBREVIATIONS)} "
                "station abbreviations."
            )
        print()
        print("No commit or push was performed.")
        print(
            "Review with:\n"
            "  git diff -- docs/app.js docs/styles.css "
            "docs/metro_network.json"
        )
        print("Then run:\n  npm test")
        return 0
    except Exception:
        for key, path in paths.items():
            path.write_bytes(originals[key])
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
