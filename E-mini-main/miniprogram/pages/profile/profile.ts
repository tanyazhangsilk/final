import { getInvoices, getOrders } from '../../services/mock'
import { getStoredUser, setStoredUser, getUserId } from '../../utils/storage'
import { get } from '../../services/request'

const app = getApp<IAppOption>()

Page({
  data: {
    nickname: '车主用户',
    email: 'user@echarge.com',
    balance: '0.00',
    level: '银卡车主',
    status: '账户状态正常',
    orderCount: 0,
    invoiceCount: 0,
    coupons: 3,
    quickServices: [
      { key: 'orders', title: '我的订单', desc: '查看充电记录' },
      { key: 'invoices', title: '发票记录', desc: '管理开票申请' },
      { key: 'wallet', title: '钱包', desc: '查看余额明细' },
      { key: 'coupons', title: '优惠券', desc: '管理优惠权益' },
    ],
    menuItems: [
      { key: 'messages', title: '消息中心', desc: '活动消息与订单通知' },
      { key: 'operatorApply', title: '运营商入驻', desc: '申请成为运营商' },
      { key: 'settings', title: '设置', desc: '账户与偏好配置' },
      { key: 'about', title: '关于平台', desc: '查看平台服务说明' },
    ],
  },

  onShow() {
    this.refreshPage()
    if (typeof this.getTabBar === 'function') {
      const tabBar = this.getTabBar()
      if (tabBar) {
        tabBar.setData({ selected: 4 })
      }
    }
  },

  refreshPage() {
    // 先从 storage 读取最新用户数据（兼容旧版 globalData 未同步的情况）
    const storedUser = getStoredUser()
    console.log('[profile] storedUser:', JSON.stringify(storedUser))
    console.log('[profile] globalData.echargeUser:', JSON.stringify(app.globalData.echargeUser))
    
    if (storedUser) {
      // 同步到 globalData 确保其他页面也能拿到最新数据
      app.globalData.echargeUser = storedUser
    }

    const user = storedUser || app.globalData.echargeUser
    this.setData({
      nickname: user?.nickname || '车主用户',
      email: user?.email || 'user@echarge.com',
      balance: (app.globalData.balance || 0).toFixed(2),
      orderCount: getOrders().length,
      invoiceCount: getInvoices().length,
    })
  },

  handleQuickService(e: WechatMiniprogram.CustomEvent) {
    const { key } = e.currentTarget.dataset as { key: string }
    const routes: Record<string, string> = {
      orders: '/pages/orders/orders',
      invoices: '/pages/invoice-records/invoice-records',
      wallet: '/pages/wallet/wallet',
    }
    if (routes[key]) {
      if (key === 'wallet') {
        wx.switchTab({ url: routes[key] })
      } else {
        wx.navigateTo({ url: routes[key] })
      }
      return
    }
    wx.showModal({
      title: '优惠券中心',
      content: '当前账户可用优惠券 3 张，支持在充电结算页自动抵扣。',
      showCancel: false,
    })
  },
    async checkOperatorApplyStatus() {
    const uid = getUserId()
    if (!uid) { wx.showToast({ title: '请先登录', icon: 'none' }); return }
    try {
      const res = await get('/operator/apply/status')
      if (res && res.is_operator) {
        wx.showToast({ title: '您已是运营商用户', icon: 'none' })
        return
      }
      if (res && res.has_application) {
        wx.showModal({ title: '入驻申请状态', content: '状态：' + (res.status_text || '') + '\n' + (res.message || ''), showCancel: false })
        return
      }
      wx.navigateTo({ url: '/pages/operator-apply/operator-apply' })
    } catch {
      wx.navigateTo({ url: '/pages/operator-apply/operator-apply' })
    }
  },

  handleMenu(e: WechatMiniprogram.CustomEvent) {
    const { key } = e.currentTarget.dataset as { key: string }
    if (key === 'messages') {
      wx.showToast({ title: '当前暂无新消息', icon: 'none' })
      return
    }
    if (key === 'operatorApply') {
      void this.checkOperatorApplyStatus()
      return
    }
    if (key === 'settings') {
      wx.showToast({ title: '设置中心已准备完成', icon: 'none' })
      return
    }
    wx.showModal({
      title: '关于平台',
      content: 'E-Charge 聚焦车主找站、扫码充电、钱包支付、订单查询与发票服务等核心场景。',
      showCancel: false,
    })
  },

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确认退出当前账户吗？',
      success: (res) => {
        if (!res.confirm) return
        setStoredUser(null)
        app.globalData.echargeUser = null
        wx.reLaunch({ url: '/pages/login/login' })
      },
    })
  },
})
