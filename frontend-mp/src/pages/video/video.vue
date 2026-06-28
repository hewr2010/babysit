<template>
  <view class="video-page">
    <view class="nav-bar" :style="{ paddingTop: safeTop + 'px' }">
      <view class="nav-content">
        <view class="back-btn" @click="goBack">
          <text class="back-icon">←</text>
          <text class="back-text">返回</text>
        </view>
        <text class="nav-title">视频播放</text>
        <view class="nav-placeholder"></view>
      </view>
    </view>

    <video
      :src="videoUrl"
      :title="videoName"
      :poster="posterUrl"
      object-fit="cover"
      controls
      class="video-player"
      @error="onVideoError"
    />
    <view v-if="videoError" class="video-error">
      <text>{{ videoError }}</text>
    </view>
    <view class="video-info">
      <text class="video-name">{{ videoName }}</text>
      <button class="save-btn" :disabled="saving" @click="saveVideo">
        <text v-if="saving" class="btn-spinner"></text>
        <text v-else>保存到相册</text>
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { MEDIA_HOST } from '@/platform'

const videoUrl = ref('')
const videoName = ref('')
const saving = ref(false)
const safeTop = ref(44)
const videoError = ref('')

const posterUrl = computed(() => {
  if (!videoName.value) return ''
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(videoName.value)}`
})

onLoad((options) => {
  if (options.url) {
    videoUrl.value = decodeURIComponent(options.url)
  }
  if (options.name) {
    videoName.value = decodeURIComponent(options.name)
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

.video-player {
  width: 100vw;
  flex: 1;
  min-height: 60vh;
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

.video-info {
  width: 100%;
  padding: 40rpx;
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24rpx;
  box-sizing: border-box;
}

.video-name {
  color: white;
  font-size: 28rpx;
  text-align: center;
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
