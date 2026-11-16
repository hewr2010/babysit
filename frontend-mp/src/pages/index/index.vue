<template>
  <view class="home-page">
    <AppHeader @edit="babyVisible = true" />
    <view v-if="loading" class="initial-state">正在加载成长记录…</view>
    <view v-else-if="loadError" class="initial-state load-error">
      <text>{{ loadError }}</text>
      <button class="secondary-button retry-button" @click="initialize">重新加载</button>
    </view>
    <view v-else class="home-content">
      <GrowthSection id="growth-section" @add="openGrowth" />
      <MilestoneSection @open="openMilestone" />
      <AlbumSection id="album-section" @open="openMedia" @actions="onMediaActions" />
    </view>
    <NativeTabBar :current="currentTab" @select="scrollToSection" @record="showRecordOptions" />
    <BabyEditor :visible="babyVisible" @close="babyVisible = false" />
    <GrowthEditor :visible="growthVisible" :type="growthType" @close="growthVisible = false" />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad, onShareAppMessage } from '@dcloudio/uni-app'
import AlbumSection from '@/components/AlbumSection.vue'
import AppHeader from '@/components/AppHeader.vue'
import BabyEditor from '@/components/BabyEditor.vue'
import GrowthEditor from '@/components/GrowthEditor.vue'
import GrowthSection from '@/components/GrowthSection.vue'
import MilestoneSection from '@/components/MilestoneSection.vue'
import NativeTabBar from '@/components/NativeTabBar.vue'
import { useAppStore } from '@/stores/app'
import { request } from '@/services/api'
import { hlsUrl, nativePreviewOptions, previewUrl, thumbUrl } from '@/services/media'
import { requireAuth } from '@/services/auth'
import { mediaSharePath } from '@/utils/share'

const store = useAppStore()
const loading = ref(true)
const loadError = ref('')
const babyVisible = ref(false)
const growthVisible = ref(false)
const growthType = ref('height')
const currentTab = ref('growth')
const sharedMedia = ref(null)
onShareAppMessage(() => {
  if (!sharedMedia.value) return { title: '宝宝成长日志', path: '/pages/index/index' }
  return {
    title: `${store.baby?.name || '宝宝'}的${sharedMedia.value.type === 'video' ? '新视频' : '新照片'}`,
    imageUrl: sharedMedia.value.type === 'video' ? thumbUrl(sharedMedia.value.name) : previewUrl(sharedMedia.value.name),
    path: mediaSharePath(sharedMedia.value)
  }
})

onLoad(() => {
  if (requireAuth()) initialize()
})

function onMediaActions(item) {
  sharedMedia.value = item
}

async function initialize() {
  loading.value = true
  loadError.value = ''
  try {
    await store.initialize()
  } catch (error) {
    loadError.value = error.message || '数据加载失败'
  } finally {
    loading.value = false
  }
}

function openGrowth(type) {
  growthType.value = type
  growthVisible.value = true
}

function scrollToSection(tab) {
  currentTab.value = tab
  uni.pageScrollTo({
    selector: tab === 'growth' ? '#growth-section' : '#album-section',
    duration: 250
  })
}

function showRecordOptions() {
  uni.showActionSheet({
    itemList: ['记录身高', '记录体重'],
    success: result => openGrowth(result.tapIndex === 0 ? 'height' : 'weight')
  })
}

function openWithHls(index, item) {
  const options = nativePreviewOptions(store.media, index)
  const position = options.sources.findIndex(source => source.url.includes(encodeURIComponent(item.name)))
  if (position >= 0) {
    options.sources[position] = { ...options.sources[position], url: hlsUrl(item) }
  }
  uni.previewMedia({
    ...options,
    fail: () => setTimeout(() => openMedia(index, 1), 3000)
  })
}

async function pollUntilReady(item, index) {
  const deadline = Date.now() + 180000
  while (Date.now() < deadline) {
    try {
      const status = await request(`/media/status/${encodeURIComponent(item.name)}`)
      if (status.state === 'hls_failed') {
        uni.hideLoading()
        store.markMediaReady(item.name, { preview_ready: true, video_ready: false })
        uni.showModal({
          title: '拉流失败',
          content: '该视频码率过高，在线低清流转码中，请稍后再试。封面图可正常查看。',
          confirmText: '知道了',
          showCancel: false
        })
        return
      }
      if (item.type === 'video' && status.hls_ready && !status.video_ready) {
        // HLS 分段边转边播：起播只等前几个分段，完整内容随转码增长
        uni.hideLoading()
        openWithHls(index, item)
        return
      }
      const done = item.type === 'video' ? status.video_ready : status.preview_ready
      if (done) {
        store.markMediaReady(item.name, status)
        uni.hideLoading()
        const freshIndex = store.media.findIndex(entry => entry.name === item.name)
        openMedia(freshIndex >= 0 ? freshIndex : index, 1)
        return
      }
    } catch (error) { /* 网络抖动时下一轮再试 */ }
    await new Promise(resolve => setTimeout(resolve, 2000))
  }
  uni.hideLoading()
  uni.showModal({
    title: '恢复时间较长',
    content: '媒体仍在从网盘恢复，请稍后手动重试。',
    confirmText: '重试',
    cancelText: '返回',
    success: result => {
      if (result.confirm) openMedia(index)
    }
  })
}

async function openMilestone(item) {
  try {
    const index = await store.openMediaMonth(item)
    if (index >= 0) openMedia(index)
    else uni.showToast({ title: '对应媒体尚未同步', icon: 'none' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  }
}
</script>

<style scoped>
.home-content {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
  padding: 32rpx 32rpx calc(160rpx + env(safe-area-inset-bottom));
}

.initial-state {
  padding: 96rpx 40rpx;
  color: #6b7280;
  text-align: center;
}

.load-error {
  color: #b91c1c;
  white-space: pre-wrap;
}

.retry-button {
  margin-top: 28rpx;
}

</style>
