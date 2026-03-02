<template>
  <section class="growth-section animate-fadeInUp stagger-2">
    <div class="section-header">
      <h2 class="section-title">生长记录</h2>
      <button class="add-btn" @click="modalStore.growth = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12h14"/>
        </svg>
      </button>
    </div>
    
    <div v-if="store.growthRecords.length > 0" class="growth-content">
      <!-- 最新数据卡片 -->
      <div class="growth-cards">
        <div class="growth-card" v-for="(item, i) in latestGrowth" :key="i">
          <div class="growth-value">{{ item.value }}</div>
          <div class="growth-unit">{{ item.unit }}</div>
          <div class="growth-label">{{ item.label }}</div>
        </div>
      </div>
      
      <!-- 生长曲线 -->
      <div class="chart-wrapper">
        <div class="chart-hint">👆 点击数据点查看详情</div>
        <div class="chart-container">
          <v-chart v-if="chartOption" :option="chartOption" autoresize @click="handleChartClick" />
        </div>
      </div>
      
      <!-- 选中的记录详情 -->
      <div v-if="selectedRecord" class="history-section">
        <h3 class="history-title">记录详情</h3>
        <div class="history-item selected">
          <div class="history-date">{{ selectedRecord.date }}</div>
          <div class="history-data">
            <span>📏 {{ selectedRecord.height }}cm</span>
            <span>⚖️ {{ selectedRecord.weight }}g</span>
            <span>🧠 {{ selectedRecord.head }}cm</span>
          </div>
          <button class="delete-btn" @click="handleDelete(selectedRecord.id)" title="删除">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <span class="empty-icon">📏</span>
      <span>暂无记录</span>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const store = useAppStore()
const modalStore = useModalStore()

// 当前选中的记录
const selectedRecord = ref(null)

function handleDelete(id) {
  if (confirm('确定要删除这条生长记录吗？')) {
    store.deleteGrowth(id)
    selectedRecord.value = null  // 清除选中状态
  }
}

// 只显示最新一条有效记录的值（过滤掉空值）
const latestGrowth = computed(() => {
  // 找到第一条所有字段都有有效值的记录
  const validRecord = store.growthRecords.find(r => {
    return r.height && r.weight && r.head && 
           r.height !== '' && r.weight !== '' && r.head !== ''
  })
  
  if (!validRecord) {
    return [
      { label: '身高', value: '-', unit: 'cm' },
      { label: '体重', value: '-', unit: 'kg' },
      { label: '头围', value: '-', unit: 'cm' }
    ]
  }
  
  return [
    { label: '身高', value: validRecord.height, unit: 'cm' },
    { label: '体重', value: validRecord.weight, unit: 'g' },
    { label: '头围', value: validRecord.head, unit: 'cm' }
  ]
})

// 图表点击事件
function handleChartClick(event) {
  if (event.componentType === 'series') {
    const dateStr = event.name  // x轴的日期
    const record = store.growthRecords.find(r => r.date === dateStr)
    if (record) {
      selectedRecord.value = record
    }
  }
}

const chartOption = computed(() => {
  const records = [...store.growthRecords].reverse()
  const dates = records.map(r => r.date)
  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (params) => {
        let result = params[0].axisValue + '<br/>'
        params.forEach(param => {
          if (param.seriesName.includes('体重')) {
            result += `${param.marker}${param.seriesName}: ${(param.value / 1000).toFixed(2)}kg<br/>`
          } else {
            result += `${param.marker}${param.seriesName}: ${param.value}<br/>`
          }
        })
        return result
      }
    },
    legend: { data: ['身高(cm)', '体重(kg)', '头围(cm)'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: dates,
      axisLabel: { fontSize: 10 }
    },
    yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    series: [
      { 
        name: '身高(cm)', 
        type: 'line', 
        data: records.map(r => r.height), 
        smooth: true,
        itemStyle: { color: '#ec4899' }
      },
      { 
        name: '体重(kg)', 
        type: 'line', 
        data: records.map(r => r.weight / 1000),  // 转换为kg显示
        smooth: true,
        itemStyle: { color: '#22c55e' }
      },
      { 
        name: '头围(cm)', 
        type: 'line', 
        data: records.map(r => r.head), 
        smooth: true,
        itemStyle: { color: '#f97316' }
      }
    ]
  }
})
</script>

<style scoped>
.growth-section {
  background: var(--surface);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.add-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.add-btn:hover {
  background: var(--primary-dark);
  transform: scale(1.05);
}

.add-btn svg {
  width: 18px;
  height: 18px;
}

.growth-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.growth-cards {
  display: flex;
  gap: 12px;
}

.growth-card {
  background: var(--bg);
  border-radius: var(--radius);
  padding: 16px;
  min-width: 80px;
  text-align: center;
  flex: 1;
}

.growth-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
}

.growth-unit {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.growth-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chart-hint {
  text-align: center;
  font-size: 11px;
  color: var(--text-tertiary);
  padding: 4px;
}

.chart-container {
  height: 220px;
  background: var(--bg);
  border-radius: var(--radius);
  padding: 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px;
  color: var(--text-tertiary);
}

.empty-icon {
  font-size: 32px;
}

.history-section {
  margin-top: 16px;
}

.history-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg);
  border-radius: var(--radius);
  font-size: 13px;
}

.history-item.selected {
  border: 2px solid var(--primary);
  background: linear-gradient(135deg, rgba(236, 72, 153, 0.05), rgba(236, 72, 153, 0.1));
}

.history-date {
  font-weight: 500;
  color: var(--text);
  min-width: 80px;
}

.history-data {
  flex: 1;
  display: flex;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 12px;
}

.delete-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  background: #fee2e2;
  color: #991b1b;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.delete-btn:hover {
  background: #fecaca;
  transform: scale(1.05);
}

.delete-btn svg {
  width: 16px;
  height: 16px;
}
</style>
