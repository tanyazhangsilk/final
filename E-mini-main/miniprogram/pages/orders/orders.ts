import { getInvoiceRecords, getOrders, withApiFallback } from '../../services/api'
import {
  OrderItem,
  findInvoiceByOrderId,
  getChargingSession,
  getOrders as getMockOrders,
} from '../../services/mock'

type TabKey = 'all' | 'charging' | 'completed' | 'abnormal'

function filterOrders(orders: OrderItem[], tab: TabKey) {
  if (tab === 'all') {
    return orders
  }
  return orders.filter(item => item.status === tab)
}

Page({
  data: {
    loading: true,
    currentTab: 'all' as TabKey,
    tabs: [
      { key: 'all', label: '全部' },
      { key: 'charging', label: '充电中' },
      { key: 'completed', label: '已完成' },
      { key: 'abnormal', label: '异常中断' },
    ],
    orders: [],
    displayOrders: [],
    empty: false,
  },

  async onShow() {
    const orders = await withApiFallback('orders:getOrders', () => getOrders(), () => getMockOrders())
    const displayOrders = filterOrders(orders, this.data.currentTab)
    this.setData({
      loading: false,
      orders,
      displayOrders,
      empty: displayOrders.length === 0
    })
  },

  switchTab(e: WechatMiniprogram.CustomEvent) {
    const { key } = e.currentTarget.dataset as { key: TabKey }
    const displayOrders = filterOrders(this.data.orders, key)
    this.setData({
      currentTab: key,
      displayOrders,
      empty: displayOrders.length === 0
    })
  },

  onOrderTap(e: WechatMiniprogram.CustomEvent) {
    const { id, status } = e.currentTarget.dataset as { id: string; status: string }
    const session = getChargingSession()

    if (status === 'charging' && session && session.orderId === id) {
      wx.navigateTo({ url: `/pages/charging-monitor/charging-monitor?orderId=${id}` })
      return
    }

    wx.navigateTo({ url: `/pages/charging-result/charging-result?orderId=${id}` })
  },

  async applyInvoice(e: WechatMiniprogram.CustomEvent) {
    const { id } = e.currentTarget.dataset as { id: string }
    const existing = await withApiFallback(
      'orders:getInvoiceRecords',
      async () => {
        const records = await getInvoiceRecords()
        return records.find(item => item.orderId === id) || null
      },
      () => findInvoiceByOrderId(id)
    )

    if (existing) {
      wx.navigateTo({ url: '/pages/invoice-records/invoice-records' })
      return
    }

    wx.navigateTo({ url: `/pages/invoice-apply/invoice-apply?orderId=${id}` })
  },

  chargeAgain(e: WechatMiniprogram.CustomEvent) {
    const { stationId, pileNo } = e.currentTarget.dataset as { stationId: string; pileNo: string }
    wx.setStorageSync('echarge_scan_context', {
      stationId,
      pileNo,
      snCode: pileNo,
    })
    wx.switchTab({ url: '/pages/scan/scan' })
  },

  openCharging(e: WechatMiniprogram.CustomEvent) {
    const { id } = e.currentTarget.dataset as { id: string }
    wx.navigateTo({ url: `/pages/charging-monitor/charging-monitor?orderId=${id}` })
  },
})
