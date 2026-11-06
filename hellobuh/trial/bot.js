// Scripted MLG-water clutch. Joins the local offline server, builds the set,
// starts a ServerReplay recording of itself, falls off a pillar and places water
// just before landing. Exits 0 if it survived with the clutch, 1 otherwise.
const mineflayer = require('mineflayer')
const { Vec3 } = require('vec3')

const NAME = process.env.BOT_NAME || 'HelloBuh'
const HEIGHT = Number(process.env.FALL_HEIGHT || 60)   // blocks above the floor
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

const bot = mineflayer.createBot({ host: '127.0.0.1', port: Number(process.env.MC_PORT || 25565), username: NAME, auth: 'offline', version: process.env.MC_VERSION || '1.21.11' })
const log = (...a) => console.log(new Date().toISOString().slice(11, 23), ...a)
bot.on('kicked', r => { log('kicked', r); process.exit(2) })
bot.on('error', e => { log('error', e); process.exit(2) })

// Ease the camera instead of snapping, so the recorded POV looks hand-moved.
async function easeLook (yaw, pitch, ms) {
  const y0 = bot.entity.yaw, p0 = bot.entity.pitch, steps = Math.max(1, Math.round(ms / 50))
  let dy = yaw - y0; while (dy > Math.PI) dy -= 2 * Math.PI; while (dy < -Math.PI) dy += 2 * Math.PI
  for (let i = 1; i <= steps; i++) {
    const t = i / steps, e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2
    await bot.look(y0 + dy * e, p0 + (pitch - p0) * e, true)
    await bot.waitForTicks(1)
  }
}
// Timeline for the HUD overlay, in ms since the recording started.
let t0 = null; const timeline = []
const mark = (event, extra = {}) => { if (t0 !== null) timeline.push({ t: Date.now() - t0, event, slot: bot.quickBarSlot, health: bot.health, ...extra }) }
const cmd = async (c) => { bot.chat(c); await bot.waitForTicks(4) }

bot.once('spawn', async () => {
  try {
    log('spawned at', bot.entity.position)
    if (process.env.VIEWER_PORT) {   // optional prismarine-viewer fallback renderer (first person)
      const { mineflayer: viewer } = require(process.env.VIEWER_MODULE || 'prismarine-viewer')
      viewer(bot, { port: Number(process.env.VIEWER_PORT), firstPerson: true, viewDistance: 6 })
    }
    const base = bot.entity.position.floored()
    // FLOOR_Y lets the set float above y=0 (prismarine-viewer can't draw faces below y=0).
    const x = Number(process.env.SET_X || 0), z = Number(process.env.SET_Z || 0), floor = process.env.FLOOR_Y ? Number(process.env.FLOOR_Y) : base.y - 1, top = floor + HEIGHT
    await cmd('/gamemode creative'); await cmd('/time set 6000'); await cmd('/weather clear')
    await cmd('/gamerule doDaylightCycle false'); await cmd('/gamerule doWeatherCycle false')
    await cmd('/gamerule sendCommandFeedback false'); await cmd('/gamerule showDeathMessages true')
    // The set: a grass landing pad ringed with some scenery, a stone pillar to jump from.
    const R = 16   // set radius
    await cmd(`/fill ${x - R} ${floor - 3} ${z - R} ${x + R} ${floor - 1} ${z + R} dirt`)
    await cmd(`/fill ${x - R} ${floor} ${z - R} ${x + R} ${floor} ${z + R} grass_block`)
    // Clear the whole set volume (in slabs: /fill is capped at 32768 blocks per command).
    for (let y0 = floor + 1; y0 <= top + 4; y0 += 30) await cmd(`/fill ${x - R} ${y0} ${z - R} ${x + R} ${Math.min(y0 + 29, top + 4)} ${z + R} air`)
    await cmd(`/fill ${x} ${floor + 1} ${z} ${x} ${top} ${z} cobblestone`)
    const LAYERS = Number(process.env.TOP_LAYERS || 5)   // snow cap: shifts the fall phase by (LAYERS-1)/8 block (snow collision height)
    if (LAYERS > 0) await cmd(`/setblock ${x} ${top + 1} ${z} snow[layers=${LAYERS}]`)
    await cmd(`/fill ${x - 6} ${floor + 1} ${z + 4} ${x - 6} ${floor + 5} ${z + 4} oak_log`)
    await cmd(`/fill ${x - 8} ${floor + 5} ${z + 2} ${x - 4} ${floor + 7} ${z + 6} oak_leaves keep`)
    await cmd(`/clear @s`)
    await cmd(`/item replace entity @s hotbar.0 with diamond_sword`)
    await cmd(`/item replace entity @s hotbar.1 with water_bucket`)
    await cmd(`/item replace entity @s hotbar.2 with cobblestone 64`)
    await cmd(`/item replace entity @s hotbar.3 with bread 16`)
    await cmd(`/effect clear @s`)
    // Teleport onto the pillar and make sure it stuck (the server can reject a stale move
    // packet right after a teleport and snap the bot back down).
    for (let i = 0; ; i++) {
      await cmd(`/tp @s ${x + 0.5} ${top + 1 + Math.max(0, LAYERS - 1) / 8} ${z + 0.5} 0 20`)
      await bot.waitForTicks(20)
      if (Math.abs(bot.entity.position.y - (top + 1 + Math.max(0, LAYERS - 1) / 8)) < 0.1 && bot.entity.onGround) break
      if (i === 4) throw new Error('could not get onto the pillar')
      log('teleport did not stick, retrying')
    }
    await cmd('/gamemode survival'); await cmd('/effect give @s instant_health 1 10 true')
    bot.setQuickBarSlot(0)
    await bot.waitForTicks(30)
    log('on top at', bot.entity.position, 'health', bot.health)

    if (process.env.VIEWER_PORT) {  // wait for the capture browser to load chunks
      const fs = require('fs'); fs.writeFileSync(process.env.READY_FILE || 'ready', '1')
      while (!fs.existsSync(process.env.GO_FILE || 'go')) await sleep(200)
    }
    t0 = Date.now(); mark('start')
    await cmd(`/replay start players ${NAME}`)
    await bot.waitForTicks(30)                     // ~1.5 s of "standing on the pillar"
    await easeLook(0, -1.0, 600)                   // peek over the edge (mineflayer: negative pitch = down)
    await easeLook(0, -0.25, 400)
    bot.setQuickBarSlot(1); mark('slot')           // pull out the water bucket
    await bot.waitForTicks(6)
    // Walk off the +z edge.
    bot.setControlState('forward', true); bot.setControlState('jump', true)
    await bot.waitForTicks(6)
    bot.setControlState('jump', false)
    await bot.waitForTicks(8)
    // Keep drifting forward for most of the fall so we come down a few blocks clear of the
    // pillar (falling right next to it lets the water ray clip the pillar instead of the floor).
    const stopDrift = () => { if (bot.entity.position.y - (floor + 1) < HEIGHT - 14) { bot.setControlState('forward', false); bot.removeListener('physicsTick', stopDrift) } }
    bot.on('physicsTick', stopDrift)
    easeLook(bot.entity.yaw, -Math.PI / 2 + 0.01, 500)   // look straight down while falling
    // Timing (see TRIAL.md): water goes down on the first tick the floor is in reach (eye 1.62 +
    // reach 4.5). With the snow cap the bot is then ~2.6 above the floor, so the NEXT tick ends
    // with its feet inside the water block and the server resets the fall distance before the
    // landing tick. Without the cap it placed at 1.98 and landed the same tick as the placement
    // was processed: a coin flip.
    let placed = false, landed = false
    // Synchronous per-tick check: an awaited loop can miss the single in-reach tick when
    // mineflayer catches up several physics ticks at once under CPU load.
    const onTick = () => {
      const p = bot.entity.position, vy = bot.entity.velocity.y, above = p.y - (floor + 1)
      if (!placed && vy < -0.5 && above + 1.62 < 4.45) {
        bot.setQuickBarSlot(1)
        bot.entity.pitch = -Math.PI / 2
        placed = true; mark('placed', { above })
        // physicsTick fires BEFORE mineflayer sends this tick's position; defer so the server
        // checks reach from where we are now, not from a tick (2.3 blocks) higher.
        process.nextTick(() => bot.activateItem())
        log('water placed at height', above.toFixed(2), 'vy', vy.toFixed(2))
      }
      if (placed && (bot.entity.onGround || bot.entity.isInWater)) landed = true
    }
    bot.on('physicsTick', onTick)
    for (let i = 0; i < 200 && !landed && !died; i++) await bot.waitForTicks(1)
    bot.removeListener('physicsTick', onTick)
    await bot.waitForTicks(8)
    log('landed, health', bot.health, 'in water', bot.entity.isInWater)
    // Scoop the water back up (the flourish).
    const below = bot.blockAt(bot.entity.position.floored())
    if (below && below.name === 'water') { await bot.look(bot.entity.yaw, -Math.PI / 2, true); bot.activateItem(); await bot.waitForTicks(4); mark('scooped', { ok: bot.heldItem && bot.heldItem.name === 'water_bucket' }) }
    // Turn around and look up at the pillar ("look how high that was").
    await bot.waitForTicks(6)
    const dx = x + 0.5 - bot.entity.position.x, dz = z + 0.5 - bot.entity.position.z
    await easeLook(Math.atan2(-dx, -dz), 1.0, 1200)
    await bot.waitForTicks(30)
    mark('end')
    await cmd(`/replay stop players ${NAME}`)
    await bot.waitForTicks(40)
    const ok = !died && bot.health > 0 && placed
    log(ok ? 'CLUTCH OK' : 'CLUTCH FAILED', 'health', bot.health)
    require('fs').writeFileSync(process.env.TIMELINE || 'timeline.json', JSON.stringify({ ok, timeline }, null, 1))
    bot.quit(); await sleep(500); process.exit(ok ? 0 : 1)
  } catch (e) { log('script error', e); process.exit(3) }
})
let died = false
bot.on('death', () => { died = true; mark('death'); log('died') })
bot.on('health', () => mark('health'))
