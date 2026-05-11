const icons = require('./icon-data.js')

Component({
  data: {
    selected: 0,
    list: [
      {
        pagePath: '/pages/home/home',
        text: '首页',
        iconPath: icons.home.default,
        selectedIconPath: icons.home.active,
      },
      {
        pagePath: '/pages/stations/stations',
        text: '电站',
        iconPath: icons.station.default,
        selectedIconPath: icons.station.active,
      },
      {
        pagePath: '/pages/scan/scan',
        text: '充电',
        iconPath: icons.charge.default,
        selectedIconPath: icons.charge.active,
      },
      {
        pagePath: '/pages/wallet/wallet',
        text: '钱包',
        iconPath: icons.wallet.default,
        selectedIconPath: icons.wallet.active,
      },
      {
        pagePath: '/pages/profile/profile',
        text: '我的',
        iconPath: icons.profile.default,
        selectedIconPath: icons.profile.active,
      },
    ],
  },
  methods: {
    switchTab(e: WechatMiniprogram.CustomEvent) {
      const { path, index } = e.currentTarget.dataset as { path: string; index: number | string }
      this.setData({ selected: Number(index) })
      wx.switchTab({ url: path })
    },
  },
})
