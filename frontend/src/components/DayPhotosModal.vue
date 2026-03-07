<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.dayPhotos" class="modal-overlay" @click.self="modalStore.dayPhotos = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>{{ formatDate(modalStore.dayPhotosData?.date) }} ({{ modalStore.dayPhotosData?.photos.length }}张)</h3>
            <button class="close-btn" @click="modalStore.dayPhotos = false">✕</button>
          </div>
          
          <div class="photos-container">
            <div class="photos-grid">
              <div v-for="photo in paginatedPhotos" :key="photo.name"
                   class="photo-item" :class="{ video: photo.type === 'video' }"
                   @click="openPhoto(photo)">
                <img :src="`/thumb/${encodeURIComponent(photo.name)}`" loading="lazy" />
                <span v-if="photo.time" class="photo-time">{{ photo.time }}</span>
              </div>
            </div>
          </div>
          
          <div class="pagination" v-if="totalPages > 1">
            <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
            <button class="page-btn" :disabled="currentPage === totalPages" @click="currentPage++">下一页</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

const currentPage = ref(1)
const PER_PAGE = 12

const totalPages = computed(() => {
  const photos = modalStore.dayPhotosData?.photos || []
  return Math.ceil(photos.length / PER_PAGE)
})

const paginatedPhotos = computed(() => {
  const photos = modalStore.dayPhotosData?.photos || []
  const start = (currentPage.value - 1) * PER_PAGE
  return photos.slice(start, start + PER_PAGE)
})

watch(() => modalStore.dayPhotos, (val) => {
  if (val) currentPage.value = 1
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  if (dateStr === '0000-00-00') return '无日期'
  const [year, month, day] = dateStr.split('-')
  return `${year}年${month}月${day}日`
}

function openPhoto(photo) {
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
  max-width: 700px;
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

.photos-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

@media (min-width: 768px) {
  .photos-grid {
    grid-template-columns: repeat(4, 1fr);
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

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid var(--border);
  background: white;
  border-radius: var(--radius);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  background: var(--bg);
  border-color: var(--primary);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: var(--text-secondary);
  min-width: 60px;
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
