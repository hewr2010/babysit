<template>
  <view class="photo-section">
    <view class="section-header">
      <text class="section-title">{{ store.monthDisplay }}照片 ({{ store.photos.length }}张)</text>
      <view v-if="store.loading" class="loading-indicator">
        <view class="spinner"></view>
      </view>
    </view>

    <view v-if="store.photos.length === 0" class="empty-state">
      <text class="empty-icon">📷</text>
      <text>本月还没有照片</text>
      <text class="empty-hint">后台会自动同步网盘照片，请稍后再来查看</text>
    </view>

    <view v-else class="timeline">
      <view v-for="(photos, date) in sortedPhotosByDate" :key="date" class="timeline-day">
        <view class="day-header">
          <text class="day-date">{{ formatDate(date) }}</text>
          <text class="day-count">{{ photos.length }}张</text>
        </view>
        <view class="photo-grid">
          <view
            v-for="photo in visiblePhotos(photos, date)"
            :key="photo.name"
            class="photo-item"
            :class="{ video: photo.type === 'video' }"
            @click="openPhoto(photo)"
          >
            <image
              :src="thumbUrl(photo.name)"
              mode="aspectFill"
              lazy-load
            />
            <text v-if="photo.time" class="photo-time">{{ photo.time }}</text>
          </view>
        </view>
        <view
          v-if="photos.length > 6 && !isExpanded(date)"
          class="view-more-btn"
          @click="expandDate(date)"
        >
          <text>查看更多 ({{ photos.length - 6 }}张)</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAppStore } from '@/stores/app'
import { MEDIA_HOST } from '@/platform'

const store = useAppStore()
const emit = defineEmits(['openPhoto'])

const expandedDates = ref(new Set())

const sortedPhotosByDate = computed(() => {
  const dates = Object.keys(store.photosByDate).sort().reverse()
  const result = {}
  for (const date of dates) {
    result[date] = store.photosByDate[date]
  }
  return result
})

function thumbUrl(filename) {
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(filename)}`
}

function formatDate(dateStr) {
  if (dateStr === '0000-00-00') return '无日期'
  const [_, month, day] = dateStr.split('-')
  return `${month}月${day}日`
}

function isExpanded(date) {
  return expandedDates.value.has(date)
}

function visiblePhotos(photos, date) {
  return isExpanded(date) ? photos : photos.slice(0, 6)
}

function expandDate(date) {
  expandedDates.value.add(date)
}

function openPhoto(photo) {
  const index = store.photos.findIndex(p => p.name === photo.name)
  if (index !== -1) {
    emit('openPhoto', index)
  }
}
</script>

<style scoped>
.photo-section {
  background: white;
  border-radius: 24rpx;
  padding: 40rpx;
  box-shadow: 0 4rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 32rpx;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #6b7280;
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  width: 40rpx;
  height: 40rpx;
  border: 4rpx solid rgba(236, 72, 153, 0.2);
  border-top-color: #ec4899;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 48rpx;
}

.day-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding-bottom: 16rpx;
  border-bottom: 4rpx solid #ec4899;
  margin-bottom: 24rpx;
}

.day-date {
  font-size: 30rpx;
  font-weight: 600;
  color: #ec4899;
}

.day-count {
  font-size: 24rpx;
  color: #9ca3af;
  background: #faf5f7;
  padding: 4rpx 16rpx;
  border-radius: 24rpx;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
}

.view-more-btn {
  width: 100%;
  padding: 16rpx;
  margin-top: 16rpx;
  border: 2rpx dashed #ec4899;
  background: transparent;
  color: #ec4899;
  border-radius: 16rpx;
  font-size: 26rpx;
  text-align: center;
}

.photo-item {
  aspect-ratio: 1;
  border-radius: 16rpx;
  overflow: hidden;
  position: relative;
  background: #faf5f7;
}

.photo-item image {
  width: 100%;
  height: 100%;
}

.photo-item.video::after {
  content: "▶";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 32rpx;
  text-shadow: 0 4rpx 8rpx rgba(0, 0, 0, 0.5);
}

.photo-time {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 18rpx;
  padding: 4rpx 8rpx;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
  padding: 96rpx 32rpx;
  color: #9ca3af;
}

.empty-icon {
  font-size: 80rpx;
}

.empty-hint {
  font-size: 24rpx;
  opacity: 0.8;
  margin-top: 8rpx;
}
</style>
