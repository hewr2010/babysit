<template>
  <section class="summary-section animate-fadeInUp">
    <h2 class="section-title">昨日总结</h2>
    <div class="cards-grid">
      <div class="summary-card" v-for="(item, i) in summaryItems" :key="i" :class="`stagger-${i+1}`">
        <div class="card-icon">{{ item.icon }}</div>
        <div class="card-value">{{ item.value }}</div>
        <div class="card-label">{{ item.label }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()

const summaryItems = computed(() => [
  { icon: '😴', value: store.yesterdaySummary.sleep || '-', label: '睡眠时长' },
  { icon: '🍼', value: store.yesterdaySummary.feeding_count || '-', label: '喂奶次数' },
  { icon: '🩲', value: store.yesterdaySummary.diaper_count || '-', label: '换尿布' }
])
</script>

<style scoped>
.summary-section {
  background: var(--surface);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.summary-card {
  background: linear-gradient(135deg, var(--bg) 0%, white 100%);
  border-radius: var(--radius);
  padding: 16px 8px;
  text-align: center;
  border: 1px solid var(--border);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.card-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 4px;
}

.card-label {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
