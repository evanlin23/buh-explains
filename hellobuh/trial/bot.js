// Scripted MLG-water clutch. Joins the local offline server, builds the set,
// starts a ServerReplay recording of itself, falls off a pillar and places water
// just before landing. Exits 0 if it survived with the clutch, 1 otherwise.
const mineflayer = require('mineflayer')
const { Vec3 } = require('vec3')

const NAME = process.env.BOT_NAME || 'HelloBuh'
const HEIGHT = Number(process.env.FALL_HEIGHT || 60)   // blocks above the floor
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

const bot = mineflayer.createBot({ host: '127.0.0.1', port: 25565, username: NAME, auth: 'offline', version: '1.21.11' })
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
const cmd = async (c) => { bot.chat(c); await bot.waitForTicks(4) }

bot.once('spawn', async () => {
  try {
    log('spawned at', bot.entity.position)
    const base = bot.entity.position.floored()
    const x = base.x, z = base.z, floor = base.y - 1, top = floor + HEIGHT
    await cmd('/gamemode creative'); await cmd('/time set 6000'); await cmd('/weather clear')
    await cmd('/gamerule doDaylightCycle false'); await cmd('/gamerule doWeatherCycle false')
    await cmd('/gamerule sendCommandFeedback false'); await cmd('/gamerule showDeathMessages true')
    // The set: a grass landing pad ringed with some scenery, a stone pillar to jump from.
    await cmd(`/fill ${x - 12} ${floor} ${z - 12} ${x + 12} ${floor} ${z + 12} grass_block`)
    await cmd(`/fill ${x - 12} ${floor + 1} ${z - 12} ${x + 12} ${top + 4} ${z + 12} air`)
    await cmd(`/fill ${x} ${floor + 1} ${z} ${x} ${top} ${z} cobblestone`)
    await cmd(`/fill ${x - 6} ${floor + 1} ${z + 4} ${x - 6} ${floor + 5} ${z + 4} oak_log`)
    await cmd(`/fill ${x - 8} ${floor + 5} ${z + 2} ${x - 4} ${floor + 7} ${z + 6} oak_leaves keep`)
    await cmd(`/clear @s`)
    await cmd(`/item replace entity @s hotbar.0 with diamond_sword`)
    await cmd(`/item replace entity @s hotbar.1 with water_bucket`)
    await cmd(`/item replace entity @s hotbar.2 with cobblestone 64`)
    await cmd(`/item replace entity @s hotbar.3 with bread 16`)
    await cmd(`/effect clear @s`)
    await cmd(`/tp @s ${x + 0.5} ${top + 1} ${z + 0.5} 0 20`)
    await bot.waitForTicks(20)
    await cmd('/gamemode survival'); await cmd('/effect give @s instant_health 1 10 true')
    bot.setQuickBarSlot(0)
    await bot.waitForTicks(30)
    log('on top at', bot.entity.position, 'health', bot.health)

    await cmd(`/replay start players ${NAME}`)
    await bot.waitForTicks(30)                     // ~1.5 s of "standing on the pillar"
    await easeLook(0, -1.0, 600)                   // peek over the edge (mineflayer: negative pitch = down)
    await easeLook(0, -0.25, 400)
    bot.setQuickBarSlot(1)                         // pull out the water bucket
    await bot.waitForTicks(6)
    // Walk off the +z edge.
    bot.setControlState('forward', true); bot.setControlState('jump', true)
    await bot.waitForTicks(6)
    bot.setControlState('jump', false)
    await bot.waitForTicks(4)
    bot.setControlState('forward', false)
    easeLook(bot.entity.yaw, -Math.PI / 2 + 0.01, 500)   // look straight down while falling
    let placed = false
    const fallStart = bot.entity.position.y
    while (bot.entity.onGround === false || bot.entity.position.y > floor + 2) {
      const p = bot.entity.position, vy = bot.entity.velocity.y
      const above = p.y - (floor + 1)
      // Place when the floor is within reach and next tick would be too late.
      if (!placed && above < 4.2 && vy < 0) {
        bot.setQuickBarSlot(1)
        await bot.look(bot.entity.yaw, -Math.PI / 2, true)
        bot.activateItem(); placed = true
        log('water placed at height', above.toFixed(2), 'vy', vy.toFixed(2))
      }
      await bot.waitForTicks(1)
      if (bot.health <= 0) break
      if (fallStart - bot.entity.position.y > HEIGHT + 10) break
    }
    await bot.waitForTicks(8)
    log('landed, health', bot.health, 'in water', bot.entity.isInWater)
    // Scoop the water back up (the flourish).
    const below = bot.blockAt(bot.entity.position.floored())
    if (below && below.name === 'water') { await bot.look(bot.entity.yaw, -Math.PI / 2, true); bot.activateItem(); await bot.waitForTicks(4) }
    await easeLook(bot.entity.yaw + 0.3, -0.15, 700)
    await bot.waitForTicks(30)
    await cmd(`/replay stop players ${NAME}`)
    await bot.waitForTicks(40)
    const ok = bot.health > 0 && placed
    log(ok ? 'CLUTCH OK' : 'CLUTCH FAILED', 'health', bot.health)
    bot.quit(); await sleep(500); process.exit(ok ? 0 : 1)
  } catch (e) { log('script error', e); process.exit(3) }
})
bot.on('death', () => log('died'))
