<template>
  <div class="direct-view">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>正在加载照片...</span>
    </div>
    
    <div v-else-if="error" class="error-state">
      <span class="error-icon">😕</span>
      <span class="error-title">{{ error }}</span>
      <router-link to="/" class="back-link">返回首页</router-link>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'
import dayjs from 'dayjs'

const API_BASE = '/api'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const modalStore = useModalStore()

const loading = ref(true)
const error = ref('')

onMounted(async () => {
  const filename = decodeURIComponent(route.params.filename)
  
  if (!filename) {
    error.value = '照片链接无效'
    loading.value = false
    return
  }
  
  // 从文件名解析日期
  // 文件名格式: IMG_YYYYMMDD_HHMMSS.jpg 或类似格式
  const dateMatch = filename.match(/(\d{4})(\d{2})(\d{2})/)
  
  if (!dateMatch) {
    error.value = '无法识别照片日期'
    loading.value = false
    return
  }
  
  const year = parseInt(dateMatch[1])
  const month = parseInt(dateMatch[2])
  const day = parseInt(dateMatch[3])
  
  // 验证日期有效性
  const photoDate = dayjs(`${year}-${month}-${day}`)
  if (!photoDate.isValid()) {
    error.value = '照片日期无效'
    loading.value = false
    return
  }
  
  // 切换到对应月份
  store.setMonth(year, month)
  
  // 等待照片加载
  await store.fetchPhotos()
  
  // 查找照片索引
  const photoIndex = store.photos.findIndex(p => p.name === filename)
  
  if (photoIndex === -1) {
    // 照片可能还在处理中，或者已被删除
    error.value = '照片未找到，可能正在处理中'
    loading.value = false
    
    // 3秒后自动跳转到对应月份
    setTimeout(() => {
      router.replace(`/${year}/${month}`)
    }, 3000)
    return
  }
  
  // 打开照片查看器
  loading.value = false
  modalStore.openPhotoViewer(photoIndex)
  
  // 替换 URL 为普通月份页面 URL
  router.replace(`/${year}/${month}`)
})
</script>

<style scoped>
.direct-view {
  min-height: 100vh;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f4f6;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state span {
  color: #6b7280;
  font-size: 14px;
}

.error-icon {
  font-size: 48px;
}

.error-title {
  font-size: 16px;
  color: #374151;
  font-weight: 500;
}

.back-link {
  padding: 10px 20px;
  background: var(--primary);
  color: white;
  text-decoration: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  margin-top: 8px;
}

.back-link:hover {
  opacity: 0.9;
}
</style>
