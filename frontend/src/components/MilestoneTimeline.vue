<template>
  <section class="milestone-section" v-if="milestones.length > 0">
    <div class="section-header">
      <h2 class="section-title">⭐ 重要时刻 ({{ milestones.length }}个)</h2>
      <router-link to="/milestones/manage" class="manage-link">
        <span>📝 管理</span>
      </router-link>
    </div>
    
    <div class="timeline-scroll">
      <div class="timeline-container">
        <div 
          v-for="milestone in milestones" 
          :key="milestone.id"
          class="milestone-card"
          @click="openMilestone(milestone)"
        >
          <div class="milestone-thumb">
            <img 
              :src="`/thumb/${encodeURIComponent(milestone.media_filename)}`" 
              loading="lazy"
            />
            <span v-if="milestone.file_type === 'video'" class="video-badge">▶</span>
          </div>
          <div class="milestone-info">
            <div class="milestone-date">{{ formatDate(milestone.date) }}</div>
            <div class="milestone-title">{{ milestone.title }}</div>
            <div v-if="milestone.description" class="milestone-desc">
              {{ milestone.description }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
  
  <!-- 空状态 - 提示用户可以标记时刻 -->
  <section class="milestone-section empty" v-else>
    <div class="section-header">
      <h2 class="section-title">⭐ 重要时刻</h2>
      <router-link to="/milestones/manage" class="manage-link">
        📝 管理
      </router-link>
    </div>
    <div class="empty-content">
      <div class="empty-hint">
        <span class="hint-icon">💡</span>
        <span>在照片查看器中点击 ⭐ 标记重要时刻</span>
      </div>
      <router-link to="/milestones/manage" class="enter-manage-btn">
        <span>🎨 批量管理照片时刻</span>
      </router-link>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const API_BASE = '/api'

const store = useAppStore()
const modalStore = useModalStore()
const milestones = ref([])

onMounted(() => {
  fetchMilestones()
})

async function fetchMilestones() {
  try {
    const res = await fetch(`${API_BASE}/milestones`)
    milestones.value = await res.json()
  } catch (e) {
    console.error('Failed to fetch milestones:', e)
  }
}

function formatDate(dateStr) {
  if (!dateStr || dateStr === '0000-00-00') return ''
  const [year, month, day] = dateStr.split('-')
  return `${month}月${day}日`
}

function openMilestone(milestone) {
  // 找到对应的照片索引
  const photoIndex = store.photos.findIndex(p => p.name === milestone.media_filename)
  
  if (photoIndex !== -1) {
    // 照片在当前月份，直接打开
    modalStore.openPhotoViewer(photoIndex)
  } else {
    // 照片不在当前月份，需要切换月份
    // 从文件名解析日期（格式：YYYYMMDD_HHMMSS）
    const date = milestone.date
    if (date) {
      const [year, month] = date.split('-')
      store.setMonth(parseInt(year), parseInt(month))
      // 等待照片加载后再打开
      setTimeout(() => {
        const idx = store.photos.findIndex(p => p.name === milestone.media_filename)
        if (idx !== -1) {
          modalStore.openPhotoViewer(idx)
        }
      }, 500)
    }
  }
}
</script>

<style scoped>
.milestone-section {
  background: var(--surface);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow);
  margin-bottom: 16px;
}

.milestone-section.empty {
  padding-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.manage-link {
  font-size: 13px;
  color: var(--primary);
  text-decoration: none;
  padding: 6px 14px;
  border-radius: 16px;
  background: rgba(236, 72, 153, 0.1);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

.manage-link:hover {
  background: rgba(236, 72, 153, 0.2);
  transform: scale(1.05);
}

.empty-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  padding: 16px;
  color: var(--text-tertiary);
  font-size: 13px;
  background: var(--bg);
  border-radius: var(--radius);
}

.hint-icon {
  font-size: 16px;
}

.enter-manage-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 20px;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
  text-decoration: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(236, 72, 153, 0.3);
}

.enter-manage-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(236, 72, 153, 0.4);
}

/* 时间轴横向滚动 */
.timeline-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
  margin: 0 -20px;
  padding: 0 20px;
}

.timeline-scroll::-webkit-scrollbar {
  display: none;
}

.timeline-container {
  display: flex;
  gap: 12px;
  padding-bottom: 4px;
}

/* 时刻卡片 */
.milestone-card {
  flex-shrink: 0;
  width: 140px;
  background: var(--bg);
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.milestone-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
  border-color: rgba(236, 72, 153, 0.2);
}

.milestone-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  background: #f3f4f6;
}

.milestone-thumb img {
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

.milestone-info {
  padding: 10px;
}

.milestone-date {
  font-size: 11px;
  color: var(--primary);
  font-weight: 500;
  margin-bottom: 4px;
}

.milestone-title {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.milestone-desc {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* PC端 */
@media (min-width: 768px) {
  .milestone-card {
    width: 160px;
  }
  
  .timeline-scroll {
    margin: 0 -24px;
    padding: 0 24px;
  }
}
</style>
