import { getStoredBalance, setStoredBalance } from '../utils/storage'

export interface PricePeriod {
  label: string,
  time: string,
  price: string
}

export interface StationPile {
  id: string,
  label: string,
  power: string,
  connector: string,
  status: 'idle' | 'busy' | 'fault',
  statusText: string,
  queueText: string
}

export interface StationItem {
  id: string,
  name: string,
  address: string,
  operator: string,
  statusKey: 'idle' | 'busy' | 'queue',
  available: number,
  total: number,
  distance: string,
  distanceValue: number,
  statusText: string,
  businessHours: string,
  parkingTips: string,
  serviceTips: string,
  currentPriceText: string,
  currentPriceValue: number,
  score: string,
  reviewCount: number,
  tags: string[],
  serviceTags: string[],
  recommendReasons: string[],
  chargeType: '快充优先' | '快慢结合' | '慢充服务',
  fastCount: number,
  slowCount: number,
  favorite: boolean,
  announcement: string,
  priceBreakdown: PricePeriod[],
  piles: StationPile[]
}

export interface PromotionCard {
  id: string,
  title: string,
  desc: string,
  tag: string,
  couponValue: string,
  expireText: string
}

export interface WalletRecord {
  id: string,
  title: string,
  time: string,
  amountText: string,
  type: 'income' | 'expense'
  category: 'recharge' | 'consume',
  channel: string,
  description: string
}

export type OrderStatus = 'charging' | 'completed' | 'abnormal'

export interface OrderItem {
  id: string,
  orderNo: string,
  stationId: string,
  stationName: string,
  pileNo: string,
  gunNo: string,
  startTime: string,
  endTime: string,
  durationText: string,
  powerText: string,
  amountText: string,
  amountValue: number,
  payableText: string,
  discountText: string,
  discountValue: number,
  status: OrderStatus,
  statusText: string,
  paymentStatusText: string,
  invoiceStatusText: string,
  canInvoice: boolean,
  canChargeAgain: boolean,
  abnormalReason: string
}

export interface InvoiceRecord {
  id: string,
  orderId: string,
  orderNo: string,
  typeText: string,
  title: string,
  email: string,
  amountText: string,
  status: 'pending' | 'issued' | 'rejected',
  statusText: string,
  applyTime: string,
  note: string,
  attachmentName: string,
  progressText: string,
  rejectReason: string
}

export interface ChargingSession {
  orderId: string,
  orderNo: string,
  stationId: string,
  stationName: string,
  pileNo: string,
  gunNo: string,
  startedAt: string,
  durationMinutes: number,
  currentBattery: number,
  currentPower: number,
  currentFee: number,
  energy: number,
  electricityFee: number,
  serviceFee: number,
  discountFee: number,
  priceNote: string
}

const ORDERS_KEY = 'echarge_orders'
const INVOICES_KEY = 'echarge_invoices'
const WALLET_RECORDS_KEY = 'echarge_wallet_records'
const CHARGING_SESSION_KEY = 'echarge_charging_session'
const USERS_KEY = 'echarge_users'
const DEFAULT_BALANCE = 286.5

const STATIONS: StationItem[] = [
  {
    id: 'station-001',
    name: '天府软件园综合充电站',
    address: '成都市高新区天府五街 200 号地下停车场 B1',
    operator: 'E-Charge 自营',
    statusKey: 'idle',
    available: 8,
    total: 12,
    distance: '1.2km',
    distanceValue: 1.2,
    statusText: '空闲充足',
    businessHours: '00:00 - 24:00',
    parkingTips: '停车 2 小时内免费，支持新能源专属车位',
    serviceTips: '便利店 / 洗手间 / 休息区 / 地下电梯',
    currentPriceText: '当前电价 ￥1.42/度',
    currentPriceValue: 1.42,
    score: '4.9',
    reviewCount: 268,
    tags: ['快充', '停车便利', '24 小时'],
    serviceTags: ['距离最近', '夜间优惠', '常用站点'],
    recommendReasons: ['距离最近', '空闲较多', '夜间优惠'],
    chargeType: '快充优先',
    fastCount: 8,
    slowCount: 4,
    favorite: true,
    announcement: '晚间 20:00 后服务费优惠，站内支持电子导航定位。',
    priceBreakdown: [
      { label: '峰时', time: '10:00 - 15:00', price: '￥1.78/度' },
      { label: '平时', time: '07:00 - 10:00 / 15:00 - 20:00', price: '￥1.42/度' },
      { label: '谷时', time: '20:00 - 次日 07:00', price: '￥1.18/度' },
    ],
    piles: [
      { id: 'TF-01', label: 'A1 号枪', power: '120kW', connector: '国标直流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
      { id: 'TF-02', label: 'A2 号枪', power: '120kW', connector: '国标直流', status: 'idle', statusText: '空闲', queueText: '推荐使用' },
      { id: 'TF-03', label: 'B1 号枪', power: '60kW', connector: '国标直流', status: 'busy', statusText: '充电中', queueText: '预计 12 分钟可用' },
      { id: 'TF-04', label: 'B2 号枪', power: '60kW', connector: '国标交流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
    ],
  },
  {
    id: 'station-002',
    name: '环球中心北广场充电站',
    address: '成都市高新区天府大道北段 1700 号 P2 停车区',
    operator: '特来电',
    statusKey: 'busy',
    available: 3,
    total: 8,
    distance: '2.6km',
    distanceValue: 2.6,
    statusText: '部分繁忙',
    businessHours: '07:00 - 23:00',
    parkingTips: '商场高峰时段车位紧张，建议错峰前往',
    serviceTips: '商场配套 / 咖啡店 / 休息区 / 地图导航',
    currentPriceText: '当前电价 ￥1.55/度',
    currentPriceValue: 1.55,
    score: '4.7',
    reviewCount: 196,
    tags: ['商圈站点', '快充', '导航便捷'],
    serviceTags: ['高评分', '商圈补能', '停车方便'],
    recommendReasons: ['购物补能', '快充优先', '服务稳定'],
    chargeType: '快慢结合',
    fastCount: 5,
    slowCount: 3,
    favorite: false,
    announcement: '周末 11:00 - 18:00 为高峰时段，建议提前查看空闲状态。',
    priceBreakdown: [
      { label: '峰时', time: '11:00 - 16:00', price: '￥1.88/度' },
      { label: '平时', time: '08:00 - 11:00 / 16:00 - 21:00', price: '￥1.55/度' },
      { label: '谷时', time: '21:00 - 次日 08:00', price: '￥1.26/度' },
    ],
    piles: [
      { id: 'HQ-11', label: 'C1 号枪', power: '180kW', connector: '国标直流', status: 'busy', statusText: '充电中', queueText: '预计 18 分钟可用' },
      { id: 'HQ-12', label: 'C2 号枪', power: '180kW', connector: '国标直流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
      { id: 'HQ-13', label: 'D1 号枪', power: '90kW', connector: '国标直流', status: 'fault', statusText: '设备维护', queueText: '暂停服务' },
      { id: 'HQ-14', label: 'D2 号枪', power: '90kW', connector: '国标交流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
    ],
  },
  {
    id: 'station-003',
    name: '东客站出行服务充电站',
    address: '成都市成华区迎晖路 8 号东广场停车楼 1 层',
    operator: '星星充电',
    statusKey: 'idle',
    available: 5,
    total: 10,
    distance: '3.8km',
    distanceValue: 3.8,
    statusText: '空闲充足',
    businessHours: '06:30 - 23:30',
    parkingTips: '支持网约车优先排队，站内引导清晰',
    serviceTips: '候车区 / 自动售货机 / 站内客服 / 卫生间',
    currentPriceText: '当前电价 ￥1.36/度',
    currentPriceValue: 1.36,
    score: '4.8',
    reviewCount: 143,
    tags: ['交通枢纽', '普通充电', '服务完善'],
    serviceTags: ['价格友好', '空闲较多', '适合长停'],
    recommendReasons: ['价格优先', '空闲较多', '交通枢纽'],
    chargeType: '快慢结合',
    fastCount: 4,
    slowCount: 6,
    favorite: false,
    announcement: '站点支持车辆长停补能，请按引导有序驶入车位。',
    priceBreakdown: [
      { label: '峰时', time: '09:00 - 14:00', price: '￥1.62/度' },
      { label: '平时', time: '07:00 - 09:00 / 14:00 - 20:00', price: '￥1.36/度' },
      { label: '谷时', time: '20:00 - 次日 07:00', price: '￥1.08/度' },
    ],
    piles: [
      { id: 'DK-21', label: 'E1 号枪', power: '90kW', connector: '国标直流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
      { id: 'DK-22', label: 'E2 号枪', power: '90kW', connector: '国标直流', status: 'busy', statusText: '充电中', queueText: '预计 8 分钟可用' },
      { id: 'DK-23', label: 'F1 号枪', power: '60kW', connector: '国标交流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
      { id: 'DK-24', label: 'F2 号枪', power: '60kW', connector: '国标交流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
    ],
  },
  {
    id: 'station-004',
    name: '金融城商务区充电站',
    address: '成都市高新区交子大道 333 号 A 座地下停车场',
    operator: 'E-Charge 合作站',
    statusKey: 'queue',
    available: 2,
    total: 6,
    distance: '4.5km',
    distanceValue: 4.5,
    statusText: '高峰排队',
    businessHours: '00:00 - 24:00',
    parkingTips: '工作日午间高峰排队较多，建议提前查看空闲枪口',
    serviceTips: '商务配套 / 代客泊车 / 保安值守 / 洗车服务',
    currentPriceText: '当前电价 ￥1.68/度',
    currentPriceValue: 1.68,
    score: '4.6',
    reviewCount: 127,
    tags: ['商务区', '高峰时段', '24 小时'],
    serviceTags: ['企业常用', '车位紧张', '高峰排队'],
    recommendReasons: ['商务区补能', '全天营业', '企业用户常用'],
    chargeType: '快充优先',
    fastCount: 4,
    slowCount: 2,
    favorite: true,
    announcement: '工作日午间 11:30 - 14:00 为高峰时段，请遵守排队秩序。',
    priceBreakdown: [
      { label: '峰时', time: '11:30 - 14:00', price: '￥1.96/度' },
      { label: '平时', time: '08:00 - 11:30 / 14:00 - 20:00', price: '￥1.68/度' },
      { label: '谷时', time: '20:00 - 次日 08:00', price: '￥1.32/度' },
    ],
    piles: [
      { id: 'JR-31', label: 'G1 号枪', power: '120kW', connector: '国标直流', status: 'busy', statusText: '充电中', queueText: '预计 20 分钟可用' },
      { id: 'JR-32', label: 'G2 号枪', power: '120kW', connector: '国标直流', status: 'busy', statusText: '充电中', queueText: '预计 26 分钟可用' },
      { id: 'JR-33', label: 'H1 号枪', power: '60kW', connector: '国标交流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
      { id: 'JR-34', label: 'H2 号枪', power: '60kW', connector: '国标交流', status: 'idle', statusText: '空闲', queueText: '到站可用' },
    ],
  },
]

const PROMOTIONS: PromotionCard[] = [
  {
    id: 'promo-01',
    title: '首充礼包已到账',
    desc: '钱包首次充值满 100 元，可领取 12 元充电券，适用于合作快充站点。',
    tag: '新人福利',
    couponValue: '￥12',
    expireText: '有效期至 05-31',
  },
  {
    id: 'promo-02',
    title: '夜间充电服务费 8 折',
    desc: '每周五至周日 20:00 后生效，夜间补能更划算。',
    tag: '限时优惠',
    couponValue: '8 折',
    expireText: '每周末可用',
  },
  {
    id: 'promo-03',
    title: '常用站点满减券',
    desc: '近 30 天累计充电 3 次，可领取常用站点专属满减权益。',
    tag: '会员权益',
    couponValue: '满 30 减 6',
    expireText: '自动发放',
  },
]

const DEFAULT_WALLET_RECORDS: WalletRecord[] = [
  {
    id: 'wallet-001',
    title: '钱包充值',
    time: '2026-04-18 20:15',
    amountText: '+100.00',
    type: 'income',
    category: 'recharge',
    channel: '微信支付',
    description: '充值到账',
  },
  {
    id: 'wallet-002',
    title: '天府软件园综合充电站',
    time: '2026-04-18 22:02',
    amountText: '-46.80',
    type: 'expense',
    category: 'consume',
    channel: '充电消费',
    description: '订单结算',
  },
  {
    id: 'wallet-003',
    title: '东客站出行服务充电站',
    time: '2026-04-16 18:26',
    amountText: '-28.40',
    type: 'expense',
    category: 'consume',
    channel: '充电消费',
    description: '订单结算',
  },
]

const DEFAULT_ORDERS: OrderItem[] = [
  {
    id: 'order-001',
    orderNo: 'EC202604180001',
    stationId: 'station-001',
    stationName: '天府软件园综合充电站',
    pileNo: 'TF-02',
    gunNo: '1 号枪',
    startTime: '2026-04-18 21:08',
    endTime: '2026-04-18 22:02',
    durationText: '54 分钟',
    powerText: '31.8 kWh',
    amountText: '46.80',
    amountValue: 46.8,
    payableText: '46.80',
    discountText: '优惠抵扣 ￥6.00',
    discountValue: 6,
    status: 'completed',
    statusText: '已完成',
    paymentStatusText: '已支付',
    invoiceStatusText: '可开票',
    canInvoice: true,
    canChargeAgain: true,
    abnormalReason: '',
  },
  {
    id: 'order-002',
    orderNo: 'EC202604170001',
    stationId: 'station-003',
    stationName: '东客站出行服务充电站',
    pileNo: 'DK-21',
    gunNo: '2 号枪',
    startTime: '2026-04-17 17:35',
    endTime: '2026-04-17 18:26',
    durationText: '51 分钟',
    powerText: '22.4 kWh',
    amountText: '28.40',
    amountValue: 28.4,
    payableText: '28.40',
    discountText: '未使用优惠',
    discountValue: 0,
    status: 'completed',
    statusText: '已完成',
    paymentStatusText: '已支付',
    invoiceStatusText: '待处理',
    canInvoice: true,
    canChargeAgain: true,
    abnormalReason: '',
  },
  {
    id: 'order-003',
    orderNo: 'EC202604150001',
    stationId: 'station-004',
    stationName: '金融城商务区充电站',
    pileNo: 'JR-31',
    gunNo: '1 号枪',
    startTime: '2026-04-15 09:20',
    endTime: '2026-04-15 09:33',
    durationText: '13 分钟',
    powerText: '8.6 kWh',
    amountText: '12.60',
    amountValue: 12.6,
    payableText: '12.60',
    discountText: '优惠抵扣 ￥2.00',
    discountValue: 2,
    status: 'abnormal',
    statusText: '异常中断',
    paymentStatusText: '已结算',
    invoiceStatusText: '不可开票',
    canInvoice: false,
    canChargeAgain: true,
    abnormalReason: '连接中断，系统已按实际电量结算',
  },
]

const DEFAULT_INVOICES: InvoiceRecord[] = [
  {
    id: 'invoice-001',
    orderId: 'order-001',
    orderNo: 'EC202604180001',
    typeText: '电子普通发票',
    title: '成都智行科技有限公司',
    email: 'finance@echarge.com',
    amountText: '46.80',
    status: 'issued',
    statusText: '已开票',
    applyTime: '2026-04-18 22:10',
    note: '用于企业差旅报销',
    attachmentName: '电子发票-EC202604180001.pdf',
    progressText: '发票已开具，可在线查看附件',
    rejectReason: '',
  },
  {
    id: 'invoice-002',
    orderId: 'order-002',
    orderNo: 'EC202604170001',
    typeText: '电子普通发票',
    title: '个人',
    email: 'user@foxmail.com',
    amountText: '28.40',
    status: 'pending',
    statusText: '待处理',
    applyTime: '2026-04-17 18:40',
    note: '请开具电子普通发票',
    attachmentName: '待生成',
    progressText: '财务系统处理中，预计 1 个工作日内完成',
    rejectReason: '',
  },
]

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function hasStorageKey(key: string) {
  try {
    return wx.getStorageInfoSync().keys.includes(key)
  } catch {
    return false
  }
}

function getStorageData<T>(key: string, fallback: T): T {
  try {
    const value = wx.getStorageSync(key)
    if (value === '' || value === undefined || value === null) {
      return clone(fallback)
    }
    return clone(value as T)
  } catch {
    return clone(fallback)
  }
}

function setStorageData<T>(key: string, value: T) {
  wx.setStorageSync(key, value)
}

function pad(value: number) {
  return String(value).padStart(2, '0')
}

export function formatDateTime(input: Date) {
  const year = input.getFullYear()
  const month = pad(input.getMonth() + 1)
  const day = pad(input.getDate())
  const hour = pad(input.getHours())
  const minute = pad(input.getMinutes())
  return `${year}-${month}-${day} ${hour}:${minute}`
}

export function formatDuration(minutes: number) {
  if (minutes < 60) {
    return `${minutes} 分钟`
  }
  const hour = Math.floor(minutes / 60)
  const minute = minutes % 60
  return `${hour} 小时 ${minute} 分钟`
}

function formatAmount(value: number) {
  return value.toFixed(2)
}

function buildOrderNo() {
  const now = new Date()
  return `EC${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(
    now.getHours()
  )}${pad(now.getMinutes())}${pad(now.getSeconds())}`
}

function buildId(prefix: string) {
  return `${prefix}-${Date.now()}`
}

export function initializeAppState() {
  if (!hasStorageKey(USERS_KEY)) {
    wx.setStorageSync(USERS_KEY, {
      'user@echarge.com': {
        id: 1,
        nickname: '车主用户',
        email: 'user@echarge.com',
        password: '123456',
      },
      '13800138000': {
        id: 1,
        nickname: '车主用户',
        email: 'user@echarge.com',
        password: '123456',
      },
    })
  }

  if (!hasStorageKey(WALLET_RECORDS_KEY)) {
    setStorageData(WALLET_RECORDS_KEY, DEFAULT_WALLET_RECORDS)
  }

  if (!hasStorageKey(ORDERS_KEY)) {
    setStorageData(ORDERS_KEY, DEFAULT_ORDERS)
  }

  if (!hasStorageKey(INVOICES_KEY)) {
    setStorageData(INVOICES_KEY, DEFAULT_INVOICES)
  }

  if (!hasStorageKey('echarge_balance')) {
    setStoredBalance(DEFAULT_BALANCE)
  }
}

export function getStations() {
  return clone(STATIONS)
}

export function getRecommendedStations() {
  return clone([STATIONS[0], STATIONS[1], STATIONS[2]])
}

export function getStationById(id: string) {
  return clone(STATIONS.find(item => item.id === id) || STATIONS[0])
}

export function getPromotions() {
  return clone(PROMOTIONS)
}

export function getWalletRecords() {
  return getStorageData(WALLET_RECORDS_KEY, DEFAULT_WALLET_RECORDS)
}

export function getOrders() {
  return getStorageData(ORDERS_KEY, DEFAULT_ORDERS)
}

function saveOrders(orders: OrderItem[]) {
  setStorageData(ORDERS_KEY, orders)
}

export function getOrderById(id: string) {
  const orders = getOrders()
  return orders.find(item => item.id === id) || null
}

export function getLatestCompletedOrder() {
  const orders = getOrders()
  return orders.find(item => item.status === 'completed') || orders[0] || null
}

export function getInvoices() {
  return getStorageData(INVOICES_KEY, DEFAULT_INVOICES)
}

function saveInvoices(invoices: InvoiceRecord[]) {
  setStorageData(INVOICES_KEY, invoices)
}

export function findInvoiceByOrderId(orderId: string) {
  return getInvoices().find(item => item.orderId === orderId) || null
}

export function getChargingSession() {
  return getStorageData<ChargingSession | null>(CHARGING_SESSION_KEY, null)
}

function saveChargingSession(session: ChargingSession) {
  setStorageData(CHARGING_SESSION_KEY, session)
}

export function clearChargingSession() {
  wx.removeStorageSync(CHARGING_SESSION_KEY)
}

export function rechargeWallet(amount: number) {
  const nextBalance = Number((getStoredBalance() + amount).toFixed(2))
  setStoredBalance(nextBalance)

  const records = getWalletRecords()
  records.unshift({
    id: buildId('wallet'),
    title: '钱包充值',
    time: formatDateTime(new Date()),
    amountText: `+${formatAmount(amount)}`,
    type: 'income',
    category: 'recharge',
    channel: '微信支付',
    description: '余额充值',
  })
  setStorageData(WALLET_RECORDS_KEY, records)

  return nextBalance
}

export function createChargingSession(stationId?: string, pileNo?: string) {
  const station = getStationById(stationId || STATIONS[0].id)
  const actualPileNo = pileNo || station.piles[0].id
  const orderId = buildId('order')
  const orderNo = buildOrderNo()
  const startedAt = formatDateTime(new Date())

  const session: ChargingSession = {
    orderId,
    orderNo,
    stationId: station.id,
    stationName: station.name,
    pileNo: actualPileNo,
    gunNo: '1 号枪',
    startedAt,
    durationMinutes: 8,
    currentBattery: 32,
    currentPower: 38,
    currentFee: 6.8,
    energy: 5.4,
    electricityFee: 4.6,
    serviceFee: 2.8,
    discountFee: 0.6,
    priceNote: '当前按平时段电价计费，夜间时段可享服务费优惠。',
  }

  const orders = getOrders()
  orders.unshift({
    id: orderId,
    orderNo,
    stationId: station.id,
    stationName: station.name,
    pileNo: actualPileNo,
    gunNo: '1 号枪',
    startTime: startedAt,
    endTime: '--',
    durationText: '进行中',
    powerText: '5.4 kWh',
    amountText: '6.80',
    amountValue: 6.8,
    payableText: '6.80',
    discountText: '优惠抵扣 ￥0.60',
    discountValue: 0.6,
    status: 'charging',
    statusText: '充电中',
    paymentStatusText: '待结算',
    invoiceStatusText: '充电完成后可开票',
    canInvoice: false,
    canChargeAgain: false,
    abnormalReason: '',
  })

  saveOrders(orders)
  saveChargingSession(session)
  return session
}

export function updateChargingSessionSnapshot(session: ChargingSession) {
  saveChargingSession(session)

  const orders = getOrders().map(item =>
    item.id === session.orderId
      ? {
          ...item,
          durationText: formatDuration(session.durationMinutes),
          powerText: `${session.energy.toFixed(1)} kWh`,
          amountText: formatAmount(session.currentFee),
          amountValue: session.currentFee,
          payableText: formatAmount(session.currentFee),
          discountText: `优惠抵扣 ￥${session.discountFee.toFixed(2)}`,
        }
      : item
  )
  saveOrders(orders)
}

export function completeChargingSession(session: ChargingSession) {
  const completedAt = formatDateTime(new Date())
  const completedOrder: OrderItem = {
    id: session.orderId,
    orderNo: session.orderNo,
    stationId: session.stationId,
    stationName: session.stationName,
    pileNo: session.pileNo,
    gunNo: session.gunNo,
    startTime: session.startedAt,
    endTime: completedAt,
    durationText: formatDuration(session.durationMinutes),
    powerText: `${session.energy.toFixed(1)} kWh`,
    amountText: formatAmount(session.currentFee),
    amountValue: session.currentFee,
    payableText: formatAmount(session.currentFee),
    discountText: `优惠抵扣 ￥${session.discountFee.toFixed(2)}`,
    discountValue: session.discountFee,
    status: 'completed',
    statusText: '已完成',
    paymentStatusText: '已支付',
    invoiceStatusText: '可开票',
    canInvoice: true,
    canChargeAgain: true,
    abnormalReason: '',
  }

  const orders = getOrders().map(item => (item.id === session.orderId ? completedOrder : item))
  saveOrders(orders)

  const nextBalance = Number(Math.max(getStoredBalance() - session.currentFee, 0).toFixed(2))
  setStoredBalance(nextBalance)

  const records = getWalletRecords()
  records.unshift({
    id: buildId('wallet'),
    title: session.stationName,
    time: completedAt,
    amountText: `-${formatAmount(session.currentFee)}`,
    type: 'expense',
    category: 'consume',
    channel: '充电消费',
    description: '订单结算',
  })
  setStorageData(WALLET_RECORDS_KEY, records)
  clearChargingSession()

  return completedOrder
}

export function createInvoiceApplication(options: {
  orderId: string,
  title: string,
  email: string,
  note: string
}) {
  const order = getOrderById(options.orderId)
  if (!order) {
    return null
  }

  const existing = findInvoiceByOrderId(options.orderId)
  if (existing) {
    return existing
  }

  const record: InvoiceRecord = {
    id: buildId('invoice'),
    orderId: order.id,
    orderNo: order.orderNo,
    typeText: '电子普通发票',
    title: options.title,
    email: options.email,
    amountText: order.amountText,
    status: 'pending',
    statusText: '待处理',
    applyTime: formatDateTime(new Date()),
    note: options.note || '电子普通发票',
    attachmentName: '待生成',
    progressText: '申请已提交，财务系统审核中',
    rejectReason: '',
  }

  const invoices = getInvoices()
  invoices.unshift(record)
  saveInvoices(invoices)
  return record
}
