<template>
  <div class="app">
    <div class="app-container">
      <Header />
      <main class="main-content">
        <GrowthSection />
        <PhotoSection />
      </main>
    </div>
    <QuickActions />
    <BabyModal />
    <GrowthModal />
    <PhotoViewer />
    <AllPhotosModal />
    <DayPhotosModal />
  </div>
</template>

<script setup>
import { onMounted, ref, provide, onUnmounted } from 'vue'
import { useAppStore } from './stores/app'
import Header from './components/Header.vue'
import GrowthSection from './components/GrowthSection.vue'
import PhotoSection from './components/PhotoSection.vue'
import QuickActions from './components/QuickActions.vue'
import BabyModal from './components/BabyModal.vue'
import GrowthModal from './components/GrowthModal.vue'
import PhotoViewer from './components/PhotoViewer.vue'
import AllPhotosModal from './components/AllPhotosModal.vue'
import DayPhotosModal from './components/DayPhotosModal.vue'

const store = useAppStore()

// 全局处理状态，通过 provide/inject 共享
const processingStatus = ref(new Map())
provide('processingStatus', processingStatus)

// 全局 SSE 连接
const eventSource = ref(null)

function connectSSE() {
  if (eventSource.value) {
    eventSource.value.close()
  }
  
  eventSource.value = new EventSource('/api/media/events')
  
  eventSource.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      
      // 忽略心跳消息
      if (data.type === 'heartbeat' || data.type === 'connected') {
        return
      }
      
      // 处理状态更新消息
      if (data.filename && data.status) {
        const currentStatus = processingStatus.value.get(data.filename) || {}
        const newStatus = { ...currentStatus, ...data.status }
        processingStatus.value.set(data.filename, newStatus)
        // 触发响应式更新
        processingStatus.value = new Map(processingStatus.value)
      }
    } catch (e) {
      console.error('Failed to parse SSE message:', e)
    }
  }
  
  eventSource.value.onerror = (error) => {
    console.error('SSE connection error:', error)
    // 3秒后尝试重连
    setTimeout(() => {
      if (eventSource.value) {
        connectSSE()
      }
    }, 3000)
  }
}

onMounted(() => {
  store.init()
  // 建立 SSE 连接
  connectSSE()
})

onUnmounted(() => {
  // 关闭 SSE 连接
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg);
}

/* 手机端：全宽 */
.app-container {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  padding-bottom: 100px;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0 16px;
}

/* PC端：居中卡片式 */
@media (min-width: 768px) {
  .app {
    background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 25%, #fae8ff 50%, #fde2e4 75%, #fce7f3 100%);
    padding: 40px 20px;
  }
  
  .app-container {
    max-width: 680px;
    background: var(--bg);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-xl);
    padding: 0 0 40px;
    overflow: hidden;
  }
  
  .main-content {
    padding: 0 24px;
  }
}
</style>
