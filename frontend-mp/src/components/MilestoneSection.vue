<template>
  <view class="card milestone-section">
    <view class="section-heading">
      <text class="section-title">重要时刻</text>
      <text class="text-button manage-milestones" @click="goManage">管理</text>
    </view>
    <view v-if="!store.monthlyMilestones.length" class="empty-state">
      <text>本月还没有重要时刻</text>
      <view class="text-button empty-manage" @click="goManage">从相册标记</view>
    </view>
    <scroll-view v-else scroll-x class="milestone-scroll" :show-scrollbar="false">
      <view class="milestone-list">
        <view v-for="item in store.monthlyMilestones" :key="item.id" class="milestone-card" @click="emit('open', item)">
          <image class="milestone-image" :src="thumbUrl(item.media_filename)" mode="aspectFill" lazy-load />
          <view class="milestone-copy">
            <text class="milestone-date">{{ shortDate(item.date) }}</text>
            <text class="milestone-title">{{ item.title }}</text>
            <text v-if="item.description" class="milestone-description">{{ item.description }}</text>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { thumbUrl } from '@/services/media'
import { shortDate } from '@/utils/date'

const emit = defineEmits(['open'])
const store = useAppStore()

function goManage() {
  uni.navigateTo({ url: '/pages/milestones/manage' })
}
</script>

<style scoped>
.milestone-scroll {
  width: 100%;
}

.milestone-list {
  display: inline-flex;
  gap: 20rpx;
  padding-right: 32rpx;
}

.milestone-card {
  overflow: hidden;
  width: 248rpx;
  border-radius: 20rpx;
  background: #faf5f7;
}

.milestone-image {
  width: 248rpx;
  height: 220rpx;
}

.milestone-copy {
  display: flex;
  flex-direction: column;
  padding: 18rpx;
}

.milestone-date {
  color: #ec4899;
  font-size: 22rpx;
}

.milestone-title {
  overflow: hidden;
  margin-top: 6rpx;
  font-size: 27rpx;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.milestone-description {
  overflow: hidden;
  margin-top: 6rpx;
  color: #9ca3af;
  font-size: 22rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-manage {
  margin-top: 12rpx;
}
</style>
