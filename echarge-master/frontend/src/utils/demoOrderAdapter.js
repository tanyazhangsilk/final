import { ORDER_STATUS, PAY_STATUS } from '../types/order'
import { useOrderStore } from '../stores/order'
import { getCurrentUserContext } from '../config/permissions'

export const demoStartUsers = [
  { id: 'u-001', nickname: '张伟', phone: '13800135678', vin: 'LGBH52E01NY100001' },
  { id: 'u-002', nickname: '李敏', phone: '13922345678', vin: 'LDC613P20N1000022' },
  { id: 'u-003', nickname: '王磊', phone: '13766889900', vin: 'LSVFA49J7N1000033' },
  { id: 'u-004', nickname: '陈静', phone: '13611112222', vin: 'LBV3A1E0XN1000044' },
]

const sourceTypeTextMap = {
  manual_demo: '手动模拟',
  qr_code: '扫码充电',
  mini_program: '小程序',
}

const statusTextMap = {
  [ORDER_STATUS.CHARGING]: '充电中',
  [ORDER_STATUS.COMPLETED]: '已完成',
  [ORDER_STATUS.ABNORMAL]: '异常结束',
}

const payStatusTextMap = {
  [PAY_STATUS.UNPAID]: '待支付',
  [PAY_STATUS.PAID]: '已支付',
  [PAY_STATUS.REFUNDED]: '已退款',
}

const formatDateTime = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

const formatDurationText = (minutes = 0) => {
  const safeMinutes = Math.max(0, Number(minutes || 0))
  if (!safeMinutes) return '0 分钟'
  const hour = Math.floor(safeMinutes / 60)
  const minute = safeMinutes % 60
  if (!hour) return `${minute} 分钟`
  return `${hour} 小时 ${minute} 分钟`
}

const buildStatusFlow = (order) => {
  const createdTime = formatDateTime(order.createdAt || order.startTime)
  const startTime = formatDateTime(order.startTime)
  const endTime = formatDateTime(order.endTime)

  const flow = [
    {
      key: 'created',
      time: createdTime,
      title: '订单创建',
      desc: `来源：${order.sourceTypeText || sourceTypeTextMap[order.sourceType] || '手动模拟'}`,
      tone: 'primary',
    },
    {
      key: 'started',
      time: startTime,
      title: '开始充电',
      desc: `${order.stationName} / ${order.chargerName}`,
      tone: 'warning',
    },
  ]

  if (order.status === ORDER_STATUS.COMPLETED) {
    flow.push({
      key: 'finished',
      time: endTime,
      title: '订单完成',
      desc: `充电时长 ${formatDurationText(order.chargeDuration)}`,
      tone: 'success',
    })
    if (order.payStatus === PAY_STATUS.PAID) {
      flow.push({
        key: 'paid',
        time: endTime,
        title: '支付完成',
        desc: '支付方式：钱包扣款（演示）',
        tone: 'success',
      })
    }
  }

  if (order.status === ORDER_STATUS.ABNORMAL) {
    flow.push({
      key: 'abnormal',
      time: endTime || formatDateTime(order.updatedAt),
      title: '异常结束',
      desc: order.abnormalReason || '订单被标记为异常结束',
      tone: 'danger',
    })
  }

  return flow
}

export const mapDemoOrderToRow = (order) => ({
  id: order.id,
  order_no: order.orderNo,
  user_nickname: order.userName,
  user_phone: order.phone,
  vin: order.vin,
  operator_name: order.operatorName,
  station_id: order.stationId,
  station_name: order.stationName,
  station_address: order.stationName ? `演示地址 · ${order.stationName}` : '',
  station_status_text: '已审核通过',
  charger_id: order.chargerId,
  charger_name: order.chargerName,
  charger_type: 'DC',
  charger_power_kw: 120,
  source_type: order.sourceType || 'manual_demo',
  source_type_text: order.sourceTypeText || sourceTypeTextMap[order.sourceType] || '手动模拟',
  start_time: formatDateTime(order.startTime),
  end_time: formatDateTime(order.endTime),
  charge_duration: Number(order.chargeDuration || 0),
  charge_duration_text: formatDurationText(order.chargeDuration),
  charge_amount: Number(order.chargeAmount || 0),
  electricity_fee: Number(order.electricityFee || 0),
  service_fee: Number(order.serviceFee || 0),
  total_amount: Number(order.totalAmount || 0),
  status: order.status,
  status_text: statusTextMap[order.status] || '处理中',
  pay_status: order.payStatus,
  pay_status_text: payStatusTextMap[order.payStatus] || '待支付',
  settlement_status: 0,
  settlement_status_text: '待结算',
  abnormal_reason: order.abnormalReason || '',
  price_template_name: order.priceTemplateName || '默认计费模板',
  fee_detail: {
    charge_amount: Number(order.chargeAmount || 0),
    electricity_fee: Number(order.electricityFee || 0),
    service_fee: Number(order.serviceFee || 0),
    total_amount: Number(order.totalAmount || 0),
    flat_price: 1.08,
    service_price: 0.32,
  },
  status_flow: buildStatusFlow(order),
})

const buildScope = () => {
  const { role, operatorId } = getCurrentUserContext()
  return { role, operatorId }
}

const getScopedRows = (type) => {
  const store = useOrderStore()
  const scope = buildScope()
  const orders =
    type === 'realtime'
      ? store.getRealtimeOrders(scope)
      : type === 'abnormal'
        ? store.getAbnormalOrders(scope)
        : store.getHistoryOrders(scope)
  return orders.map(mapDemoOrderToRow)
}

export const getDemoOrderListPayload = (type) => {
  const items = getScopedRows(type)

  if (type === 'realtime') {
    return {
      items,
      total: items.length,
      summary: {
        total_count: items.length,
        total_charge_amount: items.reduce((sum, item) => sum + Number(item.charge_amount || 0), 0),
        total_ele_fee: items.reduce((sum, item) => sum + Number(item.electricity_fee || 0), 0),
        total_service_fee: items.reduce((sum, item) => sum + Number(item.service_fee || 0), 0),
      },
    }
  }

  if (type === 'abnormal') {
    const reasonCount = new Set(items.map((item) => item.abnormal_reason).filter(Boolean)).size
    return {
      items,
      total: items.length,
      summary: {
        total_count: items.length,
        total_amount: items.reduce((sum, item) => sum + Number(item.total_amount || 0), 0),
        reason_count: reasonCount,
        abnormal_count: items.length,
      },
    }
  }

  return {
    items,
    total: items.length,
    summary: {
      total_count: items.length,
      total_charge_amount: items.reduce((sum, item) => sum + Number(item.charge_amount || 0), 0),
      total_amount: items.reduce((sum, item) => sum + Number(item.total_amount || 0), 0),
      total_service_fee: items.reduce((sum, item) => sum + Number(item.service_fee || 0), 0),
    },
  }
}

export const getDemoOrderDetail = (orderId) => {
  const store = useOrderStore()
  const order = store.getOrderById(String(orderId), buildScope())
  return order ? mapDemoOrderToRow(order) : null
}

export const startLocalDemoOrder = ({ station, charger, user, sourceType }) => {
  const store = useOrderStore()
  const { operatorId } = getCurrentUserContext()
  const created = store.startDemoOrder({
    userId: user.id,
    userName: user.nickname,
    phone: user.phone,
    vin: user.vin,
    operatorId,
    operatorName: station.operator_name || '当前运营商',
    stationId: String(station.id),
    stationName: station.station_name,
    chargerId: String(charger.id),
    chargerName: charger.charger_name,
    sourceType,
    sourceTypeText: sourceTypeTextMap[sourceType] || '手动模拟',
    priceTemplateName: station.price_template_name || '默认计费模板',
  })
  return mapDemoOrderToRow(created)
}

export const finishLocalDemoOrder = (orderId) => {
  const store = useOrderStore()
  const updated = store.finishOrder(String(orderId), buildScope())
  return updated ? mapDemoOrderToRow(updated) : null
}

export const markLocalDemoOrderAbnormal = (orderId, reason) => {
  const store = useOrderStore()
  const updated = store.markOrderAbnormal(String(orderId), reason, buildScope())
  return updated ? mapDemoOrderToRow(updated) : null
}
