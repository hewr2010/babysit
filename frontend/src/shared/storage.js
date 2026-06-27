/**
 * 平台无关的本地存储封装
 * H5 默认使用 localStorage，小程序可通过 setStorageImpl 注入 uni.storage
 */

const defaultStorage = {
  get(key) {
    return localStorage.getItem(key)
  },
  set(key, value) {
    localStorage.setItem(key, value)
  },
  remove(key) {
    localStorage.removeItem(key)
  }
}

let storageImpl = defaultStorage

export function setStorageImpl(impl) {
  storageImpl = impl
}

export function resetStorageImpl() {
  storageImpl = defaultStorage
}

export const storage = {
  get(key) {
    return storageImpl.get(key)
  },
  set(key, value) {
    storageImpl.set(key, value)
  },
  remove(key) {
    storageImpl.remove(key)
  }
}
