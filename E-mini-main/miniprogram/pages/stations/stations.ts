import { getStations, withApiFallback } from '../../services/api'
import { StationItem, getStations as getMockStations } from '../../services/mock'

type SortKey = 'distance' | 'price' | 'idle' | 'fast'

function buildDisplayStations(stations: StationItem[], keyword: string, sortKey: SortKey) {
  const lowerKeyword = keyword.trim().toLowerCase()

  const filtered = stations.filter(item => {
    if (!lowerKeyword) {
      return true
    }
    return (
      item.name.toLowerCase().includes(lowerKeyword) ||
      item.address.toLowerCase().includes(lowerKeyword) ||
      item.operator.toLowerCase().includes(lowerKeyword)
    )
  })

  return filtered.sort((left, right) => {
    if (sortKey === 'distance') {
      return left.distanceValue - right.distanceValue
    }
    if (sortKey === 'price') {
      return left.currentPriceValue - right.currentPriceValue
    }
    if (sortKey === 'idle') {
      return right.available - left.available
    }
    return right.fastCount - left.fastCount
  })
}

Page({
  data: {
    loading: true,
    keyword: '',
    sortKey: 'distance' as SortKey,
    sortOptions: [
      { key: 'distance', label: '距离优先' },
      { key: 'price', label: '价格优先' },
      { key: 'idle', label: '空闲优先' },
      { key: 'fast', label: '快充优先' },
    ],
    stations: [],
    displayStations: [],
    empty: false,
  },

  async onLoad() {
    const stations = await withApiFallback(
      'stations:getStations',
      () => getStations(),
      () => getMockStations()
    )
    this.setData({
      loading: false,
      stations,
      displayStations: buildDisplayStations(stations, '', 'distance'),
      empty: stations.length === 0
    })
  },

  onShow() {
    if (typeof this.getTabBar === 'function') {
      const tabBar = this.getTabBar()
      if (tabBar) {
        tabBar.setData({ selected: 1 })
      }
    }
  },

  onSearchInput(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    const keyword = e.detail.value
    const displayStations = buildDisplayStations(this.data.stations, keyword, this.data.sortKey)
    this.setData({
      keyword,
      displayStations,
      empty: displayStations.length === 0
    })
  },

  selectSort(e: WechatMiniprogram.CustomEvent) {
    const { key } = e.currentTarget.dataset as { key: SortKey }
    const displayStations = buildDisplayStations(this.data.stations, this.data.keyword, key)
    this.setData({
      sortKey: key,
      displayStations,
      empty: displayStations.length === 0
    })
  },

  clearKeyword() {
    const displayStations = buildDisplayStations(this.data.stations, '', this.data.sortKey)
    this.setData({
      keyword: '',
      displayStations,
      empty: displayStations.length === 0
    })
  },

  onStationTap(e: WechatMiniprogram.CustomEvent) {
    const { id } = e.currentTarget.dataset as { id: string }
    wx.navigateTo({ url: `/pages/station-detail/station-detail?id=${id}` })
  },
})
