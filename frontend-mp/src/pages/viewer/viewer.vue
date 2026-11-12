<template>
  <view class="native-preview-launch">
    <text v-if="loading">正在准备媒体…</text>
    <template v-else-if="loadError">
      <text class="load-error">{{ loadError }}</text>
      <button class="primary-button" @click="openPreview">重试</button>
      <button class="secondary-button" @click="goHome">返回首页</button>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { nativePreviewOptions } from '@/services/media'
import { requireAuth } from '@/services/auth'
import { useAppStore } from '@/stores/app'
import { decodeMediaName } from '@/utils/share'

const store = useAppStore()
const loading = ref(true)
const loadError = ref('')
const currentIndex = ref(0)

onLoad(async options => {
  if (!requireAuth()) return
  try {
    if (options.media) await openSharedMedia(options)
    else {
      if (!store.media.length) await store.loadAlbum()
      const index = Number.parseInt(options.index || '0', 10)
      currentIndex.value = Number.isInteger(index) && index >= 0 && index < store.media.length ? index : 0
    }
    await openPreview()
  } catch (error) {
    loading.value = false
    loadError.value = error.message || '媒体加载失败'
  }
})

async function openSharedMedia(options) {
  const mediaName = decodeMediaName(options.media)
  let index = store.media.findIndex(item => item.name === mediaName)
  const year = Number(options.year)
  const month = Number(options.month)
  if (index < 0 && Number.isInteger(year) && Number.isInteger(month) && month >= 1 && month <= 12) {
    store.year = year
    store.month = month
    await store.loadAlbum()
    index = store.media.findIndex(item => item.name === mediaName)
  }
  if (index < 0) throw new Error('分享的内容不存在或尚未同步')
  currentIndex.value = index
}

async function openPreview() {
  loading.value = true
  loadError.value = ''
  if (!store.media[currentIndex.value]) {
    loading.value = false
    loadError.value = '没有可预览的媒体'
    return
  }
  uni.previewMedia({
    ...nativePreviewOptions(store.media, currentIndex.value),
    fail: error => {
      loading.value = false
      loadError.value = error.errMsg || '媒体暂时无法播放，请重试'
    }
  })
}

function goHome() {
  if (getCurrentPages().length > 1) uni.navigateBack()
  else uni.reLaunch({ url: '/pages/index/index' })
}
</script>

<style scoped>
.native-preview-launch {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
  min-height: 100vh;
  padding: 40rpx;
  background: #111716;
  color: #ffffff;
  flex-direction: column;
  text-align: center;
}

.load-error {
  color: #f2aaaa;
}
</style>
