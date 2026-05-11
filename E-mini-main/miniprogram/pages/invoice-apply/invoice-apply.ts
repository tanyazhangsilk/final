import {
  ApplyInvoicePayload,
  applyInvoice,
  getInvoiceRecords,
  getOrderDetail,
  withApiFallback,
} from '../../services/api'
import {
  OrderItem,
  createInvoiceApplication,
  findInvoiceByOrderId,
  getOrderById,
} from '../../services/mock'

const app = getApp<IAppOption>()

Page({
  data: {
    order: null,
    title: '',
    email: '',
    note: '',
    invoiceType: 'E-Invoice',
    invoiceTypes: ['E-Invoice', 'Personal Invoice'],
    notices: [
      'Invoice amount follows the final paid order amount.',
      'You can review progress later on the invoice records page.',
    ],
  },

  async onLoad(options: Record<string, string | undefined>) {
    const order = await withApiFallback(
      'invoice-apply:getOrderDetail',
      async () => {
        if (!options.orderId) {
          throw new Error('missing order id')
        }
        return getOrderDetail(options.orderId)
      },
      () => getOrderById(options.orderId || '')
    )
    const email = app.globalData.echargeUser?.email || 'user@echarge.com'
    this.setData({
      order,
      title: 'Individual',
      email,
      note: 'E-Invoice',
    })
  },

  selectType(e: WechatMiniprogram.CustomEvent) {
    const { value } = e.currentTarget.dataset as { value: string }
    this.setData({
      invoiceType: value,
    })
  },

  onTitleInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ title: e.detail.value })
  },

  onEmailInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ email: e.detail.value })
  },

  onNoteInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ note: e.detail.value })
  },

  async submitInvoice() {
    const order = this.data.order
    const title = this.data.title.trim()
    const email = this.data.email.trim()

    if (!order) {
      wx.showToast({ title: 'Order not found', icon: 'none' })
      return
    }

    if (!title || !email) {
      wx.showToast({ title: 'Fill invoice info', icon: 'none' })
      return
    }

    const existing = await withApiFallback(
      'invoice-apply:getInvoiceRecords',
      async () => {
        const records = await getInvoiceRecords()
        return records.find(item => item.orderId === order.id) || null
      },
      () => findInvoiceByOrderId(order.id)
    )

    if (existing) {
      wx.showToast({ title: 'Invoice already applied', icon: 'none' })
      wx.navigateTo({ url: '/pages/invoice-records/invoice-records' })
      return
    }

    const payload: ApplyInvoicePayload = {
      order_id: order.id,
      title,
      email,
      note: `${this.data.invoiceType} - ${this.data.note.trim()}`,
      type: this.data.invoiceType,
    }

    try {
      await applyInvoice(payload)
    } catch (error) {
      console.warn('[invoice-apply] applyInvoice failed, fallback to mock record', error)
      createInvoiceApplication({
        orderId: order.id,
        title,
        email,
        note: payload.note,
      })
    }

    wx.showToast({ title: 'Invoice submitted', icon: 'success' })
    setTimeout(() => {
      wx.navigateTo({ url: '/pages/invoice-records/invoice-records' })
    }, 900)
  },
})
