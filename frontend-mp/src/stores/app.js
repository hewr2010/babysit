import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import { API_BASE } from '../shared/api'
import { request } from '../shared/request'
import { router } from '../shared/router'

export const useAppStore = defineStore('app', () => {
  // State
  const baby = ref(null)
  const currentYear = ref(dayjs().year())
  const currentMonth = ref(dayjs().month() + 1)
  const photos = ref([])
  const growthRecords = ref([])
  const milestones = ref([])
  const loading = ref(false)

  // Getters
  const babyAge = computed(() => {
    if (!baby.value?.birthday) return null
    const birth = dayjs(baby.value.birthday)
    const now = dayjs()
    let months = now.diff(birth, 'month')
    if (now.date() < birth.date()) months--
    return Math.max(0, months)
  })

  // 宝宝年龄显示（精确到几个月几天）
  const babyAgeDisplay = computed(() => {
    if (!baby.value?.birthday) return null
    const birth = dayjs(baby.value.birthday)
    const now = dayjs()

    let months = now.diff(birth, 'month')
    if (birth.add(months, 'month').isAfter(now)) {
      months--
    }
    months = Math.max(0, months)

    const monthDate = birth.add(months, 'month')
    const days = now.diff(monthDate, 'day')

    if (months === 0) {
      return `${days}天`
    }
    return `${months}个月${days}天`
  })

  const monthDisplay = computed(() => {
    return `${currentYear.value}年${currentMonth.value}月`
  })

  const daysInMonth = computed(() => {
    return dayjs(`${currentYear.value}-${currentMonth.value}`).daysInMonth()
  })

  // Actions
  async function fetchBaby() {
    baby.value = await request(`${API_BASE}/baby`)
  }

  async function saveBaby(data) {
    await request(`${API_BASE}/baby`, {
      method: 'POST',
      data
    })
    await fetchBaby()
  }

  const photosByDate = ref({})

  async function fetchPhotos() {
    loading.value = true
    try {
      const dateGroups = await request(`${API_BASE}/album/${currentYear.value}/${currentMonth.value}`)

      // 按日期分组，保持结构
      photosByDate.value = dateGroups

      // Flatten for backward compatibility
      const sortedDates = Object.keys(dateGroups).sort().reverse()
      let allPhotos = []
      for (const date of sortedDates) {
        const files = dateGroups[date]
        files.sort((a, b) => (b.time || '').localeCompare(a.time || ''))
        allPhotos = allPhotos.concat(files)
      }
      photos.value = allPhotos
    } finally {
      loading.value = false
    }
  }

  async function fetchGrowth() {
    growthRecords.value = await request(`${API_BASE}/growth`)
  }

  async function addGrowth(data) {
    await request(`${API_BASE}/growth`, {
      method: 'POST',
      data
    })
    await fetchGrowth()
  }

  async function deleteGrowth(id) {
    await request(`${API_BASE}/growth/${id}`, { method: 'DELETE' })
    await fetchGrowth()
  }

  async function fetchMilestones() {
    try {
      milestones.value = await request(`${API_BASE}/milestones`)
    } catch (e) {
      console.error('Failed to fetch milestones:', e)
    }
  }

  function changeMonth(delta) {
    let newMonth = currentMonth.value + delta
    let newYear = currentYear.value

    if (newMonth > 12) {
      newMonth = 1
      newYear++
    } else if (newMonth < 1) {
      newMonth = 12
      newYear--
    }

    currentMonth.value = newMonth
    currentYear.value = newYear

    // 同步URL参数
    updateURL()

    fetchPhotos()
  }

  function setMonth(year, month, updateUrl = false) {
    currentYear.value = year
    currentMonth.value = month
    if (updateUrl) {
      updateURL()
    }
    fetchPhotos()
  }

  function updateURL() {
    // 只更新路径，保留查询参数
    const path = `/${currentYear.value}/${currentMonth.value}`
    const query = router.getQuery()
    router.replaceURL(path, query)
  }

  function loadFromURL() {
    const path = router.getPath()
    const match = path.match(/^\/(\d{4})\/(\d{1,2})$/)

    if (match) {
      const year = parseInt(match[1])
      const month = parseInt(match[2])

      if (year && month >= 1 && month <= 12) {
        currentYear.value = year
        currentMonth.value = month
      }
    }
  }

  async function init() {
    console.log('[store] init start')
    loadFromURL()  // 先加载URL参数
    await fetchBaby()
    await Promise.all([
      fetchPhotos(),
      fetchGrowth(),
      fetchMilestones()
    ])
    updateURL()  // 更新URL保证一致
    console.log('[store] init done')
  }

  const latestGrowthRecord = computed(() => {
    return growthRecords.value[0] || null
  })

  return {
    baby,
    currentYear,
    currentMonth,
    photos,
    photosByDate,
    growthRecords,
    milestones,
    loading,
    babyAge,
    babyAgeDisplay,
    monthDisplay,
    daysInMonth,
    latestGrowthRecord,
    fetchBaby,
    saveBaby,
    fetchPhotos,
    fetchGrowth,
    addGrowth,
    deleteGrowth,
    fetchMilestones,
    changeMonth,
    setMonth,
    init
  }
})
