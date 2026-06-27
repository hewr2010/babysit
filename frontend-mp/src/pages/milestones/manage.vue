<template>
  <view class="manage-view">
    <scroll-view scroll-x class="month-scroll" show-scrollbar="false">
      <view class="month-list">
        <view
          v-for="month in availableMonths"
          :key="month.key"
          class="month-item"
          :class="{ active: selectedMonth === month.key }"
          @click="selectMonth(month.key)"
        >
          <text class="month-label">{{ month.label }}</text>
          <text v-if="month.milestoneCount > 0" class="month-badge">{{ month.milestoneCount }}</text>
        </view>
      </view>
    </scroll-view>

    <scroll-view scroll-y class="photo-scroll">
      <view v-if="loading" class="loading-state">
        <view class="spinner"></view>
      </view>
      <view v-else-if="photos.length === 0" class="empty-state">
        <text>本月还没有照片</text>
      </view>
      <view v-else class="photo-grid">
        <view
          v-for="photo in photos"
          :key="photo.name"
          class="photo-item"
          :class="{ video: photo.type === 'video', hasMilestone: hasMilestone(photo.name) }"
          @click="openEditor(photo)"
        >
          <image :src="thumbUrl(photo.name)" mode="aspectFill" lazy-load />
          <text v-if="hasMilestone(photo.name)" class="milestone-star">⭐</text>
        </view>
      </view>
    </scroll-view>

    <view v-if="editorVisible" class="editor-overlay" @click.self="closeEditor">
      <view class="editor-sheet">
        <view class="editor-header">
          <text class="editor-title">⭐ 标记重要时刻</text>
          <text class="close-btn" @click="closeEditor">✕</text>
        </view>

        <image
          v-if="editorPhoto"
          :src="previewUrl(editorPhoto.name)"
          mode="aspectFit"
          class="editor-preview"
        />

        <view class="form-group">
          <text class="label">时刻标题</text>
          <input v-model="newTitle" type="text" placeholder="例如：第一次打疫苗" maxlength="50" class="form-input" />
          <text class="char-count">{{ newTitle.length }}/50</text>
        </view>

        <view class="form-group">
          <text class="label">描述（可选）</text>
          <textarea v-model="newDescription" placeholder="添加更多细节..." maxlength="200" class="form-textarea" />
          <text class="char-count">{{ newDescription.length }}/200</text>
        </view>

        <view v-if="editorMilestones.length > 0" class="existing-list">
          <text class="label">已标记</text>
          <view v-for="ms in editorMilestones" :key="ms.id" class="existing-item">
            <text class="existing-title">{{ ms.title }}</text>
            <text class="delete-btn" @click="deleteMilestone(ms.id)">删除</text>
          </view>
        </view>

        <button class="submit-btn" :disabled="!newTitle.trim() || adding" @click="addMilestone">
          <text v-if="adding" class="btn-spinner"></text>
          <text v-else>保存</text>
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { request } from '@/shared/request'
import { API_BASE } from '@/shared/api'
import { MEDIA_HOST } from '@/platform'

const loading = ref(false)
const photos = ref([])
const allMilestones = ref([])
const milestonesByPhoto = ref({})
const selectedMonth = ref('')
const availableMonths = ref([])

const editorVisible = ref(false)
const editorPhoto = ref(null)
const editorMilestones = ref([])
const newTitle = ref('')
const newDescription = ref('')
const adding = ref(false)

const milestonesByPhotoComputed = computed(() => milestonesByPhoto.value)

onMounted(() => {
  initAvailableMonths()
  fetchAllMilestones()
})

function thumbUrl(filename) {
  return `${MEDIA_HOST}/thumb/${encodeURIComponent(filename)}`
}

function previewUrl(filename) {
  return `${MEDIA_HOST}/preview/${encodeURIComponent(filename)}`
}

function hasMilestone(filename) {
  return (milestonesByPhotoComputed.value[filename] || []).length > 0
}

async function initAvailableMonths() {
  try {
    const allPhotos = await request(`${API_BASE}/album`)
    const monthsSet = new Set()
    Object.keys(allPhotos).forEach(date => {
      if (date && date !== '0000-00-00') {
        monthsSet.add(date.substring(0, 7))
      }
    })

    const sortedMonths = Array.from(monthsSet).sort().reverse()
    availableMonths.value = sortedMonths.map(key => {
      const [year, month] = key.split('-')
      return {
        key,
        label: `${year}年${parseInt(month)}月`,
        year: parseInt(year),
        month: parseInt(month),
        milestoneCount: 0
      }
    })

    if (availableMonths.value.length > 0) {
      selectMonth(availableMonths.value[0].key)
    }
  } catch (e) {
    console.error('Failed to init months:', e)
  }
}

async function fetchAllMilestones() {
  try {
    allMilestones.value = await request(`${API_BASE}/milestones`)
    const grouped = {}
    allMilestones.value.forEach(ms => {
      if (!grouped[ms.media_filename]) {
        grouped[ms.media_filename] = []
      }
      grouped[ms.media_filename].push(ms)
    })
    milestonesByPhoto.value = grouped
    updateMonthCounts()
  } catch (e) {
    console.error('Failed to fetch milestones:', e)
  }
}

function updateMonthCounts() {
  availableMonths.value.forEach(month => {
    month.milestoneCount = allMilestones.value.filter(ms => {
      const msMonth = ms.date?.substring(0, 7)
      return msMonth === month.key
    }).length
  })
}

async function selectMonth(monthKey) {
  selectedMonth.value = monthKey
  const month = availableMonths.value.find(m => m.key === monthKey)
  if (month) {
    await loadMonthPhotos(month.year, month.month)
  }
}

async function loadMonthPhotos(year, month) {
  loading.value = true
  try {
    const dateGroups = await request(`${API_BASE}/album/${year}/${month}`)
    const sortedDates = Object.keys(dateGroups).sort().reverse()
    let allPhotos = []
    for (const date of sortedDates) {
      const files = dateGroups[date]
      files.sort((a, b) => (b.time || '').localeCompare(a.time || ''))
      allPhotos = allPhotos.concat(files)
    }
    photos.value = allPhotos
  } catch (e) {
    console.error('Failed to load photos:', e)
  } finally {
    loading.value = false
  }
}

async function openEditor(photo) {
  editorPhoto.value = photo
  editorVisible.value = true
  newTitle.value = ''
  newDescription.value = ''
  try {
    editorMilestones.value = await request(`${API_BASE}/milestones/${encodeURIComponent(photo.name)}`)
  } catch (e) {
    console.error('Failed to load photo milestones:', e)
  }
}

function closeEditor() {
  editorVisible.value = false
  editorPhoto.value = null
  editorMilestones.value = []
}

async function addMilestone() {
  if (!newTitle.value.trim() || !editorPhoto.value) return

  adding.value = true
  try {
    await request(`${API_BASE}/milestones`, {
      method: 'POST',
      data: {
        media_filename: editorPhoto.value.name,
        title: newTitle.value.trim(),
        description: newDescription.value.trim() || null
      }
    })

    newTitle.value = ''
    newDescription.value = ''
    await openEditor(editorPhoto.value)
    await fetchAllMilestones()
  } catch (e) {
    console.error('Failed to add milestone:', e)
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  } finally {
    adding.value = false
  }
}

async function deleteMilestone(id) {
  try {
    await request(`${API_BASE}/milestones/${id}`, { method: 'DELETE' })
    await openEditor(editorPhoto.value)
    await fetchAllMilestones()
  } catch (e) {
    console.error('Failed to delete milestone:', e)
    uni.showToast({ title: e.message || '删除失败', icon: 'none' })
  }
}
</script>

<style scoped>
.manage-view {
  min-height: 100vh;
  background: #faf5f7;
  display: flex;
  flex-direction: column;
}

.month-scroll {
  background: white;
  padding: 24rpx 0;
  border-bottom: 2rpx solid rgba(0, 0, 0, 0.06);
}

.month-list {
  display: inline-flex;
  gap: 16rpx;
  padding: 0 32rpx;
}

.month-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 28rpx;
  background: #f3f4f6;
  border-radius: 32rpx;
  white-space: nowrap;
}

.month-item.active {
  background: #ec4899;
}

.month-item.active .month-label {
  color: white;
}

.month-label {
  font-size: 26rpx;
  color: #374151;
  font-weight: 500;
}

.month-badge {
  font-size: 20rpx;
  color: white;
  background: #f472b6;
  padding: 2rpx 10rpx;
  border-radius: 20rpx;
}

.month-item.active .month-badge {
  background: white;
  color: #ec4899;
}

.photo-scroll {
  flex: 1;
  padding: 24rpx;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
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

.photo-item.hasMilestone {
  border: 4rpx solid #ec4899;
}

.milestone-star {
  position: absolute;
  top: 8rpx;
  right: 8rpx;
  font-size: 28rpx;
}

.loading-state {
  padding: 96rpx;
  display: flex;
  justify-content: center;
}

.spinner {
  width: 48rpx;
  height: 48rpx;
  border: 4rpx solid rgba(236, 72, 153, 0.2);
  border-top-color: #ec4899;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 96rpx;
  color: #9ca3af;
}

.editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  z-index: 300;
}

.editor-sheet {
  background: white;
  width: 100%;
  max-height: 90vh;
  border-radius: 48rpx 48rpx 0 0;
  padding: 40rpx;
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
  overflow-y: auto;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32rpx;
}

.editor-title {
  font-size: 36rpx;
  font-weight: 600;
  color: #374151;
}

.close-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 50%;
  font-size: 32rpx;
  color: #6b7280;
}

.editor-preview {
  width: 100%;
  height: 400rpx;
  border-radius: 24rpx;
  margin-bottom: 32rpx;
  background: #faf5f7;
}

.form-group {
  margin-bottom: 32rpx;
  position: relative;
}

.label {
  display: block;
  font-size: 28rpx;
  color: #6b7280;
  margin-bottom: 12rpx;
}

.form-input, .form-textarea {
  width: 100%;
  padding: 28rpx 32rpx;
  border: 4rpx solid #f3f4f6;
  border-radius: 24rpx;
  font-size: 30rpx;
  background: white;
  box-sizing: border-box;
}

.form-textarea {
  height: 180rpx;
}

.char-count {
  position: absolute;
  right: 16rpx;
  bottom: -32rpx;
  font-size: 20rpx;
  color: #9ca3af;
}

.existing-list {
  margin-bottom: 32rpx;
}

.existing-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx;
  background: #faf5f7;
  border-radius: 16rpx;
  margin-bottom: 16rpx;
}

.existing-title {
  font-size: 28rpx;
  color: #374151;
  flex: 1;
}

.delete-btn {
  font-size: 26rpx;
  color: #ef4444;
  padding: 8rpx 16rpx;
}

.submit-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  background: #ec4899;
  color: white;
  border: none;
  border-radius: 24rpx;
  font-size: 32rpx;
  font-weight: 600;
}

.submit-btn[disabled] {
  opacity: 0.5;
}

.submit-btn::after {
  border: none;
}

.btn-spinner {
  display: inline-block;
  width: 32rpx;
  height: 32rpx;
  border: 4rpx solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>
