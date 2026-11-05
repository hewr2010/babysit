<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'

onLaunch(() => {})
</script>

<style>
page {
  background: #fdf2f8;
  color: #374151;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 28rpx;
}

button::after {
  border: none;
}

button {
  margin: 0;
}

.card {
  background: #ffffff;
  border-radius: 32rpx;
  padding: 40rpx;
  box-shadow: 0 8rpx 32rpx rgba(236, 72, 153, 0.07);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28rpx;
}

.section-title {
  color: #831843;
  font-size: 30rpx;
  font-weight: 650;
}

.text-button {
  color: #db2777;
  font-size: 26rpx;
  padding: 12rpx 0 12rpx 24rpx;
}

.primary-button {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #ec4899, #f472b6);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}

.primary-button[disabled] {
  background: #f9a8d4;
  color: #ffffff;
}

.secondary-button {
  height: 80rpx;
  line-height: 80rpx;
  border: 2rpx solid #fbcfe8;
  border-radius: 20rpx;
  background: #ffffff;
  color: #db2777;
  font-size: 28rpx;
}

.empty-state {
  padding: 56rpx 24rpx;
  text-align: center;
  color: #9ca3af;
  line-height: 1.7;
}

.field {
  margin-bottom: 28rpx;
}

.field-label {
  display: block;
  margin-bottom: 12rpx;
  color: #6b7280;
  font-size: 26rpx;
}

.field-input {
  box-sizing: border-box;
  width: 100%;
  min-height: 88rpx;
  padding: 20rpx 24rpx;
  border: 2rpx solid #fce7f3;
  border-radius: 20rpx;
  background: #ffffff;
  font-size: 30rpx;
}
</style>
