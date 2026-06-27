<template>
  <view v-if="visible" class="modal-overlay" @click.self="close">
    <view class="modal-sheet">
      <view class="modal-header">
        <text class="modal-title">{{ modalTitle }}</text>
        <text class="close-btn" @click="close">✕</text>
      </view>
      <view class="form-group">
        <text class="label">日期 <text class="required">*</text></text>
        <picker mode="date" :value="form.date" @change="onDateChange">
          <view class="form-input">{{ form.date }}</view>
        </picker>
      </view>
      <view class="form-group">
        <text class="label">{{ valueLabel }} <text class="required">*</text></text>
        <input
          v-model="form.value"
          type="digit"
          :placeholder="valuePlaceholder"
          class="form-input"
          focus
        />
      </view>
      <button class="submit-btn" @click="handleSubmit">保存</button>
    </view>
  </view>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import dayjs from 'dayjs'
import { useAppStore } from '@/stores/app'

const props = defineProps({
  visible: Boolean,
  type: {
    type: String,
    default: 'height'
  }
})

const emit = defineEmits(['close'])

const store = useAppStore()

const form = reactive({
  date: dayjs().format('YYYY-MM-DD'),
  value: ''
})

const modalTitle = computed(() => props.type === 'height' ? '记录身高' : '记录体重')
const valueLabel = computed(() => props.type === 'height' ? '身高 (cm)' : '体重 (g)')
const valuePlaceholder = computed(() => props.type === 'height' ? '例如: 52.5' : '例如: 3500')

watch(() => props.visible, (val) => {
  if (val) {
    form.date = dayjs().format('YYYY-MM-DD')
    form.value = ''
  }
})

function onDateChange(e) {
  form.date = e.detail.value
}

function close() {
  emit('close')
}

async function handleSubmit() {
  if (!form.value) {
    uni.showToast({ title: '请输入数值', icon: 'none' })
    return
  }

  const data = { date: form.date }
  if (props.type === 'height') {
    data.height = parseFloat(form.value)
  } else {
    data.weight = parseInt(form.value)
  }

  await store.addGrowth(data)
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

.required {
  color: #ef4444;
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
