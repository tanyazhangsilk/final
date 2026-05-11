import {
  OrderDetailItem,
  getInvoiceRecords,
  getOrderDetail,
  withApiFallback,
} from '../../services/api'
import { findInvoiceByOrderId, getLatestCompletedOrder, getOrderById } from '../../services/mock'

Page({
  data: {
    order: null,
    invoiceReady: false,
  },

  async onLoad(options: Record<string, string | undefined>) {
    const order = await withApiFallback(
      'charging-result:getOrderDetail',
      async () => {
        if (!options.orderId) {
          throw new Error('missing order id')
        }
        return getOrderDetail(options.orderId)
      },
      () => {
        const fallbackOrder = options.orderId ? getOrderById(options.orderId) : getLatestCompletedOrder()
        if (!fallbackOrder) {
          return null
        }

        return {
          ...fallbackOrder,
          energyValue: Number(fallbackOrder.powerText.replace(/[^\d.]/g, '')) || 0,
          electricityFeeValue: 0,
          serviceFeeValue: 0,
          totalAmountValue: fallbackOrder.amountValue,
          discountFeeValue: fallbackOrder.discountValue,
          electricityFeeText: '0.00',
          serviceFeeText: '0.00',
          totalAmountText: fallbackOrder.payableText,
          paymentStatus: fallbackOrder.paymentStatusText,
          orderStatus: fallbackOrder.status,
          batteryPercent: 0,
          currentPowerValue: 0,
        } as OrderDetailItem
      }
    )

    const invoiceReady = order
      ? await withApiFallback(
          'charging-result:getInvoiceRecords',
          async () => {
            const records = await getInvoiceRecords()
            return records.some(item => item.orderId === order.id)
          },
          () => Boolean(findInvoiceByOrderId(order.id))
        )
      : false

    this.setData({
      order,
      invoiceReady,
    })
  },

  goOrders() {
    wx.navigateTo({ url: '/pages/orders/orders' })
  },

  goHome() {
    wx.switchTab({ url: '/pages/home/home' })
  },

  goInvoice() {
    const order = this.data.order
    if (!order) {
      return
    }

    if (this.data.invoiceReady) {
      wx.navigateTo({ url: '/pages/invoice-records/invoice-records' })
      return
    }

    wx.navigateTo({ url: `/pages/invoice-apply/invoice-apply?orderId=${order.id}` })
  },

  chargeAgain() {
    const order = this.data.order
    if (!order) {
      return
    }
    wx.setStorageSync('echarge_scan_context', {
      stationId: order.stationId,
      pileNo: order.pileNo,
      snCode: order.pileNo,
    })
    wx.switchTab({ url: '/pages/scan/scan' })
  },
})
