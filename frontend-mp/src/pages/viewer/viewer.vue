<template>
  <view class="viewer-page" :style="{ paddingTop: safeTop + 'px' }">
    <!-- 背景 swiper：显示所有媒体的占位/预览图，提供切项动画 -->
    <swiper
      class="viewer-swiper"
      :current="swiperCurrent"
      :circular="false"
      :display-multiple-items="1"
      :disable-touch="true"
      @change="onSwiperChange"
      @animationfinish="onAnimationFinish"
    >
      <swiper-item
        v-for="(item, i) in mediaList"
        :key="item.name"
        class="swiper-item"
      >
        <image
          v-if="item.type === 'photo'"
          :src="previewUrl(item.name)"
          mode="aspectFit"
          class="media-image"
          lazy-load
        />
        <image
          v-else
          :src="thumbUrl(item.name)"
          mode="aspectFill"
          class="media-thumb"
          lazy-load
        />
      </swiper-item>
    </swiper>

    <!-- 视频浮层：当前项为视频时显示 -->
    <video
      v-if="currentItem?.type === 'video' && !isTransitioning"
      :id="`viewer-video`"
      ref="videoRef"
      :src="videoUrl"
      :poster="thumbUrl(currentItem.name)"
      class="viewer-video"
      object-fit="cover"
      autoplay
      loop
      :controls="false"
      :vslide-gesture="false"
      :vslide-gesture-in-fullscreen="false"
      :show-progress="false"
      :show-fullscreen-btn="false"
      :show-play-btn="false"
      :show-center-play-btn="false"
      :show-mute-btn="false"
      @play="onVideoPlay"
      @pause="onVideoPause"
      @ended="onVideoEnded"
      @error="onVideoError"
      @waiting="onVideoWaiting"
      @timeupdate="onVideoTimeUpdate"
    />

    <!-- 封面层：捕获所有手势 + UI -->
    <cover-view
      class="cover-overlay"
      @touchstart="onTouchStart"
      @touchend="onTouchEnd"
    >
      <cover-view class="cover-header">
        <cover-view class="back-btn" @click="goBack">
          <cover-view class="back-icon">←</cover-view>
          <cover-view class="back-text">返回</cover-view>
        </cover-view>
        <cover-view class="viewer-title">{{ currentIndex + 1 }} / {{ mediaList.length }}</cover-view>
        <cover-view class="header-placeholder"></cover-view>
      </cover-view>

      <!-- 中部留白用于手势 -->
      <cover-view class="cover-body"></cover-view>

      <cover-view class="cover-footer">
        <cover-view class="media-info">
          <cover-view class="media-name">{{ currentItem?.name }}</cover-view>
          <cover-view v-if="currentItem?.date || currentItem?.time" class="media-meta">
            {{ [currentItem?.date, currentItem?.time].filter(Boolean).join(' · ') }}
          </cover-view>
        </cover-view>

        <cover-view class="action-row">
          <cover-view v-if="currentItem?.type === 'video'" class="video-controls">
            <cover-view class="play-btn" @click="togglePlay">
              <cover-view class="play-text">{{ isPlaying ? '暂停' : '播放' }}</cover-view>
            </cover-view>
            <cover-view class="time-text">{{ videoTimeText }}</cover-view>
          </cover-view>

          <cover-view class="save-btn" :class="{ saving: isSaving }" @click="saveCurrent">
            <cover-view>{{ saveBtnText }}</cover-view>
          </cover-view>
        </cover-view>
      </cover-view>
    </cover-view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { useAppStore } from '@/stores/app'
import { MEDIA_HOST } from '@/platform'

const store = useAppStore()
const currentIndex = ref(0)
const swiperCurrent = ref(0)
const safeTop = ref(44)
const isSaving = ref(false)
const isTransitioning = ref(false)
const isPlaying = ref(false)
const videoDuration = ref(0)
const videoCurrentTime = ref(0)
const videoError = ref('')

const mediaList = computed(() => store.photos)
const currentItem = computed(() => mediaList.value[currentIndex.value])

const saveBtnText = computed(() => {
  if (isSaving.value) return '保存中...'
  return currentItem.value?.type === 'video' ? '保存视频' : '保存到相册'
})

const videoTimeText = computed(() => {
  if (!videoDuration.value) return ''
  return `${formatTime(videoCurrentTime.value)} / ${formatTime(videoDuration.value)}`
})

const videoUrl = computed(() => {
  if (!currentItem.value || currentItem.value.type !== 'video') return ''
  const name = currentItem.value.name
  if (name.toLowerCase().endsWith('.livp')) {
    return `${MEDIA_HOST}/livp/${encodeURIComponent(name)}`
  }
  return `${MEDIA_HOST}/video/${encodeURIComponent(name)}`
})

onLoad((options) => {
  if (options.index) {
    const idx = parseInt(options.index, 10) || 0
    currentIndex.value = idx
    swiperCurrent.value = idx
  }
})

onMounted(() => {
  try {
    const sys = uni.getSystemInfoSync()
    safeTop.value = (sys.statusBarHeight || 0) + 12
  } catch (e) {
    // 使用默认值
  }
})

onUnload(() => {
  const ctx = uni.createVideoContext('viewer-video')
  if (ctx) ctx.stop()
})

watch(currentItem, (item) => {
  videoError.value = ''
  isPlaying.value = item?.type === 'video'
  videoCurrentTime.value = 0
  videoDuration.value = 0
})

function thumbUrl(filename) {
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(filename)}`
}

function previewUrl(filename) {
  return `${MEDIA_HOST}/preview/${encodeURIComponent(filename)}`
}

function formatTime(seconds) {
  const s = Math.floor(seconds || 0)
  const m = Math.floor(s / 60)
  const rs = s % 60
  return `${m}:${rs.toString().padStart(2, '0')}`
}

let touchStartX = 0
let touchStartY = 0
let touchStartTime = 0

function onTouchStart(e) {
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
  touchStartTime = Date.now()
}

function onTouchEnd(e) {
  const deltaX = e.changedTouches[0].clientX - touchStartX
  const deltaY = e.changedTouches[0].clientY - touchStartY
  const deltaTime = Date.now() - touchStartTime

  if (deltaTime > 400) return

  if (Math.abs(deltaY) > Math.abs(deltaX) && deltaY > 60) {
    goBack()
    return
  }

  if (Math.abs(deltaX) > 60) {
    if (deltaX < 0) goNext()
    else goPrev()
  }
}

function goPrev() {
  if (currentIndex.value <= 0) return
  moveTo(currentIndex.value - 1)
}

function goNext() {
  if (currentIndex.value >= mediaList.value.length - 1) return
  moveTo(currentIndex.value + 1)
}

function moveTo(index) {
  if (index < 0 || index >= mediaList.value.length) return
  isTransitioning.value = true
  currentIndex.value = index
  swiperCurrent.value = index
}

function onSwiperChange(e) {
  const newIndex = e.detail.current
  if (newIndex !== currentIndex.value) {
    currentIndex.value = newIndex
  }
}

function onAnimationFinish() {
  nextTick(() => {
    isTransitioning.value = false
  })
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

function togglePlay() {
  const ctx = uni.createVideoContext('viewer-video')
  if (!ctx) return
  if (isPlaying.value) {
    ctx.pause()
  } else {
    ctx.play()
  }
}

function onVideoPlay() {
  isPlaying.value = true
}

function onVideoPause() {
  isPlaying.value = false
}

function onVideoEnded() {
  isPlaying.value = false
}

function onVideoError(e) {
  videoError.value = '视频加载失败'
  isPlaying.value = false
  console.error('[viewer] video error:', e)
}

function onVideoWaiting() {
  // 缓冲中
}

function onVideoTimeUpdate(e) {
  videoCurrentTime.value = e.detail.currentTime || 0
  videoDuration.value = e.detail.duration || 0
}

async function saveCurrent() {
  if (!currentItem.value || isSaving.value) return

  const item = currentItem.value
  const isVideo = item.type === 'video'

  if (item.size && item.size > 50 * 1024 * 1024) {
    const mb = (item.size / 1024 / 1024).toFixed(1)
    uni.showModal({
      title: '文件过大',
      content: `该文件 ${mb}MB，超过 50MB 限制，无法保存到相册。`,
      showCancel: false,
      confirmText: '知道了'
    })
    return
  }

  isSaving.value = true
  try {
    const url = isVideo
      ? videoUrl.value
      : `${MEDIA_HOST}/api/download/${encodeURIComponent(item.name)}`

    const { tempFilePath } = await uni.downloadFile({ url })

    if (isVideo) {
      await uni.saveVideoToPhotosAlbum({ filePath: tempFilePath })
    } else {
      await uni.saveImageToPhotosAlbum({ filePath: tempFilePath })
    }

    uni.showToast({ title: '已保存', icon: 'success' })
  } catch (e) {
    console.error('Failed to save media:', e)
    uni.showToast({ title: '保存失败，请授权相册权限', icon: 'none' })
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.viewer-page {
  height: 100vh;
  background: black;
  position: relative;
  overflow: hidden;
}

.viewer-swiper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.swiper-item {
  display: flex;
  align-items: center;
  justify-content: center;
  background: black;
}

.media-image,
.media-thumb {
  width: 100%;
  height: 100%;
}

.viewer-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
}

.cover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 3;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.cover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12rpx 24rpx;
  background: rgba(0, 0, 0, 0.4);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 16rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.15);
}

.back-icon {
  color: white;
  font-size: 32rpx;
  line-height: 1;
}

.back-text {
  color: white;
  font-size: 26rpx;
}

.viewer-title {
  color: white;
  font-size: 28rpx;
  font-weight: 500;
}

.header-placeholder {
  width: 110rpx;
}

.cover-body {
  flex: 1;
}

.cover-footer {
  padding: 24rpx 32rpx calc(48rpx + env(safe-area-inset-bottom));
  background: rgba(0, 0, 0, 0.5);
}

.media-info {
  margin-bottom: 24rpx;
}

.media-name {
  color: white;
  font-size: 26rpx;
  text-align: center;
  opacity: 0.9;
  word-break: break-all;
}

.media-meta {
  color: rgba(255, 255, 255, 0.7);
  font-size: 24rpx;
  text-align: center;
  margin-top: 8rpx;
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
}

.video-controls {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.play-btn {
  padding: 12rpx 24rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 24rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.3);
}

.play-text {
  color: white;
  font-size: 26rpx;
}

.time-text {
  color: rgba(255, 255, 255, 0.8);
  font-size: 24rpx;
}

.save-btn {
  padding: 16rpx 32rpx;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  border-radius: 24rpx;
}

.save-btn cover-view {
  color: white;
  font-size: 26rpx;
  font-weight: 500;
}

.save-btn.saving {
  opacity: 0.7;
}
</style>
