/** 平台管理端在数据库暂无记录时，将前端 mock 订单映射为与列表接口一致的行结构 */

const fmtTime = (iso) => (iso ? String(iso).replace('T', ' ').slice(0, 19) : '')

const orderStatusCode = (status) => {
  if (status === 'abnormal') return 2
  if (status === 'charging') return 0
  return 1
}

const orderStatusText = (code) => {
  if (code === 2) return '异常结束'
  if (code === 0) return '充电中'
  return '已完成'
}

export function mapFrontOrderToAdminListRow(order, id) {
  const status = orderStatusCode(order.status)
  return {
    id,
    is_demo: true,
    order_no: order.orderNo,
    user_id: null,
    user_phone: order.phone,
    user_nickname: order.userName,
    operator_id: null,
    operator_name: order.operatorName,
    station_id: null,
    station_name: order.stationName,
    charger_id: null,
    charger_sn: '',
    charger_name: order.chargerName,
    vin: order.vin,
    start_time: fmtTime(order.startTime),
    end_time: fmtTime(order.endTime),
    charge_duration: order.chargeDuration,
    charge_duration_text: `${order.chargeDuration || 0} 分钟`,
    charge_amount: Number(order.chargeAmount || 0),
    electricity_fee: Number(order.electricityFee || 0),
    ele_fee: Number(order.electricityFee || 0),
    service_fee: Number(order.serviceFee || 0),
    total_amount: Number(order.totalAmount || 0),
    total_fee: Number(order.totalAmount || 0),
    pay_status: order.payStatus === 'paid' ? 1 : 0,
    pay_status_text: order.payStatus === 'paid' ? '已支付' : '待支付',
    status,
    status_text: orderStatusText(status),
    source_type: 'mini_program',
    source_type_text: '微信小程序',
    abnormal_reason: order.abnormalReason || '',
    created_at: fmtTime(order.createdAt),
    updated_at: fmtTime(order.updatedAt),
  }
}

export function buildAdminHistoryDemoPayload(mockOrders, pageSize) {
  const completed = mockOrders.filter((o) => o.status === 'completed').slice(0, Math.max(8, pageSize))
  const items = completed.map((o, i) => mapFrontOrderToAdminListRow(o, -910_001 - i))
  const total_charge_amount = items.reduce((s, r) => s + Number(r.charge_amount || 0), 0)
  const total_amount = items.reduce((s, r) => s + Number(r.total_amount || 0), 0)
  const total_service_fee = items.reduce((s, r) => s + Number(r.service_fee || 0), 0)
  return {
    items,
    total: items.length,
    page: 1,
    page_size: pageSize,
    summary: {
      total_count: items.length,
      total_charge_amount,
      total_amount,
      total_service_fee,
    },
  }
}

export function buildAdminAbnormalDemoPayload(mockOrders, pageSize) {
  const abnormal = mockOrders.filter((o) => o.status === 'abnormal').slice(0, Math.max(6, pageSize))
  const items = abnormal.map((o, i) => mapFrontOrderToAdminListRow(o, -920_001 - i))
  const total_amount = items.reduce((s, r) => s + Number(r.total_amount || 0), 0)
  const reasons = new Set(items.map((r) => r.abnormal_reason).filter(Boolean))
  return {
    items,
    total: items.length,
    page: 1,
    page_size: pageSize,
    summary: {
      total_count: items.length,
      total_amount,
      reason_count: reasons.size,
      abnormal_count: items.length,
    },
  }
}

const STATION_STATUS_TEXT = {
  0: '已审核通过',
  3: '待审核',
  4: '已驳回',
}

const mockStatusToCode = (s) => {
  if (s === 'approved') return 0
  if (s === 'rejected') return 4
  return 3
}

export function buildStationAuditDemoItems(records = []) {
  return records.map((rec, index) => {
    const status = mockStatusToCode(rec.status)
    const full = [rec.city, rec.address].filter(Boolean).join(' ')
    return {
      id: -930_001 - index,
      is_demo: true,
      station_name: rec.stationName,
      operator_id: null,
      operator_name: rec.operatorName || '',
      province: '',
      city: rec.city || '',
      district: '',
      address: rec.address || '',
      full_address: full || rec.stationName,
      longitude: Number(rec.longitude) || 0,
      latitude: Number(rec.latitude) || 0,
      lng: Number(rec.longitude) || 0,
      lat: Number(rec.latitude) || 0,
      contact_name: rec.contactName || '',
      contact_phone: rec.contactPhone || '',
      operation_hours: rec.businessHours || '',
      parking_fee_desc: '',
      station_remark: rec.remark || '',
      planned_charger_count: Number(rec.connectorCount || 0),
      planned_piles: Number(rec.connectorCount || 0),
      total_power_kw: Number(rec.totalPowerKw || 0),
      total_power: Number(rec.totalPowerKw || 0),
      cover_image: '',
      site_photos: Array.isArray(rec.amenities) ? rec.amenities.map(String) : [],
      qualification_remark: rec.gridStatus || '',
      parking_slot_count: rec.parkingSlots != null ? Number(rec.parkingSlots) : null,
      service_radius_km: rec.serviceRadiusKm != null ? Number(rec.serviceRadiusKm) : null,
      site_owner: '',
      construction_phase: rec.stationType || '',
      grid_capacity_remark: '',
      support_vehicle_types: [],
      facility_tags: Array.isArray(rec.amenities) ? [...rec.amenities] : [],
      safety_contact_name: '',
      safety_contact_phone: '',
      audit_remark: '',
      status,
      status_text: STATION_STATUS_TEXT[status] || '未知状态',
      visibility: 'private',
      visibility_text: '私有站点',
      charger_count: Number(rec.connectorCount || 0),
      price_template_id: null,
      price_template_name: '未绑定模板',
      created_at: rec.submittedAt || '',
      updated_at: rec.submittedAt || '',
      can_bind_template: false,
      can_manage_chargers: false,
      can_publish: false,
    }
  })
}

export function buildStationAuditDemoSummary(items) {
  return {
    total_count: items.length,
    pending_count: items.filter((r) => Number(r.status) === 3).length,
    approved_count: items.filter((r) => Number(r.status) === 0).length,
    rejected_count: items.filter((r) => Number(r.status) === 4).length,
  }
}
