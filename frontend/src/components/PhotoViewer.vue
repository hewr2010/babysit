<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.photoViewer" class="viewer-overlay" @click.self="close">
        <button class="nav-btn prev" @click.stop="prev" v-if="canPrev">‹</button>
        <button class="nav-btn next" @click.stop="next" v-if="canNext">›</button>
        
        <button class="close-btn" @click="close">✕</button>
        
        <div class="viewer-content">
          <div v-if="loading" class="loading">
            <div class="spinner"></div>
            <span>加载中...</span>
          </div>
          
          <!-- 显示中等质量预览图 -->
          <img v-if="currentPhoto?.type === 'photo'" 
               :src="previewUrl" 
               @load="loading = false"
               class="preview-image" />
          
          <!-- 支持的视频格式：显示video播放器 -->
          <video v-else-if="currentPhoto?.type === 'video' && isSupportedVideoFormat" 
                 :src="videoUrl" 
                 controls 
                 autoplay />
          
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
        
        <!-- 底部操作栏 -->
        <div class="viewer-actions">
          <div class="photo-info">
            <div class="photo-index">{{ currentIndex + 1 }} / {{ store.photos.length }}</div>
            <div v-if="currentPhoto?.date || currentPhoto?.time" class="photo-datetime">
              <span v-if="currentPhoto?.date">📅 {{ currentPhoto.date }}</span>
              <span v-if="currentPhoto?.time">🕒 {{ currentPhoto.time }}</span>
            </div>
          </div>
          <a v-if="originalUrl" 
             :href="originalUrl" 
             target="_blank" 
             class="download-btn">
            查看原图
          </a>
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
const previewUrl = ref('')
const videoUrl = ref('')
const originalUrl = ref('')

const currentIndex = computed(() => modalStore.photoViewerIndex)
const currentPhoto = computed(() => store.photos[currentIndex.value])
const canPrev = computed(() => currentIndex.value > 0)
const canNext = computed(() => currentIndex.value < store.photos.length - 1)

// 检测视频格式是否被浏览器支持
const isSupportedVideoFormat = computed(() => {
  if (!currentPhoto.value || currentPhoto.value.type !== 'video') return false
  
  const filename = currentPhoto.value.name.toLowerCase()
  
  // 浏览器通常支持的格式
  const supportedFormats = ['.mp4', '.webm', '.ogg', '.mov', '.livp']
  
  // 检查是否是支持的格式
  return supportedFormats.some(ext => filename.endsWith(ext))
})

// 获取视频格式名称
const videoFormat = computed(() => {
  if (!currentPhoto.value) return ''
  const filename = currentPhoto.value.name
  const ext = filename.substring(filename.lastIndexOf('.'))
  return ext.toUpperCase()
})

async function loadPhoto() {
  if (!modalStore.photoViewer || !currentPhoto.value) return
  
  loading.value = true
  previewUrl.value = ''
  videoUrl.value = ''
  originalUrl.value = ''
  
  if (currentPhoto.value.type === 'photo') {
    // 直接显示中等质量预览图
    previewUrl.value = `/preview/${encodeURIComponent(currentPhoto.value.name)}`
  } else if (currentPhoto.value.type === 'video') {
    if (isSupportedVideoFormat.value) {
      const filename = currentPhoto.value.name
      // .livp 文件使用特殊接口提取视频
      if (filename.toLowerCase().endsWith('.livp')) {
        videoUrl.value = `/livp/${encodeURIComponent(filename)}`
      } else {
        // 其他支持的视频格式：使用后端代理
        videoUrl.value = `/download/${encodeURIComponent(filename)}`
      }
      loading.value = false
    } else {
      // 不支持的视频格式：显示缩略图
      previewUrl.value = `/preview/${encodeURIComponent(currentPhoto.value.name)}`
    }
  }
  
  // 原图URL使用后端代理（避免浏览器直接访问百度PCS被拒绝）
  originalUrl.value = `/download/${encodeURIComponent(currentPhoto.value.name)}`
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
  originalUrl.value = ''
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
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.nav-btn.prev { left: 20px; }
.nav-btn.next { right: 20px; }

.viewer-actions {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.photo-info {
  color: white;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.photo-index {
  font-size: 14px;
  opacity: 0.9;
}

.photo-datetime {
  display: flex;
  gap: 16px;
  font-size: 13px;
  opacity: 0.95;
  background: rgba(255, 255, 255, 0.1);
  padding: 6px 16px;
  border-radius: 20px;
}

.download-btn {
  padding: 10px 24px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
}

.download-btn:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
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
