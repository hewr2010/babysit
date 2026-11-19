import { request } from '@/services/api'
import { hlsUrl, nativePreviewOptions, previewUrl, videoUrl } from '@/services/media'

const MAX_PREVIEW_ATTEMPTS = 20
const RECOVERY_TIMEOUT = 180000

function isCold(item) {
  return item.type === 'video' ? item.video_ready === false : item.preview_ready === false
}

function recoveryUrl(item) {
  return item.type === 'video' ? videoUrl(item) : previewUrl(item.name)
}

function isNavigationTimingError(message) {
  return message.includes('called too early') || message.includes('cannot find navigation')
}

function isColdPlaybackError(message) {
  return /not ready|CACHE_COLD|503|cannot find media|media.*fail/i.test(message)
}

export function createMediaPreview({ getMedia, onState }) {
  let generation = 0
  let timer = null
  let timerResolve = null
  let currentIndex = 0

  function emit(ticket, state) {
    if (ticket === generation) onState(state)
  }

  function schedule(ticket, callback, delay) {
    clearTimeout(timer)
    timerResolve = null
    timer = setTimeout(() => {
      if (ticket === generation) callback()
    }, delay)
  }

  function wait(ticket, delay) {
    return new Promise(resolve => {
      clearTimeout(timer)
      timerResolve = resolve
      timer = setTimeout(() => {
        timerResolve = null
        resolve(ticket === generation)
      }, delay)
    })
  }

  function fail(ticket, message = '媒体暂时无法播放，请重试') {
    emit(ticket, { phase: 'error', message })
  }

  function present(ticket, index, attempt = 0, overrideUrl = '', allowHls = true) {
    const media = getMedia()
    const item = media[index]
    if (!item) {
      fail(ticket, '没有可预览的媒体')
      return
    }
    currentIndex = index
    emit(ticket, { phase: attempt ? 'retrying' : 'opening', attempt, item })
    const options = nativePreviewOptions(media, index)
    if (overrideUrl) {
      const sourcePosition = options.sources.findIndex(source => source.url === videoUrl(item))
      if (sourcePosition >= 0) options.sources[sourcePosition] = { ...options.sources[sourcePosition], url: overrideUrl }
    }
    uni.previewMedia({
      ...options,
      success: () => emit(ticket, { phase: 'previewing', item }),
      fail: error => {
        if (ticket !== generation) return
        const message = error.errMsg || ''
        if (overrideUrl) {
          recover(ticket, item, index, false)
          return
        }
        if (isNavigationTimingError(message) && attempt < 3) {
          schedule(ticket, () => present(ticket, index, attempt + 1, '', allowHls), 300)
          return
        }
        if (isColdPlaybackError(message) && attempt === 0) {
          recover(ticket, item, index, allowHls)
          return
        }
        if (attempt < MAX_PREVIEW_ATTEMPTS) {
          schedule(ticket, () => present(ticket, index, attempt + 1, '', allowHls), 3000)
          return
        }
        fail(ticket)
      }
    })
  }

  async function recover(ticket, item, index, allowHls = true) {
    emit(ticket, { phase: 'recovering', item })
    uni.request({ url: recoveryUrl(item), timeout: 30000, fail: () => {} })
    const deadline = Date.now() + RECOVERY_TIMEOUT
    while (ticket === generation && Date.now() < deadline) {
      try {
        const status = await request(`/media/status/${encodeURIComponent(item.name)}`)
        if (ticket !== generation) return
        if (status.state === 'hls_failed') {
          fail(ticket, '在线转码暂时失败，请稍后重试')
          return
        }
        if (allowHls && item.type === 'video' && status.hls_ready && !status.video_ready) {
          present(ticket, index, 1, hlsUrl(item), false)
          return
        }
        const done = item.type === 'video' ? status.video_ready : status.preview_ready
        if (done) {
          Object.assign(item, status)
          present(ticket, index, 1, '', allowHls)
          return
        }
      } catch (error) {}
      await wait(ticket, 2000)
    }
    if (ticket === generation) fail(ticket, '恢复时间较长，请稍后重试')
  }

  async function open(index) {
    controller.cancel()
    const ticket = generation
    currentIndex = index
    const item = getMedia()[index]
    if (!item) {
      fail(ticket, '没有可预览的媒体')
      return
    }
    if (isCold(item)) {
      await recover(ticket, item, index)
      return
    }
    present(ticket, index)
  }

  const controller = {
    open,
    retry() { return open(currentIndex) },
    cancel() {
      generation += 1
      clearTimeout(timer)
      if (timerResolve) timerResolve(false)
      timerResolve = null
    }
  }
  return controller
}
