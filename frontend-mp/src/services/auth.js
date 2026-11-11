import { AUTH_KEY } from '@/config'

const CORRECT_NAME = '何与青'
let verified = false

export function isVerified() {
  return verified || uni.getStorageSync(AUTH_KEY) === 'true'
}

export function verifyName(name) {
  verified = name === CORRECT_NAME
  if (verified) uni.setStorageSync(AUTH_KEY, 'true')
  return verified
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
  if (verified) return true
  redirectToLogin()
  return false
}
