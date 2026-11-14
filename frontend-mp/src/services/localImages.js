import { reactive } from 'vue'

// iOS 上 <image> 组件拒绝加载 http 明文地址（ATS），wx.request/downloadFile
// 在调试模式下不受此限，因此统一先下载为本地临时文件再渲染。
const state = reactive({ map: {} })
const pending = new Set()

export function preloadImages(urls) {
  for (const url of urls) {
    if (!url || state.map[url] || pending.has(url)) continue
    pending.add(url)
    uni.downloadFile({
      url,
      success: response => {
        if (response.statusCode === 200 && response.tempFilePath) {
          state.map[url] = response.tempFilePath
        }
      },
      complete: () => pending.delete(url)
    })
  }
}

export function localImage(url) {
  return state.map[url] || ''
}
