import { BASE_URL } from '../config/env'
import { getMiniAuthHeaders } from './storage'

type RequestMethod = 'GET' | 'POST'

export interface RequestOptions<TData = WechatMiniprogram.IAnyObject> {
  url: string,
  method?: RequestMethod,
  data?: TData,
  header?: WechatMiniprogram.IAnyObject
}

interface ApiEnvelope<T> {
  code?: number,
  message?: string,
  msg?: string,
  data?: T
}

function joinUrl(url: string) {
  if (/^https?:\/\//.test(url)) {
    return url
  }

  return `${BASE_URL}${url.startsWith('/') ? url : `/${url}`}`
}

function getErrorMessage(data: unknown) {
  if (typeof data === 'string') {
    return data
  }

  if (data && typeof data === 'object') {
    const { message, msg } = data as ApiEnvelope<unknown>
    if (message || msg) {
      return message || msg || 'Request failed'
    }
  }

  return 'Request failed'
}

function shouldUnwrapData(data: unknown) {
  return Boolean(
    data &&
      typeof data === 'object' &&
      'data' in data &&
      ('code' in data || 'message' in data || 'msg' in data)
  )
}

export function request<T, TData = WechatMiniprogram.IAnyObject>({
  url,
  method = 'GET',
  data,
  header = {},
}: RequestOptions<TData>): Promise<T> {
  return new Promise((resolve, reject) => {
    const requestHeader: WechatMiniprogram.IAnyObject = {
      'content-type': 'application/json',
      ...getMiniAuthHeaders(),
      ...header,
    }

    wx.request({
      url: joinUrl(url),
      method,
      data,
      header: requestHeader,
      success: res => {
        const { statusCode } = res
        const responseData = res.data

        if (statusCode < 200 || statusCode >= 300) {
          console.error('[request] http error', { url, method, statusCode, responseData })
          reject(new Error(getErrorMessage(responseData)))
          return
        }

        if (
          responseData &&
          typeof responseData === 'object' &&
          'code' in responseData &&
          typeof (responseData as ApiEnvelope<T>).code === 'number' &&
          ![0, 200].includes((responseData as ApiEnvelope<T>).code as number)
        ) {
          console.error('[request] business error', { url, method, responseData })
          reject(new Error(getErrorMessage(responseData)))
          return
        }

        if (shouldUnwrapData(responseData)) {
          resolve((responseData as ApiEnvelope<T>).data as T)
          return
        }

        resolve(responseData as T)
      },
      fail: err => {
        console.error('[request] network error', { url, method, err })
        reject(new Error(err.errMsg || 'Network error, please try again later'))
      },
    })
  })
}

export function get<T, TData = WechatMiniprogram.IAnyObject>(
  url: string,
  data?: TData,
  header?: WechatMiniprogram.IAnyObject
) {
  return request<T, TData>({
    url,
    method: 'GET',
    data,
    header,
  })
}

export function post<T, TData = WechatMiniprogram.IAnyObject>(
  url: string,
  data?: TData,
  header?: WechatMiniprogram.IAnyObject
) {
  return request<T, TData>({
    url,
    method: 'POST',
    data,
    header,
  })
}
