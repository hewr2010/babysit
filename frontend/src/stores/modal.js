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
  
  return {
    baby,
    growth,
    photoViewer,
    photoViewerIndex,
    allPhotos,
    dayPhotos,
    dayPhotosData,
    growthType,
    openPhotoViewer,
    openDayPhotos,
    openGrowth
  }
})
