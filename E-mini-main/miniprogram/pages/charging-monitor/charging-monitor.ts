/**
 * 充电监控页。
 *
 * 优先使用后端实时充电模拟接口（GET /charging/status/{id}）轮询，
 * 后端不可达时退化为本地模拟。
 */

import { buildChargingSessionFromOrder, getOrderDetail, getWalletSummary } from '../../services/api'
import { finishOrder as apiFinishOrder } from '../../services/api'
import { get } from '../../services/request'
import {
  ChargingSession,
  clearChargingSession,
  completeChargingSession,
  createChargingSession,
  formatDuration,
  getChargingSession,
  getOrderById,
  updateChargingSessionSnapshot,
} from '../../services/mock'
import { getStoredBalance, getUserId } from '../../utils/storage'

const app = getApp<IAppOption>()
let monitorTimer = 0
const POLL_MS = 3000

/* ==================== 后端实时充电模拟 ==================== */

interface RealChargingData {
  charging: boolean,
  finished: boolean,
  elapsed: number,
  soc: number,
  power: number,
  fee: number,
  energy: number,
  eleFee: number,
  serviceFee: number,
  statusText: string
}

/**
 * 调用后端 GET /charging/status/{id}。
 * request.ts 已经解过一次 envlope，payload 直接是 data 字段的内容。
 */
async function fetchChargingStatus(orderId: string): Promise<RealChargingData | null> {
  try {
    const data = await get<Record<string, unknown>>(`/charging/status/${orderId}`)
    if (!data) return null

    if (data.charging === true) {
      return {
        charging: true,
        finished: false,
        elapsed: Number(data.elapsed_minutes ?? 0),
        soc: Number(data.current_soc ?? 0),
        power: Number(data.current_power_kw ?? 0),
        fee: Number(data.total_fee ?? 0),
        energy: Number(data.total_kwh ?? 0),
        eleFee: Number(data.electricity_fee ?? 0),
        serviceFee: Number(data.service_fee ?? 0),
        statusText: String(data.status_text ?? 'Charging'),
      }
    }

    if (data.finished === true) {
      return { charging: false, finished: true } as RealChargingData
    }

    return null
  } catch {
    return null
  }
}

/* ==================== 本地后备模拟 ==================== */

function localSimulateSession(session: ChargingSession): ChargingSession {
  session.durationMinutes += 1
  session.currentBattery = Math.min(session.currentBattery + 1, 96)
  session.currentPower = 38
  session.currentFee = session.energy * 1.18
  session.energy += 0.2
  session.electricityFee = session.energy * 0.72
  session.serviceFee = session.energy * 0.46
  session.priceNote = '本地演示模式'
  return session
}

function getSavedSessionOrDefault(orderId: string): ChargingSession | null {
  const currentSession = getChargingSession()
  if (currentSession && (!orderId || currentSession.orderId === orderId)) {
    return currentSession
  }

  const fallbackOrder = orderId ? getOrderById(orderId) : null
  if (fallbackOrder) {
    const powerVal = Number(fallbackOrder.powerText.replace(/[^\d.]/g, '')) || 0
    return {
      orderId: fallbackOrder.id,
      orderNo: fallbackOrder.orderNo,
      stationId: fallbackOrder.stationId,
      stationName: fallbackOrder.stationName,
      pileNo: fallbackOrder.pileNo,
      gunNo: fallbackOrder.gunNo,
      startedAt: fallbackOrder.startTime,
      durationMinutes: 0,
      currentBattery: 25,
      currentPower: 38,
      currentFee: powerVal * 1.5,
      energy: powerVal,
      electricityFee: 0,
      serviceFee: 0,
      discountFee: fallbackOrder.discountValue,
      priceNote: '本地演示模式',
    }
  }

  return null
}

/* ==================== 页面显示 ==================== */

function buildDisplayState(session: ChargingSession, statusText: string) {
  return {
    orderId: session.orderId,
    orderNo: session.orderNo,
    stationId: session.stationId,
    stationName: session.stationName,
    pileNo: session.pileNo,
    gunNo: session.gunNo,
    startedAt: session.startedAt,
    durationMinutes: session.durationMinutes,
    durationText: formatDuration(session.durationMinutes),
    batteryText: `${session.currentBattery}%`,
    progressPercent: `${Math.min(session.currentBattery, 96)}%`,
    powerText: `${session.currentPower.toFixed(0)} kW`,
    feeText: session.currentFee.toFixed(2),
    energyText: `${session.energy.toFixed(1)} kWh`,
    electricityFeeText: session.electricityFee.toFixed(2),
    serviceFeeText: session.serviceFee.toFixed(2),
    discountFeeText: session.discountFee.toFixed(2),
    priceNote: session.priceNote,
    statusText,
  }
}

Page({
  data: {
    orderId: '',
    orderNo: '',
    stationId: '',
    stationName: '',
    pileNo: '',
    gunNo: '',
    startedAt: '',
    durationMinutes: 0,
    durationText: '0 min',
    batteryText: '0%',
    progressPercent: '0%',
    powerText: '0 kW',
    feeText: '0.00',
    energyText: '0.0 kWh',
    electricityFeeText: '0.00',
    serviceFeeText: '0.00',
    discountFeeText: '0.00',
    priceNote: '',
    statusText: '充电中',
    /** 是否正在使用后端实时数据 */
    backendOnline: false,
  },

  async onLoad(options: Record<string, string | undefined>) {
    const orderId = options.orderId || ''
    if (!orderId) {
      wx.showToast({ title: '订单 ID 缺失', icon: 'none' })
      return
    }

    let session: ChargingSession
    let statusText = '充电中'
    const uid = getUserId()

    if (orderId && uid != null) {
      try {
        // 从后端获取初始订单数据，用 buildChargingSessionFromOrder 构建完整会话
        const order = await getOrderDetail(orderId)

        if (order.status !== 'charging') {
          wx.redirectTo({ url: `/pages/charging-result/charging-result?orderId=${orderId}` })
          return
        }

        session = buildChargingSessionFromOrder(order)
        this.data.backendOnline = true
      } catch {
        const saved = getSavedSessionOrDefault(orderId)
        session = saved ?? createChargingSession(undefined, orderId)
        this.data.backendOnline = false
      }
    } else {
      const saved = getSavedSessionOrDefault(orderId)
      session = saved ?? createChargingSession(undefined, orderId)
      this.data.backendOnline = false
    }

    updateChargingSessionSnapshot(session)
    this.setData(buildDisplayState(session, statusText))
    this.startMonitor()
  },

  onUnload() {
    if (monitorTimer) {
      clearInterval(monitorTimer)
      monitorTimer = 0
    }
  },

  startMonitor() {
    if (monitorTimer) clearInterval(monitorTimer)
    monitorTimer = setInterval(() => this.syncOrderFromServer(), POLL_MS)
    this.syncOrderFromServer()
  },

  /** 每次轮询：先试后端实时接口，失败后回退本地模拟 */
  async syncOrderFromServer() {
    const orderId = this.data.orderId
    if (!orderId) return

    // ===== 1. 后端充电模拟接口（首选） =====
    const real = this.data.backendOnline ? await fetchChargingStatus(orderId) : null
    if (real && real.charging) {
      this.data.backendOnline = true
      const session: ChargingSession = {
        orderId,
        orderNo: this.data.orderNo,
        stationId: this.data.stationId,
        stationName: this.data.stationName,
        pileNo: this.data.pileNo,
        gunNo: this.data.gunNo,
        startedAt: this.data.startedAt,
        durationMinutes: real.elapsed,
        currentBattery: real.soc,
        currentPower: real.power,
        currentFee: real.fee,
        energy: real.energy,
        electricityFee: real.eleFee,
        serviceFee: real.serviceFee,
        discountFee: 0,
        priceNote: '充电中，数据来自平台实时接口',
      }
      updateChargingSessionSnapshot(session)
      this.setData(buildDisplayState(session, real.statusText))
      return
    }

    if (real && real.finished) {
      // 充电已完成
      if (monitorTimer) {
        clearInterval(monitorTimer)
        monitorTimer = 0
      }
      try {
        const order = await getOrderDetail(orderId)
        const session: ChargingSession = {
          orderId,
          orderNo: order.orderNo,
          stationId: order.stationId,
          stationName: order.stationName,
          pileNo: order.pileNo || orderId,
          gunNo: '1 号枪',
          startedAt: order.startTime,
          durationMinutes: 0,
          currentBattery: 96,
          currentPower: 0,
          currentFee: order.amountValue,
          energy: order.amountValue / 1.18,
          electricityFee: 0,
          serviceFee: 0,
          discountFee: order.discountValue,
          priceNote: '充电完成',
        }
        updateChargingSessionSnapshot(session)
        this.setData(buildDisplayState(session, '已完成'))
        // 自动结束回到首页
        setTimeout(() => {
          if (monitorTimer) { clearInterval(monitorTimer); monitorTimer = 0 }
          clearChargingSession()
          wx.navigateBack({ delta: 1 })
        }, 2000)
      } catch {
        if (monitorTimer) { clearInterval(monitorTimer); monitorTimer = 0 }
        clearChargingSession()
        wx.navigateBack({ delta: 1 })
      }
      return
    }

    // ===== 2. 后端订单详情接口（备选） =====
    try {
      const order = await getOrderDetail(orderId)
      if (order.status !== 'charging') {
        if (monitorTimer) {
          clearInterval(monitorTimer)
          monitorTimer = 0
        }
        const session: ChargingSession = {
          orderId,
          orderNo: order.orderNo,
          stationId: order.stationId,
          stationName: order.stationName,
          pileNo: order.pileNo || orderId,
          gunNo: '1 号枪',
          startedAt: order.startTime,
          durationMinutes: 0,
          currentBattery: 96,
          currentPower: 0,
          currentFee: order.amountValue,
          energy: order.amountValue / 1.18,
          electricityFee: 0,
          serviceFee: 0,
          discountFee: order.discountValue,
          priceNote: '已完成',
        }
        updateChargingSessionSnapshot(session)
        this.setData(buildDisplayState(session, order.statusText || '已完成'))
        return
      }
    } catch {
      // fall through to local simulation
    }

    // ===== 3. 本地模拟（兜底） =====
    const session: ChargingSession = {
      orderId: this.data.orderId,
      orderNo: this.data.orderNo,
      stationId: this.data.stationId,
      stationName: this.data.stationName,
      pileNo: this.data.pileNo,
      gunNo: this.data.gunNo,
      startedAt: this.data.startedAt,
      durationMinutes: this.data.durationMinutes + 1,
      currentBattery: Math.min(Number(this.data.batteryText.replace('%', '')) + 1, 96),
      currentPower: 38,
      currentFee: this.data.feeText ? Number(this.data.feeText) + 0.65 : 0.65,
      energy: Number(this.data.energyText.replace(' kWh', '')) + 0.3,
      electricityFee: Number(this.data.electricityFeeText),
      serviceFee: Number(this.data.serviceFeeText),
      discountFee: Number(this.data.discountFeeText),
      priceNote: '本地演示模式',
    }
    updateChargingSessionSnapshot(session)
    this.setData(buildDisplayState(session, '充电中'))
  },

  /** 手动结束充电 */
  async endCharging() {
    const currentSession: ChargingSession = {
      orderId: this.data.orderId,
      orderNo: this.data.orderNo,
      stationId: this.data.stationId,
      stationName: this.data.stationName,
      pileNo: this.data.pileNo,
      gunNo: this.data.gunNo,
      startedAt: this.data.startedAt,
      durationMinutes: this.data.durationMinutes,
      currentBattery: Number(this.data.batteryText.replace('%', '')),
      currentPower: Number(this.data.powerText.replace(' kW', '')),
      currentFee: Number(this.data.feeText),
      energy: Number(this.data.energyText.replace(' kWh', '')),
      electricityFee: Number(this.data.electricityFeeText),
      serviceFee: Number(this.data.serviceFeeText),
      discountFee: Number(this.data.discountFeeText),
      priceNote: this.data.priceNote,
    }

    wx.showLoading({ title: '结束充电中' })

    // 优先通过后端结束
    try {
      const result = await apiFinishOrder(currentSession.orderId)
      clearChargingSession()

      try {
        const walletSummary = await getWalletSummary()
        app.globalData.balance = walletSummary.balance
      } catch {
        console.warn('[charging-monitor] refresh wallet failed')
      }

      if (monitorTimer) {
        clearInterval(monitorTimer)
        monitorTimer = 0
      }

      wx.hideLoading()
      wx.navigateBack({ delta: 1 })
      return
    } catch {
      console.warn('[charging-monitor] finishOrder failed, using local mock')
    }

    // 本地兜底
    completeChargingSession(currentSession)
    app.globalData.balance = getStoredBalance()

    if (monitorTimer) {
      clearInterval(monitorTimer)
      monitorTimer = 0
    }

    wx.hideLoading()
    wx.navigateBack({ delta: 1 })
  },
})
