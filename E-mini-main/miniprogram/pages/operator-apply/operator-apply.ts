import { post } from '../../services/request'
import { getStoredUser } from '../../utils/storage'

Page({
  data: {
    operatorName: '',
    companyName: '',
    contactName: '',
    phone: '',
    email: '',
    region: '',
    address: '',
    creditCode: '',
    description: '',
    stationCount: '0',
    submitting: false,
  },

  onLoad() {
    const user = getStoredUser()
    if (user) {
      this.setData({
        contactName: user.nickname || '',
        phone: user.phone || '',
        email: user.email || '',
      })
    }
  },

  onInput(e: WechatMiniprogram.CustomEvent) {
    const field = e.currentTarget.dataset.field as string
    const value = e.detail.value
    this.setData({ [field]: value })
  },

  async onSubmit() {
    const { operatorName, contactName, phone } = this.data

    if (!operatorName.trim()) {
      wx.showToast({ title: '请输入运营商名称', icon: 'none' })
      return
    }
    if (!contactName.trim()) {
      wx.showToast({ title: '请输入联系人', icon: 'none' })
      return
    }
    if (!phone.trim()) {
      wx.showToast({ title: '请输入联系电话', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    wx.showLoading({ title: '提交中...' })

    try {
      const result = await post('/operator/apply', {
        operator_name: this.data.operatorName.trim(),
        company_name: this.data.companyName.trim(),
        contact_name: this.data.contactName.trim(),
        phone: this.data.phone.trim(),
        email: this.data.email.trim(),
        region: this.data.region.trim(),
        address: this.data.address.trim(),
        credit_code: this.data.creditCode.trim(),
        description: this.data.description.trim(),
        station_count: parseInt(this.data.stationCount) || 0,
        charger_count: 0,
      })

      wx.hideLoading()
      wx.showModal({
        title: '提交成功',
        content: '您的入驻申请已提交，请等待管理员审核。审核结果将通过消息通知。',
        showCancel: false,
        success: () => {
          wx.navigateBack()
        },
      })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '提交失败，请重试', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },
})
