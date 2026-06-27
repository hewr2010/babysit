<template>
  <view class="viewer-page" :style="{ paddingTop: safeTop + 'px' }">
    <view class="viewer-header">
      <view class="back-btn" @click="goBack">
        <text class="back-icon">←</text>
        <text class="back-text">返回</text>
      </view>
      <text class="viewer-title">{{ currentIndex + 1 }} / {{ mediaList.length }}</text>
      <view class="header-placeholder"></view>
    </view>

    <swiper
      class="viewer-swiper"
      :current="currentIndex"
      @change="onSwiperChange"
    >
      <swiper-item v-for="(item, index) in mediaList" :key="item.name" class="swiper-item">
        <view
          class="media-wrapper"
          @touchstart="onTouchStart"
          @touchmove="onTouchMove"
          @touchend="onTouchEnd"
        >
          <image
            v-if="item.type === 'photo'"
            :src="previewUrl(item.name)"
            mode="aspectFit"
            class="media-image"
          />
          <video
            v-else
            :src="videoUrl(item.name)"
            :poster="thumbUrl(item.name)"
            :controls="true"
            :show-center-play-btn="true"
            :enable-progress-gesture="true"
            class="media-video"
            @play="onVideoPlay(index)"
            @pause="onVideoPause(index)"
          />
        </view>
      </swiper-item>
    </swiper>

    <view class="viewer-footer">
      <text v-if="currentItem?.date || currentItem?.time" class="media-meta">
        <text v-if="currentItem?.date">{{ currentItem.date }}</text>
        <text v-if="currentItem?.date && currentItem?.time"> · </text>
        <text v-if="currentItem?.time">{{ currentItem.time }}</text>
      </text>
      <view class="save-btn" :class="{ saving: isSaving }" @click="saveCurrent">
        <text>{{ isSaving ? '保存中...' : '保存到相册' }}</text>
      </view>
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
const safeTop = ref(44)
const playingVideos = ref(new Set())
const isSaving = ref(false)

const mediaList = computed(() => store.photos)
const currentItem = computed(() => mediaList.value[currentIndex.value])

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

function previewUrl(filename) {
  return `${MEDIA_HOST}/preview/${encodeURIComponent(filename)}`
}

function thumbUrl(filename) {
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(filename)}`
}

function videoUrl(filename) {
  const lowerName = filename.toLowerCase()
  if (lowerName.endsWith('.livp')) {
    return `${MEDIA_HOST}/livp/${encodeURIComponent(filename)}`
  }
  return `${MEDIA_HOST}/video/${encodeURIComponent(filename)}`
}

function onSwiperChange(e) {
  const newIndex = e.detail.current
  // 暂停之前播放的视频
  playingVideos.value.forEach(idx => {
    if (idx !== newIndex) {
      pauseVideo(idx)
    }
  })
  currentIndex.value = newIndex
}

function onVideoPlay(index) {
  playingVideos.value.add(index)
}

function onVideoPause(index) {
  playingVideos.value.delete(index)
}

function pauseVideo(index) {
  // 小程序没有直接操作 video 组件实例的跨平台方式，这里依赖视频失去焦点后自动暂停
  playingVideos.value.delete(index)
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

async function saveCurrent() {
  if (!currentItem.value || isSaving.value) return

  isSaving.value = true
  try {
    const url = currentItem.value.type === 'video'
      ? videoUrl(currentItem.value.name)
      : previewUrl(currentItem.value.name)

    const { tempFilePath } = await uni.downloadFile({ url })

    if (currentItem.value.type === 'video') {
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

// 下滑关闭手势
let touchStartY = 0
let touchStartX = 0
let touchStartTime = 0

function onTouchStart(e) {
  touchStartY = e.touches[0].clientY
  touchStartX = e.touches[0].clientX
  touchStartTime = Date.now()
}

function onTouchMove(e) {
  // swiper 内部处理横向滑动，这里不做拦截
}

function onTouchEnd(e) {
  const deltaY = e.changedTouches[0].clientY - touchStartY
  const deltaX = e.changedTouches[0].clientX - touchStartX
  const deltaTime = Date.now() - touchStartTime

  // 垂直下滑超过 80px，且横向偏移不大，且速度不快，则关闭
  if (deltaY > 80 && Math.abs(deltaX) < Math.abs(deltaY) * 0.5 && deltaTime < 300) {
    goBack()
  }
}
</script>

<style scoped>
.viewer-page {
  min-height: 100vh;
  background: black;
  display: flex;
  flex-direction: column;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12rpx 24rpx;
  background: rgba(0, 0, 0, 0.4);
  position: relative;
  z-index: 10;
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

.viewer-swiper {
  flex: 1;
  width: 100%;
}

.swiper-item {
  display: flex;
  align-items: center;
  justify-content: center;
}

.media-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.media-image {
  width: 100%;
  height: 100%;
}

.media-video {
  width: 100%;
  height: 100%;
}

.viewer-footer {
  padding: 24rpx 32rpx calc(24rpx + env(safe-area-inset-bottom));
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
}

.media-meta {
  color: rgba(255, 255, 255, 0.85);
  font-size: 24rpx;
  flex-shrink: 0;
}

.save-btn {
  padding: 16rpx 32rpx;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
  border-radius: 24rpx;
  font-size: 26rpx;
  text-align: center;
  font-weight: 500;
  white-space: nowrap;
}

.save-btn.saving {
  opacity: 0.7;
}
</style>
