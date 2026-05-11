export const ORDER_STATUS = {
  CHARGING: 'charging',
  COMPLETED: 'completed',
  ABNORMAL: 'abnormal',
} as const

export type OrderStatus = (typeof ORDER_STATUS)[keyof typeof ORDER_STATUS]

export const PAY_STATUS = {
  UNPAID: 'unpaid',
  PAID: 'paid',
  REFUNDED: 'refunded',
} as const

export type PayStatus = (typeof PAY_STATUS)[keyof typeof PAY_STATUS]

export interface Order {
  id: string
  orderNo: string
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
  startTime: string
  endTime: string | null
  chargeDuration: number
  chargeAmount: number
  electricityFee: number
  serviceFee: number
  totalAmount: number
  payStatus: PayStatus
  status: OrderStatus
  abnormalReason: string | null
  sourceType?: string
  sourceTypeText?: string
  priceTemplateName?: string
  createdAt: string
  updatedAt: string
}

export interface OrderStats {
  chargingCount: number
  todayCompletedCount: number
  todayTotalChargeAmount: number
  todayTotalAmount: number
  abnormalCount: number
}
