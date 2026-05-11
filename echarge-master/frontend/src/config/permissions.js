import {
  Bell,
  Connection,
  CreditCard,
  DataAnalysis,
  Document,
  Histogram,
  OfficeBuilding,
  Promotion,
  Setting,
  Tickets,
  UserFilled,
  Wallet,
} from '@element-plus/icons-vue'

export const ROLES = {
  ADMIN: 'admin',
  OPERATOR: 'operator',
}

export const ROLE_LABELS = {
  [ROLES.ADMIN]: '平台管理员',
  [ROLES.OPERATOR]: '充电运营商',
}

export const ROLE_DEFAULT_ROUTE = {
  [ROLES.ADMIN]: '/admin',
  [ROLES.OPERATOR]: '/operator',
}

const USER_ROLE_KEY = 'userRole'
const OPERATOR_ID_KEY = 'operatorId'
const DEFAULT_OPERATOR_ID = 'op-001'

export const getStoredRole = () => {
  const saved = localStorage.getItem(USER_ROLE_KEY)
  return saved === ROLES.ADMIN ? ROLES.ADMIN : ROLES.OPERATOR
}

export const setStoredRole = (role) => {
  localStorage.setItem(USER_ROLE_KEY, role === ROLES.ADMIN ? ROLES.ADMIN : ROLES.OPERATOR)
}

export const resolveRoleDefaultRoute = (role) => ROLE_DEFAULT_ROUTE[role] || ROLE_DEFAULT_ROUTE[ROLES.OPERATOR]

export const getStoredOperatorId = () => {
  const value = localStorage.getItem(OPERATOR_ID_KEY)
  return value && value.trim() ? value : DEFAULT_OPERATOR_ID
}

export const setStoredOperatorId = (operatorId) => {
  const value = operatorId && String(operatorId).trim() ? String(operatorId).trim() : DEFAULT_OPERATOR_ID
  localStorage.setItem(OPERATOR_ID_KEY, value)
}

export const ensureUserContext = () => {
  if (!localStorage.getItem(USER_ROLE_KEY)) {
    setStoredRole(ROLES.OPERATOR)
  }
  if (!localStorage.getItem(OPERATOR_ID_KEY)) {
    setStoredOperatorId(DEFAULT_OPERATOR_ID)
  }
}

export const getCurrentUserContext = () => ({
  role: getStoredRole(),
  operatorId: getStoredOperatorId(),
})

export const getRoleByPath = (path = '') => {
  if (path.startsWith('/admin')) return ROLES.ADMIN
  if (path.startsWith('/operator')) return ROLES.OPERATOR
  return null
}

export const MENU_CONFIG = {
  [ROLES.ADMIN]: [
    {
      label: '总览',
      items: [{ index: '/admin', title: '平台工作台', icon: Histogram }],
    },
    {
      label: '审核中心',
      items: [
        { index: '/admin/institutions', title: '运营商审核', icon: OfficeBuilding },
        { index: '/admin/institutions/stations', title: '电站审核', icon: Bell },
      ],
    },
    {
      label: '订单监管',
      items: [
        { index: '/admin/orders', title: '全局订单管理', icon: Tickets },
        { index: '/admin/orders/abnormal', title: '异常订单管理', icon: Connection },
      ],
    },
    {
      label: '资金清分',
      items: [
        { index: '/admin/finance', title: '平台清分中心', icon: Wallet },
        { index: '/admin/finance/invoices', title: '发票管理', icon: Document },
      ],
    },
    {
      label: '用户管理',
      items: [
        { index: '/admin/users', title: '用户管理', icon: UserFilled },
        { index: '/admin/users/blacklist', title: '黑名单管理', icon: UserFilled },
      ],
    },
    {
      label: '系统配置',
      items: [
        { index: '/admin/marketing', title: '营销审核', icon: Promotion },
        { index: '/admin/settings', title: '权限控制', icon: DataAnalysis },
        { index: '/admin/settings/params/basic', title: '系统参数配置', icon: Setting },
      ],
    },
  ],
  [ROLES.OPERATOR]: [
    {
      label: '总览',
      items: [{ index: '/operator', title: '运营工作台', icon: Histogram }],
    },
    {
      label: '资产管理',
      items: [
        { index: '/operator/stations', title: '电站管理', icon: OfficeBuilding },
        { index: '/operator/stations/chargers', title: '电桩管理', icon: Connection },
      ],
    },
    {
      label: '计费管理',
      items: [
        { index: '/operator/billing', title: '电价设置', icon: DataAnalysis },
        { index: '/operator/billing/templates', title: '电价模板管理', icon: Document },
      ],
    },
    {
      label: '订单管理',
      items: [
        { index: '/operator/orders/history', title: '历史订单', icon: Tickets },
        { index: '/operator/orders/realtime', title: '实时订单', icon: Bell },
        { index: '/operator/orders/abnormal', title: '异常订单', icon: Connection },
      ],
    },
    {
      label: '财务管理',
      items: [
        { index: '/operator/finance', title: '收益对账', icon: Wallet },
        { index: '/operator/finance/bank-card', title: '绑卡管理', icon: CreditCard },
        { index: '/operator/finance/invoices', title: '发票管理', icon: Document },
      ],
    },
    {
      label: '客户管理',
      items: [
        { index: '/operator/customers', title: '车队与白名单', icon: UserFilled },
        { index: '/operator/customers/fleets', title: '专属用户管理', icon: UserFilled },
        { index: '/operator/customers/tags', title: '标签管理', icon: Promotion },
      ],
    },
    {
      label: '营销管理',
      items: [
        { index: '/operator/marketing', title: '折扣优惠', icon: Promotion },
        { index: '/operator/marketing/coupons', title: '优惠券发放', icon: Promotion },
      ],
    },
    {
      label: '系统',
      items: [{ index: '/operator/settings', title: '运营商设置', icon: Setting }],
    },
  ],
}

export const buildMenuByRole = (role) => MENU_CONFIG[role] || MENU_CONFIG[ROLES.OPERATOR]
