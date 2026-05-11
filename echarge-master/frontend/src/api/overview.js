import http from './http.js'

export const fetchOverviewSummary = () => http.get('/overview/summary')

export const fetchRealtimeOrders = () => http.get('/overview/realtime-orders')

