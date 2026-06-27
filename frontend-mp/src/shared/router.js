/**
 * 平台无关的路由/URL 封装
 * H5 默认使用 window.location/window.history，小程序可通过 setRouterImpl 注入
 */

const defaultRouter = {
  getPath() {
    return window.location.pathname
  },
  getQuery() {
    return window.location.search
  },
  replaceURL(path, query = '') {
    window.history.replaceState({}, '', path + query)
  },
  navigateTo(path) {
    window.location.href = path
  },
  navigateBack() {
    window.history.back()
  }
}

let routerImpl = defaultRouter

export function setRouterImpl(impl) {
  routerImpl = { ...defaultRouter, ...impl }
}

export function resetRouterImpl() {
  routerImpl = defaultRouter
}

export const router = {
  getPath() {
    return routerImpl.getPath()
  },
  getQuery() {
    return routerImpl.getQuery()
  },
  replaceURL(path, query = '') {
    routerImpl.replaceURL(path, query)
  },
  navigateTo(path) {
    routerImpl.navigateTo(path)
  },
  navigateBack() {
    routerImpl.navigateBack()
  }
}
