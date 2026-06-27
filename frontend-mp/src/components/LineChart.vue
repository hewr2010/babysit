<template>
  <view class="chart-wrapper">
    <canvas
      canvas-id="growth-chart"
      id="growth-chart"
      class="chart-canvas"
      :style="{ width: canvasWidth + 'px', height: canvasHeight + 'px' }"
    />
  </view>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, getCurrentInstance } from 'vue'

const props = defineProps({
  dates: {
    type: Array,
    default: () => []
  },
  heightData: {
    type: Array,
    default: () => []
  },
  weightData: {
    type: Array,
    default: () => []
  }
})

const instance = getCurrentInstance()
const canvasWidth = ref(300)
const canvasHeight = ref(220)
const rpxRatio = ref(0.5)

const hasHeight = computed(() => props.heightData.some(v => v != null))
const hasWeight = computed(() => props.weightData.some(v => v != null))

onMounted(() => {
  initCanvas()
})

watch(() => [props.dates, props.heightData, props.weightData], () => {
  nextTick(() => draw())
}, { deep: true })

function initCanvas() {
  try {
    const sys = uni.getSystemInfoSync()
    rpxRatio.value = sys.windowWidth / 750
    // 容器宽度 = 屏幕宽 - 两侧 padding（约 80rpx）
    canvasWidth.value = Math.max(sys.windowWidth - 80 * rpxRatio.value, 200)
    canvasHeight.value = 440 * rpxRatio.value
  } catch (e) {
    rpxRatio.value = 0.5
    canvasWidth.value = 375
    canvasHeight.value = 220
  }
  nextTick(() => draw())
}

function px(rpx) {
  return rpx * rpxRatio.value
}

function getContext() {
  // #ifdef MP-WEIXIN
  if (instance && instance.proxy) {
    return uni.createCanvasContext('growth-chart', instance.proxy)
  }
  // #endif
  return uni.createCanvasContext('growth-chart')
}

function draw() {
  if (!props.dates.length) return

  const ctx = getContext()
  if (!ctx) {
    console.error('[LineChart] failed to get canvas context')
    return
  }

  const W = canvasWidth.value
  const H = canvasHeight.value
  const padding = { top: px(30), right: px(80), bottom: px(50), left: px(50) }
  const chartW = W - padding.left - padding.right
  const chartH = H - padding.top - padding.bottom

  // 清空
  ctx.clearRect(0, 0, W, H)

  // 背景
  ctx.fillStyle = '#faf5f7'
  ctx.fillRect(0, 0, W, H)

  // 计算范围
  const heightMinMax = getMinMax(props.heightData)
  const weightMinMax = getMinMax(props.weightData)

  // 绘制网格和 Y 轴标签
  ctx.lineWidth = 1
  ctx.font = `${px(18)}px sans-serif`

  // 左轴：身高
  if (hasHeight.value) {
    drawYAxis(ctx, padding, chartW, chartH, heightMinMax, '#ec4899', true)
  }

  // 右轴：体重
  if (hasWeight.value) {
    drawYAxis(ctx, padding, chartW, chartH, weightMinMax, '#22c55e', false)
  }

  // X 轴标签
  const xCount = props.dates.length
  ctx.fillStyle = '#9ca3af'
  const maxLabels = 5
  const xStep = Math.max(1, Math.ceil((xCount - 1) / (maxLabels - 1)))
  props.dates.forEach((date, i) => {
    if (i % xStep !== 0 && i !== xCount - 1) return
    const x = padding.left + (chartW / (xCount - 1 || 1)) * i
    const label = date.slice(5) // MM-DD
    if (i === 0) ctx.textAlign = 'left'
    else if (i === xCount - 1) ctx.textAlign = 'right'
    else ctx.textAlign = 'center'
    ctx.fillText(label, x, H - padding.bottom + px(24))
  })

  // 绘制折线
  if (hasHeight.value) {
    drawLine(ctx, padding, chartW, chartH, props.heightData, heightMinMax, '#ec4899')
  }
  if (hasWeight.value) {
    drawLine(ctx, padding, chartW, chartH, props.weightData, weightMinMax, '#22c55e')
  }

  ctx.draw()
}

function getMinMax(data) {
  const values = data.filter(v => v != null)
  if (!values.length) return { min: 0, max: 1 }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const pad = (max - min) * 0.1 || 1
  return { min: Math.max(0, min - pad), max: max + pad }
}

function drawYAxis(ctx, padding, chartW, chartH, minMax, color, isLeft) {
  const steps = 5
  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.textAlign = isLeft ? 'right' : 'left'

  for (let i = 0; i <= steps; i++) {
    const ratio = i / steps
    const value = minMax.min + (minMax.max - minMax.min) * ratio
    const y = padding.top + chartH - chartH * ratio

    // 刻度线
    ctx.beginPath()
    ctx.moveTo(isLeft ? padding.left : padding.left + chartW, y)
    ctx.lineTo(isLeft ? padding.left - px(6) : padding.left + chartW + px(6), y)
    ctx.stroke()

    // 标签
    const x = isLeft ? padding.left - px(10) : padding.left + chartW + px(10)
    ctx.fillText(formatValue(value), x, y + px(6))
  }

  // 轴线
  ctx.beginPath()
  ctx.moveTo(isLeft ? padding.left : padding.left + chartW, padding.top)
  ctx.lineTo(isLeft ? padding.left : padding.left + chartW, padding.top + chartH)
  ctx.stroke()
}

function drawLine(ctx, padding, chartW, chartH, data, minMax, color) {
  const xCount = data.length
  const points = []

  // 先收集有效点坐标
  data.forEach((value, i) => {
    if (value == null) return
    const x = padding.left + (chartW / (xCount - 1 || 1)) * i
    const ratio = (value - minMax.min) / (minMax.max - minMax.min || 1)
    const y = padding.top + chartH - chartH * ratio
    points.push({ x, y })
  })

  if (points.length < 1) return

  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.lineWidth = 2
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'

  // 绘制折线
  ctx.beginPath()
  points.forEach((p, i) => {
    if (i === 0) ctx.moveTo(p.x, p.y)
    else ctx.lineTo(p.x, p.y)
  })
  ctx.stroke()

  // 绘制数据点
  points.forEach(p => {
    ctx.beginPath()
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2)
    ctx.fill()
  })
}

function formatValue(v) {
  return Number(v).toFixed(v % 1 === 0 ? 0 : 1)
}
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
  height: 440rpx;
  background: #faf5f7;
  border-radius: 24rpx;
  overflow: hidden;
}

.chart-canvas {
  display: block;
}
</style>
