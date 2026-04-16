const canvas = document.querySelector('#metroCanvas');
const ctx = canvas.getContext('2d');
const tooltip = document.querySelector('#tooltip');
const summaryText = document.querySelector('#summaryText');
const searchInput = document.querySelector('#searchInput');
const resetViewButton = document.querySelector('#resetViewButton');
const showAllButton = document.querySelector('#showAllButton');
const clearSelectionButton = document.querySelector('#clearSelectionButton');
const detailsTitle = document.querySelector('#detailsTitle');
const detailsBody = document.querySelector('#detailsBody');
const lineFilters = document.querySelector('#lineFilters');
const visibleLineCount = document.querySelector('#visibleLineCount');

const state = {
  data: null,
  stopsByVar: new Map(),
  stopLines: new Map(),
  linePaths: new Map(),
  lineSegments: [],
  visibleLines: new Set(),
  selectedStop: null,
  hoverStop: null,
  searchMatches: new Set(),
  terrain: {
    image: null,
    loaded: false,
    centerX: 294,
    centerY: 390,
    radius: 2000,
  },
  view: { scale: 0.2, offsetX: 0, offsetY: 0 },
  bounds: null,
  dragging: false,
  lastPointer: null,
};

const stopRadius = 9;
const stationHitRadius = 14;

init();

async function init() {
  try {
    loadTerrainImage();
    const response = await fetch('metro_network.json', { cache: 'no-cache' });
    if (!response.ok) {
      throw new Error(`Could not load metro_network.json: ${response.status}`);
    }
    const data = await response.json();
    hydrateNetwork(data);
    buildLineControls();
    bindEvents();
    resizeCanvas();
    resetView();
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
  state.linePaths = new Map();
  state.lineSegments = [];

  for (const [lineName, stopVars] of Object.entries(data.line_stop_vars)) {
    for (const stopVar of stopVars) {
      state.stopLines.get(stopVar)?.push(lineName);
    }

    const specs = data.line_path_specs[lineName] || [];
    const points = specs.map(pointFromSpec).filter(Boolean);
    state.linePaths.set(lineName, points);
    state.lineSegments.push(...segmentsForLine(lineName, stopVars, specs));
  }

  const bounds = boundsForPoints([
    ...data.stops.map((stop) => ({ x: stop.x, y: stop.y })),
    ...[...state.linePaths.values()].flat(),
  ]);
  state.bounds = padBounds(bounds, 220);

  const finished = data.stops.filter((stop) => stop.has_finished_railway).length;
  summaryText.textContent = `${data.stops.length} stations, ${state.visibleLines.size} lines, ${finished} finished railway stops.`;
}

function pointFromSpec(spec) {
  const xStop = state.stopsByVar.get(spec.x_var);
  const yStop = state.stopsByVar.get(spec.y_var);
  if (!xStop || !yStop) {
    return null;
  }
  return {
    x: xStop.x + Number(spec.dx || 0),
    y: yStop.y + Number(spec.dy || 0),
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
    const complete = Boolean(
      startStop?.is_connected &&
      endStop?.is_connected &&
      startStop?.has_finished_railway &&
      endStop?.has_finished_railway,
    );

    segments.push({ lineName, startVar, endVar, points, complete });
  }
  return segments;
}

function buildLineControls() {
  lineFilters.innerHTML = '';
  const names = Object.keys(state.data.line_stop_vars).sort();
  for (const lineName of names) {
    const label = document.createElement('label');
    label.className = 'line-toggle';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = true;
    checkbox.dataset.line = lineName;
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        state.visibleLines.add(lineName);
      } else {
        state.visibleLines.delete(lineName);
      }
      updateVisibleLineCount();
      render();
    });

    const name = document.createElement('span');
    name.className = 'line-name';
    name.textContent = `Line ${lineName}`;

    const swatch = document.createElement('span');
    swatch.className = 'line-swatch';
    swatch.style.background = colorForLine(lineName);

    label.append(checkbox, name, swatch);
    lineFilters.append(label);
  }
  updateVisibleLineCount();
}

function bindEvents() {
  window.addEventListener('resize', () => {
    resizeCanvas();
    render();
  });

  canvas.addEventListener('pointerdown', (event) => {
    canvas.setPointerCapture(event.pointerId);
    state.dragging = true;
    state.lastPointer = { x: event.clientX, y: event.clientY };
    canvas.classList.add('dragging');
  });

  canvas.addEventListener('pointermove', (event) => {
    if (state.dragging && state.lastPointer) {
      const dx = event.clientX - state.lastPointer.x;
      const dy = event.clientY - state.lastPointer.y;
      state.view.offsetX += dx;
      state.view.offsetY += dy;
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
    const stop = findStopAt(event.offsetX, event.offsetY);
    if (stop) {
      selectStop(stop);
    }
  });

  canvas.addEventListener('pointerleave', () => {
    state.hoverStop = null;
    tooltip.hidden = true;
    render();
  });

  canvas.addEventListener('wheel', (event) => {
    event.preventDefault();
    const factor = event.deltaY > 0 ? 0.9 : 1.1;
    zoomAt(event.offsetX, event.offsetY, factor);
  }, { passive: false });

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.trim().toLowerCase();
    state.searchMatches.clear();
    if (query) {
      for (const stop of state.data.stops) {
        if (stop.lbl.toLowerCase().includes(query) || stop.var.toLowerCase().includes(query)) {
          state.searchMatches.add(stop.var);
        }
      }
      const firstMatch = state.data.stops.find((stop) => state.searchMatches.has(stop.var));
      if (firstMatch) {
        selectStop(firstMatch, { pan: true });
      }
    }
    render();
  });

  resetViewButton.addEventListener('click', () => {
    resetView();
    render();
  });

  showAllButton.addEventListener('click', () => {
    state.visibleLines = new Set(Object.keys(state.data.line_stop_vars));
    for (const checkbox of lineFilters.querySelectorAll('input')) {
      checkbox.checked = true;
    }
    updateVisibleLineCount();
    render();
  });

  clearSelectionButton.addEventListener('click', () => {
    state.selectedStop = null;
    state.searchMatches.clear();
    searchInput.value = '';
    detailsTitle.textContent = 'Select a station';
    detailsBody.textContent = 'Click any stop on the map to see its coordinates, served lines, and completion status.';
    render();
  });
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * pixelRatio));
  canvas.height = Math.max(1, Math.round(rect.height * pixelRatio));
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
}

function resetView() {
  if (!state.bounds) {
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const worldWidth = state.bounds.maxX - state.bounds.minX;
  const worldHeight = state.bounds.maxY - state.bounds.minY;
  const scale = Math.min(rect.width / worldWidth, rect.height / worldHeight);
  state.view.scale = Math.max(0.08, Math.min(0.8, scale));
  const center = {
    x: (state.bounds.minX + state.bounds.maxX) / 2,
    y: (state.bounds.minY + state.bounds.maxY) / 2,
  };
  state.view.offsetX = rect.width / 2 - center.x * state.view.scale;
  state.view.offsetY = rect.height / 2 - center.y * state.view.scale;
}

function render() {
  if (!state.data) {
    return;
  }

  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);

  drawTerrainUnderlay();
  drawWorldGrid(rect);
  drawLines();
  drawAlignmentReminders();
  drawStations();
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
  if (!state.terrain.loaded || !state.terrain.image) {
    return;
  }

  const { centerX, centerY, radius, image } = state.terrain;
  const topLeft = worldToScreen(centerX - radius, centerY - radius);
  const bottomRight = worldToScreen(centerX + radius, centerY + radius);

  ctx.save();
  ctx.globalAlpha = 0.72;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(
    image,
    topLeft.x,
    topLeft.y,
    bottomRight.x - topLeft.x,
    bottomRight.y - topLeft.y,
  );
  ctx.restore();
}

function drawWorldGrid(rect) {
  const gridSize = 500;
  const topLeft = screenToWorld(0, 0);
  const bottomRight = screenToWorld(rect.width, rect.height);

  ctx.save();
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(21, 32, 29, 0.12)';
  ctx.fillStyle = 'rgba(21, 32, 29, 0.48)';
  ctx.font = '12px system-ui, sans-serif';

  const minX = Math.floor(topLeft.x / gridSize) * gridSize;
  const maxX = Math.ceil(bottomRight.x / gridSize) * gridSize;
  const minY = Math.floor(topLeft.y / gridSize) * gridSize;
  const maxY = Math.ceil(bottomRight.y / gridSize) * gridSize;

  for (let x = minX; x <= maxX; x += gridSize) {
    const screen = worldToScreen(x, 0);
    ctx.beginPath();
    ctx.moveTo(screen.x, 0);
    ctx.lineTo(screen.x, rect.height);
    ctx.stroke();
    if (screen.x > 20 && screen.x < rect.width - 80) {
      ctx.fillText(String(x), screen.x + 5, 18);
    }
  }

  for (let y = minY; y <= maxY; y += gridSize) {
    const screen = worldToScreen(0, y);
    ctx.beginPath();
    ctx.moveTo(0, screen.y);
    ctx.lineTo(rect.width, screen.y);
    ctx.stroke();
    if (screen.y > 34 && screen.y < rect.height - 20) {
      ctx.fillText(String(y), 8, screen.y - 5);
    }
  }
  ctx.restore();
}

function drawLines() {
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  for (const segment of state.lineSegments) {
    if (!state.visibleLines.has(segment.lineName) || segment.points.length < 2) {
      continue;
    }
    ctx.strokeStyle = colorForLine(segment.lineName);
    ctx.lineWidth = segment.complete ? 8 : 5;
    ctx.globalAlpha = segment.complete ? 0.92 : 0.62;
    ctx.setLineDash(segment.complete ? [] : [12, 10]);
    drawPolyline(segment.points);
  }

  ctx.restore();
}

function drawAlignmentReminders() {
  const reminders = state.data.alignment_reminders || [];
  if (!reminders.length) {
    return;
  }

  ctx.save();
  ctx.strokeStyle = 'rgba(216, 47, 92, 0.35)';
  ctx.lineWidth = 2;
  ctx.setLineDash([4, 8]);
  for (const reminder of reminders) {
    const first = state.stopsByVar.get(reminder.first_var);
    const second = state.stopsByVar.get(reminder.second_var);
    if (!first || !second || !stopHasVisibleLine(first) || !stopHasVisibleLine(second)) {
      continue;
    }
    drawPolyline([
      { x: first.x, y: first.y },
      { x: second.x, y: second.y },
    ]);
  }
  ctx.restore();
}

function drawStations() {
  ctx.save();
  ctx.font = '600 13px system-ui, sans-serif';
  ctx.textBaseline = 'middle';

  for (const stop of state.data.stops) {
    if (!stopHasVisibleLine(stop)) {
      continue;
    }

    const point = worldToScreen(stop.x, stop.y);
    const isSelected = state.selectedStop?.var === stop.var;
    const isHover = state.hoverStop?.var === stop.var;
    const isSearch = state.searchMatches.has(stop.var);
    const fill = stationColor(stop);

    ctx.beginPath();
    ctx.arc(point.x, point.y, isSelected || isSearch ? stopRadius + 4 : stopRadius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.lineWidth = isSelected || isHover ? 4 : 2;
    ctx.strokeStyle = isSelected ? '#d82f5c' : '#ffffff';
    ctx.stroke();

    if (!stop.has_finished_railway || !stop.is_connected) {
      ctx.beginPath();
      ctx.arc(point.x, point.y, stopRadius + 7, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(21, 32, 29, 0.26)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    if (state.view.scale > 0.16 || isSelected || isHover || isSearch) {
      ctx.lineWidth = 4;
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.strokeText(stop.lbl, point.x + 14, point.y + 1);
      ctx.fillStyle = '#15201d';
      ctx.fillText(stop.lbl, point.x + 14, point.y + 1);
    }
  }
  ctx.restore();
}

function drawPolyline(points) {
  const first = worldToScreen(points[0].x, points[0].y);
  ctx.beginPath();
  ctx.moveTo(first.x, first.y);
  for (const point of points.slice(1)) {
    const screen = worldToScreen(point.x, point.y);
    ctx.lineTo(screen.x, screen.y);
  }
  ctx.stroke();
}

function updateHover(event) {
  const stop = findStopAt(event.offsetX, event.offsetY);
  state.hoverStop = stop;
  if (stop) {
    const lines = linesForStop(stop);
    tooltip.innerHTML = `<strong>${escapeHtml(stop.lbl)}</strong><span>${stop.x}, ${stop.y} · ${lines.join(', ')}</span>`;
    tooltip.hidden = false;
    tooltip.style.left = `${Math.min(event.offsetX + 16, canvas.clientWidth - 280)}px`;
    tooltip.style.top = `${Math.max(12, event.offsetY - 12)}px`;
  } else {
    tooltip.hidden = true;
  }
  render();
}

function findStopAt(screenX, screenY) {
  let best = null;
  let bestDistance = Infinity;
  for (const stop of state.data.stops) {
    if (!stopHasVisibleLine(stop)) {
      continue;
    }
    const point = worldToScreen(stop.x, stop.y);
    const dx = point.x - screenX;
    const dy = point.y - screenY;
    const distance = Math.hypot(dx, dy);
    if (distance <= stationHitRadius && distance < bestDistance) {
      best = stop;
      bestDistance = distance;
    }
  }
  return best;
}

function selectStop(stop, options = {}) {
  state.selectedStop = stop;
  const lines = linesForStop(stop);
  const status = [
    stop.is_connected ? 'connected' : 'not connected',
    stop.has_full_station ? 'full station' : 'station work pending',
    stop.has_finished_railway ? 'railway finished' : 'railway unfinished',
    stop.has_signs ? 'signs placed' : 'signs pending',
  ];
  detailsTitle.textContent = stop.lbl;
  detailsBody.textContent = `${stop.x}, ${stop.y}. ${lines.join(', ')}. ${status.join('; ')}.`;

  if (options.pan) {
    panTo(stop.x, stop.y);
  }
  render();
}

function panTo(worldX, worldY) {
  const rect = canvas.getBoundingClientRect();
  state.view.offsetX = rect.width / 2 - worldX * state.view.scale;
  state.view.offsetY = rect.height / 2 - worldY * state.view.scale;
}

function zoomAt(screenX, screenY, factor) {
  const before = screenToWorld(screenX, screenY);
  state.view.scale = Math.max(0.06, Math.min(1.8, state.view.scale * factor));
  const after = worldToScreen(before.x, before.y);
  state.view.offsetX += screenX - after.x;
  state.view.offsetY += screenY - after.y;
  render();
}

function worldToScreen(x, y) {
  return {
    x: x * state.view.scale + state.view.offsetX,
    y: y * state.view.scale + state.view.offsetY,
  };
}

function screenToWorld(x, y) {
  return {
    x: (x - state.view.offsetX) / state.view.scale,
    y: (y - state.view.offsetY) / state.view.scale,
  };
}

function stopHasVisibleLine(stop) {
  return linesForStop(stop).some((lineName) => state.visibleLines.has(lineName));
}

function linesForStop(stop) {
  return state.stopLines.get(stop.var) || [];
}

function stationColor(stop) {
  const lines = linesForStop(stop).filter((lineName) => state.visibleLines.has(lineName));
  return lines.length === 1 ? colorForLine(lines[0]) : '#ffffff';
}

function colorForLine(lineName) {
  return state.data.line_colors[lineName] || '#15201d';
}

function updateVisibleLineCount() {
  visibleLineCount.textContent = `${state.visibleLines.size} visible`;
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

function padBounds(bounds, padding) {
  return {
    minX: bounds.minX - padding,
    minY: bounds.minY - padding,
    maxX: bounds.maxX + padding,
    maxY: bounds.maxY + padding,
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
