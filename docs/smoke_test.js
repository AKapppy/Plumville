const fs = require('node:fs');
const path = require('node:path');

const docsDir = __dirname;
const repoRoot = path.resolve(docsDir, '..');
const indexHtml = fs.readFileSync(path.join(docsDir, 'index.html'), 'utf8');
const appJs = fs.readFileSync(path.join(docsDir, 'app.js'), 'utf8');
const network = JSON.parse(fs.readFileSync(path.join(docsDir, 'metro_network.json'), 'utf8'));
const terrainMetadata = JSON.parse(fs.readFileSync(path.join(docsDir, 'assets', 'blackport_topdown.render.json'), 'utf8'));
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
assert(appJs.includes("fetch('metro_network.json'"), 'app.js no longer fetches metro_network.json.');
assert(appJs.includes('new Image()'), 'app.js no longer loads the terrain image.');
assert(appJs.includes('function fitRenderedMap'), 'app.js is missing fitRenderedMap().');
assert(Array.isArray(network.stops) && network.stops.length > 0, 'metro_network.json has no stops.');
assert(network.line_stop_vars && Object.keys(network.line_stop_vars).length > 0, 'metro_network.json has no line data.');

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
