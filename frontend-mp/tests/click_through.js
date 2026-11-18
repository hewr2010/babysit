const assert = require('node:assert/strict')
const path = require('node:path')
const automator = require('miniprogram-automator')

// 真实点击贯穿测试：构建产物（API 指向线上 dev 通道）在开发者工具里
// 逐个点击宫格媒体，验证点击链路真的走到 previewMedia，且服务端收到媒体请求。
// 防止「函数声明丢失/处理器崩溃」这类构建成功但点击静默失败的错误。

const cliPath = '/Applications/wechatwebdevtools.app/Contents/MacOS/cli'
const projectPath = path.resolve(__dirname, '../dist/build/mp-weixin')
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))

async function waitFor(callback, message, timeout = 20000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    if (await callback()) return
    await sleep(300)
  }
  throw new Error(`Timed out: ${message}`)
}

async function main() {
  const miniProgram = process.env.WS_ENDPOINT
    ? await automator.connect({ wsEndpoint: process.env.WS_ENDPOINT })
    : await automator.launch({ cliPath, projectPath, trustProject: true, timeout: 120000 })
  const consoleErrors = []
  miniProgram.on('console', message => {
    const text = message.text || message.message || String(message)
    if (message.type === 'error') {
      consoleErrors.push(text)
      console.log('[console.error]', text.slice(0, 200))
    }
  })

  try {
    // 已验证设备直接进首页；未验证则走姓名验证
    await miniProgram.evaluate(() => {
      wx.__previewCalls = []
      const original = wx.previewMedia
      wx.previewMedia = options => {
        wx.__previewCalls.push({ sources: (options.sources || []).map(s => s.url), current: options.current })
        options.success && options.success()
      }
      wx.__originalPreviewMedia = original
    })
    await miniProgram.reLaunch('/pages/index/index')
    await sleep(2500)
    let page = await miniProgram.currentPage()
    if (page.path.includes('auth')) {
      await (await page.$('.auth-input')).input('何与青')
      await (await page.$('.auth-button')).tap()
      await sleep(2000)
      page = await miniProgram.currentPage()
    }

    await waitFor(async () => (await page.$$('.media-cell')).length > 0, '宫格渲染')
    const cells = await page.$$('.media-cell')
    console.log(`宫格 ${cells.length} 项，逐个点击`)
    assert.ok(cells.length >= 3, '宫格媒体太少，无法有效测试')

    const failures = []
    const clickCount = Math.min(cells.length, 6)
    for (let i = 0; i < clickCount; i++) {
      const before = await miniProgram.evaluate(() => wx.__previewCalls.length)
      await cells[i].tap()
      try {
        await waitFor(
          async () => (await miniProgram.evaluate(() => wx.__previewCalls.length)) > before,
          `第 ${i + 1} 项点击后 previewMedia 被调用`,
          30000
        )
        const call = await miniProgram.evaluate(() => wx.__previewCalls[wx.__previewCalls.length - 1])
        console.log(`  [OK] 第 ${i + 1} 项 → previewMedia: ${call.sources[call.current || 0]?.slice(-60)}`)
      } catch (error) {
        failures.push(i + 1)
        console.log(`  [FAIL] 第 ${i + 1} 项点击后 30s 内未调用 previewMedia`)
      }
      await sleep(800)
    }

    // 恢复中的媒体应触发服务端状态轮询（证明恢复流程被触发）
    const statusPolls = await miniProgram.evaluate(() => wx.__previewCalls.length)
    console.log(`previewMedia 调用总数: ${statusPolls}`)

    if (consoleErrors.length) {
      console.log('控制台错误:')
      consoleErrors.slice(0, 5).forEach(e => console.log(' ', e.slice(0, 200)))
    }
    assert.deepEqual(failures, [], `点击无响应的媒体: ${failures.join(', ')}`)
    assert.equal(consoleErrors.length, 0, '存在控制台错误')
    console.log('点击贯穿测试全部通过')
  } finally {
    await miniProgram.close()
  }
}

main().catch(error => {
  console.error(error.message)
  process.exit(1)
})
