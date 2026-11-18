const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawn } = require('node:child_process')
const automator = require('miniprogram-automator')
const { startMockServer } = require('./mock-server')

const root = path.resolve(__dirname, '..')
const outputDir = fs.mkdtempSync(path.join(os.tmpdir(), 'babysit-mp-recovery-'))
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
    await sleep(200)
  }
  throw new Error(`Timed out: ${message}`)
}

async function main() {
  console.log(`Recovery artifacts: ${outputDir}`)
  const videoPath = path.join(outputDir, 'sample.mp4')
  const ffmpeg = spawn('ffmpeg', ['-f', 'lavfi', '-i', 'color=c=teal:s=320x240:d=1', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-y', videoPath])
  await new Promise(resolve => ffmpeg.on('exit', resolve))
  const mock = await startMockServer(videoPath)
  let miniProgram
  try {
    await run('npm', ['run', 'build:mp-weixin'], {
      env: { ...process.env, VITE_API_HOST: `http://127.0.0.1:${mock.port}` }
    })
    miniProgram = process.env.WS_ENDPOINT
      ? await automator.connect({ wsEndpoint: process.env.WS_ENDPOINT })
      : await automator.launch({
        cliPath: '/Applications/wechatwebdevtools.app/Contents/MacOS/cli',
        projectPath: path.join(root, 'dist/build/mp-weixin'),
        trustProject: true,
        timeout: 120000
      })
    await miniProgram.evaluate(() => {
      wx.setStorageSync('baby_auth_verified', 'true')
      wx.previewMedia = options => {
        wx.__nativePreviewOptions = options
        options.success?.()
      }
    })
    await miniProgram.reLaunch('/pages/index/index')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.media-cell')), 'album')
    let page = await miniProgram.currentPage()
    await (await page.$('.media-cell')).tap()
    const nativePreview = await miniProgram.evaluate(() => wx.__nativePreviewOptions)
    assert.equal(nativePreview.current, 0, '热媒体必须保留原生预览')

    const currentDate = Object.keys(mock.albums[`${mock.current.year}-${mock.current.month}`])[0]
    const items = mock.albums[`${mock.current.year}-${mock.current.month}`][currentDate]
    items[2].preview_ready = false
    items[1].video_ready = false
    mock.state.delays['第三张照片.jpg'] = 3000
    mock.state.delays['第一段视频.mp4'] = 3000
    await miniProgram.reLaunch('/pages/index/index')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.media-cell')), 'album reload')
    page = await miniProgram.currentPage()
    const cells = await page.$$('.media-cell')
    await cells[2].tap()
    await waitFor(async () => {
      const options = await miniProgram.evaluate(() => wx.__nativePreviewOptions)
      return options?.current === 2
    }, 'cold photo always uses native preview')
    assert.equal((await miniProgram.currentPage()).path, 'pages/index/index', '冷照片不能跳自定义页面')

    await miniProgram.reLaunch('/pages/index/index')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.media-cell')), 'album for video')
    page = await miniProgram.currentPage()
    const videoCells = await page.$$('.media-cell')
    await miniProgram.evaluate(() => { wx.__nativePreviewOptions = null })
    await videoCells[1].tap()
    await waitFor(async () => {
      const options = await miniProgram.evaluate(() => wx.__nativePreviewOptions)
      return options?.current === 1
    }, 'cold video always uses native preview')
    assert.equal((await miniProgram.currentPage()).path, 'pages/index/index', '冷视频不能跳自定义页面')
    assert.equal(mock.state.requests.filter(item => item.includes('/api/media/warm')).length, 0, '前端不得发起恢复任务')
    await miniProgram.screenshot({ path: path.join(outputDir, '03-video-ready.png') })
    console.log('Cold media WeChat DevTools verification passed.')
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
