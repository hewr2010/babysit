<template>
  <view class="app-header" :style="{ paddingTop: `${statusBarHeight + 12}px` }">
    <view class="baby-card" @click="emit('edit')">
      <view class="baby-avatar">{{ store.baby?.gender === '男' ? '👦' : '👧' }}</view>
      <view class="baby-details">
        <view class="baby-name-row">
          <text class="baby-name">{{ store.baby?.name || '宝宝' }}</text>
          <text class="gender-label">{{ store.baby?.gender === '男' ? '男宝' : '女宝' }}</text>
        </view>
        <text class="baby-age">{{ store.babyAge || '等待设置生日' }}</text>
        <text v-if="store.baby?.birthday" class="baby-birthday">出生于 {{ store.baby.birthday }}</text>
      </view>
      <view class="quick-stats">
        <view class="stat-item">
          <text class="stat-value">{{ store.media.length }}</text>
          <text class="stat-label">照片</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ store.monthlyMilestones.length }}</text>
          <text class="stat-label">时刻</text>
        </view>
      </view>
    </view>
    <view class="month-switcher">
      <view class="month-arrow previous-month" @click="changeMonth(-1)">‹</view>
      <text class="month-label">{{ store.selectedMonthLabel }}</text>
      <view class="month-arrow next-month" @click="changeMonth(1)">›</view>
    </view>
  </view>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAppStore } from '@/stores/app'

const emit = defineEmits(['edit'])
const store = useAppStore()
const statusBarHeight = ref(20)
const changing = ref(false)

onMounted(() => {
  statusBarHeight.value = uni.getSystemInfoSync().statusBarHeight || 20
})

async function changeMonth(delta) {
  if (changing.value) return
  changing.value = true
  try {
    await store.changeMonth(delta)
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    changing.value = false
  }
}
</script>

<style scoped>
.app-header {
  padding-right: 32rpx;
  padding-bottom: 32rpx;
  padding-left: 32rpx;
  background: linear-gradient(160deg, #fce7f3, #fbcfe8 40%, #f5d0fe);
  border-radius: 0 0 48rpx 48rpx;
  color: #831843;
}

.baby-card {
  display: flex;
  align-items: center;
  padding: 16rpx 0 32rpx;
}

.baby-avatar {
  flex-shrink: 0;
  width: 112rpx;
  height: 112rpx;
  margin-right: 24rpx;
  border-radius: 32rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(236, 72, 153, 0.12);
  text-align: center;
  line-height: 112rpx;
  font-size: 56rpx;
}

.baby-details {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.baby-name-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.baby-name {
  overflow: hidden;
  font-size: 42rpx;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gender-label {
  flex-shrink: 0;
  color: #db2777;
  font-size: 22rpx;
}

.baby-age {
  margin-top: 6rpx;
  color: #9f1239;
  font-size: 26rpx;
}

.baby-birthday {
  margin-top: 4rpx;
  color: #be185d;
  font-size: 22rpx;
}

.quick-stats {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 16rpx;
  padding: 16rpx 20rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.65);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 52rpx;
}

.stat-value {
  color: #db2777;
  font-size: 30rpx;
  font-weight: 700;
}

.stat-label {
  color: #9f1239;
  font-size: 18rpx;
}

.stat-divider {
  width: 2rpx;
  height: 40rpx;
  margin: 0 12rpx;
  background: #f9a8d4;
}

.month-switcher {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.75);
}

.month-arrow {
  width: 96rpx;
  text-align: center;
  color: #be185d;
  font-size: 56rpx;
  line-height: 80rpx;
}

.month-label {
  font-size: 30rpx;
  font-weight: 600;
}
</style>
