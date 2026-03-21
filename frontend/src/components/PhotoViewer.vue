<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.photoViewer" class="viewer-overlay" @click.self="close">
        <button class="close-btn" @click="close">✕</button>

        <!-- 滑动相册容器 -->
        <div class="viewer-wrapper"
             @touchstart="handleTouchStart"
             @touchmove="handleTouchMove"
             @touchend="handleTouchEnd">
          <div class="viewer-track"
               :class="{ 'is-animating': isAnimating }"
               :style="trackStyle">
            <!-- 上一张 -->
            <div v-if="prevPhoto" class="slide prev-slide">
              <SlideContent :photo="prevPhoto" />
            </div>
            <div v-else class="slide empty-slide"></div>

            <!-- 当前 -->
            <div class="slide current-slide">
              <div v-if="loadError" class="slide-error">
                <span>{{ loadError }}</span>
              </div>
              <div v-else-if="loading && !currentPhoto?.type" class="slide-loading">
                <div class="spinner"></div>
                <span>加载中...</span>
              </div>
              <SlideContent v-else :photo="currentPhoto" :is-current="true" @loaded="loading = false" @error="onSlideError" />
            </div>

            <!-- 下一张 -->
            <div v-if="nextPhoto" class="slide next-slide">
              <SlideContent :photo="nextPhoto" />
            </div>
            <div v-else class="slide empty-slide"></div>
          </div>
        </div>

        <!-- 左右导航按钮（桌面端显示） -->
        <button class="nav-btn prev" @click.stop="navigatePrev" v-if="canPrev">‹</button>
        <button class="nav-btn next" @click.stop="navigateNext" v-if="canNext">›</button>

        <!-- 已有关联时刻 -->
        <div v-if="milestones.length > 0" class="milestones-bar">
          <div class="milestone-list">
            <div v-for="ms in milestones" :key="ms.id" class="milestone-item">
              <div class="milestone-title">⭐ {{ ms.title }}</div>
              <div v-if="ms.description" class="milestone-desc">{{ ms.description }}</div>
            </div>
          </div>
        </div>

        <!-- 底部信息栏 -->
        <div class="viewer-actions">
          <div class="bottom-bar">
            <!-- 左侧：翻页指示器 -->
            <div class="nav-info">
              <span class="photo-index">{{ currentIndex + 1 }} / {{ store.photos.length }}</span>
            </div>

            <!-- 中间：拍摄时间 -->
            <div v-if="currentPhoto?.date || currentPhoto?.time" class="photo-datetime">
              <span v-if="currentPhoto?.date">📅 {{ currentPhoto.date }}</span>
              <span v-if="currentPhoto?.time">🕒 {{ currentPhoto.time }}</span>
            </div>

            <!-- 右侧操作按钮组 -->
            <div class="action-buttons">
              <!-- 标记时刻按钮 -->
              <button
                class="action-btn milestone-btn"
                @click="openMilestoneEditor"
                :class="{ 'has-milestone': milestones.length > 0 }"
              >
                <span class="btn-icon">⭐</span>
                <span class="btn-text">标记</span>
              </button>

              <!-- 下载按钮 -->
              <button
                class="action-btn download-btn"
                @click="downloadOriginal"
                :disabled="isDownloading || isOversized"
                :class="{ 'downloading': isDownloading, 'oversized': isOversized }"
              >
                <span v-if="isDownloading" class="btn-spinner"></span>
                <template v-else-if="isLivp">
                  <span class="btn-icon">⬇️</span>
                  <span class="btn-text">视频</span>
                </template>
                <template v-else-if="isOversized">
                  <span class="btn-icon">📦</span>
                  <span class="btn-text">{{ formatFileSize(currentPhoto?.size) }} > 50MB</span>
                </template>
                <template v-else>
                  <span class="btn-icon">⬇️</span>
                  <span class="btn-text">{{ currentPhoto?.type === 'video' ? '视频' : '原图' }}</span>
                </template>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'
import SlideContent from './SlideContent.vue'

const API_BASE = '/api'

const store = useAppStore()
const modalStore = useModalStore()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const loadError = ref('')
const isDownloading = ref(false)
const milestones = ref([])

const currentIndex = computed(() => modalStore.photoViewerIndex)
const currentPhoto = computed(() => store.photos[currentIndex.value])
const prevPhoto = computed(() => store.photos[currentIndex.value - 1])
const nextPhoto = computed(() => store.photos[currentIndex.value + 1])
const canPrev = computed(() => currentIndex.value > 0)
const canNext = computed(() => currentIndex.value < store.photos.length - 1)

// 50MB 限制
const MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024

// 检查文件是否超过大小限制
const isOversized = computed(() => {
  if (!currentPhoto.value?.size) return false
  return currentPhoto.value.size > MAX_DOWNLOAD_SIZE
})

// 检查是否为 livp 文件（暂不支持下载）
const isLivp = computed(() => {
  if (!currentPhoto.value?.name) return false
  return currentPhoto.value.name.toLowerCase().endsWith('.livp')
})

// 格式化文件大小
function formatFileSize(size) {
  if (!size) return ''
  const numSize = Number(size)
  if (numSize < 1024) {
    return `${numSize}B`
  } else if (numSize < 1024 * 1024) {
    return `${(numSize / 1024).toFixed(1)}KB`
  } else if (numSize < 1024 * 1024 * 1024) {
    return `${(numSize / (1024 * 1024)).toFixed(1)}MB`
  } else {
    return `${(numSize / (1024 * 1024 * 1024)).toFixed(2)}GB`
  }
}

// 加载关联的时刻
async function loadMilestones() {
  if (!currentPhoto.value) {
    milestones.value = []
    return
  }
  try {
    const res = await fetch(`${API_BASE}/milestones/${encodeURIComponent(currentPhoto.value.name)}`)
    if (res.ok) {
      milestones.value = await res.json()
    }
  } catch (e) {
    console.error('Failed to load milestones:', e)
  }
}

// 更新 URL 为当前照片
function updatePhotoURL() {
  if (currentPhoto.value) {
    router.replace({
      query: {
        ...route.query,
        photo: currentPhoto.value.name
      }
    })
  }
}

// 打开时刻编辑器
function openMilestoneEditor() {
  modalStore.openMilestoneEditor(currentPhoto.value)
}

// 下载原文件
async function downloadOriginal() {
  if (!currentPhoto.value || isDownloading.value || isOversized.value) return

  isDownloading.value = true

  try {
    const filename = encodeURIComponent(currentPhoto.value.name)
    const downloadUrl = `/api/download/${filename}`

    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = currentPhoto.value.name
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)

  } catch (error) {
    console.error('Download error:', error)
    alert('下载失败，请稍后重试')
  } finally {
    setTimeout(() => {
      isDownloading.value = false
    }, 500)
  }
}

function onSlideError(msg) {
  loadError.value = msg
  loading.value = false
}

// 监听查看器打开
watch(() => modalStore.photoViewer, (val) => {
  if (val) {
    loading.value = true
    loadError.value = ''
    loadMilestones()
    updatePhotoURL()
    resetSwipeState()
  }
})

// 监听索引变化（左右切换）
watch(() => modalStore.photoViewerIndex, () => {
  if (modalStore.photoViewer) {
    loading.value = true
    loadError.value = ''
    loadMilestones()
    updatePhotoURL()
    resetSwipeState()
  }
})

// 监听时刻更新事件
window.addEventListener('milestone-updated', () => {
  if (modalStore.photoViewer) {
    loadMilestones()
  }
})

function close() {
  modalStore.photoViewer = false
  loadError.value = ''
  milestones.value = []

  if (route.query.photo && !route.path.includes('/milestones/manage')) {
    const { photo, ...otherQuery } = route.query
    router.replace({ query: otherQuery })
  }
}

// ========== 滑动逻辑 ==========
const SLIDE_WIDTH = 100 // 每个 slide 占 viewport 的百分比
const THRESHOLD = 0.25 // 滑动超过 25% 就切换

const trackOffset = ref(0) // 当前偏移量（百分比）
const isDragging = ref(false)
const isAnimating = ref(false)
const startX = ref(0)
const currentX = ref(0)

const trackStyle = computed(() => {
  // 初始位置是 -100%（显示中间的 current）
  const baseOffset = -SLIDE_WIDTH
  const totalOffset = baseOffset + trackOffset.value
  return {
    transform: `translateX(${totalOffset}%)`,
    willChange: isDragging.value ? 'transform' : 'auto'
  }
})

function resetSwipeState() {
  trackOffset.value = 0
  isDragging.value = false
  isAnimating.value = false
  startX.value = 0
  currentX.value = 0
}

function handleTouchStart(e) {
  if (store.photos.length <= 1) return

  isAnimating.value = false
  isDragging.value = true
  startX.value = e.touches[0].clientX
  currentX.value = startX.value
}

function handleTouchMove(e) {
  if (!isDragging.value) return

  currentX.value = e.touches[0].clientX
  const deltaX = currentX.value - startX.value

  // 计算百分比偏移
  const wrapperWidth = e.currentTarget.offsetWidth
  let offsetPercent = (deltaX / wrapperWidth) * 100

  // 边界限制：第一张不能往右滑，最后一张不能往左滑
  if (!canPrev.value && offsetPercent > 0) {
    offsetPercent = offsetPercent * 0.3 // 阻尼效果
  } else if (!canNext.value && offsetPercent < 0) {
    offsetPercent = offsetPercent * 0.3
  }

  trackOffset.value = offsetPercent
}

function handleTouchEnd(e) {
  if (!isDragging.value) return

  isDragging.value = false
  isAnimating.value = true

  const wrapperWidth = e.currentTarget.offsetWidth
  const deltaX = currentX.value - startX.value
  const deltaPercent = deltaX / wrapperWidth

  // 判断是否要切换
  let shouldSwitch = false
  let direction = 0 // -1 = 下一张(左滑), 1 = 上一张(右滑)

  if (Math.abs(deltaPercent) > THRESHOLD) {
    if (deltaPercent < 0 && canNext.value) {
      // 左滑 -> 下一张
      shouldSwitch = true
      direction = -1
    } else if (deltaPercent > 0 && canPrev.value) {
      // 右滑 -> 上一张
      shouldSwitch = true
      direction = 1
    }
  }

  if (shouldSwitch) {
    // 动画到完全切换的位置
    trackOffset.value = direction * SLIDE_WIDTH

    // 动画完成后更新索引
    setTimeout(() => {
      if (direction === 1) {
        modalStore.photoViewerIndex--
      } else {
        modalStore.photoViewerIndex++
      }
      // 索引更新后会触发 watch，自动重置 trackOffset
    }, 300)
  } else {
    // 回弹到原位
    trackOffset.value = 0
  }
}

// 按钮导航（带动画）
function navigatePrev() {
  if (!canPrev.value) return
  isAnimating.value = true
  trackOffset.value = SLIDE_WIDTH
  setTimeout(() => {
    modalStore.photoViewerIndex--
  }, 300)
}

function navigateNext() {
  if (!canNext.value) return
  isAnimating.value = true
  trackOffset.value = -SLIDE_WIDTH
  setTimeout(() => {
    modalStore.photoViewerIndex++
  }, 300)
}
</script>

<style scoped>
.viewer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 400;
  overflow: hidden;
}

.viewer-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  touch-action: pan-y;
}

.viewer-track {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
}

.viewer-track.is-animating {
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.slide {
  flex: 0 0 100%;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0 120px; /* 留出顶部关闭按钮和底部操作栏空间 */
  box-sizing: border-box;
}

.empty-slide {
  pointer-events: none;
}

.slide-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: white;
}

.slide-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #ff6b6b;
  font-size: 16px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 8px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 50%;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  z-index: 410;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 50%;
  font-size: 28px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  z-index: 410;
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.nav-btn.prev { left: 20px; }
.nav-btn.next { right: 20px; }

/* 移动端隐藏导航按钮 */
@media (max-width: 768px) {
  .nav-btn {
    display: none;
  }
}

/* 已有关联时刻 */
.milestones-bar {
  position: absolute;
  top: 70px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 410;
  max-width: 90vw;
  max-height: calc(50vh - 100px);
  overflow-y: auto;
  padding: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
  pointer-events: none;
}

.milestones-bar::-webkit-scrollbar {
  width: 4px;
}

.milestones-bar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
}

.milestone-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

.milestone-item {
  padding: 8px 14px;
  background: rgba(236, 72, 153, 0.9);
  color: white;
  border-radius: 10px;
  backdrop-filter: blur(8px);
  max-width: 80vw;
  min-width: 120px;
  text-align: center;
  pointer-events: auto;
}

.milestone-title {
  font-size: 13px;
  font-weight: 600;
}

.milestone-desc {
  font-size: 11px;
  opacity: 0.9;
  line-height: 1.3;
  margin-top: 2px;
}

/* 底部信息栏 */
.viewer-actions {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 410;
}

.bottom-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 28px;
  backdrop-filter: blur(8px);
}

.nav-info {
  display: flex;
  align-items: center;
}

.photo-index {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
  min-width: 50px;
  text-align: center;
}

.photo-datetime {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
}

.photo-datetime span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 操作按钮组 */
.action-buttons {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  border: none;
  border-radius: 18px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 标记时刻按钮 */
.milestone-btn {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.milestone-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.25);
}

.milestone-btn.has-milestone {
  background: rgba(236, 72, 153, 0.8);
}

.milestone-btn.has-milestone:hover:not(:disabled) {
  background: rgba(236, 72, 153, 1);
}

/* 下载按钮 */
.download-btn {
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
}

.download-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(236, 72, 153, 0.4);
}

.download-btn.downloading {
  background: linear-gradient(135deg, #9ca3af 0%, #d1d5db 100%);
}

.download-btn.oversized {
  background: linear-gradient(135deg, #6b7280 0%, #9ca3af 100%);
}

.btn-icon {
  font-size: 12px;
}

.btn-text {
  font-size: 12px;
}

.btn-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
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
