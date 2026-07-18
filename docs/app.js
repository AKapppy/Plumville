const canvas = document.querySelector('#metroCanvas');
const ctx = canvas.getContext('2d');
const tooltip = document.querySelector('#tooltip');
const infoPopup = document.querySelector('#infoPopup');
const summaryText = document.querySelector('#summaryText');
const searchInput = document.querySelector('#searchInput');
const searchButton = document.querySelector('#searchButton');
const searchStatus = document.querySelector('#searchStatus');
const routeStartInput = document.querySelector('#routeStartInput');
const routeEndInput = document.querySelector('#routeEndInput');
const routeButton = document.querySelector('#routeButton');
const swapRouteButton = document.querySelector('#swapRouteButton');
const clearRouteButton = document.querySelector('#clearRouteButton');
const routeSummary = document.querySelector('#routeSummary');
const routeSteps = document.querySelector('#routeSteps');
const stationSuggestions = document.querySelector('#stationSuggestions');
const resetViewButton = document.querySelector('#resetViewButton');
const fitMapButton = document.querySelector('#fitMapButton');
const blackportButton = document.querySelector('#blackportButton');
const clearSelectionButton = document.querySelector('#clearSelectionButton');
const mapZoomInButton = document.querySelector('#mapZoomInButton');
const mapZoomOutButton = document.querySelector('#mapZoomOutButton');
const mapFitButton = document.querySelector('#mapFitButton');
const showWorldMapInput = document.querySelector('#showWorldMapInput');
const showLabelsInput = document.querySelector('#showLabelsInput');
const showSuggestedWalkingPathsInput = document.querySelector('#showSuggestedWalkingPathsInput');

const CONSTANTS = {
  padding: 80,
  backgroundColor: '#050505',
  textColor: '#f7f7f7',
  gridColor: '#4b4b4b',
  intersectionColor: '#ffffff',
  defaultZoom: 1,
  zoomStep: 1.22,
  maxZoom: 20,
  wheelZoomSpeed: 0.0018,
  clampPadding: 64,
  labelAngle: -30 * Math.PI / 180,
  baseLabelFontSize: 13,
  stationRadius: 4,
  stationHitTolerance: 10,
  unconnectedDash: [10, 6],
  unconnectedWidth: 3,
  connectedWidth: 4,
  labelCasingColor: '#f2efe6',
  labelCasingWidth: 2,
  junctionLabelColor: '#050505',
  routeOutline: '#ffffff',
  routeOutlineWidth: 10,
  routeWidth: 6,
  connectorPathColor: '#f0f0f0',
  walkingPathColor: '#f7c7db',
  walkingPathDash: [8, 6],
  extraPathWidth: 4,
  worldMapAlpha: 0.745,
  terrainMetadataUrl: 'assets/blackport_topdown.render.json',
  blackportVar: 'P_ABCDE',
  blackportViewRadius: 2000,
};

const state = {
  data: null,
  stopsByVar: new Map(),
  stopLines: new Map(),
  lineSegments: [],
  visibleLines: new Set(),
  selectedStop: null,
  selectedPathEdge: null,
  hoverStop: null,
  searchMatches: [],
  preferredRouteInput: null,
  currentRoute: null,
  routeRequest: null,
  terrain: {
    image: null,
    loaded: false,
    bounds: null,
    stationBounds: null,
  },
  camera: {
    zoom: CONSTANTS.defaultZoom,
    translateX: 0,
    translateY: 0,
    minZoom: CONSTANTS.defaultZoom,
    maxZoom: CONSTANTS.maxZoom,
    viewportWidth: 1,
    viewportHeight: 1,
    worldWidth: 1,
    worldHeight: 1,
    initialized: false,
    userChangedView: false,
  },
  transform: null,
  plotBounds: null,
  dragging: false,
  dragDistance: 0,
  lastPointer: null,
};

init();

async function init() {
  try {
    loadTerrainImage();
    loadTerrainBounds();
    const response = await fetch('metro_network.json', { cache: 'no-cache' });
    if (!response.ok) {
      throw new Error(`Could not load metro_network.json: ${response.status}`);
    }
    hydrateNetwork(await response.json());
    bindEvents();
    resizeCanvas();
    resetView();
    refreshSearch();
    render();
  } catch (error) {
    summaryText.textContent = error.message;
  }
}

function hydrateNetwork(data) {
  state.data = data;
  state.stopsByVar = new Map(data.stops.map((stop) => [stop.var, stop]));
  state.stopLines = new Map(data.stops.map((stop) => [stop.var, []]));
  state.visibleLines = new Set(Object.keys(data.line_stop_vars).sort());
  state.lineSegments = [];

  for (const [lineName, stopVars] of Object.entries(data.line_stop_vars)) {
    for (const stopVar of stopVars) {
      state.stopLines.get(stopVar)?.push(lineName);
    }
    state.lineSegments.push(...segmentsForLine(lineName, stopVars, data.line_path_specs[lineName] || []));
  }

  const allPoints = [
    ...data.stops.map(stationPlotPoint),
    ...state.lineSegments.flatMap((segment) => segment.points),
    ...(data.path_nodes || []).map((node) => ({ x: node.x, y: -node.y })),
    ...(data.suggested_walking_segments || []).flatMap((segment) => suggestedWalkingSegmentPlotPoints(segment)),
  ];
  state.plotBounds = boundsForPoints(allPoints);
  state.terrain.stationBounds = terrainStationBounds(data.stops);
  populateStationSuggestions();
  summaryText.textContent = networkSummary();
}

function populateStationSuggestions() {
  if (!stationSuggestions) {
    return;
  }
  const seen = new Set();
  const values = [];
  for (const stop of state.data.stops) {
    for (const value of [displayLabel(stop.lbl), stop.var, stop.var.replace(/^P_/, '')]) {
      const normalized = normalizeIdentity(value);
      if (normalized && !seen.has(normalized)) {
        seen.add(normalized);
        values.push(value);
      }
    }
  }
  values.sort((first, second) => first.localeCompare(second, undefined, { numeric: true }));
  stationSuggestions.innerHTML = values
    .map((value) => `<option value="${escapeHtml(value)}"></option>`)
    .join('');
}

function pointFromSpec(spec) {
  const xStop = state.stopsByVar.get(spec.x_var);
  const yStop = state.stopsByVar.get(spec.y_var);
  if (!xStop || !yStop) {
    return null;
  }
  return {
    x: xStop.x + Number(spec.dx || 0),
    y: -yStop.y + Number(spec.dy || 0),
  };
}

function segmentsForLine(lineName, stopVars, specs) {
  const anchorIndexes = new Map();
  specs.forEach((spec, index) => {
    if (spec.x_var === spec.y_var && stopVars.includes(spec.x_var)) {
      anchorIndexes.set(spec.x_var, index);
    }
  });

  const segments = [];
  for (let index = 0; index < stopVars.length - 1; index += 1) {
    const startVar = stopVars[index];
    const endVar = stopVars[index + 1];
    const startIndex = anchorIndexes.get(startVar);
    const endIndex = anchorIndexes.get(endVar);
    if (startIndex === undefined || endIndex === undefined) {
      continue;
    }
    const first = Math.min(startIndex, endIndex);
    const last = Math.max(startIndex, endIndex);
    const points = specs.slice(first, last + 1).map(pointFromSpec).filter(Boolean);
    if (endIndex < startIndex) {
      points.reverse();
    }
    const startStop = state.stopsByVar.get(startVar);
    const endStop = state.stopsByVar.get(endVar);
    const connected = Boolean(startStop?.is_connected && endStop?.is_connected);
    segments.push({ lineName, startVar, endVar, points, connected });
  }
  return segments;
}

function bindEvents() {
  window.addEventListener('resize', () => {
    resizeCanvas();
    render();
  });

  canvas.addEventListener('pointerdown', (event) => {
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
      render();
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
    if (infoPopup.hidden || infoPopup.contains(event.target)) {
      return;
    }
    if (event.target instanceof HTMLElement && event.target.closest('.side-panel')) {
      return;
    }
    state.selectedStop = null;
    state.selectedPathEdge = null;
    hidePopup();
    render();
  });
  document.addEventListener('keydown', handleHotkey);

  searchInput.addEventListener('input', refreshSearch);
  searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      jumpToSearchResult();
    }
  });
  searchButton.addEventListener('click', jumpToSearchResult);

  routeStartInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      planRoute();
    }
  });
  routeEndInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      planRoute();
    }
  });
  for (const input of [routeStartInput, routeEndInput]) {
    input.addEventListener('input', clearRouteStateForInput);
    input.addEventListener('focus', () => prepareRouteInput(input));
    input.addEventListener('pointerdown', () => {
      state.preferredRouteInput = input;
    });
  }
  routeButton.addEventListener('click', planRoute);
  swapRouteButton.addEventListener('click', swapRoute);
  clearRouteButton.addEventListener('click', clearRoute);

  resetViewButton.addEventListener('click', () => {
    resetView();
    render();
  });
  fitMapButton.addEventListener('click', fitRenderedMap);
  blackportButton.addEventListener('click', showBlackportView);
  clearSelectionButton.addEventListener('click', clearSelection);
  mapZoomInButton?.addEventListener('click', () => zoomAtViewportCenter(state.camera.zoom * CONSTANTS.zoomStep));
  mapZoomOutButton?.addEventListener('click', () => zoomAtViewportCenter(state.camera.zoom / CONSTANTS.zoomStep));
  mapFitButton?.addEventListener('click', () => {
    fitToMap();
    render();
  });

  for (const input of [showWorldMapInput, showLabelsInput, showSuggestedWalkingPathsInput]) {
    input.addEventListener('change', render);
  }
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * pixelRatio));
  canvas.height = Math.max(1, Math.round(rect.height * pixelRatio));
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  updateCameraViewport(rect.width, rect.height);
}

function updateCameraViewport(width, height) {
  state.camera.viewportWidth = Math.max(1, width);
  state.camera.viewportHeight = Math.max(1, height);
  updateCameraWorld();
  if (!state.camera.initialized && cameraHasWorld()) {
    fitToMap();
    return;
  }
  if (!state.camera.userChangedView && cameraHasWorld()) {
    fitToMap();
    return;
  }
  clampCamera();
}

function resetView() {
  fitToMap();
  hidePopup();
}

function showBlackportView() {
  const blackport = state.stopsByVar.get(CONSTANTS.blackportVar);
  if (!blackport) {
    return;
  }
  const center = stationPlotPoint(blackport);
  setViewToPlotBounds({
    minX: center.x - CONSTANTS.blackportViewRadius,
    maxX: center.x + CONSTANTS.blackportViewRadius,
    minY: center.y - CONSTANTS.blackportViewRadius,
    maxY: center.y + CONSTANTS.blackportViewRadius,
  });
  render();
}

function fitRenderedMap() {
  const bounds = currentTerrainBounds();
  if (!bounds) {
    return;
  }
  setViewToPlotBounds({
    minX: bounds.minX,
    maxX: bounds.maxX,
    minY: -bounds.maxZ,
    maxY: -bounds.minZ,
  });
  render();
}

function setViewToPlotBounds(bounds) {
  if (!cameraHasWorld()) {
    return;
  }
  const first = plotToWorld({ x: bounds.minX, y: bounds.minY });
  const second = plotToWorld({ x: bounds.maxX, y: bounds.maxY });
  const worldBounds = normalizedWorldBounds(first, second);
  const spanX = Math.max(worldBounds.maxX - worldBounds.minX, 1);
  const spanY = Math.max(worldBounds.maxY - worldBounds.minY, 1);
  const availableWidth = Math.max(state.camera.viewportWidth - (CONSTANTS.padding * 2), 1);
  const availableHeight = Math.max(state.camera.viewportHeight - (CONSTANTS.padding * 2), 1);
  state.camera.zoom = clamp(
    Math.min(availableWidth / spanX, availableHeight / spanY),
    state.camera.minZoom,
    state.camera.maxZoom,
  );
  const worldCenter = {
    x: (bounds.minX + bounds.maxX) / 2,
    y: (bounds.minY + bounds.maxY) / 2,
  };
  const center = plotToWorld(worldCenter);
  state.camera.translateX = (state.camera.viewportWidth / 2) - (center.x * state.camera.zoom);
  state.camera.translateY = (state.camera.viewportHeight / 2) - (center.y * state.camera.zoom);
  state.camera.userChangedView = true;
  clampCamera();
  hidePopup();
}

function handleHotkey(event) {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || hotkeysAreSuppressed(event.target)) {
    return;
  }
  const key = event.key.toLowerCase();
  if (key === 'r') {
    event.preventDefault();
    resetView();
    render();
  } else if (key === 'b') {
    event.preventDefault();
    showBlackportView();
  }
}

function hotkeysAreSuppressed(target) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tagName = target.tagName.toLowerCase();
  return target.isContentEditable || ['input', 'textarea', 'select', 'button'].includes(tagName);
}

function render() {
  if (!state.data) {
    return;
  }

  const rect = canvas.getBoundingClientRect();
  updateCameraViewport(rect.width, rect.height);
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = CONSTANTS.backgroundColor;
  ctx.fillRect(0, 0, rect.width, rect.height);

  drawTerrainUnderlay();
  drawZeroAxes();
  drawMetroLines();
  drawExtraEdges();
  drawSuggestedWalkingPaths();
  drawCurrentRoute();
  drawStations();
  positionInfoPopup();
}

function loadTerrainImage() {
  const image = new Image();
  image.onload = () => {
    state.terrain.image = image;
    state.terrain.loaded = true;
    updateCameraWorld();
    if (!state.camera.initialized) {
      fitToMap();
    }
    render();
  };
  image.src = `assets/blackport_topdown.png?v=${Date.now()}`;
}

async function loadTerrainBounds() {
  try {
    const response = await fetch(`${CONSTANTS.terrainMetadataUrl}?v=${Date.now()}`, { cache: 'no-cache' });
    if (!response.ok) {
      return;
    }
    const bounds = terrainBoundsFromMetadata(await response.json());
    if (!bounds) {
      return;
    }
    state.terrain.bounds = bounds;
    updateCameraWorld();
    if (!state.camera.initialized) {
      fitToMap();
    }
    render();
  } catch (_error) {
    // The viewer can still place the image from the network and image dimensions.
  }
}

function drawTerrainUnderlay() {
  if (!showWorldMapInput.checked || !state.terrain.loaded || !state.terrain.image || !cameraHasWorld()) {
    return;
  }
  const { image } = state.terrain;
  const topLeft = worldToScreen({ x: 0, y: 0 });
  const bottomRight = worldToScreen({ x: state.camera.worldWidth, y: state.camera.worldHeight });
  const left = topLeft.x;
  const top = topLeft.y;
  const width = bottomRight.x - topLeft.x;
  const height = bottomRight.y - topLeft.y;
  ctx.save();
  ctx.globalAlpha = CONSTANTS.worldMapAlpha;
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(image, left, top, width, height);
  ctx.restore();
}

function drawZeroAxes() {
  const terrainBounds = currentTerrainBounds();
  if (!terrainBounds || !cameraHasWorld()) {
    return;
  }
  const minX = terrainBounds.minX;
  const maxX = terrainBounds.maxX;
  const minY = -terrainBounds.maxZ;
  const maxY = -terrainBounds.minZ;
  ctx.save();
  ctx.strokeStyle = CONSTANTS.gridColor;
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  if (minX <= 0 && maxX >= 0) {
    const top = plotToCanvas({ x: 0, y: maxY });
    const bottom = plotToCanvas({ x: 0, y: minY });
    drawLine(top, bottom);
  }
  if (minY <= 0 && maxY >= 0) {
    const left = plotToCanvas({ x: minX, y: 0 });
    const right = plotToCanvas({ x: maxX, y: 0 });
    drawLine(left, right);
  }
  ctx.restore();
}

function drawMetroLines() {
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const segment of state.lineSegments) {
    if (!state.visibleLines.has(segment.lineName) || segment.points.length < 2) {
      continue;
    }
    const lineWidth = segment.connected ? CONSTANTS.connectedWidth : CONSTANTS.unconnectedWidth;
    ctx.setLineDash(segment.connected ? [] : CONSTANTS.unconnectedDash);
    ctx.strokeStyle = colorForLine(segment.lineName);
    ctx.lineWidth = lineWidth;
    drawPlotPolyline(segment.points);
  }
  ctx.restore();
}

function drawExtraEdges() {
  const edges = state.data.extra_edges || [];
  if (!edges.length) {
    return;
  }
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const edge of edges) {
    const points = extraEdgePlotPoints(edge);
    if (points.length < 2) {
      continue;
    }
    ctx.strokeStyle = edge.kind === 'walk' ? CONSTANTS.walkingPathColor : CONSTANTS.connectorPathColor;
    ctx.lineWidth = CONSTANTS.extraPathWidth;
    ctx.setLineDash(edge.kind === 'walk' ? CONSTANTS.walkingPathDash : []);
    drawPlotPolyline(points);
  }
  ctx.restore();
}

function drawSuggestedWalkingPaths() {
  if (!showSuggestedWalkingPathsInput?.checked) {
    return;
  }
  const segments = state.data.suggested_walking_segments || [];
  if (!segments.length) {
    return;
  }
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = CONSTANTS.walkingPathColor;
  ctx.lineWidth = CONSTANTS.extraPathWidth;
  ctx.setLineDash(CONSTANTS.walkingPathDash);
  for (const segment of segments) {
    const points = suggestedWalkingSegmentPlotPoints(segment);
    if (points.length >= 2) {
      drawPlotPolyline(points);
    }
  }
  ctx.restore();
}

function drawCurrentRoute() {
  if (!state.currentRoute) {
    return;
  }
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const step of state.currentRoute.steps) {
    if (!step.pathPoints || step.pathPoints.length < 2) {
      continue;
    }
    ctx.strokeStyle = CONSTANTS.routeOutline;
    ctx.lineWidth = CONSTANTS.routeOutlineWidth;
    ctx.setLineDash([]);
    drawPlotPolyline(step.pathPoints);
    ctx.strokeStyle = routeStepColor(step);
    ctx.lineWidth = CONSTANTS.routeWidth;
    drawPlotPolyline(step.pathPoints);
  }
  ctx.restore();
}

function extraEdgePlotPoints(edge) {
  const rawPathPoints = Array.isArray(edge.path_points) ? edge.path_points : [];
  if (rawPathPoints.length) {
    return rawPathPoints
      .map((point) => plotPointFromCoordinateRecord(point))
      .filter(Boolean);
  }
  const fromPoint = endpointPlotPoint(edge.from_endpoint || endpointFromLegacyStop(edge.from_var));
  const toPoint = endpointPlotPoint(edge.to_endpoint || endpointFromLegacyStop(edge.to_var));
  return [fromPoint, toPoint].filter(Boolean);
}

function endpointFromLegacyStop(stopVar) {
  return stopVar ? { kind: 'stop', stop_var: stopVar } : null;
}

function endpointPlotPoint(endpoint) {
  if (!endpoint) {
    return null;
  }
  if (endpoint.kind === 'stop') {
    const stop = state.stopsByVar.get(endpoint.stop_var || endpoint.key);
    return stop ? stationPlotPoint(stop) : null;
  }
  if (endpoint.kind === 'coord') {
    return plotPointFromCoordinateRecord(endpoint);
  }
  return null;
}

function endpointWorldPoint(endpoint) {
  if (!endpoint) {
    return null;
  }
  if (endpoint.kind === 'stop') {
    const stop = state.stopsByVar.get(endpoint.stop_var || endpoint.key);
    return stop ? { x: stop.x, y: stop.y } : null;
  }
  if (endpoint.kind === 'coord') {
    const x = Number(endpoint.x);
    const y = Number(endpoint.y);
    return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
  }
  return null;
}

function endpointLabel(endpoint) {
  if (!endpoint) {
    return 'Unknown';
  }
  if (endpoint.kind === 'stop') {
    const stopVar = endpoint.stop_var || endpoint.key;
    const stop = state.stopsByVar.get(stopVar);
    return stop ? displayLabel(stop.lbl) : stopVar;
  }
  if (endpoint.kind === 'coord') {
    return `(${endpoint.x}, ${endpoint.y})`;
  }
  return 'Unknown';
}

function plotPointFromCoordinateRecord(record) {
  const x = Number(record?.x);
  const y = Number(record?.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return null;
  }
  return { x, y: -y };
}

function suggestedWalkingSegmentPlotPoints(segment) {
  const rawPath = Array.isArray(segment?.path) ? segment.path : [];
  return rawPath.map((point) => plotPointFromCoordinateRecord(point)).filter(Boolean);
}

function extraEdgeWorldPoints(edge) {
  const rawPathPoints = Array.isArray(edge.path_points) ? edge.path_points : [];
  if (rawPathPoints.length) {
    return rawPathPoints
      .map((point) => {
        const x = Number(point?.x);
        const y = Number(point?.y);
        return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
      })
      .filter(Boolean);
  }
  const fromPoint = endpointWorldPoint(edge.from_endpoint || endpointFromLegacyStop(edge.from_var));
  const toPoint = endpointWorldPoint(edge.to_endpoint || endpointFromLegacyStop(edge.to_var));
  return [fromPoint, toPoint].filter(Boolean);
}

function pathEdgeTurnCoordinates(edge) {
  const points = extraEdgeWorldPoints(edge);
  if (points.length <= 2) {
    return [];
  }
  return points.slice(1, -1);
}

function selectedPathEdgeAnchorPoint(edge) {
  const points = extraEdgePlotPoints(edge);
  if (!points.length) {
    return { x: CONSTANTS.padding, y: CONSTANTS.padding };
  }
  return plotToCanvas(points[Math.floor(points.length / 2)]);
}

function drawStations() {
  ctx.save();
  const labelFontSize = labelFontSizeForZoom();
  ctx.font = `${labelFontSize}px Helvetica, Arial, sans-serif`;
  ctx.textBaseline = 'alphabetic';

  for (const stop of state.data.stops) {
    if (!stopHasVisibleLine(stop)) {
      continue;
    }
    const point = plotToCanvas(stationPlotPoint(stop));
    const fill = stationColor(stop);
    ctx.beginPath();
    ctx.arc(point.x, point.y, CONSTANTS.stationRadius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();

    if (showLabelsInput.checked) {
      drawRotatedLabel(
        displayLabel(stop.lbl),
        point.x + labelOffset(),
        point.y - labelOffset(),
        stationLabelColor(stop),
        labelFontSize,
        false,
      );
    }
  }
  ctx.restore();
}

function drawPlotPolyline(points) {
  if (points.length < 2) {
    return;
  }
  const first = plotToCanvas(points[0]);
  ctx.beginPath();
  ctx.moveTo(first.x, first.y);
  for (const point of points.slice(1)) {
    const screen = plotToCanvas(point);
    ctx.lineTo(screen.x, screen.y);
  }
  ctx.stroke();
}

function drawLine(first, second) {
  ctx.beginPath();
  ctx.moveTo(first.x, first.y);
  ctx.lineTo(second.x, second.y);
  ctx.stroke();
}

function drawRotatedLabel(text, x, y, fill, fontSize, bold) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(CONSTANTS.labelAngle);
  ctx.font = `${bold ? '700 ' : ''}${fontSize}px Helvetica, Arial, sans-serif`;
  ctx.lineJoin = 'round';
  ctx.strokeStyle = CONSTANTS.labelCasingColor;
  ctx.lineWidth = CONSTANTS.labelCasingWidth;
  ctx.strokeText(text, 0, 0);
  ctx.fillStyle = fill;
  ctx.fillText(text, 0, 0);
  ctx.restore();
}

function updateHover(event) {
  const stop = findStopAt(event.offsetX, event.offsetY);
  state.hoverStop = stop;
  if (stop) {
    const lines = linesForStop(stop);
    tooltip.innerHTML = `<strong>${escapeHtml(displayLabel(stop.lbl))}</strong><span>${stop.x}, ${stop.y} · ${lines.join(', ')}</span>`;
    tooltip.hidden = false;
    tooltip.style.left = `${Math.min(event.offsetX + 14, canvas.clientWidth - 290)}px`;
    tooltip.style.top = `${Math.max(14, event.offsetY + 14)}px`;
  } else {
    tooltip.hidden = true;
  }
}

function findStopAt(screenX, screenY) {
  let best = null;
  let bestDistanceSq = Infinity;
  for (const stop of state.data.stops) {
    if (!stopHasVisibleLine(stop)) {
      continue;
    }
    const point = plotToCanvas(stationPlotPoint(stop));
    const dx = point.x - screenX;
    const dy = point.y - screenY;
    const distanceSq = dx * dx + dy * dy;
    if (distanceSq <= CONSTANTS.stationHitTolerance ** 2 && distanceSq < bestDistanceSq) {
      best = stop;
      bestDistanceSq = distanceSq;
    }
  }
  return best;
}

function findExtraEdgeAt(screenX, screenY) {
  let best = null;
  let bestDistanceSq = Infinity;
  const maxDistanceSq = CONSTANTS.stationHitTolerance ** 2;
  for (const edge of state.data.extra_edges || []) {
    const points = extraEdgePlotPoints(edge).map(plotToCanvas);
    const distanceSq = pointToPolylineDistanceSq({ x: screenX, y: screenY }, points);
    if (distanceSq !== null && distanceSq <= maxDistanceSq && distanceSq < bestDistanceSq) {
      best = edge;
      bestDistanceSq = distanceSq;
    }
  }
  return best;
}

function selectStop(stop, options = {}) {
  state.selectedStop = stop;
  state.selectedPathEdge = null;
  if (options.pan) {
    centerOnPlotPoint(stationPlotPoint(stop));
  }
  if (options.updateRouteStart) {
    fillRouteInputFromStop(stop);
  }
  updateInfoPopup();
  render();
}

function selectPathEdge(edge) {
  state.selectedStop = null;
  state.selectedPathEdge = edge;
  updateInfoPopup();
  render();
}

function clearSelection() {
  state.selectedStop = null;
  state.selectedPathEdge = null;
  state.searchMatches = [];
  searchInput.value = '';
  refreshSearch();
  hidePopup();
  render();
}

function updateInfoPopup() {
  if (!state.selectedStop && !state.selectedPathEdge) {
    hidePopup();
    return;
  }
  if (state.selectedPathEdge) {
    updatePathEdgePopup(state.selectedPathEdge);
    return;
  }
  const stop = state.selectedStop;
  const statusText = stop.is_connected ? 'Open' : 'Planned';
  const chimeText = stop.is_connected && stop.chime_directions?.length
    ? `<p class="section-label">Chimes</p><p>${stop.chime_directions.map(capitalize).join(', ')}</p>`
    : '';
  infoPopup.innerHTML = `
    <h2>${escapeHtml(displayLabel(stop.lbl))}</h2>
    <p>Coords: (${stop.x}, ${stop.y})<br>Lines: ${escapeHtml(linesForStop(stop).join(', '))}<br>Status: ${statusText}</p>
    ${chimeText}
  `;
  infoPopup.hidden = false;
  positionInfoPopup();
}

function updatePathEdgePopup(edge) {
  const points = extraEdgeWorldPoints(edge);
  const turnPoints = pathEdgeTurnCoordinates(edge);
  const fromLabel = endpointLabel(edge.from_endpoint || endpointFromLegacyStop(edge.from_var));
  const toLabel = endpointLabel(edge.to_endpoint || endpointFromLegacyStop(edge.to_var));
  const kindLabel = edge.kind === 'walk' ? 'Walking path' : 'Metro connector';
  const turnText = turnPoints.length
    ? turnPoints.map((point) => `(${point.x}, ${point.y})`).join('<br>')
    : 'No turn coordinates';
  infoPopup.innerHTML = `
    <h2>${kindLabel}</h2>
    <p>From: ${escapeHtml(fromLabel)}<br>To: ${escapeHtml(toLabel)}<br>Distance: ${formatTrackDistance(Math.round(polylineDistance(points.map((point) => ({ x: point.x, y: -point.y })))))}<br>Shape: ${turnPoints.length ? 'turn' : 'direct'}</p>
    <p class="section-label">Turn Coordinates</p>
    <p>${turnText}</p>
  `;
  infoPopup.hidden = false;
  positionInfoPopup();
}

function positionInfoPopup() {
  if ((!state.selectedStop && !state.selectedPathEdge) || infoPopup.hidden) {
    return;
  }
  const point = state.selectedStop
    ? plotToCanvas(stationPlotPoint(state.selectedStop))
    : selectedPathEdgeAnchorPoint(state.selectedPathEdge);
  const stageRect = canvas.getBoundingClientRect();
  const box = infoPopup.getBoundingClientRect();
  const margin = CONSTANTS.padding / 2;
  let left = point.x + 14;
  if (left + box.width > stageRect.width - margin) {
    left = point.x - 14 - box.width;
  }
  left = Math.max(margin, Math.min(left, stageRect.width - margin - box.width));
  let top = point.y - 14 - box.height;
  if (top < margin) {
    top = point.y + 14;
  }
  top = Math.max(margin, Math.min(top, stageRect.height - margin - box.height));
  infoPopup.style.left = `${left}px`;
  infoPopup.style.top = `${top}px`;
}

function hidePopup() {
  infoPopup.hidden = true;
}

function refreshSearch() {
  const query = searchInput.value.trim();
  state.searchMatches = searchMatches(query);
  if (!query) {
    searchStatus.textContent = 'Search stations by village name or station code.';
  } else if (state.searchMatches.length === 0) {
    searchStatus.textContent = 'No station matches that search.';
  } else if (state.searchMatches.length === 1) {
    searchStatus.textContent = 'Press Enter or click Go to jump to the match.';
  } else {
    searchStatus.textContent = `${state.searchMatches.length} matches. Press Enter or click Go to jump to the best match.`;
  }
}

function jumpToSearchResult() {
  refreshSearch();
  const [first] = state.searchMatches;
  if (!first) {
    return;
  }
  selectStop(first, { pan: true, updateRouteStart: true });
}

function searchMatches(query) {
  const normalizedQuery = normalizeIdentity(query);
  if (!normalizedQuery) {
    return [];
  }
  const ranked = [];
  for (const stop of state.data.stops) {
    const normalizedLabel = normalizeIdentity(stop.lbl);
    const normalizedDisplay = normalizeIdentity(displayLabel(stop.lbl));
    const normalizedVar = normalizeIdentity(stop.var.replace(/^P_/, ''));
    let rank = null;
    if ([normalizedLabel, normalizedDisplay].includes(normalizedQuery)) {
      rank = [0, stop.lbl.length, stop.lbl.toLowerCase()];
    } else if (normalizedQuery === normalizedVar) {
      rank = [1, stop.var.length, stop.lbl.toLowerCase()];
    } else if ([normalizedLabel, normalizedDisplay].some((candidate) => candidate.startsWith(normalizedQuery))) {
      rank = [2, stop.lbl.length, stop.lbl.toLowerCase()];
    } else if (normalizedVar.startsWith(normalizedQuery)) {
      rank = [3, stop.var.length, stop.lbl.toLowerCase()];
    } else if ([normalizedLabel, normalizedDisplay].some((candidate) => candidate.includes(normalizedQuery))) {
      rank = [4, stop.lbl.length, stop.lbl.toLowerCase()];
    } else if (normalizedVar.includes(normalizedQuery)) {
      rank = [5, stop.var.length, stop.lbl.toLowerCase()];
    }
    if (rank) {
      ranked.push({ rank, stop });
    }
  }
  ranked.sort((a, b) => compareRank(a.rank, b.rank));
  return ranked.map((item) => item.stop);
}

function planRoute() {
  const start = resolveStop(routeStartInput.value);
  const end = resolveStop(routeEndInput.value);
  if (!start || !end) {
    state.currentRoute = null;
    state.routeRequest = null;
    routeSummary.textContent = 'Choose two stations.';
    routeSteps.textContent = 'Could not find one of those station names.';
    render();
    return;
  }
  state.routeRequest = [start.var, end.var];
  const route = findRoute(start.var, end.var);
  state.currentRoute = route;
  if (!route) {
    routeSummary.textContent = `No route from ${displayLabel(start.lbl)} to ${displayLabel(end.lbl)}.`;
    routeSteps.textContent = 'No route exists for those endpoints with the current metro data.';
  } else {
    routeSummary.textContent = `${displayLabel(start.lbl)} to ${displayLabel(end.lbl)}\n${formatTrackDistance(route.totalDistance)}, ${route.totalInterchanges} interchange(s)`;
    routeSteps.textContent = routeInstructions(route);
  }
  render();
}

function clearRouteStateForInput() {
  state.currentRoute = null;
  state.routeRequest = null;
  routeSummary.textContent = 'Choose two stations.';
  routeSteps.textContent = 'Enter or select a start and destination, then press Route.';
}

function prepareRouteInput(input) {
  state.preferredRouteInput = input;
  state.selectedStop = null;
  state.selectedPathEdge = null;
  hidePopup();
}

function swapRoute() {
  const start = routeStartInput.value;
  routeStartInput.value = routeEndInput.value;
  routeEndInput.value = start;
  if (routeStartInput.value.trim() && routeEndInput.value.trim()) {
    planRoute();
  }
}

function clearRoute() {
  state.currentRoute = null;
  state.routeRequest = null;
  state.preferredRouteInput = routeStartInput;
  routeStartInput.value = '';
  routeEndInput.value = '';
  routeSummary.textContent = 'Choose two stations.';
  routeSteps.textContent = 'Enter or select a start and destination, then press Route.';
  render();
}

function fillRouteInputFromStop(stop) {
  const targetInput = routeInputTargetForStop(stop);
  if (!targetInput) {
    return;
  }
  targetInput.value = displayLabel(stop.lbl);
  state.preferredRouteInput = targetInput === routeStartInput ? routeEndInput : routeStartInput;
  clearRouteStateForInput();
}

function routeInputTargetForStop(stop) {
  const preferredInput = state.preferredRouteInput;
  if (document.activeElement === routeStartInput || document.activeElement === routeEndInput) {
    return document.activeElement;
  }
  if (
    (preferredInput === routeStartInput || preferredInput === routeEndInput)
    && !preferredInput.value.trim()
  ) {
    return preferredInput;
  }

  if (!routeStartInput.value.trim()) {
    return routeStartInput;
  }
  if (!routeEndInput.value.trim() && resolveStop(routeStartInput.value)?.var !== stop.var) {
    return routeEndInput;
  }
  return null;
}

function findRoute(startVar, endVar) {
  if (startVar === endVar) {
    return { startVar, endVar, totalDistance: 0, totalInterchanges: 0, steps: [] };
  }
  return findMetroRoute(startVar, endVar);
}

function findMetroRoute(startVar, endVar) {
  const graph = buildRouteGraph();
  const startNodes = graphNodesForStop(graph, startVar);
  const endKeys = new Set(graphNodesForStop(graph, endVar).map(nodeKey));
  if (!startNodes.length || !endKeys.size) {
    return null;
  }
  const costs = new Map();
  const previous = new Map();
  const queue = [];
  for (const node of startNodes) {
    const key = nodeKey(node);
    costs.set(key, [0, 0]);
    previous.set(key, null);
    queue.push({ node, distance: 0, transfers: 0 });
  }

  let bestEnd = null;
  while (queue.length) {
    queue.sort((a, b) => a.distance - b.distance || a.transfers - b.transfers);
    const current = queue.shift();
    const currentKey = nodeKey(current.node);
    const bestCost = costs.get(currentKey);
    if (!bestCost || bestCost[0] !== current.distance || bestCost[1] !== current.transfers) {
      continue;
    }
    if (endKeys.has(currentKey)) {
      bestEnd = current.node;
      break;
    }
    for (const edge of graph.get(currentKey) || []) {
      const nextKey = nodeKey(edge.end);
      const nextCost = [current.distance + edge.distance, current.transfers + edge.transferCount];
      const oldCost = costs.get(nextKey) || [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER];
      if (nextCost[0] < oldCost[0] || (nextCost[0] === oldCost[0] && nextCost[1] < oldCost[1])) {
        costs.set(nextKey, nextCost);
        previous.set(nextKey, { node: current.node, edge });
        queue.push({ node: edge.end, distance: nextCost[0], transfers: nextCost[1] });
      }
    }
  }
  if (!bestEnd) {
    return null;
  }

  const edges = [];
  let cursorKey = nodeKey(bestEnd);
  while (previous.get(cursorKey)) {
    const item = previous.get(cursorKey);
    edges.push(item.edge);
    cursorKey = nodeKey(item.node);
  }
  edges.reverse();
  const steps = [];
  for (const edge of edges) {
    appendRouteStep(steps, edge);
  }
  const total = costs.get(nodeKey(bestEnd));
  return { startVar, endVar, totalDistance: total[0], totalInterchanges: total[1], steps };
}

function buildRouteGraph() {
  const graph = new Map();
  for (const stop of state.data.stops) {
    const lines = linesForStop(stop);
    for (const lineName of lines) {
      ensureGraphNode(graph, { stopVar: stop.var, lineName });
    }
    for (let i = 0; i < lines.length; i += 1) {
      for (let j = i + 1; j < lines.length; j += 1) {
        appendGraphEdge(graph, {
          start: { stopVar: stop.var, lineName: lines[i] },
          end: { stopVar: stop.var, lineName: lines[j] },
          distance: 0,
          transferCount: 1,
          kind: 'transfer',
          lineName: lines[j],
          pathPoints: [],
        });
        appendGraphEdge(graph, {
          start: { stopVar: stop.var, lineName: lines[j] },
          end: { stopVar: stop.var, lineName: lines[i] },
          distance: 0,
          transferCount: 1,
          kind: 'transfer',
          lineName: lines[i],
          pathPoints: [],
        });
      }
    }
  }
  for (const segment of state.lineSegments) {
    const distance = Math.round(polylineDistance(segment.points));
    appendGraphEdge(graph, {
      start: { stopVar: segment.startVar, lineName: segment.lineName },
      end: { stopVar: segment.endVar, lineName: segment.lineName },
      distance,
      transferCount: 0,
      kind: 'ride',
      lineName: segment.lineName,
      pathPoints: segment.points,
    });
    appendGraphEdge(graph, {
      start: { stopVar: segment.endVar, lineName: segment.lineName },
      end: { stopVar: segment.startVar, lineName: segment.lineName },
      distance,
      transferCount: 0,
      kind: 'ride',
      lineName: segment.lineName,
      pathPoints: [...segment.points].reverse(),
    });
  }
  return graph;
}

function appendRouteStep(steps, edge) {
  if (edge.kind === 'transfer') {
    steps.push({
      kind: 'transfer',
      startVar: edge.start.stopVar,
      endVar: edge.end.stopVar,
      distance: 0,
      lineName: edge.lineName,
      stopVars: [edge.start.stopVar],
      pathPoints: [],
    });
    return;
  }
  const previous = steps[steps.length - 1];
  if (previous && edge.kind === 'ride' && previous.kind === 'ride' && previous.lineName === edge.lineName) {
    previous.endVar = edge.end.stopVar;
    previous.distance += edge.distance;
    if (previous.stopVars[previous.stopVars.length - 1] !== edge.end.stopVar) {
      previous.stopVars.push(edge.end.stopVar);
    }
    if (previous.pathPoints.length && edge.pathPoints.length && samePoint(previous.pathPoints[previous.pathPoints.length - 1], edge.pathPoints[0])) {
      previous.pathPoints.push(...edge.pathPoints.slice(1));
    } else {
      previous.pathPoints.push(...edge.pathPoints);
    }
    return;
  }
  steps.push({
    kind: edge.kind,
    startVar: edge.start.stopVar,
    endVar: edge.end.stopVar,
    distance: edge.distance,
    lineName: edge.lineName,
    stopVars: [edge.start.stopVar, edge.end.stopVar],
    pathPoints: edge.pathPoints,
  });
}

function routeInstructions(route) {
  const start = state.stopsByVar.get(route.startVar);
  const end = state.stopsByVar.get(route.endVar);
  if (!route.steps.length) {
    return `You are already at ${displayLabel(start.lbl)}.\nTrack distance: ${formatTrackDistance(0)}.`;
  }
  const lines = [
    `Track distance: ${formatTrackDistance(route.totalDistance)}`,
    `Interchanges: ${route.totalInterchanges}`,
    '',
  ];
  route.steps.forEach((step, index) => {
    const stepStart = state.stopsByVar.get(step.startVar);
    const stepEnd = state.stopsByVar.get(step.endVar);
    const startLabel = displayLabel(stepStart.lbl);
    const endLabel = displayLabel(stepEnd.lbl);
    if (step.kind === 'ride') {
      const stopCount = Math.max(0, step.stopVars.length - 1);
      lines.push(`${index + 1}. Take Line ${step.lineName} from ${startLabel} to ${endLabel} for ${formatTrackDistance(step.distance)} (${stopCount} ${stopCount === 1 ? 'stop' : 'stops'}).`);
    } else if (step.kind === 'transfer') {
      lines.push(`${index + 1}. Transfer at ${startLabel} to Line ${step.lineName}.`);
    }
  });
  lines.push('');
  const unfinishedLineNames = unfinishedRouteLineNames(route);
  if (unfinishedLineNames.length) {
    const lineWord = unfinishedLineNames.length === 1 ? 'line is' : 'lines are';
    lines.push(`Warning: the ${formatLineList(unfinishedLineNames)} ${lineWord} not fully constructed for this route. Consider direct flying instead.`);
    lines.push('');
  }
  lines.push(`Route from ${displayLabel(start.lbl)} to ${displayLabel(end.lbl)}.`);
  return lines.join('\n');
}

function unfinishedRouteLineNames(route) {
  const lineNames = new Set();
  for (const step of route.steps) {
    if (step.kind !== 'ride' || !step.lineName || step.stopVars.length < 2) {
      continue;
    }
    for (let index = 0; index < step.stopVars.length - 1; index += 1) {
      const segment = state.lineSegments.find((candidate) => (
        candidate.lineName === step.lineName &&
        (
          (candidate.startVar === step.stopVars[index] && candidate.endVar === step.stopVars[index + 1]) ||
          (candidate.startVar === step.stopVars[index + 1] && candidate.endVar === step.stopVars[index])
        )
      ));
      if (segment && !segment.connected) {
        lineNames.add(step.lineName);
      }
    }
  }
  return [...lineNames].sort();
}

function formatLineList(lineNames) {
  if (lineNames.length <= 2) {
    return lineNames.join(lineNames.length === 2 ? ' and ' : '');
  }
  return `${lineNames.slice(0, -1).join(', ')}, and ${lineNames[lineNames.length - 1]}`;
}

function stationPlotPoint(stop) {
  return { x: stop.x, y: -stop.y };
}

function cameraHasWorld() {
  return state.camera.worldWidth > 1
    && state.camera.worldHeight > 1
    && state.camera.viewportWidth > 1
    && state.camera.viewportHeight > 1;
}

function updateCameraWorld() {
  const bounds = currentTerrainBounds();
  const image = state.terrain.image;
  const width = image?.naturalWidth || (bounds ? Math.max(1, bounds.maxX - bounds.minX + 1) : 1);
  const height = image?.naturalHeight || (bounds ? Math.max(1, bounds.maxZ - bounds.minZ + 1) : 1);
  state.camera.worldWidth = width;
  state.camera.worldHeight = height;
  const fitZoom = Math.min(
    state.camera.viewportWidth / width,
    state.camera.viewportHeight / height,
  );
  state.camera.minZoom = Math.max(0.0001, fitZoom);
  state.camera.maxZoom = Math.max(state.camera.minZoom * 2, CONSTANTS.maxZoom);
  state.camera.zoom = clamp(state.camera.zoom, state.camera.minZoom, state.camera.maxZoom);
  clampCamera();
}

function plotToWorld(point) {
  const bounds = currentTerrainBounds();
  if (!bounds || !cameraHasWorld()) {
    return { x: point.x, y: -point.y };
  }
  const xSpan = Math.max(bounds.maxX - bounds.minX, 1);
  const zSpan = Math.max(bounds.maxZ - bounds.minZ, 1);
  return {
    x: ((point.x - bounds.minX) / xSpan) * state.camera.worldWidth,
    y: (((-point.y) - bounds.minZ) / zSpan) * state.camera.worldHeight,
  };
}

function worldToPlot(point) {
  const bounds = currentTerrainBounds();
  if (!bounds || !cameraHasWorld()) {
    return { x: point.x, y: -point.y };
  }
  return {
    x: bounds.minX + ((point.x / state.camera.worldWidth) * (bounds.maxX - bounds.minX)),
    y: -(bounds.minZ + ((point.y / state.camera.worldHeight) * (bounds.maxZ - bounds.minZ))),
  };
}

function worldToScreen(point) {
  return {
    x: (point.x * state.camera.zoom) + state.camera.translateX,
    y: (point.y * state.camera.zoom) + state.camera.translateY,
  };
}

function screenToWorld(point) {
  return {
    x: (point.x - state.camera.translateX) / state.camera.zoom,
    y: (point.y - state.camera.translateY) / state.camera.zoom,
  };
}

function plotToCanvas(point) {
  return worldToScreen(plotToWorld(point));
}

function centerOnPlotPoint(point) {
  if (!cameraHasWorld()) {
    return;
  }
  const world = plotToWorld(point);
  state.camera.translateX = (state.camera.viewportWidth / 2) - (world.x * state.camera.zoom);
  state.camera.translateY = (state.camera.viewportHeight / 2) - (world.y * state.camera.zoom);
  state.camera.userChangedView = true;
  clampCamera();
  hidePopup();
}

function zoomAtViewportCenter(nextZoom) {
  zoomAtScreenPoint(state.camera.viewportWidth / 2, state.camera.viewportHeight / 2, nextZoom);
}

function zoomAtScreenPoint(screenX, screenY, nextZoom) {
  if (!cameraHasWorld()) {
    return;
  }
  const oldWorldPoint = screenToWorld({ x: screenX, y: screenY });
  state.camera.zoom = clamp(nextZoom, state.camera.minZoom, state.camera.maxZoom);

  // Keep the same world coordinate under the cursor after zooming.
  state.camera.translateX = screenX - (oldWorldPoint.x * state.camera.zoom);
  state.camera.translateY = screenY - (oldWorldPoint.y * state.camera.zoom);
  state.camera.userChangedView = true;
  clampCamera();
  hidePopup();
  render();
}

function panBy(deltaX, deltaY) {
  state.camera.translateX += deltaX;
  state.camera.translateY += deltaY;
  state.camera.userChangedView = true;
  clampCamera();
  hidePopup();
}

function fitToMap() {
  if (!cameraHasWorld()) {
    return;
  }
  state.camera.zoom = state.camera.minZoom;
  state.camera.translateX = (state.camera.viewportWidth - (state.camera.worldWidth * state.camera.zoom)) / 2;
  state.camera.translateY = (state.camera.viewportHeight - (state.camera.worldHeight * state.camera.zoom)) / 2;
  state.camera.initialized = true;
  state.camera.userChangedView = false;
  clampCamera();
}

function clampCamera() {
  if (!cameraHasWorld()) {
    return;
  }
  const scaledWidth = state.camera.worldWidth * state.camera.zoom;
  const scaledHeight = state.camera.worldHeight * state.camera.zoom;
  state.camera.translateX = clampAxis(state.camera.translateX, scaledWidth, state.camera.viewportWidth);
  state.camera.translateY = clampAxis(state.camera.translateY, scaledHeight, state.camera.viewportHeight);
}

function clampAxis(translate, scaledSize, viewportSize) {
  const padding = Math.min(CONSTANTS.clampPadding, viewportSize * 0.2);
  if (scaledSize <= viewportSize - (padding * 2)) {
    return (viewportSize - scaledSize) / 2;
  }
  const minTranslate = viewportSize - scaledSize - padding;
  const maxTranslate = padding;
  return clamp(translate, minTranslate, maxTranslate);
}

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function wheelNextZoom(event) {
  let delta = event.deltaY;
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) {
    delta *= 16;
  } else if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) {
    delta *= state.camera.viewportHeight;
  }
  return state.camera.zoom * Math.exp(-delta * CONSTANTS.wheelZoomSpeed);
}

function normalizedWorldBounds(first, second) {
  return {
    minX: Math.min(first.x, second.x),
    maxX: Math.max(first.x, second.x),
    minY: Math.min(first.y, second.y),
    maxY: Math.max(first.y, second.y),
  };
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function graphNodesForStop(graph, stopVar) {
  return [...graph.keys()]
    .map(parseNodeKey)
    .filter((node) => node.stopVar === stopVar);
}

function ensureGraphNode(graph, node) {
  const key = nodeKey(node);
  if (!graph.has(key)) {
    graph.set(key, []);
  }
}

function appendGraphEdge(graph, edge) {
  ensureGraphNode(graph, edge.start);
  ensureGraphNode(graph, edge.end);
  graph.get(nodeKey(edge.start)).push(edge);
}

function nodeKey(node) {
  return `${node.stopVar}|${node.lineName}`;
}

function parseNodeKey(key) {
  const [stopVar, lineName] = key.split('|');
  return { stopVar, lineName };
}

function resolveStop(value) {
  const query = value.trim();
  if (!query) {
    return null;
  }
  const normalized = normalizeIdentity(query);
  return state.data.stops.find((stop) => normalizeIdentity(stop.lbl) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(displayLabel(stop.lbl)) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(stop.var) === normalized)
    || state.data.stops.find((stop) => normalizeIdentity(stop.var.replace(/^P_/, '')) === normalized)
    || searchMatches(query)[0]
    || null;
}

function stationColor(stop) {
  const lines = linesForStop(stop).filter((lineName) => state.visibleLines.has(lineName));
  return lines.length === 1 ? colorForLine(lines[0]) : CONSTANTS.intersectionColor;
}

function stationLabelColor(stop) {
  const lines = linesForStop(stop).filter((lineName) => state.visibleLines.has(lineName));
  return lines.length === 1 ? colorForLine(lines[0]) : CONSTANTS.junctionLabelColor;
}

function stopHasVisibleLine(stop) {
  return linesForStop(stop).some((lineName) => state.visibleLines.has(lineName));
}

function linesForStop(stop) {
  return state.stopLines.get(stop.var) || [];
}

function colorForLine(lineName) {
  return state.data.line_colors[lineName] || CONSTANTS.textColor;
}

function routeStepColor(step) {
  if (step.kind === 'ride' && step.lineName) {
    return colorForLine(step.lineName);
  }
  return CONSTANTS.routeOutline;
}

function labelFontSizeForZoom() {
  const scale = cameraStyleScale();
  const growth = Math.min(4, Math.max(0, Math.round(Math.log2(scale) * 1.2)));
  return CONSTANTS.baseLabelFontSize + growth;
}

function labelOffset() {
  return 7 + (labelFontSizeForZoom() - CONSTANTS.baseLabelFontSize);
}

function cameraStyleScale() {
  return Math.max(1, state.camera.zoom / Math.max(state.camera.minZoom, 0.0001));
}

function networkSummary() {
  const stops = state.data.stops;
  const openStops = stops.filter((stop) => stop.is_connected).length;
  const lineCount = Object.keys(state.data.line_stop_vars || {}).length;
  return `${stops.length} stations · ${openStops} open · ${lineCount} lines`;
}

function polylineDistance(points) {
  let total = 0;
  for (let index = 0; index < points.length - 1; index += 1) {
    const first = points[index];
    const second = points[index + 1];
    total += Math.hypot(second.x - first.x, second.y - first.y);
  }
  return total;
}

function pointToPolylineDistanceSq(point, points) {
  if (points.length < 2) {
    return null;
  }
  let bestDistanceSq = Infinity;
  for (let index = 0; index < points.length - 1; index += 1) {
    const first = points[index];
    const second = points[index + 1];
    const dx = second.x - first.x;
    const dy = second.y - first.y;
    const lengthSq = (dx * dx) + (dy * dy);
    const t = lengthSq === 0
      ? 0
      : clamp(
        (((point.x - first.x) * dx) + ((point.y - first.y) * dy)) / lengthSq,
        0,
        1,
      );
    const closest = {
      x: first.x + (dx * t),
      y: first.y + (dy * t),
    };
    const distanceSq = ((point.x - closest.x) ** 2) + ((point.y - closest.y) ** 2);
    bestDistanceSq = Math.min(bestDistanceSq, distanceSq);
  }
  return bestDistanceSq;
}

function boundsForPoints(points) {
  return points.reduce((bounds, point) => ({
    minX: Math.min(bounds.minX, point.x),
    minY: Math.min(bounds.minY, point.y),
    maxX: Math.max(bounds.maxX, point.x),
    maxY: Math.max(bounds.maxY, point.y),
  }), {
    minX: Infinity,
    minY: Infinity,
    maxX: -Infinity,
    maxY: -Infinity,
  });
}

function validBounds(bounds) {
  return Number.isFinite(bounds.minX)
    && Number.isFinite(bounds.maxX)
    && Number.isFinite(bounds.minY)
    && Number.isFinite(bounds.maxY)
    && bounds.minX <= bounds.maxX
    && bounds.minY <= bounds.maxY;
}

function samePoint(first, second) {
  return first.x === second.x && first.y === second.y;
}

function compareRank(first, second) {
  for (let index = 0; index < Math.min(first.length, second.length); index += 1) {
    if (first[index] < second[index]) return -1;
    if (first[index] > second[index]) return 1;
  }
  return first.length - second.length;
}

function formatTrackDistance(distanceMeters) {
  if (distanceMeters < 1000) {
    return `${Math.round(distanceMeters).toLocaleString()} m`;
  }
  return `${Number((distanceMeters / 1000).toFixed(1)).toLocaleString()} km`;
}

function terrainStationBounds(stops) {
  if (!stops.length) {
    return null;
  }
  const xs = stops.map((stop) => stop.x);
  const zs = stops.map((stop) => stop.y);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minZ: Math.min(...zs),
    maxZ: Math.max(...zs),
  };
}

function currentTerrainBounds() {
  if (state.terrain.bounds) {
    return state.terrain.bounds;
  }
  const bounds = state.terrain.stationBounds;
  const image = state.terrain.image;
  if (!bounds || !image?.naturalWidth || !image?.naturalHeight) {
    return null;
  }
  const stationWidth = bounds.maxX - bounds.minX + 1;
  const stationHeight = bounds.maxZ - bounds.minZ + 1;
  const xMargin = Math.max(0, (image.naturalWidth - stationWidth) / 2);
  const zMargin = Math.max(0, (image.naturalHeight - stationHeight) / 2);
  const minX = bounds.minX - xMargin;
  const minZ = bounds.minZ - zMargin;
  return {
    minX,
    maxX: minX + image.naturalWidth - 1,
    minZ,
    maxZ: minZ + image.naturalHeight - 1,
  };
}

function terrainBoundsFromMetadata(payload) {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const minX = finiteNumber(payload.min_x);
  const maxX = finiteNumber(payload.max_x);
  const minZ = finiteNumber(payload.min_z);
  const maxZ = finiteNumber(payload.max_z);
  if (minX === null || maxX === null || minZ === null || maxZ === null || minX >= maxX || minZ >= maxZ) {
    return null;
  }
  return { minX, maxX, minZ, maxZ };
}

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function displayLabel(label) {
  const match = /^([A-Za-z]+)_?\{?([0-9-]+)\}?$/.exec(label);
  if (!match || !label.includes('_')) {
    return label;
  }
  return `${match[1]}${toSubscript(match[2])}`;
}

function toSubscript(value) {
  const map = { '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉', '-': '₋' };
  return String(value).replace(/[0-9-]/g, (character) => map[character] || character);
}

function normalizeIdentity(value) {
  return String(value).trim().toLowerCase().replace(/[^a-z0-9-]/g, '');
}

function capitalize(value) {
  return String(value).charAt(0).toUpperCase() + String(value).slice(1);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
