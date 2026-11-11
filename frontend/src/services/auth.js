const AUTH_KEY = 'baby_auth_verified'

export function getAccessToken() {
  const raw = localStorage.getItem(AUTH_KEY)
  if (!raw) return ''
  try {
    const session = JSON.parse(raw)
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
  localStorage.setItem(AUTH_KEY, JSON.stringify({
    token,
    expiresAt: Date.now() + Number(expiresIn) * 1000
  }))
}

export function clearAccessToken() {
  localStorage.removeItem(AUTH_KEY)
}

export function authorizedUrl(url) {
  const token = getAccessToken()
  if (!token) return url
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}access_token=${encodeURIComponent(token)}`
}

export async function login(password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password })
  })
  const result = await response.json()
  if (!response.ok) throw new Error(result.error || '验证失败，请重试')
  saveAccessToken(result.token, result.expires_in)
}

export async function authFetch(input, options = {}) {
  const token = getAccessToken()
  const headers = { ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(input, { ...options, headers })
  if (response.status === 401) {
    clearAccessToken()
    window.location.reload()
    throw new Error('登录已过期，请重新验证')
  }
  return response
}
