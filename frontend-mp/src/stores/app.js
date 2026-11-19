import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { request } from '@/services/api'
import { flattenAlbum } from '@/utils/album'
import { ageText, currentMonth, monthKey, monthLabel, shiftMonth } from '@/utils/date'

export const useAppStore = defineStore('app', () => {
  const initialMonth = currentMonth()
  const baby = ref(null)
  const year = ref(initialMonth.year)
  const month = ref(initialMonth.month)
  const albumByDate = ref({})
  const growthRecords = ref([])
  const milestones = ref([])
  const albumLoading = ref(false)
  let albumRequestId = 0

  const media = computed(() => flattenAlbum(albumByDate.value))
  const selectedMonthKey = computed(() => monthKey(year.value, month.value))
  const selectedMonthLabel = computed(() => monthLabel(year.value, month.value))
  const babyAge = computed(() => ageText(baby.value?.birthday))
  const monthlyMilestones = computed(() => milestones.value.filter(item => item.date?.startsWith(selectedMonthKey.value)))

  async function loadBaby() {
    baby.value = await request('/baby')
  }

  async function saveBaby(data) {
    await request('/baby', { method: 'POST', data })
    await loadBaby()
  }

  async function loadGrowth() {
    growthRecords.value = await request('/growth')
  }

  async function addGrowth(data) {
    await request('/growth', { method: 'POST', data })
    await loadGrowth()
  }

  async function loadMilestones() {
    milestones.value = await request('/milestones')
  }

  async function addMilestone(data) {
    await request('/milestones', { method: 'POST', data })
    await loadMilestones()
  }

  async function removeMilestone(id) {
    await request(`/milestones/${id}`, { method: 'DELETE' })
    await loadMilestones()
  }

  async function loadAlbum(target = null) {
    const requestId = ++albumRequestId
    const targetYear = target?.year ?? year.value
    const targetMonth = target?.month ?? month.value
    albumLoading.value = true
    try {
      const groups = await request(`/album/${targetYear}/${targetMonth}`)
      if (requestId === albumRequestId) {
        albumByDate.value = groups
        if (target) {
          year.value = targetYear
          month.value = targetMonth
        }
      }
    } finally {
      if (requestId === albumRequestId) albumLoading.value = false
    }
  }

  async function changeMonth(delta) {
    const next = shiftMonth(year.value, month.value, delta)
    await loadAlbum(next)
  }

  function markMediaReady(name, status = {}) {
    for (const date of Object.keys(albumByDate.value)) {
      const item = albumByDate.value[date].find(entry => entry.name === name)
      if (item) {
        if ('preview_ready' in status) item.preview_ready = status.preview_ready
        if ('video_ready' in status) item.video_ready = status.video_ready
        return
      }
    }
  }

  async function openMediaMonth(item) {
    if (!item.date) return -1
    const [itemYear, itemMonth] = item.date.split('-').map(Number)
    if (itemYear !== year.value || itemMonth !== month.value) {
      await loadAlbum({ year: itemYear, month: itemMonth })
    }
    return media.value.findIndex(mediaItem => mediaItem.name === item.media_filename)
  }

  async function initialize() {
    await Promise.all([loadBaby(), loadGrowth(), loadMilestones(), loadAlbum()])
  }

  return {
    baby,
    year,
    month,
    albumByDate,
    markMediaReady,
    growthRecords,
    milestones,
    albumLoading,
    media,
    selectedMonthKey,
    selectedMonthLabel,
    babyAge,
    monthlyMilestones,
    loadBaby,
    saveBaby,
    loadGrowth,
    addGrowth,
    loadMilestones,
    addMilestone,
    removeMilestone,
    loadAlbum,
    changeMonth,
    openMediaMonth,
    initialize
  }
})
