#!/usr/bin/env node

const fs = require('fs')
const path = require('path')
const { createClient } = require('bedrock-protocol')

const host = process.env.BEDROCK_HOST || '127.0.0.1'
const port = parseInt(process.env.BEDROCK_PORT || '19132', 10)
const username = process.env.BEDROCK_USERNAME || 'MetroChunkLoader'
const version = process.env.BEDROCK_VERSION || '26.10'
const waitMs = parseInt(process.env.BEDROCK_WAIT_MS || '45000', 10)
const chunkRadius = parseInt(process.env.BEDROCK_CHUNK_RADIUS || '12', 10)
const resultFile = process.env.BEDROCK_LOADER_RESULT_FILE || ''
const chunkPacketFile = process.env.BEDROCK_CHUNK_PACKET_FILE || ''
const startGameMetadataFile =
  process.env.BEDROCK_START_GAME_METADATA_FILE ||
  (chunkPacketFile
    ? path.join(path.dirname(chunkPacketFile), 'headless_start_game.json')
    : (resultFile ? path.join(path.dirname(resultFile), 'headless_start_game.json') : ''))
const connectTimeout = parseInt(process.env.BEDROCK_CONNECT_TIMEOUT_MS || '20000', 10)
const raknetBackend = process.env.BEDROCK_RAKNET_BACKEND || 'raknet-node'
const useRaknetWorkers = process.env.BEDROCK_USE_RAKNET_WORKERS !== 'false'

const startedAt = new Date()
const chunkColumns = new Set()
const requestedSubChunks = new Set()
let chunksReceived = 0
let subChunksReceived = 0
let joined = false
let spawned = false
let finished = false
let client = null
let startGameMetadataWritten = false
const warnedFileOperations = new Set()
const retryableFsErrorCodes = new Set(['EAGAIN', 'EDEADLK', 'EBUSY', 'UNKNOWN'])

function isRetryableFsError (err) {
  if (!err) return false
  return retryableFsErrorCodes.has(err.code) || err.errno === -35 || err.errno === 11 || err.errno === -11
}

function sleepSync (ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)
}

function retrySync (operation, attempts = 6, delayMs = 150) {
  let lastError = null
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return operation()
    } catch (err) {
      lastError = err
      if (!isRetryableFsError(err) || attempt === attempts - 1) {
        throw err
      }
      sleepSync(delayMs * (attempt + 1))
    }
  }
  throw lastError
}

function ensureOutputDir (filePath) {
  retrySync(() => fs.mkdirSync(path.dirname(filePath), { recursive: true }))
}

function writeFileWithRetry (filePath, text) {
  ensureOutputDir(filePath)
  retrySync(() => fs.writeFileSync(filePath, text))
}

function appendFileWithRetry (filePath, text) {
  ensureOutputDir(filePath)
  retrySync(() => fs.appendFileSync(filePath, text))
}

function log (message) {
  console.log(`[headless-loader] ${message}`)
}

function warnFileOperationOnce (label, filePath, err) {
  const key = `${label}:${filePath}`
  if (warnedFileOperations.has(key)) return
  warnedFileOperations.add(key)
  console.error(
    `[headless-loader] warning: could not ${label} ${filePath}: ${err && err.message ? err.message : String(err)}`
  )
}

function writeResult (reason, exitCode) {
  if (!resultFile) return
  const payload = {
    generated_at: new Date().toISOString(),
    started_at: startedAt.toISOString(),
    reason,
    exit_code: exitCode,
    host,
    port,
    username,
    version,
    wait_ms: waitMs,
    chunk_radius: chunkRadius,
    raknet_backend: raknetBackend,
    use_raknet_workers: useRaknetWorkers,
    joined,
    spawned,
    chunks_received: chunksReceived,
    unique_chunk_columns: chunkColumns.size,
    subchunks_received: subChunksReceived
  }
  try {
    writeFileWithRetry(resultFile, JSON.stringify(payload, null, 2) + '\n')
  } catch (err) {
    warnFileOperationOnce('write result file', resultFile, err)
  }
}

function appendChunkPacket (record) {
  if (!chunkPacketFile || !record || !record.payload) return
  const payload = Buffer.from(record.payload)
  if (payload.length === 0) return
  const outputRecord = { ...record }
  delete outputRecord.payload
  outputRecord.generated_at = new Date().toISOString()
  outputRecord.payload_base64 = payload.toString('base64')
  try {
    appendFileWithRetry(chunkPacketFile, JSON.stringify(outputRecord) + '\n')
  } catch (err) {
    warnFileOperationOnce('append chunk packet', chunkPacketFile, err)
  }
}

function normalizeBlockName (name) {
  if (!name || typeof name !== 'string') return null
  return name.startsWith('minecraft:') ? name : `minecraft:${name}`
}

function writeStartGameMetadata (packet) {
  if (!startGameMetadataFile || startGameMetadataWritten || !packet) return

  const blockNames = new Set()
  if (Array.isArray(packet.block_properties)) {
    for (const block of packet.block_properties) {
      const blockName = normalizeBlockName(block && block.name)
      if (blockName) blockNames.add(blockName)
    }
  }

  const payload = {
    generated_at: new Date().toISOString(),
    version,
    block_network_ids_are_hashes: packet.block_network_ids_are_hashes === true,
    block_pallette_checksum: packet.block_pallette_checksum ?? null,
    block_properties_count: Array.isArray(packet.block_properties) ? packet.block_properties.length : 0,
    unique_block_names: Array.from(blockNames).sort(),
  }
  try {
    writeFileWithRetry(startGameMetadataFile, JSON.stringify(payload, null, 2) + '\n')
    startGameMetadataWritten = true
  } catch (err) {
    warnFileOperationOnce('write start-game metadata', startGameMetadataFile, err)
  }
}

function cacheLevelChunkPacket (packet) {
  if (!packet || !packet.payload) return
  const payload = Buffer.from(packet.payload)
  if (payload.length === 0) return
  appendChunkPacket({
    type: 'level_chunk',
    x: packet.x,
    z: packet.z,
    dimension: packet.dimension,
    sub_chunk_count: packet.sub_chunk_count,
    highest_subchunk_count: packet.highest_subchunk_count,
    payload
  })
}

function requestSubChunksForLevelChunk (packet) {
  if (!packet || packet.sub_chunk_count !== -2) return
  const chunkKey = `${packet.dimension || 0},${packet.x},${packet.z}`
  if (requestedSubChunks.has(chunkKey)) return
  requestedSubChunks.add(chunkKey)
  const requests = []
  for (let y = -4; y <= 24; y++) {
    requests.push({ dx: 0, dy: y, dz: 0 })
  }
  client.queue('subchunk_request', {
    dimension: packet.dimension || 0,
    origin: { x: packet.x, y: 0, z: packet.z },
    requests
  })
}

function finish (exitCode, reason) {
  if (finished) return
  finished = true
  log(`${reason}; chunks=${chunksReceived}; chunk_columns=${chunkColumns.size}`)
  writeResult(reason, exitCode)
  if (client) {
    try {
      client.disconnect('Headless chunk loader finished.', true)
    } catch (_err) {
      try {
        client.close()
      } catch (_err2) {}
    }
  }
  setTimeout(() => process.exit(exitCode), 500)
}

try {
  log(
    `connecting to ${host}:${port} as ${username} with Bedrock protocol ${version} via ${raknetBackend}` +
    ` (workers=${useRaknetWorkers ? 'yes' : 'no'})`
  )
  client = createClient({
    host,
    port,
    username,
    version,
    offline: true,
    raknetBackend,
    useRaknetWorkers,
    connectTimeout,
    conLog: message => log(String(message)),
  })
  client.viewDistance = chunkRadius
} catch (err) {
  console.error(`[headless-loader] failed to create client: ${err.message}`)
  writeResult(err.message, 1)
  process.exit(1)
}

client.on('join', () => {
  joined = true
  log('joined server')
})

client.on('spawn', () => {
  spawned = true
  log(`spawned; requesting chunk radius ${chunkRadius}`)
  client.queue('request_chunk_radius', { chunk_radius: chunkRadius })
})

client.on('start_game', packet => {
  writeStartGameMetadata(packet)
})

client.on('level_chunk', packet => {
  chunksReceived += 1
  chunkColumns.add(`${packet.x},${packet.z}`)
  cacheLevelChunkPacket(packet)
  requestSubChunksForLevelChunk(packet)
  if (chunksReceived === 1 || chunksReceived % 25 === 0) {
    log(`received ${chunksReceived} chunk packets across ${chunkColumns.size} chunk columns`)
  }
})

client.on('subchunk', packet => {
  if (!packet || !Array.isArray(packet.entries)) return
  const origin = packet.origin || { x: 0, y: 0, z: 0 }
  for (const entry of packet.entries) {
    if (!entry || !entry.payload) continue
    const result = String(entry.result)
    if (result !== 'success' && result !== '1') continue
    subChunksReceived += 1
    appendChunkPacket({
      type: 'subchunk',
      x: origin.x + entry.dx,
      z: origin.z + entry.dz,
      dimension: packet.dimension,
      subchunk_y: origin.y + entry.dy,
      payload: entry.payload
    })
  }
  if (subChunksReceived === 1 || subChunksReceived % 250 === 0) {
    log(`received ${subChunksReceived} subchunk payloads`)
  }
})

client.on('kick', packet => {
  const message = packet && packet.message ? packet.message : 'kicked by server'
  finish(chunksReceived > 0 ? 0 : 1, message)
})

client.on('error', err => {
  finish(1, err && err.message ? err.message : String(err))
})

client.on('close', () => {
  if (!finished) {
    finish(chunksReceived > 0 ? 0 : 2, 'connection closed')
  }
})

setTimeout(() => {
  finish(chunksReceived > 0 ? 0 : 2, 'wait window finished')
}, waitMs)

process.on('SIGTERM', () => finish(143, 'received SIGTERM'))
process.on('SIGINT', () => finish(130, 'received SIGINT'))
process.on('uncaughtException', err => {
  finish(1, err && err.message ? err.message : String(err))
})
process.on('unhandledRejection', err => {
  finish(1, err && err.message ? err.message : String(err))
})
