<template>
  <view class="native-preview-launch">
    <text v-if="loading">{{ statusText }}</text>
    <template v-else-if="loadError">
      <text class="load-error">{{ loadError }}</text>
      <button class="primary-button" @click="openPreview">重试</button>
      <button class="secondary-button" @click="goHome">返回首页</button>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onHide, onLoad, onReady, onShow, onUnload } from '@dcloudio/uni-app'
import { createMediaPreview } from '@/services/mediaPreview'
import { requireAuth } from '@/services/auth'
import { useAppStore } from '@/stores/app'
import { decodeMediaName } from '@/utils/share'

const store = useAppStore()
const loading = ref(true)
const statusText = ref('正在准备媒体…')
const loadError = ref('')
const currentIndex = ref(0)
const pageReady = ref(false)
let initialized = false
let leaving = false
let previewOpened = false
let previewHidden = false

const preview = createMediaPreview({
  getMedia: () => store.media,
  onState: state => {
    if (state.phase === 'recovering') {
      loading.value = true
      statusText.value = '媒体恢复中…'
      loadError.value = ''
    } else if (state.phase === 'opening' || state.phase === 'retrying') {
      loading.value = true
      statusText.value = state.phase === 'retrying' ? '正在重新打开媒体…' : '正在准备媒体…'
      loadError.value = ''
    } else if (state.phase === 'previewing') {
      loading.value = false
      loadError.value = ''
      previewOpened = true
    } else if (state.phase === 'error') {
      loading.value = false
      previewOpened = false
      loadError.value = state.message
    }
  }
})

onLoad(async options => {
  if (!requireAuth()) return
  try {
    if (options.media) await openSharedMedia(options)
    else {
      if (!store.media.length) await store.loadAlbum()
      const index = Number.parseInt(options.index || '0', 10)
      currentIndex.value = Number.isInteger(index) && index >= 0 && index < store.media.length ? index : 0
    }
    initialized = true
    openWhenReady()
  } catch (error) {
    loading.value = false
    loadError.value = error.message || '媒体加载失败'
  }
})

onReady(() => {
  pageReady.value = true
  openWhenReady()
})

onHide(() => {
  if (previewOpened) previewHidden = true
})

onShow(() => {
  if (!previewOpened || !previewHidden || leaving) return
  returnHome()
})

onUnload(() => preview.cancel())

function openWhenReady() {
  if (pageReady.value && initialized && !leaving) openPreview()
}

async function openSharedMedia(options) {
  const mediaName = decodeMediaName(options.media)
  const year = Number(options.year)
  const month = Number(options.month)
  const hasMonth = Number.isInteger(year) && Number.isInteger(month) && month >= 1 && month <= 12
  const monthChanged = hasMonth && store.selectedMonthKey !== `${year}-${String(month).padStart(2, '0')}`
  if (monthChanged || !store.media.length) {
    await store.loadAlbum(hasMonth ? { year, month } : null)
  }
  const index = store.media.findIndex(item => item.name === mediaName)
  if (index < 0) throw new Error('分享的内容不存在或尚未同步')
  currentIndex.value = index
}

function openPreview() {
  previewOpened = false
  previewHidden = false
  preview.open(currentIndex.value)
}

function returnHome() {
  if (leaving) return
  leaving = true
  preview.cancel()
  uni.reLaunch({ url: '/pages/index/index' })
}

function goHome() {
  if (leaving) return
  leaving = true
  preview.cancel()
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
  box-sizing: border-box;
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
