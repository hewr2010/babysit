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

    const mediaTypes = await miniProgram.evaluate(() => {
      const groups = getApp()?.$vm?.$pinia?.state?.value?.app?.albumByDate || {}
      return Object.keys(groups).sort().reverse().flatMap(date => {
        return [...groups[date]].sort((a, b) => (b.time || '').localeCompare(a.time || '')).map(item => item.type)
      })
    })
    const photoIndex = mediaTypes.findIndex(type => type !== 'video')
    const videoIndex = mediaTypes.findIndex(type => type === 'video')
    assert.ok(photoIndex >= 0, 'Real album should contain a photo')
    console.log(`Loaded ${mediaTypes.length} real media items`)

    await miniProgram.evaluate(index => wx.navigateTo({ url: `/pages/viewer/viewer?index=${index}` }), photoIndex)
    await waitFor()
    await screenshot(miniProgram, '04-photo')
    await miniProgram.evaluate(() => wx.navigateBack())
    await sleep(800)

    if (videoIndex >= 0) {
      await miniProgram.evaluate(index => wx.navigateTo({ url: `/pages/viewer/viewer?index=${index}` }), videoIndex)
      await waitFor()
      await screenshot(miniProgram, '05-video')
      await miniProgram.evaluate(() => wx.navigateBack())
      await sleep(800)
    }

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
