import { post } from '../../services/request'
import { setStoredUser, UserInfo } from '../../utils/storage'

const app = getApp<IAppOption>()

interface LoginApiData {
  id: number,
  user_id?: number,
  nickname: string,
  phone: string,
  email: string
}

type LoginType = 'mobile' | 'email'

Page({
  data: {
    loginType: 'email' as LoginType,
    account: '',
    password: '',
    agreeChecked: true,
    accountLabel: '邮箱账号',
    accountPlaceholder: '请输入邮箱账号',
    backendOnline: true
  },

  onLoad() {
    this.updateLoginTypeView('email')
    this.setData({
      account: 'user@echarge.com',
      password: '123456',
    })
    // 异步检测后端是否在线
    this.checkBackendStatus()
  },

  async checkBackendStatus() {
    try {
      await post<LoginApiData>('/auth/login', {
        account: 'user@echarge.com',
        password: '',
      })
    } catch {
      // 后端返回了错误（密码不对）说明后端在线；完全不响应才说明离线
    }
    this.setData({ backendOnline: true })
  },

  switchLoginType(e: WechatMiniprogram.CustomEvent) {
    const { type } = e.currentTarget.dataset as { type: LoginType }
    this.updateLoginTypeView(type)
    this.setData({
      account: type === 'mobile' ? '13800138000' : 'user@echarge.com',
    })
  },

  onAccountInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ account: e.detail.value })
  },

  onPasswordInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ password: e.detail.value })
  },

  toggleAgree() {
    this.setData({ agreeChecked: !this.data.agreeChecked })
  },

  /**
   * 登录成功后统一处理：存数据、更新全局变量、跳转首页。
   */
  _doLogin(user: UserInfo) {
    setStoredUser(user)
    app.globalData.echargeUser = user
    wx.switchTab({ url: '/pages/home/home' })
  },

  async onLogin() {
    const account = this.data.account.trim()
    const password = this.data.password.trim()

    if (!this.data.agreeChecked) {
      wx.showToast({ title: '请先勾选服务协议', icon: 'none' })
      return
    }
    if (!account || !password) {
      wx.showToast({ title: '请填写账号和密码', icon: 'none' })
      return
    }

    // === 1. 尝试使用后端 API 登录 ===
    try {
      const payload =
        this.data.loginType === 'mobile'
          ? { phone: account, password }
          : { account, password }

      const data = await post<LoginApiData>('/auth/login', payload)
      const user: UserInfo = {
        id: data.id,
        nickname: data.nickname,
        email: data.email,
        phone: data.phone,
      }
      this._doLogin(user)
      return
    } catch {
      // 后端不可用或账号不存在，尝试本地回退
      console.warn('[login] API login failed, trying local fallback')
    }

    // === 2. 本地回退：从注册记录中查找 ===
    const localUsers: Record<string, { nickname: string; email: string; password: string }> =
      wx.getStorageSync('echarge_users') || {}

    // 尝试精确匹配或默认演示账号
    const localUser =
      localUsers[account] ||
      localUsers['user@echarge.com']

    if (localUser && localUser.password === password) {
      const user: UserInfo = {
        id: 1,
        nickname: localUser.nickname || localUser.email || account,
        email: account.includes('@') ? account : (localUser.email || account),
        phone: account,
      }
      this._doLogin(user)
      return
    }

    // === 3. 本地演示账号兜底（仅供离线演示使用）====
    if (!this.data.backendOnline) {
      const user: UserInfo = {
        id: 1,
        nickname: '车主用户',
        email: account.includes('@') ? account : (account + '@mini.echarge'),
        phone: account,
      }
      this._doLogin(user)
      wx.showToast({ title: '离线演示模式', icon: 'none' })
      return
    }

    wx.showToast({ title: '账号或密码不正确', icon: 'none' })
  },

  async onQuickLogin() {
    // 先试后端
    try {
      const data = await post<LoginApiData>('/auth/login', {
        account: 'user@echarge.com',
        password: '123456',
      })
      this._doLogin({
        id: data.id,
        nickname: data.nickname,
        email: data.email,
        phone: data.phone,
      })
      return
    } catch {
      console.warn('[login] QuickLogin API failed, using local')
    }

    // 后端不可达时使用本地演示账号
    this._doLogin({
      id: 1,
      nickname: '演示车主',
      email: '13800138000@mini.echarge',
      phone: '13800138000',
    })
    wx.showToast({ title: '离线演示模式', icon: 'none' })
  },

  goRegister() {
    wx.navigateTo({ url: '/pages/register/register' })
  },

  updateLoginTypeView(type: LoginType) {
    this.setData({
      loginType: type,
      accountLabel: type === 'mobile' ? '手机号' : '邮箱账号',
      accountPlaceholder: type === 'mobile' ? '请输入手机号' : '请输入邮箱账号',
    })
  },
})
