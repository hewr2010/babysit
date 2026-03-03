<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.growth" class="modal-overlay" @click.self="close">
        <div class="modal-sheet">
          <div class="modal-header">
            <h3>{{ modalTitle }}</h3>
            <button class="close-btn" @click="close">✕</button>
          </div>
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label>日期 <span class="required">*</span></label>
              <input v-model="form.date" type="date" required />
            </div>
            
            <!-- 身高输入 -->
            <div v-if="modalStore.growthType === 'height'" class="form-group">
              <label>身高 (cm) <span class="required">*</span></label>
              <input 
                ref="inputRef"
                v-model="form.value" 
                type="number" 
                step="0.1" 
                placeholder="例如: 52.5"
                required
              />
            </div>
            
            <!-- 体重输入 -->
            <div v-if="modalStore.growthType === 'weight'" class="form-group">
              <label>体重 (g) <span class="required">*</span></label>
              <input 
                ref="inputRef"
                v-model="form.value" 
                type="number" 
                step="1"
                min="0"
                placeholder="例如: 3500"
                required
              />
            </div>
            
            <button type="submit" class="submit-btn">保存</button>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { reactive, watch, ref, nextTick, computed } from 'vue'
import dayjs from 'dayjs'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()
const inputRef = ref(null)

const form = reactive({
  date: dayjs().format('YYYY-MM-DD'),
  value: ''
})

const modalTitle = computed(() => {
  return modalStore.growthType === 'height' ? '记录身高' : '记录体重'
})

watch(() => modalStore.growth, (val) => {
  if (val) {
    form.date = dayjs().format('YYYY-MM-DD')
    form.value = ''
    
    // 自动聚焦输入框
    nextTick(() => {
      if (inputRef.value) {
        inputRef.value.focus()
      }
    })
  }
})

function close() {
  modalStore.growth = false
}

function handleSubmit() {
  if (!form.value) {
    alert('请输入数值')
    return
  }
  
  const data = { date: form.date }
  
  if (modalStore.growthType === 'height') {
    data.height = parseFloat(form.value)
  } else if (modalStore.growthType === 'weight') {
    data.weight = parseInt(form.value)
  }
  
  store.addGrowth(data)
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
  background: var(--surface);
  width: 100%;
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--bg);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 16px;
  color: var(--text-secondary);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.required {
  color: #ef4444;
}

.form-group input {
  width: 100%;
  padding: 14px;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  font-size: 16px;
}

.form-group input:focus {
  border-color: var(--primary);
  outline: none;
}

.submit-btn {
  width: 100%;
  padding: 16px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
}

.submit-btn:hover {
  background: var(--primary-dark);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
