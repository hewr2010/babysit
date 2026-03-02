<template>
  <div class="month-selector">
    <button class="nav-btn" @click="store.changeMonth(-1)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 18l-6-6 6-6"/>
      </svg>
    </button>
    <div class="month-display">{{ store.monthDisplay }}</div>
    <button class="nav-btn" @click="store.changeMonth(1)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 18l6-6-6-6"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { useAppStore } from '../stores/app'

const store = useAppStore()
</script>

<style scoped>
.month-selector {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  margin: 20px 16px 0;
  padding: 12px 16px;
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
}

.nav-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: var(--bg);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-btn:hover {
  background: var(--border);
}

.nav-btn:active {
  transform: scale(0.95);
}

.nav-btn svg {
  width: 20px;
  height: 20px;
  color: var(--text);
}

.month-display {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
}
</style>
