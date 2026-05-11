import { getStationDetail, withApiFallback } from '../../services/api'
import { StationItem, getStationById } from '../../services/mock'

Page({
  data: {
    station: null
  },

  async onLoad(options: Record<string, string | undefined>) {
    const stationId = options.id || 'station-001'
    const station = await withApiFallback(
      'station-detail:getStationDetail',
      () => getStationDetail(stationId),
      () => getStationById(stationId)
    )

    this.setData({
      station,
    })
  },

  toggleFavorite() {
    const station = this.data.station
    if (!station) {
      return
    }
    this.setData({
      station: {
        ...station,
        favorite: !station.favorite,
      },
    })
  },

  goNavigate() {
    wx.showToast({ title: 'Navigation ready', icon: 'none' })
  },

  goCharge() {
    const station = this.data.station
    if (!station) {
      return
    }
    const targetPile = station.piles.find(item => item.status === 'idle') || station.piles[0]
    wx.setStorageSync('echarge_scan_context', {
      stationId: station.id,
      pileNo: targetPile?.id || '',
      snCode: targetPile?.id || '',
    })
    wx.switchTab({ url: '/pages/scan/scan' })
  },

  onPileTap(e: WechatMiniprogram.CustomEvent) {
    const station = this.data.station
    if (!station) {
      return
    }

    const { pileNo, snCode, status } = e.currentTarget.dataset as {
      pileNo: string,
      snCode?: string,
      status: string
    }

    if (status !== 'idle') {
      wx.showToast({ title: 'Pile unavailable', icon: 'none' })
      return
    }

    wx.setStorageSync('echarge_scan_context', {
      stationId: station.id,
      pileNo,
      snCode: snCode || pileNo,
    })
    wx.switchTab({ url: '/pages/scan/scan' })
  },
})
