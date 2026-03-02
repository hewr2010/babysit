<template>
  <div class="quick-actions">
    <button v-for="action in actions" :key="action.type" 
            class="action-btn" 
            :class="action.type"
            @click="modalStore.openRecord(action.type)">
      <span class="action-icon">{{ action.icon }}</span>
      <span class="action-label">{{ action.label }}</span>
    </button>
    <button class="action-btn" @click="modalStore.growth = true">
      <span class="action-icon">📏</span>
      <span class="action-label">生长</span>
    </button>
  </div>
</template>

<script setup>
import { useModalStore } from '../stores/modal'

const modalStore = useModalStore()

const actions = [
  { type: 'feeding', icon: '🍼', label: '喂奶' },
  { type: 'sleep', icon: '😴', label: '睡眠' },
  { type: 'diaper', icon: '🩲', label: '尿布' },
]
</script>

<style scoped>
.quick-actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: 8px;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--border);
  z-index: 100;
  overflow-x: auto;
}

@media (min-width: 768px) {
  .quick-actions {
    max-width: 600px;
    left: 50%;
    transform: translateX(-50%);
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }
}

.action-btn {
  flex: 1;
  min-width: 64px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: var(--bg);
  border: 2px solid transparent;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:active {
  transform: scale(0.95);
}

.action-btn.feeding:hover { border-color: var(--feeding); }
.action-btn.sleep:hover { border-color: var(--sleep); }
.action-btn.diaper:hover { border-color: var(--diaper); }
.action-btn.food:hover { border-color: var(--food); }

.action-icon {
  font-size: 24px;
}

.action-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}
</style>
