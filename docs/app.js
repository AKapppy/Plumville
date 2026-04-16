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
const useMetroInput = document.querySelector('#useMetroInput');
const useFlyingInput = document.querySelector('#useFlyingInput');
const routeButton = document.querySelector('#routeButton');
const swapRouteButton = document.querySelector('#swapRouteButton');
const clearRouteButton = document.querySelector('#clearRouteButton');
const routeSummary = document.querySelector('#routeSummary');
const routeSteps = document.querySelector('#routeSteps');
const resetViewButton = document.querySelector('#resetViewButton');
const blackportButton = document.querySelector('#blackportButton');
const clearSelectionButton = document.querySelector('#clearSelectionButton');
const showWorldMapInput = document.querySelector('#showWorldMapInput');
const showLabelsInput = document.querySelector('#showLabelsInput');
const showAlignmentInput = document.querySelector('#showAlignmentInput');
const showFrontierInput = document.querySelector('#showFrontierInput');

const CONSTANTS = {
  padding: 80,
  backgroundColor: '#050505',
  textColor: '#f7f7f7',
  gridColor: '#4b4b4b',
  intersectionColor: '#ffffff',
  defaultZoom: 1,
  zoomStep: 1.15,
  maxVisibleBlocksAtMaxZoom: 10,
  labelAngle: -30 * Math.PI / 180,
  baseLabelFontSize: 12,
  stationRadius: 4,
  stationHitTolerance: 10,
  unconnectedDash: [10, 6],
  unconnectedWidth: 3,
  connectedWidth: 4,
  routeOutline: '#ffffff',
  routeOutlineWidth: 10,
  routeWidth: 6,
  frontierOutline: '#ffd6e6',
  frontierOutlineWidth: 12,
  frontierWidth: 8,
  alignmentOutline: '#d8d8d8',
  alignmentWidth: 2,
  alignmentPadding: 16,
  alignmentMinSize: 30,
  alignmentLabelSize: 10,
  worldMapAlpha: 0.745,
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
  hoverStop: null,
  searchMatches: [],
  currentRoute: null,
  routeRequest: null,
  terrain: {
    image: null,
    loaded: false,
    centerX: 294,
    centerZ: 390,
    radius: 2000,
  },
  viewport: {
    zoom: CONSTANTS.defaultZoom,
    panX: 0,
    panY: 0,
  },
  transform: {
    width: 1,
    height: 1,
    minX: 0,
    maxX: 1,
    minY: 0,
    maxY: 1,
    scale: 1,
  },
  plotBounds: null,
  dragging: false,
  dragDistance: 0,
  lastPointer: null,
};

init();

async function init() {
  try {
    loadTerrainImage();
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
  ];
  state.plotBounds = boundsForPoints(allPoints);
  summaryText.textContent = stationProgressSummary();
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
      state.viewport.panX += dx;
      state.viewport.panY += dy;
      state.dragDistance += Math.abs(dx) + Math.abs(dy);
      state.lastPointer = { x: event.clientX, y: event.clientY };
      render();
      return;
    }
    updateHover(event);
  });

  canvas.addEventListener('pointerup', (event) => {
    canvas.releasePointerCapture(event.pointerId);
    state.dragging = false;
    state.lastPointer = null;
    canvas.classList.remove('dragging');
    if (state.dragDistance <= 4) {
      const stop = findStopAt(event.offsetX, event.offsetY);
      if (stop) {
        selectStop(stop, { updateRouteStart: true });
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
    zoomAt(event.offsetX, event.offsetY, event.deltaY > 0 ? 1 / CONSTANTS.zoomStep : CONSTANTS.zoomStep);
  }, { passive: false });

  document.addEventListener('pointerdown', (event) => {
    if (infoPopup.hidden || infoPopup.contains(event.target)) {
      return;
    }
    state.selectedStop = null;
    hidePopup();
    render();
  });

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
  routeButton.addEventListener('click', planRoute);
  swapRouteButton.addEventListener('click', swapRoute);
  clearRouteButton.addEventListener('click', clearRoute);
  useMetroInput.addEventListener('change', refreshRouteIfNeeded);
  useFlyingInput.addEventListener('change', refreshRouteIfNeeded);

  resetViewButton.addEventListener('click', () => {
    resetView();
    render();
  });
  blackportButton.addEventListener('click', showBlackportView);
  clearSelectionButton.addEventListener('click', clearSelection);

  for (const input of [showWorldMapInput, showLabelsInput, showAlignmentInput, showFrontierInput]) {
    input.addEventListener('change', render);
  }
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * pixelRatio));
  canvas.height = Math.max(1, Math.round(rect.height * pixelRatio));
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  updateTransform(rect.width, rect.height);
}

function updateTransform(width, height) {
  if (!state.plotBounds) {
    return;
  }
  const xSpan = Math.max(state.plotBounds.maxX - state.plotBounds.minX, 1);
  const ySpan = Math.max(state.plotBounds.maxY - state.plotBounds.minY, 1);
  const scale = Math.min(
    (width - (CONSTANTS.padding * 2)) / xSpan,
    (height - (CONSTANTS.padding * 2)) / ySpan,
  );
  state.transform = {
    width,
    height,
    minX: state.plotBounds.minX,
    maxX: state.plotBounds.maxX,
    minY: state.plotBounds.minY,
    maxY: state.plotBounds.maxY,
    scale: Math.max(scale, 0.001),
  };
}

function resetView() {
  state.viewport.zoom = CONSTANTS.defaultZoom;
  state.viewport.panX = 0;
  state.viewport.panY = 0;
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

function setViewToPlotBounds(bounds) {
  const { width, height, scale } = state.transform;
  const spanX = Math.max(bounds.maxX - bounds.minX, 1);
  const spanY = Math.max(bounds.maxY - bounds.minY, 1);
  const availableWidth = Math.max(width - (CONSTANTS.padding * 2), 1);
  const availableHeight = Math.max(height - (CONSTANTS.padding * 2), 1);
  state.viewport.zoom = Math.max(
    CONSTANTS.defaultZoom,
    Math.min(availableWidth / (spanX * scale), availableHeight / (spanY * scale), maxZoom()),
  );
  const baseCenter = plotToBaseCanvas({
    x: (bounds.minX + bounds.maxX) / 2,
    y: (bounds.minY + bounds.maxY) / 2,
  });
  state.viewport.panX = ((width / 2) - baseCenter.x) * state.viewport.zoom;
  state.viewport.panY = ((height / 2) - baseCenter.y) * state.viewport.zoom;
  hidePopup();
}

function render() {
  if (!state.data) {
    return;
  }

  const rect = canvas.getBoundingClientRect();
  updateTransform(rect.width, rect.height);
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = CONSTANTS.backgroundColor;
  ctx.fillRect(0, 0, rect.width, rect.height);

  drawTerrainUnderlay();
  drawZeroAxes();
  drawCurrentRoute();
  drawMetroLines();
  if (showFrontierInput.checked && !state.currentRoute) {
    drawFrontierHighlights();
  }
  if (showAlignmentInput.checked) {
    drawAlignmentReminders();
  }
  drawStations();
  positionInfoPopup();
}

function loadTerrainImage() {
  const image = new Image();
  image.onload = () => {
    state.terrain.image = image;
    state.terrain.loaded = true;
    render();
  };
  image.src = 'assets/blackport_topdown.png';
}

function drawTerrainUnderlay() {
  if (!showWorldMapInput.checked || !state.terrain.loaded || !state.terrain.image) {
    return;
  }
  const { centerX, centerZ, radius, image } = state.terrain;
  const first = plotToCanvas({ x: centerX - radius, y: -(centerZ - radius) });
  const second = plotToCanvas({ x: centerX + radius, y: -(centerZ + radius) });
  const left = Math.min(first.x, second.x);
  const right = Math.max(first.x, second.x);
  const top = Math.min(first.y, second.y);
  const bottom = Math.max(first.y, second.y);
  if (right <= left || bottom <= top) {
    return;
  }
  ctx.save();
  ctx.globalAlpha = CONSTANTS.worldMapAlpha;
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(image, left, top, right - left, bottom - top);
  ctx.restore();
}

function drawZeroAxes() {
  const { minX, maxX, minY, maxY } = state.transform;
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
    ctx.strokeStyle = colorForLine(segment.lineName);
    ctx.lineWidth = segment.connected ? CONSTANTS.connectedWidth : CONSTANTS.unconnectedWidth;
    ctx.setLineDash(segment.connected ? [] : CONSTANTS.unconnectedDash);
    drawPlotPolyline(segment.points);
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

function drawFrontierHighlights() {
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const segment of frontierSegments()) {
    ctx.strokeStyle = CONSTANTS.frontierOutline;
    ctx.lineWidth = CONSTANTS.frontierOutlineWidth;
    ctx.setLineDash([]);
    drawPlotPolyline(segment.points);
    ctx.strokeStyle = colorForLine(segment.lineName);
    ctx.lineWidth = CONSTANTS.frontierWidth;
    drawPlotPolyline(segment.points);
  }
  ctx.restore();
}

function drawAlignmentReminders() {
  const reminders = state.data.alignment_reminders || [];
  ctx.save();
  ctx.strokeStyle = CONSTANTS.alignmentOutline;
  ctx.fillStyle = CONSTANTS.alignmentOutline;
  ctx.lineWidth = CONSTANTS.alignmentWidth;
  ctx.font = `${CONSTANTS.alignmentLabelSize}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  ctx.setLineDash([8, 4]);
  for (const reminder of reminders) {
    const stops = alignmentReminderStops(reminder);
    if (stops.length < 2 || reminderIsAligned(reminder, stops)) {
      continue;
    }
    const points = stops.map(stationPlotPoint).map(plotToCanvas);
    const xs = points.map((point) => point.x);
    const ys = points.map((point) => point.y);
    const padding = Math.max(CONSTANTS.alignmentPadding, Math.round(CONSTANTS.alignmentPadding * state.viewport.zoom));
    let left = Math.min(...xs) - padding;
    let right = Math.max(...xs) + padding;
    let top = Math.min(...ys) - padding;
    let bottom = Math.max(...ys) + padding;
    if (right - left < CONSTANTS.alignmentMinSize) {
      const center = (left + right) / 2;
      left = center - CONSTANTS.alignmentMinSize / 2;
      right = center + CONSTANTS.alignmentMinSize / 2;
    }
    if (bottom - top < CONSTANTS.alignmentMinSize) {
      const center = (top + bottom) / 2;
      top = center - CONSTANTS.alignmentMinSize / 2;
      bottom = center + CONSTANTS.alignmentMinSize / 2;
    }
    drawEllipse(left, top, right, bottom);
    ctx.fillText(`${reminder.axis}: ${stops.map((stop) => displayLabel(stop.lbl)).join(', ')}`, (left + right) / 2, Math.max(CONSTANTS.alignmentLabelSize + 2, top - 4));
  }
  ctx.restore();
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
      drawRotatedLabel(displayLabel(stop.lbl), point.x + labelOffset(), point.y - labelOffset(), fill, labelFontSize, false);
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

function drawEllipse(left, top, right, bottom) {
  ctx.beginPath();
  ctx.ellipse((left + right) / 2, (top + bottom) / 2, (right - left) / 2, (bottom - top) / 2, 0, 0, Math.PI * 2);
  ctx.stroke();
}

function drawRotatedLabel(text, x, y, fill, fontSize, bold) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(CONSTANTS.labelAngle);
  ctx.fillStyle = fill;
  ctx.font = `${bold ? '700 ' : ''}${fontSize}px Helvetica, Arial, sans-serif`;
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

function selectStop(stop, options = {}) {
  state.selectedStop = stop;
  if (options.pan) {
    centerOnPlotPoint(stationPlotPoint(stop));
  }
  if (options.updateRouteStart && !routeStartInput.value.trim()) {
    routeStartInput.value = displayLabel(stop.lbl);
  }
  updateInfoPopup();
  render();
}

function clearSelection() {
  state.selectedStop = null;
  state.searchMatches = [];
  searchInput.value = '';
  refreshSearch();
  hidePopup();
  render();
}

function updateInfoPopup() {
  if (!state.selectedStop) {
    hidePopup();
    return;
  }
  const stop = state.selectedStop;
  const reminders = (state.data.alignment_reminders || []).filter(
    (reminder) => reminder.first_var === stop.var || reminder.second_var === stop.var,
  );
  const checks = [
    ['Has Name', Boolean(stop.lbl.trim())],
    ['Facade', stop.has_connector],
    ['Station', stop.has_full_station],
    ['Connected', stop.is_connected],
    ['Finished Railway', stop.has_finished_railway],
    ['Signs', stop.has_signs],
  ];
  const chimeText = stop.is_connected && stop.chime_directions?.length
    ? `<p class="section-label">Chimes</p><p>${stop.chime_directions.map(capitalize).join(', ')}</p>`
    : '';
  const reminderText = reminders.length
    ? `<p class="section-label">Alignment Reminders</p><p>${reminders.map((reminder) => escapeHtml(reminderDebugLabel(reminder))).join('<br>')}</p>`
    : '';
  infoPopup.innerHTML = `
    <h2>${escapeHtml(displayLabel(stop.lbl))}</h2>
    <p>Coords: (${stop.x}, ${stop.y})<br>Lines: ${escapeHtml(linesForStop(stop).join(', '))}<br>Progress: ${stationCheckpointCount(stop)}/${stationCheckpointTotal(stop)}<br>Alignments: ${reminders.length ? `${reminders.length} active` : 'none'}</p>
    <div class="readonly-checks">
      ${checks.map(([label, checked]) => `<label><input type="checkbox" ${checked ? 'checked' : ''} disabled><span>${label}</span></label>`).join('')}
    </div>
    ${chimeText}
    ${reminderText}
  `;
  infoPopup.hidden = false;
  positionInfoPopup();
}

function positionInfoPopup() {
  if (!state.selectedStop || infoPopup.hidden) {
    return;
  }
  const point = plotToCanvas(stationPlotPoint(state.selectedStop));
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
  const route = findRoute(start.var, end.var, {
    allowMetro: useMetroInput.checked,
    allowFlying: useFlyingInput.checked,
  });
  state.currentRoute = route;
  if (!route) {
    routeSummary.textContent = `No route from ${displayLabel(start.lbl)} to ${displayLabel(end.lbl)}.`;
    routeSteps.textContent = 'No route exists for those endpoints with the current metro data.';
  } else {
    routeStartInput.value = displayLabel(start.lbl);
    routeEndInput.value = displayLabel(end.lbl);
    routeSummary.textContent = `${displayLabel(start.lbl)} to ${displayLabel(end.lbl)}\n${formatTrackDistance(route.totalDistance)}, ${route.totalInterchanges} interchange(s)`;
    routeSteps.textContent = routeInstructions(route);
  }
  render();
}

function refreshRouteIfNeeded() {
  if (state.routeRequest) {
    planRoute();
  }
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
  routeStartInput.value = '';
  routeEndInput.value = '';
  routeSummary.textContent = 'Choose two stations.';
  routeSteps.textContent = 'Enter or select a start and destination, then press Route.';
  render();
}

function findRoute(startVar, endVar, options) {
  if (startVar === endVar) {
    return { startVar, endVar, totalDistance: 0, totalInterchanges: 0, steps: [] };
  }
  const metroRoute = options.allowMetro ? findMetroRoute(startVar, endVar) : null;
  const flyRoute = options.allowFlying ? directFlyRoute(startVar, endVar) : null;
  if (!metroRoute) {
    return flyRoute;
  }
  if (!flyRoute) {
    return metroRoute;
  }
  return [metroRoute, flyRoute].sort((a, b) => (
    a.totalDistance - b.totalDistance ||
    a.totalInterchanges - b.totalInterchanges ||
    a.steps.length - b.steps.length
  ))[0];
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
    if (!stop.is_connected) {
      continue;
    }
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
    const start = state.stopsByVar.get(segment.startVar);
    const end = state.stopsByVar.get(segment.endVar);
    if (!start?.is_connected || !end?.is_connected) {
      continue;
    }
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

function directFlyRoute(startVar, endVar) {
  const start = state.stopsByVar.get(startVar);
  const end = state.stopsByVar.get(endVar);
  if (!start || !end) {
    return null;
  }
  return {
    startVar,
    endVar,
    totalDistance: Math.round(Math.hypot(end.x - start.x, end.y - start.y)),
    totalInterchanges: 0,
    steps: [{
      kind: 'fly',
      startVar,
      endVar,
      distance: Math.round(Math.hypot(end.x - start.x, end.y - start.y)),
      lineName: null,
      stopVars: [startVar, endVar],
      pathPoints: [stationPlotPoint(start), stationPlotPoint(end)],
    }],
  };
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
    } else if (step.kind === 'fly') {
      lines.push(`${index + 1}. Fly directly from ${startLabel} to ${endLabel} for ${formatTrackDistance(step.distance)}.`);
    }
  });
  lines.push('');
  lines.push(`Route from ${displayLabel(start.lbl)} to ${displayLabel(end.lbl)}.`);
  return lines.join('\n');
}

function stationPlotPoint(stop) {
  return { x: stop.x, y: -stop.y };
}

function plotToBaseCanvas(point) {
  const { minX, minY, height, scale } = state.transform;
  return {
    x: CONSTANTS.padding + ((point.x - minX) * scale),
    y: height - CONSTANTS.padding - ((point.y - minY) * scale),
  };
}

function plotToCanvas(point) {
  const base = plotToBaseCanvas(point);
  const { width, height } = state.transform;
  return {
    x: (width / 2) + ((base.x - (width / 2)) * state.viewport.zoom) + state.viewport.panX,
    y: (height / 2) + ((base.y - (height / 2)) * state.viewport.zoom) + state.viewport.panY,
  };
}

function canvasToPlot(x, y) {
  const { width, height, minX, minY, scale } = state.transform;
  const baseX = (width / 2) + ((x - (width / 2) - state.viewport.panX) / state.viewport.zoom);
  const baseY = (height / 2) + ((y - (height / 2) - state.viewport.panY) / state.viewport.zoom);
  return {
    x: minX + ((baseX - CONSTANTS.padding) / scale),
    y: minY + ((height - CONSTANTS.padding - baseY) / scale),
  };
}

function centerOnPlotPoint(point) {
  const base = plotToBaseCanvas(point);
  const { width, height } = state.transform;
  state.viewport.panX = -((base.x - (width / 2)) * state.viewport.zoom);
  state.viewport.panY = -((base.y - (height / 2)) * state.viewport.zoom);
  hidePopup();
}

function zoomAt(anchorX, anchorY, factor) {
  const oldZoom = state.viewport.zoom;
  const newZoom = Math.max(CONSTANTS.defaultZoom, Math.min(oldZoom * factor, maxZoom()));
  if (newZoom === oldZoom) {
    return;
  }
  const { width, height } = state.transform;
  const ratio = newZoom / oldZoom;
  state.viewport.panX = anchorX - (width / 2) - ((anchorX - (width / 2) - state.viewport.panX) * ratio);
  state.viewport.panY = anchorY - (height / 2) - ((anchorY - (height / 2) - state.viewport.panY) * ratio);
  state.viewport.zoom = newZoom;
  hidePopup();
  render();
}

function maxZoom() {
  const { width, height, scale } = state.transform;
  const visibleWidth = Math.max(width - (CONSTANTS.padding * 2), 1) / scale;
  const visibleHeight = Math.max(height - (CONSTANTS.padding * 2), 1) / scale;
  return Math.max(CONSTANTS.defaultZoom, Math.max(visibleWidth, visibleHeight) / CONSTANTS.maxVisibleBlocksAtMaxZoom);
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
  if (step.kind === 'fly') {
    return '#8ad4ff';
  }
  return CONSTANTS.routeOutline;
}

function frontierSegments() {
  const segments = [];
  for (const [lineName, stopVars] of Object.entries(state.data.line_stop_vars)) {
    for (let index = 0; index < stopVars.length - 1; index += 1) {
      const first = state.stopsByVar.get(stopVars[index]);
      const second = state.stopsByVar.get(stopVars[index + 1]);
      if (!first || !second) {
        continue;
      }
      if (first.is_connected !== second.is_connected) {
        const segment = state.lineSegments.find((candidate) => (
          candidate.lineName === lineName &&
          candidate.startVar === first.var &&
          candidate.endVar === second.var
        ));
        if (segment) {
          segments.push(segment);
        }
      }
    }
  }
  return segments;
}

function alignmentReminderStops(reminder) {
  const first = state.stopsByVar.get(reminder.first_var);
  const second = state.stopsByVar.get(reminder.second_var);
  if (!first || !second) {
    return [];
  }
  const sharedLines = linesForStop(first).filter((lineName) => linesForStop(second).includes(lineName));
  const ordered = [];
  const seen = new Set();
  for (const lineName of sharedLines) {
    const stopVars = state.data.line_stop_vars[lineName] || [];
    const firstIndex = stopVars.indexOf(first.var);
    const secondIndex = stopVars.indexOf(second.var);
    if (firstIndex < 0 || secondIndex < 0) {
      continue;
    }
    const low = Math.min(firstIndex, secondIndex);
    const high = Math.max(firstIndex, secondIndex);
    for (const stopVar of stopVars.slice(low, high + 1)) {
      if (!seen.has(stopVar)) {
        ordered.push(state.stopsByVar.get(stopVar));
        seen.add(stopVar);
      }
    }
  }
  return ordered.length ? ordered.filter(Boolean) : [first, second];
}

function reminderIsAligned(reminder, stops) {
  if (reminder.axis === 'x') {
    return new Set(stops.map((stop) => stop.x)).size === 1;
  }
  if (reminder.axis === 'y') {
    return new Set(stops.map((stop) => stop.y)).size === 1;
  }
  return false;
}

function reminderDebugLabel(reminder) {
  return `${reminder.axis}: ${alignmentReminderStops(reminder).map((stop) => displayLabel(stop.lbl)).join(', ')}`;
}

function labelFontSizeForZoom() {
  if (state.viewport.zoom <= CONSTANTS.defaultZoom) {
    return CONSTANTS.baseLabelFontSize;
  }
  const growthSteps = Math.log(state.viewport.zoom) / Math.log(CONSTANTS.zoomStep);
  const growth = Math.min(14, Math.round(growthSteps * 0.3));
  return CONSTANTS.baseLabelFontSize + growth;
}

function labelOffset() {
  return 7 + (labelFontSizeForZoom() - CONSTANTS.baseLabelFontSize);
}

function stationProgressSummary() {
  const stops = state.data.stops;
  const connectedStops = stops.filter((stop) => stop.is_connected);
  const total = stops.length;
  const connectedTotal = connectedStops.length || 1;
  const requiredChimes = connectedStops.reduce((totalChimes, stop) => totalChimes + maxChimeCount(stop), 0);
  const completedChimes = connectedStops.reduce((totalChimes, stop) => totalChimes + completedChimeCount(stop), 0);
  return [
    `Named: ${stops.filter((stop) => stop.lbl.trim()).length}/${total}`,
    `Facades: ${stops.filter((stop) => stop.has_connector).length}/${total}`,
    `Stations: ${stops.filter((stop) => stop.has_full_station).length}/${total}`,
    `Connected: ${stops.filter((stop) => stop.is_connected).length}/${total}`,
    `Finished Railway: ${connectedStops.filter((stop) => stop.has_finished_railway).length}/${connectedTotal}`,
    `Signs: ${connectedStops.filter((stop) => stop.has_signs).length}/${connectedTotal}`,
    `Chimes: ${completedChimes}/${requiredChimes}`,
  ].join('\n');
}

function stationCheckpointTotal(stop) {
  let total = 4;
  if (stop.is_connected) {
    total += 2;
  }
  if (stop.is_connected && maxChimeCount(stop) > 0) {
    total += 1;
  }
  return total;
}

function stationCheckpointCount(stop) {
  let count = 0;
  if (stop.lbl.trim()) count += 1;
  if (stop.has_connector) count += 1;
  if (stop.has_full_station) count += 1;
  if (stop.is_connected) count += 1;
  if (stop.is_connected && stop.has_finished_railway) count += 1;
  if (stop.is_connected && stop.has_signs) count += 1;
  if (stop.is_connected && maxChimeCount(stop) > 0 && completedChimeCount(stop) >= maxChimeCount(stop)) {
    count += 1;
  }
  return count;
}

function maxChimeCount(stop) {
  return stop.is_connected ? linesForStop(stop).length : 0;
}

function completedChimeCount(stop) {
  return Array.isArray(stop.chime_directions) ? stop.chime_directions.length : 0;
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
