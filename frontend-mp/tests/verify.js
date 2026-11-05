const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawn, spawnSync } = require('node:child_process')
const automator = require('miniprogram-automator')
const { startMockServer } = require('./mock-server')

const root = path.resolve(__dirname, '..')
const projectPath = path.join(root, 'dist/build/mp-weixin')
const cliPath = '/Applications/wechatwebdevtools.app/Contents/MacOS/cli'
const outputDir = fs.mkdtempSync(path.join(os.tmpdir(), 'babysit-mp-verify-'))
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd: root, stdio: 'inherit', ...options })
    child.on('error', reject)
    child.on('exit', code => code === 0 ? resolve() : reject(new Error(`${command} exited with ${code}`)))
  })
}

async function waitFor(callback, message, timeout = 15000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    if (await callback()) return
    await sleep(250)
  }
  throw new Error(`Timed out: ${message}`)
}

async function elementText(page, selector) {
  const element = await page.$(selector)
  return element ? element.text() : ''
}

async function screenshot(miniProgram, name) {
  const file = path.join(outputDir, `${name}.png`)
  try {
    await miniProgram.screenshot({ path: file })
    return
  } catch (error) {
    if (process.env.ALLOW_SCREENSHOT_FAILURE === '1') {
      console.warn(`Screenshot skipped: ${name}`)
      return
    }
    const captured = spawnSync('screencapture', ['-x', file])
    if (captured.status !== 0 || !fs.existsSync(file)) throw error
  }
}

async function main() {
  console.log(`Verification artifacts: ${outputDir}`)
  let videoPath = null
  const ffmpeg = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' })
  if (ffmpeg.status === 0) {
    videoPath = path.join(outputDir, 'sample.mp4')
    const generated = spawnSync('ffmpeg', ['-f', 'lavfi', '-i', 'color=c=teal:s=320x240:d=1', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', '-y', videoPath], { stdio: 'ignore' })
    if (generated.status !== 0) videoPath = null
  }

  const mock = await startMockServer(videoPath)
  let miniProgram
  const consoleErrors = []
  try {
    await run('npm', ['run', 'build:mp-weixin'], {
      env: { ...process.env, VITE_API_HOST: `http://127.0.0.1:${mock.port}` }
    })
    miniProgram = process.env.WS_ENDPOINT
      ? await automator.connect({ wsEndpoint: process.env.WS_ENDPOINT })
      : await automator.launch({ cliPath, projectPath, trustProject: true, timeout: 120000 })
    miniProgram.on('console', message => {
      const text = message.text || message.message || String(message)
      console.log(`[mini-program ${message.type || 'log'}]`, text)
      if (message.type === 'error') consoleErrors.push(text)
    })

    await miniProgram.evaluate(() => wx.clearStorageSync())
    await miniProgram.reLaunch('/pages/auth/auth')
    await sleep(1200)
    let page = await miniProgram.currentPage()
    await screenshot(miniProgram, '01-auth')
    const authInput = await page.$('.auth-input')
    await authInput.input('错误名字')
    await (await page.$('.auth-button')).tap()
    assert.match(await elementText(page, '.auth-error'), /名字不对/)
    await authInput.input('何与青')
    await (await page.$('.auth-button')).tap()
    await waitFor(async () => (await miniProgram.currentPage()).path === 'pages/index/index', 'home after auth')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.growth-section')), 'initial data')
    page = await miniProgram.currentPage()
    await sleep(1000)
    await screenshot(miniProgram, '02-home')

    await (await page.$('.album-tab')).tap()
    await sleep(400)
    await (await page.$('.growth-tab')).tap()
    await miniProgram.evaluate(() => {
      wx.showActionSheet = options => {
        wx.__recordMenuItems = options.itemList
        options.success?.({ tapIndex: 0 })
      }
    })
    await (await page.$('.record-tab')).tap()
    await waitFor(async () => !!(await page.$('.growth-value-input')), 'record action sheet')
    assert.deepEqual(await miniProgram.evaluate(() => wx.__recordMenuItems), ['记录身高', '记录体重'])
    await (await page.$('.sheet-close')).tap()

    await (await page.$('.baby-card')).tap()
    await (await page.$('.baby-name-input')).input('新名字')
    await (await page.$('.save-baby')).tap()
    await waitFor(async () => mock.state.baby.name === '新名字', 'baby saved')
    await waitFor(async () => (await elementText(page, '.baby-name')) === '新名字', 'baby rendered')

    const growthCount = mock.state.growth.length
    await (await page.$('.add-growth')).tap()
    await (await page.$('.growth-value-input')).input('53.2')
    await (await page.$('.save-growth')).tap()
    await waitFor(async () => mock.state.growth.length === growthCount + 1, 'growth saved')
    assert.equal(await page.$('.delete-growth'), null)
    await miniProgram.evaluate(() => {
      wx.showModal = options => options.success?.({ confirm: true, cancel: false })
    })

    await (await page.$('.previous-month')).tap()
    await waitFor(async () => (await elementText(page, '.month-label')).includes(`${mock.previous.year}年${mock.previous.month}月`), 'previous month')
    await (await page.$('.next-month')).tap()
    await waitFor(async () => (await elementText(page, '.month-label')).includes(`${mock.current.year}年${mock.current.month}月`), 'current month')

    await (await page.$('.media-cell')).tap()
    await waitFor(async () => (await miniProgram.currentPage()).path === 'pages/viewer/viewer', 'photo viewer')
    await sleep(800)
    await screenshot(miniProgram, '03-photo-viewer')
    await miniProgram.navigateBack()
    await sleep(500)

    page = await miniProgram.currentPage()
    await (await page.$('.manage-milestones')).tap()
    await waitFor(async () => (await miniProgram.currentPage()).path === 'pages/milestones/manage', 'milestone manager')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.manage-cell')), 'manage media')
    page = await miniProgram.currentPage()
    await (await page.$('.manage-cell')).tap()
    await (await page.$('.milestone-title-input')).input('自动化重要时刻')
    await (await page.$('.save-milestone')).tap()
    await waitFor(async () => mock.state.milestones.length === 1, 'milestone saved')
    await (await page.$('.sheet-close')).tap()
    await waitFor(async () => !!(await page.$('.manage-cell.marked')), 'marked media')
    await screenshot(miniProgram, '04-milestone-manage')

    await (await page.$('.manage-cell')).tap()
    await (await page.$('.delete-milestone')).tap()
    await waitFor(async () => mock.state.milestones.length === 0, 'milestone deleted')
    await (await page.$('.sheet-close')).tap()

    await miniProgram.navigateTo('/pages/viewer/viewer?index=1')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.viewer-video')), 'video viewer')
    await sleep(1200)
    await screenshot(miniProgram, '05-video-viewer')
    assert.ok(mock.state.requests.some(item => item.startsWith('GET /video/')), 'video should be requested')

    if (consoleErrors.length) throw new Error(`Mini program console errors:\n${consoleErrors.join('\n')}`)
    console.log('WeChat DevTools verification passed.')
    console.log(`Screenshots: ${outputDir}`)
  } finally {
    if (miniProgram) await miniProgram.close().catch(() => {})
    await new Promise(resolve => mock.server.close(resolve))
    if (process.env.KEEP_SCREENSHOTS !== '1') fs.rmSync(outputDir, { recursive: true, force: true })
  }
}

main().catch(error => {
  console.error(error)
  process.exitCode = 1
})
