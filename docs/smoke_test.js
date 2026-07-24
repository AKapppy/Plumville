const fs = require('node:fs');
const path = require('node:path');

const docsDir = __dirname;
const repoRoot = path.resolve(docsDir, '..');
const indexHtml = fs.readFileSync(path.join(docsDir, 'index.html'), 'utf8');
const appJs = fs.readFileSync(path.join(docsDir, 'app.js'), 'utf8');
const stylesCss = fs.readFileSync(path.join(docsDir, 'styles.css'), 'utf8');
const network = JSON.parse(fs.readFileSync(path.join(docsDir, 'metro_network.json'), 'utf8'));
const terrainMetadata = JSON.parse(fs.readFileSync(path.join(docsDir, 'assets', 'blackport_topdown.render.json'), 'utf8'));
const terrainMetadataText = fs.readFileSync(path.join(docsDir, 'assets', 'blackport_topdown.render.json'), 'utf8');
const terrainPng = fs.readFileSync(path.join(docsDir, 'assets', 'blackport_topdown.png'));

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function pngDimensions(buffer) {
  const signature = buffer.subarray(0, 8).toString('hex');
  assert(signature === '89504e470d0a1a0a', 'Terrain image is not a PNG.');
  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20),
  };
}

assert(indexHtml.includes('id="metroCanvas"'), 'Viewer canvas is missing from index.html.');
assert(indexHtml.includes('id="fitMapButton"'), 'Fit rendered map button is missing from index.html.');
assert(indexHtml.includes('id="mapZoomInButton"'), 'In-map zoom-in control is missing from index.html.');
assert(indexHtml.includes('id="mapZoomOutButton"'), 'In-map zoom-out control is missing from index.html.');
assert(indexHtml.includes('id="mapFitButton"'), 'In-map fit control is missing from index.html.');
assert(indexHtml.includes('id="copyLinkButton"'), 'Copy-link action is missing from index.html.');
assert(appJs.includes("fetch('metro_network.json'"), 'app.js no longer fetches metro_network.json.');
assert(appJs.includes('new Image()'), 'app.js no longer loads the terrain image.');
assert(appJs.includes('function fitRenderedMap'), 'app.js is missing fitRenderedMap().');
assert(appJs.includes('function screenToWorld'), 'app.js is missing the shared camera screenToWorld() helper.');
assert(appJs.includes('function worldToScreen'), 'app.js is missing the shared camera worldToScreen() helper.');
assert(appJs.includes('function zoomAtScreenPoint'), 'app.js is missing cursor-centered zoomAtScreenPoint().');
assert(appJs.includes('function clampCamera'), 'app.js is missing camera clamping.');
assert(appJs.includes('function drawExtraEdges'), 'app.js is missing extra path-edge rendering.');
assert(!indexHtml.includes('railway finishing'), 'Retired railway finishing text is still visible in index.html.');
assert(indexHtml.includes('id="routeButton"'), 'Directions route button is missing from index.html.');
assert(indexHtml.includes('<details class="collapsible-section" open>'), 'Directions should start expanded in the public viewer.');
assert(indexHtml.includes('id="stationSuggestions"'), 'Directions station suggestions are missing from index.html.');
assert(indexHtml.includes('Station label or code'), 'Directions should clarify station-only route inputs.');
assert(indexHtml.includes('id="showSuggestedWalkingPathsInput"'), 'Suggested walking path view toggle is missing from index.html.');
assert(indexHtml.includes('id="lineLegend"'), 'Line visibility legend is missing from index.html.');
assert(indexHtml.includes('id="searchInput"'), 'Station search input is missing from index.html.');
assert(indexHtml.indexOf('id="searchInput"') < indexHtml.indexOf('id="showWorldMapInput"'), 'Search should sit above the view checklist.');
assert(appJs.includes('function routeInputTargetForStop'), 'Directions station selection helper is missing from app.js.');
assert(appJs.includes('function populateLineLegend'), 'app.js is missing line legend/toggle population.');
assert(appJs.includes('planRoute({ syncUrl: false })'), 'Line toggles no longer replan active routes.');
assert(appJs.includes('linesForStop(stop).filter((lineName) => state.visibleLines.has(lineName))'), 'Route graph no longer respects visible line toggles.');
assert(appJs.includes('function applyInitialUrlState'), 'app.js is missing shareable URL restoration.');
assert(appJs.includes('function replaceShareParams'), 'app.js is missing shareable URL updates.');
assert(appJs.includes('function copyCurrentLink'), 'app.js is missing copy-link behavior.');
assert(appJs.includes('function visibleLineShareParam'), 'app.js is missing shareable visible-line state.');
assert(appJs.includes("params.get('lines')"), 'app.js no longer restores visible lines from URL params.');
assert(appJs.includes("replaceShareParams({ from: routeStartInput.value, to: routeEndInput.value, ...lineShareParams() })"), 'Route planning no longer updates shareable route URL params.');
assert(appJs.includes('function drawSuggestedWalkingPaths'), 'app.js is missing suggested walking path rendering.');
assert(appJs.includes('function visibleUnderlaySourceBox'), 'app.js is missing desktop-style underlay cropping.');
assert(appJs.includes('function underlayDrawIsUpscaled'), 'app.js is missing desktop-style sharp underlay sampling.');
assert(appJs.includes('function drawTerrainBoundaryCompletionEdges'), 'app.js is missing terrain boundary completion strokes.');
assert(appJs.includes('function coordinateQueryPoint'), 'app.js is missing coordinate search parsing.');
assert(appJs.includes('function searchPointDistanceRows'), 'app.js is missing along-track point distance reporting.');
assert(appJs.includes('minecartSpeedMps: 8'), 'app.js is missing public minecart speed configuration.');
assert(appJs.includes('function formatDistanceAndTime'), 'app.js is missing distance/time route formatting.');
assert(appJs.includes('formatDistanceAndTime(route.totalDistance)'), 'Route summary no longer shows minecart travel time.');
assert(appJs.includes('function segmentConstructionStatus'), 'app.js is missing explicit public segment construction status.');
assert(appJs.includes("constructionStatus = 'open_checklist_incomplete'"), 'Public segment status no longer separates routing-open segments from station checklist completion.');
assert(appJs.includes('Railway checklist complete'), 'Station popups no longer show railway checklist status.');
assert(appJs.includes('function routeConstructionWarningLines'), 'Route instructions no longer distinguish construction warning categories.');
assert(appJs.includes('open track with unfinished station checklist work'), 'Route instructions no longer explain open checklist-incomplete track.');
assert(appJs.includes('function lineBadgesHtml'), 'Station popups no longer render line badges.');
assert(stylesCss.includes('.line-badge'), 'Line badge styling is missing.');
assert(appJs.includes('Distance: ${formatDistanceAndTime(distance)}'), 'Path-edge popups no longer show minecart travel time.');
assert(appJs.includes('function lineLegendStatusText'), 'Line legend no longer exposes construction status text.');
assert(appJs.includes('function showPublicLoadError'), 'Public load errors no longer use a visitor-friendly handler.');
assert(appJs.includes('console.error(error)'), 'Public load error details are no longer kept in the browser console.');
assert(appJs.includes('function requestRender'), 'Public viewer no longer coalesces repeated render requests.');
assert(appJs.includes('window.requestAnimationFrame(render)'), 'Public viewer render scheduler no longer uses animation frames.');
assert(appJs.includes('function formatInterchangeCount'), 'Route summaries no longer format interchange counts cleanly.');
assert(!appJs.includes('interchange(s)'), 'Route summaries still use awkward interchange(s) text.');
assert(!appJs.includes('No route exists for those endpoints'), 'Public route failure still uses technical endpoint wording.');
assert(appJs.includes('function placeStationLabels'), 'app.js is missing automatic station label placement.');
assert(!appJs.includes('stopRouteInputPropagation'), 'Route inputs still intercept native pointer/click events.');
assert(!indexHtml.includes('Checklist'), 'Maintenance checklist is visible in the public viewer.');
assert(!indexHtml.includes('showAlignmentInput'), 'Alignment maintenance overlay control is visible in the public viewer.');
assert(!indexHtml.includes('showFrontierInput'), 'Frontier maintenance overlay control is visible in the public viewer.');
assert(!indexHtml.includes('useFlyingInput'), 'Flying route control is visible in the public viewer.');
assert(!indexHtml.includes('readOnlyNotice'), 'Read-only/admin notice is visible in the public viewer.');
assert(!appJs.includes('function drawAlignmentReminders'), 'Alignment maintenance renderer is bundled in the public viewer.');
assert(!appJs.includes('function drawFrontierHighlights'), 'Frontier maintenance renderer is bundled in the public viewer.');
for (const forbiddenPattern of [
  /\/Users\//,
  /Library\/Application Support/,
  /worldgen\/cache/,
  /worldgen\/output/,
  /headless_chunk_packets/,
  /bedrock-data/,
]) {
  assert(!terrainMetadataText.match(forbiddenPattern), `Public terrain metadata contains private path text: ${forbiddenPattern}`);
}
assert(Array.isArray(network.stops) && network.stops.length > 0, 'metro_network.json has no stops.');
assert(network.line_stop_vars && Object.keys(network.line_stop_vars).length > 0, 'metro_network.json has no line data.');
assert(Array.isArray(network.suggested_walking_segments), 'metro_network.json has no suggested walking segment data.');
assert(network.suggested_walking_segments.length > 0, 'Suggested walking segment data is empty.');
assert(!fs.existsSync(path.join(repoRoot, 'metro_network.json')), 'Duplicate root metro_network.json should not exist; docs/metro_network.json is canonical.');

const dimensions = pngDimensions(terrainPng);
assert(dimensions.width === terrainMetadata.width, `PNG width ${dimensions.width} does not match metadata width ${terrainMetadata.width}.`);
assert(dimensions.height === terrainMetadata.height, `PNG height ${dimensions.height} does not match metadata height ${terrainMetadata.height}.`);
assert(
  terrainMetadata.width === terrainMetadata.max_x - terrainMetadata.min_x + 1,
  'Terrain metadata width no longer matches min_x..max_x bounds.',
);
assert(
  terrainMetadata.height === terrainMetadata.max_z - terrainMetadata.min_z + 1,
  'Terrain metadata height no longer matches min_z..max_z bounds.',
);

console.log(`OK: docs viewer assets load from ${path.relative(repoRoot, docsDir)}, and terrain bounds match the PNG.`);
