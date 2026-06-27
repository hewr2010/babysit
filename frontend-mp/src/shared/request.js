/**
 * 平台无关的网络请求封装
 * H5 默认使用 fetch，小程序可通过 setRequestImpl 注入 uni.request
 */

async function defaultRequest(url, options = {}) {
  const fetchOptions = {
    method: options.method || 'GET',
    headers: options.headers || {}
  }

  if (options.data && fetchOptions.method !== 'GET') {
    if (typeof options.data === 'string') {
      fetchOptions.body = options.data
    } else {
      fetchOptions.body = JSON.stringify(options.data)
      if (!fetchOptions.headers['Content-Type']) {
        fetchOptions.headers['Content-Type'] = 'application/json'
      }
    }
  }

  const res = await fetch(url, fetchOptions)

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }

  if (options.responseType === 'text') {
    return res.text()
  }

  return res.json()
}

let requestImpl = defaultRequest

export function setRequestImpl(impl) {
  requestImpl = impl
}

export function resetRequestImpl() {
  requestImpl = defaultRequest
}

export async function request(url, options = {}) {
  return requestImpl(url, options)
}
