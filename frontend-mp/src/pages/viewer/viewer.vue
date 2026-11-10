<template>
  <view class="viewer-page" :style="viewerStyle" @touchstart="onTouchStart" @touchmove="onTouchMove" @touchend="onTouchEnd" @touchcancel="resetGesture">
    <view class="viewer-header" :style="{ paddingTop: `${statusBarHeight}px`, paddingRight: `${headerRightPadding}px` }">
      <view class="viewer-back" @click="goBack">‹ 返回</view>
      <text>{{ store.media.length ? `${currentIndex + 1} / ${store.media.length}` : '媒体预览' }}</text>
      <view class="viewer-actions">
        <button v-if="current" class="viewer-share" open-type="share">转发</button>
        <view v-if="current" class="viewer-mark" @click="editorVisible = true">标记</view>
      </view>
    </view>
    <swiper v-if="current" class="viewer-swiper" :current="currentIndex" :disable-touch="interactionLocked" @change="changeMedia">
      <swiper-item v-for="(item, index) in store.media" :key="item.name" class="viewer-item">
        <movable-area :key="`${item.name}-${zoomResetKey}`" class="viewer-media zoom-area" scale-area>
          <movable-view
            class="zoom-view"
            :direction="interactionLocked ? 'all' : 'none'"
            scale
            :scale-value="1"
            :scale-min="1"
            :scale-max="4"
            @scale="onScale"
          >
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
              loop
              @error="videoError = '视频加载失败，请稍后重试'"
            />
          </movable-view>
        </movable-area>
      </swiper-item>
    </swiper>
    <view v-else class="viewer-empty">{{ loadError || (loading ? '正在加载分享内容…' : '没有可预览的媒体') }}</view>
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
import { onLoad, onShareAppMessage, onUnload } from '@dcloudio/uni-app'
import MilestoneEditor from '@/components/MilestoneEditor.vue'
import { AUTH_KEY } from '@/config'
import { previewUrl, saveToAlbum, thumbUrl, videoUrl } from '@/services/media'
import { useAppStore } from '@/stores/app'
import { mediaSharePath } from '@/utils/share'

const store = useAppStore()
const currentIndex = ref(0)
const statusBarHeight = ref(20)
const headerRightPadding = ref(24)
const zoomResetKey = ref(0)
const interactionLocked = ref(false)
const viewerStyle = ref({})
const saving = ref(false)
const editorVisible = ref(false)
const videoError = ref('')
const loading = ref(false)
const loadError = ref('')
const current = computed(() => store.media[currentIndex.value])
let zoomScale = 1
let gestureStart = null
let gestureAxis = ''
let multiTouch = false
let dismissing = false
let viewportHeight = 844

onLoad(async options => {
  const system = uni.getSystemInfoSync()
  statusBarHeight.value = system.statusBarHeight || 20
  viewportHeight = system.windowHeight || 844
  try {
    const menuButton = uni.getMenuButtonBoundingClientRect()
    if (menuButton?.left) {
      headerRightPadding.value = Math.ceil(system.windowWidth - menuButton.left + 12)
    }
  } catch (error) {}
  if (uni.getStorageSync(AUTH_KEY) !== 'true') {
    const query = Object.entries(options).map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join('&')
    const target = `/pages/viewer/viewer${query ? `?${query}` : ''}`
    uni.reLaunch({ url: `/pages/auth/auth?redirect=${encodeURIComponent(target)}` })
    return
  }

  if (options.media) {
    await openSharedMedia(options)
    return
  }
  const index = Number.parseInt(options.index || '0', 10)
  currentIndex.value = Number.isInteger(index) && index >= 0 && index < store.media.length ? index : 0
})

onShareAppMessage(() => {
  if (!current.value) return { title: '宝宝成长日志', path: '/pages/index/index' }
  return {
    title: `${store.baby?.name || '宝宝'}的${current.value.type === 'video' ? '新视频' : '新照片'}`,
    imageUrl: current.value.type === 'video' ? thumbUrl(current.value.name) : previewUrl(current.value.name),
    path: mediaSharePath(current.value)
  }
})

async function openSharedMedia(options) {
  loading.value = true
  loadError.value = ''
  try {
    let index = store.media.findIndex(item => item.name === options.media)
    const year = Number(options.year)
    const month = Number(options.month)
    if (index < 0 && Number.isInteger(year) && Number.isInteger(month) && month >= 1 && month <= 12) {
      store.year = year
      store.month = month
      await store.loadAlbum()
      index = store.media.findIndex(item => item.name === options.media)
    }
    if (index < 0) {
      loadError.value = '分享的内容不存在或尚未同步'
      return
    }
    currentIndex.value = index
  } catch (error) {
    loadError.value = error.message || '分享内容加载失败'
  } finally {
    loading.value = false
  }
}

onUnload(stopCurrentVideo)

function stopCurrentVideo() {
  if (current.value?.type !== 'video') return
  uni.createVideoContext(`media-video-${currentIndex.value}`).stop()
}

function changeMedia(event) {
  const index = event.detail.current
  if (index === currentIndex.value) return
  stopCurrentVideo()
  currentIndex.value = index
  videoError.value = ''
  zoomScale = 1
  zoomResetKey.value += 1
  resetGesture()
}

function onScale(event) {
  zoomScale = event.detail.scale
  interactionLocked.value = multiTouch || zoomScale > 1.05
}

function onTouchStart(event) {
  if (dismissing) return
  if (event.touches?.length > 1) {
    multiTouch = true
    interactionLocked.value = true
    gestureStart = null
    return
  }
  multiTouch = false
  if (event.touches?.length !== 1 || zoomScale > 1.05) {
    resetGesture()
    return
  }
  interactionLocked.value = false
  gestureAxis = ''
  gestureStart = { x: event.touches[0].clientX, y: event.touches[0].clientY }
}

function onTouchMove(event) {
  if (!gestureStart || multiTouch || dismissing || event.touches?.length !== 1) return
  const deltaX = event.touches[0].clientX - gestureStart.x
  const deltaY = event.touches[0].clientY - gestureStart.y
  if (!gestureAxis && Math.max(Math.abs(deltaX), Math.abs(deltaY)) > 8) {
    gestureAxis = Math.abs(deltaY) > Math.abs(deltaX) * 1.1 ? 'vertical' : 'horizontal'
  }
  if (gestureAxis !== 'vertical' || deltaY <= 0) return
  const offsetY = deltaY * 0.65
  const scale = Math.max(0.85, 1 - deltaY / 2000)
  viewerStyle.value = {
    transform: `translateY(${offsetY}px) scale(${scale})`,
    opacity: Math.max(0.35, 1 - deltaY / viewportHeight),
    transition: 'none'
  }
}

function onTouchEnd(event) {
  if (multiTouch) {
    if (!event.touches?.length) interactionLocked.value = zoomScale > 1.05
    resetGesture()
    return
  }
  if (!gestureStart || !event.changedTouches?.length) return
  const deltaY = event.changedTouches[0].clientY - gestureStart.y
  if (gestureAxis === 'vertical' && deltaY > 100) dismiss()
  else resetGesture()
}

function resetGesture() {
  gestureStart = null
  gestureAxis = ''
  multiTouch = false
  interactionLocked.value = zoomScale > 1.05
  if (dismissing) return
  viewerStyle.value = {
    transform: 'translateY(0) scale(1)',
    opacity: 1,
    transition: 'transform 180ms ease-out, opacity 180ms ease-out'
  }
}

function dismiss() {
  if (dismissing) return
  dismissing = true
  gestureStart = null
  viewerStyle.value = {
    transform: `translateY(${viewportHeight}px) scale(0.9)`,
    opacity: 0,
    transition: 'transform 200ms ease-in, opacity 200ms ease-in'
  }
  setTimeout(goBack, 200)
}

function goBack() {
  if (getCurrentPages().length > 1) uni.navigateBack()
  else uni.reLaunch({ url: '/pages/index/index' })
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
  transform-origin: center center;
  will-change: transform, opacity;
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

.viewer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 120rpx;
}

.viewer-share {
  padding: 0 16rpx;
  background: transparent;
  color: #f9a8d4;
  font-size: 26rpx;
  line-height: 56rpx;
}

.viewer-media {
  width: 100%;
  height: 100%;
}

.viewer-swiper,
.viewer-item {
  flex: 1;
  min-height: 0;
}

.zoom-area {
  flex: 1;
  min-height: 0;
}

.zoom-area,
.zoom-view {
  width: 100%;
  height: 100%;
}

.zoom-view {
  display: flex;
  align-items: center;
  justify-content: center;
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
