import { getInvoiceRecords, withApiFallback } from '../../services/api'
import { InvoiceRecord, getInvoices } from '../../services/mock'

Page({
  data: {
    records: []
  },

  async onShow() {
    const records = await withApiFallback(
      'invoice-records:getInvoiceRecords',
      () => getInvoiceRecords(),
      () => getInvoices()
    )
    this.setData({
      records,
    })
  },

  viewAttachment(e: WechatMiniprogram.CustomEvent) {
    const { name, status } = e.currentTarget.dataset as { name: string; status: string }
    wx.showModal({
      title: 'Invoice file',
      content: `${status}\nFile: ${name}`,
      showCancel: false,
    })
  },
})
