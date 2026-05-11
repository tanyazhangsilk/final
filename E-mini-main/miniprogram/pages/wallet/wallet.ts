import { getWalletSummary, getWalletTransactions, withApiFallback } from '../../services/api'
import { WalletRecord, getWalletRecords } from '../../services/mock'

const app = getApp<IAppOption>()

type FilterKey = 'all' | 'recharge' | 'consume'

function filterRecords(records: WalletRecord[], filterKey: FilterKey) {
  if (filterKey === 'all') {
    return records
  }
  return records.filter(item => item.category === filterKey)
}

Page({
  data: {
    balance: '0.00',
    currentFilter: 'all' as FilterKey,
    filters: [
      { key: 'all', label: 'All' },
      { key: 'recharge', label: 'Recharge' },
      { key: 'consume', label: 'Consume' },
    ],
    records: [],
    displayRecords: []
  },

  onShow() {
    void this.refreshPage()
    if (typeof this.getTabBar === 'function') {
      const tabBar = this.getTabBar()
      if (tabBar) {
        tabBar.setData({ selected: 3 })
      }
    }
  },

  async refreshPage() {
    const summary = await withApiFallback(
      'wallet:getWalletSummary',
      () => getWalletSummary(),
      () => ({
        balance: app.globalData.balance,
        balanceText: app.globalData.balance.toFixed(2),
        couponCount: 0,
      })
    )
    const records = await withApiFallback(
      'wallet:getWalletTransactions',
      () => getWalletTransactions(),
      () => getWalletRecords()
    )

    app.globalData.balance = summary.balance
    this.setData({
      balance: summary.balanceText,
      records,
      displayRecords: filterRecords(records, this.data.currentFilter),
    })
  },

  onRecharge() {
    wx.navigateTo({ url: '/pages/recharge/recharge' })
  },

  onRefresh() {
    void this.refreshPage()
    wx.showToast({ title: 'Wallet updated', icon: 'none' })
  },

  switchFilter(e: WechatMiniprogram.CustomEvent) {
    const { key } = e.currentTarget.dataset as { key: FilterKey }
    this.setData({
      currentFilter: key,
      displayRecords: filterRecords(this.data.records, key),
    })
  },

  openCoupons() {
    wx.showModal({
      title: 'Coupons',
      content: 'Coupon center is still using local demo content.',
      showCancel: false,
    })
  },
})
