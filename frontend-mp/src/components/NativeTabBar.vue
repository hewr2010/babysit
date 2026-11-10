<template>
  <view class="native-tab-bar">
    <view class="tab-item growth-tab" :class="{ active: current === 'growth' }" @click="emit('select', 'growth')">
      <view class="tab-icon chart-icon">
        <view class="chart-bar chart-bar-short" />
        <view class="chart-bar chart-bar-medium" />
        <view class="chart-bar chart-bar-tall" />
      </view>
      <text>成长曲线</text>
    </view>
    <view class="record-tab" @click="emit('record')">
      <view class="record-button">＋</view>
      <text>记录</text>
    </view>
    <view class="tab-item album-tab" :class="{ active: current === 'album' }" @click="emit('select', 'album')">
      <view class="tab-icon album-icon">
        <view class="album-sun" />
        <view class="album-mountain album-mountain-large" />
        <view class="album-mountain album-mountain-small" />
      </view>
      <text>相册</text>
    </view>
  </view>
</template>

<script setup>
defineProps({ current: { type: String, default: 'growth' } })
const emit = defineEmits(['select', 'record'])
</script>

<style scoped>
.native-tab-bar {
  position: fixed;
  z-index: 50;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-around;
  padding-top: 12rpx;
  padding-bottom: env(safe-area-inset-bottom);
  border-top: 2rpx solid #fce7f3;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 -8rpx 28rpx rgba(131, 24, 67, 0.06);
}

.tab-item,
.record-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 180rpx;
  color: #9ca3af;
  font-size: 22rpx;
}

.tab-item.active {
  color: #ec4899;
}

.tab-icon {
  box-sizing: border-box;
  height: 48rpx;
  color: inherit;
}

.chart-icon {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 6rpx;
  padding-bottom: 6rpx;
}

.chart-bar {
  width: 6rpx;
  border-radius: 3rpx;
  background: currentColor;
}

.chart-bar-short {
  height: 16rpx;
}

.chart-bar-medium {
  height: 26rpx;
}

.chart-bar-tall {
  height: 36rpx;
}

.album-icon {
  position: relative;
  width: 42rpx;
  height: 36rpx;
  margin-top: 4rpx;
  border: 3rpx solid currentColor;
  border-radius: 5rpx;
}

.album-sun {
  position: absolute;
  top: 5rpx;
  right: 5rpx;
  width: 6rpx;
  height: 6rpx;
  border-radius: 50%;
  background: currentColor;
}

.album-mountain {
  position: absolute;
  bottom: 3rpx;
  width: 0;
  height: 0;
  border-right: 8rpx solid transparent;
  border-bottom: 14rpx solid currentColor;
  border-left: 8rpx solid transparent;
}

.album-mountain-large {
  left: 4rpx;
}

.album-mountain-small {
  right: 4rpx;
  border-right-width: 6rpx;
  border-bottom-width: 10rpx;
  border-left-width: 6rpx;
}

.record-tab {
  color: #be185d;
}

.record-button {
  width: 72rpx;
  height: 72rpx;
  margin-top: -36rpx;
  border: 6rpx solid #ffffff;
  border-radius: 50%;
  background: linear-gradient(135deg, #ec4899, #f472b6);
  box-shadow: 0 8rpx 20rpx rgba(236, 72, 153, 0.25);
  color: #ffffff;
  text-align: center;
  line-height: 64rpx;
  font-size: 44rpx;
}
</style>
