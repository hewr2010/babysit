const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const automator = require('miniprogram-automator')

const projectPath = path.resolve(__dirname, '../dist/build/mp-weixin')
const cliPath = '/Applications/wechatwebdevtools.app/Contents/MacOS/cli'
const outputDir = fs.mkdtempSync(path.join(os.tmpdir(), 'babysit-production-'))
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))

async function waitFor() {
  await sleep(5000)
}

async function screenshot(miniProgram, name) {
  if (process.env.CAPTURE_SCREENSHOTS !== '1') return
  try {
    await miniProgram.screenshot({ path: path.join(outputDir, `${name}.png`) })
  } catch (error) {
    if (process.env.ALLOW_SCREENSHOT_FAILURE !== '1') throw error
    console.warn(`Screenshot skipped: ${name}`)
  }
}

async function main() {
  console.log(`Production verification artifacts: ${outputDir}`)
  const miniProgram = process.env.WS_ENDPOINT
    ? await automator.connect({ wsEndpoint: process.env.WS_ENDPOINT })
    : await automator.launch({ cliPath, projectPath, trustProject: true, timeout: 120000 })
  const errors = []
  miniProgram.on('console', message => {
    const text = message.text || message.message || String(message)
    console.log(`[mini-program ${message.type || 'log'}]`, text)
    if (message.type === 'error') errors.push(text)
  })
  try {
    await miniProgram.evaluate(() => wx.clearStorageSync())
    await miniProgram.reLaunch('/pages/auth/auth')
    await sleep(1000)
    await screenshot(miniProgram, '01-auth')
    await miniProgram.evaluate(() => {
      wx.setStorageSync('baby_auth_verified', 'true')
      wx.reLaunch({ url: '/pages/index/index' })
    })
    console.log('Opening real home data')
    await waitFor()
    await screenshot(miniProgram, '02-home')

    await miniProgram.evaluate(() => wx.pageScrollTo({ selector: '#album-section', duration: 250 }))
    await sleep(800)
    await screenshot(miniProgram, '03-album-tab')

    const mediaItems = await miniProgram.evaluate(() => {
      const groups = getApp()?.$vm?.$pinia?.state?.value?.app?.albumByDate || {}
      return Object.keys(groups).sort().reverse().flatMap(date => {
        return [...groups[date]].sort((a, b) => (b.time || '').localeCompare(a.time || '')).map(item => ({ ...item, date }))
      })
    })
    const photo = mediaItems.find(item => item.type !== 'video')
    const video = mediaItems.find(item => item.type === 'video')
    assert.ok(photo, 'Real album should contain a photo')
    console.log(`Loaded ${mediaItems.length} real media items`)

    async function openShared(item, screenshotName) {
      const [year, month] = item.date.split('-')
      const path = `/pages/viewer/viewer?media=${encodeURIComponent(item.name)}&year=${year}&month=${Number(month)}`
      await miniProgram.evaluate(path => wx.navigateTo({ url: path }), path)
      await waitFor()
      assert.equal((await miniProgram.currentPage()).path, 'pages/viewer/viewer')
      assert.equal(await (await miniProgram.currentPage()).$('.load-error'), null)
      await screenshot(miniProgram, screenshotName)
      await miniProgram.evaluate(() => wx.navigateBack())
      await sleep(800)
    }

    await openShared(photo, '04-photo')
    if (video) await openShared(video, '05-video')

    await miniProgram.evaluate(() => wx.navigateTo({ url: '/pages/milestones/manage' }))
    await waitFor()
    await screenshot(miniProgram, '06-manage')
    await miniProgram.evaluate(() => wx.navigateBack())
    await sleep(800)
    if (errors.length) throw new Error(`Mini program console errors:\n${errors.join('\n')}`)
    console.log('Production read-only verification passed; no create, update or delete actions were performed.')
  } finally {
    await miniProgram.disconnect()
  }
}

main().catch(error => {
  console.error(error)
  process.exitCode = 1
})
