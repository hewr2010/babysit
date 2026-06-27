<template>
  <view class="home">
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

onMounted(async () => {
  console.log('[index] onMounted')
  try {
    await store.init()
    console.log('[index] init done')
  } catch (e) {
    console.error('init failed:', e)
    uni.showToast({ title: '数据加载失败，请检查网络', icon: 'none', duration: 3000 })
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
  uni.navigateTo({
    url: `/pages/viewer/viewer?index=${index}`
  })
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #faf5f7;
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
