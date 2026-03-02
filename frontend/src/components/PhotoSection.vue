<template>
  <section class="photo-section animate-fadeInUp stagger-4">
    <div class="section-header">
      <h2 class="section-title">{{ store.monthDisplay }}照片 ({{ store.photos.length }}张)</h2>
      <button class="refresh-btn" @click="handleRefresh" :disabled="store.loading" title="刷新照片">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: store.loading }">
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
        </svg>
      </button>
    </div>
    <div v-if="store.photos.length === 0" class="empty-state">
      <span class="empty-icon">📷</span>
      <span>本月还没有照片</span>
    </div>
    <div v-else class="timeline">
      <div v-for="(photos, date) in sortedPhotosByDate" :key="date" class="timeline-day">
        <div class="day-header">
          <span class="day-date">{{ formatDate(date) }}</span>
          <span class="day-count">{{ photos.length }}张</span>
        </div>
        <div class="photo-grid">
          <div v-for="photo in photos.slice(0, 6)" :key="photo.name" 
               class="photo-item" :class="{ video: photo.type === 'video' }"
               @click="openPhoto(date, photo)">
            <img :src="`/thumb/${encodeURIComponent(photo.name)}`" loading="lazy" />
            <span v-if="photo.time" class="photo-time">{{ photo.time }}</span>
          </div>
        </div>
        <button v-if="photos.length > 6" class="view-more-btn" @click="viewMorePhotos(date, photos)">
          查看更多 ({{ photos.length - 6 }}张)
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

// 按日期排序（最新的在前）
const sortedPhotosByDate = computed(() => {
  const dates = Object.keys(store.photosByDate).sort().reverse()
  const result = {}
  for (const date of dates) {
    result[date] = store.photosByDate[date]
  }
  return result
})

function formatDate(dateStr) {
  if (dateStr === '0000-00-00') return '无日期'
  const [year, month, day] = dateStr.split('-')
  return `${month}月${day}日`
}

function openPhoto(date, photo) {
  // 找到该照片在所有照片中的索引
  const index = store.photos.findIndex(p => p.name === photo.name)
  if (index !== -1) {
    modalStore.openPhotoViewer(index)
  }
}

function viewMorePhotos(date, photos) {
  modalStore.openDayPhotos(date, photos)
}

async function handleRefresh() {
  await store.refreshPhotos()
}
</script>

<style scoped>
.photo-section {
  background: var(--surface);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
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

.refresh-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  background: var(--bg);
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  color: var(--text-secondary);
}

.refresh-btn:hover:not(:disabled) {
  background: var(--border);
  color: var(--primary);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-btn svg {
  width: 18px;
  height: 18px;
}

.refresh-btn svg.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.timeline-day {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.day-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--primary);
}

.day-date {
  font-size: 15px;
  font-weight: 600;
  color: var(--primary);
}

.day-count {
  font-size: 12px;
  color: var(--text-tertiary);
  background: var(--bg);
  padding: 2px 8px;
  border-radius: 12px;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

@media (min-width: 768px) {
  .photo-grid {
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
  }
}

.view-more-btn {
  width: 100%;
  padding: 8px;
  margin-top: 8px;
  border: 1px dashed var(--primary);
  background: transparent;
  color: var(--primary);
  border-radius: var(--radius);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.view-more-btn:hover {
  background: rgba(236, 72, 153, 0.05);
  border-style: solid;
}

.photo-item {
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  overflow: hidden;
  position: relative;
  cursor: pointer;
  background: var(--bg);
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.photo-item:hover img {
  transform: scale(1.05);
}

.photo-item.video::after {
  content: "▶";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 16px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.photo-time {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 9px;
  padding: 2px 4px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px;
  color: var(--text-tertiary);
}

.empty-icon {
  font-size: 40px;
}
</style>
