import { operatorConsoleMock, stationAuditMock } from '../mock/console'
import { adminDashboardMock } from '../mock/adminDashboard'

const clone = (value) => JSON.parse(JSON.stringify(value))

const simulateRequest = (payload, delay = 320) =>
  new Promise((resolve) => {
    window.setTimeout(() => {
      resolve({
        code: 0,
        message: 'ok',
        data: clone(payload),
      })
    }, delay)
  })

export const fetchAdminDashboard = () => simulateRequest(adminDashboardMock)

export const fetchStationAuditPage = () => simulateRequest(stationAuditMock)

export const fetchOperatorDashboard = () => simulateRequest(operatorConsoleMock)
