// Offline, frame-exact renderer for a bot recording (bot.js RECORD=...), using prismarine-viewer's
// browser bundle in headless Chromium. For each output frame it sends the interpolated camera pose
// (and any block changes due by then) over the viewer's socket, waits for the camera tween (50 ms)
// and two animation frames, then screenshots. Smoothness doesn't depend on CPU speed.
// usage: node render.js recording.json outDir [fps=60] [width=1080] [height=1011]
const fs = require('fs')
const path = require('path')
const http = require('http')
const express = require('express')
const { chromium } = require('playwright')
const [recPath, outDir, fpsArg, wArg, hArg] = process.argv.slice(2)
const FPS = Number(fpsArg || 60), W = Number(wArg || 1080), H = Number(hArg || 1011)
const rec = JSON.parse(fs.readFileSync(recPath))
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

function poseAt (t) { // t in ticks (float)
  const P = rec.poses, i = Math.min(P.length - 2, Math.max(0, Math.floor(t))), f = Math.min(1, Math.max(0, t - i))
  const a = P[i], b = P[i + 1]
  let dy = b[4] - a[4]; while (dy > Math.PI) dy -= 2 * Math.PI; while (dy < -Math.PI) dy += 2 * Math.PI
  return { pos: { x: a[1] + (b[1] - a[1]) * f, y: a[2] + (b[2] - a[2]) * f, z: a[3] + (b[3] - a[3]) * f }, yaw: a[4] + dy * f, pitch: a[5] + (b[5] - a[5]) * f }
}

;(async () => {
  const app = express()
  const server = http.createServer(app)
  const io = require('socket.io')(server, { path: '/socket.io' })
  app.use('/', express.static(path.join(require.resolve('prismarine-viewer/package.json'), '..', 'public')))
  let sock = null
  io.on('connection', (s) => {
    sock = s
    s.emit('version', rec.version)
    for (const c of rec.columns) s.emit('loadChunk', c)
  })
  await new Promise(r => server.listen(0, '127.0.0.1', r))
  const port = server.address().port
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
  await page.goto(`http://127.0.0.1:${port}/`)
  while (!sock) await sleep(50)
  const p0 = poseAt(0)
  sock.emit('position', { pos: p0.pos, yaw: p0.yaw, pitch: p0.pitch, addMesh: false })
  await sleep(6000) // let the workers mesh the snapshot
  fs.mkdirSync(outDir, { recursive: true })
  const ticks = rec.poses.length - 1, frames = Math.floor(ticks / 20 * FPS)
  const raf = () => page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))))
  let bi = 0
  const t0 = Date.now()
  for (let f = 0; f < frames; f++) {
    const t = f * 20 / FPS
    let changed = false
    while (bi < rec.blocks.length && rec.blocks[bi][0] <= t) {
      const [, x, y, z, stateId] = rec.blocks[bi++]
      sock.emit('blockUpdate', { pos: { x, y, z }, stateId }); changed = true
    }
    const p = poseAt(t)
    sock.emit('position', { pos: p.pos, yaw: p.yaw, pitch: p.pitch, addMesh: false })
    await sleep(changed ? 160 : 60) // camera tween is 50 ms; block changes re-mesh in a worker
    await raf()
    await page.screenshot({ path: `${outDir}/f${String(f).padStart(5, '0')}.png` })
    if (f % 60 === 0) console.log(`frame ${f}/${frames}`)
  }
  const secs = (Date.now() - t0) / 1000
  console.log(`rendered ${frames} frames (${(frames / FPS).toFixed(2)} s of video) in ${secs.toFixed(1)} s = ${(secs / (frames / FPS)).toFixed(1)} s per video second`)
  await browser.close(); server.close(); process.exit(0)
})()
