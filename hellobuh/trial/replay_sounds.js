// Extracts what the audio rebuild needs from a ReplayMod .tmcpr:
//   sounds: server sound packets {t, id, category, x, y, z, volume, pitch, seed}
//   track:  the POV player's position {t, x, y, z, onGround}
//   blocks: block changes {t, x, y, z, state}
// usage: node replay_sounds.js recording.tmcpr > events.json
const fs = require('fs')
const mcp = require('minecraft-protocol')
const buf = fs.readFileSync(process.argv[2])
const meta = JSON.parse(fs.readFileSync(require('path').join(require('path').dirname(process.argv[2]), 'metaData.json')))
const des = {}
const get = (s) => des[s] || (des[s] = mcp.createDeserializer({ state: s, isServer: false, version: meta.mcversion }))
let state = 'login', self = null, selfUuid = (meta.players || [])[0]
const pos = {}, sounds = [], track = [], blocks = []
const num = (v) => typeof v === 'bigint' ? Number(v) : v
for (let i = 0; i < buf.length;) {
  const t = buf.readInt32BE(i), len = buf.readInt32BE(i + 4)
  const pkt = buf.subarray(i + 8, i + 8 + len); i += 8 + len
  let p
  try { p = get(state).parsePacketBuffer(pkt).data } catch (e) { continue }
  const d = p.params
  if (state === 'login' && p.name === 'success') { state = 'configuration'; continue }
  if (state === 'configuration' && p.name === 'finish_configuration') { state = 'play'; continue }
  if (state !== 'play') continue
  switch (p.name) {
    case 'spawn_entity':
      pos[d.entityId] = { x: d.x, y: d.y, z: d.z }
      if (selfUuid && d.objectUUID && d.objectUUID.replace(/-/g, '') === selfUuid.replace(/-/g, '')) self = d.entityId
      break
    case 'rel_entity_move': case 'entity_move_look': {
      const e = pos[d.entityId]; if (!e) break
      e.x += d.dX / 4096; e.y += d.dY / 4096; e.z += d.dZ / 4096
      if (d.entityId === self) track.push({ t, ...e, onGround: d.onGround })
      break
    }
    case 'sync_entity_position': case 'entity_teleport': {
      pos[d.entityId] = { x: d.x, y: d.y, z: d.z }
      if (d.entityId === self) track.push({ t, x: d.x, y: d.y, z: d.z, onGround: d.onGround })
      break
    }
    case 'sound_effect':
      sounds.push({ t, id: d.sound.soundId, category: d.soundCategory, x: d.x / 8, y: d.y / 8, z: d.z / 8, volume: d.volume, pitch: d.pitch, seed: num(d.seed?.[0] ?? 0) })
      break
    case 'entity_sound_effect':
      sounds.push({ t, id: d.sound.soundId, category: d.soundCategory, entity: d.entityId, volume: d.volume, pitch: d.pitch, seed: 0 })
      break
    case 'block_change':
      blocks.push({ t, ...d.location, state: d.type })
      break
    case 'multi_block_change':
      for (const r of d.records || []) {
        const v = BigInt(r), st = Number(v >> 12n)
        const cx = d.chunkCoordinates.x * 16, cy = d.chunkCoordinates.y * 16, cz = d.chunkCoordinates.z * 16
        blocks.push({ t, x: cx + Number((v >> 8n) & 15n), y: cy + Number(v & 15n), z: cz + Number((v >> 4n) & 15n), state: st })
      }
      break
  }
}
console.log(JSON.stringify({ duration: meta.duration, self, sounds, track, blocks }, (k, v) => typeof v === 'bigint' ? Number(v) : v))
