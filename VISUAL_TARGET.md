PLUMVILLE DESKTOP MMCP VISUAL TARGET

Purpose:
Translate the three mockup images in data/mockups/ into an implementable
desktop specification.

======================================================================
1. VISUAL PRINCIPLE
======================================================================

The target is a modern control panel for a Minecraft transit system.

It should feel:

- deliberate;
- dense but calm;
- technical without looking like developer tooling;
- Minecraft-influenced without using novelty textures everywhere;
- map-first;
- clearly divided into workspace regions.

It should not feel like:

- one endlessly scrolling sidebar;
- a stock Tkinter form;
- a collection of floating utility dialogs;
- a generic rounded mobile app enlarged for desktop;
- a debug dashboard.

======================================================================
2. WORKSPACE GEOMETRY
======================================================================

Approximate desktop target:

- top application bar: 52–60 px
- left mode rail: 72–92 px
- secondary mode panel: 280–330 px
- center map: flexible and dominant
- right inspector: 340–390 px
- optional status strip: 26–32 px

Use these as design guidance, not rigid pixel requirements.

Minimum usable window should remain practical around 1180 x 720.

At narrower widths:

1. inspector may collapse;
2. secondary panel may narrow;
3. mode rail remains visible;
4. map must never collapse to an unusable sliver.

======================================================================
3. TOP APPLICATION BAR
======================================================================

Content:

- Plumville / Metro Control identity
- current mode name
- concise world/network status
- selected route status when relevant
- compact global actions
- optional completion/status indicators

Appearance:

- near-black background
- subtle lower border
- mono/pixel accent for the product name
- modern body text elsewhere
- no oversized title
- no full-width gradient

======================================================================
4. LEFT MODE RAIL
======================================================================

Modes:

- Explore
- Directions
- Construction
- Edit
- World
- Advanced

Behavior:

- always visible;
- one active mode;
- active mode uses diamond-blue focus;
- mode labels or short icons remain understandable;
- no vertical scrolling at normal desktop height;
- All may remain as a utility/debug option, but should not be the primary
  polished experience.

Appearance:

- compact block-like buttons;
- tiny or zero corner radius;
- clear active inset/edge;
- mono/pixel label accents;
- tooltips only when labels are abbreviated.

======================================================================
5. SECONDARY MODE PANEL
======================================================================

Explore:

- search
- visibility/filter shortcuts
- priority summary
- selection guidance

Directions:

- From / To
- Route / Swap / Clear
- route options
- route summary
- Fit Route
- expandable steps

Construction:

- checklist summary
- line/station progress
- priority work
- construction filters

Edit:

- add station
- add point of interest
- path and line editing tools
- current edit context

World:

- terrain visibility
- render status
- export
- completed-worldgen status
- generation controls only when needed

Advanced:

- unsupported/experimental warning
- path detection
- diagnostics and maintenance tools

The secondary panel should contain only the active workflow, not all sections.

======================================================================
6. CENTER MAP
======================================================================

The map remains the main surface.

Required:

- terrain underlay
- open/planned line grammar
- station diamonds
- line shields
- selected focus ring
- route highlight
- overlays
- temporary hover tooltip

Avoid:

- persistent station details floating over the map;
- oversized controls covering map content;
- control panels that shrink the map excessively.

======================================================================
7. RIGHT DOCKED INSPECTOR
======================================================================

Empty state:

- large muted station diamond
- “Select a station”
- one sentence describing selection

Selected header:

- station diamond
- station name
- abbreviation chip
- coordinates
- status chip
- line circles

Tabs:

- Overview
- Construction
- Lines
- Signs
- Actions

Overview:

- open/planned status
- railway checklist summary
- connected status
- chimes/signage summary
- key quick facts

Construction:

- façade
- station
- entrances
- walking paths
- connected
- progress and missing work

Lines:

- current line memberships
- segment status
- add/switch/remove workflows

Signs:

- chimes
- directions
- station signage

Actions:

- edit station
- move station
- alignments
- path actions
- danger area

The inspector should replace the persistent selected-station popup.

======================================================================
8. COMPONENT LANGUAGE
======================================================================

Colors:

- background: near-black
- panels: charcoal
- raised controls: slightly lighter charcoal
- text: warm white
- muted text: desaturated gray-green
- success: emerald
- warning/landmark: gold
- error/destructive: redstone
- focus/selection: diamond blue
- line identity: configured metro colors

Geometry:

- crisp rectangles
- 0–3 px corner radii
- 1 px borders
- restrained inset/raised edges
- no pill buttons except circular line badges

Typography:

- modern body font for forms and instructions
- mono/pixel-inspired font for headings, coordinates, abbreviations, and
  compact status labels
- never use pixel typography for paragraphs

Spacing:

- 4 px base
- 8 px normal gap
- 12–16 px panel padding
- 20–24 px major section separation

======================================================================
9. MAP SYMBOL GRAMMAR
======================================================================

- circle = line
- diamond = station
- larger/double diamond = junction
- terminal remains diamond-first
- Mt. Phosphagos = large gold/purple home diamond
- diamond blue ring = selected
- solid line = open
- dotted/dashed line = planned or unfinished

Keep marker sizes in screen space.

======================================================================
10. DEFINITION OF VISUAL PARITY
======================================================================

The desktop visual phase is successful when:

- a screenshot is immediately recognizable as the same design family as the
  mockups;
- the workspace regions match the mockup hierarchy;
- the map dominates;
- station details live in the inspector;
- mode changes feel like changing workspaces;
- controls look intentionally designed rather than recursively recolored;
- all existing functionality remains available;
- no private/public boundary is weakened.
