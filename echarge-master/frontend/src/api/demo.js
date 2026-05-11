import http, { httpMutation } from './http'

export const fetchDemoFlowHealth = () => http.get('/demo/flow/health')

export const startDemoOrder = (payload) => httpMutation.post('/demo/orders/start', payload)
export const finishDemoOrder = (orderId) => httpMutation.post(`/demo/orders/${orderId}/finish`)
export const markDemoOrderAbnormal = (orderId, payload) => httpMutation.post(`/demo/orders/${orderId}/abnormal`, payload)
export const fetchDemoOrderDetail = (orderId) => http.get(`/demo/orders/${orderId}`)

export const applyDemoStation = (payload) => httpMutation.post('/demo/stations/apply', payload)
export const approveDemoStation = (stationId, payload) => httpMutation.post(`/demo/stations/${stationId}/approve`, payload)
export const rejectDemoStation = (stationId, payload) => httpMutation.post(`/demo/stations/${stationId}/reject`, payload)
export const createDemoStationCharger = (stationId, payload) =>
  httpMutation.post(`/demo/stations/${stationId}/chargers`, payload)
export const bindDemoStationTemplate = (stationId, payload) =>
  httpMutation.post(`/demo/stations/${stationId}/bind-template`, payload)

export const runDemoSettlement = (payload) => httpMutation.post('/demo/settlements/run', payload)
export const fetchDemoSettlements = () => http.get('/demo/settlements')

export const applyDemoInvoice = (payload) => httpMutation.post('/demo/invoices/apply', payload)
export const processDemoInvoice = (invoiceId, payload) => httpMutation.post(`/demo/invoices/${invoiceId}/process`, payload)
export const fetchDemoInvoices = () => http.get('/demo/invoices')
