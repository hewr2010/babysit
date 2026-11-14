<template>
  <view class="manage-page">
    <scroll-view v-if="months.length" scroll-x class="month-scroll" :show-scrollbar="false">
      <view class="month-list">
        <view v-for="item in months" :key="item.key" class="manage-month" :class="{ selected: selected === item.key }" @click="selectMonth(item)">
          <text>{{ item.year }}年{{ item.month }}月</text>
          <text v-if="milestoneCount(item.key)" class="month-count">{{ milestoneCount(item.key) }}</text>
        </view>
      </view>
    </scroll-view>
    <view v-if="loading" class="empty-state">正在加载相册…</view>
    <view v-else-if="!media.length" class="empty-state">还没有可标记的照片或视频</view>
    <view v-else class="manage-grid">
      <view v-for="item in media" :key="item.name" class="manage-cell" :class="{ marked: hasMilestone(item.name) }" @click="openEditor(item)">
        <image class="manage-image" :src="localImage(thumbUrl(item.name))" mode="aspectFill" lazy-load />
        <text v-if="hasMilestone(item.name)" class="marked-label">已标记</text>
      </view>
    </view>
    <MilestoneEditor :visible="editorVisible" :media="selectedMedia" @close="editorVisible = false" />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MilestoneEditor from '@/components/MilestoneEditor.vue'
import { request } from '@/services/api'
import { requireAuth } from '@/services/auth'
import { thumbUrl } from '@/services/media'
import { localImage, preloadImages } from '@/services/localImages'
import { useAppStore } from '@/stores/app'
import { albumMonths, flattenAlbum } from '@/utils/album'

const store = useAppStore()
const months = ref([])
const selected = ref('')
const media = ref([])
const loading = ref(true)
const editorVisible = ref(false)
const selectedMedia = ref(null)

onLoad(() => {
  if (requireAuth()) initialize()
})

async function initialize() {
  loading.value = true
  try {
    const groups = await request('/album')
    months.value = albumMonths(groups)
    const initial = months.value.find(item => item.key === store.selectedMonthKey) || months.value[0]
    if (initial) await selectMonth(initial)
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function selectMonth(item) {
  selected.value = item.key
  loading.value = true
  try {
    media.value = flattenAlbum(await request(`/album/${item.year}/${item.month}`))
    preloadImages(media.value.map(entry => thumbUrl(entry.name)))
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function milestoneCount(key) {
  return store.milestones.filter(item => item.date?.startsWith(key)).length
}

function hasMilestone(filename) {
  return store.milestones.some(item => item.media_filename === filename)
}

function openEditor(item) {
  selectedMedia.value = item
  editorVisible.value = true
}
</script>

<style scoped>
.manage-page {
  min-height: 100vh;
  padding-bottom: calc(28rpx + env(safe-area-inset-bottom));
}

.month-scroll {
  border-bottom: 2rpx solid #edf0ef;
  background: #ffffff;
}

.month-list {
  display: inline-flex;
  gap: 16rpx;
  padding: 24rpx 28rpx;
}

.manage-month {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 24rpx;
  border-radius: 28rpx;
  background: #f3f4f6;
  white-space: nowrap;
  font-size: 25rpx;
}

.manage-month.selected {
  background: #ec4899;
  color: #ffffff;
}

.month-count {
  padding: 0 10rpx;
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.8);
  color: #db2777;
  font-size: 20rpx;
}

.manage-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  padding: 28rpx;
}

.manage-cell {
  position: relative;
  overflow: hidden;
  aspect-ratio: 1;
  border: 4rpx solid transparent;
  border-radius: 16rpx;
  background: #fdf2f8;
}

.manage-cell.marked {
  border-color: #ec4899;
}

.manage-image {
  width: 100%;
  height: 100%;
}

.marked-label {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 6rpx;
  background: rgba(236, 72, 153, 0.85);
  color: #ffffff;
  text-align: center;
  font-size: 20rpx;
}
</style>
