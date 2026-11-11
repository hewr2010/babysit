import { API_HOST, MAX_DOWNLOAD_SIZE } from '@/config'
import { authorizedUrl } from '@/services/auth'
import { previewWindow } from '@/utils/album'

function encoded(filename) {
  return encodeURIComponent(filename)
}

export function thumbUrl(filename) {
  return authorizedUrl(`${API_HOST}/thumb/${encoded(filename)}`)
}

export function previewUrl(filename) {
  return authorizedUrl(`${API_HOST}/preview/${encoded(filename)}`)
}

export function videoUrl(item) {
  const route = item.name.toLowerCase().endsWith('.livp') ? 'livp' : 'video'
  return authorizedUrl(`${API_HOST}/${route}/${encoded(item.name)}`)
}

export function nativePreviewOptions(media, index) {
  const { start, items } = previewWindow(media, index)
  return {
    current: index - start,
    sources: items.map(item => ({
      url: item.type === 'video' ? videoUrl(item) : previewUrl(item.name),
      poster: thumbUrl(item.name),
      type: item.type === 'video' ? 'video' : 'image'
    }))
  }
}

function download(url) {
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url,
      success: response => {
        if (response.statusCode >= 200 && response.statusCode < 300) resolve(response.tempFilePath)
        else reject(new Error(`下载失败 (${response.statusCode})`))
      },
      fail: error => reject(new Error(error.errMsg || '下载失败'))
    })
  })
}

export async function saveToAlbum(item) {
  if ((item.size || 0) > MAX_DOWNLOAD_SIZE) {
    throw new Error('文件超过 50MB，无法保存到相册')
  }
  const isVideo = item.type === 'video'
  const url = isVideo ? videoUrl(item) : authorizedUrl(`${API_HOST}/api/download/${encoded(item.name)}`)
  const filePath = await download(url)
  await new Promise((resolve, reject) => {
    const options = {
      filePath,
      success: resolve,
      fail: () => reject(new Error('保存失败，请检查相册权限'))
    }
    if (isVideo) uni.saveVideoToPhotosAlbum(options)
    else uni.saveImageToPhotosAlbum(options)
  })
}
