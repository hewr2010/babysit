<template>
  <AppSheet :visible="visible" title="标记重要时刻" @close="emit('close')">
    <image v-if="media" class="milestone-preview" :src="localImage(previewUrl(media.name))" mode="aspectFit" />
    <view v-if="existing.length" class="existing-milestones">
      <text class="field-label">这个媒体的已有时刻</text>
      <view v-for="item in existing" :key="item.id" class="existing-row">
        <view class="existing-copy">
          <text class="existing-title">{{ item.title }}</text>
          <text v-if="item.description" class="existing-description">{{ item.description }}</text>
        </view>
        <text class="delete-milestone" @click="remove(item)">删除</text>
      </view>
    </view>
    <view class="field">
      <text class="field-label">标题</text>
      <input v-model="title" class="field-input milestone-title-input" maxlength="50" placeholder="例如：第一次翻身" />
    </view>
    <view class="field">
      <text class="field-label">描述（可选）</text>
      <textarea v-model="description" class="field-input milestone-description-input" maxlength="200" placeholder="记录这一刻的细节" />
    </view>
    <button class="primary-button save-milestone" :disabled="saving || !title.trim()" @click="save">{{ saving ? '保存中…' : '保存时刻' }}</button>
  </AppSheet>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppSheet from '@/components/AppSheet.vue'
import { previewUrl } from '@/services/media'
import { localImage, preloadImages } from '@/services/localImages'
import { useAppStore } from '@/stores/app'

const props = defineProps({
  visible: Boolean,
  media: { type: Object, default: null }
})
const emit = defineEmits(['close', 'saved'])
const store = useAppStore()
const title = ref('')
const description = ref('')
const saving = ref(false)
const existing = computed(() => props.media ? store.milestones.filter(item => item.media_filename === props.media.name) : [])

watch(() => props.media, media => {
  if (media) preloadImages([previewUrl(media.name)])
}, { immediate: true })

watch(() => props.visible, visible => {
  if (visible) {
    title.value = ''
    description.value = ''
  }
})

async function save() {
  if (!props.media || !title.value.trim()) return
  saving.value = true
  try {
    await store.addMilestone({
      media_filename: props.media.name,
      title: title.value.trim(),
      description: description.value.trim() || null
    })
    title.value = ''
    description.value = ''
    emit('saved')
    uni.showToast({ title: '时刻已保存', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error.message, icon: 'none' })
  } finally {
    saving.value = false
  }
}

function remove(item) {
  uni.showModal({
    title: '删除重要时刻',
    content: `删除“${item.title}”？`,
    success: async result => {
      if (!result.confirm) return
      try {
        await store.removeMilestone(item.id)
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none' })
      }
    }
  })
}
</script>

<style scoped>
.milestone-preview {
  width: 100%;
  height: 320rpx;
  margin-bottom: 28rpx;
  border-radius: 16rpx;
  background: #f2f5f4;
}

.existing-milestones {
  margin-bottom: 28rpx;
}

.existing-row {
  display: flex;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 2rpx solid #fce7f3;
}

.existing-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.existing-title {
  font-weight: 600;
}

.existing-description {
  overflow: hidden;
  margin-top: 6rpx;
  color: #64716f;
  font-size: 24rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-milestone {
  padding-left: 24rpx;
  color: #b14d4d;
}

.milestone-description-input {
  height: 160rpx;
}
</style>
