<template>
  <view class="video-page">
    <view class="nav-bar" :style="{ paddingTop: safeTop + 'px' }">
      <view class="nav-content">
        <view class="back-btn" @click="goBack">
          <text class="back-icon">←</text>
          <text class="back-text">返回</text>
        </view>
        <text class="nav-title">{{ currentIndex + 1 }} / {{ store.photos.length }}</text>
        <view class="nav-placeholder"></view>
      </view>
    </view>

    <view class="video-stage" @touchstart="onTouchStart" @touchend="onTouchEnd">
      <video
        :id="`video-${currentIndex}`"
        :src="videoUrl"
        :poster="posterUrl"
        object-fit="cover"
        autoplay
        loop
        controls
        class="video-player"
        @error="onVideoError"
      />
      <view v-if="videoError" class="video-error">
        <text>{{ videoError }}</text>
      </view>

      <view class="nav-overlay nav-prev" @click="goPrev">
        <text class="nav-arrow">‹</text>
      </view>
      <view class="nav-overlay nav-next" @click="goNext">
        <text class="nav-arrow">›</text>
      </view>
    </view>

    <view class="video-info">
      <text class="video-name">{{ currentItem?.name }}</text>
      <text v-if="currentItem?.date || currentItem?.time" class="video-meta">
        {{ [currentItem?.date, currentItem?.time].filter(Boolean).join(' · ') }}
      </text>
      <button class="save-btn" :disabled="saving" @click="saveVideo">
        <text v-if="saving" class="btn-spinner"></text>
        <text v-else>保存到相册</text>
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useAppStore } from '@/stores/app'
import { MEDIA_HOST } from '@/platform'

const store = useAppStore()
const currentIndex = ref(0)
const saving = ref(false)
const safeTop = ref(44)
const videoError = ref('')

const currentItem = computed(() => store.photos[currentIndex.value])

const videoUrl = computed(() => {
  if (!currentItem.value) return ''
  const lowerName = currentItem.value.name.toLowerCase()
  if (lowerName.endsWith('.livp')) {
    return `${MEDIA_HOST}/livp/${encodeURIComponent(currentItem.value.name)}`
  }
  return `${MEDIA_HOST}/video/${encodeURIComponent(currentItem.value.name)}`
})

const posterUrl = computed(() => {
  if (!currentItem.value) return ''
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(currentItem.value.name)}`
})

onLoad((options) => {
  if (options.index) {
    currentIndex.value = parseInt(options.index, 10) || 0
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
  if (deltaTime > 300 || Math.abs(deltaX) < 50) return
  if (Math.abs(deltaX) > Math.abs(deltaY)) {
    if (deltaX < 0) goNext()
    else goPrev()
  }
}

function goPrev() {
  if (currentIndex.value <= 0) return
  navigateToIndex(currentIndex.value - 1)
}

function goNext() {
  if (currentIndex.value >= store.photos.length - 1) return
  navigateToIndex(currentIndex.value + 1)
}

function navigateToIndex(index) {
  const item = store.photos[index]
  if (!item) return
  if (item.type === 'video') {
    uni.redirectTo({ url: `/pages/video/video?index=${index}` })
  } else {
    const photoIndex = store.photos.filter(p => p.type === 'photo').findIndex(p => p.name === item.name)
    if (photoIndex >= 0) {
      uni.redirectTo({ url: `/pages/viewer/viewer?index=${photoIndex}` })
    }
  }
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

function onVideoError(e) {
  videoError.value = '视频加载失败，请检查网络或重试'
  console.error('[video] load error:', e)
}

async function saveVideo() {
  if (!videoUrl.value || saving.value) return

  saving.value = true
  try {
    const { tempFilePath } = await uni.downloadFile({ url: videoUrl.value })
    await uni.saveVideoToPhotosAlbum({ filePath: tempFilePath })
    uni.showToast({ title: '已保存', icon: 'success' })
  } catch (e) {
    console.error('Failed to save video:', e)
    uni.showToast({ title: '保存失败，请授权相册权限', icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.video-page {
  min-height: 100vh;
  background: black;
  display: flex;
  flex-direction: column;
  position: relative;
}

.nav-bar {
  width: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8rpx);
  position: relative;
  z-index: 10;
}

.nav-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 24rpx;
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

.nav-title {
  color: white;
  font-size: 30rpx;
  font-weight: 500;
}

.nav-placeholder {
  width: 110rpx;
}

.video-stage {
  flex: 1;
  width: 100%;
  min-height: 60vh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: black;
}

.video-player {
  width: 100%;
  height: 100%;
  min-height: 60vh;
  display: block;
}

.video-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 28rpx;
  text-align: center;
  padding: 24rpx;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 16rpx;
}

.nav-overlay {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 120rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.nav-prev {
  left: 0;
}

.nav-next {
  right: 0;
}

.nav-arrow {
  color: rgba(255, 255, 255, 0.6);
  font-size: 64rpx;
  font-weight: 300;
}

.video-info {
  width: 100%;
  padding: 40rpx;
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
  box-sizing: border-box;
}

.video-name {
  color: white;
  font-size: 26rpx;
  text-align: center;
  opacity: 0.9;
}

.video-meta {
  color: rgba(255, 255, 255, 0.7);
  font-size: 24rpx;
}

.save-btn {
  width: 80%;
  height: 88rpx;
  line-height: 88rpx;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
  border: none;
  border-radius: 24rpx;
  font-size: 30rpx;
  font-weight: 500;
}

.save-btn[disabled] {
  opacity: 0.5;
}

.save-btn::after {
  border: none;
}

.btn-spinner {
  display: inline-block;
  width: 32rpx;
  height: 32rpx;
  border: 4rpx solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
