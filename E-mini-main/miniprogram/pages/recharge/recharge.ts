import { rechargeWalletApi } from '../../services/api'
import { rechargeWallet } from '../../services/mock'
import { getStoredUser, setStoredBalance } from '../../utils/storage'

const app = getApp<IAppOption>()

Page({
  data: {
    presetAmounts: [20, 50, 100, 200],
    selectedAmount: 100,
    customAmount: '',
  },

  selectAmount(e: WechatMiniprogram.CustomEvent) {
    const { amount } = e.currentTarget.dataset as { amount: number }
    this.setData({
      selectedAmount: amount,
      customAmount: '',
    })
  },

  onCustomInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({
      customAmount: e.detail.value,
      selectedAmount: 0,
    })
  },

  async submitRecharge() {
    const inputAmount = this.data.customAmount ? Number(this.data.customAmount) : this.data.selectedAmount
    if (!Number.isFinite(inputAmount) || inputAmount <= 0) {
      wx.showToast({ title: '请输入有效充值金额', icon: 'none' })
      return
    }

    try {
      if (getStoredUser()?.id != null) {
        const summary = await rechargeWalletApi(inputAmount)
        setStoredBalance(summary.balance)
        app.globalData.balance = summary.balance
      } else {
        const nextBalance = rechargeWallet(inputAmount)
        app.globalData.balance = nextBalance
        setStoredBalance(nextBalance)
      }

      wx.showToast({ title: '充值成功', icon: 'success' })
      setTimeout(() => {
        wx.navigateBack()
      }, 1000)
      return
    } catch (error) {
      console.warn('[recharge] api failed, local mock', error)
    }

    const nextBalance = rechargeWallet(inputAmount)
    app.globalData.balance = nextBalance
    setStoredBalance(nextBalance)
    wx.showToast({ title: '充值成功（本地）', icon: 'success' })
    setTimeout(() => {
      wx.navigateBack()
    }, 1000)
  },
})
