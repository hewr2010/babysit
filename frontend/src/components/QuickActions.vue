<template>
  <div class="quick-actions">
    <button class="action-btn height-btn" @click="modalStore.openGrowth('height')">
      <span class="action-icon">📏</span>
      <span class="action-label">身高</span>
    </button>
    <button class="action-btn weight-btn" @click="modalStore.openGrowth('weight')">
      <span class="action-icon">⚖️</span>
      <span class="action-label">体重</span>
    </button>
  </div>
</template>

<script setup>
import { useModalStore } from '../stores/modal'

const modalStore = useModalStore()
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

.action-btn.height-btn:hover { border-color: var(--height); }
.action-btn.weight-btn:hover { border-color: var(--weight); }

.action-icon {
  font-size: 24px;
}

.action-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}
</style>
