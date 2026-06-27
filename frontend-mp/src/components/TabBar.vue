<template>
  <view class="tab-bar">
    <view class="tab-bar-inner">
      <view class="tab-item" :class="{ active: currentTab === 'growth' }" @click="selectTab('growth')">
        <text class="tab-icon">📊</text>
        <text class="tab-label">成长曲线</text>
      </view>

      <view class="tab-item add" @click="record">
        <view class="add-btn">
          <text class="add-icon">+</text>
        </view>
        <text class="tab-label">记录</text>
      </view>

      <view class="tab-item" :class="{ active: currentTab === 'photos' }" @click="selectTab('photos')">
        <text class="tab-icon">🖼️</text>
        <text class="tab-label">相册</text>
      </view>
    </view>
  </view>
</template>

<script setup>
const props = defineProps({
  currentTab: {
    type: String,
    default: 'growth'
  }
})

const emit = defineEmits(['select', 'record'])

function selectTab(tab) {
  emit('select', tab)
}

function record() {
  emit('record')
}
</script>

<style scoped>
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 128rpx;
  background: white;
  border-top: 2rpx solid rgba(0, 0, 0, 0.06);
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom);
}

.tab-bar-inner {
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: 128rpx;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  padding: 16rpx;
  height: 128rpx;
}

.tab-icon {
  font-size: 44rpx;
  line-height: 1;
}

.tab-label {
  font-size: 22rpx;
  color: #9ca3af;
  font-weight: 500;
}

.tab-item.active .tab-icon {
  transform: scale(1.1);
}

.tab-item.active .tab-label {
  color: #ec4899;
  font-weight: 600;
}

.tab-item.add .tab-label {
  color: #ec4899;
  font-weight: 600;
}

.add-btn {
  width: 88rpx;
  height: 88rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 16rpx rgba(236, 72, 153, 0.3);
}

.add-icon {
  color: white;
  font-size: 48rpx;
  font-weight: 300;
  line-height: 1;
  margin-top: -2rpx;
}
</style>
