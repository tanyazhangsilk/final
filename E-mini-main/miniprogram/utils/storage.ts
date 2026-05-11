const USER_KEY = 'echarge_user'
const BALANCE_KEY = 'echarge_balance'

export interface UserInfo {
  nickname: string,
  email: string
  /** 后端 sys_users.id，请求头 X-Mini-User-Id */
  id?: number,
  phone?: string
}

/**
 * 获取当前登录用户。
 * 自动修复：旧版本地回退数据只有 nickname/email 没有 id，
 * 这里补一个合成 id=1 并写回存储，确保 getStoredUser()?.id != null。
 */
export function getStoredUser(): UserInfo | null {
  try {
    const raw = wx.getStorageSync(USER_KEY)
    if (!raw) return null
    // 旧数据修复：补 id
    if (raw.id == null && (raw.nickname || raw.email)) {
      raw.id = 1
      wx.setStorageSync(USER_KEY, raw)
    }
    return raw as UserInfo
  } catch {
    return null
  }
}

/**
 * 设置当前登录用户。
 * 始终确保 id 字段存在且为 number 类型。
 */
export function setStoredUser(user: UserInfo | null) {
  if (user) {
    // 保证 id 字段不为 undefined
    const safe = { ...user, id: user.id ?? 1 }
    wx.setStorageSync(USER_KEY, safe)
  } else {
    wx.removeStorageSync(USER_KEY)
  }
}

/**
 * 返回已登录用户的数字 ID（始终 != null 时表示已登录）。
 * 如果存储数据缺少 id 但用户确实存在，返回合成值 1。
 */
export function getUserId(): number | null {
  const user = getStoredUser()
  if (!user) return null
  if (user.id != null && Number.isFinite(Number(user.id))) {
    return Number(user.id)
  }
  // 兜底：用户有 profile 但缺 id → 合成
  if (user.nickname || user.email) {
    user.id = 1
    wx.setStorageSync(USER_KEY, user)
    return 1
  }
  return null
}

/** 生成请求头，用于后端 X-Mini-User-Id 鉴权 */
export function getMiniAuthHeaders(): WechatMiniprogram.IAnyObject {
  const uid = getUserId()
  if (uid != null) {
    return { 'X-Mini-User-Id': String(uid) }
  }
  return {}
}

export function getStoredBalance(): number {
  try {
    const data = wx.getStorageSync(BALANCE_KEY)
    return typeof data === 'number' ? data : 0
  } catch {
    return 0
  }
}

export function setStoredBalance(balance: number) {
  wx.setStorageSync(BALANCE_KEY, balance)
}
