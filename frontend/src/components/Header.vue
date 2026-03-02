<template>
  <header class="header">
    <div class="header-bg">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
    </div>
    <div class="header-content">
      <div class="baby-avatar">
        <span class="avatar-icon">👧</span>
        <div class="avatar-ring"></div>
      </div>
      <h1 class="baby-name">{{ babyName }}</h1>
      <p class="baby-age">{{ babyAgeText }}</p>
    </div>
    <MonthSelector />
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import MonthSelector from './MonthSelector.vue'

const store = useAppStore()

const babyName = computed(() => store.baby?.name || '青青')
const babyAgeText = computed(() => {
  if (!store.baby?.birthday) return '女宝 · 2026-02-12'
  const age = store.babyAge
  return `女宝 · ${age}个月 · ${store.baby.birthday}`
})
</script>

<style scoped>
.header {
  position: relative;
  padding: 24px 16px 32px;
  margin-bottom: -16px;
  overflow: hidden;
}

.header-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.4;
}

.orb-1 {
  width: 200px;
  height: 200px;
  background: #a78bfa;
  top: -50px;
  right: -50px;
  animation: float 8s ease-in-out infinite;
}

.orb-2 {
  width: 150px;
  height: 150px;
  background: #60a5fa;
  bottom: -30px;
  left: -30px;
  animation: float 6s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -20px); }
}

.header-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
}

.baby-avatar {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform var(--transition-fast);
}

.baby-avatar:active {
  transform: scale(0.95);
}

.avatar-icon {
  font-size: 36px;
  z-index: 1;
}

.avatar-ring {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.2); opacity: 0; }
}

.baby-name {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.baby-age {
  font-size: 14px;
  opacity: 0.9;
}
</style>
