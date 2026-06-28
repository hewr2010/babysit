<template>
  <view class="home">
    <view v-if="initError" class="error-banner">
      <text class="error-text">{{ initError }}</text>
    </view>
    <scroll-view
      scroll-y
      class="main-scroll"
      :scroll-into-view="scrollIntoView"
      scroll-with-animation
    >
      <Header @open-baby="babyModalVisible = true" />
      <view class="main-content">
        <GrowthSection id="growth-section" />
        <MilestoneTimeline @open-photo="openPhotoViewer" />
        <PhotoSection id="photo-section" @open-photo="openPhotoViewer" />
      </view>
      <view class="safe-area"></view>
    </scroll-view>

    <TabBar :current-tab="currentTab" @select="onTabSelect" @record="showRecordOptions" />

    <BabyModal :visible="babyModalVisible" @close="babyModalVisible = false" />
    <GrowthModal :visible="growthModalVisible" :type="growthType" @close="growthModalVisible = false" />
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { MEDIA_HOST } from '@/platform'
import Header from '@/components/Header.vue'
import GrowthSection from '@/components/GrowthSection.vue'
import PhotoSection from '@/components/PhotoSection.vue'
import MilestoneTimeline from '@/components/MilestoneTimeline.vue'
import TabBar from '@/components/TabBar.vue'
import BabyModal from '@/components/BabyModal.vue'
import GrowthModal from '@/components/GrowthModal.vue'

const store = useAppStore()

const currentTab = ref('growth')
const scrollIntoView = ref('')
const babyModalVisible = ref(false)
const growthModalVisible = ref(false)
const growthType = ref('height')
const initError = ref('')

onMounted(async () => {
  console.log('[index] onMounted')
  try {
    await store.init()
    console.log('[index] init done')
  } catch (e) {
    const detail = e && (e.errMsg || e.message || JSON.stringify(e))
    const text = `数据加载失败\n${detail}`
    initError.value = text
    console.error('init failed:', e)
    uni.showModal({
      title: '加载失败',
      content: text,
      showCancel: false,
      confirmText: '知道了'
    })
  }
})

function onTabSelect(tab) {
  currentTab.value = tab
  if (tab === 'growth') {
    scrollIntoView.value = 'growth-section'
  } else if (tab === 'photos') {
    scrollIntoView.value = 'photo-section'
  }
  setTimeout(() => {
    scrollIntoView.value = ''
  }, 300)
}

function showRecordOptions() {
  uni.showActionSheet({
    itemList: ['记录身高', '记录体重'],
    success: (res) => {
      growthType.value = res.tapIndex === 0 ? 'height' : 'weight'
      growthModalVisible.value = true
    }
  })
}

function videoUrl(filename) {
  const lowerName = filename.toLowerCase()
  if (lowerName.endsWith('.livp')) {
    return `${MEDIA_HOST}/livp/${encodeURIComponent(filename)}`
  }
  return `${MEDIA_HOST}/video/${encodeURIComponent(filename)}`
}

function openPhotoViewer(index) {
  if (!store.photos.length) return

  // uni.previewMedia 最多支持 50 个 source，取当前项附近的窗口
  const total = store.photos.length
  const MAX_SOURCES = 50
  let start = 0
  let end = total
  if (total > MAX_SOURCES) {
    const half = Math.floor(MAX_SOURCES / 2)
    start = Math.max(0, index - half)
    end = Math.min(total, start + MAX_SOURCES)
    if (end - start < MAX_SOURCES) {
      start = Math.max(0, end - MAX_SOURCES)
    }
  }

  const windowed = store.photos.slice(start, end)
  const sources = windowed.map(p => {
    if (p.type === 'video') {
      return {
        url: videoUrl(p.name),
        type: 'video',
        poster: `${MEDIA_HOST}/thumb/${encodeURIComponent(p.name)}`
      }
    }
    return {
      url: `${MEDIA_HOST}/preview/${encodeURIComponent(p.name)}`,
      type: 'image'
    }
  })

  uni.previewMedia({
    sources,
    current: index - start,
    showmenu: true,
    success: () => console.log('[previewMedia] success'),
    fail: (err) => console.error('[previewMedia] fail', err)
  })
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #faf5f7;
}

.error-banner {
  background: #fee2e2;
  padding: 24rpx 32rpx;
  border-bottom: 2rpx solid #fecaca;
}

.error-text {
  color: #991b1b;
  font-size: 24rpx;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.main-scroll {
  height: 100vh;
  padding-bottom: 128rpx;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
  padding: 32rpx 32rpx 0;
}

.safe-area {
  height: 160rpx;
}
</style>
