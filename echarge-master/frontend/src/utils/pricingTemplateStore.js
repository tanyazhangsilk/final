import { mockOperatorStations, mockPricingTemplates } from '../mock/backoffice'
import { readLocalState, writeLocalState } from './localState'

const TEMPLATE_KEY = 'echarge-local-pricing-templates'
const BINDING_KEY = 'echarge-local-template-bindings'

const nowText = () =>
  new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })

const normalizePeriods = (periods = []) =>
  periods.map((item, index) => ({
    id: item.id ?? index + 1,
    type: item.type || 'flat',
    type_text: item.type_text || (item.type === 'peak' ? '高峰' : item.type === 'valley' ? '低谷' : '平段'),
    time_range: item.time_range || '',
    ele_fee: Number(item.ele_fee ?? 0),
    service_fee: Number(item.service_fee ?? 0),
  }))

const seedTemplates = () => {
  const stored = readLocalState(TEMPLATE_KEY, [])
  if (stored.length) return stored
  writeLocalState(TEMPLATE_KEY, mockPricingTemplates)
  return readLocalState(TEMPLATE_KEY, mockPricingTemplates)
}

const seedBindings = () => {
  const stored = readLocalState(BINDING_KEY, {})
  if (Object.keys(stored).length) return stored
  const initial = mockOperatorStations.reduce((result, station) => {
    if (station.price_template_id) {
      result[String(station.id)] = station.price_template_id
    }
    return result
  }, {})
  writeLocalState(BINDING_KEY, initial)
  return initial
}

export const getLocalPricingTemplates = () =>
  seedTemplates().map((item) => ({
    ...item,
    periods: normalizePeriods(item.periods || []),
  }))

export const mergePricingTemplates = (remoteRows = []) => {
  const localRows = getLocalPricingTemplates()
  const merged = [...remoteRows, ...localRows]
  const seen = new Set()
  return merged.filter((item) => {
    const key = String(item.id)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export const saveLocalPricingTemplate = (payload) => {
  const list = getLocalPricingTemplates()
  const nextId = payload.id ?? `local-template-${Date.now()}`
  const record = {
    id: nextId,
    name: payload.name,
    peak_price: Number(payload.peak_price ?? 0),
    flat_price: Number(payload.flat_price ?? 0),
    valley_price: Number(payload.valley_price ?? 0),
    service_price: Number(payload.service_price ?? 0),
    scope: payload.scope || 'station',
    status: payload.status || 'active',
    stations: Number(payload.stations || 0),
    description: payload.description || '',
    updated_at: nowText(),
    periods: normalizePeriods(payload.periods || []),
  }
  const nextList = list.filter((item) => String(item.id) !== String(record.id))
  nextList.unshift(record)
  writeLocalState(TEMPLATE_KEY, nextList)
  return record
}

export const getStationTemplateBindings = () => seedBindings()

export const applyLocalTemplateToStations = (templateId, stationIds = []) => {
  const bindings = seedBindings()
  stationIds.forEach((stationId) => {
    bindings[String(stationId)] = templateId
  })
  writeLocalState(BINDING_KEY, bindings)
  return bindings
}

export const enrichStationsWithTemplateBindings = (stations = [], templates = []) => {
  const mergedTemplates = mergePricingTemplates(templates)
  const templateMap = new Map(mergedTemplates.map((item) => [String(item.id), item]))
  const bindings = seedBindings()

  return stations.map((station) => {
    const bindingId = station.price_template_id ?? bindings[String(station.id)] ?? null
    const template = bindingId != null ? templateMap.get(String(bindingId)) : null
    return {
      ...station,
      price_template_id: bindingId,
      price_template_name: template?.name || station.price_template_name || '',
    }
  })
}
