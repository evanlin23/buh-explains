// Screenshots the prismarine-viewer page at a fixed interval while the bot does the stunt.
const { chromium } = require('playwright')
const fs = require('fs')
const [port, outDir, readyFile, goFile, seconds] = process.argv.slice(2)
;(async () => {
  while (!fs.existsSync(readyFile)) await new Promise(r => setTimeout(r, 200))
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
  const page = await browser.newPage({ viewport: { width: 540, height: 740 }, deviceScaleFactor: 1 })
  page.on('console', m => { if (m.type() === 'error') console.log('page:', m.text().slice(0, 200)) })
  await page.goto(`http://127.0.0.1:${port}`)
  await page.waitForTimeout(8000)
  fs.mkdirSync(outDir, { recursive: true })
  fs.writeFileSync(goFile, '1')
  const t0 = Date.now(); let n = 0; const stamps = []
  while (Date.now() - t0 < Number(seconds) * 1000) {
    const t = Date.now() - t0
    await page.screenshot({ path: `${outDir}/f${String(n).padStart(4, '0')}.jpg`, quality: 85 })
    stamps.push(t); n++
  }
  // ffmpeg concat list with real per-frame durations, so playback speed is true to the game.
  let list = ''
  for (let i = 0; i < n; i++) list += `file 'f${String(i).padStart(4, '0')}.jpg'\nduration ${((i + 1 < n ? stamps[i + 1] : stamps[i] + 50) - stamps[i]) / 1000}\n`
  fs.writeFileSync(`${outDir}/frames.txt`, list)
  console.log('frames', n, 'in', (Date.now() - t0) / 1000, 's')
  await browser.close()
})()
