<template>
  <header class="header">
    <div class="header-content">
      <!-- 宝宝信息卡片 -->
      <div class="baby-card">
        <div class="baby-avatar">
          <span class="avatar-icon">{{ avatarEmoji }}</span>
        </div>
        <div class="baby-info">
          <h1 class="baby-name">{{ babyName }}</h1>
          <div class="baby-meta">
            <span class="meta-tag gender">{{ genderText }}</span>
            <span class="meta-divider">·</span>
            <span class="meta-age">{{ babyAgeText }}</span>
          </div>
          <div class="baby-birthday">{{ birthdayText }}</div>
        </div>
      </div>

      <!-- 快速统计 -->
      <div class="quick-stats" v-if="showStats">
        <div class="stat-item">
          <span class="stat-value">{{ photoCount }}</span>
          <span class="stat-label">照片</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ milestoneCount }}</span>
          <span class="stat-label">时刻</span>
        </div>
      </div>
    </div>

    <!-- 月份选择器 -->
    <MonthSelector />
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import MonthSelector from './MonthSelector.vue'

const store = useAppStore()

const babyName = computed(() => store.baby?.name || '宝宝')
const genderText = computed(() => store.baby?.gender === '男' ? '男宝' : '女宝')
const avatarEmoji = computed(() => store.baby?.gender === '男' ? '👦' : '👧')

const babyAgeText = computed(() => {
  if (!store.baby?.birthday) return '刚出生'
  return store.babyAgeDisplay
})

const birthdayText = computed(() => {
  if (!store.baby?.birthday) return ''
  return `出生于 ${store.baby.birthday}`
})

// 当月时刻数
const milestoneCount = computed(() => {
  const year = store.currentYear
  const month = String(store.currentMonth).padStart(2, '0')
  const prefix = `${year}-${month}`
  return store.milestones.filter(m => m.date && m.date.startsWith(prefix)).length
})

const showStats = computed(() => store.photos.length > 0 || milestoneCount.value > 0)
const photoCount = computed(() => store.photos.length)
</script>

<style scoped>
.header {
  position: relative;
  padding: 20px 0 16px;
  background: linear-gradient(160deg, #fce7f3 0%, #fbcfe8 40%, #f5d0fe 100%);
  border-radius: 0 0 24px 24px;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 16px 16px;
}

/* 宝宝信息卡片 */
.baby-card {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
}

.baby-avatar {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #ffffff 0%, #fdf2f8 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 2px 8px rgba(236, 72, 153, 0.15),
    inset 0 1px 2px rgba(255, 255, 255, 0.8);
  flex-shrink: 0;
}

.avatar-icon {
  font-size: 32px;
  line-height: 1;
}

.baby-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.baby-name {
  font-size: 22px;
  font-weight: 700;
  color: #831843;
  line-height: 1.2;
  letter-spacing: -0.5px;
}

.baby-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.meta-tag {
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
  font-size: 11px;
}

.meta-tag.gender {
  background: rgba(236, 72, 153, 0.12);
  color: #be185d;
}

.meta-divider {
  color: #f472b6;
  opacity: 0.6;
}

.meta-age {
  color: #9f1239;
  font-weight: 500;
}

.baby-birthday {
  font-size: 11px;
  color: #be185d;
  opacity: 0.7;
}

/* 快速统计 */
.quick-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8px);
  padding: 10px 14px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 36px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #db2777;
  line-height: 1;
}

.stat-label {
  font-size: 10px;
  color: #9f1239;
  opacity: 0.7;
  font-weight: 500;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: linear-gradient(180deg, transparent, rgba(236, 72, 153, 0.3), transparent);
}

/* PC端适配 */
@media (min-width: 768px) {
  .header {
    padding: 24px 0 20px;
    border-radius: 0 0 32px 32px;
  }

  .header-content {
    max-width: 720px;
    margin: 0 auto;
    padding: 0 24px 0;
  }

  .baby-card {
    gap: 18px;
  }

  .baby-avatar {
    width: 72px;
    height: 72px;
    border-radius: 24px;
  }

  .avatar-icon {
    font-size: 36px;
  }

  .baby-name {
    font-size: 26px;
  }

  .baby-meta {
    font-size: 14px;
    gap: 8px;
  }

  .meta-tag {
    font-size: 12px;
    padding: 3px 10px;
  }

  .baby-birthday {
    font-size: 12px;
  }

  .quick-stats {
    padding: 12px 18px;
    gap: 16px;
  }

  .stat-item {
    min-width: 44px;
  }

  .stat-value {
    font-size: 20px;
  }

  .stat-label {
    font-size: 11px;
  }
}
</style>
