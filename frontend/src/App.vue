<template>
  <div class="app">
    <div class="app-container">
      <router-view />
    </div>

    <!-- 底部 Tab Bar -->
    <div class="tab-bar">
      <div class="tab-bar-inner">
        <button class="tab-item" :class="{ active: currentTab === 'growth' }" @click="scrollToGrowth">
          <span class="tab-icon">📊</span>
          <span class="tab-label">成长曲线</span>
        </button>

        <button class="tab-item add" @click="showActionSheet = true">
          <div class="add-btn">
            <span class="add-icon">+</span>
          </div>
          <span class="tab-label">记录</span>
        </button>

        <button class="tab-item" :class="{ active: currentTab === 'photos' }" @click="scrollToPhotos">
          <span class="tab-icon">🖼️</span>
          <span class="tab-label">相册</span>
        </button>
      </div>
    </div>

    <!-- 动作面板 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showActionSheet" class="action-sheet-overlay" @click.self="showActionSheet = false">
          <div class="action-sheet">
            <div class="action-sheet-handle"></div>
            <h3 class="action-sheet-title">记录成长</h3>
            <div class="action-grid">
              <button class="action-card" @click="openGrowth('height')">
                <div class="action-card-icon pink">
                  <span>📏</span>
                </div>
                <span class="action-card-text">记录身高</span>
              </button>
              <button class="action-card" @click="openGrowth('weight')">
                <div class="action-card-icon green">
                  <span>⚖️</span>
                </div>
                <span class="action-card-text">记录体重</span>
              </button>
            </div>
            <button class="cancel-btn" @click="showActionSheet = false">取消</button>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 全局弹窗 -->
    <BabyModal />
    <GrowthModal />
    <PhotoViewer />
    <AllPhotosModal />
    <DayPhotosModal />
    <MilestoneEditor />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useModalStore } from './stores/modal'
import BabyModal from './components/BabyModal.vue'
import GrowthModal from './components/GrowthModal.vue'
import PhotoViewer from './components/PhotoViewer.vue'
import AllPhotosModal from './components/AllPhotosModal.vue'
import DayPhotosModal from './components/DayPhotosModal.vue'
import MilestoneEditor from './components/MilestoneEditor.vue'

const route = useRoute()
const modalStore = useModalStore()
const currentTab = ref('growth')
const showActionSheet = ref(false)

// 监听路由变化，更新当前标签
watch(() => route.path, (path) => {
  if (path === '/' || path.match(/^\/\d{4}\/\d{1,2}$/)) {
    currentTab.value = 'growth'
  }
}, { immediate: true })

function scrollToGrowth() {
  currentTab.value = 'growth'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function scrollToPhotos() {
  currentTab.value = 'photos'
  const photoSection = document.querySelector('.photo-section')
  if (photoSection) {
    photoSection.scrollIntoView({ behavior: 'smooth' })
  }
}

function openGrowth(type) {
  showActionSheet.value = false
  modalStore.openGrowth(type)
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg);
}

.app-container {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  padding-bottom: 80px;
}

/* PC端 */
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
    padding: 0 0 20px;
    overflow: hidden;
    padding-bottom: 0;
  }
}

/* ========== Tab Bar ========== */
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: #ffffff;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.tab-bar-inner {
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: 64px;
  max-width: 680px;
  margin: 0 auto;
}

/* Tab 项 */
.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: none;
  background: none;
  cursor: pointer;
  padding: 8px;
  height: 64px;
  transition: all 0.2s ease;
}

.tab-icon {
  font-size: 22px;
  line-height: 1;
  transition: all 0.2s ease;
}

.tab-label {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
  transition: all 0.2s ease;
}

.tab-item.active .tab-icon {
  transform: scale(1.1);
}

.tab-item.active .tab-label {
  color: #ec4899;
  font-weight: 600;
}

/* 中间添加按钮 */
.tab-item.add .tab-label {
  color: #ec4899;
  font-weight: 600;
}

.add-btn {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(236, 72, 153, 0.3);
  transition: all 0.2s ease;
}

.add-btn:active {
  transform: scale(0.95);
}

.add-icon {
  color: white;
  font-size: 24px;
  font-weight: 300;
  line-height: 1;
  margin-top: -1px;
}

/* PC端 Tab Bar */
@media (min-width: 768px) {
  .tab-bar {
    max-width: 680px;
    left: 50%;
    transform: translateX(-50%);
    border-radius: 0 0 var(--radius-xl) var(--radius-xl);
    border-top: none;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.08);
  }
}

/* ========== 动作面板 ========== */
.action-sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.action-sheet {
  background: #ffffff;
  width: 100%;
  max-width: 680px;
  border-radius: 24px 24px 0 0;
  padding: 20px 24px 32px;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.action-sheet-handle {
  width: 40px;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  margin: 0 auto 16px;
}

.action-sheet-title {
  font-size: 17px;
  font-weight: 600;
  color: #374151;
  text-align: center;
  margin-bottom: 24px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px;
  background: #f9fafb;
  border: 2px solid transparent;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-card:hover {
  border-color: rgba(236, 72, 153, 0.2);
  background: #fdf2f8;
  transform: translateY(-2px);
}

.action-card:active {
  transform: scale(0.98);
}

.action-card-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.action-card-icon.pink {
  background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%);
}

.action-card-icon.green {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.action-card-text {
  font-size: 15px;
  font-weight: 500;
  color: #374151;
}

.cancel-btn {
  width: 100%;
  padding: 16px;
  background: #f3f4f6;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cancel-btn:hover {
  background: #e5e7eb;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
