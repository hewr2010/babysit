import { API_BASE } from '@/config'

export function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: options.data ? { 'Content-Type': 'application/json' } : {},
      timeout: 15000,
      success: response => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data)
          return
        }
        const message = response.data?.error || response.data?.message || `请求失败 (${response.statusCode})`
        reject(new Error(message))
      },
      fail: error => reject(new Error(error.errMsg || '网络连接失败'))
    })
  })
}
