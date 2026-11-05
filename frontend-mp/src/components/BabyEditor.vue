<template>
  <AppSheet :visible="visible" title="宝宝资料" @close="emit('close')">
    <view class="field">
      <text class="field-label">姓名</text>
      <input v-model="form.name" class="field-input baby-name-input" maxlength="30" placeholder="宝宝姓名" />
    </view>
    <view class="field">
      <text class="field-label">出生日期</text>
      <picker mode="date" :value="form.birthday" :end="today" @change="form.birthday = $event.detail.value">
        <view class="field-input">{{ form.birthday || '请选择出生日期' }}</view>
      </picker>
    </view>
    <view class="field">
      <text class="field-label">性别</text>
      <radio-group class="gender-options" @change="form.gender = $event.detail.value">
        <label class="gender-option"><radio value="女" :checked="form.gender === '女'" />女</label>
        <label class="gender-option"><radio value="男" :checked="form.gender === '男'" />男</label>
      </radio-group>
    </view>
    <button class="primary-button save-baby" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存资料' }}</button>
  </AppSheet>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import AppSheet from '@/components/AppSheet.vue'
import { useAppStore } from '@/stores/app'
import { today } from '@/utils/date'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close'])
const store = useAppStore()
const form = reactive({ name: '', birthday: '', gender: '女' })
const saving = ref(false)

watch(() => props.visible, visible => {
  if (!visible) return
  form.name = store.baby?.name || ''
  form.birthday = store.baby?.birthday || ''
  form.gender = store.baby?.gender || '女'
})

async function save() {
  if (!form.name.trim() || !form.birthday) {
    uni.showToast({ title: '请填写姓名和出生日期', icon: 'none' })
    return
  }
  saving.value = true
  try {
    await store.saveBaby({ name: form.name.trim(), birthday: form.birthday, gender: form.gender })
    emit('close')
    uni.showToast({ title: '资料已保存', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.gender-options {
  display: flex;
  gap: 48rpx;
}

.gender-option {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
</style>
