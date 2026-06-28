<template>
  <view class="viewer-page" :style="{ paddingTop: safeTop + 'px' }">
    <view class="viewer-header">
      <view class="back-btn" @click="goBack">
        <text class="back-icon">←</text>
        <text class="back-text">返回</text>
      </view>
      <text class="viewer-title">{{ currentIndex + 1 }} / {{ photoList.length }}</text>
      <view class="header-placeholder"></view>
    </view>

    <swiper
      class="viewer-swiper"
      :current="currentIndex"
      @change="onSwiperChange"
      @touchstart="onTouchStart"
      @touchend="onTouchEnd"
    >
      <swiper-item
        v-for="(item, i) in photoList"
        :key="item.name"
        class="swiper-item"
      >
        <view
          v-if="isInWindow(i)"
          class="media-wrapper"
        >
          <!-- 模糊缩略图占位，立刻显示 -->
          <image
            :src="thumbUrl(item.name)"
            mode="aspectFill"
            class="media-thumb"
            @error="onThumbError(i)"
          />
          <!-- 清晰预览图，铺满全屏 -->
          <image
            :src="previewUrl(item.name)"
            mode="aspectFill"
            class="media-image"
            @load="onImageLoad(i)"
            @error="onImageError(i)"
          />
        </view>
      </swiper-item>
    </swiper>

    <view class="viewer-footer">
      <text v-if="currentItem?.date || currentItem?.time" class="media-meta">
        {{ [currentItem?.date, currentItem?.time].filter(Boolean).join(' · ') }}
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
const isSaving = ref(false)
const loadedSet = ref(new Set())
const errorSet = ref(new Set())

const photoList = computed(() => store.photos.filter(p => p.type === 'photo'))
const currentItem = computed(() => photoList.value[currentIndex.value])

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
  preloadWindow(currentIndex.value)
})

function thumbUrl(filename) {
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(filename)}`
}

function previewUrl(filename) {
  return `${MEDIA_HOST}/preview/${encodeURIComponent(filename)}`
}

function isInWindow(i) {
  return Math.abs(i - currentIndex.value) <= 1
}

function onSwiperChange(e) {
  const newIndex = e.detail.current
  currentIndex.value = newIndex
  preloadWindow(newIndex)
}

function onImageLoad(i) {
  loadedSet.value.add(i)
  errorSet.value.delete(i)
}

function onImageError(i) {
  errorSet.value.add(`preview-${i}`)
  console.error(`[viewer] preview image load error at index ${i}`)
}

function onThumbError(i) {
  errorSet.value.add(`thumb-${i}`)
  console.error(`[viewer] thumb image load error at index ${i}`)
}

function preloadWindow(center) {
  const total = photoList.value.length
  const preloadList = []
  for (let offset = -1; offset <= 2; offset++) {
    const idx = center + offset
    if (idx < 0 || idx >= total) continue
    const item = photoList.value[idx]
    if (item && !loadedSet.value.has(idx)) {
      preloadList.push(previewUrl(item.name))
    }
  }
  if (preloadList.length) {
    preloadImages(preloadList)
  }
}

function preloadImages(urls) {
  urls.forEach(url => {
    uni.downloadFile({ url, success: () => {} })
  })
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

async function saveCurrent() {
  if (!currentItem.value || isSaving.value) return

  isSaving.value = true
  try {
    const url = `${MEDIA_HOST}/api/download/${encodeURIComponent(currentItem.value.name)}`
    const { tempFilePath } = await uni.downloadFile({ url })
    await uni.saveImageToPhotosAlbum({ filePath: tempFilePath })
    uni.showToast({ title: '已保存', icon: 'success' })
  } catch (e) {
    console.error('Failed to save photo:', e)
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

function onTouchEnd(e) {
  const deltaY = e.changedTouches[0].clientY - touchStartY
  const deltaX = e.changedTouches[0].clientX - touchStartX
  const deltaTime = Date.now() - touchStartTime

  if (deltaY > 80 && Math.abs(deltaX) < Math.abs(deltaY) * 0.5 && deltaTime < 300) {
    goBack()
  }
}
</script>

<style scoped>
.viewer-page {
  height: 100vh;
  background: black;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
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
  background: black;
}

.swiper-item {
  display: flex;
  align-items: center;
  justify-content: center;
}

.media-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  background: #1a1a1a;
  overflow: hidden;
}

.media-thumb,
.media-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.media-thumb {
  filter: blur(20rpx) brightness(0.6);
  transform: scale(1.1);
  z-index: 1;
}

.media-image {
  z-index: 2;
}

.viewer-footer {
  padding: 24rpx 32rpx calc(48rpx + env(safe-area-inset-bottom));
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  flex-shrink: 0;
  min-height: 112rpx;
  box-sizing: border-box;
}

.media-meta {
  color: rgba(255, 255, 255, 0.85);
  font-size: 24rpx;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  flex-shrink: 0;
}

.save-btn.saving {
  opacity: 0.7;
}
</style>
