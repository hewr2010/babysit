<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.growth" class="modal-overlay" @click.self="modalStore.growth = false">
        <div class="modal-sheet">
          <div class="modal-header">
            <h3>记录生长数据</h3>
            <button class="close-btn" @click="modalStore.growth = false">✕</button>
          </div>
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label>日期 <span class="required">*</span></label>
              <input v-model="form.date" type="date" required />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>身高 (cm) <span class="required">*</span></label>
                <input v-model="form.height" type="number" step="0.1" placeholder="52.5" required />
              </div>
              <div class="form-group">
                <label>体重 (g) <span class="required">*</span></label>
                <input v-model="form.weight" type="number" step="1" min="0" placeholder="3500" required />
              </div>
            </div>
            <div class="form-group">
              <label>头围 (cm) <span class="required">*</span></label>
              <input v-model="form.head" type="number" step="0.1" placeholder="36.0" required />
            </div>
            <button type="submit" class="submit-btn">保存</button>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { reactive, watch } from 'vue'
import dayjs from 'dayjs'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

const form = reactive({
  date: dayjs().format('YYYY-MM-DD'),
  height: '',
  weight: '',
  head: ''
})

watch(() => modalStore.growth, (val) => {
  if (val) {
    form.date = dayjs().format('YYYY-MM-DD')
    
    // 预填充上一次的数据
    const lastRecord = store.growthRecords[0]
    if (lastRecord) {
      form.height = lastRecord.height
      form.weight = lastRecord.weight
      form.head = lastRecord.head
    } else {
      form.height = ''
      form.weight = ''
      form.head = ''
    }
  }
})

function handleSubmit() {
  // 验证所有字段都有值
  if (!form.height || !form.weight || !form.head) {
    alert('请填写所有生长数据')
    return
  }
  
  store.addGrowth({
    date: form.date,
    height: parseFloat(form.height),
    weight: parseInt(form.weight),  // 体重为整数g
    head: parseFloat(form.head)
  })
  modalStore.growth = false
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
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
