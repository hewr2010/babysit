<template>
  <view class="chart-wrapper">
    <canvas
      canvas-id="growth-chart"
      id="growth-chart"
      class="chart-canvas"
      :style="{ width: canvasWidth + 'px', height: canvasHeight + 'px' }"
      @tap="onTap"
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
const activeIndex = ref(-1)

const hasHeight = computed(() => props.heightData.some(v => v != null))
const hasWeight = computed(() => props.weightData.some(v => v != null))

let chartGeom = null

onMounted(() => {
  initCanvas()
})

watch(() => [props.dates, props.heightData, props.weightData], () => {
  activeIndex.value = -1
  nextTick(() => draw())
}, { deep: true })

function initCanvas() {
  try {
    const sys = uni.getSystemInfoSync()
    rpxRatio.value = sys.windowWidth / 750
    // 画布比容器再小一圈，确保标签不贴边；容器在 GrowthSection 里有 40rpx 内边距
    canvasWidth.value = Math.max(sys.windowWidth - 140 * rpxRatio.value, 200)
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
  const padding = {
    top: px(50),
    right: px(120),
    bottom: px(60),
    left: px(70)
  }
  const chartW = W - padding.left - padding.right
  const chartH = H - padding.top - padding.bottom

  chartGeom = { W, H, padding, chartW, chartH }

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
  ctx.font = `${px(20)}px sans-serif`

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
    ctx.fillText(label, x, H - padding.bottom + px(30))
  })

  // 绘制折线
  if (hasHeight.value) {
    drawLine(ctx, padding, chartW, chartH, props.heightData, heightMinMax, '#ec4899')
  }
  if (hasWeight.value) {
    drawLine(ctx, padding, chartW, chartH, props.weightData, weightMinMax, '#22c55e')
  }

  // 绘制高亮提示
  if (activeIndex.value >= 0 && activeIndex.value < xCount) {
    drawTooltip(ctx, padding, chartW, chartH, activeIndex.value, heightMinMax, weightMinMax)
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
  ctx.font = `${px(20)}px sans-serif`

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
    const x = isLeft ? padding.left - px(12) : padding.left + chartW + px(12)
    ctx.fillText(formatValue(value), x, y + px(7))
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

  data.forEach((value, i) => {
    if (value == null) return
    const x = padding.left + (chartW / (xCount - 1 || 1)) * i
    const ratio = (value - minMax.min) / (minMax.max - minMax.min || 1)
    const y = padding.top + chartH - chartH * ratio
    points.push({ x, y, value })
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
    ctx.arc(p.x, p.y, px(6), 0, Math.PI * 2)
    ctx.fill()
  })
}

function drawTooltip(ctx, padding, chartW, chartH, index, heightMinMax, weightMinMax) {
  const xCount = props.dates.length
  const x = padding.left + (chartW / (xCount - 1 || 1)) * index

  // 竖线
  ctx.strokeStyle = 'rgba(107, 114, 128, 0.4)'
  ctx.lineWidth = 1
  ctx.setLineDash([px(6), px(4)])
  ctx.beginPath()
  ctx.moveTo(x, padding.top)
  ctx.lineTo(x, padding.top + chartH)
  ctx.stroke()
  ctx.setLineDash([])

  // 高亮点
  const heightValue = props.heightData[index]
  const weightValue = props.weightData[index]
  const radius = px(10)

  if (heightValue != null) {
    const ratio = (heightValue - heightMinMax.min) / (heightMinMax.max - heightMinMax.min || 1)
    const y = padding.top + chartH - chartH * ratio
    ctx.fillStyle = '#ec4899'
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
  }

  if (weightValue != null) {
    const ratio = (weightValue - weightMinMax.min) / (weightMinMax.max - weightMinMax.min || 1)
    const y = padding.top + chartH - chartH * ratio
    ctx.fillStyle = '#22c55e'
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
  }

  // 提示卡片
  const date = props.dates[index]
  const lines = []
  if (heightValue != null) lines.push({ text: `身高 ${formatValue(heightValue)} cm`, color: '#ec4899' })
  if (weightValue != null) lines.push({ text: `体重 ${formatValue(weightValue)} g`, color: '#22c55e' })
  if (!lines.length) return

  const cardPadding = px(16)
  const lineHeight = px(32)
  ctx.font = `${px(22)}px sans-serif`
  let maxWidth = 0
  lines.forEach(line => {
    const w = ctx.measureText(line.text).width
    if (w > maxWidth) maxWidth = w
  })
  const dateWidth = ctx.measureText(date).width
  if (dateWidth > maxWidth) maxWidth = dateWidth

  const cardW = maxWidth + cardPadding * 2
  const cardH = cardPadding * 2 + lineHeight * (lines.length + 1)
  let cardX = x + px(16)
  let cardY = padding.top + px(16)
  if (cardX + cardW > padding.left + chartW) {
    cardX = x - cardW - px(16)
  }

  ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
  ctx.strokeStyle = 'rgba(236, 72, 153, 0.2)'
  ctx.lineWidth = 1
  roundRect(ctx, cardX, cardY, cardW, cardH, px(12))
  ctx.fill()
  ctx.stroke()

  ctx.fillStyle = '#374151'
  ctx.textAlign = 'left'
  ctx.fillText(date, cardX + cardPadding, cardY + cardPadding + px(20))

  lines.forEach((line, i) => {
    ctx.fillStyle = line.color
    ctx.fillText(line.text, cardX + cardPadding, cardY + cardPadding + lineHeight * (i + 1) + px(20))
  })
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + r)
  ctx.lineTo(x + w, y + h - r)
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  ctx.lineTo(x + r, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
}

function onTap(e) {
  if (!chartGeom) return
  const { padding, chartW } = chartGeom
  const touchX = e.detail.x
  const xCount = props.dates.length
  const chartLeft = padding.left
  const relativeX = touchX - chartLeft
  const step = chartW / (xCount - 1 || 1)
  let index = Math.round(relativeX / step)
  index = Math.max(0, Math.min(xCount - 1, index))
  activeIndex.value = index
  draw()
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
