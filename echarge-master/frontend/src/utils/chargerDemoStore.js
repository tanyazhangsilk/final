const STORAGE_KEY = 'echarge-demo-chargers'

const statusTextMap = {
  0: '空闲',
  1: '充电中',
  2: '故障',
  3: '停用',
}

const readStore = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch (error) {
    return {}
  }
}

const writeStore = (value) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
}

const toStationKey = (stationId) => String(stationId)

const formatNow = () =>
  new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })

const createChargerRecord = (station, payload, sequence = 0) => {
  const stationCode = String(station?.id || 'ST').replace(/\D/g, '').padStart(3, '0')
  const snCode =
    payload.sn_code ||
    `${stationCode}${payload.type || 'DC'}${String(Date.now() + sequence).slice(-6).toUpperCase()}`

  return {
    id: `local-${Date.now()}-${sequence}`,
    station_id: station?.id,
    station_name: station?.station_name || '演示电站',
    sn_code: snCode,
    charger_name: payload.charger_name || `演示电桩 ${snCode.slice(-3)}`,
    type: payload.type || 'DC',
    power_kw: Number(payload.power_kw || 120),
    status: Number(payload.status ?? 0),
    status_text: statusTextMap[Number(payload.status ?? 0)] || '空闲',
    updated_at: formatNow(),
    is_local_demo: true,
  }
}

const buildSeedChargers = (station, count = 6) => {
  const stationName = station?.station_name || '演示电站'
  const basePower = Number(station?.total_power_kw || 0)
  const averagePower = count ? Math.max(7, Math.round((basePower || count * 120) / count)) : 120

  return Array.from({ length: count }).map((_, index) => {
    const status = index === 0 ? 1 : index === count - 1 ? 2 : 0
    return {
      id: `seed-${station?.id || 'demo'}-${index + 1}`,
      station_id: station?.id,
      station_name: stationName,
      sn_code: `ST${String(station?.id || 0).padStart(3, '0')}${index % 2 === 0 ? 'DC' : 'AC'}${String(index + 1).padStart(3, '0')}`,
      charger_name: `${stationName.slice(0, 10)}-${String(index + 1).padStart(2, '0')}号桩`,
      type: index % 2 === 0 ? 'DC' : 'AC',
      power_kw: index % 2 === 0 ? Math.max(60, averagePower) : Math.min(averagePower, 40),
      status,
      status_text: statusTextMap[status],
      updated_at: formatNow(),
      is_seed_demo: true,
    }
  })
}

export const getLocalChargers = (stationId) => {
  const store = readStore()
  return store[toStationKey(stationId)] || []
}

export const getFallbackChargersForStation = (station, remoteRows = []) => {
  const localRows = getLocalChargers(station?.id)
  const seedRows = buildSeedChargers(station, Math.max(4, Number(station?.planned_charger_count || 6)))
  return mergeChargersWithLocal(station?.id, [...remoteRows, ...seedRows, ...localRows])
}

export const mergeChargersWithLocal = (stationId, remoteRows = []) => {
  const localRows = getLocalChargers(stationId)
  const seen = new Set()
  const merged = []

  ;[...remoteRows, ...localRows].forEach((item) => {
    const key = item.id || item.sn_code
    if (!key || seen.has(key)) return
    seen.add(key)
    merged.push(item)
  })

  return merged
}

export const addLocalCharger = (station, payload) => {
  const store = readStore()
  const key = toStationKey(station?.id)
  const current = store[key] || []
  const created = createChargerRecord(station, payload)
  store[key] = [created, ...current]
  writeStore(store)
  return created
}

export const batchAddLocalChargers = (station, payload) => {
  const count = Math.max(1, Number(payload.count || 1))
  const store = readStore()
  const key = toStationKey(station?.id)
  const current = store[key] || []
  const created = Array.from({ length: count }).map((_, index) =>
    createChargerRecord(
      station,
      {
        charger_name: `${station?.station_name || '演示电站'} ${payload.type || 'DC'} 桩 ${String(index + 1).padStart(2, '0')}`,
        type: payload.type,
        power_kw: payload.power_kw,
        status: 0,
      },
      index,
    ),
  )
  store[key] = [...created, ...current]
  writeStore(store)
  return created
}

export const regenerateLocalChargers = (station, payload = {}) => {
  const store = readStore()
  const key = toStationKey(station?.id)
  store[key] = buildSeedChargers(station, Math.max(4, Number(payload.count || station?.planned_charger_count || 6)))
  writeStore(store)
  return store[key]
}

export const updateLocalChargerStatus = (stationId, chargerId, status) => {
  const store = readStore()
  const key = toStationKey(stationId)
  const rows = store[key] || []
  store[key] = rows.map((item) =>
    item.id === chargerId
      ? {
          ...item,
          status: Number(status),
          status_text: statusTextMap[Number(status)] || '空闲',
          updated_at: formatNow(),
        }
      : item,
  )
  writeStore(store)
}
