<template>
  <view class="growth-chart">
    <canvas id="growth-canvas" canvas-id="growth-canvas" class="chart-canvas" />
    <view class="chart-legend">{{ metric === 'height' ? '身高 cm' : '体重 g' }}</view>
  </view>
</template>

<script setup>
import { getCurrentInstance, nextTick, onMounted, watch } from 'vue'

const props = defineProps({
  records: { type: Array, default: () => [] },
  metric: { type: String, default: 'height' }
})
const instance = getCurrentInstance()
let width = 320
const height = 220

onMounted(() => {
  nextTick(resizeAndDraw)
})
watch(() => [props.records, props.metric], () => nextTick(draw), { deep: true })

function resizeAndDraw() {
  uni.createSelectorQuery().in(instance.proxy).select('.chart-canvas').boundingClientRect(rect => {
    if (rect?.width) width = rect.width
    draw()
  }).exec()
}

function draw() {
  const context = uni.createCanvasContext('growth-canvas', instance.proxy)
  context.clearRect(0, 0, width, height)
  const records = [...props.records].sort((a, b) => a.date.localeCompare(b.date))
  if (!records.length) {
    context.draw()
    return
  }

  const padding = { left: 46, right: 18, top: 24, bottom: 38 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const values = records.map(record => Number(record.value))
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  const margin = Math.max((maximum - minimum) * 0.18, maximum * 0.03, 1)
  const low = Math.max(0, minimum - margin)
  const high = maximum + margin

  context.lineWidth = 1
  context.font = '10px sans-serif'
  for (let index = 0; index <= 4; index += 1) {
    const y = padding.top + chartHeight * index / 4
    context.beginPath()
    context.setStrokeStyle('#e7eceb')
    context.moveTo(padding.left, y)
    context.lineTo(width - padding.right, y)
    context.stroke()
    context.setFillStyle('#85908f')
    context.setTextAlign('right')
    const label = high - (high - low) * index / 4
    context.fillText(String(Math.round(label * 10) / 10), padding.left - 7, y + 3)
  }

  const points = records.map((record, index) => ({
    x: records.length === 1 ? padding.left + chartWidth / 2 : padding.left + chartWidth * index / (records.length - 1),
    y: padding.top + chartHeight * (high - Number(record.value)) / (high - low)
  }))
  context.beginPath()
  context.setStrokeStyle('#ec4899')
  context.setLineWidth(2)
  points.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y))
  context.stroke()

  points.forEach(point => {
    context.beginPath()
    context.setFillStyle('#ffffff')
    context.setStrokeStyle('#ec4899')
    context.setLineWidth(2)
    context.arc(point.x, point.y, 4, 0, Math.PI * 2)
    context.fill()
    context.stroke()
  })

  context.setFillStyle('#64716f')
  context.setTextAlign('left')
  context.fillText(records[0].date.slice(5), padding.left, height - 10)
  context.setTextAlign('right')
  context.fillText(records[records.length - 1].date.slice(5), width - padding.right, height - 10)
  context.draw()
}
</script>

<style scoped>
.growth-chart {
  position: relative;
  height: 220px;
  margin-top: 24rpx;
}

.chart-canvas {
  width: 100%;
  height: 220px;
}

.chart-legend {
  position: absolute;
  top: 0;
  right: 0;
  color: #ec4899;
  font-size: 22rpx;
}
</style>
