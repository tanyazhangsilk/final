/**
 * 将 HH:mm 转换为分钟数 / Parse HH:mm to minutes
 * @param {string} value
 * @returns {number|null}
 */
export const parseTimeToMinutes = (value) => {
  if (!value) return null
  if (value === '24:00') return 1440
  const m = /^(\d{2}):(\d{2})$/.exec(String(value))
  if (!m) return null
  const hh = Number(m[1])
  const mm = Number(m[2])
  if (Number.isNaN(hh) || Number.isNaN(mm)) return null
  if (hh < 0 || hh > 23) return null
  if (mm < 0 || mm > 59) return null
  return hh * 60 + mm
}

/**
 * 将分钟数格式化为 HH:mm / Format minutes to HH:mm
 * @param {number} minutes
 * @returns {string}
 */
export const minutesToTime = (minutes) => {
  const m = Math.max(0, Math.min(1440, Number(minutes || 0)))
  if (m === 1440) return '24:00'
  const hh = String(Math.floor(m / 60)).padStart(2, '0')
  const mm = String(m % 60).padStart(2, '0')
  return `${hh}:${mm}`
}

/**
 * 禁用分钟：只允许 00 / 30（00:30 step）/ Disable minutes except 0/30
 * @returns {number[]}
 */
export const disabledMinutes30Step = () => {
  const disabled = []
  for (let i = 0; i < 60; i += 1) {
    if (i !== 0 && i !== 30) disabled.push(i)
  }
  return disabled
}

/**
 * 获取时段的起止分钟 / Get period minutes
 * @param {{timeRange?: [string,string]}} p
 * @returns {{start:number,end:number}|null}
 */
export const getPeriodMinutes = (p) => {
  const start = parseTimeToMinutes(p?.timeRange?.[0])
  const end = parseTimeToMinutes(p?.timeRange?.[1])
  if (start == null || end == null) return null
  if (end <= start) return null
  return { start, end }
}

/**
 * 判断是否存在重叠 / Detect overlap
 * @param {Array} periods
 * @returns {boolean}
 */
export const hasOverlap = (periods) => {
  const ranges = (periods || [])
    .map(getPeriodMinutes)
    .filter(Boolean)
    .sort((a, b) => a.start - b.start)

  for (let i = 1; i < ranges.length; i += 1) {
    if (ranges[i].start < ranges[i - 1].end) return true
  }
  return false
}

/**
 * 计算覆盖分钟数（合并重叠）/ Calculate covered minutes (merge overlaps)
 * @param {Array} periods
 * @returns {number}
 */
export const calcCoverageMinutes = (periods) => {
  const ranges = (periods || [])
    .map(getPeriodMinutes)
    .filter(Boolean)
    .sort((a, b) => a.start - b.start)

  if (ranges.length === 0) return 0
  let covered = 0
  let curStart = ranges[0].start
  let curEnd = ranges[0].end

  for (let i = 1; i < ranges.length; i += 1) {
    const r = ranges[i]
    if (r.start > curEnd) {
      covered += curEnd - curStart
      curStart = r.start
      curEnd = r.end
    } else {
      curEnd = Math.max(curEnd, r.end)
    }
  }

  covered += curEnd - curStart
  return covered
}

/**
 * 找到第一个空白时段 / Find first gap in 0..1440
 * @param {Array} periods
 * @returns {[number, number] | null}
 */
export const findFirstGap = (periods) => {
  const ranges = (periods || [])
    .map(getPeriodMinutes)
    .filter(Boolean)
    .sort((a, b) => a.start - b.start)

  let cursor = 0
  for (const r of ranges) {
    if (r.start > cursor) return [cursor, r.start]
    cursor = Math.max(cursor, r.end)
  }
  if (cursor < 1440) return [cursor, 1440]
  return null
}

/**
 * 为一个 gap 生成默认时段 / Create default period for a gap
 * @param {[number, number]} gap
 * @param {string} type
 */
export const createDefaultPeriodForGap = (gap, type) => {
  const [start, end] = gap
  const minEnd = Math.min(start + 60, end)
  return {
    id: `p-${Math.random().toString(16).slice(2, 10)}`,
    type,
    timeRange: [minutesToTime(start), minutesToTime(minEnd)],
    elecFee: 0.9000,
    serviceFee: 0.3000,
  }
}

