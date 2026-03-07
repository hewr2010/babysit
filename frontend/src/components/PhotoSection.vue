<template>
  <section class="photo-section animate-fadeInUp stagger-4">
    <div class="section-header">
      <h2 class="section-title">{{ store.monthDisplay }}照片 ({{ store.photos.length }}张)</h2>
      <button class="refresh-btn" @click="handleRefresh" :disabled="store.loading" title="每小时自动刷新，也可手动点击">
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
               class="photo-item" 
               :class="{ 
                 video: photo.type === 'video',
                 'is-processing': !isReady(photo),
                 'is-error': isError(photo)
               }"
               @click="openPhoto(date, photo)">
            <img :src="`/thumb/${encodeURIComponent(photo.name)}`" loading="lazy" />
            <span v-if="photo.time" class="photo-time">{{ photo.time }}</span>
            <!-- 处理中遮罩 -->
            <div v-if="!isReady(photo)" class="processing-overlay">
              <span class="processing-spinner"></span>
              <span class="processing-text">处理中</span>
            </div>
            <!-- 错误提示 -->
            <div v-if="isError(photo)" class="error-overlay">
              <span class="error-icon">⚠️</span>
              <span class="error-text">处理失败</span>
            </div>
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
import { computed, onMounted, ref, watch, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

// 本地状态管理 - 不使用 provide/inject
const processingStatus = ref(new Map())
const queriedPhotos = ref(new Set())
let eventSource = null
let refreshInterval = null

// 建立 SSE 连接
function connectSSE() {
  if (eventSource) {
    eventSource.close()
  }
  
  eventSource = new EventSource('/api/media/events')
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'heartbeat' || data.type === 'connected') return
      
      if (data.filename && data.status) {
        const current = processingStatus.value.get(data.filename) || {}
        processingStatus.value.set(data.filename, { ...current, ...data.status })
        processingStatus.value = new Map(processingStatus.value)
      }
    } catch (e) {
      console.error('SSE parse error:', e)
    }
  }
  
  eventSource.onerror = () => {
    setTimeout(connectSSE, 3000)
  }
}

onMounted(() => {
  store.refreshPhotos()
  connectSSE()
  
  refreshInterval = setInterval(() => {
    store.refreshPhotos()
  }, 60 * 60 * 1000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  if (eventSource) eventSource.close()
})

// 监听照片变化
watch(() => store.photos, (newPhotos) => {
  const toQuery = newPhotos.filter(p => {
    return !queriedPhotos.value.has(p.name) && !processingStatus.value.has(p.name)
  })
  if (toQuery.length > 0) {
    queryPhotoStatus(toQuery.map(p => p.name))
  }
}, { deep: true })

async function queryPhotoStatus(filenames) {
  if (filenames.length === 0) return
  
  filenames.forEach(name => queriedPhotos.value.add(name))
  const batch = filenames.slice(0, 20)
  
  await Promise.all(batch.map(async (filename) => {
    try {
      const res = await fetch(`/api/media/status/${encodeURIComponent(filename)}`)
      if (res.ok) {
        const status = await res.json()
        processingStatus.value.set(filename, status)
      }
    } catch (e) {
      console.error('Query status failed:', e)
    }
  }))
  
  processingStatus.value = new Map(processingStatus.value)
}

const sortedPhotosByDate = computed(() => {
  const dates = Object.keys(store.photosByDate).sort().reverse()
  const result = {}
  for (const date of dates) result[date] = store.photosByDate[date]
  return result
})

function formatDate(dateStr) {
  if (dateStr === '0000-00-00') return '无日期'
  const [y, m, d] = dateStr.split('-')
  return `${m}月${d}日`
}

function isReady(photo) {
  const s = processingStatus.value.get(photo.name)
  if (!s) return false
  if (s.thumb_200 !== 'done' || s.thumb_800 !== 'done') return false
  if (photo.type === 'video' && s.video !== 'done') return false
  return true
}

function isError(photo) {
  const s = processingStatus.value.get(photo.name)
  if (!s) return false
  if (s.thumb_200 === 'error' || s.thumb_800 === 'error') return true
  if (photo.type === 'video' && s.video === 'error') return true
  return false
}

function openPhoto(date, photo) {
  if (!isReady(photo)) return
  const index = store.photos.findIndex(p => p.name === photo.name)
  if (index !== -1) modalStore.openPhotoViewer(index)
}

function viewMorePhotos(date, photos) {
  modalStore.openDayPhotos(date, photos)
}

async function handleRefresh() {
  await store.refreshPhotos()
  queriedPhotos.value.clear()
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

.photo-item:hover:not(.is-processing):not(.is-error) img {
  transform: scale(1.05);
}

.photo-item.is-processing,
.photo-item.is-error {
  cursor: not-allowed;
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
  z-index: 1;
}

.photo-item.is-processing.video::after,
.photo-item.is-error.video::after {
  display: none;
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
  z-index: 1;
}

.processing-overlay,
.error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  z-index: 2;
}

.processing-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spinner 0.8s linear infinite;
}

@keyframes spinner {
  to { transform: rotate(360deg); }
}

.processing-text,
.error-text {
  font-size: 10px;
  font-weight: 500;
}

.error-overlay {
  background: rgba(0, 0, 0, 0.5);
}

.error-icon {
  font-size: 16px;
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
