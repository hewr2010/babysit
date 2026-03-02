<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalStore.recordDetail" class="modal-overlay" @click.self="modalStore.recordDetail = false">
        <div class="modal-sheet">
          <div class="modal-header">
            <h3>{{ title }}</h3>
            <button class="close-btn" @click="modalStore.recordDetail = false">✕</button>
          </div>
          <div class="records-list">
            <div v-for="r in records" :key="r.id" class="record-item">
              <div class="record-icon" :style="{ background: typeColors[r.type] }">
                {{ typeIcons[r.type] }}
              </div>
              <div class="record-info">
                <div class="record-type">{{ typeNames[r.type] }}</div>
                <div class="record-meta">{{ formatTime(r.start_time) }} · {{ formatAmount(r) }}</div>
              </div>
              <button class="delete-btn" @click="handleDelete(r.id)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import dayjs from 'dayjs'
import { useAppStore } from '../stores/app'
import { useModalStore } from '../stores/modal'

const store = useAppStore()
const modalStore = useModalStore()

const typeNames = { feeding: '喂奶', sleep: '睡眠', diaper: '换尿布' }
const typeIcons = { feeding: '🍼', sleep: '😴', diaper: '🩲' }
const typeColors = { 
  feeding: 'var(--feeding)', 
  sleep: 'var(--sleep)', 
  diaper: 'var(--diaper)'
}

const data = computed(() => modalStore.recordDetailData || {})
const records = computed(() => data.value.records || [])
const title = computed(() => {
  const { day, slot } = data.value
  return day ? `${store.currentMonth}月${day}日 ${slot}:00-${slot+2}:59` : '记录详情'
})

function formatTime(time) {
  return time ? dayjs(time).format('HH:mm') : '--'
}

function formatAmount(r) {
  if (r.amount) return `${r.amount}${r.unit || ''}`
  return '无数据'
}

function handleDelete(id) {
  if (confirm('确定要删除这条记录吗？')) {
    store.deleteRecord(id)
    modalStore.recordDetail = false
  }
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
  max-height: 80vh;
  overflow-y: auto;
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

.records-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: var(--bg);
  border-radius: var(--radius);
}

.record-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.record-info {
  flex: 1;
}

.record-type {
  font-weight: 500;
  margin-bottom: 4px;
}

.record-meta {
  font-size: 12px;
  color: var(--text-tertiary);
}

.delete-btn {
  padding: 6px 12px;
  background: #fee2e2;
  color: #991b1b;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
}

.delete-btn:hover {
  background: #fecaca;
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
