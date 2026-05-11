// 充电站本地数据
export interface ChargingStation {
  id: string,
  name: string,
  address: string,
  operator: string,
  available: number,
  total: number
}

export const STATIONS: ChargingStation[] = [
  { id: '1', name: '天府软件园充电站', address: '深圳市南山区科技南路18号', operator: 'E-Charge', available: 4, total: 6 },
  { id: '2', name: '四川师范充电站', address: '深圳市福田区福华路88号', operator: '特来电', available: 2, total: 4 },
  { id: '3', name: '双流机场充电站', address: '深圳市宝安区航城大道', operator: '星星充电', available: 5, total: 8 },
  { id: '4', name: '龙华寺充电站', address: '深圳市龙华区大浪街道', operator: 'E-Charge', available: 3, total: 4 },
  { id: '5', name: '罗湖东门充电站', address: '深圳市罗湖区东门步行街', operator: '特来电', available: 1, total: 6 },
]
