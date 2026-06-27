<template>
  <view class="month-selector">
    <view class="selector-inner">
      <view class="nav-arrow" @click="prevMonth">
        <text class="arrow">‹</text>
      </view>
      <text class="month-text">{{ store.monthDisplay }}</text>
      <view class="nav-arrow" @click="nextMonth">
        <text class="arrow">›</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { useAppStore } from '@/stores/app'

const store = useAppStore()

function prevMonth() {
  store.changeMonth(-1)
}

function nextMonth() {
  store.changeMonth(1)
}
</script>

<style scoped>
.month-selector {
  padding: 0 32rpx;
}

.selector-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8rpx);
  border-radius: 40rpx;
  padding: 16rpx 24rpx;
  border: 2rpx solid rgba(255, 255, 255, 0.5);
}

.nav-arrow {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.arrow {
  font-size: 48rpx;
  color: #be185d;
  font-weight: 300;
}

.month-text {
  font-size: 32rpx;
  font-weight: 600;
  color: #831843;
}
</style>
