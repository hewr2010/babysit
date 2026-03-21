<template>
  <div class="manage-view">
    <!-- 顶部导航 -->
    <div class="manage-header">
      <router-link to="/" class="back-btn">
        ← 返回
      </router-link>
      <h1>管理重要时刻</h1>
      <span class="count-badge">共 {{ allMilestones.length }} 个</span>
    </div>

    <div class="manage-body">
      <!-- 左侧：时间线选择器 -->
      <div class="timeline-sidebar">
        <h3>选择时间</h3>
        <div class="month-list">
          <div
            v-for="month in availableMonths"
            :key="month.key"
            class="month-item"
            :class="{ active: selectedMonth === month.key }"
            @click="selectMonth(month.key)"
          >
            <span class="month-name">{{ month.label }}</span>
            <span v-if="month.milestoneCount > 0" class="month-badge">
              {{ month.milestoneCount }}
            </span>
          </div>
        </div>
      </div>

      <!-- 右侧：照片网格 -->
      <div class="photos-content">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>

        <div v-else-if="photos.length === 0" class="empty-state">
          <span class="empty-icon">📷</span>
          <span>该月暂无照片</span>
        </div>

        <div v-else class="photos-grid">
          <div
            v-for="photo in photos"
            :key="photo.name"
            class="photo-card"
            :class="{ 'has-milestone': getPhotoMilestones(photo.name).length > 0 }"
            @click="openEditor(photo)"
          >
            <img :src="`/thumb/${encodeURIComponent(photo.name)}`" loading="lazy" />
            <div v-if="photo.type === 'video'" class="video-badge">▶</div>

            <!-- 已标记指示器 -->
            <div v-if="getPhotoMilestones(photo.name).length > 0" class="milestone-indicator">
              <span>⭐ {{ getPhotoMilestones(photo.name).length }}</span>
            </div>

            <!-- 悬浮提示 -->
            <div class="photo-overlay">
              <span class="overlay-text">
                {{ getPhotoMilestones(photo.name).length > 0 ? '编辑时刻' : '标记时刻' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="editorVisible" class="editor-overlay" @click.self="closeEditor">
          <div class="editor-modal">
            <div class="editor-header">
              <h3>{{ editorPhoto ? '编辑时刻' : '标记时刻' }}</h3>
              <button class="close-btn" @click="closeEditor">✕</button>
            </div>

            <div class="editor-body">
              <div class="photo-preview">
                <img
                  v-if="editorPhoto"
                  :src="`/preview/${encodeURIComponent(editorPhoto.name)}`"
                />
              </div>

              <!-- 新增时刻表单 -->
              <div class="add-milestone-form">
                <input
                  v-model="newTitle"
                  type="text"
                  placeholder="输入时刻标题，如：第一次打疫苗"
                  maxlength="50"
                  @keyup.enter="addMilestone"
                />
                <textarea
                  v-model="newDescription"
                  placeholder="添加描述（可选）"
                  maxlength="200"
                  rows="2"
                ></textarea>
                <button
                  class="add-btn"
                  @click="addMilestone"
                  :disabled="!newTitle.trim() || adding"
                >
                  <span v-if="adding" class="spinner"></span>
                  <span v-else>+ 添加时刻</span>
                </button>
              </div>

              <!-- 已有时刻列表 -->
              <div v-if="editorMilestones.length > 0" class="existing-list">
                <h4>已标记的时刻</h4>
                <div class="milestone-items">
                  <div
                    v-for="ms in editorMilestones"
                    :key="ms.id"
                    class="milestone-item"
                  >
                    <div class="item-content">
                      <span class="item-title">⭐ {{ ms.title }}</span>
                      <span v-if="ms.description" class="item-desc">{{ ms.description }}</span>
                    </div>
                    <button
                      class="delete-btn"
                      @click="deleteMilestone(ms.id)"
                      :disabled="deleting === ms.id"
                    >
                      <span v-if="deleting === ms.id" class="spinner"></span>
                      <span v-else>🗑️</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'

const API_BASE = '/api'

const loading = ref(false)
const photos = ref([])
const allMilestones = ref([])
const milestonesByPhoto = ref({})
const selectedMonth = ref('')
const availableMonths = ref([])

// 编辑器状态
const editorVisible = ref(false)
const editorPhoto = ref(null)
const editorMilestones = ref([])
const newTitle = ref('')
const newDescription = ref('')
const adding = ref(false)
const deleting = ref(null)

onMounted(() => {
  initAvailableMonths()
  fetchAllMilestones()
})

// 获取所有有照片的月份
async function initAvailableMonths() {
  try {
    // 获取所有已处理的媒体文件
    const res = await fetch(`${API_BASE}/album`)
    if (!res.ok) return

    const allPhotos = await res.json()

    // 提取所有有照片的月份
    const monthsSet = new Set()
    Object.keys(allPhotos).forEach(date => {
      if (date && date !== '0000-00-00') {
        const monthKey = date.substring(0, 7) // YYYY-MM
        monthsSet.add(monthKey)
      }
    })

    // 转换为数组并排序（最新的在前）
    const sortedMonths = Array.from(monthsSet).sort().reverse()

    // 构建月份对象
    const months = sortedMonths.map(key => {
      const [year, month] = key.split('-')
      return {
        key,
        label: `${year}年${parseInt(month)}月`,
        year: parseInt(year),
        month: parseInt(month),
        milestoneCount: 0
      }
    })

    availableMonths.value = months

    // 默认选中第一个（最新的）
    if (months.length > 0) {
      selectedMonth.value = months[0].key
      loadMonthPhotos(months[0].year, months[0].month)
    }
  } catch (e) {
    console.error('Failed to init months:', e)
  }
}

// 获取某照片关联的时刻
function getPhotoMilestones(filename) {
  return milestonesByPhoto.value[filename] || []
}

// 计算每个月的时刻数量
function updateMonthCounts() {
  availableMonths.value.forEach(month => {
    month.milestoneCount = allMilestones.value.filter(ms => {
      const msMonth = ms.date?.substring(0, 7)
      return msMonth === month.key
    }).length
  })
}

async function fetchAllMilestones() {
  try {
    const res = await fetch(`${API_BASE}/milestones`)
    if (res.ok) {
      allMilestones.value = await res.json()

      // 按照片分组
      const grouped = {}
      allMilestones.value.forEach(ms => {
        if (!grouped[ms.media_filename]) {
          grouped[ms.media_filename] = []
        }
        grouped[ms.media_filename].push(ms)
      })
      milestonesByPhoto.value = grouped

      updateMonthCounts()
    }
  } catch (e) {
    console.error('Failed to fetch milestones:', e)
  }
}

function selectMonth(monthKey) {
  selectedMonth.value = monthKey
  const month = availableMonths.value.find(m => m.key === monthKey)
  if (month) {
    loadMonthPhotos(month.year, month.month)
  }
}

async function loadMonthPhotos(year, month) {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/album/${year}/${month}`)
    if (res.ok) {
      const dateGroups = await res.json()

      // 按日期排序，展开为数组
      const sortedDates = Object.keys(dateGroups).sort().reverse()
      let allPhotos = []
      for (const date of sortedDates) {
        const files = dateGroups[date]
        files.sort((a, b) => (b.time || '').localeCompare(a.time || ''))
        allPhotos = allPhotos.concat(files)
      }
      photos.value = allPhotos
    }
  } catch (e) {
    console.error('Failed to load photos:', e)
  } finally {
    loading.value = false
  }
}

// 打开编辑器
async function openEditor(photo) {
  editorPhoto.value = photo
  editorVisible.value = true
  newTitle.value = ''
  newDescription.value = ''

  // 加载已有关联时刻
  try {
    const res = await fetch(`${API_BASE}/milestones/${encodeURIComponent(photo.name)}`)
    if (res.ok) {
      editorMilestones.value = await res.json()
    }
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
    const res = await fetch(`${API_BASE}/milestones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        media_filename: editorPhoto.value.name,
        title: newTitle.value.trim(),
        description: newDescription.value.trim() || null
      })
    })

    if (res.ok) {
      newTitle.value = ''
      newDescription.value = ''
      // 刷新列表
      await openEditor(editorPhoto.value)
      // 刷新全局数据
      await fetchAllMilestones()
    } else {
      const err = await res.json()
      alert(err.error || '添加失败')
    }
  } catch (e) {
    console.error('Failed to add milestone:', e)
    alert('添加失败')
  } finally {
    adding.value = false
  }
}

async function deleteMilestone(id) {
  deleting.value = id
  try {
    const res = await fetch(`${API_BASE}/milestones/${id}`, {
      method: 'DELETE'
    })

    if (res.ok) {
      await openEditor(editorPhoto.value)
      await fetchAllMilestones()
    }
  } catch (e) {
    console.error('Failed to delete milestone:', e)
    alert('删除失败')
  } finally {
    deleting.value = null
  }
}
</script>

<style scoped>
.manage-view {
  min-height: 100vh;
  background: var(--bg);
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
.manage-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: white;
  border-bottom: 1px solid #f3f4f6;
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-btn {
  font-size: 14px;
  color: var(--primary);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(236, 72, 153, 0.1);
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(236, 72, 153, 0.2);
}

.manage-header h1 {
  font-size: 17px;
  font-weight: 600;
  color: #374151;
  flex: 1;
  margin: 0;
}

.count-badge {
  font-size: 13px;
  color: var(--primary);
  background: rgba(236, 72, 153, 0.1);
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 500;
}

/* 主体布局 */
.manage-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧时间线 */
.timeline-sidebar {
  width: 160px;
  background: white;
  border-right: 1px solid #f3f4f6;
  padding: 16px 0;
  overflow-y: auto;
}

.timeline-sidebar h3 {
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
  padding: 0 16px 12px;
  margin: 0;
}

.month-list {
  display: flex;
  flex-direction: column;
}

.month-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #4b5563;
}

.month-item:hover {
  background: #f9fafb;
}

.month-item.active {
  background: rgba(236, 72, 153, 0.1);
  color: var(--primary);
  font-weight: 500;
}

.month-badge {
  font-size: 11px;
  background: var(--primary);
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.month-item.active .month-badge {
  background: white;
  color: var(--primary);
}

/* 右侧照片网格 */
.photos-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  color: #9ca3af;
}

.empty-icon {
  font-size: 48px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f4f6;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 照片网格 */
.photos-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

@media (min-width: 768px) {
  .photos-grid {
    grid-template-columns: repeat(5, 1fr);
  }
}

@media (min-width: 1024px) {
  .photos-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

.photo-card {
  aspect-ratio: 1;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  background: #f3f4f6;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.photo-card:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.photo-card.has-milestone {
  border-color: rgba(236, 72, 153, 0.5);
}

.photo-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-badge {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 28px;
  height: 28px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 10px;
}

.milestone-indicator {
  position: absolute;
  top: 6px;
  right: 6px;
  padding: 3px 8px;
  background: rgba(236, 72, 153, 0.9);
  color: white;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.photo-card:hover .photo-overlay {
  opacity: 1;
}

.overlay-text {
  color: white;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  backdrop-filter: blur(4px);
}

/* 编辑弹窗 */
.editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.editor-modal {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 420px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f3f4f6;
}

.editor-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #f3f4f6;
  border-radius: 50%;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #e5e7eb;
}

.editor-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.photo-preview {
  width: 100%;
  aspect-ratio: 4/3;
  border-radius: 12px;
  overflow: hidden;
  background: #f3f4f6;
  margin-bottom: 20px;
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 新增表单 */
.add-milestone-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.add-milestone-form input,
.add-milestone-form textarea {
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  font-size: 14px;
  background: #f9fafb;
  transition: all 0.2s;
}

.add-milestone-form input:focus,
.add-milestone-form textarea:focus {
  outline: none;
  border-color: #ec4899;
  background: white;
}

.add-milestone-form textarea {
  resize: none;
  font-family: inherit;
}

.add-btn {
  padding: 12px;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.add-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 已有时刻列表 */
.existing-list h4 {
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
  margin: 0 0 12px;
}

.milestone-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.milestone-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #f9fafb;
  border-radius: 12px;
}

.item-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.item-desc {
  font-size: 12px;
  color: #9ca3af;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.delete-btn:hover {
  background: #fee2e2;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
