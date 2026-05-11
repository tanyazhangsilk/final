import { createRouter, createWebHistory } from 'vue-router'

import LoginPage from '../views/LoginPage.vue'
import MainLayout from '../layouts/MainLayout.vue'
import PlaceholderPage from '../views/PlaceholderPage.vue'
import AdminDashboard from '../views/admin/AdminDashboard.vue'
import OperatorDashboard from '../views/operator/OperatorDashboard.vue'
import {
  ROLES,
  getRoleByPath,
  getStoredRole,
  resolveRoleDefaultRoute,
  setStoredRole,
} from '../config/permissions'

const roleAwareRedirect = (mapping) => {
  const role = getStoredRole()
  return mapping[role] || mapping.default || resolveRoleDefaultRoute(role)
}

const routes = [
  { path: '/login', name: 'Login', component: LoginPage, meta: { guest: true } },
  { path: '/', redirect: () => resolveRoleDefaultRoute(getStoredRole()) },
  {
    path: '/admin',
    component: MainLayout,
    meta: { role: ROLES.ADMIN },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: AdminDashboard,
        meta: { role: ROLES.ADMIN, title: '平台工作台', section: '总览', description: '查看平台核心指标、待办事项与运行概况' },
      },
      {
        path: 'institutions',
        name: 'AdminInstitutions',
        component: () => import('../views/admin/OperatorAudit.vue'),
        meta: { role: ROLES.ADMIN, title: '运营商审核', section: '审核中心', description: '审核运营商入驻资料、资质与结算信息' },
      },
      {
        path: 'institutions/stations',
        name: 'AdminInstitutionStations',
        component: () => import('../views/admin/todo/StationAudit.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '电站审核',
          section: '审核中心',
          description: '审核电站申请资料、建设信息与上架状态',
          keepAlive: true,
        },
      },
      {
        path: 'orders',
        name: 'AdminOrders',
        component: () => import('../views/orders/HistoryOrders.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '全局订单管理',
          section: '订单监管',
          description: '查看平台订单、状态流转与交易信息',
          keepAlive: true,
        },
      },
      {
        path: 'orders/abnormal',
        name: 'AdminOrderAbnormal',
        component: () => import('../views/orders/AbnormalOrders.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '异常订单管理',
          section: '订单监管',
          description: '查看异常订单与处理结果',
          keepAlive: true,
        },
      },
      { path: 'orders/anomalies', redirect: '/admin/orders/abnormal' },
      {
        path: 'orders/detail/:id',
        name: 'AdminOrderDetail',
        component: () => import('../views/orders/OrderDetailPage.vue'),
        meta: { role: ROLES.ADMIN, title: '订单详情', section: '订单监管', description: '查看订单完整交易与状态明细' },
      },
      {
        path: 'finance',
        name: 'AdminFinance',
        component: () => import('../views/admin/GlobalSettle.vue'),
        meta: { role: ROLES.ADMIN, title: '平台清分中心', section: '资金清分', description: '查看清分进度、批次执行与资金状态' },
      },
      {
        path: 'finance/invoices',
        name: 'AdminFinanceInvoices',
        component: () => import('../views/finance/InvoiceManagement.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '发票管理',
          section: '资金清分',
          description: '查看发票记录与处理状态',
          keepAlive: true,
        },
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('../views/admin/UserManagement.vue'),
        meta: { role: ROLES.ADMIN, title: '用户管理', section: '用户管理', description: '查看平台用户资料、状态与账户信息' },
      },
      {
        path: 'users/blacklist',
        name: 'AdminUsersBlacklist',
        component: () => import('../views/admin/UserBlacklist.vue'),
        meta: { role: ROLES.ADMIN, title: '黑名单管理', section: '用户管理', description: '管理高风险用户与限制对象' },
      },
      {
        path: 'marketing',
        name: 'AdminMarketing',
        component: () => import('../views/admin/MarketingAudit.vue'),
        meta: { role: ROLES.ADMIN, title: '营销审核', section: '系统配置', description: '审核活动策略、投放对象与执行状态' },
      },
      {
        path: 'settings',
        name: 'AdminSettings',
        component: () => import('../views/admin/PermissionControl.vue'),
        meta: { role: ROLES.ADMIN, title: '权限控制', section: '系统配置', description: '维护后台模块权限与角色能力范围' },
      },
      { path: 'settings/params', redirect: '/admin/settings/params/basic' },
      {
        path: 'settings/params/basic',
        name: 'AdminSettingsParamsBasic',
        component: () => import('../views/admin/SystemParams.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '系统参数配置',
          section: '系统配置',
          description: '维护平台基础、计费、清分与通知参数',
          settingsSection: 'basic',
        },
      },
      {
        path: 'settings/params/billing',
        name: 'AdminSettingsParamsBilling',
        component: () => import('../views/admin/SystemParams.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '系统参数配置',
          section: '系统配置',
          description: '维护平台基础、计费、清分与通知参数',
          settingsSection: 'billing',
        },
      },
      {
        path: 'settings/params/settlement',
        name: 'AdminSettingsParamsSettlement',
        component: () => import('../views/admin/SystemParams.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '系统参数配置',
          section: '系统配置',
          description: '维护平台基础、计费、清分与通知参数',
          settingsSection: 'settlement',
        },
      },
      {
        path: 'settings/params/notification',
        name: 'AdminSettingsParamsNotification',
        component: () => import('../views/admin/SystemParams.vue'),
        meta: {
          role: ROLES.ADMIN,
          title: '系统参数配置',
          section: '系统配置',
          description: '维护平台基础、计费、清分与通知参数',
          settingsSection: 'notification',
        },
      },
      { path: 'settings/rules', redirect: '/admin/settings/params/notification' },
    ],
  },
  {
    path: '/operator',
    component: MainLayout,
    meta: { role: ROLES.OPERATOR },
    children: [
      {
        path: '',
        name: 'OperatorDashboard',
        component: OperatorDashboard,
        meta: { role: ROLES.OPERATOR, title: '运营工作台', section: '总览', description: '查看订单、营收、设备与电站运营情况' },
      },
      {
        path: 'stations',
        name: 'OperatorStations',
        component: () => import('../views/stations/StationList.vue'),
        meta: {
          role: ROLES.OPERATOR,
          title: '电站管理',
          section: '资产管理',
          description: '维护电站资料、审核状态与运营信息',
          keepAlive: true,
        },
      },
      {
        path: 'stations/chargers',
        name: 'OperatorStationsChargers',
        component: () => import('../views/stations/PileManagement.vue'),
        meta: {
          role: ROLES.OPERATOR,
          title: '电桩管理',
          section: '资产管理',
          description: '维护电桩编号、功率、状态与所属电站',
          keepAlive: true,
        },
      },
      {
        path: 'billing',
        name: 'OperatorBilling',
        component: () => import('../views/stations/PricingSettings.vue'),
        meta: { role: ROLES.OPERATOR, title: '电价设置', section: '计费管理', description: '维护时段价格、服务费与电价规则' },
      },
      {
        path: 'billing/templates',
        name: 'OperatorBillingTemplates',
        component: () => import('../views/operator/BillingTemplates.vue'),
        meta: { role: ROLES.OPERATOR, title: '电价模板管理', section: '计费管理', description: '维护可复用计费模板与适用范围' },
      },
      { path: 'orders', redirect: '/operator/orders/history' },
      {
        path: 'orders/history',
        name: 'OperatorOrdersHistory',
        component: () => import('../views/orders/HistoryOrders.vue'),
        meta: {
          role: ROLES.OPERATOR,
          title: '历史订单',
          section: '订单管理',
          description: '查看已完成订单与结算信息',
          keepAlive: true,
        },
      },
      {
        path: 'orders/realtime',
        name: 'OperatorOrdersRealtime',
        component: () => import('../views/orders/RealtimeOrders.vue'),
        meta: { role: ROLES.OPERATOR, title: '实时订单', section: '订单管理', description: '监控当前充电订单与实时状态' },
      },
      {
        path: 'orders/abnormal',
        name: 'OperatorOrdersAbnormal',
        component: () => import('../views/orders/AbnormalOrders.vue'),
        meta: {
          role: ROLES.OPERATOR,
          title: '异常订单',
          section: '订单管理',
          description: '查看异常订单与复核结果',
          keepAlive: true,
        },
      },
      {
        path: 'orders/detail/:id',
        name: 'OperatorOrderDetail',
        component: () => import('../views/orders/OrderDetailPage.vue'),
        meta: { role: ROLES.OPERATOR, title: '订单详情', section: '订单管理', description: '查看订单完整交易与状态明细' },
      },
      {
        path: 'finance',
        name: 'OperatorFinance',
        component: () => import('../views/finance/Settlement.vue'),
        meta: { role: ROLES.OPERATOR, title: '收益对账', section: '财务管理', description: '查看营收、对账结果与结算状态' },
      },
      {
        path: 'finance/bank-card',
        name: 'OperatorFinanceBankCard',
        component: () => import('../views/finance/CardManagement.vue'),
        meta: { role: ROLES.OPERATOR, title: '绑卡管理', section: '财务管理', description: '维护结算账户与收款银行卡信息' },
      },
      {
        path: 'finance/invoices',
        name: 'OperatorFinanceInvoices',
        component: () => import('../views/finance/InvoiceManagement.vue'),
        meta: {
          role: ROLES.OPERATOR,
          title: '发票管理',
          section: '财务管理',
          description: '处理发票申请与开票记录',
          keepAlive: true,
        },
      },
      {
        path: 'customers',
        name: 'OperatorCustomers',
        component: () => import('../views/operator/CustomerOverview.vue'),
        meta: { role: ROLES.OPERATOR, title: '车队与白名单', section: '客户管理', description: '管理车队客户、白名单与合作用户' },
      },
      {
        path: 'customers/fleets',
        name: 'OperatorCustomerFleets',
        component: () => import('../views/operator/FleetManagement.vue'),
        meta: { role: ROLES.OPERATOR, title: '专属用户管理', section: '客户管理', description: '维护重点客户、专属权益与用户关系' },
      },
      {
        path: 'customers/tags',
        name: 'OperatorCustomerTags',
        component: () => import('../views/operator/TagManagement.vue'),
        meta: { role: ROLES.OPERATOR, title: '标签管理', section: '客户管理', description: '配置用户标签、分层与运营标记' },
      },
      {
        path: 'marketing',
        name: 'OperatorMarketing',
        component: () => import('../views/operator/MarketingDiscounts.vue'),
        meta: { role: ROLES.OPERATOR, title: '折扣优惠', section: '营销管理', description: '管理折扣活动、优惠策略与投放计划' },
      },
      {
        path: 'marketing/coupons',
        name: 'OperatorMarketingCoupons',
        component: () => import('../views/operator/CouponManagement.vue'),
        meta: { role: ROLES.OPERATOR, title: '优惠券发放', section: '营销管理', description: '管理优惠券模板、投放与使用情况' },
      },
      {
        path: 'settings',
        name: 'OperatorSettings',
        component: () => import('../views/operator/OperatorSettings.vue'),
        meta: { role: ROLES.OPERATOR, title: '运营商设置', section: '系统', description: '维护运营主体资料与基础设置' },
      },
    ],
  },
  { path: '/overview', redirect: () => roleAwareRedirect({ admin: '/admin', operator: '/operator' }) },
  { path: '/orders/history', redirect: () => roleAwareRedirect({ admin: '/admin/orders', operator: '/operator/orders/history' }) },
  { path: '/orders/realtime', redirect: () => roleAwareRedirect({ admin: '/admin/orders', operator: '/operator/orders/realtime' }) },
  { path: '/orders/abnormal', redirect: () => roleAwareRedirect({ admin: '/admin/orders/abnormal', operator: '/operator/orders/abnormal' }) },
  { path: '/finance/cards', redirect: '/operator/finance/bank-card' },
  { path: '/finance/settlement', redirect: '/operator/finance' },
  { path: '/finance/global-settle', redirect: '/admin/finance' },
  { path: '/finance/invoice', redirect: () => roleAwareRedirect({ admin: '/admin/finance/invoices', operator: '/operator/finance/invoices' }) },
  { path: '/stations/list', redirect: '/operator/stations' },
  { path: '/stations/piles', redirect: '/operator/stations/chargers' },
  { path: '/stations/pricing', redirect: '/operator/billing' },
  { path: '/stations/review', redirect: '/admin/institutions/stations' },
  { path: '/organizations/operators', redirect: '/admin/institutions' },
  { path: '/organizations/exclusive', redirect: '/operator/customers/fleets' },
  { path: '/users/fleet', redirect: '/operator/customers' },
  { path: '/users/whitelist', redirect: '/operator/customers' },
  { path: '/marketing/tags', redirect: '/operator/customers/tags' },
  { path: '/marketing/discounts', redirect: '/operator/marketing' },
  { path: '/role-blueprint', redirect: () => roleAwareRedirect({ admin: '/admin/settings', operator: '/operator/settings' }) },
  { path: '/settings', redirect: () => roleAwareRedirect({ admin: '/admin/settings', operator: '/operator/settings' }) },
  { path: '/legacy-placeholder', component: PlaceholderPage },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const roleFromPath = getRoleByPath(to.path)
  if (roleFromPath) {
    setStoredRole(roleFromPath)
    return true
  }

  if (to.path === '/') {
    return resolveRoleDefaultRoute(getStoredRole())
  }

  return true
})

export default router
