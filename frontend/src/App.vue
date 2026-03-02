<template>
  <div class="app">
    <div class="app-container">
      <Header />
      <main class="main-content">
        <SummaryCards />
        <Heatmap />
        <GrowthSection />
        <PhotoSection />
      </main>
    </div>
    <QuickActions />
    <RecordModal />
    <BabyModal />
    <GrowthModal />
    <RecordDetailModal />
    <PhotoViewer />
    <AllPhotosModal />
    <DayPhotosModal />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'
import Header from './components/Header.vue'
import SummaryCards from './components/SummaryCards.vue'
import Heatmap from './components/Heatmap.vue'
import GrowthSection from './components/GrowthSection.vue'
import PhotoSection from './components/PhotoSection.vue'
import QuickActions from './components/QuickActions.vue'
import RecordModal from './components/RecordModal.vue'
import BabyModal from './components/BabyModal.vue'
import GrowthModal from './components/GrowthModal.vue'
import RecordDetailModal from './components/RecordDetailModal.vue'
import PhotoViewer from './components/PhotoViewer.vue'
import AllPhotosModal from './components/AllPhotosModal.vue'
import DayPhotosModal from './components/DayPhotosModal.vue'

const store = useAppStore()

onMounted(() => {
  store.init()
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
