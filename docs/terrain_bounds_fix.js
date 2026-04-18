(function () {
  const FALLBACK_CENTER_X = 294;
  const FALLBACK_CENTER_Z = 390;
  const FALLBACK_RADIUS_Z = 2000;
  const METADATA_URLS = [
    'assets/blackport_topdown.bounds.json',
    'assets/world_map_bounds.json',
    'assets/blackport_topdown.render.json',
  ];

  function normalizeBounds(payload) {
    if (!payload || typeof payload !== 'object') {
      return null;
    }

    const direct = readBounds(payload);
    if (direct) {
      return direct;
    }

    if (payload.render_bounds && typeof payload.render_bounds === 'object') {
      const renderBounds = readBounds(payload.render_bounds);
      if (renderBounds) {
        return renderBounds;
      }
    }

    if (payload.colored_bounds && typeof payload.colored_bounds === 'object') {
      const coloredBounds = readBounds(payload.colored_bounds);
      if (coloredBounds) {
        return coloredBounds;
      }
    }

    return null;
  }

  function readBounds(source) {
    const minX = numberValue(source.min_x);
    const maxX = numberValue(source.max_x);
    const minZ = numberValue(source.min_z);
    const maxZ = numberValue(source.max_z);
    if (
      minX === null ||
      maxX === null ||
      minZ === null ||
      maxZ === null ||
      minX >= maxX ||
      minZ >= maxZ
    ) {
      return null;
    }
    return {
      minX,
      maxX,
      minZ,
      maxZ,
      source: 'metadata',
    };
  }

  function numberValue(value) {
    return Number.isFinite(Number(value)) ? Number(value) : null;
  }

  function fallbackBounds() {
    const image = state?.terrain?.image;
    const imageWidth = image?.naturalWidth || image?.width || 1;
    const imageHeight = image?.naturalHeight || image?.height || 1;

    const worldHeight = FALLBACK_RADIUS_Z * 2;
    const aspect =
      imageWidth > 1 && imageHeight > 1
        ? (imageWidth - 1) / (imageHeight - 1)
        : 1;

    const worldWidth = worldHeight * aspect;

    return {
      minX: FALLBACK_CENTER_X - (worldWidth / 2),
      maxX: FALLBACK_CENTER_X + (worldWidth / 2),
      minZ: FALLBACK_CENTER_Z - FALLBACK_RADIUS_Z,
      maxZ: FALLBACK_CENTER_Z + FALLBACK_RADIUS_Z,
      source: 'aspect-fallback',
    };
  }

  function setTerrainBounds(bounds) {
    if (!state.terrain) {
      state.terrain = {};
    }
    state.terrain.bounds = bounds;
  }

  function currentTerrainBounds() {
    return state?.terrain?.bounds || fallbackBounds();
  }

  async function loadTerrainBoundsMetadata() {
    for (const url of METADATA_URLS) {
      try {
        const response = await fetch(`${url}?v=${Date.now()}`, { cache: 'no-cache' });
        if (!response.ok) {
          continue;
        }
        const payload = await response.json();
        const bounds = normalizeBounds(payload);
        if (!bounds) {
          continue;
        }
        setTerrainBounds(bounds);
        if (typeof render === 'function') {
          render();
        }
        return;
      } catch (_error) {
        // Keep trying the next metadata path.
      }
    }

    if (state?.terrain?.image) {
      setTerrainBounds(fallbackBounds());
      if (typeof render === 'function') {
        render();
      }
    }
  }

  function refreshFallbackBoundsIfNeeded() {
    const bounds = state?.terrain?.bounds;
    if (bounds && bounds.source === 'metadata') {
      return;
    }
    if (!state?.terrain?.image) {
      return;
    }
    setTerrainBounds(fallbackBounds());
    if (typeof render === 'function') {
      render();
    }
  }

  drawTerrainUnderlay = function drawTerrainUnderlayWithWorldBounds() {
    if (!showWorldMapInput.checked || !state.terrain.loaded || !state.terrain.image) {
      return;
    }

    const image = state.terrain.image;
    const bounds = currentTerrainBounds();

    const first = plotToCanvas({ x: bounds.minX, y: -bounds.minZ });
    const second = plotToCanvas({ x: bounds.maxX, y: -bounds.maxZ });

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
  };

  loadTerrainBoundsMetadata();

  const waitForImage = window.setInterval(() => {
    if (!state?.terrain?.image || !state.terrain.loaded) {
      return;
    }
    window.clearInterval(waitForImage);
    refreshFallbackBoundsIfNeeded();
  }, 50);
})();
