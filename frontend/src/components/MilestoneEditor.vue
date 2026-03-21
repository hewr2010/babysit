<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="editor-overlay" @click.self="close">
        <div class="editor-container">
          <div class="editor-header">
            <h3>⭐ 标记重要时刻</h3>
            <button class="close-btn" @click="close">✕</button>
          </div>
          
          <div class="editor-body">
            <div class="photo-preview">
              <img 
                v-if="photo" 
                :src="`/thumb/${encodeURIComponent(photo.name)}`" 
              />
            </div>
            
            <div class="form-group">
              <label>时刻标题</label>
              <input 
                v-model="title"
                type="text" 
                placeholder="例如：第一次打疫苗"
                maxlength="50"
                @keyup.enter="save"
              />
              <span class="char-count">{{ title.length }}/50</span>
            </div>
            
            <div class="form-group">
              <label>描述（可选）</label>
              <textarea 
                v-model="description"
                placeholder="添加更多细节..."
                maxlength="200"
                rows="3"
              ></textarea>
              <span class="char-count">{{ description.length }}/200</span>
            </div>
            
            <!-- 已有时刻列表 -->
            <div v-if="existingMilestones.length > 0" class="existing-milestones">
              <label>已标记的时刻</label>
              <div class="milestone-list">
                <div 
                  v-for="ms in existingMilestones" 
                  :key="ms.id"
                  class="milestone-tag"
                >
                  <span class="tag-text">{{ ms.title }}</span>
                  <button class="delete-tag" @click="deleteMilestone(ms.id)">✕</button>
                </div>
              </div>
            </div>
          </div>
          
          <div class="editor-footer">
            <button class="btn-secondary" @click="close">取消</button>
            <button 
              class="btn-primary" 
              @click="save"
              :disabled="!title.trim() || saving"
            >
              <span v-if="saving" class="spinner"></span>
              <span v-else>保存</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useModalStore } from '../stores/modal'

const API_BASE = '/api'

const modalStore = useModalStore()
const visible = ref(false)
const photo = ref(null)
const title = ref('')
const description = ref('')
const saving = ref(false)
const existingMilestones = ref([])

// 监听弹窗状态
watch(() => modalStore.milestoneEditor, (val) => {
  if (val) {
    photo.value = modalStore.milestoneEditorPhoto
    visible.value = true
    title.value = ''
    description.value = ''
    fetchExistingMilestones()
  } else {
    visible.value = false
  }
})

async function fetchExistingMilestones() {
  if (!photo.value) return
  try {
    const res = await fetch(`${API_BASE}/milestones/${encodeURIComponent(photo.value.name)}`)
    existingMilestones.value = await res.json()
  } catch (e) {
    console.error('Failed to fetch milestones:', e)
  }
}

async function save() {
  if (!title.value.trim() || !photo.value) return
  
  saving.value = true
  try {
    const res = await fetch(`${API_BASE}/milestones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        media_filename: photo.value.name,
        title: title.value.trim(),
        description: description.value.trim() || null
      })
    })
    
    if (res.ok) {
      // 清空表单并刷新列表
      title.value = ''
      description.value = ''
      await fetchExistingMilestones()
      // 可以在这里触发一个全局事件来刷新时间轴
      window.dispatchEvent(new CustomEvent('milestone-updated'))
    } else {
      const err = await res.json()
      alert(err.error || '保存失败')
    }
  } catch (e) {
    console.error('Failed to save milestone:', e)
    alert('保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

async function deleteMilestone(id) {
  if (!confirm('确定要删除这个时刻吗？')) return
  
  try {
    const res = await fetch(`${API_BASE}/milestones/${id}`, {
      method: 'DELETE'
    })
    
    if (res.ok) {
      await fetchExistingMilestones()
      window.dispatchEvent(new CustomEvent('milestone-updated'))
    }
  } catch (e) {
    console.error('Failed to delete milestone:', e)
    alert('删除失败')
  }
}

function close() {
  modalStore.closeMilestoneEditor()
}
</script>

<style scoped>
.editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.editor-container {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 400px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f3f4f6;
}

.editor-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #f3f4f6;
  border-radius: 50%;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

.editor-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.photo-preview {
  width: 120px;
  height: 120px;
  margin: 0 auto 20px;
  border-radius: 12px;
  overflow: hidden;
  background: #f3f4f6;
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.form-group {
  margin-bottom: 16px;
  position: relative;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  font-size: 14px;
  background: #f9fafb;
  transition: all 0.2s;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #ec4899;
  background: white;
  box-shadow: 0 0 0 3px rgba(236, 72, 153, 0.1);
}

.form-group textarea {
  resize: none;
  font-family: inherit;
}

.char-count {
  position: absolute;
  right: 12px;
  bottom: 12px;
  font-size: 11px;
  color: #9ca3af;
}

.form-group textarea + .char-count {
  bottom: 12px;
}

/* 已有时刻 */
.existing-milestones {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed #e5e7eb;
}

.existing-milestones label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 10px;
}

.milestone-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.milestone-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: rgba(236, 72, 153, 0.1);
  border-radius: 20px;
  font-size: 12px;
  color: #ec4899;
}

.tag-text {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-tag {
  width: 16px;
  height: 16px;
  border: none;
  background: rgba(236, 72, 153, 0.2);
  border-radius: 50%;
  font-size: 10px;
  color: #ec4899;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.delete-tag:hover {
  background: #ec4899;
  color: white;
}

/* 底部按钮 */
.editor-footer {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #f3f4f6;
}

.editor-footer button {
  flex: 1;
  padding: 12px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-secondary {
  background: #f3f4f6;
  color: #6b7280;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-primary {
  background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
