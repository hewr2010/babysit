import { reactive } from 'vue'

// iOS 上 <image> 组件拒绝加载 http 明文地址（ATS），wx.request/downloadFile
// 在调试模式下不受此限，因此统一先下载为本地临时文件再渲染。
const state = reactive({ map: {}, failed: {} })
const pending = new Set()
const attempts = {}

export function preloadImages(urls) {
  for (const url of urls) {
    if (!url || state.map[url] || pending.has(url)) continue
    pending.add(url)
    uni.downloadFile({
      url,
      success: response => {
        if (response.statusCode === 200 && response.tempFilePath) {
          state.map[url] = response.tempFilePath
          delete state.failed[url]
          delete attempts[url]
        } else scheduleRetry(url)
      },
      fail: () => scheduleRetry(url),
      complete: () => pending.delete(url)
    })
  }
}

function scheduleRetry(url) {
  attempts[url] = (attempts[url] || 0) + 1
  if (attempts[url] >= 3) {
    state.failed[url] = true
    return
  }
  setTimeout(() => preloadImages([url]), attempts[url] === 1 ? 1000 : 3000)
}

export function retryImage(url) {
  delete attempts[url]
  delete state.failed[url]
  preloadImages([url])
}

export function imageFailed(url) {
  return state.failed[url] === true
}

export function localImage(url) {
  return state.map[url] || ''
}
