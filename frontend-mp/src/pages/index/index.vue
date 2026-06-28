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

function openPhotoViewer(index) {
  if (!store.photos.length) return
  const item = store.photos[index]
  if (!item) return

  if (item.type === 'video') {
    uni.navigateTo({ url: `/pages/video/video?index=${index}` })
    return
  }

  const photoIndex = store.photos.filter(p => p.type === 'photo').findIndex(p => p.name === item.name)
  if (photoIndex >= 0) {
    uni.navigateTo({ url: `/pages/viewer/viewer?index=${photoIndex}` })
  }
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
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
  padding: 32rpx 32rpx 0;
}

.safe-area {
  height: calc(160rpx + env(safe-area-inset-bottom));
}
</style>
