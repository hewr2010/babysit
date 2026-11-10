<template>
  <AppSheet :visible="visible" :title="type === 'height' ? '记录身高' : '记录体重'" @close="emit('close')">
    <view class="field">
      <text class="field-label">测量日期</text>
      <picker mode="date" :value="date" :end="today" @change="date = $event.detail.value">
        <view class="field-input growth-date">{{ date }}</view>
      </picker>
    </view>
    <view class="field">
      <text class="field-label">{{ type === 'height' ? '身高（cm）' : '体重（kg）' }}</text>
      <input v-model="value" class="field-input growth-value-input" type="digit" :placeholder="type === 'height' ? '例如 52.5' : '例如 4.2'" />
    </view>
    <button class="primary-button save-growth" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存记录' }}</button>
  </AppSheet>
</template>

<script setup>
import { ref, watch } from 'vue'
import AppSheet from '@/components/AppSheet.vue'
import { useAppStore } from '@/stores/app'
import { today } from '@/utils/date'
import { kilogramsToGrams } from '@/utils/growth'

const props = defineProps({
  visible: Boolean,
  type: { type: String, default: 'height' }
})
const emit = defineEmits(['close'])
const store = useAppStore()
const date = ref(today())
const value = ref('')
const saving = ref(false)

watch(() => props.visible, visible => {
  if (visible) {
    date.value = today()
    value.value = ''
  }
})

async function save() {
  const number = Number(value.value)
  if (!Number.isFinite(number) || number <= 0) {
    uni.showToast({ title: props.type === 'height' ? '请输入有效身高' : '请输入有效体重（kg）', icon: 'none' })
    return
  }
  saving.value = true
  try {
    const value = props.type === 'weight' ? kilogramsToGrams(number) : number
    await store.addGrowth({ date: date.value, [props.type]: value })
    emit('close')
    uni.showToast({ title: '记录已保存', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>
