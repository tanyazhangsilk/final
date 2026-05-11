/**
 * 保存模板到列表（纯函数）/ Save template into list (pure function)
 * @param {Array} templates 模板列表 / Template list
 * @param {string} id 模板ID / Template id
 * @param {{name:string,isDefault:boolean,stationIds:string[]}} payload 基础信息 / Basic payload
 * @param {Array} periods 时段数组 / Periods
 * @returns {Array} 新模板列表 / Next templates
 */
export const saveTemplateToList = (templates, id, payload, periods) => {
  const idx = (templates || []).findIndex((t) => t.id === id)
  if (idx < 0) return templates
  const next = [...templates]
  next[idx] = {
    ...next[idx],
    name: String(payload?.name || '').trim(),
    isDefault: Boolean(payload?.isDefault),
    stationIds: Array.isArray(payload?.stationIds) ? [...payload.stationIds] : [],
    periods: Array.isArray(periods) ? periods.map((p) => ({ ...p, timeRange: [...(p.timeRange || [])] })) : [],
  }
  return next
}

