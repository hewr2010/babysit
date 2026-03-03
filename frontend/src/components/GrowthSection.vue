<template>
  <section class="growth-section animate-fadeInUp stagger-2">
    <div class="section-header">
      <h2 class="section-title">生长记录</h2>
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
        <div class="chart-container">
          <v-chart v-if="chartOption" :option="chartOption" autoresize @click="handleChartClick" />
        </div>
      </div>
      
      <!-- 记录列表（点击图表点显示） -->
      <div v-if="selectedDate && recordsForDate.length > 0" class="history-section">
        <h3 class="history-title">{{ selectedDate }} 记录</h3>
        <div class="history-list">
          <div class="metrics-list">
            <div v-for="record in recordsForDate" :key="record.id" class="metric-item">
              <div class="metric-icon">{{ getMetricIcon(record.metric_type) }}</div>
              <div class="metric-info">
                <div class="metric-label">{{ getMetricLabel(record.metric_type) }}</div>
                <div class="metric-value">{{ record.value }}{{ getMetricUnit(record.metric_type) }}</div>
              </div>
              <button class="delete-btn" @click="handleDelete(record.id, record.metric_type)" title="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="selectedDate" class="history-section empty-history">
        <span class="empty-hint">{{ selectedDate }} 无记录</span>
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

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const store = useAppStore()

// 选中的日期
const selectedDate = ref(null)

// 处理图表点击事件
function handleChartClick(params) {
  selectedDate.value = params.name
}

// 获取选中日期的记录
const recordsForDate = computed(() => {
  if (!selectedDate.value) return []
  return store.growthRecords
    .filter(r => r.date === selectedDate.value)
    .sort((a, b) => {
      const order = { height: 0, weight: 1 }
      return order[a.metric_type] - order[b.metric_type]
    })
})

// 删除单个指标
function handleDelete(id, metricType) {
  const metricNames = { height: '身高', weight: '体重' }
  if (confirm(`确定要删除这条${metricNames[metricType]}记录吗？`)) {
    store.deleteGrowth(id)
  }
}

// 按指标类型分组
const metricsByType = computed(() => {
  const grouped = {
    height: [],
    weight: []
  }
  
  store.growthRecords.forEach(record => {
    if (record.metric_type && grouped[record.metric_type]) {
      grouped[record.metric_type].push(record)
    }
  })
  
  return grouped
})

// 最新数据卡片
const latestGrowth = computed(() => {
  return [
    { 
      label: '身高', 
      value: metricsByType.value.height[0]?.value || '-', 
      unit: 'cm' 
    },
    { 
      label: '体重', 
      value: metricsByType.value.weight[0]?.value || '-', 
      unit: 'g' 
    }
  ]
})



// 辅助函数
function getMetricIcon(type) {
  const icons = { height: '📏', weight: '⚖️' }
  return icons[type] || ''
}

function getMetricLabel(type) {
  const labels = { height: '身高', weight: '体重' }
  return labels[type] || ''
}

function getMetricUnit(type) {
  const units = { height: 'cm', weight: 'g' }
  return units[type] || ''
}

const chartOption = computed(() => {
  // 身高和体重各自用独立的日期轴，不混在一起
  const heightRecords = metricsByType.value.height.slice().reverse() // 按日期升序
  const weightRecords = metricsByType.value.weight.slice().reverse()
  
  // 获取所有日期用于 x 轴（合并去重排序）
  const heightDates = heightRecords.map(r => r.date)
  const weightDates = weightRecords.map(r => r.date)
  const allDates = [...new Set([...heightDates, ...weightDates])].sort()
  
  // 构建系列数据 - 每个指标只在自己的日期上有值
  const series = []
  const legendData = []
  
  if (heightRecords.length > 0) {
    // 身高数据：只在自己有的日期上显示，其他日期用 null
    const heightData = allDates.map(date => {
      const record = heightRecords.find(r => r.date === date)
      return record ? record.value : null
    })
    
    series.push({
      name: '身高(cm)',
      type: 'line',
      data: heightData,
      smooth: true,
      connectNulls: true, // 连接有效点之间的线
      itemStyle: { color: '#ec4899' },
      lineStyle: { width: 2 },
      symbol: 'circle',
      symbolSize: 6
    })
    legendData.push('身高(cm)')
  }
  
  if (weightRecords.length > 0) {
    // 体重数据：只在自己有的日期上显示，其他日期用 null
    const weightData = allDates.map(date => {
      const record = weightRecords.find(r => r.date === date)
      return record ? record.value : null
    })
    
    series.push({
      name: '体重(g)',
      type: 'line',
      data: weightData,
      smooth: true,
      connectNulls: true, // 连接有效点之间的线
      itemStyle: { color: '#22c55e' },
      lineStyle: { width: 2 },
      symbol: 'circle',
      symbolSize: 6
    })
    legendData.push('体重(g)')
  }
  
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let result = params[0].axisValue + '<br/>'
        params.forEach(param => {
          if (param.value !== null && param.value !== undefined) {
            result += `${param.marker}${param.seriesName}: ${param.value}<br/>`
          }
        })
        return result
      }
    },
    legend: { data: legendData, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '20%', containLabel: true },
    xAxis: {
      type: 'category',
      data: allDates,
      axisLabel: { fontSize: 10 },
      triggerEvent: true
    },
    yAxis: [
      {
        type: 'value',
        name: '身高(cm)',
        position: 'left',
        axisLabel: { fontSize: 10, color: '#ec4899' },
        axisLine: { show: true, lineStyle: { color: '#ec4899' } },
        splitLine: { show: false }
      },
      {
        type: 'value',
        name: '体重(g)',
        position: 'right',
        axisLabel: { fontSize: 10, color: '#22c55e' },
        axisLine: { show: true, lineStyle: { color: '#22c55e' } },
        splitLine: { show: false }
      }
    ],
    series: series.map((s, i) => ({
      ...s,
      yAxisIndex: i // 身高用左轴，体重用右轴
    }))
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
  gap: 16px;
}

.date-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.date-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  padding: 4px 0;
}

.metrics-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  transition: all var(--transition-fast);
}

.metric-item:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-sm);
}

.metric-icon {
  font-size: 20px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(236, 72, 153, 0.1), rgba(236, 72, 153, 0.05));
  border-radius: var(--radius-sm);
}

.metric-info {
  flex: 1;
}

.metric-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
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

.empty-history {
  text-align: center;
  padding: 16px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-tertiary);
}
</style>
