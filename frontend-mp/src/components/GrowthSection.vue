<template>
  <view class="growth-section">
    <view class="section-header">
      <text class="section-title">成长记录</text>
    </view>

    <view v-if="store.growthRecords.length > 0" class="growth-content">
      <view class="growth-cards">
        <view v-for="(item, i) in latestGrowth" :key="i" class="growth-card">
          <text class="growth-value">{{ item.value }}</text>
          <text class="growth-unit">{{ item.unit }}</text>
          <text class="growth-label">{{ item.label }}</text>
        </view>
      </view>

      <!-- 生长曲线 -->
      <LineChart
        v-if="chartDates.length > 0"
        :dates="chartDates"
        :height-data="chartHeightData"
        :weight-data="chartWeightData"
      />


    </view>

    <view v-else class="empty-state">
      <text class="empty-icon">📏</text>
      <text>暂无记录</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import LineChart from './LineChart.vue'

const store = useAppStore()

const metricsByType = computed(() => {
  const grouped = { height: [], weight: [] }
  store.growthRecords.forEach(record => {
    if (record.metric_type && grouped[record.metric_type]) {
      grouped[record.metric_type].push(record)
    }
  })
  return grouped
})

const latestGrowth = computed(() => [
  { label: '身高', value: metricsByType.value.height[0]?.value || '-', unit: 'cm' },
  { label: '体重', value: metricsByType.value.weight[0]?.value || '-', unit: 'g' }
])

// 按日期升序排列，用于折线图
const chartDates = computed(() => {
  const dates = [...new Set(store.growthRecords.map(r => r.date))].sort()
  return dates
})

const chartHeightData = computed(() => {
  return chartDates.value.map(date => {
    const record = store.growthRecords.find(r => r.date === date && r.metric_type === 'height')
    return record ? record.value : null
  })
})

const chartWeightData = computed(() => {
  return chartDates.value.map(date => {
    const record = store.growthRecords.find(r => r.date === date && r.metric_type === 'weight')
    return record ? record.value : null
  })
})

</script>

<style scoped>
.growth-section {
  background: white;
  border-radius: 24rpx;
  padding: 40rpx;
  box-shadow: 0 4rpx 24rpx rgba(0, 0, 0, 0.04);
  margin-bottom: 32rpx;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32rpx;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #6b7280;
}

.growth-content {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
}

.growth-cards {
  display: flex;
  gap: 24rpx;
}

.growth-card {
  background: #faf5f7;
  border-radius: 24rpx;
  padding: 32rpx;
  text-align: center;
  flex: 1;
}

.growth-value {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #ec4899;
}

.growth-unit {
  display: block;
  font-size: 22rpx;
  color: #9ca3af;
  margin-bottom: 8rpx;
}

.growth-label {
  display: block;
  font-size: 24rpx;
  color: #6b7280;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
  padding: 64rpx;
  color: #9ca3af;
}

.empty-icon {
  font-size: 64rpx;
}
</style>
