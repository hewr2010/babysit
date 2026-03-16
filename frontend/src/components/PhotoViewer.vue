<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.photoViewer" class="viewer-overlay" @click.self="close">
        <button class="nav-btn prev" @click.stop="prev" v-if="canPrev">‹</button>
        <button class="nav-btn next" @click.stop="next" v-if="canNext">›</button>
        
        <button class="close-btn" @click="close">✕</button>
        
        <div class="viewer-content">
          <div v-if="loadError" class="load-error">
            <span>{{ loadError }}</span>
          </div>
          
          <div v-else-if="loading" class="loading">
            <div class="spinner"></div>
            <span>加载中...</span>
          </div>
          
          <!-- 显示中等质量预览图（已预生成） -->
          <img v-if="currentPhoto?.type === 'photo'" 
               :src="previewUrl" 
               @load="loading = false"
               class="preview-image" />
          
          <!-- 支持的视频格式：显示video播放器 -->
          <video v-else-if="currentPhoto?.type === 'video' && isSupportedVideoFormat" 
                 :src="videoUrl" 
                 controls 
                 playsinline
                 @canplay="loading = false"
                 @loadedmetadata="loading = false"
                 @error="onVideoError"
                 style="max-width: 90vw; max-height: 80vh;" />
          
          <!-- 不支持的视频格式：显示缩略图 -->
          <div v-else-if="currentPhoto?.type === 'video' && !isSupportedVideoFormat" class="unsupported-video">
            <img :src="previewUrl" 
                 @load="loading = false"
                 class="preview-image" />
            <div class="video-overlay">
              <div class="video-icon">▶</div>
              <div class="video-hint">不支持的视频格式 ({{ videoFormat }})</div>
            </div>
          </div>
        </div>
        
        <!-- 底部信息栏 - 单行布局 -->
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
            
            <!-- 右侧：下载按钮（包含文件大小） -->
            <button 
              class="download-original-btn" 
              @click="downloadOriginal"
              :disabled="isDownloading || isOversized"
              :class="{ 'downloading': isDownloading, 'oversized': isOversized }"
            >
              <span v-if="isDownloading" class="btn-spinner"></span>
              <template v-else-if="isLivp">
                <span class="btn-icon">⬇️</span>
                <span class="btn-text">
                  下载视频
                  <span v-if="currentPhoto?.size" class="size-in-btn">({{ formatFileSize(currentPhoto.size) }})</span>
                </span>
              </template>
              <template v-else-if="isOversized">
                <span class="btn-icon">📦</span>
                <span class="btn-text">{{ formatFileSize(currentPhoto?.size) }} > 50MB</span>
              </template>
              <template v-else>
                <span class="btn-icon">⬇️</span>
                <span class="btn-text">
                  {{ currentPhoto?.type === 'video' ? '原视频' : '原图' }}
                  <span v-if="currentPhoto?.size" class="size-in-btn">({{ formatFileSize(currentPhoto.size) }})</span>
                </span>
              </template>
            </button>
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

const loading = ref(true)
const loadError = ref('')
const previewUrl = ref('')
const videoUrl = ref('')
const isDownloading = ref(false)

const currentIndex = computed(() => modalStore.photoViewerIndex)
const currentPhoto = computed(() => store.photos[currentIndex.value])
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

// 检测视频格式是否被浏览器支持
const isSupportedVideoFormat = computed(() => {
  if (!currentPhoto.value || currentPhoto.value.type !== 'video') return false
  
  const filename = currentPhoto.value.name.toLowerCase()
  
  // 浏览器通常支持的格式（包括预提取的 .mov 文件）
  const supportedFormats = ['.mp4', '.webm', '.ogg', '.mov', '.livp']
  
  return supportedFormats.some(ext => filename.endsWith(ext))
})

// 获取视频格式名称
const videoFormat = computed(() => {
  if (!currentPhoto.value) return ''
  const filename = currentPhoto.value.name
  const ext = filename.substring(filename.lastIndexOf('.'))
  return ext.toUpperCase()
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

// 下载原文件 - 使用 a 标签触发浏览器下载
async function downloadOriginal() {
  if (!currentPhoto.value || isDownloading.value || isOversized.value) return
  
  isDownloading.value = true
  
  try {
    const filename = encodeURIComponent(currentPhoto.value.name)
    const downloadUrl = `/api/download/${filename}`
    
    // 使用 a 标签触发下载
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
    // 短暂延迟后恢复按钮状态
    setTimeout(() => {
      isDownloading.value = false
    }, 500)
  }
}

async function loadPhoto() {
  if (!modalStore.photoViewer || !currentPhoto.value) return
  
  loading.value = true
  loadError.value = ''
  previewUrl.value = ''
  videoUrl.value = ''
  
  if (currentPhoto.value.type === 'photo') {
    // 直接显示中等质量预览图（已预生成）
    previewUrl.value = `/preview/${encodeURIComponent(currentPhoto.value.name)}`
  } else if (currentPhoto.value.type === 'video') {
    if (isSupportedVideoFormat.value) {
      const filename = currentPhoto.value.name
      const lowerName = filename.toLowerCase()
      // .livp 文件使用已预提取的视频
      if (lowerName.endsWith('.livp')) {
        videoUrl.value = `/livp/${encodeURIComponent(filename)}`
      } else if (lowerName.endsWith('.mov') || lowerName.endsWith('.mp4')) {
        // .mov 和 .mp4 使用直链播放
        videoUrl.value = `/video/${encodeURIComponent(filename)}`
      } else {
        // 其他视频格式：显示缩略图
        previewUrl.value = `/preview/${encodeURIComponent(filename)}`
      }
      loading.value = false
    } else {
      // 不支持的视频格式：显示缩略图
      previewUrl.value = `/preview/${encodeURIComponent(currentPhoto.value.name)}`
    }
  }
}

// 监听查看器打开
watch(() => modalStore.photoViewer, (val) => {
  if (val) loadPhoto()
})

// 监听索引变化（左右切换）
watch(() => modalStore.photoViewerIndex, () => {
  if (modalStore.photoViewer) loadPhoto()
})

function close() {
  modalStore.photoViewer = false
  previewUrl.value = ''
  videoUrl.value = ''
  loadError.value = ''
}

function prev() {
  if (canPrev.value) {
    modalStore.photoViewerIndex--
  }
}

function next() {
  if (canNext.value) {
    modalStore.photoViewerIndex++
  }
}

function onVideoError(e) {
  console.error('Video load error:', e)
  loading.value = false
  loadError.value = '视频加载失败，请稍后重试'
}
</script>

<style scoped>
.viewer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 400;
}

.viewer-content {
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.viewer-content img,
.viewer-content video {
  max-width: 90vw;
  max-height: 80vh;
  object-fit: contain;
}

.preview-image {
  max-width: 90vw;
  max-height: 80vh;
}

.unsupported-video {
  position: relative;
  max-width: 90vw;
  max-height: 80vh;
}

.video-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  color: white;
  pointer-events: none;
}

.video-icon {
  font-size: 72px;
  margin-bottom: 16px;
  opacity: 0.9;
}

.video-hint {
  font-size: 16px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 8px;
  opacity: 0.95;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: white;
}

.load-error {
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

/* 底部信息栏 - 单行布局 */
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
  gap: 16px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 24px;
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

/* 下载按钮 */
.download-original-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
  border: none;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.download-original-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(236, 72, 153, 0.4);
}

.download-original-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.download-original-btn.downloading {
  background: linear-gradient(135deg, #9ca3af 0%, #d1d5db 100%);
}

.download-original-btn.oversized {
  background: linear-gradient(135deg, #6b7280 0%, #9ca3af 100%);
  font-size: 11px;
}



.btn-icon {
  font-size: 12px;
}

.btn-text {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.size-in-btn {
  opacity: 0.9;
  font-size: 11px;
  white-space: nowrap;
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
