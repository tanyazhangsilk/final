import { BASE_URL } from '../config/env'
import { getMiniAuthHeaders } from '../utils/storage'

type Primitive = string | number | boolean
type QueryValue = Primitive | null | undefined | Primitive[]
type QueryParams = Record<string, QueryValue>
type RequestMethod = 'GET' | 'POST' | 'PUT'

interface ApiResponse<T> {
  code?: number,
  data?: T,
  message?: string,
  msg?: string
}

export interface RequestOptions<TBody = unknown, TQuery extends QueryParams = QueryParams> {
  url: string,
  method?: RequestMethod,
  data?: TBody,
  query?: TQuery,
  header?: WechatMiniprogram.IAnyObject
}

export const baseUrl = BASE_URL

function isNil(value: unknown) {
  return value === undefined || value === null || value === ''
}

function appendQuery(url: string, query?: QueryParams) {
  if (!query) {
    return url
  }

  const segments = Object.keys(query).flatMap(key => {
    const value = query[key]
    if (Array.isArray(value)) {
      return value
        .filter(item => !isNil(item))
        .map(item => `${encodeURIComponent(key)}=${encodeURIComponent(String(item))}`)
    }

    if (isNil(value)) {
      return []
    }

    return [`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`]
  })

  if (!segments.length) {
    return url
  }

  return `${url}${url.includes('?') ? '&' : '?'}${segments.join('&')}`
}

function joinUrl(url: string, query?: QueryParams) {
  const fullUrl = /^https?:\/\//.test(url)
    ? url
    : `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`

  return appendQuery(fullUrl, query)
}

function getMessage(payload: unknown) {
  if (payload && typeof payload === 'object') {
    const { message, msg } = payload as ApiResponse<unknown>
    if (message || msg) {
      return message || msg || '\u8bf7\u6c42\u5931\u8d25'
    }
  }

  if (typeof payload === 'string' && payload.trim()) {
    return payload
  }

  return '\u7f51\u7edc\u5f02\u5e38\uff0c\u8bf7\u68c0\u67e5\u540e\u7aef\u670d\u52a1'
}

function showToast(title: string) {
  wx.showToast({
    title,
    icon: 'none',
  })
}

export function request<T, TBody = unknown, TQuery extends QueryParams = QueryParams>({
  url,
  method = 'GET',
  data,
  query,
  header = {},
}: RequestOptions<TBody, TQuery>) {
  return new Promise<T>((resolve, reject) => {
    wx.request({
      url: joinUrl(url, query),
      method,
      data,
      header: {
        'content-type': 'application/json',
        ...getMiniAuthHeaders(),
        ...header,
      },
      success: res => {
        const payload = res.data as ApiResponse<T> | T

        if (res.statusCode < 200 || res.statusCode >= 300) {
          const message = getMessage(payload)
          showToast(message)
          reject(new Error(message))
          return
        }

        if (payload && typeof payload === 'object' && 'code' in payload) {
          const envelope = payload as ApiResponse<T>
          if (envelope.code === 200) {
            resolve((envelope.data ?? ({})) as T)
            return
          }

          const message = getMessage(envelope)
          showToast(message)
          reject(new Error(message))
          return
        }

        resolve(payload as T)
      },
      fail: err => {
        const message = '\u7f51\u7edc\u5f02\u5e38\uff0c\u8bf7\u68c0\u67e5\u540e\u7aef\u670d\u52a1'
        console.error('[request] network error', { url, method, err })
        showToast(message)
        reject(new Error(message))
      },
    })
  })
}

export function get<T, TQuery extends QueryParams = QueryParams>(
  url: string,
  query?: TQuery,
  header?: WechatMiniprogram.IAnyObject
) {
  return request<T, undefined, TQuery>({
    url,
    method: 'GET',
    query,
    header,
  })
}

export function post<T, TBody = unknown, TQuery extends QueryParams = QueryParams>(
  url: string,
  data?: TBody,
  query?: TQuery,
  header?: WechatMiniprogram.IAnyObject
) {
  return request<T, TBody, TQuery>({
    url,
    method: 'POST',
    data,
    query,
    header,
  })
}

export function put<T, TBody = unknown, TQuery extends QueryParams = QueryParams>(
  url: string,
  data?: TBody,
  query?: TQuery,
  header?: WechatMiniprogram.IAnyObject
) {
  return request<T, TBody, TQuery>({
    url,
    method: 'PUT',
    data,
    query,
    header,
  })
}
