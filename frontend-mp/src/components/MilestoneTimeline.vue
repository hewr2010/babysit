<template>
  <view v-if="monthlyMilestones.length > 0" class="milestone-section">
    <view class="section-header">
      <text class="section-title">⭐ 重要时刻 ({{ monthlyMilestones.length }}个)</text>
      <view class="manage-link" @click="goManage">
        <text>📝 管理</text>
      </view>
    </view>

    <scroll-view scroll-x class="timeline-scroll" show-scrollbar="false">
      <view class="timeline-container">
        <view
          v-for="milestone in monthlyMilestones"
          :key="milestone.id"
          class="milestone-card"
          @click="openMilestone(milestone)"
        >
          <view class="milestone-thumb">
            <image
              :src="thumbUrl(milestone.media_filename)"
              mode="aspectFill"
              lazy-load
            />
            <text v-if="milestone.file_type === 'video'" class="video-badge">▶</text>
          </view>
          <view class="milestone-info">
            <text class="milestone-date">{{ formatDate(milestone.date) }}</text>
            <text class="milestone-title">{{ milestone.title }}</text>
            <text v-if="milestone.description" class="milestone-desc">
              {{ milestone.description }}
            </text>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>

  <view v-else-if="store.milestones.length === 0" class="milestone-section empty">
    <view class="section-header">
      <text class="section-title">⭐ 重要时刻</text>
    </view>
    <view class="empty-content">
      <view class="empty-hint">
        <text class="hint-icon">💡</text>
        <text>在照片查看器中点击 ⭐ 标记重要时刻</text>
      </view>
      <view class="enter-manage-btn" @click="goManage">
        <text>🎨 批量管理照片时刻</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { MEDIA_HOST } from '@/platform'

const store = useAppStore()
const emit = defineEmits(['openPhoto'])

const monthlyMilestones = computed(() => {
  const year = store.currentYear
  const month = String(store.currentMonth).padStart(2, '0')
  const prefix = `${year}-${month}`
  return store.milestones.filter(m => m.date && m.date.startsWith(prefix))
})

function thumbUrl(filename) {
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(filename)}`
}

function formatDate(dateStr) {
  if (!dateStr || dateStr === '0000-00-00') return ''
  const [_, month, day] = dateStr.split('-')
  return `${month}月${day}日`
}

function openMilestone(milestone) {
  const photoIndex = store.photos.findIndex(p => p.name === milestone.media_filename)
  if (photoIndex !== -1) {
    emit('openPhoto', photoIndex)
  } else {
    const date = milestone.date
    if (date) {
      const [year, month] = date.split('-')
      store.setMonth(parseInt(year), parseInt(month))
      setTimeout(() => {
        const idx = store.photos.findIndex(p => p.name === milestone.media_filename)
        if (idx !== -1) {
          emit('openPhoto', idx)
        }
      }, 500)
    }
  }
}

function goManage() {
  uni.navigateTo({ url: '/pages/milestones/manage' })
}
</script>

<style scoped>
.milestone-section {
  background: white;
  border-radius: 24rpx;
  padding: 40rpx;
  box-shadow: 0 4rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 32rpx;
  overflow: hidden;
}

.milestone-section.empty {
  padding-bottom: 32rpx;
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

.manage-link {
  font-size: 26rpx;
  color: #ec4899;
  padding: 12rpx 28rpx;
  border-radius: 32rpx;
  background: rgba(236, 72, 153, 0.1);
  font-weight: 500;
}

.timeline-scroll {
  width: 100%;
  white-space: nowrap;
}

.timeline-container {
  display: inline-flex;
  gap: 20rpx;
  padding-bottom: 8rpx;
}

.milestone-card {
  flex-shrink: 0;
  width: 260rpx;
  background: #faf5f7;
  border-radius: 24rpx;
  overflow: hidden;
}

.milestone-thumb {
  position: relative;
  width: 100%;
  height: 260rpx;
  background: #f3f4f6;
}

.milestone-thumb image {
  width: 100%;
  height: 100%;
}

.video-badge {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 56rpx;
  height: 56rpx;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20rpx;
}

.milestone-info {
  padding: 16rpx;
}

.milestone-date {
  display: block;
  font-size: 22rpx;
  color: #ec4899;
  font-weight: 500;
  margin-bottom: 8rpx;
}

.milestone-title {
  display: block;
  font-size: 26rpx;
  color: #374151;
  font-weight: 600;
  line-height: 1.3;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.milestone-desc {
  display: block;
  font-size: 20rpx;
  color: #9ca3af;
  margin-top: 4rpx;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-content {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  text-align: center;
  padding: 32rpx;
  color: #9ca3af;
  font-size: 26rpx;
  background: #faf5f7;
  border-radius: 24rpx;
}

.hint-icon {
  font-size: 32rpx;
}

.enter-manage-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx 40rpx;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
  border-radius: 24rpx;
  font-size: 28rpx;
  font-weight: 500;
}
</style>
