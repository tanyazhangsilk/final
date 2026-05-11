import { ORDER_STATUS, PAY_STATUS, type Order } from '../types/order'

const toIso = (date: Date): string => date.toISOString()

const addMinutes = (date: Date, mins: number): Date => new Date(date.getTime() + mins * 60 * 1000)

const baseNow = new Date()

const makeStart = (daysAgo: number, hour: number, minute: number): Date => {
  const d = new Date(baseNow)
  d.setDate(d.getDate() - daysAgo)
  d.setHours(hour, minute, 0, 0)
  return d
}

const stations = [
  { id: 'st-001', name: '南山科技园超充站' },
  { id: 'st-002', name: '福田会展中心停车场站' },
  { id: 'st-003', name: '宝安机场T3充电站' },
  { id: 'st-004', name: '前海金融中心地下站' },
  { id: 'st-005', name: '龙华红山地铁口站' },
]

const operators = [
  { id: 'op-001', name: '深能星充运营商' },
  { id: 'op-002', name: '南粤智充运营商' },
]

const users = [
  { id: 'u-001', name: '张伟', phone: '13800135678', vin: 'LGBH52E01NY100001' },
  { id: 'u-002', name: '李敏', phone: '13922345678', vin: 'LDC613P20N1000022' },
  { id: 'u-003', name: '王磊', phone: '13766889900', vin: 'LSVFA49J7N1000033' },
  { id: 'u-004', name: '陈静', phone: '13611112222', vin: 'LBV3A1E0XN1000044' },
  { id: 'u-005', name: '周峰', phone: '13598761234', vin: 'LFPH3ACC8N1000055' },
  { id: 'u-006', name: '刘洋', phone: '18800001111', vin: 'LHGCR2650N1000066' },
]

const buildOrder = (payload: Partial<Order> & Pick<Order, 'id' | 'orderNo' | 'status'>): Order => ({
  id: payload.id,
  orderNo: payload.orderNo,
  userId: payload.userId || 'u-001',
  userName: payload.userName || '张伟',
  phone: payload.phone || '13800135678',
  vin: payload.vin || 'LGBH52E01NY100001',
  operatorId: payload.operatorId || 'op-001',
  operatorName: payload.operatorName || '深能星充运营商',
  stationId: payload.stationId || 'st-001',
  stationName: payload.stationName || '南山科技园超充站',
  chargerId: payload.chargerId || 'ch-001',
  chargerName: payload.chargerName || 'A区01号直流桩',
  startTime: payload.startTime || toIso(makeStart(0, 9, 0)),
  endTime: payload.endTime ?? null,
  chargeDuration: payload.chargeDuration ?? 0,
  chargeAmount: payload.chargeAmount ?? 0,
  electricityFee: payload.electricityFee ?? 0,
  serviceFee: payload.serviceFee ?? 0,
  totalAmount: payload.totalAmount ?? 0,
  payStatus: payload.payStatus || PAY_STATUS.UNPAID,
  status: payload.status,
  abnormalReason: payload.abnormalReason ?? null,
  createdAt: payload.createdAt || payload.startTime || toIso(makeStart(0, 9, 0)),
  updatedAt: payload.updatedAt || payload.createdAt || payload.startTime || toIso(makeStart(0, 9, 0)),
})

const chargingOrders: Order[] = Array.from({ length: 5 }).map((_, idx) => {
  const user = users[idx % users.length]
  const station = stations[idx % stations.length]
  const operator = operators[idx % operators.length]
  const start = makeStart(0, 8 + idx, 10 + idx * 6)
  const minutes = 20 + idx * 9
  const chargeAmount = Number((8.5 + idx * 2.7).toFixed(2))
  const electricityFee = Number((chargeAmount * 1.05).toFixed(2))
  const serviceFee = Number((chargeAmount * 0.26).toFixed(2))

  return buildOrder({
    id: `ord-c-${idx + 1}`,
    orderNo: `EC20260401C${String(idx + 1).padStart(4, '0')}`,
    userId: user.id,
    userName: user.name,
    phone: user.phone,
    vin: user.vin,
    operatorId: operator.id,
    operatorName: operator.name,
    stationId: station.id,
    stationName: station.name,
    chargerId: `ch-${idx + 1}`,
    chargerName: `${String.fromCharCode(65 + idx)}区0${idx + 1}号直流桩`,
    startTime: toIso(start),
    endTime: null,
    chargeDuration: minutes,
    chargeAmount,
    electricityFee,
    serviceFee,
    totalAmount: Number((electricityFee + serviceFee).toFixed(2)),
    payStatus: PAY_STATUS.UNPAID,
    status: ORDER_STATUS.CHARGING,
    abnormalReason: null,
    createdAt: toIso(start),
    updatedAt: toIso(addMinutes(start, minutes)),
  })
})

const completedOrders: Order[] = Array.from({ length: 10 }).map((_, idx) => {
  const user = users[(idx + 1) % users.length]
  const station = stations[(idx + 2) % stations.length]
  const operator = operators[(idx + 1) % operators.length]
  const start = makeStart(idx % 3, 9 + (idx % 8), 5 + idx * 3)
  const duration = 45 + idx * 7
  const end = addMinutes(start, duration)
  const chargeAmount = Number((16 + idx * 1.9).toFixed(2))
  const electricityFee = Number((chargeAmount * 1.08).toFixed(2))
  const serviceFee = Number((chargeAmount * 0.32).toFixed(2))
  const totalAmount = Number((electricityFee + serviceFee).toFixed(2))

  return buildOrder({
    id: `ord-h-${idx + 1}`,
    orderNo: `EC202603${String(20 + (idx % 9)).padStart(2, '0')}H${String(idx + 1).padStart(3, '0')}`,
    userId: user.id,
    userName: user.name,
    phone: user.phone,
    vin: user.vin,
    operatorId: operator.id,
    operatorName: operator.name,
    stationId: station.id,
    stationName: station.name,
    chargerId: `ch-${(idx % 8) + 11}`,
    chargerName: `${String.fromCharCode(65 + (idx % 4))}区${String((idx % 8) + 11).padStart(2, '0')}号直流桩`,
    startTime: toIso(start),
    endTime: toIso(end),
    chargeDuration: duration,
    chargeAmount,
    electricityFee,
    serviceFee,
    totalAmount,
    payStatus: PAY_STATUS.PAID,
    status: ORDER_STATUS.COMPLETED,
    abnormalReason: null,
    createdAt: toIso(start),
    updatedAt: toIso(end),
  })
})

const abnormalReasons = ['充电枪中途断连', '计费校验异常', '支付回调超时']

const abnormalOrders: Order[] = Array.from({ length: 3 }).map((_, idx) => {
  const user = users[(idx + 3) % users.length]
  const station = stations[(idx + 1) % stations.length]
  const operator = operators[idx % operators.length]
  const start = makeStart(idx % 2, 14 + idx, 8 + idx * 10)
  const duration = 18 + idx * 6
  const updateTime = addMinutes(start, duration)
  const chargeAmount = Number((6.8 + idx * 1.6).toFixed(2))
  const electricityFee = Number((chargeAmount * 1.03).toFixed(2))
  const serviceFee = Number((chargeAmount * 0.2).toFixed(2))
  const totalAmount = Number((electricityFee + serviceFee).toFixed(2))

  return buildOrder({
    id: `ord-a-${idx + 1}`,
    orderNo: `EC20260401A${String(idx + 1).padStart(4, '0')}`,
    userId: user.id,
    userName: user.name,
    phone: user.phone,
    vin: user.vin,
    operatorId: operator.id,
    operatorName: operator.name,
    stationId: station.id,
    stationName: station.name,
    chargerId: `ch-${idx + 31}`,
    chargerName: `${String.fromCharCode(66 + idx)}区${String(idx + 31).padStart(2, '0')}号直流桩`,
    startTime: toIso(start),
    endTime: null,
    chargeDuration: duration,
    chargeAmount,
    electricityFee,
    serviceFee,
    totalAmount,
    payStatus: PAY_STATUS.UNPAID,
    status: ORDER_STATUS.ABNORMAL,
    abnormalReason: abnormalReasons[idx],
    createdAt: toIso(start),
    updatedAt: toIso(updateTime),
  })
})

export const mockOrders: Order[] = [...chargingOrders, ...completedOrders, ...abnormalOrders]

