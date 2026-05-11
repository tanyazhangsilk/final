import type {
  ChargingSession,
  InvoiceRecord,
  OrderItem,
  OrderStatus,
  StationItem,
  StationPile,
  WalletRecord,
} from './mock'
import { formatDuration } from './mock'
import { get, post } from './request'
import { getStoredBalance, getStoredUser } from '../utils/storage'

type AnyRecord = Record<string, unknown>
type PileStatus = StationPile['status']

export interface MiniHealth {
  ok: boolean,
  message: string,
  timestamp: string
}

export interface WalletSummary {
  balance: number,
  balanceText: string,
  couponCount: number
}

export interface CouponItem {
  id: string,
  title: string,
  desc: string,
  tag: string,
  couponValue: string,
  expireText: string,
  received: boolean
}

export interface ChargerLookupResult {
  id: string,
  stationId: string,
  stationName: string,
  pileNo: string,
  snCode: string,
  gunNo: string,
  available: boolean,
  status: PileStatus,
  statusText: string,
  power: string,
  connector: string
}

export interface StartOrderPayload {
  sn_code: string,
  station_id?: string
}

export interface ApplyInvoicePayload {
  order_id: string,
  title: string,
  email: string,
  note?: string,
  type?: string
}

export interface OrderDetailItem extends OrderItem {
  energyValue: number,
  electricityFeeValue: number,
  serviceFeeValue: number,
  totalAmountValue: number,
  discountFeeValue: number,
  electricityFeeText: string,
  serviceFeeText: string,
  totalAmountText: string,
  paymentStatus: string,
  orderStatus: string,
  batteryPercent: number,
  currentPowerValue: number
  /** 与后端 charge_duration 一致，充电页轮询用 */
  elapsedMinutes?: number
}

function isRecord(value: unknown): value is AnyRecord {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function pickValue<T>(source: AnyRecord, keys: string[], fallback?: T) {
  for (const key of keys) {
    const value = source[key]
    if (value !== undefined && value !== null && value !== '') {
      return value as T
    }
  }
  return fallback
}

function toRecord(value: unknown) {
  return isRecord(value) ? value : {}
}

function toId(value: unknown, fallback = '') {
  if (value === undefined || value === null) {
    return fallback
  }
  return String(value)
}

function toNumber(value: unknown, fallback = 0) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value === 'string') {
    const parsed = Number(value.replace(/[^\d.-]/g, ''))
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }

  return fallback
}

function toStringArray(value: unknown) {
  if (Array.isArray(value)) {
    return value.map(item => String(item).trim()).filter(Boolean)
  }

  if (typeof value === 'string') {
    return value.split(/[,/|]/).map(item => item.trim()).filter(Boolean)
  }

  return []
}

function listFromResponse<T>(value: unknown) {
  if (Array.isArray(value)) {
    return value as T[]
  }

  if (!isRecord(value)) {
    return []
  }

  for (const key of ['list', 'items', 'results', 'records', 'rows', 'data']) {
    const current = value[key]
    if (Array.isArray(current)) {
      return current as T[]
    }
  }

  return []
}

function formatMoney(value: number) {
  return value.toFixed(2)
}

function formatAmountText(value: number) {
  return value > 0 ? `+${formatMoney(value)}` : formatMoney(value)
}

function formatDateTime(value: unknown) {
  if (typeof value === 'string' && value.trim()) {
    return value.replace('T', ' ').replace(/\.\d+Z?$/, '').trim()
  }
  return '--'
}

function formatDistance(value: unknown) {
  if (typeof value === 'string' && value.trim()) {
    return value.includes('km') ? value : `${value}km`
  }

  const numeric = toNumber(value, 0)
  return numeric > 0 ? `${numeric.toFixed(1)}km` : '--'
}

function buildPriceText(price: number) {
  return price > 0 ? `CNY ${formatMoney(price)}/kWh` : 'Price pending'
}

function derivePileStatus(raw: string, available = false): PileStatus {
  const normalized = raw.toLowerCase()
  if (available || ['idle', 'free', 'available', 'ready'].some(item => normalized.includes(item))) {
    return 'idle'
  }
  if (['fault', 'offline', 'error', 'broken', 'unavailable'].some(item => normalized.includes(item))) {
    return 'fault'
  }
  return 'busy'
}

function buildPileStatusText(status: PileStatus) {
  if (status === 'idle') {
    return 'Available'
  }
  if (status === 'fault') {
    return 'Unavailable'
  }
  return 'Charging'
}

function buildPileQueueText(status: PileStatus, available: number, total: number) {
  if (status === 'idle') {
    return 'Ready to use'
  }
  if (status === 'fault') {
    return 'Temporarily unavailable'
  }
  if (total > 0) {
    return `${available}/${total} available`
  }
  return 'Refer to onsite equipment status'
}

function buildStationStatus(available: number, total: number) {
  if (available <= 0) {
    return {
      statusKey: 'queue',
      statusText: 'Busy',
    }
  }

  if (total > 0 && available / total <= 0.3) {
    return {
      statusKey: 'busy',
      statusText: 'Partially busy',
    }
  }

  return {
    statusKey: 'idle',
    statusText: 'Available',
  }
}

function buildChargeType(value: unknown, fastCount: number, slowCount: number): StationItem['chargeType'] {
  if (typeof value === 'string' && value.trim()) {
    return value as StationItem['chargeType']
  }

  if (fastCount > 0 && slowCount > 0) {
    return '\u5feb\u6162\u7ed3\u5408' as StationItem['chargeType']
  }

  if (fastCount > 0) {
    return '\u5feb\u5145\u4f18\u5148' as StationItem['chargeType']
  }

  return '\u6162\u5145\u670d\u52a1' as StationItem['chargeType']
}

function buildPriceBreakdown(source: AnyRecord) {
  const periods = listFromResponse<unknown>(
    pickValue(source, ['price_breakdown', 'price_periods', 'prices'], [])
  )
  if (!periods.length) {
    return [
      {
        label: 'Default',
        time: '00:00 - 24:00',
        price: buildPriceText(toNumber(pickValue(source, ['price', 'current_price', 'fee_per_kwh'], 0))),
      },
    ]
  }

  return periods.map(item => {
    const record = toRecord(item)
    return {
      label: String(pickValue(record, ['label', 'period', 'name'], 'Period')),
      time: String(pickValue(record, ['time', 'range'], '00:00 - 24:00')),
      price: String(pickValue(record, ['price', 'price_text'], 'Pending')),
    }
  })
}

function mapStationPile(value: unknown, stationId: string, available: number, total: number): StationPile {
  const source = toRecord(value)
  const rawStatus = String(pickValue(source, ['status', 'charger_status', 'state'], '') || '')
  const status = derivePileStatus(rawStatus, Boolean(pickValue(source, ['available', 'is_available'], false)))
  const id = toId(
    pickValue(source, ['sn_code', 'snCode', 'pile_no', 'pileNo', 'id'], ''),
    `${stationId}-pile`
  )
  const rawPower = String(pickValue(source, ['power', 'power_kw', 'powerKw'], '--'))

  return {
    id,
    label: String(pickValue(source, ['label', 'name', 'pile_name', 'pileName'], `${id}`)),
    power: rawPower === '--' || rawPower.includes('kW') ? rawPower : `${rawPower}kW`,
    connector: String(pickValue(source, ['connector', 'connector_type', 'connectorType'], 'GBT DC')),
    status,
    statusText: String(pickValue(source, ['status_text', 'statusText'], buildPileStatusText(status))),
    queueText: String(
      pickValue(source, ['queue_text', 'queueText'], buildPileQueueText(status, available, total))
    ),
  }
}

function buildFallbackPiles(stationId: string, available: number, total: number) {
  const status = available > 0 ? 'idle' : 'busy'
  return [
    {
      id: `${stationId}-summary`,
      label: 'Pile info pending',
      power: '--',
      connector: 'Refer to onsite equipment',
      status,
      statusText: buildPileStatusText(status),
      queueText: `${available}/${total} available`,
    } as StationPile,
  ]
}

function mapStation(sourceValue: unknown): StationItem {
  const sourceRoot = toRecord(sourceValue)
  const source = {
    ...sourceRoot,
    ...toRecord(pickValue(sourceRoot, ['station'], sourceRoot)),
  }
  const id = toId(pickValue(source, ['id', 'station_id', 'stationId'], ''))
  const available = toNumber(
    pickValue(source, ['available_chargers', 'available_count', 'idle_piles', 'available'], 0)
  )
  const total = toNumber(pickValue(source, ['total_chargers', 'total_piles', 'total'], 0))
  const fastCount = toNumber(pickValue(source, ['fast_count', 'fast_chargers', 'fastCount'], 0))
  const slowCount = toNumber(pickValue(source, ['slow_count', 'slow_chargers', 'slowCount'], 0))
  const price = toNumber(pickValue(source, ['current_price', 'price', 'fee_per_kwh'], 0))
  const tags = toStringArray(pickValue(source, ['tags', 'station_tags', 'labels'], []))
  const serviceTags = toStringArray(pickValue(source, ['service_tags', 'serviceTags'], tags))
  const recommendReasons = toStringArray(
    pickValue(source, ['recommend_reasons', 'recommendReasons'], serviceTags)
  )
  const chargers = listFromResponse<unknown>(
    pickValue(sourceRoot, ['chargers', 'piles'], pickValue(source, ['chargers', 'piles'], []))
  )
  const { statusKey, statusText } = buildStationStatus(available, total)

  return {
    id,
    name: String(pickValue(source, ['station_name', 'stationName', 'name'], 'Charging Station')),
    address: String(pickValue(source, ['address', 'detail_address', 'location'], 'Address pending')),
    operator: String(
      pickValue(source, ['operator_name', 'operator', 'brand', 'provider'], 'Operator pending')
    ),
    statusKey,
    available,
    total,
    distance: formatDistance(pickValue(source, ['distance', 'distance_km', 'distanceKm'], 0)),
    distanceValue: toNumber(pickValue(source, ['distance_km', 'distanceKm', 'distance'], 0)),
    statusText: String(pickValue(source, ['status_text', 'statusText'], statusText)),
    businessHours: String(pickValue(source, ['business_hours', 'businessHours'], '00:00 - 24:00')),
    parkingTips: String(pickValue(source, ['parking_tips', 'parkingTips'], 'Refer to onsite parking')),
    serviceTips: String(pickValue(source, ['service_tips', 'serviceTips'], 'Scan to start charging')),
    currentPriceText: String(
      pickValue(source, ['current_price_text', 'currentPriceText'], buildPriceText(price))
    ),
    currentPriceValue: price,
    score: String(pickValue(source, ['score', 'rating'], '4.8')),
    reviewCount: toNumber(pickValue(source, ['review_count', 'reviewCount'], 0)),
    tags: tags.length ? tags : ['scan', 'stable'],
    serviceTags: serviceTags.length ? serviceTags : ['stable'],
    recommendReasons: recommendReasons.length ? recommendReasons : ['nearby'],
    chargeType: buildChargeType(pickValue(source, ['charge_type', 'chargeType'], ''), fastCount, slowCount),
    fastCount,
    slowCount,
    favorite: Boolean(pickValue(source, ['favorite', 'is_favorite', 'isFavorite'], false)),
    announcement: String(
      pickValue(source, ['announcement', 'notice'], 'Confirm vehicle and charger are connected.')
    ),
    priceBreakdown: buildPriceBreakdown(source),
    piles: chargers.length
      ? chargers.map(item => mapStationPile(item, id, available, total))
      : buildFallbackPiles(id, available, total),
  }
}

function normalizeOrderStatus(rawStatus: string): OrderStatus {
  const normalized = rawStatus.toLowerCase()
  if (['charging', 'pending', 'started', 'running'].some(item => normalized.includes(item))) {
    return 'charging'
  }
  if (['abnormal', 'failed', 'fault', 'cancel'].some(item => normalized.includes(item))) {
    return 'abnormal'
  }
  return 'completed'
}

function buildOrderStatusText(status: OrderStatus) {
  if (status === 'charging') {
    return 'Charging'
  }
  if (status === 'abnormal') {
    return 'Abnormal'
  }
  return 'Completed'
}

function buildPaymentStatusText(rawStatus: string, orderStatus: OrderStatus) {
  const normalized = rawStatus.toLowerCase()
  if (['paid', 'success', 'settled', 'done'].some(item => normalized.includes(item))) {
    return 'Paid'
  }
  if (orderStatus === 'charging') {
    return 'Pending'
  }
  return 'Unpaid'
}

function buildInvoiceStatusText(rawStatus: string, orderStatus: OrderStatus) {
  const normalized = rawStatus.toLowerCase()
  if (['issued', 'done', 'completed'].some(item => normalized.includes(item))) {
    return 'Issued'
  }
  if (['pending', 'review'].some(item => normalized.includes(item))) {
    return 'Pending'
  }
  if (orderStatus === 'completed') {
    return 'Available'
  }
  return 'After completion'
}

function diffMinutes(startTime: string, endTime: string) {
  const start = new Date(startTime.replace(/-/g, '/')).getTime()
  const end = new Date(endTime.replace(/-/g, '/')).getTime()

  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return 0
  }

  return Math.max(Math.round((end - start) / 60000), 0)
}

function mapOrder(value: unknown): OrderDetailItem {
  const sourceRoot = toRecord(value)
  const source = {
    ...sourceRoot,
    ...toRecord(pickValue(sourceRoot, ['order'], sourceRoot)),
  }
  // 后端 serialize_order 同时带数值 status 与字符串 order_status，须优先用字符串以免把 0 当成 "0"
  const orderStatusRaw = String(pickValue(source, ['order_status', 'orderStatus', 'status'], 'completed'))
  const status = normalizeOrderStatus(orderStatusRaw)
  const startTime = formatDateTime(pickValue(source, ['start_time', 'started_at', 'startTime'], '--'))
  const endTime = formatDateTime(pickValue(source, ['end_time', 'finished_at', 'endTime'], '--'))
  const durationMinutes =
    toNumber(
      pickValue(source, ['duration_minutes', 'duration', 'durationMinutes', 'charge_duration'], 0)
    ) || (endTime !== '--' ? diffMinutes(startTime, endTime) : 0)
  const energyValue = toNumber(
    pickValue(source, ['total_power', 'power', 'energy', 'charged_kwh', 'total_energy', 'charge_amount', 'total_kwh'], 0)
  )
  const electricityFeeValue = toNumber(
    pickValue(source, ['electricity_fee', 'ele_fee', 'power_fee', 'energy_fee'], 0)
  )
  const serviceFeeValue = toNumber(pickValue(source, ['service_fee', 'serviceFee'], 0))
  const discountFeeValue = toNumber(
    pickValue(source, ['discount_fee', 'discount_amount', 'discount'], 0)
  )
  const totalAmountValue = toNumber(
    pickValue(source, ['total_amount', 'total_fee', 'amount', 'pay_amount', 'payable_amount'], 0)
  )
  const paymentStatus = String(
    pickValue(
      source,
      ['payment_status', 'paymentStatus', 'pay_status_label', 'pay_status'],
      status === 'charging' ? 'pending' : 'paid'
    )
  )
  const invoiceStatus = String(pickValue(source, ['invoice_status', 'invoiceStatus'], ''))

  return {
    id: toId(pickValue(source, ['id', 'order_id', 'orderId'], '')),
    orderNo: String(pickValue(source, ['order_no', 'orderNo', 'trade_no'], '--')),
    stationId: toId(pickValue(source, ['station_id', 'stationId'], '')),
    stationName: String(pickValue(source, ['station_name', 'stationName', 'station'], 'Station')),
    pileNo: String(pickValue(source, ['pile_no', 'pileNo', 'sn_code', 'snCode', 'charger_sn'], '--')),
    gunNo: String(pickValue(source, ['gun_no', 'gunNo'], 'Gun 1')),
    startTime,
    endTime: status === 'charging' && endTime === '--' ? '--' : endTime,
    durationText: status === 'charging' && durationMinutes <= 0 ? 'In progress' : formatDuration(durationMinutes),
    powerText: `${energyValue.toFixed(1)} kWh`,
    amountText: formatMoney(totalAmountValue),
    amountValue: totalAmountValue,
    payableText: formatMoney(totalAmountValue),
    discountText: discountFeeValue > 0 ? `Discount ${formatMoney(discountFeeValue)}` : 'No discount',
    discountValue: discountFeeValue,
    status,
    statusText: String(pickValue(source, ['status_text', 'statusText'], buildOrderStatusText(status))),
    paymentStatusText: buildPaymentStatusText(paymentStatus, status),
    invoiceStatusText: buildInvoiceStatusText(invoiceStatus, status),
    canInvoice: status === 'completed',
    canChargeAgain: status !== 'charging',
    abnormalReason: String(
      pickValue(source, ['abnormal_reason', 'abnormalReason'], status === 'abnormal' ? 'Abnormal stop' : '')
    ),
    energyValue,
    electricityFeeValue,
    serviceFeeValue,
    totalAmountValue,
    discountFeeValue,
    electricityFeeText: formatMoney(electricityFeeValue),
    serviceFeeText: formatMoney(serviceFeeValue),
    totalAmountText: formatMoney(totalAmountValue),
    paymentStatus,
    orderStatus: orderStatusRaw,
    batteryPercent: toNumber(pickValue(source, ['battery_percent', 'battery', 'soc'], 32)),
    currentPowerValue: toNumber(pickValue(source, ['current_power', 'power_kw', 'real_time_power'], 38)),
    elapsedMinutes: durationMinutes,
  }
}

function mapWalletSummary(value: unknown): WalletSummary {
  const source = toRecord(value)
  const balance = toNumber(
    pickValue(source, ['balance', 'available_balance', 'wallet_balance', 'amount'], 0)
  )

  return {
    balance,
    balanceText: formatMoney(balance),
    couponCount: toNumber(pickValue(source, ['coupon_count', 'couponCount'], 0)),
  }
}

function mapWalletRecord(value: unknown): WalletRecord {
  const source = toRecord(value)
  const amount = toNumber(pickValue(source, ['amount', 'change_amount', 'value'], 0))
  const category = String(
    pickValue(source, ['category', 'biz_type', 'type'], amount >= 0 ? 'recharge' : 'consume')
  )
  const normalizedCategory = category.toLowerCase().includes('recharge') ? 'recharge' : 'consume'

  return {
    id: toId(pickValue(source, ['id', 'record_id', 'recordId'], '')),
    title: String(
      pickValue(
        source,
        ['title', 'transaction_type_label', 'station_name', 'stationName', 'remark'],
        'Wallet change'
      )
    ),
    time: formatDateTime(pickValue(source, ['time', 'created_at', 'createdAt'], '--')),
    amountText: formatAmountText(amount),
    type: amount >= 0 ? 'income' : 'expense',
    category: normalizedCategory,
    channel: String(
      pickValue(
        source,
        ['channel', 'payment_channel', 'paymentChannel'],
        normalizedCategory === 'recharge' ? 'Wallet recharge' : 'Charging payment'
      )
    ),
    description: String(
      pickValue(
        source,
        ['description', 'remark'],
        normalizedCategory === 'recharge' ? 'Balance recharge' : 'Order settlement'
      )
    ),
  }
}

function mapInvoiceRecord(value: unknown): InvoiceRecord {
  const source = toRecord(value)
  const rawStatus = pickValue(source, ['status', 'invoice_status'], 'pending')
  let normalizedStatus: InvoiceRecord['status'] = 'pending'
  if (typeof rawStatus === 'number') {
    if (rawStatus === 1) {
      normalizedStatus = 'issued'
    } else if (rawStatus === 2) {
      normalizedStatus = 'rejected'
    } else {
      normalizedStatus = 'pending'
    }
  } else {
    const status = String(rawStatus).toLowerCase()
    normalizedStatus =
      status.includes('issue') || status.includes('done')
        ? 'issued'
        : status.includes('reject')
          ? 'rejected'
          : 'pending'
  }

  return {
    id: toId(pickValue(source, ['id', 'invoice_id', 'invoiceId'], '')),
    orderId: toId(pickValue(source, ['order_id', 'orderId'], '')),
    orderNo: String(pickValue(source, ['order_no', 'orderNo'], '--')),
    typeText: String(pickValue(source, ['type_text', 'typeText', 'invoice_type'], 'E-Invoice')),
    title: String(pickValue(source, ['title', 'invoice_title'], 'Individual')),
    email: String(pickValue(source, ['email', 'receiver_email'], '')),
    amountText: formatMoney(toNumber(pickValue(source, ['amount', 'invoice_amount'], 0))),
    status: normalizedStatus,
    statusText:
      normalizedStatus === 'issued'
        ? 'Issued'
        : normalizedStatus === 'rejected'
          ? 'Rejected'
          : 'Pending',
    applyTime: formatDateTime(pickValue(source, ['apply_time', 'created_at', 'createdAt'], '--')),
    note: String(pickValue(source, ['note', 'remark'], '')),
    attachmentName: String(
      pickValue(
        source,
        ['attachment_name', 'attachmentName', 'file_name'],
        normalizedStatus === 'issued' ? 'invoice.pdf' : 'Pending'
      )
    ),
    progressText: String(
      pickValue(
        source,
        ['progress_text', 'progressText'],
        normalizedStatus === 'issued' ? 'Invoice issued.' : 'Application submitted.'
      )
    ),
    rejectReason: String(pickValue(source, ['reject_reason', 'rejectReason'], '')),
  }
}

function mapCoupon(value: unknown): CouponItem {
  const source = toRecord(value)
  return {
    id: toId(pickValue(source, ['id', 'coupon_id', 'couponId'], '')),
    title: String(pickValue(source, ['title', 'name'], 'Coupon')),
    desc: String(pickValue(source, ['desc', 'description'], 'Available for charging orders')),
    tag: String(pickValue(source, ['tag', 'type'], 'Coupon')),
    couponValue: String(pickValue(source, ['coupon_value', 'couponValue', 'value_text'], 'Pending')),
    expireText: String(
      pickValue(source, ['expire_text', 'expireText', 'expired_at'], 'Refer to backend validity')
    ),
    received: Boolean(pickValue(source, ['received', 'is_received', 'isReceived'], false)),
  }
}

export async function withApiFallback<T>(
  label: string,
  apiCall: () => Promise<T>,
  fallback: () => T | Promise<T>
) {
  try {
    return await apiCall()
  } catch (error) {
    console.warn(`[api fallback] ${label}`, error)
    return fallback()
  }
}

export function buildChargingSessionFromOrder(order: OrderDetailItem): ChargingSession {
  const elapsed =
    typeof order.elapsedMinutes === 'number' && order.elapsedMinutes >= 0
      ? order.elapsedMinutes
      : order.endTime !== '--'
        ? diffMinutes(order.startTime, order.endTime)
        : 0

  return {
    orderId: order.id,
    orderNo: order.orderNo,
    stationId: order.stationId,
    stationName: order.stationName,
    pileNo: order.pileNo,
    gunNo: order.gunNo,
    startedAt: order.startTime,
    durationMinutes: elapsed,
    currentBattery: order.batteryPercent,
    currentPower: order.currentPowerValue,
    currentFee: order.totalAmountValue,
    energy: order.energyValue,
    electricityFee: order.electricityFeeValue,
    serviceFee: order.serviceFeeValue,
    discountFee: order.discountFeeValue,
    priceNote: '数据来自平台订单接口，随轮询刷新。',
  }
}

export async function getMiniHealth() {
  const payload = await get<unknown>('/health')
  const source = toRecord(payload)
  return {
    ok: Boolean(pickValue(source, ['ok', 'healthy'], true)),
    message: String(pickValue(source, ['message', 'status'], 'ok')),
    timestamp: String(pickValue(source, ['timestamp', 'time'], '')),
  } as MiniHealth
}

export async function getStations() {
  const payload = await get<unknown>('/stations')
  return listFromResponse<unknown>(payload).map(item => mapStation(item))
}

export async function getRecommendStations() {
  const payload = await get<unknown>('/stations/recommend')
  return listFromResponse<unknown>(payload).map(item => mapStation(item))
}

export async function getStationDetail(stationId: string) {
  const payload = await get<unknown>(`/stations/${stationId}`)
  return mapStation(payload)
}

export async function getChargerBySn(snCode: string) {
  const payload = await get<unknown>('/chargers/by-sn', { sn_code: snCode })
  const source = toRecord(payload)
  const charger = toRecord(pickValue(source, ['charger', 'data'], source))
  const station = toRecord(pickValue(source, ['station'], {}))
  const rawStatus = String(pickValue(charger, ['status', 'charger_status', 'state'], '') || '')
  const status = derivePileStatus(
    rawStatus,
    Boolean(pickValue(charger, ['available', 'is_available', 'isAvailable'], false))
  )

  return {
    id: toId(pickValue(charger, ['id', 'charger_id', 'chargerId', 'sn_code', 'snCode'], snCode)),
    stationId: toId(
      pickValue(charger, ['station_id', 'stationId'], pickValue(station, ['id', 'station_id'], ''))
    ),
    stationName: String(
      pickValue(
        charger,
        ['station_name', 'stationName'],
        pickValue(station, ['station_name', 'stationName', 'name'], '')
      )
    ),
    pileNo: String(pickValue(charger, ['pile_no', 'pileNo', 'sn_code', 'snCode'], snCode)),
    snCode: String(pickValue(charger, ['sn_code', 'snCode', 'pile_no', 'pileNo'], snCode)),
    gunNo: String(pickValue(charger, ['gun_no', 'gunNo'], 'Gun 1')),
    available: status === 'idle',
    status,
    statusText: String(pickValue(charger, ['status_text', 'statusText'], buildPileStatusText(status))),
    power: String(pickValue(charger, ['power', 'power_kw', 'powerKw'], '--')),
    connector: String(pickValue(charger, ['connector', 'connector_type'], 'GBT DC')),
  } as ChargerLookupResult
}

export async function startOrder(payload: StartOrderPayload) {
  if (getStoredUser()?.id == null) {
    throw new Error('请先登录后再发起充电')
  }
  const response = await post<unknown, StartOrderPayload>('/orders/start', payload)
  return mapOrder(response)
}

export async function finishOrder(orderId: string) {
  if (getStoredUser()?.id == null) {
    throw new Error('请先登录')
  }
  const response = await post<unknown, { order_id: string }>('/orders/end', { order_id: orderId })
  return mapOrder(response)
}

export async function getOrders() {
  if (getStoredUser()?.id == null) {
    return []
  }
  const payload = await get<unknown>('/orders/my')
  return listFromResponse<unknown>(payload).map(item => mapOrder(item))
}

export async function getOrderDetail(orderId: string) {
  if (getStoredUser()?.id == null) {
    throw new Error('请先登录')
  }
  const payload = await get<unknown>(`/orders/${orderId}`)
  return mapOrder(payload)
}

export async function getWalletSummary() {
  if (getStoredUser()?.id == null) {
    const balance = getStoredBalance()
    return {
      balance,
      balanceText: balance.toFixed(2),
      couponCount: 0,
    }
  }
  const payload = await get<unknown>('/wallet')
  return mapWalletSummary(payload)
}

export async function getWalletTransactions() {
  if (getStoredUser()?.id == null) {
    return []
  }
  const payload = await get<unknown>('/wallet/transactions')
  return listFromResponse<unknown>(payload).map(item => mapWalletRecord(item))
}

/** 写入 trade_wallet_transactions，与后台钱包余额一致 */
export async function rechargeWalletApi(amount: number) {
  if (getStoredUser()?.id == null) {
    throw new Error('请先登录')
  }
  const payload = await post<unknown, { amount: number }>('/wallet/recharge', { amount })
  return mapWalletSummary(payload)
}

export async function applyInvoice(payload: ApplyInvoicePayload) {
  if (getStoredUser()?.id == null) {
    throw new Error('请先登录')
  }
  const response = await post<unknown, ApplyInvoicePayload>('/invoices/apply', payload)
  return mapInvoiceRecord(response)
}

export async function getInvoiceRecords() {
  if (getStoredUser()?.id == null) {
    return []
  }
  const payload = await get<unknown>('/invoices')
  return listFromResponse<unknown>(payload).map(item => mapInvoiceRecord(item))
}

export async function getCoupons() {
  const payload = await get<unknown>('/coupons')
  return listFromResponse<unknown>(payload).map(item => mapCoupon(item))
}

export async function receiveCoupon(couponId: string) {
  const response = await post<unknown, { coupon_id: string }>(`/coupons/${couponId}/receive`, {
    coupon_id: couponId,
  })
  return mapCoupon(response)
}
