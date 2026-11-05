<template>
  <view class="card growth-section">
    <view class="section-heading">
      <text class="section-title">成长记录</text>
      <text class="text-button add-growth" @click="emit('add', metric)">+ 添加</text>
    </view>
    <view class="metric-summary">
      <view v-for="item in summaries" :key="item.type" class="metric-card" :class="{ active: metric === item.type }" @click="metric = item.type">
        <text class="metric-label">{{ item.label }}</text>
        <text class="metric-value">{{ item.value }} <text class="metric-unit">{{ item.unit }}</text></text>
      </view>
    </view>
    <GrowthChart v-if="filteredRecords.length" :records="filteredRecords" :metric="metric" />
    <view v-else class="empty-state">还没有{{ metric === 'height' ? '身高' : '体重' }}记录</view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import GrowthChart from '@/components/GrowthChart.vue'
import { useAppStore } from '@/stores/app'
import { latestByMetric } from '@/utils/album'

const emit = defineEmits(['add'])
const store = useAppStore()
const metric = ref('height')
const filteredRecords = computed(() => store.growthRecords.filter(record => record.metric_type === metric.value))
const summaries = computed(() => [
  { type: 'height', label: '最新身高', unit: 'cm', value: latestByMetric(store.growthRecords, 'height')?.value ?? '—' },
  { type: 'weight', label: '最新体重', unit: 'g', value: latestByMetric(store.growthRecords, 'weight')?.value ?? '—' }
])
</script>

<style scoped>
.metric-summary {
  display: flex;
  gap: 20rpx;
}

.metric-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  padding: 28rpx 24rpx;
  border: 2rpx solid transparent;
  border-radius: 24rpx;
  background: #faf5f7;
}

.metric-card.active {
  border-color: #f9a8d4;
  background: #fdf2f8;
}

.metric-label {
  order: 3;
  margin-top: 4rpx;
  color: #6b7280;
  font-size: 24rpx;
}

.metric-value {
  color: #ec4899;
  font-size: 40rpx;
  font-weight: 700;
}

.metric-unit {
  display: block;
  color: #9ca3af;
  text-align: center;
  font-size: 22rpx;
  font-weight: 400;
}

</style>
