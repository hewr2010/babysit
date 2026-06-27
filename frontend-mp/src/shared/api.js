/**
 * API 配置
 * H5 使用相对路径 /api，小程序需要设置为完整域名 https://qqing.top/api
 */

export let API_BASE = '/api'

export function setApiBase(base) {
  API_BASE = base
}
