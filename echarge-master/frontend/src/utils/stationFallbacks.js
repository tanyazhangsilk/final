import { mockOperatorStations } from '../mock/backoffice'
import { buildPendingDraftStations, mergeStationApplicationDraft } from './stationApplicationDrafts'
import { enrichStationsWithTemplateBindings } from './pricingTemplateStore'

const normalize = (value) => String(value || '').trim().toLowerCase()

const buildBaseStations = () => {
  const baseRows = enrichStationsWithTemplateBindings(mockOperatorStations.map(mergeStationApplicationDraft))
  const drafts = buildPendingDraftStations(baseRows)
  return [...baseRows, ...drafts]
}

export const getFallbackStationRows = (params = {}) => {
  const rows = buildBaseStations()
  const keyword = normalize(params.keyword)
  const status = params.status === undefined || params.status === null || params.status === '' ? null : Number(params.status)
  const visibility = params.visibility ? String(params.visibility) : ''
  const page = Math.max(1, Number(params.page || 1))
  const pageSize = Math.max(1, Number(params.page_size || params.pageSize || 10))

  const filtered = rows.filter((item) => {
    const matchKeyword =
      !keyword ||
      [item.station_name, item.full_address, item.contact_name, item.contact_phone, item.price_template_name]
        .filter(Boolean)
        .some((field) => normalize(field).includes(keyword))
    const matchStatus = status == null || Number(item.status) === status
    const matchVisibility = !visibility || item.visibility === visibility
    return matchKeyword && matchStatus && matchVisibility
  })

  const start = (page - 1) * pageSize
  const items = filtered.slice(start, start + pageSize)

  return {
    items,
    total: filtered.length,
    page,
    page_size: pageSize,
    summary: {
      total_count: filtered.length,
      online_count: filtered.filter((item) => Number(item.status) === 0).length,
      pending_count: filtered.filter((item) => Number(item.status) === 3).length,
      private_count: filtered.filter((item) => item.visibility !== 'public').length,
    },
  }
}

export const getFallbackStationOptions = () =>
  buildBaseStations().map((item) => ({
    id: item.id,
    station_name: item.station_name,
    full_address: item.full_address,
    status: item.status,
    status_text: item.status_text,
    visibility: item.visibility,
    visibility_text: item.visibility_text,
    price_template_id: item.price_template_id || null,
    price_template_name: item.price_template_name || '',
    operator_name: item.operator_name,
    is_local_draft: Boolean(item.is_local_draft),
  }))

export const getFallbackStationAudits = () =>
  buildBaseStations()
    .sort((left, right) => String(right.created_at || '').localeCompare(String(left.created_at || '')))
    .map((item) => ({
      ...item,
      audit_remark: item.audit_remark || '等待审核',
    }))
