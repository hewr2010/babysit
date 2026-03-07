<template>
  <Teleport to="body">
    <Transition name="slide-up">
      <div v-if="modalStore.record" class="modal-overlay" @click.self="modalStore.record = false">
        <div class="modal-sheet">
          <div class="modal-handle"></div>
          <h3 class="modal-title">{{ title }}</h3>
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label>日期</label>
              <input v-model="form.date" type="date" required />
            </div>
            
            <div class="form-group">
              <label>时间</label>
              <select v-model="form.hour">
                <option v-for="h in 24" :key="h" :value="h-1">{{ h-1 }}:00</option>
              </select>
            </div>
            
            <div v-if="isFeeding" class="form-group">
              <label>奶量 (ml)</label>
              <input v-model="form.amount" type="number" placeholder="120" />
            </div>
            
            <button type="submit" class="submit-btn">保存</button>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import dayjs from 'dayjs'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

const titles = {
  feeding: '喂奶记录',
  poop: '大便记录',
  pee: '小便记录'
}

const title = computed(() => titles[modalStore.recordType] || '添加记录')
const isFeeding = computed(() => modalStore.recordType === 'feeding')

const form = reactive({
  date: dayjs().format('YYYY-MM-DD'),
  hour: dayjs().hour(),
  amount: ''
})

watch(() => modalStore.record, (val) => {
  if (val) {
    form.date = dayjs().format('YYYY-MM-DD')
    form.hour = dayjs().hour()
    form.amount = ''
  }
})

function handleSubmit() {
  const data = {
    type: modalStore.recordType,
    start_time: `${form.date}T${String(form.hour).padStart(2, '0')}:00:00`,
    amount: form.amount || null,
    unit: isFeeding.value ? 'ml' : null
  }
  
  store.addRecord(data)
  modalStore.record = false
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
  animation: slideUp var(--transition) ease;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.modal-handle {
  width: 40px;
  height: 4px;
  background: var(--border);
  border-radius: var(--radius-full);
  margin: 0 auto 20px;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  text-align: center;
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

.form-group input,
.form-group select {
  width: 100%;
  padding: 14px;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  font-size: 16px;
  background: var(--surface);
}

.form-group input:focus,
.form-group select:focus {
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

.submit-btn:active {
  background: var(--primary-dark);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: opacity var(--transition);
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
}
</style>
