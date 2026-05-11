const clone = (value) => {
  if (typeof structuredClone === 'function') {
    return structuredClone(value)
  }
  return JSON.parse(JSON.stringify(value))
}

const isEmptyArrayWithFallback = (value, fallbackValue, options = {}) =>
  options.preferFallbackOnEmptyArray &&
  Array.isArray(value) &&
  value.length === 0 &&
  Array.isArray(fallbackValue) &&
  fallbackValue.length > 0

export const hasLocalState = (key) => {
  try {
    return localStorage.getItem(key) != null
  } catch (error) {
    return false
  }
}

export const readLocalState = (key, fallbackValue, options = {}) => {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) {
      return clone(fallbackValue)
    }
    const parsed = JSON.parse(raw)
    if (isEmptyArrayWithFallback(parsed, fallbackValue, options)) {
      return clone(fallbackValue)
    }
    return parsed
  } catch (error) {
    return clone(fallbackValue)
  }
}

export const writeLocalState = (key, value, options = {}) => {
  if (options.skipEmptyArray && Array.isArray(value) && value.length === 0) {
    return value
  }
  localStorage.setItem(key, JSON.stringify(value))
  return value
}

export const readLocalListState = (key, fallbackList = []) =>
  readLocalState(key, fallbackList, { preferFallbackOnEmptyArray: true })

export const writeLocalListState = (key, value) => writeLocalState(key, value, { skipEmptyArray: true })

export const upsertLocalItem = (key, item, fallbackList = [], matcher = (current) => current.id === item.id) => {
  const list = readLocalState(key, fallbackList)
  const index = list.findIndex((current) => matcher(current))
  if (index === -1) {
    list.unshift(item)
  } else {
    list.splice(index, 1, { ...list[index], ...item })
  }
  writeLocalState(key, list)
  return list
}
