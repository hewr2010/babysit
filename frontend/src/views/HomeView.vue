<template>
  <div class="home">
    <Header />
    <main class="main-content">
      <GrowthSection />
      <MilestoneTimeline />
      <PhotoSection />
    </main>
    <div class="safe-area"></div>

    <!-- 备案号 -->
    <footer class="beian-footer">
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
        class="beian-link"
      >
        沪ICP备2026008773号-1
      </a>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'
import Header from '../components/Header.vue'
import GrowthSection from '../components/GrowthSection.vue'
import PhotoSection from '../components/PhotoSection.vue'
import MilestoneTimeline from '../components/MilestoneTimeline.vue'

const store = useAppStore()
const modalStore = useModalStore()
const route = useRoute()
const router = useRouter()

// 打开指定照片
async function openPhotoByFilename(filename) {
  if (!filename) return

  // 处理 URL 编码：先替换 + 为空格，再解码
  let decodedFilename = filename
  try {
    decodedFilename = filename.replace(/\+/g, ' ')
    decodedFilename = decodeURIComponent(decodedFilename)
    if (decodedFilename.includes('%')) {
      decodedFilename = decodeURIComponent(decodedFilename)
    }
  } catch (e) {
    decodedFilename = filename.replace(/\+/g, ' ')
  }

  // 从文件名解析日期 (支持 YYYY-MM-DD 或 YYYYMMDD 格式)
  const dateMatch = decodedFilename.match(/(\d{4})[-]?(\d{2})[-]?(\d{2})/)
  if (dateMatch) {
    const year = parseInt(dateMatch[1])
    const month = parseInt(dateMatch[2])

    // 使用 setMonth 设置年月并加载照片
    store.setMonth(year, month, false)

    // 等待照片加载完成
    await new Promise(resolve => setTimeout(resolve, 500))

    // 查找照片索引
    const index = store.photos.findIndex(p => p.name === decodedFilename)
    if (index !== -1) {
      modalStore.openPhotoViewer(index)
    }
  }
}

onMounted(async () => {
  // 如果 URL 中有 photo 参数，优先处理
  if (route.query.photo) {
    // 从 URL 加载年月并加载数据（不更新 URL）
    const path = window.location.pathname
    const match = path.match(/\/(\d{4})\/(\d{1,2})/)
    if (match) {
      store.setMonth(parseInt(match[1]), parseInt(match[2]), false)
    }

    // 加载基础数据
    await store.fetchBaby()
    await store.fetchGrowth()

    // 等待照片加载后再打开
    await store.fetchPhotos()
    await openPhotoByFilename(route.query.photo)
  } else {
    // 正常初始化
    await store.init()
  }
})

// 监听 URL 参数变化
watch(() => route.query.photo, (newPhoto) => {
  if (newPhoto && !modalStore.photoViewer) {
    openPhotoByFilename(newPhoto)
  }
})
</script>

<style scoped>
.home {
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg);
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 16px 0;
}

.safe-area {
  height: 80px;
}

/* 备案号 */
.beian-footer {
  text-align: center;
  padding: 12px 16px 24px;
  margin-top: -10px;
}

.beian-link {
  font-size: 11px;
  color: #be185d;
  opacity: 0.5;
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.beian-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}

/* PC端 */
@media (min-width: 768px) {
  .home {
    background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 25%, #fae8ff 50%, #fde2e4 75%, #fce7f3 100%);
    padding: 40px 20px;
  }

  .main-content {
    padding: 24px 24px 0;
  }

  .safe-area {
    display: none;
  }

  .beian-footer {
    padding: 20px 24px 24px;
    margin-top: 0;
  }

  .beian-link {
    font-size: 12px;
  }
}
</style>
