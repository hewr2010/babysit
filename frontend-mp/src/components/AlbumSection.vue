<template>
  <view class="card album-section">
    <view class="section-heading">
      <view class="album-heading-copy">
        <text class="section-title">{{ store.selectedMonthLabel }}相册</text>
        <text class="album-hint">点 ··· 可标记 / 转发</text>
      </view>
      <text class="album-count">{{ store.albumLoading ? '加载中…' : `${store.media.length} 项` }}</text>
    </view>
    <view v-if="!store.media.length && !store.albumLoading" class="empty-state">这个月还没有照片或视频</view>
    <view v-for="group in groups" :key="group.date" class="album-day">
      <view class="day-heading">
        <text>{{ shortDate(group.date) }}</text>
        <text class="day-count">{{ group.items.length }} 项</text>
      </view>
      <view class="media-grid">
        <view v-for="item in visibleItems(group)" :key="item.name" class="media-cell" @click="open(item)" @longpress.stop="showActions(item)">
          <image class="media-thumb" :src="thumbUrl(item.name)" mode="aspectFill" lazy-load />
          <view v-if="item.type === 'video'" class="video-badge">▶</view>
          <view v-if="milestoneNames.has(item.name)" class="milestone-badge">⭐</view>
          <button class="media-menu-button" @click.stop="showActions(item)">···</button>
          <text v-if="item.time" class="media-time">{{ item.time }}</text>
        </view>
      </view>
      <view v-if="group.items.length > 6" class="view-more-btn" @click="toggleDate(group.date)">
        {{ expandedDates.has(group.date) ? '收起' : `查看更多（${group.items.length - 6} 项）` }}
      </view>
    </view>
    <AppSheet :visible="actionVisible" title="照片 / 视频操作" @close="closeActions">
      <view class="album-actions">
        <button class="secondary-button action-button open-milestone-editor" @click="openEditor">
          {{ selectedMilestones.length ? `查看重要时刻（${selectedMilestones.length}）` : '标记重要时刻' }}
        </button>
        <button class="secondary-button action-button action-share" open-type="share" @click="closeActions">转发小程序卡片</button>
        <button class="secondary-button action-button" :disabled="saving" @click="saveCurrent">{{ saving ? '保存中…' : '保存原文件' }}</button>
      </view>
    </AppSheet>
    <MilestoneEditor :visible="editorVisible" :media="selectedMedia" @close="editorVisible = false" />
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppSheet from '@/components/AppSheet.vue'
import MilestoneEditor from '@/components/MilestoneEditor.vue'
import { saveToAlbum, thumbUrl } from '@/services/media'
import { useAppStore } from '@/stores/app'
import { shortDate } from '@/utils/date'

const emit = defineEmits(['open', 'actions'])
const store = useAppStore()
const expandedDates = ref(new Set())
const actionVisible = ref(false)
const editorVisible = ref(false)
const selectedMedia = ref(null)
const saving = ref(false)
let suppressClick = false
const groups = computed(() => Object.keys(store.albumByDate).sort().reverse().map(date => ({
  date,
  items: [...store.albumByDate[date]].sort((a, b) => (b.time || '').localeCompare(a.time || ''))
})))
const milestoneNames = computed(() => new Set(store.milestones.map(item => item.media_filename)))
const selectedMilestones = computed(() => selectedMedia.value
  ? store.milestones.filter(item => item.media_filename === selectedMedia.value.name)
  : [])

watch(() => store.selectedMonthKey, () => {
  expandedDates.value = new Set()
  actionVisible.value = false
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
  if (suppressClick) return
  const index = store.media.findIndex(mediaItem => mediaItem.name === item.name)
  if (index >= 0) emit('open', index)
}

function showActions(item) {
  suppressClick = true
  selectedMedia.value = item
  actionVisible.value = true
  emit('actions', item)
  setTimeout(() => { suppressClick = false }, 500)
}

function closeActions() {
  suppressClick = false
  actionVisible.value = false
}

function openEditor() {
  closeActions()
  editorVisible.value = true
}

async function saveCurrent() {
  if (!selectedMedia.value || saving.value) return
  closeActions()
  saving.value = true
  try {
    await saveToAlbum(selectedMedia.value)
    uni.showToast({ title: '已保存到相册', icon: 'success' })
  } catch (error) {
    uni.showModal({ title: '无法保存', content: error.message, showCancel: false })
  } finally {
    saving.value = false
  }
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

.album-heading-copy {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.album-hint {
  color: #9ca3af;
  font-size: 21rpx;
  font-weight: 400;
}

.milestone-badge {
  position: absolute;
  top: 8rpx;
  left: 8rpx;
  padding: 4rpx 8rpx;
  border-radius: 16rpx;
  background: rgba(236, 72, 153, 0.9);
  font-size: 20rpx;
  line-height: 1.2;
}

.media-menu-button {
  position: absolute;
  z-index: 1;
  top: 8rpx;
  right: 8rpx;
  width: 52rpx;
  height: 52rpx;
  padding: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #ffffff;
  text-align: center;
  line-height: 46rpx;
  font-size: 28rpx;
}

.album-actions {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}

.action-button {
  width: 100%;
}
</style>
