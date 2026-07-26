#!/usr/bin/env python3
# Apply Plumville public-viewer implementation run 03.
#
# Changes only:
# - docs/app.js
# - docs/styles.css
# - docs/index.html
#
# The updater does not commit, push, pull, or touch ignored runtime data.
# It restores all three original files if a transformation or check fails.

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


INDEX_HTML = '<!doctype html>\n<html lang="en">\n  <head>\n    <meta charset="utf-8">\n    <meta\n      name="viewport"\n      content="width=device-width, initial-scale=1, viewport-fit=cover"\n    >\n    <title>Plumville Metro Viewer</title>\n    <link rel="canonical" href="https://akapppy.github.io/Plumville/">\n    <meta property="og:title" content="Plumville Metro Viewer">\n    <meta\n      property="og:description"\n      content="Explore the Plumville metro map."\n    >\n    <meta property="og:type" content="website">\n    <meta\n      property="og:url"\n      content="https://akapppy.github.io/Plumville/"\n    >\n    <link rel="stylesheet" href="styles.css?v=20260726-run03">\n  </head>\n  <body>\n    <main class="viewer-shell">\n      <aside\n        class="side-panel"\n        aria-label="Map controls and station details"\n      >\n        <section class="control-section" aria-label="Network">\n          <h1>Plumville Metro</h1>\n          <p id="summaryText" class="summary">\n            Loading the network...\n          </p>\n        </section>\n\n        <section class="control-section" aria-label="Search">\n          <label\n            class="field-label section-heading"\n            for="searchInput"\n          >\n            Search\n          </label>\n          <div class="input-row">\n            <input\n              id="searchInput"\n              class="sidebar-input"\n              type="search"\n              autocomplete="off"\n              aria-autocomplete="list"\n              aria-controls="stationSuggestions"\n              aria-expanded="false"\n              placeholder="Blackport"\n            >\n            <button id="searchButton" type="button">Go</button>\n          </div>\n          <p id="searchStatus" class="hint">\n            Search by station, or enter x, y to plot a point.\n          </p>\n        </section>\n\n        <section\n          class="control-section"\n          aria-labelledby="showHideHeading"\n        >\n          <p id="showHideHeading" class="section-heading">View</p>\n          <label class="check-row">\n            <input id="showWorldMapInput" type="checkbox" checked>\n            <span>World Map</span>\n          </label>\n          <label class="check-row">\n            <input id="showLabelsInput" type="checkbox" checked>\n            <span>Station labels</span>\n          </label>\n          <label class="check-row">\n            <input\n              id="showSuggestedWalkingPathsInput"\n              type="checkbox"\n            >\n            <span>Suggested walking paths</span>\n          </label>\n          <div\n            id="lineLegend"\n            class="line-legend"\n            aria-label="Line visibility"\n          ></div>\n        </section>\n\n        <details class="collapsible-section" open>\n          <summary>Directions</summary>\n          <section class="control-section">\n            <label class="field-label" for="routeStartInput">\n              From\n            </label>\n            <input\n              id="routeStartInput"\n              class="sidebar-input"\n              type="search"\n              autocomplete="off"\n              aria-autocomplete="list"\n              aria-controls="stationSuggestions"\n              aria-expanded="false"\n              placeholder="Blackport"\n            >\n            <p class="hint">Station label or code</p>\n\n            <label\n              class="field-label spaced"\n              for="routeEndInput"\n            >\n              To\n            </label>\n            <input\n              id="routeEndInput"\n              class="sidebar-input"\n              type="search"\n              autocomplete="off"\n              aria-autocomplete="list"\n              aria-controls="stationSuggestions"\n              aria-expanded="false"\n              placeholder="Dicton"\n            >\n            <p class="hint">Station label or code</p>\n\n            <div class="actions" aria-label="Route actions">\n              <button id="routeButton" type="button">Route</button>\n              <button id="swapRouteButton" type="button">Swap</button>\n              <button id="clearRouteButton" type="button">Clear</button>\n            </div>\n          </section>\n\n          <section class="text-panel" aria-live="polite">\n            <p id="routeSummary">Choose two stations.</p>\n            <pre id="routeSteps">Enter or select two stations, then press Route.</pre>\n          </section>\n        </details>\n\n        <div class="actions" aria-label="Map actions">\n          <button id="resetViewButton" type="button">\n            Reset view\n          </button>\n          <button id="fitMapButton" type="button">Fit map</button>\n          <button id="blackportButton" type="button">\n            Blackport\n          </button>\n          <button id="copyLinkButton" type="button">\n            Copy link\n          </button>\n          <button id="clearSelectionButton" type="button">\n            Clear selection\n          </button>\n        </div>\n      </aside>\n\n      <section\n        class="map-stage"\n        aria-label="Interactive Plumville metro map"\n      >\n        <canvas\n          id="metroCanvas"\n          aria-label="Metro map canvas"\n        ></canvas>\n        <div class="map-controls" aria-label="Map zoom controls">\n          <button\n            id="mapZoomInButton"\n            type="button"\n            aria-label="Zoom in"\n          >\n            +\n          </button>\n          <button\n            id="mapZoomOutButton"\n            type="button"\n            aria-label="Zoom out"\n          >\n            −\n          </button>\n          <button\n            id="mapFitButton"\n            type="button"\n            aria-label="Fit active route or map"\n          >\n            Fit\n          </button>\n        </div>\n        <div id="tooltip" class="tooltip" hidden></div>\n        <div id="infoPopup" class="info-popup" hidden></div>\n      </section>\n    </main>\n\n    <div\n      id="stationSuggestions"\n      class="station-suggestions"\n      role="listbox"\n      aria-label="Station suggestions"\n      hidden\n    ></div>\n\n    <script src="app.js?v=20260726-run03" defer></script>\n  </body>\n</html>\n'
STYLES_CSS = ':root {\n  color-scheme: dark;\n  --bg: #080b0d;\n  --panel: #101417;\n  --panel-raised: #151b1f;\n  --panel-inset: #090c0e;\n  --panel-hover: #20282d;\n  --ink: #f5f7f2;\n  --muted: #9aa59f;\n  --faint: #68736d;\n  --line: #2b3439;\n  --border-light: #465159;\n  --border-dark: #050708;\n  --field: #090c0e;\n  --field-active: #12181c;\n  --emerald: #55b86a;\n  --gold: #f0c75e;\n  --redstone: #de5750;\n  --diamond: #72c9ec;\n  --focus-ring: rgba(114, 201, 236, 0.34);\n  --shadow: rgba(0, 0, 0, 0.42);\n  --panel-width: 356px;\n  --safe-top: env(safe-area-inset-top, 0px);\n  --safe-right: env(safe-area-inset-right, 0px);\n  --safe-bottom: env(safe-area-inset-bottom, 0px);\n  --safe-left: env(safe-area-inset-left, 0px);\n}\n\n* {\n  box-sizing: border-box;\n}\n\nhtml,\nbody {\n  height: 100%;\n}\n\nhtml {\n  background: var(--bg);\n}\n\nbody {\n  margin: 0;\n  background:\n    linear-gradient(rgba(255, 255, 255, 0.012) 1px, transparent 1px),\n    linear-gradient(90deg, rgba(255, 255, 255, 0.012) 1px, transparent 1px),\n    var(--bg);\n  background-size: 16px 16px;\n  color: var(--ink);\n  font-family:\n    Inter,\n    ui-sans-serif,\n    -apple-system,\n    BlinkMacSystemFont,\n    "Segoe UI",\n    Helvetica,\n    Arial,\n    sans-serif;\n}\n\nbutton,\ninput {\n  font: inherit;\n}\n\nbutton,\ninput,\nsummary {\n  -webkit-tap-highlight-color: transparent;\n}\n\n.viewer-shell {\n  display: grid;\n  grid-template-columns: var(--panel-width) minmax(0, 1fr);\n  min-height: 100vh;\n  min-height: 100svh;\n}\n\n.side-panel {\n  position: relative;\n  z-index: 4;\n  display: flex;\n  flex-direction: column;\n  gap: 12px;\n  width: var(--panel-width);\n  min-height: 100vh;\n  min-height: 100svh;\n  max-height: 100vh;\n  max-height: 100svh;\n  padding:\n    calc(14px + var(--safe-top))\n    14px\n    calc(18px + var(--safe-bottom))\n    calc(14px + var(--safe-left));\n  background:\n    linear-gradient(180deg, rgba(255, 255, 255, 0.018), transparent 180px),\n    var(--panel);\n  border-right: 1px solid var(--border-light);\n  box-shadow:\n    inset -1px 0 var(--border-dark),\n    10px 0 28px rgba(0, 0, 0, 0.2);\n  overflow-y: auto;\n  scrollbar-color: var(--border-light) var(--panel-inset);\n}\n\n.map-stage {\n  position: relative;\n  min-height: 100vh;\n  min-height: 100svh;\n  background: var(--bg);\n  overflow: hidden;\n  isolation: isolate;\n}\n\n#metroCanvas {\n  display: block;\n  width: 100%;\n  height: 100%;\n  min-height: 100vh;\n  min-height: 100svh;\n  cursor: grab;\n  touch-action: none;\n}\n\n#metroCanvas.dragging {\n  cursor: grabbing;\n}\n\n.map-controls {\n  position: absolute;\n  top: calc(14px + var(--safe-top));\n  right: calc(14px + var(--safe-right));\n  z-index: 2;\n  display: grid;\n  gap: 7px;\n}\n\n.map-controls button {\n  width: 42px;\n  min-height: 42px;\n  padding: 0;\n  border-color: var(--border-light);\n  background: rgba(16, 20, 23, 0.93);\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.08),\n    inset -2px -2px var(--border-dark),\n    0 8px 24px var(--shadow);\n  backdrop-filter: blur(8px);\n}\n\n.map-controls #mapFitButton {\n  width: 50px;\n  color: var(--diamond);\n}\n\nh1,\nh2,\np,\npre {\n  margin: 0;\n}\n\nh1,\nh2,\n.section-heading,\n.collapsible-section > summary {\n  font-family:\n    "SFMono-Regular",\n    "Cascadia Mono",\n    Menlo,\n    Consolas,\n    monospace;\n}\n\nh1 {\n  font-size: 21px;\n  line-height: 1.15;\n}\n\nh2 {\n  font-size: 22px;\n  line-height: 1.15;\n}\n\n.control-section,\n.collapsible-section,\n.text-panel {\n  border: 1px solid var(--border-light);\n  background: var(--panel-raised);\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.05),\n    inset -2px -2px var(--border-dark),\n    0 5px 16px rgba(0, 0, 0, 0.14);\n}\n\n.control-section {\n  display: grid;\n  gap: 8px;\n  padding: 11px;\n}\n\n.section-heading,\n.collapsible-section > summary {\n  color: var(--ink);\n  font-size: 15px;\n  font-weight: 800;\n  line-height: 1.2;\n  text-transform: uppercase;\n}\n\n.collapsible-section {\n  display: grid;\n  gap: 0;\n}\n\n.collapsible-section > summary {\n  position: relative;\n  min-height: 44px;\n  padding: 13px 38px 11px 12px;\n  cursor: pointer;\n  list-style: none;\n  user-select: none;\n}\n\n.collapsible-section > summary::-webkit-details-marker {\n  display: none;\n}\n\n.collapsible-section > summary::after {\n  content: "+";\n  position: absolute;\n  top: 50%;\n  right: 13px;\n  width: 20px;\n  height: 20px;\n  border: 1px solid var(--border-light);\n  background: var(--panel-inset);\n  color: var(--diamond);\n  font-family: monospace;\n  font-size: 17px;\n  line-height: 17px;\n  text-align: center;\n  transform: translateY(-50%);\n}\n\n.collapsible-section[open] > summary::after {\n  content: "−";\n}\n\n.collapsible-section > .control-section,\n.collapsible-section > .summary,\n.collapsible-section > .text-panel {\n  margin: 0 10px 10px;\n}\n\n.collapsible-section > .control-section {\n  border-color: var(--line);\n  background: var(--panel-inset);\n}\n\n.summary,\n.hint,\n.text-panel,\n.info-popup p {\n  color: var(--ink);\n  font-size: 12px;\n  line-height: 1.45;\n  white-space: pre-line;\n}\n\n.summary {\n  color: #c9d1cc;\n}\n\n.hint {\n  color: var(--muted);\n  font-size: 11px;\n}\n\n.field-label {\n  display: block;\n  color: var(--ink);\n  font-size: 12px;\n  font-weight: 800;\n}\n\n.field-label.spaced {\n  margin-top: 5px;\n}\n\n.input-row {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) auto;\n  gap: 8px;\n}\n\n.sidebar-input {\n  width: 100%;\n  min-height: 38px;\n  padding: 8px 10px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: var(--field);\n  color: var(--ink);\n  outline: none;\n  box-shadow:\n    inset 2px 2px var(--border-dark),\n    inset -1px -1px rgba(255, 255, 255, 0.035);\n}\n\n.sidebar-input::placeholder {\n  color: var(--faint);\n}\n\n.sidebar-input:focus {\n  background: var(--field-active);\n  border-color: var(--diamond);\n  box-shadow:\n    0 0 0 3px var(--focus-ring),\n    inset 2px 2px var(--border-dark);\n}\n\n.actions {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 8px;\n}\n\nbutton {\n  min-height: 36px;\n  padding: 7px 11px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: var(--panel-raised);\n  color: var(--ink);\n  font-size: 11px;\n  font-weight: 800;\n  cursor: pointer;\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.08),\n    inset -2px -2px var(--border-dark);\n}\n\nbutton:hover {\n  border-color: #69767e;\n  background: var(--panel-hover);\n}\n\nbutton:focus-visible {\n  border-color: var(--diamond);\n  outline: 3px solid var(--focus-ring);\n  outline-offset: 1px;\n}\n\nbutton:active {\n  transform: translateY(1px);\n  box-shadow:\n    inset 2px 2px var(--border-dark),\n    inset -1px -1px rgba(255, 255, 255, 0.04);\n}\n\n#routeButton,\n#searchButton {\n  border-color: #4f8e5c;\n  background: linear-gradient(180deg, #397b49, #2a6338);\n}\n\n.check-row {\n  display: flex;\n  align-items: center;\n  gap: 9px;\n  min-height: 30px;\n  color: var(--ink);\n  font-size: 12px;\n  cursor: pointer;\n}\n\n.check-row input {\n  width: 16px;\n  height: 16px;\n  margin: 0;\n  accent-color: var(--emerald);\n}\n\n.line-legend {\n  display: grid;\n  grid-template-columns: repeat(auto-fill, minmax(86px, 1fr));\n  gap: 7px;\n  margin-top: 7px;\n}\n\n.line-toggle {\n  display: inline-flex;\n  align-items: center;\n  gap: 7px;\n  min-height: 36px;\n  padding: 5px 7px;\n  border: 1px solid var(--line);\n  border-radius: 2px;\n  background: var(--panel-inset);\n  color: var(--ink);\n  font-size: 11px;\n  font-weight: 800;\n  cursor: pointer;\n}\n\n.line-toggle:hover {\n  border-color: var(--border-light);\n  background: var(--panel-hover);\n}\n\n.line-toggle input {\n  width: 13px;\n  height: 13px;\n  margin: 0;\n  accent-color: var(--emerald);\n}\n\n.line-swatch,\n.line-badge {\n  display: inline-grid;\n  place-items: center;\n  flex: 0 0 auto;\n  border-radius: 50%;\n  background: var(--line-color, var(--panel-hover));\n  font-family:\n    "SFMono-Regular",\n    Menlo,\n    Consolas,\n    monospace;\n  font-weight: 900;\n  line-height: 1;\n}\n\n.line-swatch {\n  width: 22px;\n  height: 22px;\n  border: 2px solid currentColor;\n  color: var(--ink);\n  font-size: 11px;\n}\n\n.line-badges {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 6px;\n  margin-top: 5px;\n}\n\n.line-badge {\n  width: 25px;\n  height: 25px;\n  min-height: 25px;\n  padding: 0;\n  border: 2px solid var(--line-ink, var(--ink));\n  color: var(--line-ink, var(--ink));\n  font-size: 11px;\n}\n\n.line-badge.muted {\n  width: auto;\n  min-width: 42px;\n  padding: 0 8px;\n  border-radius: 2px;\n  border-color: var(--border-light);\n  background: var(--panel-inset);\n  color: var(--muted);\n}\n\n.text-panel {\n  height: auto;\n  min-height: 0;\n  max-height: none;\n  padding: 11px 12px;\n  overflow: visible;\n}\n\n#routeSummary {\n  margin-bottom: 9px;\n  color: var(--gold);\n  font-weight: 800;\n}\n\n#routeSteps {\n  height: auto;\n  min-height: 0;\n  max-height: none;\n  overflow: visible;\n  white-space: pre-wrap;\n  color: var(--ink);\n  font-size: 12px;\n  line-height: 1.45;\n  font-family: inherit;\n}\n\n\n.station-suggestions {\n  position: fixed;\n  z-index: 20;\n  display: grid;\n  max-height: min(320px, 44dvh);\n  padding: 5px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: rgba(9, 12, 14, 0.985);\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.04),\n    inset -2px -2px var(--border-dark),\n    0 14px 34px var(--shadow);\n  overflow-x: hidden;\n  overflow-y: auto;\n  overscroll-behavior: contain;\n  scrollbar-color: var(--border-light) var(--panel-inset);\n  -webkit-overflow-scrolling: touch;\n}\n\n.station-suggestions[hidden] {\n  display: none;\n}\n\n.station-suggestion {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) auto;\n  align-items: center;\n  gap: 10px;\n  width: 100%;\n  min-height: 40px;\n  padding: 7px 9px;\n  border: 1px solid transparent;\n  border-radius: 1px;\n  background: transparent;\n  color: var(--ink);\n  text-align: left;\n  box-shadow: none;\n}\n\n.station-suggestion:hover,\n.station-suggestion.active,\n.station-suggestion[aria-selected="true"] {\n  border-color: var(--diamond);\n  background: var(--panel-hover);\n  outline: none;\n}\n\n.station-suggestion-name {\n  min-width: 0;\n  overflow: hidden;\n  font-size: 12px;\n  font-weight: 800;\n  text-overflow: ellipsis;\n  white-space: nowrap;\n}\n\n.station-suggestion-meta {\n  display: inline-flex;\n  align-items: center;\n  gap: 7px;\n  color: var(--muted);\n  font-size: 10px;\n}\n\n.station-suggestion-abbr {\n  min-width: 34px;\n  padding: 3px 5px;\n  border: 1px solid #8c743a;\n  border-radius: 2px;\n  background: #2a2415;\n  color: var(--gold);\n  font-family:\n    "SFMono-Regular",\n    Menlo,\n    Consolas,\n    monospace;\n  font-weight: 900;\n  text-align: center;\n}\n\n.station-suggestion-empty {\n  padding: 10px;\n  color: var(--muted);\n  font-size: 12px;\n}\n\n.tooltip {\n  position: absolute;\n  z-index: 3;\n  max-width: min(300px, calc(100% - 16px));\n  padding: 9px 11px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: rgba(16, 20, 23, 0.96);\n  color: var(--ink);\n  box-shadow: 0 8px 24px var(--shadow);\n  pointer-events: none;\n}\n\n.tooltip strong {\n  display: block;\n  margin-bottom: 3px;\n  font-size: 12px;\n}\n\n.tooltip span {\n  color: var(--muted);\n  font-size: 12px;\n}\n\n.info-popup {\n  position: absolute;\n  z-index: 2;\n  width: max-content;\n  max-width: min(340px, calc(100% - 16px));\n  max-height: calc(100% - 16px);\n  overflow: auto;\n  padding: 11px 12px;\n  border: 1px solid var(--border-light);\n  border-radius: 2px;\n  background: rgba(16, 20, 23, 0.97);\n  color: var(--ink);\n  box-shadow:\n    inset 1px 1px rgba(255, 255, 255, 0.045),\n    inset -2px -2px var(--border-dark),\n    0 12px 34px var(--shadow);\n}\n\n.info-popup h2 {\n  display: flex;\n  flex-wrap: wrap;\n  align-items: baseline;\n  gap: 8px;\n  margin-bottom: 7px;\n}\n\n.station-abbr {\n  display: inline-block;\n  padding: 2px 5px;\n  border: 1px solid #8c743a;\n  border-radius: 2px;\n  background: #2a2415;\n  color: var(--gold);\n  font-family:\n    "SFMono-Regular",\n    Menlo,\n    Consolas,\n    monospace;\n  font-size: 11px;\n  font-weight: 900;\n}\n\n.info-popup .section-label {\n  margin-top: 9px;\n  color: var(--muted);\n  font-size: 10px;\n  font-weight: 900;\n  letter-spacing: 0.08em;\n  text-transform: uppercase;\n}\n\n@media (max-width: 860px) {\n  .viewer-shell {\n    display: block;\n    min-height: 100svh;\n  }\n\n  .map-stage {\n    position: sticky;\n    top: 0;\n    z-index: 5;\n    width: 100%;\n    height: clamp(230px, 42dvh, 440px);\n    min-height: 0;\n    max-height: none;\n    border-bottom: 1px solid var(--border-light);\n    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);\n  }\n\n  #metroCanvas {\n    width: 100%;\n    height: 100%;\n    min-height: 0;\n  }\n\n  .side-panel {\n    width: 100%;\n    min-height: calc(100svh - 42dvh);\n    max-height: none;\n    padding:\n      9px\n      max(9px, var(--safe-right))\n      max(11px, var(--safe-bottom))\n      max(9px, var(--safe-left));\n    border-top: 1px solid var(--border-dark);\n    border-right: 0;\n    box-shadow: none;\n    overflow: visible;\n  }\n\n  .map-controls {\n    top: max(8px, var(--safe-top));\n    right: max(8px, var(--safe-right));\n  }\n\n  .map-controls button,\n  button,\n  .sidebar-input {\n    min-height: 44px;\n  }\n\n  .map-controls button {\n    width: 46px;\n  }\n\n  .map-controls #mapFitButton {\n    width: 56px;\n  }\n\n  .line-toggle {\n    min-height: 42px;\n  }\n\n  .station-suggestions {\n    max-height: min(300px, 42dvh);\n  }\n}\n\n@media (max-width: 860px) and (orientation: landscape) {\n  .map-stage {\n    height: clamp(180px, 48dvh, 320px);\n  }\n\n  .side-panel {\n    min-height: 52dvh;\n  }\n}\n\n@media (max-width: 560px) {\n  .side-panel {\n    gap: 9px;\n    padding-inline:\n      max(7px, var(--safe-left))\n      max(7px, var(--safe-right));\n  }\n\n  .line-legend {\n    grid-template-columns: repeat(3, minmax(0, 1fr));\n  }\n\n  .actions {\n    display: grid;\n    grid-template-columns: repeat(2, minmax(0, 1fr));\n  }\n\n  .actions button {\n    width: 100%;\n  }\n\n  .input-row {\n    grid-template-columns: minmax(0, 1fr) 56px;\n  }\n\n  .info-popup {\n    width: min(330px, calc(100% - 12px));\n    max-width: none;\n  }\n\n  .station-suggestions {\n    max-height: min(280px, 40dvh);\n  }\n}\n\n@media (prefers-reduced-motion: reduce) {\n  *,\n  *::before,\n  *::after {\n    transition-duration: 0.001ms !important;\n  }\n}\n'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one matching block, found {count}."
        )
    return text.replace(old, new, 1)


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
        "const stationSuggestions = document.querySelector('#stationSuggestions');",
        '''const stationSuggestions = document.querySelector('#stationSuggestions');
const mapStage = document.querySelector('.map-stage');
const sidePanel = document.querySelector('.side-panel');''',
        "public suggestion and map-stage elements",
    )

    app = replace_once(
        app,
        '''  stationRadius: 4,
  stationHitTolerance: 10,''',
        '''  stationRadius: 9,
  stationHitTolerance: 16,''',
        "larger public station markers",
    )

    app = replace_once(
        app,
        '''  lineMarkerRadius: 8,
};''',
        '''  lineMarkerRadius: 9,
  lineMarkerDistances: [34, 48, 64, 82],
  overlayMargin: 8,
};''',
        "line shield settings",
    )

    app = replace_once(
        app,
        '''  lastPointer: null,
  renderScheduled: false,
};''',
        '''  lastPointer: null,
  renderScheduled: false,
  stationSuggestionStops: [],
  activeSuggestionInput: null,
  activeSuggestionIndex: -1,
  resizeFrame: null,
};''',
        "suggestion and resize state",
    )

    suggestion_helpers = r'''function populateStationSuggestions() {
  state.stationSuggestionStops = [...state.data.stops].sort(
    (first, second) => displayLabel(first.lbl).localeCompare(
      displayLabel(second.lbl),
      undefined,
      { numeric: true },
    ),
  );
  stationSuggestions.replaceChildren();
}

function suggestionStopsForInput(input) {
  const query = input.value.trim();
  if (!query) {
    return state.stationSuggestionStops.slice(0, 100);
  }
  return searchMatches(query).slice(0, 100);
}

function renderStationSuggestions(input) {
  if (!input || document.activeElement !== input) {
    return;
  }
  state.activeSuggestionInput = input;
  state.activeSuggestionIndex = -1;
  const stops = suggestionStopsForInput(input);
  stationSuggestions.replaceChildren();

  if (!stops.length) {
    const empty = document.createElement('div');
    empty.className = 'station-suggestion-empty';
    empty.textContent = 'No station matches.';
    stationSuggestions.append(empty);
  } else {
    stops.forEach((stop, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.id = `station-suggestion-${index}`;
      button.className = 'station-suggestion';
      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', 'false');
      button.dataset.stopVar = stop.var;

      const name = document.createElement('span');
      name.className = 'station-suggestion-name';
      name.textContent = displayLabel(stop.lbl);

      const meta = document.createElement('span');
      meta.className = 'station-suggestion-meta';
      const abbreviation = stationAbbreviation(stop);
      if (abbreviation) {
        const abbr = document.createElement('span');
        abbr.className = 'station-suggestion-abbr';
        abbr.textContent = abbreviation;
        meta.append(abbr);
      }
      const code = document.createElement('span');
      code.textContent = stop.var.replace(/^P_/, '');
      meta.append(code);

      button.append(name, meta);
      button.addEventListener('pointerdown', (event) => {
        event.preventDefault();
      });
      button.addEventListener('click', () => {
        chooseStationSuggestion(stop);
      });
      stationSuggestions.append(button);
    });
  }

  stationSuggestions.hidden = false;
  input.setAttribute('aria-expanded', 'true');
  input.removeAttribute('aria-activedescendant');
  positionStationSuggestions(input);
}

function openStationSuggestions(input) {
  if (!state.data) {
    return;
  }
  renderStationSuggestions(input);
}

function hideStationSuggestions() {
  const input = state.activeSuggestionInput;
  if (input) {
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
  }
  state.activeSuggestionInput = null;
  state.activeSuggestionIndex = -1;
  stationSuggestions.hidden = true;
  stationSuggestions.replaceChildren();
}

function chooseStationSuggestion(stop) {
  const input = state.activeSuggestionInput;
  if (!input || !stop) {
    return;
  }
  input.value = displayLabel(stop.lbl);
  hideStationSuggestions();

  if (input === searchInput) {
    refreshSearch();
    jumpToSearchResult();
    return;
  }

  clearRouteStateForInput();
  state.preferredRouteInput = input === routeStartInput
    ? routeEndInput
    : routeStartInput;
  input.focus();
}

function positionStationSuggestions(input = state.activeSuggestionInput) {
  if (!input || stationSuggestions.hidden) {
    return;
  }
  const rect = input.getBoundingClientRect();
  const viewportWidth = window.visualViewport?.width
    || document.documentElement.clientWidth;
  const viewportHeight = window.visualViewport?.height
    || document.documentElement.clientHeight;
  const margin = 8;
  const width = Math.max(220, rect.width);
  const availableBelow = viewportHeight - rect.bottom - margin;
  const availableAbove = rect.top - margin;
  const panelHeight = Math.min(
    stationSuggestions.scrollHeight,
    Math.max(120, Math.max(availableBelow, availableAbove)),
  );
  const openAbove = availableBelow < 160 && availableAbove > availableBelow;
  const left = clamp(
    rect.left,
    margin,
    Math.max(margin, viewportWidth - width - margin),
  );
  const top = openAbove
    ? Math.max(margin, rect.top - panelHeight - 4)
    : Math.min(
      viewportHeight - panelHeight - margin,
      rect.bottom + 4,
    );
  stationSuggestions.style.left = `${left}px`;
  stationSuggestions.style.top = `${Math.max(margin, top)}px`;
  stationSuggestions.style.width = `${Math.min(
    width,
    viewportWidth - (margin * 2),
  )}px`;
  stationSuggestions.style.maxHeight = `${Math.max(120, panelHeight)}px`;
}

function moveStationSuggestion(delta) {
  const buttons = [...stationSuggestions.querySelectorAll(
    '.station-suggestion',
  )];
  if (!buttons.length) {
    return false;
  }
  state.activeSuggestionIndex = (
    state.activeSuggestionIndex + delta + buttons.length
  ) % buttons.length;
  buttons.forEach((button, index) => {
    const active = index === state.activeSuggestionIndex;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  const active = buttons[state.activeSuggestionIndex];
  state.activeSuggestionInput?.setAttribute(
    'aria-activedescendant',
    active.id,
  );
  active.scrollIntoView({ block: 'nearest' });
  return true;
}

function chooseActiveStationSuggestion() {
  const buttons = [...stationSuggestions.querySelectorAll(
    '.station-suggestion',
  )];
  const active = buttons[state.activeSuggestionIndex];
  if (!active) {
    return false;
  }
  const stop = state.stopsByVar.get(active.dataset.stopVar);
  if (!stop) {
    return false;
  }
  chooseStationSuggestion(stop);
  return true;
}

function handleStationSuggestionKeydown(
  event,
  input,
  fallbackEnter,
) {
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    if (stationSuggestions.hidden) {
      openStationSuggestions(input);
    }
    moveStationSuggestion(1);
    return;
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault();
    if (stationSuggestions.hidden) {
      openStationSuggestions(input);
    }
    moveStationSuggestion(-1);
    return;
  }
  if (event.key === 'Escape') {
    hideStationSuggestions();
    return;
  }
  if (event.key === 'Tab') {
    hideStationSuggestions();
    return;
  }
  if (event.key === 'Enter') {
    if (!stationSuggestions.hidden && chooseActiveStationSuggestion()) {
      event.preventDefault();
      return;
    }
    hideStationSuggestions();
    fallbackEnter();
  }
}
'''

    app = replace_between(
        app,
        "function populateStationSuggestions() {",
        "function pointFromSpec(",
        suggestion_helpers,
        "custom scrollable station suggestions",
    )

    bind_events = r'''function bindEvents() {
  window.addEventListener('resize', scheduleViewportSync);
  window.visualViewport?.addEventListener(
    'resize',
    scheduleViewportSync,
  );
  window.addEventListener('orientationchange', () => {
    scheduleViewportSync();
    window.setTimeout(scheduleViewportSync, 240);
  });

  if (window.ResizeObserver && mapStage) {
    const observer = new ResizeObserver(() => {
      scheduleViewportSync();
    });
    observer.observe(mapStage);
  }

  window.addEventListener('scroll', () => {
    positionStationSuggestions();
  }, { passive: true });

  sidePanel?.addEventListener('scroll', () => {
    positionStationSuggestions();
  }, { passive: true });

  canvas.addEventListener('pointerdown', (event) => {
    hideStationSuggestions();
    canvas.setPointerCapture(event.pointerId);
    state.dragging = true;
    state.dragDistance = 0;
    state.lastPointer = { x: event.clientX, y: event.clientY };
    canvas.classList.add('dragging');
  });

  canvas.addEventListener('pointermove', (event) => {
    if (state.dragging && state.lastPointer) {
      const dx = event.clientX - state.lastPointer.x;
      const dy = event.clientY - state.lastPointer.y;
      panBy(dx, dy);
      state.dragDistance += Math.abs(dx) + Math.abs(dy);
      state.lastPointer = { x: event.clientX, y: event.clientY };
      requestRender();
      return;
    }
    updateHover(event);
  });

  canvas.addEventListener('pointerup', (event) => {
    if (canvas.hasPointerCapture(event.pointerId)) {
      canvas.releasePointerCapture(event.pointerId);
    }
    state.dragging = false;
    state.lastPointer = null;
    canvas.classList.remove('dragging');
    if (state.dragDistance <= 4) {
      const point = canvasPoint(event);
      const stop = findStopAt(point.x, point.y);
      if (stop) {
        selectStop(stop, { updateRouteStart: true });
      } else {
        const edge = findExtraEdgeAt(point.x, point.y);
        if (edge) {
          selectPathEdge(edge);
        }
      }
    }
  });

  canvas.addEventListener('pointerleave', () => {
    state.hoverStop = null;
    tooltip.hidden = true;
    render();
  });

  canvas.addEventListener('wheel', (event) => {
    event.preventDefault();
    event.stopPropagation();
    const point = canvasPoint(event);
    zoomAtScreenPoint(point.x, point.y, wheelNextZoom(event));
  }, { passive: false });

  document.addEventListener('pointerdown', (event) => {
    const target = event.target;
    if (
      target instanceof Node
      && (
        stationSuggestions.contains(target)
        || target === searchInput
        || target === routeStartInput
        || target === routeEndInput
      )
    ) {
      return;
    }
    hideStationSuggestions();

    if (infoPopup.hidden || infoPopup.contains(target)) {
      return;
    }
    if (
      target instanceof HTMLElement
      && target.closest('.side-panel')
    ) {
      return;
    }
    state.selectedStop = null;
    state.selectedPathEdge = null;
    state.selectedSearchPoint = null;
    hidePopup();
    render();
  });
  document.addEventListener('keydown', handleHotkey);

  searchInput.addEventListener('input', () => {
    refreshSearch();
    renderStationSuggestions(searchInput);
  });
  searchInput.addEventListener('focus', () => {
    openStationSuggestions(searchInput);
  });
  searchInput.addEventListener('keydown', (event) => {
    handleStationSuggestionKeydown(
      event,
      searchInput,
      jumpToSearchResult,
    );
  });
  searchButton.addEventListener('click', () => {
    hideStationSuggestions();
    jumpToSearchResult();
  });

  for (const input of [routeStartInput, routeEndInput]) {
    input.addEventListener('input', () => {
      clearRouteStateForInput();
      renderStationSuggestions(input);
    });
    input.addEventListener('focus', () => {
      prepareRouteInput(input);
      openStationSuggestions(input);
    });
    input.addEventListener('pointerdown', () => {
      state.preferredRouteInput = input;
    });
    input.addEventListener('keydown', (event) => {
      handleStationSuggestionKeydown(
        event,
        input,
        planRoute,
      );
    });
  }

  routeButton.addEventListener('click', () => {
    hideStationSuggestions();
    planRoute();
  });
  swapRouteButton.addEventListener('click', swapRoute);
  clearRouteButton.addEventListener('click', clearRoute);

  resetViewButton.addEventListener('click', () => {
    resetView();
    render();
  });
  fitMapButton.addEventListener('click', fitRenderedMap);
  blackportButton.addEventListener('click', showBlackportView);
  copyLinkButton.addEventListener('click', copyCurrentLink);
  clearSelectionButton.addEventListener('click', clearSelection);
  mapZoomInButton?.addEventListener(
    'click',
    () => zoomAtViewportCenter(
      state.camera.zoom * CONSTANTS.zoomStep,
    ),
  );
  mapZoomOutButton?.addEventListener(
    'click',
    () => zoomAtViewportCenter(
      state.camera.zoom / CONSTANTS.zoomStep,
    ),
  );
  mapFitButton?.addEventListener('click', fitPrimaryView);

  for (const input of [
    showWorldMapInput,
    showLabelsInput,
    showSuggestedWalkingPathsInput,
  ]) {
    input.addEventListener('change', requestRender);
  }
}

function scheduleViewportSync() {
  if (state.resizeFrame !== null) {
    window.cancelAnimationFrame(state.resizeFrame);
  }
  state.resizeFrame = window.requestAnimationFrame(() => {
    state.resizeFrame = null;
    resizeCanvas({ refitRoute: true });
    positionStationSuggestions();
    requestRender();
  });
}
'''

    app = replace_between(
        app,
        "function bindEvents() {",
        "function resizeCanvas() {",
        bind_events,
        "responsive event handling",
    )

    resize_canvas = r'''function resizeCanvas(options = {}) {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.round(rect.width * pixelRatio));
  const height = Math.max(1, Math.round(rect.height * pixelRatio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  updateCameraViewport(rect.width, rect.height);
  if (options.refitRoute && state.currentRoute) {
    fitCurrentRoute({ render: false });
  }
}
'''

    app = replace_between(
        app,
        "function resizeCanvas() {",
        "function updateCameraViewport(",
        resize_canvas,
        "responsive canvas resizing",
    )

    station_rendering = r'''function drawStations() {
  ctx.save();
  const labelFontSize = labelFontSizeForZoom();
  ctx.font = `${labelFontSize}px Helvetica, Arial, sans-serif`;
  ctx.textBaseline = 'alphabetic';
  const visibleStops = state.data.stops.filter(
    (stop) => stopHasVisibleLine(stop),
  );
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
  const lineShields = stationLineShieldPlacements(stationRects);
  const shieldRects = lineShields.map((shield) => shield.rect);
  const labelLayout = showLabelsInput.checked
    ? placeStationLabels(
      stationRects,
      labelFontSize,
      shieldRects,
    )
    : new Map();

  for (const item of stationRects) {
    drawStationMarker(item.stop, item.point);
  }
  for (const shield of lineShields) {
    drawLineCircle(
      shield.point,
      shield.lineName,
      CONSTANTS.lineMarkerRadius,
    );
  }
  for (const item of stationRects) {
    if (!showLabelsInput.checked) {
      continue;
    }
    const label = labelLayout.get(item.stop.var);
    if (!label) {
      continue;
    }
    drawRotatedLabel(
      label.text,
      label.x,
      label.y,
      stationLabelColor(item.stop),
      labelFontSize,
      stationLabelPriority(item.stop) <= 4,
    );
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
  ctx.lineWidth = phosphagos ? 4 : 2.5;
  ctx.stroke();

  if (junction && !phosphagos) {
    drawDiamondPath(point, Math.max(4, size - 4));
    ctx.strokeStyle = CONSTANTS.stationOutline;
    ctx.lineWidth = 1.75;
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

function stationLineShieldPlacements(stationItems) {
  const occupied = stationItems.map(
    (item) => expandRect(item.rect, 4),
  );
  const placements = [];
  const ordered = [...stationItems].sort((first, second) => (
    stationLabelPriority(first.stop)
      - stationLabelPriority(second.stop)
  ));

  for (const item of ordered) {
    for (const lineName of markerLineNamesForStop(item.stop)) {
      const candidates = lineShieldCandidates(
        item.stop,
        lineName,
      );
      let best = null;
      for (const candidate of candidates) {
        const radius = CONSTANTS.lineMarkerRadius;
        const rect = {
          minX: candidate.point.x - radius - 2,
          maxX: candidate.point.x + radius + 2,
          minY: candidate.point.y - radius - 2,
          maxY: candidate.point.y + radius + 2,
        };
        const score = lineShieldPlacementScore(
          rect,
          occupied,
          candidate.preference,
        );
        if (!best || score < best.score) {
          best = {
            ...candidate,
            rect,
            score,
            lineName,
          };
        }
        if (score === candidate.preference) {
          break;
        }
      }
      if (!best) {
        continue;
      }
      placements.push(best);
      occupied.push(expandRect(best.rect, 3));
    }
  }
  return placements;
}

function lineShieldCandidates(stop, lineName) {
  const segments = state.lineSegments.filter((segment) => (
    segment.lineName === lineName
    && (
      segment.startVar === stop.var
      || segment.endVar === stop.var
    )
  ));
  const candidates = [];
  for (const segment of segments) {
    const points = segment.startVar === stop.var
      ? segment.points
      : [...segment.points].reverse();
    const screenPoints = points.map(plotToCanvas);
    CONSTANTS.lineMarkerDistances.forEach(
      (distance, distanceIndex) => {
        const point = pointAtPolylineScreenDistance(
          screenPoints,
          distance,
        );
        if (!point) {
          return;
        }
        candidates.push({
          point,
          preference: distanceIndex,
        });
      },
    );
  }
  return candidates;
}

function pointAtPolylineScreenDistance(points, targetDistance) {
  if (points.length < 2) {
    return null;
  }
  let traversed = 0;
  for (let index = 0; index < points.length - 1; index += 1) {
    const first = points[index];
    const second = points[index + 1];
    const dx = second.x - first.x;
    const dy = second.y - first.y;
    const length = Math.hypot(dx, dy);
    if (length <= 0) {
      continue;
    }
    if (traversed + length >= targetDistance) {
      const ratio = (targetDistance - traversed) / length;
      return {
        x: first.x + (dx * ratio),
        y: first.y + (dy * ratio),
      };
    }
    traversed += length;
  }
  return points[points.length - 1];
}

function lineShieldPlacementScore(rect, occupied, preference) {
  let score = preference;
  const viewport = {
    minX: 4,
    minY: 4,
    maxX: state.camera.viewportWidth - 4,
    maxY: state.camera.viewportHeight - 4,
  };
  if (!rectContainsRect(viewport, rect)) {
    score += 1000000;
  }
  for (const other of occupied) {
    if (rectsOverlap(rect, other)) {
      score += 100000 + rectOverlapArea(rect, other);
    }
  }
  return score;
}

function drawLineCircle(point, lineName, radius) {
  const color = colorForLine(lineName);
  ctx.save();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = backgroundContrastColorAt(point, radius);
  ctx.lineWidth = 2.5;
  ctx.stroke();
  ctx.fillStyle = contrastingTextColor(color);
  ctx.font = `900 ${Math.max(10, radius + 2)}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(lineName, point.x, point.y + 0.5);
  ctx.restore();
}

function backgroundContrastColorAt(point, radius) {
  const pixelRatio = window.devicePixelRatio || 1;
  const sampleRadius = radius + 6;
  const offsets = [
    [-sampleRadius, 0],
    [sampleRadius, 0],
    [0, -sampleRadius],
    [0, sampleRadius],
    [-sampleRadius * 0.7, -sampleRadius * 0.7],
    [sampleRadius * 0.7, -sampleRadius * 0.7],
    [-sampleRadius * 0.7, sampleRadius * 0.7],
    [sampleRadius * 0.7, sampleRadius * 0.7],
  ];
  let red = 0;
  let green = 0;
  let blue = 0;
  let count = 0;
  try {
    for (const [dx, dy] of offsets) {
      const x = clamp(
        Math.round((point.x + dx) * pixelRatio),
        0,
        canvas.width - 1,
      );
      const y = clamp(
        Math.round((point.y + dy) * pixelRatio),
        0,
        canvas.height - 1,
      );
      const data = ctx.getImageData(x, y, 1, 1).data;
      red += data[0];
      green += data[1];
      blue += data[2];
      count += 1;
    }
  } catch (_error) {
    return CONSTANTS.stationDarkOutline;
  }
  if (!count) {
    return CONSTANTS.stationDarkOutline;
  }
  const luminance = (
    ((red / count) * 0.299)
    + ((green / count) * 0.587)
    + ((blue / count) * 0.114)
  ) / 255;
  return luminance > 0.53
    ? CONSTANTS.stationDarkOutline
    : CONSTANTS.stationOutline;
}
'''

    app = replace_between(
        app,
        "function drawStations() {",
        "function placeStationLabels(",
        station_rendering,
        "line shields and larger station diamonds",
    )

    app = replace_once(
        app,
        "function placeStationLabels(stationItems, fontSize) {",
        '''function placeStationLabels(
  stationItems,
  fontSize,
  extraOccupiedRects = [],
) {''',
        "label layout shield awareness",
    )

    app = replace_once(
        app,
        "  const occupiedRects = stationItems.map((item) => item.rect);",
        '''  const occupiedRects = [
    ...stationItems.map((item) => item.rect),
    ...extraOccupiedRects,
  ];''',
        "label occupancy for line shields",
    )

    hover_block = r'''function updateHover(event) {
  const stop = findStopAt(event.offsetX, event.offsetY);
  state.hoverStop = stop;
  if (!stop) {
    tooltip.hidden = true;
    return;
  }
  const lines = linesForStop(stop);
  const abbr = stationAbbreviation(stop);
  const abbrText = abbr ? ` · ${escapeHtml(abbr)}` : '';
  tooltip.innerHTML = `<strong>${escapeHtml(displayLabel(stop.lbl))}${abbrText}</strong><span>${stop.x}, ${stop.y} · ${lines.join(', ')}</span>`;
  tooltip.hidden = false;
  positionOverlayNearPoint(
    tooltip,
    { x: event.offsetX, y: event.offsetY },
    { preferAbove: false },
  );
}

function positionOverlayNearPoint(
  element,
  point,
  options = {},
) {
  const margin = CONSTANTS.overlayMargin;
  const gap = 12;
  const box = element.getBoundingClientRect();
  const width = Math.min(
    box.width,
    state.camera.viewportWidth - (margin * 2),
  );
  const height = Math.min(
    box.height,
    state.camera.viewportHeight - (margin * 2),
  );
  const horizontal = [
    point.x + gap,
    point.x - gap - width,
  ];
  const vertical = options.preferAbove
    ? [point.y - gap - height, point.y + gap]
    : [point.y + gap, point.y - gap - height];

  let left = horizontal[0];
  let top = vertical[0];
  let found = false;
  for (const candidateTop of vertical) {
    for (const candidateLeft of horizontal) {
      if (
        candidateLeft >= margin
        && candidateLeft + width
          <= state.camera.viewportWidth - margin
        && candidateTop >= margin
        && candidateTop + height
          <= state.camera.viewportHeight - margin
      ) {
        left = candidateLeft;
        top = candidateTop;
        found = true;
        break;
      }
    }
    if (found) {
      break;
    }
  }

  left = clamp(
    left,
    margin,
    Math.max(
      margin,
      state.camera.viewportWidth - width - margin,
    ),
  );
  top = clamp(
    top,
    margin,
    Math.max(
      margin,
      state.camera.viewportHeight - height - margin,
    ),
  );
  element.style.left = `${left}px`;
  element.style.top = `${top}px`;
}
'''

    app = replace_between(
        app,
        "function updateHover(event) {",
        "function findStopAt(",
        hover_block,
        "viewport-safe hover popup",
    )

    popup_block = r'''function positionInfoPopup() {
  if (
    (
      !state.selectedStop
      && !state.selectedPathEdge
      && !state.selectedSearchPoint
    )
    || infoPopup.hidden
  ) {
    return;
  }
  const point = state.selectedStop
    ? plotToCanvas(stationPlotPoint(state.selectedStop))
    : state.selectedPathEdge
      ? selectedPathEdgeAnchorPoint(state.selectedPathEdge)
      : plotToCanvas(state.selectedSearchPoint.point);
  positionOverlayNearPoint(
    infoPopup,
    point,
    { preferAbove: true },
  );
}
'''

    app = replace_between(
        app,
        "function positionInfoPopup() {",
        "function hidePopup() {",
        popup_block,
        "viewport-safe station popup",
    )

    app = replace_once(
        app,
        '''function stationMarkerSize(stop) {
  if (isPhosphagos(stop)) {
    return 11;
  }
  if (isJunctionStop(stop)) {
    return 9;
  }
  return 7;
}''',
        '''function stationMarkerSize(stop) {
  if (isPhosphagos(stop)) {
    return 14;
  }
  if (isJunctionStop(stop)) {
    return 12;
  }
  return 9;
}''',
        "larger diamond sizes",
    )

    required = [
        "function stationLineShieldPlacements(",
        "function backgroundContrastColorAt(",
        "function renderStationSuggestions(",
        "function scheduleViewportSync(",
        "function positionOverlayNearPoint(",
    ]
    missing = [item for item in required if item not in app]
    if missing:
        raise RuntimeError(
            f"Transformed app.js is missing required features: {missing}"
        )
    return app


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
        "index": docs / "index.html",
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
        atomic_write(paths["app"], transformed_app)
        atomic_write(paths["styles"], STYLES_CSS.rstrip() + "\n")
        atomic_write(paths["index"], INDEX_HTML.rstrip() + "\n")

        syntax_result = validate_javascript(paths["app"])

        print("Updated:")
        for path in paths.values():
            print(f"- {path.relative_to(repo)}")
        print(syntax_result)
        print()
        print("No commit or push was performed.")
        print(
            "Review with:\n"
            "  git diff -- docs/app.js docs/styles.css docs/index.html"
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
