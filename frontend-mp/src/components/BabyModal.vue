<template>
  <view v-if="visible" class="modal-overlay" @click.self="close">
    <view class="modal-sheet">
      <view class="modal-header">
        <text class="modal-title">设置宝宝信息</text>
        <text class="close-btn" @click="close">✕</text>
      </view>
      <view class="form-group">
        <text class="label">姓名</text>
        <input v-model="form.name" type="text" placeholder="宝宝姓名" class="form-input" />
      </view>
      <view class="form-group">
        <text class="label">出生日期</text>
        <picker mode="date" :value="form.birthday" @change="onDateChange">
          <view class="form-input">{{ form.birthday || '请选择出生日期' }}</view>
        </picker>
      </view>
      <view class="form-group">
        <text class="label">性别</text>
        <radio-group class="radio-group" @change="onGenderChange">
          <label class="radio-label">
            <radio value="男" :checked="form.gender === '男'" />
            <text>男</text>
          </label>
          <label class="radio-label">
            <radio value="女" :checked="form.gender === '女'" />
            <text>女</text>
          </label>
        </radio-group>
      </view>
      <button class="submit-btn" @click="handleSubmit">保存</button>
    </view>
  </view>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { useAppStore } from '@/stores/app'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['close'])

const store = useAppStore()

const form = reactive({
  name: '',
  birthday: '',
  gender: '女'
})

watch(() => props.visible, (val) => {
  if (val && store.baby) {
    form.name = store.baby.name || ''
    form.birthday = store.baby.birthday || ''
    form.gender = store.baby.gender || '女'
  }
})

function onDateChange(e) {
  form.birthday = e.detail.value
}

function onGenderChange(e) {
  form.gender = e.detail.value
}

function close() {
  emit('close')
}

async function handleSubmit() {
  await store.saveBaby(form)
  close()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  z-index: 300;
}

.modal-sheet {
  background: white;
  width: 100%;
  border-radius: 48rpx 48rpx 0 0;
  padding: 40rpx;
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40rpx;
}

.modal-title {
  font-size: 36rpx;
  font-weight: 600;
  color: #374151;
}

.close-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 50%;
  font-size: 32rpx;
  color: #6b7280;
}

.form-group {
  margin-bottom: 32rpx;
}

.label {
  display: block;
  font-size: 28rpx;
  color: #6b7280;
  margin-bottom: 12rpx;
}

.form-input {
  width: 100%;
  height: 96rpx;
  padding: 28rpx 32rpx;
  border: 4rpx solid #f3f4f6;
  border-radius: 24rpx;
  font-size: 32rpx;
  background: white;
  box-sizing: border-box;
}

.radio-group {
  display: flex;
  gap: 48rpx;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 12rpx;
  font-size: 30rpx;
  color: #374151;
}

.submit-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  background: #ec4899;
  color: white;
  border: none;
  border-radius: 24rpx;
  font-size: 32rpx;
  font-weight: 600;
  margin-top: 16rpx;
}

.submit-btn::after {
  border: none;
}
</style>
