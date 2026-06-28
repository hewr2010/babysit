const automator = require('miniprogram-automator')
const path = require('path')

const projectPath = path.resolve(__dirname, '../dist/build/mp-weixin')
const cliPath = '/Applications/wechatwebdevtools.app/Contents/MacOS/cli'
const outDir = path.resolve(__dirname, '../')

const sleep = ms => new Promise(r => setTimeout(r, ms))

async function screenshot(miniProgram, name) {
  const file = path.join(outDir, `screenshot_${name}.png`)
  await miniProgram.screenshot({ path: file })
  console.log(`Screenshot saved: ${file}`)
}

;(async () => {
  let miniProgram
  try {
    console.log('Launching WeChat DevTools...')
    miniProgram = await automator.launch({
      cliPath,
      projectPath,
      trustProject: true,
      timeout: 120000
    })

    miniProgram.on('console', msg => {
      const text = msg.text || msg.message || JSON.stringify(msg)
      console.log('[CONSOLE]', msg.type || 'log', text)
      if (msg.type === 'error') {
        console.error('[ERROR]', text)
      }
    })

    // 清空本地缓存
    const info = await miniProgram.evaluate(() => {
      try {
        wx.clearStorageSync()
      } catch (e) {}
      try {
        return wx.getStorageInfoSync()
      } catch (e) {
        return { keys: [] }
      }
    })
    console.log('Storage after clear:', info.keys)

    // 1. 授权页
    await miniProgram.reLaunch('/pages/auth/auth')
    await sleep(2000)
    await screenshot(miniProgram, 'auth')

    // 2. 首页
    await miniProgram.evaluate(() => {
      wx.setStorageSync('baby_auth_verified', 'true')
      wx.reLaunch({ url: '/pages/index/index' })
    })
    await sleep(4000)
    await screenshot(miniProgram, 'index')

    // 3. 点击相册 Tab 滚动到相册区域
    const indexPage = await miniProgram.currentPage()
    const photosTab = await indexPage.$('.tab-item:nth-child(3)')
    if (photosTab) {
      await photosTab.tap()
      await sleep(1500)
      await screenshot(miniProgram, 'index_photos_tab')

      // 3.5 点击"查看更多"验证展开
      const viewMore = await indexPage.$('.view-more-btn')
      if (viewMore) {
        await viewMore.tap()
        await sleep(1500)
        await screenshot(miniProgram, 'photos_expanded')
      }

      // 3.6 多测几个照片和视频的预览，避免音频串扰
      const mediaIndices = await miniProgram.evaluate(() => {
        const app = getApp()
        const store = app?.$vm?.$pinia?.state?.value?.app
        if (!store) return { photos: [], videos: [] }
        const photos = store.photos
          .map((p, i) => ({ ...p, originalIndex: i }))
          .filter(p => p.type === 'photo')
          .slice(0, 3)
          .map((p, i) => ({ originalIndex: p.originalIndex, photoIndex: i, name: p.name }))
        const videos = store.photos
          .map((p, i) => ({ ...p, originalIndex: i }))
          .filter(p => p.type === 'video')
          .slice(0, 3)
          .map(p => ({ originalIndex: p.originalIndex, name: p.name }))
        return { photos, videos }
      })

      const { MEDIA_HOST } = await miniProgram.evaluate(() => {
        return { MEDIA_HOST: 'https://qqing.top' }
      })

      for (let i = 0; i < mediaIndices.photos.length; i++) {
        const p = mediaIndices.photos[i]
        await miniProgram.navigateTo(`/pages/viewer/viewer?index=${p.photoIndex}`)
        await sleep(2500)
        await screenshot(miniProgram, `viewer_photo_${i}`)
        await miniProgram.navigateBack({ delta: 1 })
        await sleep(800)
      }

      for (let i = 0; i < mediaIndices.videos.length; i++) {
        const v = mediaIndices.videos[i]
        const lowerName = v.name.toLowerCase()
        const videoUrl = lowerName.endsWith('.livp')
          ? `${MEDIA_HOST}/livp/${encodeURIComponent(v.name)}`
          : `${MEDIA_HOST}/video/${encodeURIComponent(v.name)}`
        await miniProgram.navigateTo(`/pages/video/video?url=${encodeURIComponent(videoUrl)}&name=${encodeURIComponent(v.name)}`)
        await sleep(2500)
        await screenshot(miniProgram, `viewer_video_${i}`)
        await miniProgram.navigateBack({ delta: 1 })
        await sleep(800)
      }

    }

    // 4. 点击宝宝卡片打开宝宝弹窗
    const babyCard = await indexPage.$('.baby-card')
    if (babyCard) {
      await babyCard.tap()
      await sleep(1500)
      await screenshot(miniProgram, 'baby_modal')
      // 点击遮罩关闭
      const overlay = await indexPage.$('.modal-overlay')
      if (overlay) await overlay.tap()
      await sleep(800)
    }

    // 5. 点击记录按钮打开 ActionSheet
    const addTab = await indexPage.$('.tab-item.add')
    if (addTab) {
      await addTab.tap()
      await sleep(1500)
      await screenshot(miniProgram, 'record_sheet')
    }

    // 6. 切换到下个月验证月份切换
    await miniProgram.evaluate(() => {
      const app = getApp()
      const store = app?.$vm?.$pinia?.state?.value?.app
      if (store) {
        store.currentMonth += 1
        if (store.currentMonth > 12) {
          store.currentMonth = 1
          store.currentYear += 1
        }
      }
    })
    await sleep(2000)
    await screenshot(miniProgram, 'index_next_month')

    // 7. 重要时刻管理页
    await miniProgram.navigateTo('/pages/milestones/manage')
    await sleep(2500)
    await screenshot(miniProgram, 'milestones_manage')

    // 8. 视频播放页
    await miniProgram.reLaunch('/pages/video/video?url=https%3A%2F%2Fqqing.top%2Fapi%2Fplaceholder.mp4&name=test.mp4')
    await sleep(2000)
    await screenshot(miniProgram, 'video')

    await miniProgram.close()
    console.log('All screenshots done.')
    process.exit(0)
  } catch (err) {
    console.error('Screenshot failed:', err)
    if (miniProgram) await miniProgram.close().catch(() => {})
    process.exit(1)
  }
})()
