<template>
  <view class="header" :style="headerStyle">
    <view class="header-content">
      <view class="baby-card" @click="openBabyModal">
        <view class="baby-avatar">
          <text class="avatar-icon">{{ avatarEmoji }}</text>
        </view>
        <view class="baby-info">
          <view class="baby-title">
            <text class="baby-name">{{ babyName }}</text>
            <text class="meta-tag gender">{{ genderText }}</text>
          </view>
          <text class="meta-age">{{ babyAgeText }}</text>
          <text class="baby-birthday">{{ birthdayText }}</text>
        </view>
      </view>

      <view v-if="showStats" class="quick-stats">
        <view class="stat-item">
          <text class="stat-value">{{ photoCount }}</text>
          <text class="stat-label">照片</text>
        </view>
        <view class="stat-divider"></view>
        <view class="stat-item">
          <text class="stat-value">{{ milestoneCount }}</text>
          <text class="stat-label">时刻</text>
        </view>
      </view>
    </view>

    <MonthSelector />
  </view>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import MonthSelector from './MonthSelector.vue'

const store = useAppStore()
const emit = defineEmits(['openBaby'])

const safeTop = ref(44)

const headerStyle = computed(() => ({
  paddingTop: `${safeTop.value}px`
}))

onMounted(() => {
  try {
    const sys = uni.getSystemInfoSync()
    const statusBar = sys.statusBarHeight || 0
    // 顶部留足状态栏高度 + 呼吸间距
    safeTop.value = statusBar + 20
  } catch (e) {
    // 使用默认值
  }
})

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

const milestoneCount = computed(() => {
  const year = store.currentYear
  const month = String(store.currentMonth).padStart(2, '0')
  const prefix = `${year}-${month}`
  return store.milestones.filter(m => m.date && m.date.startsWith(prefix)).length
})

const showStats = computed(() => store.photos.length > 0 || milestoneCount.value > 0)
const photoCount = computed(() => store.photos.length)

function openBabyModal() {
  emit('openBaby')
}
</script>

<style scoped>
.header {
  padding: 0 0 32rpx;
  background: linear-gradient(160deg, #fce7f3 0%, #fbcfe8 40%, #f5d0fe 100%);
  border-radius: 0 0 48rpx 48rpx;
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding: 0 32rpx 32rpx;
}

.baby-card {
  display: flex;
  align-items: center;
  gap: 28rpx;
}

.baby-avatar {
  width: 128rpx;
  height: 128rpx;
  background: linear-gradient(135deg, #ffffff 0%, #fdf2f8 100%);
  border-radius: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 16rpx rgba(236, 72, 153, 0.15);
  flex-shrink: 0;
}

.avatar-icon {
  font-size: 64rpx;
  line-height: 1;
}

.baby-info {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.baby-title {
  display: flex;
  align-items: center;
  gap: 12rpx;
  white-space: nowrap;
}

.baby-name {
  font-size: 44rpx;
  font-weight: 700;
  color: #831843;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta-tag {
  padding: 4rpx 16rpx;
  border-radius: 24rpx;
  font-weight: 500;
  font-size: 22rpx;
  flex-shrink: 0;
}

.meta-tag.gender {
  background: rgba(236, 72, 153, 0.12);
  color: #be185d;
}

.meta-age {
  font-size: 26rpx;
  color: #9f1239;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.baby-birthday {
  font-size: 22rpx;
  color: #be185d;
  opacity: 0.7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.quick-stats {
  display: inline-flex;
  align-items: center;
  align-self: center;
  gap: 16rpx;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8rpx);
  padding: 16rpx 32rpx;
  border-radius: 32rpx;
  border: 2rpx solid rgba(255, 255, 255, 0.5);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
  flex: 1;
  min-width: 72rpx;
}

.stat-value {
  font-size: 30rpx;
  font-weight: 700;
  color: #db2777;
  line-height: 1;
}

.stat-label {
  font-size: 18rpx;
  color: #9f1239;
  opacity: 0.7;
  font-weight: 500;
}

.stat-divider {
  width: 2rpx;
  height: 40rpx;
  background: linear-gradient(180deg, transparent, rgba(236, 72, 153, 0.3), transparent);
  flex-shrink: 0;
}
</style>
