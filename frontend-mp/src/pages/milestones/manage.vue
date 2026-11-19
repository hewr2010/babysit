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
    <view v-else-if="loadError" class="empty-state load-error">
      <text>{{ loadError }}</text>
      <button class="secondary-button retry-button" @click="retry">重新加载</button>
    </view>
    <view v-else-if="!media.length" class="empty-state">还没有可标记的照片或视频</view>
    <view v-else class="manage-grid">
      <view v-for="item in media" :key="item.name" class="manage-cell" :class="{ marked: hasMilestone(item.name) }" @click="openEditor(item)">
        <image v-if="!imageFailed(thumbUrl(item.name))" class="manage-image" :src="localImage(thumbUrl(item.name))" mode="aspectFill" lazy-load />
        <view v-else class="thumb-error" @click.stop="retryImage(thumbUrl(item.name))">缩略图加载失败，点击重试</view>
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
import { imageFailed, localImage, preloadImages, retryImage } from '@/services/localImages'
import { useAppStore } from '@/stores/app'
import { albumMonths, flattenAlbum } from '@/utils/album'

const store = useAppStore()
const months = ref([])
const selected = ref('')
const media = ref([])
const loading = ref(true)
const loadError = ref('')
const editorVisible = ref(false)
const selectedMedia = ref(null)
let monthRequestId = 0

onLoad(() => {
  if (requireAuth()) initialize()
})

async function initialize() {
  loading.value = true
  loadError.value = ''
  try {
    const [groups] = await Promise.all([request('/album'), store.loadMilestones()])
    months.value = albumMonths(groups)
    const initial = months.value.find(item => item.key === store.selectedMonthKey) || months.value[0]
    if (initial) await selectMonth(initial)
    else media.value = []
  } catch (error) {
    loadError.value = error.message || '数据加载失败'
  } finally {
    loading.value = false
  }
}

async function selectMonth(item) {
  const requestId = ++monthRequestId
  selected.value = item.key
  loading.value = true
  loadError.value = ''
  try {
    const groups = await request(`/album/${item.year}/${item.month}`)
    if (requestId !== monthRequestId) return
    media.value = flattenAlbum(groups)
    preloadImages(media.value.map(entry => thumbUrl(entry.name)))
  } catch (error) {
    if (requestId === monthRequestId) loadError.value = error.message || '相册加载失败'
  } finally {
    if (requestId === monthRequestId) loading.value = false
  }
}

function retry() {
  const current = months.value.find(item => item.key === selected.value)
  if (current) selectMonth(current)
  else initialize()
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
  border-radius: 14rpx;
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

.thumb-error {
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  padding: 16rpx;
  color: #9f1239;
  text-align: center;
  font-size: 20rpx;
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

.load-error {
  color: #b91c1c;
}

.retry-button {
  margin-top: 24rpx;
}
</style>
