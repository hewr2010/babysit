<template>
  <view v-if="visible" class="sheet-overlay" @click="emit('close')">
    <view class="sheet-panel" @click.stop>
      <view class="sheet-header">
        <text class="sheet-title">{{ title }}</text>
        <view class="sheet-close" @click="emit('close')">×</view>
      </view>
      <slot />
    </view>
  </view>
</template>

<script setup>
defineProps({
  visible: Boolean,
  title: { type: String, default: '' }
})
const emit = defineEmits(['close'])
</script>

<style scoped>
.sheet-overlay {
  position: fixed;
  z-index: 100;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  align-items: flex-end;
  background: rgba(20, 30, 29, 0.48);
}

.sheet-panel {
  box-sizing: border-box;
  width: 100%;
  max-height: 88vh;
  overflow-y: auto;
  padding: 32rpx;
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
  border-radius: 40rpx 40rpx 0 0;
  background: #ffffff;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32rpx;
}

.sheet-title {
  font-size: 34rpx;
  font-weight: 650;
}

.sheet-close {
  width: 64rpx;
  height: 64rpx;
  line-height: 56rpx;
  text-align: center;
  color: #64716f;
  font-size: 48rpx;
}
</style>
