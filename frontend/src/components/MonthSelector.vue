<template>
  <div class="month-selector">
    <button class="nav-btn" @click="store.changeMonth(-1)" aria-label="上个月">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15 18l-6-6 6-6"/>
      </svg>
    </button>

    <div class="month-display">
      <span class="month-year">{{ yearText }}</span>
      <span class="month-month">{{ monthText }}</span>
    </div>

    <button class="nav-btn" @click="store.changeMonth(1)" aria-label="下个月">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 18l6-6-6-6"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()

const yearText = computed(() => {
  return store.currentYear + '年'
})

const monthText = computed(() => {
  return store.currentMonth + '月'
})
</script>

<style scoped>
.month-selector {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  margin: 16px 16px 0;
  padding: 12px 16px;
  border-radius: 20px;
  box-shadow:
    0 4px 20px rgba(236, 72, 153, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.nav-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(253, 242, 248, 0.8);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #be185d;
}

.nav-btn:hover {
  background: rgba(236, 72, 153, 0.1);
  transform: scale(1.05);
}

.nav-btn:active {
  transform: scale(0.95);
}

.nav-btn svg {
  width: 18px;
  height: 18px;
}

.month-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.month-year {
  font-size: 11px;
  color: #be185d;
  opacity: 0.7;
  font-weight: 500;
}

.month-month {
  font-size: 18px;
  font-weight: 700;
  color: #831843;
  line-height: 1.2;
}

/* PC端适配 */
@media (min-width: 768px) {
  .month-selector {
    max-width: 600px;
    margin: 20px auto 0;
    padding: 14px 24px;
    border-radius: 24px;
  }

  .nav-btn {
    width: 40px;
    height: 40px;
    border-radius: 16px;
  }

  .nav-btn svg {
    width: 20px;
    height: 20px;
  }

  .month-year {
    font-size: 12px;
  }

  .month-month {
    font-size: 20px;
  }
}
</style>
