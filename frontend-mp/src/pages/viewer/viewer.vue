<template>
  <view class="viewer-page">
    <view class="viewer-header" :style="{ paddingTop: `${statusBarHeight}px` }">
      <view class="viewer-back" @click="goBack">‹ 返回</view>
      <text>{{ store.media.length ? `${currentIndex + 1} / ${store.media.length}` : '媒体预览' }}</text>
      <view v-if="current" class="viewer-mark" @click="editorVisible = true">标记</view>
      <view v-else class="viewer-mark" />
    </view>
    <swiper v-if="current" class="viewer-swiper" :current="currentIndex" @change="changeMedia">
      <swiper-item v-for="(item, index) in store.media" :key="item.name" class="viewer-item">
        <image v-if="item.type !== 'video'" class="viewer-media" :src="previewUrl(item.name)" mode="aspectFit" />
        <video
          v-else-if="index === currentIndex"
          :id="`media-video-${index}`"
          class="viewer-media viewer-video"
          :src="videoUrl(item)"
          :poster="thumbUrl(item.name)"
          object-fit="contain"
          controls
          autoplay
          @error="videoError = '视频加载失败，请稍后重试'"
        />
      </swiper-item>
    </swiper>
    <view v-else class="viewer-empty">没有可预览的媒体</view>
    <view v-if="current" class="viewer-footer">
      <view class="viewer-meta">
        <text class="viewer-name">{{ current.name }}</text>
        <text class="viewer-date">{{ [current.date, current.time].filter(Boolean).join(' ') }}</text>
        <text v-if="videoError && current.type === 'video'" class="viewer-error">{{ videoError }}</text>
      </view>
      <button class="primary-button save-media" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存到相册' }}</button>
    </view>
    <MilestoneEditor :visible="editorVisible" :media="current" @close="editorVisible = false" />
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import MilestoneEditor from '@/components/MilestoneEditor.vue'
import { previewUrl, saveToAlbum, thumbUrl, videoUrl } from '@/services/media'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const currentIndex = ref(0)
const statusBarHeight = ref(20)
const saving = ref(false)
const editorVisible = ref(false)
const videoError = ref('')
const current = computed(() => store.media[currentIndex.value])

onLoad(options => {
  const index = Number.parseInt(options.index || '0', 10)
  currentIndex.value = Number.isInteger(index) && index >= 0 && index < store.media.length ? index : 0
  statusBarHeight.value = uni.getSystemInfoSync().statusBarHeight || 20
})

onUnload(stopCurrentVideo)

function stopCurrentVideo() {
  if (current.value?.type !== 'video') return
  uni.createVideoContext(`media-video-${currentIndex.value}`).stop()
}

function changeMedia(event) {
  stopCurrentVideo()
  currentIndex.value = event.detail.current
  videoError.value = ''
}

function goBack() {
  uni.navigateBack()
}

async function save() {
  if (!current.value || saving.value) return
  saving.value = true
  try {
    await saveToAlbum(current.value)
    uni.showToast({ title: '已保存到相册', icon: 'success' })
  } catch (error) {
    uni.showModal({ title: '无法保存', content: error.message, showCancel: false })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.viewer-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #111716;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 24rpx;
  padding-bottom: 16rpx;
  padding-left: 24rpx;
  color: #ffffff;
  font-size: 27rpx;
}

.viewer-back,
.viewer-mark {
  width: 120rpx;
  padding: 16rpx 0;
}

.viewer-mark {
  color: #f9a8d4;
  text-align: right;
}

.viewer-swiper,
.viewer-item {
  flex: 1;
  min-height: 0;
}

.viewer-media {
  width: 100%;
  height: 100%;
}

.viewer-empty {
  flex: 1;
  padding-top: 40vh;
  color: #ffffff;
  text-align: center;
}

.viewer-footer {
  padding: 24rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  background: #202827;
}

.viewer-meta {
  display: flex;
  flex-direction: column;
  margin-bottom: 20rpx;
}

.viewer-name {
  overflow: hidden;
  color: #ffffff;
  font-size: 24rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.viewer-date {
  margin-top: 6rpx;
  color: #a7b1af;
  font-size: 22rpx;
}

.viewer-error {
  margin-top: 6rpx;
  color: #f2aaaa;
  font-size: 22rpx;
}
</style>
