import { get } from '../utils/request'

export interface StationListParams {
  keyword?: string,
  city?: string
}

export interface StationDetailParams {
  id: string
}

export interface StationApiItem {
  id?: string | number
  station_id?: string | number
  stationId?: string | number
  name?: string,
  station_name?: string,
  stationName?: string,
  address?: string,
  location?: string,
  detail_address?: string,
  operator?: string,
  operator_name?: string,
  brand?: string,
  provider?: string,
  available?: number,
  available_count?: number,
  idle_piles?: number,
  idleCount?: number,
  total?: number,
  total_piles?: number,
  totalCount?: number
  [key: string]: unknown
}

export interface StationListResult {
  list?: StationApiItem[]
  results?: StationApiItem[]
  items?: StationApiItem[]
}

export function getStationList(params?: StationListParams) {
  return get<StationApiItem[] | StationListResult>('/stations', params)
}

export function getStationDetail({ id }: StationDetailParams) {
  return get<StationApiItem>(`/stations/${id}`)
}
