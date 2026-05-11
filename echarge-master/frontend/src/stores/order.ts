import { defineStore } from 'pinia'
import { ref } from 'vue'
import { mockOrders } from '../mock/orders'
import { ORDER_STATUS, PAY_STATUS, type Order, type OrderStats } from '../types/order'
import { getStoredOperatorId, getStoredRole, ROLES } from '../config/permissions'

// 订单明细页与列表页已切换为后端接口，此 store 仅保留给总览页做趋势兼容展示。
export interface OrderScope {
  role?: 'admin' | 'operator'
  operatorId?: string
}

export interface OrderTrendPoint {
  date: string
  orderCount: number
  revenue: number
}

export interface DemoOrderPayload {
  userId: string
  userName: string
  phone: string
  vin: string
  operatorId: string
  operatorName: string
  stationId: string
  stationName: string
  chargerId: string
  chargerName: string
  sourceType: string
  sourceTypeText: string
  priceTemplateName?: string
}

const cloneOrders = (): Order[] => JSON.parse(JSON.stringify(mockOrders))

const safeNumber = (value: unknown): number => {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

const isToday = (dateStr: string | null): boolean => {
  if (!dateStr) return false
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return false

  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

const toDateValue = (value: string | null | undefined): number => {
  if (!value) return 0
  const parsed = new Date(value).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}

const sortByLatest = (a: Order, b: Order): number =>
  toDateValue(b.updatedAt || b.endTime || b.startTime) - toDateValue(a.updatedAt || a.endTime || a.startTime)

const toDayKey = (date: Date): string => {
  const y = date.getFullYear()
  const m = `${date.getMonth() + 1}`.padStart(2, '0')
  const d = `${date.getDate()}`.padStart(2, '0')
  return `${y}-${m}-${d}`
}

const toDayLabel = (dayKey: string): string => dayKey.slice(5)

export const useOrderStore = defineStore('order', () => {
  const orders = ref<Order[]>(cloneOrders())

  const normalizeScope = (scope?: OrderScope): Required<OrderScope> => {
    const role = scope?.role || (getStoredRole() as 'admin' | 'operator')
    const operatorId = scope?.operatorId || getStoredOperatorId()
    return {
      role: role === ROLES.ADMIN ? ROLES.ADMIN : ROLES.OPERATOR,
      operatorId,
    }
  }

  const isOrderVisible = (order: Order, scope?: OrderScope): boolean => {
    const normalized = normalizeScope(scope)
    if (normalized.role === ROLES.ADMIN) return true
    return order.operatorId === normalized.operatorId
  }

  const scopedOrders = (scope?: OrderScope): Order[] => orders.value.filter((order) => isOrderVisible(order, scope))

  const getAllOrders = (scope?: OrderScope): Order[] => scopedOrders(scope).slice().sort(sortByLatest)

  const getRealtimeOrders = (scope?: OrderScope): Order[] =>
    scopedOrders(scope)
      .filter((order) => order.status === ORDER_STATUS.CHARGING)
      .sort((a, b) => toDateValue(b.startTime) - toDateValue(a.startTime))

  const getHistoryOrders = (scope?: OrderScope): Order[] =>
    scopedOrders(scope)
      .filter((order) => order.status === ORDER_STATUS.COMPLETED)
      .sort(sortByLatest)

  const getAbnormalOrders = (scope?: OrderScope): Order[] =>
    scopedOrders(scope)
      .filter((order) => order.status === ORDER_STATUS.ABNORMAL)
      .sort(sortByLatest)

  const getOrderById = (id: string, scope?: OrderScope): Order | undefined =>
    scopedOrders(scope).find((order) => order.id === id)

  const finishOrder = (id: string, scope?: OrderScope): Order | null => {
    const target = getOrderById(id, scope)
    if (!target || target.status !== ORDER_STATUS.CHARGING) return null

    const now = new Date()
    const start = new Date(target.startTime)
    const diffMs = now.getTime() - start.getTime()
    const duration = Number.isFinite(diffMs) && diffMs > 0 ? Math.round(diffMs / 60000) : target.chargeDuration

    target.status = ORDER_STATUS.COMPLETED
    target.endTime = now.toISOString()
    target.chargeDuration = duration
    target.totalAmount = Number((safeNumber(target.electricityFee) + safeNumber(target.serviceFee)).toFixed(2))
    target.payStatus = PAY_STATUS.PAID
    target.updatedAt = now.toISOString()

    return target
  }

  const markOrderAbnormal = (id: string, reason: string, scope?: OrderScope): Order | null => {
    const target = getOrderById(id, scope)
    if (!target || target.status !== ORDER_STATUS.CHARGING) return null

    target.status = ORDER_STATUS.ABNORMAL
    target.endTime = new Date().toISOString()
    target.abnormalReason = reason?.trim() || '系统判定异常'
    target.updatedAt = target.endTime

    return target
  }

  const startDemoOrder = (payload: DemoOrderPayload): Order => {
    const now = new Date()
    const stamp = `${now.getFullYear()}${`${now.getMonth() + 1}`.padStart(2, '0')}${`${now.getDate()}`.padStart(2, '0')}${`${now.getHours()}`.padStart(2, '0')}${`${now.getMinutes()}`.padStart(2, '0')}${`${now.getSeconds()}`.padStart(2, '0')}`
    const orderNo = `EC${stamp}${Math.floor(Math.random() * 900 + 100)}`
    const order: Order = {
      id: `local-${Date.now()}`,
      orderNo,
      userId: payload.userId,
      userName: payload.userName,
      phone: payload.phone,
      vin: payload.vin,
      operatorId: payload.operatorId,
      operatorName: payload.operatorName,
      stationId: payload.stationId,
      stationName: payload.stationName,
      chargerId: payload.chargerId,
      chargerName: payload.chargerName,
      startTime: now.toISOString(),
      endTime: null,
      chargeDuration: 0,
      chargeAmount: 0,
      electricityFee: 0,
      serviceFee: 0,
      totalAmount: 0,
      payStatus: PAY_STATUS.UNPAID,
      status: ORDER_STATUS.CHARGING,
      abnormalReason: null,
      sourceType: payload.sourceType,
      sourceTypeText: payload.sourceTypeText,
      priceTemplateName: payload.priceTemplateName || '默认计费模板',
      createdAt: now.toISOString(),
      updatedAt: now.toISOString(),
    }
    orders.value.unshift(order)
    return order
  }

  const getOrderStats = (scope?: OrderScope): OrderStats => {
    const visibleOrders = scopedOrders(scope)
    const chargingCount = visibleOrders.filter((order) => order.status === ORDER_STATUS.CHARGING).length
    const todayCompleted = visibleOrders.filter(
      (order) => order.status === ORDER_STATUS.COMPLETED && isToday(order.endTime || order.updatedAt),
    )
    const abnormalCount = visibleOrders.filter((order) => order.status === ORDER_STATUS.ABNORMAL).length

    return {
      chargingCount,
      todayCompletedCount: todayCompleted.length,
      todayTotalChargeAmount: Number(todayCompleted.reduce((sum, item) => sum + safeNumber(item.chargeAmount), 0).toFixed(2)),
      todayTotalAmount: Number(todayCompleted.reduce((sum, item) => sum + safeNumber(item.totalAmount), 0).toFixed(2)),
      abnormalCount,
    }
  }

  const getOrderTrend = (scope?: OrderScope, days = 7): OrderTrendPoint[] => {
    const safeDays = Math.max(1, days)
    const now = new Date()
    const buckets = Array.from({ length: safeDays }, (_, index) => {
      const current = new Date(now)
      current.setDate(now.getDate() - (safeDays - 1 - index))
      return {
        key: toDayKey(current),
        date: toDayLabel(toDayKey(current)),
        orderCount: 0,
        revenue: 0,
      }
    })
    const map = new Map(buckets.map((item) => [item.key, item]))

    scopedOrders(scope)
      .filter((item) => item.status === ORDER_STATUS.COMPLETED)
      .forEach((order) => {
        const time = order.endTime || order.updatedAt || order.startTime
        const dateObj = new Date(time)
        if (Number.isNaN(dateObj.getTime())) return
        const key = toDayKey(dateObj)
        const bucket = map.get(key)
        if (!bucket) return
        bucket.orderCount += 1
        bucket.revenue = Number((bucket.revenue + safeNumber(order.totalAmount)).toFixed(2))
      })

    return buckets.map((item) => ({
      date: item.date,
      orderCount: item.orderCount,
      revenue: item.revenue,
    }))
  }

  return {
    orders,
    getAllOrders,
    getRealtimeOrders,
    getHistoryOrders,
    getAbnormalOrders,
    getOrderById,
    startDemoOrder,
    finishOrder,
    markOrderAbnormal,
    getOrderStats,
    getOrderTrend,
  }
})
