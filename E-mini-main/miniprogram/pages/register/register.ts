interface AccountMap {
  [key: string]: {
    id?: number,
    nickname: string,
    email: string,
    password: string
  }
}

Page({
  data: {
    nickname: '',
    account: '',
    password: '',
    confirmPassword: '',
  },

  onNicknameInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ nickname: e.detail.value })
  },

  onAccountInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ account: e.detail.value })
  },

  onPasswordInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ password: e.detail.value })
  },

  onConfirmPasswordInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ confirmPassword: e.detail.value })
  },

  onRegister() {
    const nickname = this.data.nickname.trim()
    const account = this.data.account.trim()
    const password = this.data.password.trim()
    const confirmPassword = this.data.confirmPassword.trim()

    if (!nickname || !account || !password || !confirmPassword) {
      wx.showToast({ title: '请完整填写注册信息', icon: 'none' })
      return
    }

    if (password.length < 6) {
      wx.showToast({ title: '密码至少需要 6 位', icon: 'none' })
      return
    }

    if (password !== confirmPassword) {
      wx.showToast({ title: '两次输入的密码不一致', icon: 'none' })
      return
    }

    const users = (wx.getStorageSync('echarge_users') || {}) as AccountMap
    if (users[account]) {
      wx.showToast({ title: '该账号已注册', icon: 'none' })
      return
    }

    users[account] = {
      id: 1,
      nickname,
      email: account,
      password,
    }
    wx.setStorageSync('echarge_users', users)

    wx.showToast({ title: '注册成功，请登录', icon: 'success' })
    setTimeout(() => {
      wx.navigateBack()
    }, 1200)
  },

  goLogin() {
    wx.navigateBack()
  },
})
