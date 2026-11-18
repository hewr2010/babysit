<template>
  <div class="slide-content" :class="{ 'is-zoomed': isZoomed }">
    <template v-if="photo?.type === 'photo'">
      <img
        ref="imageRef"
        :src="previewUrl"
        class="slide-media"
        :style="mediaStyle"
        @load="onLoaded"
        @error="onError"
        @dblclick="toggleZoom"
        @wheel.prevent="handleWheel"
        @touchstart="handleTouchStart"
        @touchmove.prevent="handleTouchMove"
        @touchend="handleTouchEnd"
        @touchcancel="handleTouchEnd"
        draggable="false"
      />
    </template>

    <template v-else-if="photo?.type === 'video' && isSupportedVideo">
      <video
        ref="videoRef"
        :src="activatedVideoUrl"
        class="slide-media"
        autoplay
        muted
        loop
        playsinline
        controls
        @canplay="onLoaded"
        @loadedmetadata="onLoaded"
        @error="onVideoError"
      />
    </template>

    <template v-else-if="photo?.type === 'video' && !isSupportedVideo">
      <div class="unsupported-video">
        <img
          :src="previewUrl"
          class="slide-media"
          @load="onLoaded"
          @error="onError"
          draggable="false"
        />
        <div class="video-overlay">
          <div class="video-icon">▶</div>
          <div class="video-hint">不支持的视频格式 ({{ videoFormat }})</div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="empty-content"></div>
    </template>

    <div v-if="showRecoveryHint" class="recovery-overlay">
      <div class="recovery-spinner"></div>
      <div class="recovery-text">媒体恢复中，请稍候…</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  photo: {
    type: Object,
    default: null
  },
  isCurrent: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['loaded', 'error', 'zoom-change'])
const videoRef = ref(null)
const imageRef = ref(null)
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const pointers = ref(new Map())
const gesture = ref('')
const pinchStartDistance = ref(0)
const pinchStartScale = ref(1)
const panStartX = ref(0)
const panStartY = ref(0)
const panOriginX = ref(0)
const panOriginY = ref(0)

const isZoomed = computed(() => scale.value > 1.01)
const mediaStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  transition: gesture.value ? 'none' : 'transform 0.2s ease-out'
}))

const MAX_RETRIES = 10
const retryCount = ref(0)
const showRecoveryHint = ref(false)
let retryTimer = null
let hintTimer = null

watch(isZoomed, value => emit('zoom-change', value), { immediate: true })
watch(() => props.photo, () => {
  resetZoom()
  resetRecovery()
  scheduleHint()
})
watch(() => props.isCurrent, (isCurrent) => {
  if (!videoRef.value) return
  if (isCurrent) {
    videoRef.value.play().catch(() => {})
  } else {
    videoRef.value.pause()
    videoRef.value.currentTime = 0
  }
})
scheduleHint()
onBeforeUnmount(clearRecoveryTimers)

const SUPPORTED_VIDEO_FORMATS = ['.mp4', '.webm', '.ogg', '.mov', '.livp']
const isSupportedVideo = computed(() => {
  if (!props.photo || props.photo.type !== 'video') return false
  const filename = props.photo.name.toLowerCase()
  return SUPPORTED_VIDEO_FORMATS.some(ext => filename.endsWith(ext))
})
const videoFormat = computed(() => {
  if (!props.photo) return ''
  return props.photo.name.substring(props.photo.name.lastIndexOf('.')).toUpperCase()
})
const retrySuffix = computed(() => (retryCount.value ? `?r=${retryCount.value}` : ''))
const activated = ref(false)
watch(() => props.isCurrent, value => {
  if (value) activated.value = true
}, { immediate: true })
const activatedVideoUrl = computed(() => (activated.value ? videoUrl.value : ''))
const previewUrl = computed(() => {
  if (!props.photo) return ''
  return `/preview/${encodeURIComponent(props.photo.name)}${retrySuffix.value}`
})
const videoUrl = computed(() => {
  if (!props.photo || props.photo.type !== 'video') return ''
  const filename = props.photo.name
  const route = filename.toLowerCase().endsWith('.livp')
    ? `/livp/${encodeURIComponent(filename)}`
    : `/video/${encodeURIComponent(filename)}`
  return `${route}${retrySuffix.value}`
})

function clearRecoveryTimers() {
  clearTimeout(retryTimer)
  clearTimeout(hintTimer)
}

function resetRecovery() {
  clearRecoveryTimers()
  retryCount.value = 0
  showRecoveryHint.value = false
}

function scheduleHint() {
  clearTimeout(hintTimer)
  hintTimer = setTimeout(() => {
    showRecoveryHint.value = true
  }, 3000)
}

function retryOrFail(message) {
  if (retryCount.value >= MAX_RETRIES) {
    clearRecoveryTimers()
    emit('error', message)
    return
  }
  showRecoveryHint.value = true
  clearTimeout(retryTimer)
  retryTimer = setTimeout(() => {
    retryCount.value += 1
  }, 3000)
}

function onLoaded() {
  resetRecovery()
  emit('loaded')
}
function onError() {
  retryOrFail('图片加载失败')
}
function onVideoError() {
  retryOrFail('视频加载失败')
}

function clampScale(value) {
  return Math.min(4, Math.max(1, value))
}

function clampPan() {
  if (!imageRef.value) return
  const rect = imageRef.value.getBoundingClientRect()
  const maxX = Math.max(0, rect.width * (scale.value - 1) / 2)
  const maxY = Math.max(0, rect.height * (scale.value - 1) / 2)
  panX.value = Math.min(maxX, Math.max(-maxX, panX.value))
  panY.value = Math.min(maxY, Math.max(-maxY, panY.value))
}

function resetZoom() {
  scale.value = 1
  panX.value = 0
  panY.value = 0
  pointers.value.clear()
  gesture.value = ''
}

function toggleZoom() {
  if (isZoomed.value) {
    resetZoom()
  } else {
    scale.value = 2.5
    panX.value = 0
    panY.value = 0
  }
}

function handleWheel(event) {
  scale.value = clampScale(scale.value * (event.deltaY < 0 ? 1.15 : 0.87))
  if (!isZoomed.value) resetZoom()
  clampPan()
}

function handleTouchStart(event) {
  for (const touch of event.changedTouches) {
    pointers.value.set(touch.identifier, { x: touch.clientX, y: touch.clientY })
  }
  if (pointers.value.size === 2) {
    const [first, second] = [...pointers.value.values()]
    pinchStartDistance.value = Math.hypot(first.x - second.x, first.y - second.y)
    pinchStartScale.value = scale.value
    gesture.value = 'pinch'
  } else if (pointers.value.size === 1 && isZoomed.value) {
    const point = [...pointers.value.values()][0]
    gesture.value = 'pan'
    panStartX.value = point.x
    panStartY.value = point.y
    panOriginX.value = panX.value
    panOriginY.value = panY.value
  } else {
    gesture.value = ''
  }
}

function handleTouchMove(event) {
  if (!gesture.value) return
  for (const touch of event.changedTouches) {
    if (pointers.value.has(touch.identifier)) {
      pointers.value.set(touch.identifier, { x: touch.clientX, y: touch.clientY })
    }
  }
  if (gesture.value === 'pinch' && pointers.value.size >= 2) {
    const [first, second] = [...pointers.value.values()]
    const distance = Math.hypot(first.x - second.x, first.y - second.y)
    if (pinchStartDistance.value > 0) {
      scale.value = clampScale(pinchStartScale.value * distance / pinchStartDistance.value)
      clampPan()
    }
  } else if (gesture.value === 'pan') {
    const point = [...pointers.value.values()][0]
    panX.value = panOriginX.value + point.x - panStartX.value
    panY.value = panOriginY.value + point.y - panStartY.value
    clampPan()
  }
}

function handleTouchEnd(event) {
  for (const touch of event.changedTouches) {
    pointers.value.delete(touch.identifier)
  }
  if (pointers.value.size === 1 && isZoomed.value) {
    const point = [...pointers.value.values()][0]
    gesture.value = 'pan'
    panStartX.value = point.x
    panStartY.value = point.y
    panOriginX.value = panX.value
    panOriginY.value = panY.value
  } else if (pointers.value.size === 0) {
    gesture.value = ''
  }
}
</script>

<style scoped>
.slide-content {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.slide-media {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
  transform-origin: center center;
  will-change: transform;
}

.slide-content.is-zoomed .slide-media {
  max-width: none;
  max-height: none;
  touch-action: none;
  cursor: grab;
}

.slide-content.is-zoomed .slide-media:active {
  cursor: grabbing;
}

.empty-content {
  width: 100%;
  height: 100%;
}

.unsupported-video {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  color: white;
  pointer-events: none;
}

.video-icon {
  font-size: 72px;
  margin-bottom: 16px;
  opacity: 0.9;
}

.video-hint {
  font-size: 16px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 8px;
  opacity: 0.95;
}

.recovery-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  background: rgba(0, 0, 0, 0.35);
  color: white;
  pointer-events: none;
  z-index: 5;
}

.recovery-spinner {
  width: 34px;
  height: 34px;
  border: 3px solid rgba(255, 255, 255, 0.35);
  border-top-color: white;
  border-radius: 50%;
  animation: recovery-spin 0.9s linear infinite;
}

.recovery-text {
  font-size: 15px;
  padding: 6px 14px;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 8px;
}

@keyframes recovery-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
