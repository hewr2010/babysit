<template>
  <view class="slide-wrapper">
    <image
      :src="thumbUrl"
      mode="aspectFill"
      class="media-thumb"
      @error="onThumbError"
    />
    <image
      :src="previewUrl"
      mode="aspectFill"
      class="media-image"
      @load="onImageLoad"
      @error="onImageError"
    />
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { MEDIA_HOST } from '@/platform'

const props = defineProps({
  filename: {
    type: String,
    required: true
  }
})

const thumbUrl = computed(() => `${MEDIA_HOST}/thumb/${encodeURIComponent(props.filename)}`)
const previewUrl = computed(() => `${MEDIA_HOST}/preview/${encodeURIComponent(props.filename)}`)

function onImageLoad() {
  // 图片加载完成
}

function onImageError() {
  console.error(`[viewer] preview image load error: ${props.filename}`)
}

function onThumbError() {
  console.error(`[viewer] thumb image load error: ${props.filename}`)
}
</script>

<style scoped>
.slide-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  background: #1a1a1a;
  overflow: hidden;
}

.media-thumb,
.media-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.media-thumb {
  filter: blur(20rpx) brightness(0.6);
  transform: scale(1.1);
  z-index: 1;
}

.media-image {
  z-index: 2;
}
</style>
