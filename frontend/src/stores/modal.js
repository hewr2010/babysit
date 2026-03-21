import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useModalStore = defineStore('modal', () => {
  const baby = ref(false)
  const growth = ref(false)
  const growthType = ref('height') // 'height' 或 'weight'
  const photoViewer = ref(false)
  const photoViewerIndex = ref(0)
  const allPhotos = ref(false)
  const dayPhotos = ref(false)
  const dayPhotosData = ref(null)
  
  // 重要时刻编辑器
  const milestoneEditor = ref(false)
  const milestoneEditorPhoto = ref(null)
  
  function openPhotoViewer(index) {
    photoViewerIndex.value = index
    photoViewer.value = true
  }
  
  function openDayPhotos(date, photos) {
    dayPhotosData.value = { date, photos }
    dayPhotos.value = true
  }
  
  function openGrowth(type) {
    growthType.value = type
    growth.value = true
  }
  
  function openMilestoneEditor(photo) {
    milestoneEditorPhoto.value = photo
    milestoneEditor.value = true
  }
  
  function closeMilestoneEditor() {
    milestoneEditor.value = false
    milestoneEditorPhoto.value = null
  }
  
  return {
    baby,
    growth,
    growthType,
    photoViewer,
    photoViewerIndex,
    allPhotos,
    dayPhotos,
    dayPhotosData,
    milestoneEditor,
    milestoneEditorPhoto,
    openPhotoViewer,
    openDayPhotos,
    openGrowth,
    openMilestoneEditor,
    closeMilestoneEditor
  }
})
