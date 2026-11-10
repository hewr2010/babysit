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
        :src="videoUrl"
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
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

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

watch(isZoomed, value => emit('zoom-change', value), { immediate: true })
watch(() => props.photo, resetZoom)
watch(() => props.isCurrent, (isCurrent) => {
  if (!videoRef.value) return
  if (isCurrent) {
    videoRef.value.play().catch(() => {})
  } else {
    videoRef.value.pause()
    videoRef.value.currentTime = 0
  }
})

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
const previewUrl = computed(() => {
  if (!props.photo) return ''
  return `/preview/${encodeURIComponent(props.photo.name)}`
})
const videoUrl = computed(() => {
  if (!props.photo || props.photo.type !== 'video') return ''
  const filename = props.photo.name
  return filename.toLowerCase().endsWith('.livp')
    ? `/livp/${encodeURIComponent(filename)}`
    : `/video/${encodeURIComponent(filename)}`
})

function onLoaded() {
  emit('loaded')
}
function onError() {
  emit('error', '图片加载失败')
}
function onVideoError() {
  emit('error', '视频加载失败')
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
</style>
