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

export function normalizeRedirect(value = '') {
  let target = value
  if (/^%2f/i.test(target)) {
    try {
      target = decodeURIComponent(target)
    } catch (error) {
      return ''
    }
  }
  const path = target.split('?')[0]
  const allowed = ['/pages/viewer/viewer', '/pages/index/index', '/pages/milestones/manage']
  return allowed.includes(path) ? target : ''
}

export function redirectToLogin() {
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  if (!current || current.route === 'pages/auth/auth') return
  const query = Object.entries(current.options || {})
    .map(([key, value]) => {
      let decoded = value
      try {
        decoded = decodeURIComponent(value)
      } catch (error) {}
      return `${key}=${encodeURIComponent(decoded)}`
    })
    .join('&')
  const target = `/${current.route}${query ? `?${query}` : ''}`
  uni.reLaunch({ url: `/pages/auth/auth?redirect=${encodeURIComponent(target)}` })
}

export function requireAuth() {
  if (isVerified()) return true
  redirectToLogin()
  return false
}
