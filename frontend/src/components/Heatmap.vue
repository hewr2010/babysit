<template>
  <section class="heatmap-section animate-fadeInUp stagger-1">
    <div class="section-header">
      <h2 class="section-title">本月记录</h2>
      <div class="legend">
        <span class="legend-item">🍼 喂奶</span>
        <span class="legend-item">😴 睡眠</span>
        <span class="legend-item">🩲 尿布</span>
      </div>
    </div>
    <div class="heatmap-container">
      <div class="heatmap">
        <div class="heatmap-row header-row">
          <div class="cell corner"></div>
          <div v-for="hour in 24" :key="hour" class="cell hour-label" :class="{ 'has-num': hour % 6 === 0 }">
            {{ hour % 6 === 0 ? hour : '' }}
          </div>
        </div>
        <div v-for="day in daysInMonth" :key="day" class="heatmap-row">
          <div class="cell day-label">{{ day }}</div>
          <div v-for="hour in 24" :key="hour" 
               class="cell data-cell"
               :class="{ 'has-data': getCellData(day, hour - 1).length > 0 }"
               @click="handleCellClick(day, hour - 1)">
            <div class="badges" v-if="getCellData(day, hour - 1).length > 0">
              <span v-for="(type, idx) in getUniqueTypes(day, hour - 1)" :key="idx" 
                    class="mini-icon">{{ getTypeIcon(type) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

const daysInMonth = computed(() => store.daysInMonth)

function getCellData(day, hour) {
  const dayData = store.heatmapData[day] || {}
  return dayData[hour] || []
}

function getUniqueTypes(day, hour) {
  const records = getCellData(day, hour)
  return [...new Set(records.map(r => r.type))]
}

function handleCellClick(day, hour) {
  const records = getCellData(day, hour)
  if (records.length > 0) {
    modalStore.openRecordDetail(day, hour, records)
  }
}

function getTypeIcon(type) {
  const icons = {
    feeding: '🍼',
    sleep: '😴',
    diaper: '🩲',
  }
  return icons[type] || ''
}
</script>

<style scoped>
.heatmap-section {
  background: var(--surface);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.legend {
  display: flex;
  gap: 12px;
  font-size: 11px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
}

.heatmap-container {
  overflow-y: visible;
}

.heatmap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.heatmap-row {
  display: flex;
  gap: 2px;
  align-items: center;
}

.cell {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  flex-shrink: 0;
}

.cell.corner { background: transparent; }

.cell.day-label {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  font-size: 10px;
  color: var(--text-secondary);
  font-weight: 500;
  width: 28px;
  padding-right: 4px;
}

.cell.hour-label {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  color: var(--text-tertiary);
  width: 20px;
  height: 18px;
}

.cell.hour-label.has-num {
  color: var(--text-secondary);
  font-weight: 500;
}

.cell.data-cell {
  background: var(--bg);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}

.cell.data-cell:hover {
  background: var(--border);
}

.cell.data-cell.has-data {
  background: #e0e7ff;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  justify-content: center;
  align-items: center;
  padding: 2px;
}

.mini-icon {
  font-size: 10px;
  line-height: 1;
}
</style>
