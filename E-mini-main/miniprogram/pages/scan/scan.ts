import {
  buildChargingSessionFromOrder,
  getChargerBySn,
  getMiniHealth,
  startOrder,
  withApiFallback,
} from '../../services/api'
import { createChargingSession, getStationById, getStations } from '../../services/mock'
import { getStoredUser, getUserId } from '../../utils/storage'
import { drawQRCode } from '../../utils/qrcode'

type ScanStatus = 'idle' | 'recognizing' | 'ready'
type ConnectionMode = 'unknown' | 'online' | 'offline'

function extractSnCode(value: string) {
  const input = value.trim()
  if (!input) {
    return ''
  }

  const matched = input.match(/sn_code=([^&]+)/i)
  if (matched?.[1]) {
    return decodeURIComponent(matched[1])
  }

  const segments = input.split(/[/?#=&\s]+/).filter(Boolean)
  return segments[segments.length - 1] || input
}

Page({
  data: {
    stationId: 'station-001',
    stationName: 'Station',
    pileNo: '',
    scanStatus: 'idle' as ScanStatus,
    scanStatusText: 'Idle',
    scanStatusClass: 'pending',
    connectionMode: 'unknown' as ConnectionMode,
    connectionText: 'Checking backend...',
    quickPiles: ['DEMO-A-CH-001', 'DEMO-A-CH-004', 'DEMO-B-CH-001'],
    recentPiles: [
      { station: '演示已审核电站A', pileNo: 'DEMO-A-CH-001' },
      { station: '演示已审核电站B', pileNo: 'DEMO-B-CH-001' },
    ],
    notices: [
      '扫描电桩二维码或手动输入 SN 编码即可开始充电',
      '如果扫描失败，可以手动输入 SN 编码或选择最近使用的电桩',
    ],
    showQRCode: false,
    qrSN: '',
    qrImagePath: '',
  },

  async onLoad(options: Record<string, string | undefined>) {
    this.restoreScanContext(options)
    await this.checkBackendConnection()
  },

  async onShow() {
    this.restoreScanContext({})
    await this.checkBackendConnection()
    if (typeof this.getTabBar === 'function') {
      const tabBar = this.getTabBar()
      if (tabBar) {
        tabBar.setData({ selected: 2 })
      }
    }
  },

  async checkBackendConnection() {
    try {
      const health = await withApiFallback(
        'scan:healthCheck',
        async () => {
          return await getMiniHealth()
        },
        () => ({ ok: false } as { ok: boolean })
      )
      if (health && health.ok === true) {
        this.setData({
          connectionMode: 'online',
          connectionText: 'Backend connected',
        })
      } else {
        this.setData({
          connectionMode: 'offline',
          connectionText: 'Backend offline, using local demo',
        })
      }
    } catch {
      this.setData({
        connectionMode: 'offline',
        connectionText: 'Backend offline, using local demo',
      })
    }
  },

  onPileInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    const nextValue = e.detail.value.trim()
    const nextStatus = nextValue ? 'ready' : 'idle'
    this.updateScanStatus(nextStatus)
    this.setData({
      pileNo: nextValue,
    })
  },

  fillQuickPile(e: WechatMiniprogram.CustomEvent) {
    const { value } = e.currentTarget.dataset as { value: string }
    this.updateScanStatus('ready')
    this.setData({
      pileNo: value,
    })
  },

  fillRecentPile(e: WechatMiniprogram.CustomEvent) {
    const { value } = e.currentTarget.dataset as { value: string }
    this.updateScanStatus('ready')
    this.setData({
      pileNo: value,
    })
  },

  onSearchPile() {
    const snCode = extractSnCode(this.data.pileNo)
    if (!snCode) {
      wx.showToast({ title: '请输入 SN 编码', icon: 'none' })
      return
    }
    void this.beginChargeFlow(snCode)
  },

  onQuickScan() {
    this.updateScanStatus('recognizing')
    wx.scanCode({
      success: ({ result }) => {
        const snCode = extractSnCode(result || '')
        this.updateScanStatus(snCode ? 'ready' : 'idle')
        this.setData({
          pileNo: snCode,
        })

        if (!snCode) {
          wx.showToast({ title: '未识别到电桩编码', icon: 'none' })
          return
        }

        void this.beginChargeFlow(snCode)
      },
      fail: () => {
        this.updateScanStatus(this.data.pileNo ? 'ready' : 'idle')
        wx.showToast({ title: '扫码已取消', icon: 'none' })
      },
    })
  },

  restoreScanContext(options: Record<string, string | undefined>) {
    const cachedContext = (wx.getStorageSync('echarge_scan_context') || {}) as {
      stationId?: string,
      pileNo?: string,
      snCode?: string
    }
    const stationId = options.stationId || cachedContext.stationId || 'station-001'
    const pileNo = options.pileNo || cachedContext.snCode || cachedContext.pileNo || this.data.pileNo
    const station = getStationById(stationId)

    this.setData({
      stationId: station.id,
      stationName: station.name,
      pileNo: pileNo || '',
    })
    this.updateScanStatus(pileNo ? 'ready' : 'idle')

    if (cachedContext.stationId || cachedContext.pileNo || cachedContext.snCode) {
      wx.removeStorageSync('echarge_scan_context')
    }
  },

  async beginChargeFlow(snCode: string) {
    if (getUserId() == null) {
      wx.showToast({ title: '请先登录', icon: 'none' })
      return
    }

    wx.showLoading({ title: '正在连接电桩...' })

    // 尝试从后端获取电桩信息
    const charger = await withApiFallback(
      'scan:getChargerBySn',
      () => getChargerBySn(snCode),
      () => ({
        id: snCode,
        stationId: this.data.stationId,
        stationName: this.data.stationName,
        pileNo: snCode,
        snCode,
        gunNo: '1 号枪',
        available: true,
        status: 'idle' as 'idle',
        statusText: '空闲',
        power: '--',
        connector: '国标直流',
      })
    )

    if (!charger.available) {
      wx.hideLoading()
      wx.showToast({
        title: charger.statusText || '电桩不可用',
        icon: 'none',
      })
      return
    }

    this.setData({
      stationId: charger.stationId || this.data.stationId,
      stationName: charger.stationName || this.data.stationName,
      pileNo: charger.snCode || charger.pileNo || snCode,
    })

    // 调用后端创建订单
    try {
      const order = await startOrder({
        sn_code: charger.snCode || snCode,
        station_id: charger.stationId || this.data.stationId,
      })

      // 后端创建成功 — 使用真实数据
      wx.setStorageSync('echarge_charging_session', buildChargingSessionFromOrder(order))
      wx.hideLoading()
      wx.navigateTo({
        url: `/pages/charging-monitor/charging-monitor?orderId=${order.id}`,
      })
    } catch (error) {
      console.warn('[scan] startOrder failed, using local demo session:', error)

      // 后端不可用 — 使用本地演示会话
      if (this.data.connectionMode === 'offline') {
        const session = createChargingSession(this.data.stationId, charger.pileNo || snCode)
        wx.hideLoading()
        wx.navigateTo({
          url: `/pages/charging-monitor/charging-monitor?orderId=${session.orderId}`,
        })
      } else {
        wx.hideLoading()
        wx.showToast({ title: '充电启动失败，请重试', icon: 'none' })
      }
    }
  },
  /** 展示当前输入电桩的二维码 */
  async onShowQRCode() {
    const snCode = extractSnCode(this.data.pileNo)
    if (!snCode) {
      wx.showToast({ title: '请先输入 SN 编码', icon: 'none' })
      return
    }
    this.setData({ showQRCode: true, qrSN: snCode, qrImagePath: '' })
    wx.showLoading({ title: '生成二维码中' })
    try {
      const path = await drawQRCode(snCode, 220)
      this.setData({ qrImagePath: path })
    } catch {
      wx.showToast({ title: '二维码生成失败', icon: 'none' })
    }
    wx.hideLoading()
  },

  onCloseQRCode() {
    this.setData({ showQRCode: false, qrImagePath: '' })
  },



  updateScanStatus(status: ScanStatus) {
    const config =
      status === 'idle'
        ? { scanStatusText: '待扫码', scanStatusClass: 'pending' }
        : status === 'recognizing'
          ? { scanStatusText: '识别中', scanStatusClass: 'busy' }
          : { scanStatusText: '准备就绪', scanStatusClass: 'completed' }

    this.setData({
      scanStatus: status,
      scanStatusText: config.scanStatusText,
      scanStatusClass: config.scanStatusClass,
    })
  },
})
