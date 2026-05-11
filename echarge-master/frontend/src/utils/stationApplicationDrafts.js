import { getStoredOperatorId } from '../config/permissions'

const STORAGE_KEY = 'echarge-station-application-drafts'

const readDrafts = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch (error) {
    return []
  }
}

const writeDrafts = (drafts) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts))
}

const normalizeText = (value) => String(value || '').trim()

const buildAddress = (payload) =>
  [payload.province, payload.city, payload.district, payload.address]
    .map((item) => normalizeText(item))
    .filter(Boolean)
    .join('')

const buildDraftKey = (payload, operatorId = getStoredOperatorId()) =>
  [operatorId, normalizeText(payload.station_name), buildAddress(payload)].filter(Boolean).join('::')

const withFallback = (primary, fallback) => {
  if (Array.isArray(primary)) {
    return primary.length ? primary : fallback || []
  }
  if (primary === undefined || primary === null || primary === '') {
    return fallback
  }
  return primary
}

export const saveStationApplicationDraft = (payload) => {
  const operatorId = getStoredOperatorId()
  const drafts = readDrafts()
  const fullAddress = [payload.province, payload.city, payload.district, payload.address]
    .map((item) => normalizeText(item))
    .filter(Boolean)
    .join(' ')

  const draft = {
    key: buildDraftKey(payload, operatorId),
    operator_id: operatorId,
    station_name: normalizeText(payload.station_name),
    province: normalizeText(payload.province),
    city: normalizeText(payload.city),
    district: normalizeText(payload.district),
    address: normalizeText(payload.address),
    full_address: fullAddress,
    longitude: payload.longitude,
    latitude: payload.latitude,
    contact_name: normalizeText(payload.contact_name),
    contact_phone: normalizeText(payload.contact_phone),
    operation_hours: normalizeText(payload.operation_hours),
    parking_fee_desc: normalizeText(payload.parking_fee_desc),
    station_remark: normalizeText(payload.station_remark),
    planned_charger_count: Number(payload.planned_charger_count || 0),
    total_power_kw: Number(payload.total_power_kw || 0),
    parking_slot_count: Number(payload.parking_slot_count || 0),
    service_radius_km: Number(payload.service_radius_km || 0),
    site_owner: normalizeText(payload.site_owner),
    grid_capacity_remark: normalizeText(payload.grid_capacity_remark),
    construction_phase: normalizeText(payload.construction_phase),
    support_vehicle_types: Array.isArray(payload.support_vehicle_types)
      ? payload.support_vehicle_types.filter(Boolean)
      : [],
    facility_tags: Array.isArray(payload.facility_tags) ? payload.facility_tags.filter(Boolean) : [],
    safety_contact_name: normalizeText(payload.safety_contact_name),
    safety_contact_phone: normalizeText(payload.safety_contact_phone),
    cover_image: normalizeText(payload.cover_image),
    site_photos: Array.isArray(payload.site_photos) ? payload.site_photos.filter(Boolean) : [],
    qualification_remark: normalizeText(payload.qualification_remark),
    updated_at: new Date().toISOString(),
  }

  const nextDrafts = drafts.filter((item) => item.key !== draft.key)
  nextDrafts.unshift(draft)
  writeDrafts(nextDrafts.slice(0, 100))
  return draft
}

export const findStationApplicationDraft = (station) => {
  const stationName = normalizeText(station?.station_name)
  if (!stationName) return null

  const fullAddress = normalizeText(station?.full_address || station?.address)
  const operatorId = station?.operator_id ? String(station.operator_id) : null

  return (
    readDrafts().find((draft) => {
      const sameStationName = draft.station_name === stationName
      if (!sameStationName) return false

      const sameOperator = !operatorId || !draft.operator_id || draft.operator_id === operatorId
      const sameAddress = !fullAddress || draft.full_address === fullAddress || draft.address === fullAddress
      return sameOperator && sameAddress
    }) || null
  )
}

export const mergeStationApplicationDraft = (station) => {
  const draft = findStationApplicationDraft(station)
  if (!draft) return station

  return {
    ...draft,
    ...station,
    province: withFallback(station.province, draft.province),
    city: withFallback(station.city, draft.city),
    district: withFallback(station.district, draft.district),
    address: withFallback(station.address, draft.address),
    full_address: withFallback(station.full_address, draft.full_address),
    longitude: withFallback(station.longitude, draft.longitude),
    latitude: withFallback(station.latitude, draft.latitude),
    contact_name: withFallback(station.contact_name, draft.contact_name),
    contact_phone: withFallback(station.contact_phone, draft.contact_phone),
    operation_hours: withFallback(station.operation_hours, draft.operation_hours),
    parking_fee_desc: withFallback(station.parking_fee_desc, draft.parking_fee_desc),
    station_remark: withFallback(station.station_remark, draft.station_remark),
    planned_charger_count: withFallback(station.planned_charger_count, draft.planned_charger_count),
    total_power_kw: withFallback(station.total_power_kw, draft.total_power_kw),
    parking_slot_count: withFallback(station.parking_slot_count, draft.parking_slot_count),
    service_radius_km: withFallback(station.service_radius_km, draft.service_radius_km),
    site_owner: withFallback(station.site_owner, draft.site_owner),
    grid_capacity_remark: withFallback(station.grid_capacity_remark, draft.grid_capacity_remark),
    construction_phase: withFallback(station.construction_phase, draft.construction_phase),
    support_vehicle_types: withFallback(station.support_vehicle_types, draft.support_vehicle_types),
    facility_tags: withFallback(station.facility_tags, draft.facility_tags),
    safety_contact_name: withFallback(station.safety_contact_name, draft.safety_contact_name),
    safety_contact_phone: withFallback(station.safety_contact_phone, draft.safety_contact_phone),
    cover_image: withFallback(station.cover_image, draft.cover_image),
    site_photos: withFallback(station.site_photos, draft.site_photos),
    qualification_remark: withFallback(station.qualification_remark, draft.qualification_remark),
  }
}

export const mergeStationApplicationList = (stations = []) => stations.map(mergeStationApplicationDraft)

export const buildPendingDraftStations = (stations = []) => {
  const existingKeys = new Set(
    stations.map((station) =>
      [normalizeText(station.station_name), normalizeText(station.full_address || station.address)].filter(Boolean).join('::'),
    ),
  )

  return readDrafts()
    .filter((draft) => {
      const key = [normalizeText(draft.station_name), normalizeText(draft.full_address || draft.address)].filter(Boolean).join('::')
      return key && !existingKeys.has(key)
    })
    .map((draft) => ({
      id: `draft-${draft.key}`,
      operator_id: draft.operator_id,
      operator_name: '当前运营商',
      station_name: draft.station_name,
      province: draft.province,
      city: draft.city,
      district: draft.district,
      address: draft.address,
      full_address: draft.full_address,
      longitude: draft.longitude,
      latitude: draft.latitude,
      contact_name: draft.contact_name,
      contact_phone: draft.contact_phone,
      operation_hours: draft.operation_hours,
      parking_fee_desc: draft.parking_fee_desc,
      station_remark: draft.station_remark,
      planned_charger_count: draft.planned_charger_count,
      total_power_kw: draft.total_power_kw,
      parking_slot_count: draft.parking_slot_count,
      service_radius_km: draft.service_radius_km,
      site_owner: draft.site_owner,
      grid_capacity_remark: draft.grid_capacity_remark,
      construction_phase: draft.construction_phase,
      support_vehicle_types: draft.support_vehicle_types,
      facility_tags: draft.facility_tags,
      safety_contact_name: draft.safety_contact_name,
      safety_contact_phone: draft.safety_contact_phone,
      cover_image: draft.cover_image,
      site_photos: draft.site_photos,
      qualification_remark: draft.qualification_remark,
      price_template_name: '',
      price_template_id: null,
      charger_count: 0,
      visibility: 'private',
      visibility_text: '未公开',
      status: 3,
      status_text: '待审核',
      audit_remark: '前端暂存申请，等待提交后端或管理员审核',
      created_at: draft.updated_at,
      updated_at: draft.updated_at,
      is_local_draft: true,
    }))
}
