import { API_BASE, AUTH_KEY } from '@/config'

export function getAccessToken() {
  const raw = uni.getStorageSync(AUTH_KEY)
  if (!raw) return ''
  try {
    const session = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!session.token || Number(session.expiresAt) <= Date.now()) {
      clearAccessToken()
      return ''
    }
    return session.token
  } catch (error) {
    clearAccessToken()
    return ''
  }
}

export function saveAccessToken(token, expiresIn) {
  uni.setStorageSync(AUTH_KEY, {
    token,
    expiresAt: Date.now() + Number(expiresIn) * 1000
  })
}

export function clearAccessToken() {
  uni.removeStorageSync(AUTH_KEY)
}

export function authorizedUrl(url) {
  const token = getAccessToken()
  if (!token) return url
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}access_token=${encodeURIComponent(token)}`
}

export function redirectToLogin() {
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  if (!current || current.route === 'pages/auth/auth') return
  const query = Object.entries(current.options || {})
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join('&')
  const target = `/${current.route}${query ? `?${query}` : ''}`
  uni.reLaunch({ url: `/pages/auth/auth?redirect=${encodeURIComponent(target)}` })
}

export function requireAuth() {
  if (getAccessToken()) return true
  redirectToLogin()
  return false
}

export async function login(password) {
  const response = await new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}/auth/login`,
      method: 'POST',
      data: { password },
      header: { 'Content-Type': 'application/json' },
      success: resolve,
      fail: error => reject(new Error(error.errMsg || '网络连接失败'))
    })
  })
  if (response.statusCode !== 200) {
    throw new Error(response.data?.error || '访问密码不正确')
  }
  saveAccessToken(response.data.token, response.data.expires_in)
}
