<template>
  <view class="card album-section">
    <view class="section-heading">
      <text class="section-title">{{ store.selectedMonthLabel }}相册</text>
      <text class="album-count">{{ store.albumLoading ? '加载中…' : `${store.media.length} 项` }}</text>
    </view>
    <view v-if="!store.media.length && !store.albumLoading" class="empty-state">这个月还没有照片或视频</view>
    <view v-for="group in groups" :key="group.date" class="album-day">
      <view class="day-heading">
        <text>{{ shortDate(group.date) }}</text>
        <text class="day-count">{{ group.items.length }} 项</text>
      </view>
      <view class="media-grid">
        <view v-for="item in visibleItems(group)" :key="item.name" class="media-cell" @click="open(item)">
          <image class="media-thumb" :src="thumbUrl(item.name)" mode="aspectFill" lazy-load />
          <view v-if="item.type === 'video'" class="video-badge">▶</view>
          <text v-if="item.time" class="media-time">{{ item.time }}</text>
        </view>
      </view>
      <view v-if="group.items.length > 6" class="view-more-btn" @click="toggleDate(group.date)">
        {{ expandedDates.has(group.date) ? '收起' : `查看更多（${group.items.length - 6} 项）` }}
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { thumbUrl } from '@/services/media'
import { shortDate } from '@/utils/date'

const emit = defineEmits(['open'])
const store = useAppStore()
const expandedDates = ref(new Set())
const groups = computed(() => Object.keys(store.albumByDate).sort().reverse().map(date => ({
  date,
  items: [...store.albumByDate[date]].sort((a, b) => (b.time || '').localeCompare(a.time || ''))
})))

watch(() => store.selectedMonthKey, () => {
  expandedDates.value = new Set()
})

function visibleItems(group) {
  return expandedDates.value.has(group.date) ? group.items : group.items.slice(0, 6)
}

function toggleDate(date) {
  const next = new Set(expandedDates.value)
  if (next.has(date)) next.delete(date)
  else next.add(date)
  expandedDates.value = next
}

function open(item) {
  const index = store.media.findIndex(mediaItem => mediaItem.name === item.name)
  if (index >= 0) emit('open', index)
}
</script>

<style scoped>
.album-count,
.day-count {
  color: #9ca3af;
  font-size: 24rpx;
}

.album-day {
  margin-top: 32rpx;
}

.day-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
  padding-bottom: 12rpx;
  border-bottom: 3rpx solid #ec4899;
  color: #ec4899;
  font-weight: 600;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
}

.media-cell {
  position: relative;
  overflow: hidden;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 16rpx;
  background: #fdf2f8;
}

.media-thumb {
  width: 100%;
  height: 100%;
}

.video-badge {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 52rpx;
  height: 52rpx;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #ffffff;
  text-align: center;
  line-height: 52rpx;
  font-size: 24rpx;
}

.media-time {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  overflow: hidden;
  padding: 4rpx 8rpx;
  background: rgba(0, 0, 0, 0.5);
  color: #ffffff;
  font-size: 18rpx;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.view-more-btn {
  margin-top: 20rpx;
  padding: 18rpx;
  border: 2rpx dashed #ec4899;
  border-radius: 16rpx;
  color: #db2777;
  text-align: center;
  font-size: 26rpx;
}
</style>
