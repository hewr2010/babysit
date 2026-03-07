import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useModalStore = defineStore('modal', () => {
  const record = ref(false)
  const recordType = ref('feeding')
  const baby = ref(false)
  const growth = ref(false)
  const growthType = ref('height') // 'height' 或 'weight'
  const recordDetail = ref(false)
  const recordDetailData = ref(null)
  const photoViewer = ref(false)
  const photoViewerIndex = ref(0)
  const allPhotos = ref(false)
  const dayPhotos = ref(false)
  const dayPhotosData = ref(null)
  
  function openRecord(type) {
    recordType.value = type
    record.value = true
  }
  
  function openRecordDetail(day, slot, records) {
    recordDetailData.value = { day, slot, records }
    recordDetail.value = true
  }
  
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
    record,
    recordType,
    baby,
    growth,
    recordDetail,
    recordDetailData,
    photoViewer,
    photoViewerIndex,
    allPhotos,
    dayPhotos,
    dayPhotosData,
    growthType,
    openRecord,
    openRecordDetail,
    openPhotoViewer,
    openDayPhotos,
    openGrowth
  }
})
