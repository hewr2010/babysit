<template>
  <view class="native-tab-bar">
    <view class="tab-item growth-tab" :class="{ active: current === 'growth' }" @click="emit('select', 'growth')">
      <text class="tab-icon">▥</text>
      <text>成长曲线</text>
    </view>
    <view class="record-tab" @click="emit('record')">
      <view class="record-button">＋</view>
      <text>记录</text>
    </view>
    <view class="tab-item album-tab" :class="{ active: current === 'album' }" @click="emit('select', 'album')">
      <text class="tab-icon">▦</text>
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
  height: 48rpx;
  line-height: 48rpx;
  font-size: 36rpx;
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
