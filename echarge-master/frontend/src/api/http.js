import axios from 'axios'
import { getCurrentUserContext } from '../config/permissions'

/** 解析 .env 中的毫秒数，避免空格/引号导致 NaN 后误用默认短超时 */
const parseTimeoutMs = (raw) => {
  if (raw === undefined || raw === null) return null
  const s = String(raw).trim().replace(/^['"]|['"]$/g, '')
  if (!s) return null
  const n = Number(s)
  return Number.isFinite(n) && n > 0 ? n : null
}

const _timeoutMs = parseTimeoutMs(import.meta.env.VITE_API_TIMEOUT_MS) ?? 300000
const _mutationTimeoutMs = parseTimeoutMs(import.meta.env.VITE_API_MUTATION_TIMEOUT_MS) ?? 20000

const LONG_TIMEOUT_HINT =
  '请求超时：若 uvicorn 正带 --reload 热更新，重启瞬间易超时，请刷新页面；稳定联调可去掉 --reload。仍慢请检查 MySQL，或在 frontend/.env.development 设置 VITE_API_TIMEOUT_MS=600000 后重启 npm run dev。'

const MUTATION_TIMEOUT_HINT =
  '请求超时：表单提交已等待较长时间仍未返回，请稍后重试或检查网络与后端服务。'

const createHttpClient = (timeoutMs, timeoutHint) => {
  const instance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
    timeout: timeoutMs,
  })

  instance.interceptors.request.use((config) => {
    const { role, operatorId } = getCurrentUserContext()
    config.headers = config.headers || {}
    config.headers['x-role'] = role
    config.headers['x-operator-id'] = operatorId
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error?.response?.status
      const data = error?.response?.data
      let backendMessage = data?.message
      if (!backendMessage && Array.isArray(data?.detail)) {
        backendMessage = data.detail
          .map((d) => (typeof d === 'string' ? d : d?.msg || JSON.stringify(d?.loc || []) + ': ' + (d?.msg || '')))
          .filter(Boolean)
          .join('；')
      } else if (!backendMessage && typeof data?.detail === 'string') {
        backendMessage = data.detail
      }
      const msgLower = String(error?.message || '').toLowerCase()
      const isAbortTimeout =
        error?.code === 'ECONNABORTED' ||
        msgLower.includes('timeout') ||
        msgLower.includes('exceeded')
      const isNetworkFail =
        error?.code === 'ERR_NETWORK' || error?.code === 'ECONNREFUSED' || msgLower.includes('network error')

      if (backendMessage) {
        error.message = backendMessage
        return Promise.reject(error)
      }

      if (isAbortTimeout) {
        error.message = timeoutHint
        return Promise.reject(error)
      }

      if (status >= 500) {
        error.message = '后端服务暂时不可用，请稍后重试'
        return Promise.reject(error)
      }

      if (!error?.response) {
        error.message = isNetworkFail
          ? '网络异常或后端未启动：请确认 uvicorn 已监听（默认与启动文档一致为 8001，勿与 C-Lodop 占用的 8000 冲突）；开发环境勿把 VITE_API_BASE_URL 指到不可达地址，可留空走 Vite 代理。'
          : '无法连接后端：请确认已启动 uvicorn，且未设置错误的 VITE_API_BASE_URL（开发环境可留空以走 Vite 代理 /api）。'
      }

      return Promise.reject(error)
    },
  )

  return instance
}

const http = createHttpClient(_timeoutMs, LONG_TIMEOUT_HINT)

/** 写操作、表单提交：较短超时，避免长时间挂起 */
export const httpMutation = createHttpClient(_mutationTimeoutMs, MUTATION_TIMEOUT_HINT)

export default http
