import { isProxy, isRef, toRaw, unref } from 'vue'

import { getCurrentUserContext } from '../config/permissions'

export const DEFAULT_REQUEST_CACHE_TTL = 45 * 1000

const requestCache = new Map()

/** 运营商订单类接口（实时/历史/异常等）在变更后递增，用于丢弃已失效的在途响应，避免旧数据写回缓存与界面 */
let operatorOrderDataEpoch = 0

export const getOperatorOrderDataEpoch = () => operatorOrderDataEpoch

/** 仅用于订单列表（实时/历史/异常）防陈旧写回；运营工作台快照勿用 epoch 丢弃在途响应 */
export const bumpOperatorOrderDataEpoch = () => {
  operatorOrderDataEpoch += 1
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('echarge:operator-orders-mutated'))
  }
}

const isPlainObject = (value) => Object.prototype.toString.call(value) === '[object Object]'

/** 去掉 Vue 响应式包装与不可序列化字段，降低 structuredClone / JSON 失败概率 */
const normalizeForCache = (value) => {
  if (isRef(value)) return normalizeForCache(unref(value))
  if (isProxy(value)) return normalizeForCache(toRaw(value))

  if (value == null) return value
  const t = typeof value
  if (t !== 'object') return value
  if (value instanceof Date) return new Date(value.getTime())

  if (Array.isArray(value)) {
    return value.map(normalizeForCache)
  }

  if (t === 'object') {
    const plain = {}
    Object.entries(value).forEach(([key, item]) => {
      if (typeof item !== 'function' && typeof item !== 'symbol') {
        plain[key] = normalizeForCache(item)
      }
    })
    return plain
  }

  return value
}

const deepClone = (value) => {
  const plain = normalizeForCache(value)

  try {
    if (typeof structuredClone === 'function') {
      return structuredClone(plain)
    }
  } catch (error) {
    console.warn('[requestCache] structuredClone failed, fallback to JSON clone:', error)
  }

  try {
    return JSON.parse(JSON.stringify(plain))
  } catch (error) {
    console.warn('[requestCache] JSON clone failed, returning normalized plain object:', error)
    return plain
  }
}

const normalizeValue = (value) => {
  if (Array.isArray(value)) {
    return value.map(normalizeValue)
  }

  if (isPlainObject(value)) {
    return Object.keys(value)
      .sort()
      .reduce((result, key) => {
        const current = value[key]
        if (current === undefined || current === null || current === '') {
          return result
        }
        result[key] = normalizeValue(current)
        return result
      }, {})
  }

  return value
}

const serialize = (value) => JSON.stringify(normalizeValue(value))

export const buildRequestCacheKey = (url, params = {}, extra = {}) => {
  const { role, operatorId } = getCurrentUserContext()
  return serialize({
    url,
    params,
    role: extra.role || role,
    operatorId: extra.operatorId || operatorId,
    scope: extra.scope || '',
  })
}

export const getRequestCache = (key, { ttl = DEFAULT_REQUEST_CACHE_TTL, allowStale = true } = {}) => {
  const entry = requestCache.get(key)
  if (!entry) return null

  const age = Date.now() - entry.updatedAt
  const isFresh = age <= ttl

  if (!isFresh && !allowStale) {
    requestCache.delete(key)
    return null
  }

  return {
    value: deepClone(entry.value),
    updatedAt: entry.updatedAt,
    age,
    isFresh,
  }
}

export const setRequestCache = (key, value) => {
  requestCache.set(key, {
    value: deepClone(value),
    updatedAt: Date.now(),
  })
}

export const clearRequestCache = (matcher) => {
  if (!matcher) {
    requestCache.clear()
    return
  }

  for (const key of requestCache.keys()) {
    const matched = typeof matcher === 'function' ? matcher(key) : key.includes(String(matcher))
    if (matched) {
      requestCache.delete(key)
    }
  }
}

export const formatCacheUpdatedAt = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export const formatCacheLabel = (timestamp, prefix = '最近更新于') => {
  const formatted = formatCacheUpdatedAt(timestamp)
  return formatted ? `${prefix} ${formatted}` : ''
}

export const shouldRefreshRequestCache = (key, ttl = DEFAULT_REQUEST_CACHE_TTL) => {
  const cached = getRequestCache(key, { ttl, allowStale: true })
  return !cached || !cached.isFresh
}

const tryParseCacheKey = (key) => {
  try {
    return JSON.parse(key)
  } catch {
    return null
  }
}

/** 运营商电站分页列表 GET /operator/stations */
export const clearOperatorMainStationsCache = () => {
  clearRequestCache((key) => {
    const o = tryParseCacheKey(key)
    return Boolean(o && o.url === '/operator/stations')
  })
}

/** 电桩管理等下拉用 GET /operator/stations/options */
export const clearOperatorStationsOptionsCache = () => {
  clearRequestCache((key) => {
    const o = tryParseCacheKey(key)
    return Boolean(o && o.url === '/operator/stations/options')
  })
}

/** 创建订单等用 GET /operator/orders/start-options（任意 query 组合） */
export const clearOperatorOrderStartOptionsCaches = () => {
  clearRequestCache((key) => {
    const o = tryParseCacheKey(key)
    return Boolean(o && o.url === '/operator/orders/start-options')
  })
}

/** 指定电站电桩列表 GET /operator/stations/:id/chargers */
export const clearStationChargersCachesForStation = (stationId) => {
  const path = `/operator/stations/${String(stationId)}/chargers`
  clearRequestCache((key) => {
    const o = tryParseCacheKey(key)
    return Boolean(o && o.url === path)
  })
}

/** 实时 / 历史 / 异常订单列表 GET（不含 start-options） */
export const clearOperatorOrderListCaches = () => {
  clearRequestCache((key) => {
    const o = tryParseCacheKey(key)
    if (!o || typeof o.url !== 'string') return false
    return (
      o.url === '/operator/orders/realtime' ||
      o.url === '/operator/orders/history' ||
      o.url === '/operator/orders/abnormal'
    )
  })
}

/** 仅当前页实时订单轮询用 GET /operator/orders/realtime */
export const clearOperatorRealtimeListCache = () => {
  clearRequestCache((key) => {
    const o = tryParseCacheKey(key)
    return Boolean(o && o.url === '/operator/orders/realtime')
  })
}
