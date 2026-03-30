<template>
  <div class="slide-content">
    <!-- 图片 -->
    <template v-if="photo?.type === 'photo'">
      <img
        :src="previewUrl"
        class="slide-media"
        @load="onLoaded"
        @error="onError"
        draggable="false"
      />
    </template>

    <!-- 支持的视频格式 -->
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

    <!-- 不支持的视频格式 -->
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

    <!-- 空状态 -->
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

const emit = defineEmits(['loaded', 'error'])

const videoRef = ref(null)

// 监听当前 slide 变化，控制视频播放
watch(() => props.isCurrent, (isCurrent) => {
  if (!videoRef.value) return

  if (isCurrent) {
    // 切换到当前 slide 时自动播放
    videoRef.value.play().catch(() => {
      // 自动播放可能被浏览器阻止，忽略错误
    })
  } else {
    // 离开当前 slide 时暂停并重置
    videoRef.value.pause()
    videoRef.value.currentTime = 0
  }
})

// 支持的媒体格式
const SUPPORTED_VIDEO_FORMATS = ['.mp4', '.webm', '.ogg', '.mov', '.livp']

const isSupportedVideo = computed(() => {
  if (!props.photo || props.photo.type !== 'video') return false
  const filename = props.photo.name.toLowerCase()
  return SUPPORTED_VIDEO_FORMATS.some(ext => filename.endsWith(ext))
})

const videoFormat = computed(() => {
  if (!props.photo) return ''
  const ext = props.photo.name.substring(props.photo.name.lastIndexOf('.'))
  return ext.toUpperCase()
})

const previewUrl = computed(() => {
  if (!props.photo) return ''
  return `/preview/${encodeURIComponent(props.photo.name)}`
})

const videoUrl = computed(() => {
  if (!props.photo || props.photo.type !== 'video') return ''
  const filename = props.photo.name
  const lowerName = filename.toLowerCase()

  if (lowerName.endsWith('.livp')) {
    return `/livp/${encodeURIComponent(filename)}`
  } else {
    return `/video/${encodeURIComponent(filename)}`
  }
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
