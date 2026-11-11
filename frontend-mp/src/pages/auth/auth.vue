<template>
  <view class="auth-page">
    <view class="auth-card">
      <view class="auth-symbol">👶</view>
      <text class="auth-title">宝宝成长日志</text>
      <text class="auth-description">请输入宝宝的真名以继续访问</text>
      <input v-model="name" class="field-input auth-input" placeholder="宝宝真名" confirm-type="done" @confirm="verify" />
      <text v-if="error" class="auth-error">{{ error }}</text>
      <button class="primary-button auth-button" :disabled="!name.trim()" @click="verify">进入</button>
    </view>
  </view>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { isVerified, verifyName } from '@/services/auth'

const name = ref('')
const error = ref('')
const redirect = ref('')

onLoad(options => {
  const allowedPrefixes = ['/pages/viewer/viewer', '/pages/index/index', '/pages/milestones/manage']
  if (allowedPrefixes.some(prefix => options.redirect?.startsWith(prefix))) {
    redirect.value = options.redirect
  }
})

onMounted(() => {
  if (isVerified()) continueToTarget()
})

function verify() {
  if (!verifyName(name.value.trim())) {
    error.value = '名字不对，请再试一次'
    return
  }
  error.value = ''
  continueToTarget()
}

function continueToTarget() {
  uni.reLaunch({ url: redirect.value || '/pages/index/index' })
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  min-height: 100vh;
  padding: 48rpx;
  background: linear-gradient(135deg, #fce7f3, #fbcfe8 30%, #fae8ff 65%, #fde2e4);
}

.auth-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 64rpx 48rpx;
  border-radius: 40rpx;
  background: #ffffff;
  box-shadow: 0 24rpx 80rpx rgba(236, 72, 153, 0.14);
}

.auth-symbol {
  align-self: center;
  text-align: center;
  line-height: 1;
  font-size: 88rpx;
}

.auth-title {
  margin-top: 28rpx;
  color: #374151;
  text-align: center;
  font-size: 40rpx;
  font-weight: 700;
}

.auth-description {
  margin: 16rpx 0 40rpx;
  color: #9ca3af;
  text-align: center;
}

.auth-input {
  text-align: center;
}

.auth-error {
  margin-top: 16rpx;
  color: #ef4444;
  font-size: 25rpx;
}

.auth-button {
  margin-top: 32rpx;
}
</style>
