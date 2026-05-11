Page({
  data: {
    records: [] as { id: string; stationName: string; status: string; duration: string; amount: string; time: string }[],
  },

  onLoad() {
    // 可从本地存储或接口获取充电记录
    const records = wx.getStorageSync('echarge_charging_records') || []
    this.setData({ records })
  },
})
