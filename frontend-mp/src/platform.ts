import { setApiBase } from './shared/api'
import { setRequestImpl } from './shared/request'
import { setStorageImpl } from './shared/storage'
import { setRouterImpl } from './shared/router'

const API_HOST = import.meta.env.VITE_API_HOST || 'https://qqing.top'

export function initPlatform() {
  console.log('[platform] initPlatform start, API_HOST:', API_HOST)
  setApiBase(`${API_HOST}/api`)

  setRequestImpl((url: string, options: any = {}) => {
    return new Promise((resolve, reject) => {
      const headers = options.headers || {}
      if (options.data && typeof options.data === 'object' && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json'
      }
      console.log('[request]', options.method || 'GET', url)
      uni.request({
        url,
        method: options.method || 'GET',
        data: options.data,
        header: headers,
        timeout: 10000,
        success: (res: any) => {
          console.log('[response]', res.statusCode, url)
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data)
          } else {
            reject(new Error(`HTTP ${res.statusCode}`))
          }
        },
        fail: (err: any) => {
          console.error('[request fail]', url, err)
          reject(err)
        }
      })
    })
  })

  setStorageImpl({
    get(key: string) {
      try {
        return uni.getStorageSync(key)
      } catch (e) {
        return null
      }
    },
    set(key: string, value: any) {
      try {
        uni.setStorageSync(key, value)
      } catch (e) {
        // ignore
      }
    },
    remove(key: string) {
      try {
        uni.removeStorageSync(key)
      } catch (e) {
        // ignore
      }
    }
  })

  setRouterImpl({
    getPath() {
      const pages = getCurrentPages()
      const current = pages[pages.length - 1]
      return current ? `/${current.route}` : '/'
    },
    getQuery() {
      const pages = getCurrentPages()
      const current = pages[pages.length - 1]
      const query = current ? current.options || {} : {}
      const pairs = Object.entries(query)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      return pairs.length > 0 ? `?${pairs.join('&')}` : ''
    },
    replaceURL(_path: string, _query: string = '') {
      // 小程序没有浏览器地址栏，无需同步 URL
    },
    navigateTo(path: string) {
      uni.navigateTo({ url: path })
    },
    navigateBack() {
      uni.navigateBack()
    }
  })
}

export const MEDIA_HOST = API_HOST
