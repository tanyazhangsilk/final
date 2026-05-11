import {
  OrderItem,
  PromotionCard,
  StationItem,
  getLatestCompletedOrder,
  getPromotions,
  getRecommendedStations,
} from '../../services/mock'
import {
  getOrders,
  getRecommendStations,
  getStations,
  getWalletSummary,
  withApiFallback,
} from '../../services/api'

const app = getApp<IAppOption>()

function sortByLatest(left: OrderItem, right: OrderItem) {
  const leftTime = new Date((left.endTime || left.startTime || '').replace(/-/g, '/')).getTime()
  const rightTime = new Date((right.endTime || right.startTime || '').replace(/-/g, '/')).getTime()
  return rightTime - leftTime
}

Page({
  data: {
    nickname: 'User',
    balance: '0.00',
    stations: /** @type {StationItem[]} */ ([]),
    promotions: /** @type {PromotionCard[]} */ ([]),
    recentOrder: null,
    quickActions: [
      { id: 'scan', title: 'Scan', desc: 'Start charging quickly', icon: 'S', type: 'scan' },
      { id: 'stations', title: 'Stations', desc: 'Browse nearby stations', icon: 'T', type: 'stations' },
      { id: 'orders', title: 'Orders', desc: 'View charging orders', icon: 'O', type: 'orders' },
      { id: 'wallet', title: 'Wallet', desc: 'Balance and transactions', icon: 'W', type: 'wallet' },
    ],
  },

  onShow() {
    void this.refreshPage()
    if (typeof this.getTabBar === 'function') {
      const tabBar = this.getTabBar()
      if (tabBar) {
        tabBar.setData({ selected: 0 })
      }
    }
  },

  async refreshPage() {
    const nickname = app.globalData.echargeUser?.nickname || 'User'
    const promotions = getPromotions()

    const walletSummary = await withApiFallback(
      'home:getWalletSummary',
      () => getWalletSummary(),
      () => ({
        balance: app.globalData.balance,
        balanceText: app.globalData.balance.toFixed(2),
        couponCount: 0,
      })
    )
    app.globalData.balance = walletSummary.balance

    const stations = await withApiFallback(
      'home:getRecommendStations',
      async () => {
        const recommendStations = await getRecommendStations()
        if (recommendStations.length) {
          return recommendStations
        }
        return getStations()
      },
      () => getRecommendedStations()
    )

    const recentOrder = await withApiFallback(
      'home:getOrders',
      async () => {
        const orders = await getOrders()
        return orders.filter(item => item.status === 'completed').sort(sortByLatest)[0] || null
      },
      () => getLatestCompletedOrder()
    )

    this.setData({
      nickname,
      balance: walletSummary.balanceText,
      stations,
      promotions,
      recentOrder,
    })
  },

  onActionTap(e: WechatMiniprogram.CustomEvent) {
    const { type } = e.currentTarget.dataset as { type: string }

    switch (type) {
      case 'scan':
        wx.switchTab({ url: '/pages/scan/scan' })
        break
      case 'stations':
        wx.switchTab({ url: '/pages/stations/stations' })
        break
      case 'wallet':
        wx.switchTab({ url: '/pages/wallet/wallet' })
        break
      case 'orders':
        wx.navigateTo({ url: '/pages/orders/orders' })
        break
      default:
        break
    }
  },

  onStationTap(e: WechatMiniprogram.CustomEvent) {
    const { id } = e.currentTarget.dataset as { id: string }
    wx.navigateTo({ url: `/pages/station-detail/station-detail?id=${id}` })
  },

  openRecentOrder() {
    const order = this.data.recentOrder
    if (!order) {
      return
    }
    wx.navigateTo({ url: `/pages/charging-result/charging-result?orderId=${order.id}` })
  },

  openCoupons() {
    wx.showModal({
      title: 'Coupons',
      content: 'Coupon center is still using local demo content.',
      showCancel: false,
    })
  },

  onPromotionTap() {
    wx.showToast({ title: 'Promotion synced', icon: 'none' })
  },
})
