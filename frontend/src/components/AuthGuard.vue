<template>
  <div v-if="isAuthenticated" class="auth-container">
    <slot />
  </div>
  <div v-else class="auth-wall">
    <div class="auth-box">
      <div class="auth-icon">👶</div>
      <h2 class="auth-title">宝宝成长日志</h2>
      <p class="auth-desc">请输入宝宝的真名以继续访问</p>
      <div class="auth-input-wrapper">
        <input
          v-model="inputName"
          type="text"
          placeholder="宝宝真名"
          class="auth-input"
          @keyup.enter="verify"
        />
      </div>
      <p v-if="errorMsg" class="auth-error">{{ errorMsg }}</p>
      <button class="auth-btn" @click="verify" :disabled="!inputName.trim()">
        进入
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const CORRECT_NAME = '何与青'
const AUTH_KEY = 'baby_auth_verified'

const isAuthenticated = ref(false)
const inputName = ref('')
const errorMsg = ref('')

onMounted(() => {
  // 检查 localStorage 中是否已验证
  const verified = localStorage.getItem(AUTH_KEY)
  if (verified === 'true') {
    isAuthenticated.value = true
  }
})

function verify() {
  const name = inputName.value.trim()
  if (!name) return

  if (name === CORRECT_NAME) {
    localStorage.setItem(AUTH_KEY, 'true')
    isAuthenticated.value = true
    errorMsg.value = ''
  } else {
    errorMsg.value = '名字不对哦，请再试一次'
    inputName.value = ''
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
}

.auth-wall {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 25%, #fae8ff 50%, #fde2e4 75%, #fce7f3 100%);
}

.auth-box {
  background: white;
  border-radius: 24px;
  padding: 40px 32px;
  width: 100%;
  max-width: 320px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(236, 72, 153, 0.15);
}

.auth-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.auth-title {
  font-size: 20px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.auth-desc {
  font-size: 14px;
  color: #9ca3af;
  margin-bottom: 24px;
}

.auth-input-wrapper {
  margin-bottom: 12px;
}

.auth-input {
  width: 100%;
  padding: 14px 16px;
  font-size: 16px;
  border: 2px solid #f3f4f6;
  border-radius: 12px;
  text-align: center;
  outline: none;
  transition: all 0.2s;
  box-sizing: border-box;
}

.auth-input:focus {
  border-color: #ec4899;
  background: #fdf2f8;
}

.auth-error {
  font-size: 13px;
  color: #ef4444;
  margin-bottom: 16px;
}

.auth-btn {
  width: 100%;
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.auth-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);
}

.auth-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
