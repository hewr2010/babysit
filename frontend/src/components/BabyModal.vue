<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.baby" class="modal-overlay" @click.self="modalStore.baby = false">
        <div class="modal-sheet">
          <div class="modal-header">
            <h3>设置宝宝信息</h3>
            <button class="close-btn" @click="modalStore.baby = false">✕</button>
          </div>
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label>姓名</label>
              <input v-model="form.name" type="text" placeholder="宝宝姓名" required />
            </div>
            <div class="form-group">
              <label>出生日期</label>
              <input v-model="form.birthday" type="date" required />
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
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

const form = reactive({
  name: '',
  birthday: ''
})

watch(() => modalStore.baby, (val) => {
  if (val && store.baby) {
    form.name = store.baby.name || ''
    form.birthday = store.baby.birthday || ''
  }
})

function handleSubmit() {
  store.saveBaby(form)
  modalStore.baby = false
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

.form-group input {
  width: 100%;
  padding: 14px;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  font-size: 16px;
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
