<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.allPhotos" class="modal-overlay" @click.self="modalStore.allPhotos = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>{{ store.monthDisplay }}全部照片 ({{ store.photos.length }}张)</h3>
            <button class="close-btn" @click="modalStore.allPhotos = false">✕</button>
          </div>
          
          <div class="photos-container">
            <div class="timeline">
              <div v-for="(photos, date) in sortedPhotosByDate" :key="date" class="timeline-day">
                <div class="day-header">
                  <span class="day-date">{{ formatDate(date) }}</span>
                  <span class="day-count">{{ photos.length }}张</span>
                </div>
                <div class="photos-grid">
                  <div v-for="photo in photos" :key="photo.name"
                       class="photo-item" :class="{ video: photo.type === 'video' }"
                       @click="openPhoto(photo)">
                    <img :src="`/thumb/${encodeURIComponent(photo.name)}`" loading="lazy" />
                    <span v-if="photo.time" class="photo-time">{{ photo.time }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
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
  return `${year}年${month}月${day}日`
}

function openPhoto(photo) {
  // 找到该照片在所有照片中的索引
  const index = store.photos.findIndex(p => p.name === photo.name)
  if (index !== -1) {
    modalStore.openPhotoViewer(index)
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 350;
  padding: 20px;
}

.modal-content {
  background: var(--surface);
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow-xl);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--bg);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 16px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: var(--border);
}

.photos-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.timeline-day {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.day-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--primary);
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 10;
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

.photos-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (min-width: 768px) {
  .photos-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

.photo-item {
  aspect-ratio: 1;
  border-radius: var(--radius);
  overflow: hidden;
  position: relative;
  cursor: pointer;
  background: var(--bg);
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
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
  font-size: 20px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.photo-time {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 11px;
  padding: 4px;
  text-align: center;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
