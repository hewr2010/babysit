<template>
  <view class="auth-wall">
    <view class="auth-box">
      <view class="auth-icon">👶</view>
      <text class="auth-title">宝宝成长日志</text>
      <text class="auth-desc">请输入宝宝的真名以继续访问</text>
      <view class="auth-input-wrapper">
        <input
          v-model="inputName"
          type="text"
          placeholder="宝宝真名"
          class="auth-input"
          confirm-type="done"
          @confirm="verify"
        />
      </view>
      <text v-if="errorMsg" class="auth-error">{{ errorMsg }}</text>
      <button class="auth-btn" :disabled="!inputName.trim()" @click="verify">
        进入
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { storage } from '@/shared/storage'

const CORRECT_NAME = '何与青'
const AUTH_KEY = 'baby_auth_verified'

const inputName = ref('')
const errorMsg = ref('')

onMounted(() => {
  console.log('[auth] onMounted')
  const verified = storage.get(AUTH_KEY)
  console.log('[auth] verified:', verified)
  if (verified === 'true') {
    goHome()
  }
})

function verify() {
  const name = inputName.value.trim()
  if (!name) return

  if (name === CORRECT_NAME) {
    storage.set(AUTH_KEY, 'true')
    errorMsg.value = ''
    goHome()
  } else {
    errorMsg.value = '名字不对哦，请再试一次'
    inputName.value = ''
  }
}

function goHome() {
  uni.reLaunch({ url: '/pages/index/index' })
}
</script>

<style scoped>
.auth-wall {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
  background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 25%, #fae8ff 50%, #fde2e4 75%, #fce7f3 100%);
}

.auth-box {
  background: white;
  border-radius: 48rpx;
  padding: 80rpx 64rpx;
  width: 100%;
  max-width: 640rpx;
  text-align: center;
  box-shadow: 0 40rpx 120rpx rgba(236, 72, 153, 0.15);
}

.auth-icon {
  font-size: 96rpx;
  margin-bottom: 32rpx;
}

.auth-title {
  display: block;
  font-size: 40rpx;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16rpx;
}

.auth-desc {
  display: block;
  font-size: 28rpx;
  color: #9ca3af;
  margin-bottom: 48rpx;
}

.auth-input-wrapper {
  margin-bottom: 24rpx;
}

.auth-input {
  width: 100%;
  height: 96rpx;
  padding: 28rpx 32rpx;
  font-size: 32rpx;
  border: 4rpx solid #f3f4f6;
  border-radius: 24rpx;
  text-align: center;
  outline: none;
  background: white;
  box-sizing: border-box;
}

.auth-input:focus {
  border-color: #ec4899;
  background: #fdf2f8;
}

.auth-error {
  display: block;
  font-size: 26rpx;
  color: #ef4444;
  margin-bottom: 32rpx;
}

.auth-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  border: none;
  border-radius: 24rpx;
}

.auth-btn[disabled] {
  opacity: 0.5;
}

.auth-btn::after {
  border: none;
}
</style>
