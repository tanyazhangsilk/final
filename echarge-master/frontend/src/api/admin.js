import http, { httpMutation } from './http'
import { mockAdminUsers, mockBlacklistRows, mockMarketingAudits } from '../mock/backoffice'

const clone = (value) => JSON.parse(JSON.stringify(value))
const resolveMock = (data, extra = {}) => Promise.resolve({ data: { data: clone(data), ...clone(extra) } })

let adminUsersState = clone(mockAdminUsers.rows)
let blacklistState = clone(mockBlacklistRows)
let marketingAuditsState = clone(mockMarketingAudits)

const getAdminUserSummary = () => ({
  total_users: adminUsersState.length,
  active_users: adminUsersState.filter((item) => item.status !== 'blacklisted').length,
  blacklisted_users: adminUsersState.filter((item) => item.status === 'blacklisted').length,
})

export const fetchOperatorAudits = () => http.get('/admin/operators/audits')
export const processOperatorAudit = (id, payload) => httpMutation.post(`/admin/operators/${id}/process`, payload)

/** 运营商入驻审核（详情页数据源，MySQL busi_operator_audit_applications） */
export const fetchOperatorAuditApplications = () => http.get('/admin/audit/operator-applications')
export const createOperatorAuditApplication = (payload) => httpMutation.post('/admin/audit/operator-applications', payload)
export const processOperatorAuditApplication = (applicationId, payload) =>
  httpMutation.post(`/admin/audit/operator-applications/${applicationId}/process`, payload)

export const fetchAdminUsers = () => resolveMock(adminUsersState, { summary: getAdminUserSummary() })
export const toggleAdminUserBlacklist = (id) => {
  const target = adminUsersState.find((item) => Number(item.id) === Number(id))
  if (target) {
    const nextBlacklisted = target.status !== 'blacklisted'
    target.status = nextBlacklisted ? 'blacklisted' : 'active'

    if (nextBlacklisted) {
      if (!blacklistState.some((item) => Number(item.id) === Number(id))) {
        blacklistState.unshift({
          id: target.id,
          name: target.name,
          phone: target.phone,
          reason: '运营风控演示名单',
          created_at: new Date().toLocaleString('zh-CN', { hour12: false }),
        })
      }
    } else {
      blacklistState = blacklistState.filter((item) => Number(item.id) !== Number(id))
    }
  }

  return Promise.resolve({ data: { message: 'ok' } })
}
export const fetchAdminBlacklist = () => resolveMock(blacklistState)

export const fetchMarketingAudits = () => http.get('/admin/marketing/audits')
export const processMarketingAudit = (id, payload) => httpMutation.post('/admin/marketing/audits/' + id + '/process', payload)
export const fetchSystemParams = () => http.get('/admin/settings/params')
export const updateSystemParams = (payload) => httpMutation.put('/admin/settings/params', payload)
export const fetchAdminPermissionSettings = () => http.get('/admin/settings/permissions')
export const updateAdminPermissionSettings = (payload) => httpMutation.put('/admin/settings/permissions', payload)

export const fetchStationAudits = (params = {}) => http.get('/admin/audit/stations', { params })
export const processStationAudit = (stationId, payload) =>
  httpMutation.post(`/admin/audit/stations/${stationId}/process`, payload)
export const fetchAdminStationOptions = (params = {}) => http.get('/admin/stations/options', { params })

export const fetchAdminOrders = (params = {}) => http.get('/admin/orders', { params })
export const fetchAdminAbnormalOrders = (params = {}) => http.get('/admin/orders/abnormal', { params })
export const fetchAdminOrderDetail = (orderId) => http.get(`/admin/orders/${orderId}`)
export const markAdminOrderAbnormal = (orderId, abnormalReason) =>
  httpMutation.post(`/admin/orders/${orderId}/mark-abnormal`, { abnormal_reason: abnormalReason })
