const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawn, spawnSync } = require('node:child_process')
const automator = require('miniprogram-automator')
const { startMockServer } = require('./mock-server')

const root = path.resolve(__dirname, '..')
const outputDir = fs.mkdtempSync(path.join(os.tmpdir(), 'babysit-mp-interactions-'))
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))
const cases = []

function testCase(id, title, run) {
  cases.push({ id, title, run })
}

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
  const videoPath = path.join(outputDir, 'sample.mp4')
  const generated = spawnSync('ffmpeg', ['-f', 'lavfi', '-i', 'color=c=teal:s=320x240:d=1', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-y', videoPath], { stdio: 'ignore' })
  assert.equal(generated.status, 0, 'ffmpeg must create the test video')
  const mock = await startMockServer(videoPath)
  const currentDate = Object.keys(mock.albums[`${mock.current.year}-${mock.current.month}`])[0]
  const items = mock.albums[`${mock.current.year}-${mock.current.month}`][currentDate]
  let miniProgram

  async function resetStore() {
    const monthJson = JSON.stringify({ year: mock.current.year, month: mock.current.month })
    await miniProgram.evaluate(monthJson => {
      const month = JSON.parse(monthJson)
      const state = getApp()?.$vm?.$pinia?.state?.value?.app
      if (!state) return
      state.year = month.year
      state.month = month.month
      state.albumByDate = {}
      state.milestones = []
    }, monthJson)
    mock.state.requests.length = 0
  }

  async function stubPreview(failures = []) {
    await miniProgram.evaluate(failuresJson => {
      wx.__previewCalls = []
      wx.__previewFailures = JSON.parse(failuresJson)
      wx.previewMedia = options => {
        wx.__previewCalls.push(options)
        const errMsg = wx.__previewFailures[wx.__previewCalls.length - 1]
        if (errMsg) options.fail?.({ errMsg })
        else options.success?.()
      }
    }, JSON.stringify(failures))
  }

  async function previewCalls() {
    return miniProgram.evaluate(() => wx.__previewCalls || [])
  }

  async function openShare(name, year = mock.current.year, month = mock.current.month) {
    await resetStore()
    await miniProgram.reLaunch(`/pages/viewer/viewer?media=${encodeURIComponent(name)}&year=${year}&month=${month}`)
    return miniProgram.currentPage()
  }

  async function openHome() {
    await resetStore()
    await miniProgram.reLaunch('/pages/index/index')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.media-cell')), 'home media')
    return miniProgram.currentPage()
  }

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
    await miniProgram.evaluate(() => wx.setStorageSync('baby_auth_verified', 'true'))
    await miniProgram.reLaunch('/pages/index/index')
    await waitFor(async () => !!(await (await miniProgram.currentPage()).$('.media-cell')), 'automation warmup')

    testCase('SHARE-01', '热视频分享卡片直接进入正确的原生播放项', async () => {
      await stubPreview()
      await openShare(items[1].name)
      await waitFor(async () => (await previewCalls()).length === 1, 'shared preview')
      const [options] = await previewCalls()
      assert.equal(options.current, 1)
      assert.equal(options.sources[1].type, 'video')
      assert.ok(options.sources[1].url.includes('/video/'))
    })

    testCase('SHARE-02', '首次 called too early 自动恢复，不展示底层导航错误', async () => {
      await stubPreview(['previewMedia:fail called too early, cannot find navigation'])
      const page = await openShare(items[0].name)
      await waitFor(async () => (await previewCalls()).length >= 2, 'automatic preview retry', 5000)
      assert.equal(await page.$('.load-error'), null)
    })

    testCase('SHARE-03', '退出原生播放器直接回首页，不显示分享启动页', async () => {
      await stubPreview()
      await openShare(items[1].name)
      await waitFor(async () => (await previewCalls()).length === 1, 'preview opened')
      await miniProgram.navigateTo('/pages/index/index')
      await waitFor(async () => (await miniProgram.currentPage()).path === 'pages/index/index', 'launcher hidden')
      await miniProgram.evaluate(() => wx.navigateBack())
      await waitFor(async () => (await miniProgram.currentPage()).path === 'pages/index/index', 'home after native preview closes')
      assert.equal((await miniProgram.currentPage()).path, 'pages/index/index')
    })

    testCase('SHARE-04', '冷媒体分享自动触发恢复并重试，不要求用户理解错误后手点', async () => {
      items[2].preview_ready = false
      await stubPreview(['previewMedia:fail media not ready'])
      await openShare(items[2].name)
      await waitFor(async () => {
        const statusRequests = mock.state.requests.filter(item => item.includes('/api/media/status/'))
        return (await previewCalls()).length >= 2 || statusRequests.length > 0
      }, 'cold shared media recovery', 5000)
      items[2].preview_ready = true
    })

    testCase('SHARE-05', '失效分享显示可理解错误，返回首页可用', async () => {
      await stubPreview()
      const page = await openShare('不存在.jpg')
      await waitFor(async () => !!(await page.$('.load-error')), 'missing share error')
      assert.match(await (await page.$('.load-error')).text(), /不存在|尚未同步/)
      await (await page.$('.secondary-button')).tap()
      await waitFor(async () => (await miniProgram.currentPage()).path === 'pages/index/index', 'missing share home')
    })

    testCase('HOME-01', '热照片宫格点击使用原生预览且索引正确', async () => {
      items.forEach(item => {
        item.preview_ready = true
        if (item.type === 'video') item.video_ready = true
      })
      await stubPreview()
      const page = await openHome()
      await (await page.$('.media-cell')).tap()
      await waitFor(async () => (await previewCalls()).length === 1, 'home photo preview')
      const [options] = await previewCalls()
      assert.equal(options.current, 0)
      assert.equal(options.sources.length, 8)
      assert.equal(options.sources[0].type, 'image')
    })

    testCase('HOME-02', '热媒体瞬时打开失败每 3 秒自动重试', async () => {
      await stubPreview(['previewMedia:fail transient'])
      const page = await openHome()
      await (await page.$('.media-cell')).tap()
      await waitFor(async () => (await previewCalls()).length >= 2, 'home transient retry', 5000)
      assert.equal((await miniProgram.currentPage()).path, 'pages/index/index')
    })

    testCase('COLD-01', '首页冷照片先请求媒体并轮询状态，再打开原生预览', async () => {
      items[2].preview_ready = false
      await stubPreview()
      const page = await openHome()
      mock.state.requests.length = 0
      const cells = await page.$$('.media-cell')
      await cells[2].tap()
      await waitFor(async () => {
        return mock.state.requests.some(item => item.startsWith('GET /preview/'))
          && mock.state.requests.some(item => item.includes('/api/media/status/'))
      }, 'cold home recovery')
      items[2].preview_ready = true
      await waitFor(async () => (await previewCalls()).length === 1, 'cold home preview')
      assert.equal((await previewCalls())[0].current, 2)
    })

    testCase('MONTH-01', '每日展开后第 7 项仍能打开正确索引', async () => {
      await stubPreview()
      const page = await openHome()
      await (await page.$('.view-more-btn')).tap()
      const cells = await page.$$('.media-cell')
      assert.equal(cells.length, 8)
      await cells[6].tap()
      await waitFor(async () => (await previewCalls()).length === 1, 'expanded media preview')
      assert.equal((await previewCalls())[0].current, 6)
    })

    testCase('ACTION-01', '超过 50MB 的原文件阻止下载并给出提示', async () => {
      items[0].size = 51 * 1024 * 1024
      await stubPreview()
      const page = await openHome()
      await miniProgram.evaluate(() => {
        wx.__modals = []
        wx.__originalDownloads = []
        wx.showModal = options => wx.__modals.push(options)
        const original = wx.downloadFile
        wx.downloadFile = options => {
          if (options.url.includes('/api/download/')) wx.__originalDownloads.push(options.url)
          return original(options)
        }
      })
      await (await page.$('.media-menu-button')).tap()
      const buttons = await page.$$('.album-actions .action-button')
      await buttons[2].tap()
      await waitFor(async () => (await miniProgram.evaluate(() => wx.__modals.length)) === 1, 'oversize modal')
      const result = await miniProgram.evaluate(() => ({ modals: wx.__modals, downloads: wx.__originalDownloads }))
      assert.match(result.modals[0].content, /50MB/)
      assert.equal(result.downloads.length, 0)
      items[0].size = 1024
    })

    testCase('MANAGE-01', '直接打开管理页也展示已有关联时刻', async () => {
      mock.state.milestones = [{ id: 99, media_filename: items[0].name, title: '已有时刻', date: currentDate }]
      await resetStore()
      await miniProgram.reLaunch('/pages/milestones/manage')
      const page = await miniProgram.currentPage()
      await waitFor(async () => !!(await page.$('.manage-cell')), 'manage cells')
      await waitFor(async () => !!(await page.$('.manage-cell.marked')), 'existing milestone marker', 3000)
      mock.state.milestones = []
    })

    testCase('MONTH-02', '切月失败不得在新月份标题下保留旧月份媒体', async () => {
      await stubPreview()
      const page = await openHome()
      await miniProgram.evaluate(() => {
        wx.__monthFailureToasts = []
        wx.showToast = options => wx.__monthFailureToasts.push(options)
        wx.__originalRequest = wx.request
        wx.request = options => {
          if (/\/api\/album\/\d+\/\d+$/.test(options.url)) {
            options.fail?.({ errMsg: 'request:fail simulated month failure' })
            return
          }
          return wx.__originalRequest(options)
        }
      })
      await (await page.$('.next-month')).tap()
      await waitFor(async () => (await miniProgram.evaluate(() => wx.__monthFailureToasts.length)) === 1, 'month failure toast')
      const label = await (await page.$('.month-label')).text()
      const oldMediaVisible = !!(await page.$('.media-cell'))
      const returnedToCurrent = label.includes(`${mock.current.year}年${mock.current.month}月`) && oldMediaVisible
      const clearedFailedMonth = !oldMediaVisible
      assert.ok(returnedToCurrent || clearedFailedMonth, `${label} still renders stale media`)
      await miniProgram.evaluate(() => { wx.request = wx.__originalRequest })
    })

    testCase('SHARE-06', '跨月特殊文件名分享打开对应月份的非首项', async () => {
      const previousGroups = mock.albums[`${mock.previous.year}-${mock.previous.month}`]
      const previousDate = Object.keys(previousGroups)[0]
      const special = { name: '上月 特殊%#.jpg', type: 'photo', size: 1024, time: '09:00:00', preview_ready: true }
      previousGroups[previousDate].push(special)
      await stubPreview()
      await openShare(special.name, mock.previous.year, mock.previous.month)
      await waitFor(async () => (await previewCalls()).length === 1, 'special shared media')
      const [options] = await previewCalls()
      assert.equal(options.current, 1)
      assert.ok(options.sources[1].url.includes(encodeURIComponent(special.name)))
      previousGroups[previousDate].pop()
    })

    testCase('HOME-03', '冷媒体等待中点击另一项，只打开最后选择的媒体', async () => {
      items[2].preview_ready = false
      mock.state.delays[items[2].name] = 10000
      delete mock.state.recovery[items[2].name]
      await stubPreview()
      const page = await openHome()
      const cells = await page.$$('.media-cell')
      await cells[2].tap()
      await cells[0].tap()
      await waitFor(async () => (await previewCalls()).length === 1, 'latest media preview')
      await sleep(2500)
      const calls = await previewCalls()
      assert.equal(calls.length, 1)
      assert.equal(calls[0].current, 0)
      items[2].preview_ready = true
      delete mock.state.delays[items[2].name]
      delete mock.state.recovery[items[2].name]
    })

    testCase('HLS-01', '冷视频 HLS 先就绪时使用原生播放器打开低清流', async () => {
      items[1].video_ready = false
      mock.state.hlsReady[items[1].name] = true
      mock.state.delays[items[1].name] = 10000
      delete mock.state.recovery[items[1].name]
      await stubPreview()
      const page = await openHome()
      const cells = await page.$$('.media-cell')
      await cells[1].tap()
      await waitFor(async () => (await previewCalls()).length === 1, 'HLS preview')
      const [options] = await previewCalls()
      assert.ok(options.sources[1].url.includes(`/hls/${encodeURIComponent(items[1].name)}/index.m3u8`))
      items[1].video_ready = true
      delete mock.state.hlsReady[items[1].name]
      delete mock.state.delays[items[1].name]
      delete mock.state.recovery[items[1].name]
    })

    testCase('MANAGE-02', '管理页加载失败可重试，不停留无媒体空态', async () => {
      await resetStore()
      await miniProgram.evaluate(() => {
        wx.__originalManageRequest = wx.request
        wx.request = options => {
          if (options.url.endsWith('/api/album')) options.fail?.({ errMsg: 'request:fail simulated manage failure' })
          else wx.__originalManageRequest(options)
        }
      })
      await miniProgram.reLaunch('/pages/milestones/manage')
      let page = await miniProgram.currentPage()
      await waitFor(async () => !!(await page.$('.load-error')), 'manage load error')
      await miniProgram.evaluate(() => { wx.request = wx.__originalManageRequest })
      await (await page.$('.retry-button')).tap()
      await waitFor(async () => !!(await page.$('.manage-cell')), 'manage retry cells')
      assert.equal(await page.$('.load-error'), null)
    })

    testCase('MANAGE-03', '慢月份响应不得覆盖最后选择的月份', async () => {
      mock.state.albumDelays[`${mock.previous.year}-${mock.previous.month}`] = 1000
      mock.state.albumDelays[`${mock.current.year}-${mock.current.month}`] = 0
      await resetStore()
      await miniProgram.reLaunch('/pages/milestones/manage')
      const page = await miniProgram.currentPage()
      await waitFor(async () => !!(await page.$('.manage-cell')), 'initial manage month')
      const months = await page.$$('.manage-month')
      await months[1].tap()
      await months[0].tap()
      await sleep(1400)
      assert.equal((await page.$$('.manage-cell')).length, items.length)
      const selectedMonth = await page.$('.manage-month.selected')
      assert.match(await selectedMonth.text(), new RegExp(`${mock.current.year}年${mock.current.month}月`))
      delete mock.state.albumDelays[`${mock.previous.year}-${mock.previous.month}`]
    })

    testCase('THUMB-01', '缩略图自动重试后显示失败占位，点击可恢复', async () => {
      const item = { name: '缩略图重试.jpg', type: 'photo', size: 1024, time: '01:00:00', preview_ready: true }
      items.push(item)
      mock.state.thumbFailures[item.name] = 3
      await stubPreview()
      const page = await openHome()
      await (await page.$('.view-more-btn')).tap()
      await waitFor(async () => !!(await page.$('.thumb-error')), 'thumbnail failure placeholder', 10000)
      const requestsBeforeRetry = mock.state.requests.filter(request => request === `GET /thumb/${item.name}`).length
      assert.equal(requestsBeforeRetry, 3)
      await (await page.$('.thumb-error')).tap()
      await waitFor(async () => !(await page.$('.thumb-error')), 'thumbnail manual retry')
      assert.equal(mock.state.requests.filter(request => request === `GET /thumb/${item.name}`).length, 4)
      items.pop()
    })

    testCase('ACTION-02', '视频保存使用原文件，权限失败后仍可重试', async () => {
      await stubPreview()
      const page = await openHome()
      await miniProgram.evaluate(() => {
        wx.__originalDownloadForSave = wx.downloadFile
        wx.__originalDownloads = []
        wx.__savedVideos = []
        wx.__saveModals = []
        wx.downloadFile = options => {
          if (options.url.includes('/api/download/') || options.url.includes('/video/')) {
            wx.__originalDownloads.push(options.url)
            options.success?.({ statusCode: 200, tempFilePath: '/tmp/original.mp4' })
            return
          }
          return wx.__originalDownloadForSave(options)
        }
        wx.saveVideoToPhotosAlbum = options => {
          wx.__savedVideos.push(options.filePath)
          options.success?.()
        }
        wx.showModal = options => wx.__saveModals.push(options)
      })
      const menus = await page.$$('.media-menu-button')
      await menus[1].tap()
      let buttons = await page.$$('.album-actions .action-button')
      await buttons[2].tap()
      await waitFor(async () => (await miniProgram.evaluate(() => wx.__savedVideos.length)) === 1, 'original video saved')
      const originalDownloads = await miniProgram.evaluate(() => wx.__originalDownloads)
      assert.ok(originalDownloads[0].includes(`/api/download/${encodeURIComponent(items[1].name)}`))
      await miniProgram.evaluate(() => {
        wx.saveVideoToPhotosAlbum = options => options.fail?.({ errMsg: 'saveVideoToPhotosAlbum:fail auth deny' })
      })
      await menus[1].tap()
      buttons = await page.$$('.album-actions .action-button')
      await buttons[2].tap()
      await waitFor(async () => (await miniProgram.evaluate(() => wx.__saveModals.length)) === 1, 'save permission error')
      const modals = await miniProgram.evaluate(() => wx.__saveModals)
      assert.match(modals[0].content, /保存失败/)
      await miniProgram.evaluate(() => { wx.downloadFile = wx.__originalDownloadForSave })
    })

    testCase('ACTION-03', '长按打开操作层但不触发媒体预览', async () => {
      await stubPreview()
      const page = await openHome()
      await (await page.$('.media-cell')).longpress()
      await waitFor(async () => !!(await page.$('.action-share')), 'long press actions')
      await sleep(600)
      assert.equal((await previewCalls()).length, 0)
      await (await page.$('.sheet-close')).tap()
      assert.equal((await previewCalls()).length, 0)
    })

    testCase('AUTH-01', '未验证用户从分享卡片验证后回到原媒体', async () => {
      await stubPreview()
      await miniProgram.evaluate(() => wx.clearStorageSync())
      await miniProgram.reLaunch(`/pages/viewer/viewer?media=${encodeURIComponent(items[1].name)}&year=${mock.current.year}&month=${mock.current.month}`)
      const authPage = await miniProgram.currentPage()
      await waitFor(async () => !!(await authPage.$('.auth-input')), 'shared media auth')
      await (await authPage.$('.auth-input')).input('错误名字')
      await (await authPage.$('.auth-button')).tap()
      assert.match(await (await authPage.$('.auth-error')).text(), /名字不对/)
      await (await authPage.$('.auth-input')).input('何与青')
      await (await authPage.$('.auth-button')).tap()
      await waitFor(async () => (await previewCalls()).length === 1, 'auth return preview')
      assert.equal((await miniProgram.currentPage()).path, 'pages/viewer/viewer')
      assert.equal((await previewCalls())[0].current, 1)
    })

    const results = { passed: 0, failed: 0 }
    const selectedCases = process.env.CASE_FILTER
      ? cases.filter(item => item.id === process.env.CASE_FILTER)
      : cases
    for (const item of selectedCases) {
      try {
        await item.run()
        results.passed += 1
        console.log(`PASS ${item.id} ${item.title}`)
      } catch (error) {
        results.failed += 1
        const page = await miniProgram.currentPage()
        const launcher = await page.$('.native-preview-launch')
        console.error(`FAIL ${item.id} ${item.title}\n${error.stack}`)
        console.error('页面诊断：', {
          path: page.path,
          text: launcher ? await launcher.text() : '',
          previewCalls: (await previewCalls()).length,
          requests: mock.state.requests
        })
      }
    }
    console.log(`Interaction cases: ${results.passed} passed, ${results.failed} failed`)
    if (results.failed) process.exitCode = 1
  } finally {
    if (miniProgram) await miniProgram.close().catch(() => {})
    await new Promise(resolve => mock.server.close(resolve))
    fs.rmSync(outputDir, { recursive: true, force: true })
  }
}

main().catch(error => {
  console.error(error)
  process.exitCode = 1
})
