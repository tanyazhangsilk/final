import { get, post } from '../utils/request'

export interface StartChargingPayload {
  pileId: string,
  stationId?: string
}

export interface EndOrderPayload {
  orderId: string
}

export function startCharging(data: StartChargingPayload) {
  return post('/orders/start', data)
}

export function getMyOrders() {
  return get('/orders/my')
}

export function endOrder(data: EndOrderPayload) {
  return post('/orders/end', data)
}
