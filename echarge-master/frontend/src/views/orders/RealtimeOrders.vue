<script setup>
import { computed, nextTick, onActivated, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Lightning, Money, Plus, RefreshRight, Tickets } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import {
  finishOperatorOrder,
  fetchOperatorOrderStartOptions,
  fetchOperatorRealtimeOrders,
  fetchStationChargers,
  markOperatorOrderAbnormal,
  startDemoCharging,
} from '../../api/operator'
import {
  buildRequestCacheKey,
  bumpOperatorOrderDataEpoch,
  clearOperatorOrderListCaches,
  clearOperatorOrderStartOptionsCaches,
  clearOperatorRealtimeListCache,
  clearStationChargersCachesForStation,
  formatCacheLabel,
  getOperatorOrderDataEpoch,
  getRequestCache,
  setRequestCache,
  shouldRefreshRequestCache,
} from '../../utils/requestCache'

let realtimePollTimer = null
/** 充电中列表与「结束/异常」后各列表对齐，不宜过长间隔 */
const REALTIME_POLL_MS = 6000

/** 将实时订单列表请求串行化，避免轮询、创建成功、页面激活同时发起多路相同请求 */
let realtimeOrdersFetchTail = Promise.resolve()

/** >0 时暂停轮询，避免与写订单争用连接 */
const realtimeMutationDepth = ref(0)

const pauseRealtimePoll = () => {
  realtimeMutationDepth.value += 1
  if (realtimePollTimer) {
    window.clearInterval(realtimePollTimer)
    realtimePollTimer = null
  }
}

const resumeRealtimePoll = () => {
  realtimeMutationDepth.value = Math.max(0, realtimeMutationDepth.value - 1)
  if (
    realtimeMutationDepth.value === 0 &&
    typeof document !== 'undefined' &&
    document.visibilityState !== 'hidden'
  ) {
    scheduleRealtimePoll()
  }
}

const scheduleRealtimePoll = () => {
  if (realtimeMutationDepth.value > 0) {
    return
  }
  if (realtimePollTimer) {
    window.clearInterval(realtimePollTimer)
    realtimePollTimer = null
  }
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    return
  }
  realtimePollTimer = window.setInterval(() => {
    if (document.visibilityState !== 'visible') return
    if (realtimeMutationDepth.value > 0) return
    clearOperatorRealtimeListCache()
    void loadOrders({ background: true })
  }, REALTIME_POLL_MS)
}

const onRealtimeVisibility = () => {
  if (document.visibilityState === 'visible') {
    void loadOrders({ background: true })
    scheduleRealtimePoll()
  } else if (realtimePollTimer) {
    window.clearInterval(realtimePollTimer)
    realtimePollTimer = null
  }
}

const router = useRouter()
const CACHE_TTL = 5000

const loading = ref(false)
const tableReady = ref(false)
const orders = ref([])
const total = ref(0)
const busyOrderId = ref(null)
const cacheLabel = ref('')

const startDialogVisible = ref(false)
const startLoading = ref(false)
const startOptionsLoading = ref(false)
const startMode = ref('manual_demo')
const startUsers = ref([])
const startStations = ref([])
const startChargers = ref([])

const pagination = reactive({ page: 1, pageSize: 10 })
const summary = reactive({
  total_count: 0,
  total_charge_amount: 0,
  total_ele_fee: 0,
  total_service_fee: 0,
})
const startForm = reactive({
  user_id: null,
  station_id: null,
  charger_id: null,
  source_type: 'manual_demo',
})

const queryParams = computed(() => ({ page: pagination.page, page_size: pagination.pageSize }))
const listCacheKey = computed(() => buildRequestCacheKey('/operator/orders/realtime', queryParams.value))
const startCacheKey = computed(() =>
  buildRequestCacheKey('/operator/orders/start-options', {
    scope: 'start-options',
    station_id: startForm.station_id || '',
  }),
)
const manualStations = computed(() => startStations.value.filter((item) => Number(item.status) === 0))
const sourceTypeLabel = computed(() => (startMode.value === 'manual_demo' ? '演示创建订单' : '扫码充电'))

const formatMoney = (value) => `¥${Number(value || 0).toFixed(2)}`

/** 与后端 _build_order_summary 对齐，避免 Object.assign 时缺字段导致旧数字残留 */
const REALTIME_SUMMARY_DEFAULTS = {
  total_count: 0,
  total_charge_amount: 0,
  total_ele_fee: 0,
  total_service_fee: 0,
  total_amount: 0,
  charging_count: 0,
  completed_count: 0,
  abnormal_count: 0,
  station_count: 0,
  reason_count: 0,
}

const stats = computed(() => [
  {
    label: '实时订单',
    value: summary.total_count,
    suffix: ' 单',
    trend: '当前处于充电中的订单数',
    trendLabel: '支持结束和异常处理',
    tone: 'primary',
    icon: Lightning,
  },
  {
    label: '实时电量',
    value: Number(summary.total_charge_amount || 0).toFixed(2),
    suffix: ' kWh',
    trend: '实时订单累计电量',
    trendLabel: '用于演示当前负载',
    tone: 'success',
    icon: DataAnalysis,
  },
  {
    label: '实时电费',
    value: Number(summary.total_ele_fee || 0).toFixed(2),
    prefix: '¥',
    trend: '实时订单累计电费',
    trendLabel: '按当前计费结果汇总',
    tone: 'warning',
    icon: Money,
  },
  {
    label: '实时服务费',
    value: Number(summary.total_service_fee || 0).toFixed(2),
    prefix: '¥',
    trend: '实时订单累计服务费',
    trendLabel: '与电费共同构成总额',
    tone: 'info',
    icon: Tickets,
  },
])

const applyPayload = (payload = {}, updatedAt = Date.now()) => {
  orders.value = payload.items || []
  total.value = Number(payload.total || orders.value.length)
  pagination.page = Number(payload.page || pagination.page)
  pagination.pageSize = Number(payload.page_size || pagination.pageSize)
  Object.assign(summary, { ...REALTIME_SUMMARY_DEFAULTS, ...(payload.summary || {}) })
  tableReady.value = true
  cacheLabel.value = formatCacheLabel(updatedAt)
}

const removeOrderFromRealtime = (orderId) => {
  const oid = Number(orderId)
  const prev = orders.value.length
  orders.value = orders.value.filter((o) => Number(o.id) !== oid)
  const removed = prev - orders.value.length
  if (removed) {
    total.value = Math.max(0, Number(total.value || 0) - removed)
    summary.total_count = Math.max(0, Number(summary.total_count || 0) - removed)
  }
}

/** 演示创建成功：首屏直接插入一行，完整汇总由后台拉取对齐 */
const prependDemoOrderRow = (d) => {
  if (!d?.id || pagination.page !== 1) return
  const row = {
    id: d.id,
    order_no: d.order_no || '',
    status: d.status ?? 0,
    user_nickname: d.user_nickname || '',
    user_phone: d.user_phone || '',
    source_type: d.source_type || 'manual_demo',
    source_type_text: d.source_type_text || '',
    start_time: d.start_time || '',
    station_name: d.station_name || '',
    charger_name: d.charger_name || '',
    charge_amount: d.charge_amount ?? 0,
    total_amount: d.total_amount ?? 0,
  }
  orders.value = [row, ...orders.value.filter((o) => Number(o.id) !== Number(d.id))]
  total.value = Number(total.value || 0) + 1
  summary.total_count = Number(summary.total_count || 0) + 1
  tableReady.value = true
}

const runRealtimeListFetch = async ({ background }) => {
  const epoch = getOperatorOrderDataEpoch()
  const cached = getRequestCache(listCacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    if (epoch !== getOperatorOrderDataEpoch()) return
    applyPayload(cached.value, cached.updatedAt)
  }

  loading.value = !cached || !background
  try {
    const { data } = await fetchOperatorRealtimeOrders(queryParams.value)
    if (epoch !== getOperatorOrderDataEpoch()) return
    if (data?.code !== 200) {
      throw new Error(data?.message || '实时订单加载失败')
    }
    const payload = data?.data || {}
    applyPayload(payload, Date.now())
    if (epoch !== getOperatorOrderDataEpoch()) return
    setRequestCache(listCacheKey.value, payload)
  } catch (error) {
    if (epoch !== getOperatorOrderDataEpoch()) return
    if (!orders.value.length) {
      applyPayload(
        {
          items: [],
          total: 0,
          page: 1,
          page_size: pagination.pageSize,
          summary: { ...REALTIME_SUMMARY_DEFAULTS },
        },
        Date.now(),
      )
      ElMessage.error(error?.message || '实时订单加载失败')
    }
  } finally {
    loading.value = false
  }
}

const loadOrders = ({ background = false } = {}) => {
  realtimeOrdersFetchTail = realtimeOrdersFetchTail
    .then(() => runRealtimeListFetch({ background }))
    .catch(() => {})
  return realtimeOrdersFetchTail
}

/** 接口回填表单时写入电站，避免触发 @change 再拉一遍电桩 */
let skipStartStationChangeHandler = false

const applyStartOptions = (payload = {}, updatedAt = Date.now()) => {
  skipStartStationChangeHandler = true
  startUsers.value = payload.users?.length ? payload.users : []
  startStations.value = payload.stations?.length ? payload.stations : []
  startForm.user_id = payload.default_user_id || startUsers.value[0]?.id || null
  startForm.station_id =
    payload.default_station_id ||
    startStations.value.find((item) => Number(item.status) === 0)?.id ||
    startStations.value[0]?.id ||
    null
  startChargers.value = (payload.chargers || []).filter((item) => Number(item.status) === 0)
  startForm.charger_id = startChargers.value[0]?.id || null
  if (!cacheLabel.value) {
    cacheLabel.value = formatCacheLabel(updatedAt)
  }
  nextTick(() => {
    skipStartStationChangeHandler = false
  })
}

/** 同一电站并发拉桩合并为一次请求；若用户已切换电站则丢弃过期结果 */
const chargersInFlight = new Map()

const loadChargersByStation = async (stationId) => {
  if (!stationId) {
    startChargers.value = []
    startForm.charger_id = null
    return
  }
  const sid = Number(stationId)
  const existing = chargersInFlight.get(sid)
  if (existing) {
    await existing
    return
  }
  const task = (async () => {
    try {
      const { data } = await fetchStationChargers(sid)
      if (data?.code !== 200) {
        throw new Error(data?.message || '电桩加载失败')
      }
      if (Number(startForm.station_id) !== sid) return
      startChargers.value = (Array.isArray(data?.data) ? data.data : []).filter((item) => Number(item.status) === 0)
      startForm.charger_id = startChargers.value[0]?.id || null
    } catch (error) {
      if (Number(startForm.station_id) === sid) {
        startChargers.value = []
        startForm.charger_id = null
        ElMessage.error(error?.message || '电桩加载失败')
      }
    } finally {
      chargersInFlight.delete(sid)
    }
  })()
  chargersInFlight.set(sid, task)
  await task
}

const loadStartOptions = async ({ background = false, force = false } = {}) => {
  const cached = getRequestCache(startCacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyStartOptions(cached.value, cached.updatedAt)
    if (!startForm.charger_id && startForm.station_id) {
      await loadChargersByStation(startForm.station_id)
    }
    if (cached.isFresh && background && !force) {
      startOptionsLoading.value = false
      return
    }
  }

  startOptionsLoading.value = !cached || !background
  try {
    const params = {}
    if (startForm.station_id) params.station_id = startForm.station_id
    const { data } = await fetchOperatorOrderStartOptions(params)
    if (data?.code !== 200) {
      throw new Error(data?.message || '订单创建选项加载失败')
    }
    const payload = data?.data || {}
    applyStartOptions(payload, Date.now())
    setRequestCache(startCacheKey.value, payload)
    if (!payload.chargers?.length && startForm.station_id) {
      await loadChargersByStation(startForm.station_id)
    }
  } catch (error) {
    if (!cached) {
      applyStartOptions({ users: [], stations: [], chargers: [] })
      ElMessage.error(error?.message || '订单创建选项加载失败')
    }
  } finally {
    startOptionsLoading.value = false
  }
}

const handleStartStationChange = async (stationId) => {
  if (skipStartStationChangeHandler) return
  if (stationId == null || stationId === '') {
    startChargers.value = []
    startForm.charger_id = null
    return
  }
  startForm.charger_id = null
  await loadChargersByStation(stationId)
}

const openStartDialog = (mode) => {
  clearOperatorOrderStartOptionsCaches()
  startMode.value = mode
  startForm.source_type = mode === 'manual_demo' ? 'manual_demo' : 'qr_code'
  startForm.user_id = null
  startForm.station_id = null
  startForm.charger_id = null
  startDialogVisible.value = true
  loadStartOptions({ background: true, force: true })
}

const submitStartOrder = async () => {
  const user = startUsers.value.find((item) => String(item.id) === String(startForm.user_id))
  const station = startStations.value.find((item) => String(item.id) === String(startForm.station_id))
  const charger = startChargers.value.find((item) => String(item.id) === String(startForm.charger_id))

  if (!station || !charger) {
    ElMessage.warning('请选择已审核电站和空闲电桩')
    return
  }

  pauseRealtimePoll()
  startLoading.value = true
  try {
    const { data } = await startDemoCharging({
      user_id: startForm.user_id,
      station_id: startForm.station_id,
      charger_id: startForm.charger_id,
      source_type: startForm.source_type,
    })
    if (data?.code !== 200) {
      throw new Error(data?.message || '演示订单创建失败')
    }
    prependDemoOrderRow(data?.data)
    clearOperatorOrderListCaches()
    clearOperatorOrderStartOptionsCaches()
    const sid = data?.data?.station_id
    if (sid != null) clearStationChargersCachesForStation(sid)
    bumpOperatorOrderDataEpoch()
    ElMessage.success(data?.message || '演示订单创建成功')
  } catch (error) {
    ElMessage.error(error?.message || '演示订单创建失败')
  } finally {
    startLoading.value = false
    startDialogVisible.value = false
    resumeRealtimePoll()
    void loadOrders({ background: true })
  }
}

const handleFinish = async (row) => {
  try {
    await ElMessageBox.confirm(`确认结束订单 ${row.order_no} 吗？`, '结束订单', { type: 'warning' })
  } catch {
    return
  }

  pauseRealtimePoll()
  try {
    busyOrderId.value = row.id
    const { data } = await finishOperatorOrder(row.id)
    if (data?.code !== 200) {
      throw new Error(data?.message || '订单结束失败')
    }
    removeOrderFromRealtime(row.id)
    clearOperatorOrderListCaches()
    clearOperatorOrderStartOptionsCaches()
    if (row.station_id != null) clearStationChargersCachesForStation(row.station_id)
    bumpOperatorOrderDataEpoch()
    const w = data?.data?.wallet_transaction_id
    const bal = data?.data?.wallet_balance_after
    ElMessage.success(
      w
        ? `${data?.message || '订单已结束'}（钱包流水 #${w}，余额 ¥${Number(bal || 0).toFixed(2)}）`
        : data?.message || '订单已结束并完成扣费',
    )
  } catch (error) {
    ElMessage.error(error?.message || '订单结束失败')
  } finally {
    busyOrderId.value = null
    resumeRealtimePoll()
    void loadOrders({ background: true })
  }
}

const handleMarkAbnormal = async (row) => {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt('请输入异常原因', '标记异常', {
      inputPlaceholder: '例如：设备连接中断',
      inputValidator: (value) => (value && value.trim() ? true : '异常原因不能为空'),
    })
    reason = result.value.trim()
  } catch {
    return
  }

  pauseRealtimePoll()
  try {
    busyOrderId.value = row.id
    const { data } = await markOperatorOrderAbnormal(row.id, reason)
    if (data?.code !== 200) {
      throw new Error(data?.message || '异常订单处理失败')
    }
    removeOrderFromRealtime(row.id)
    clearOperatorOrderListCaches()
    if (row.station_id != null) clearStationChargersCachesForStation(row.station_id)
    bumpOperatorOrderDataEpoch()
    ElMessage.success(data?.message || '订单已标记为异常')
  } catch (error) {
    ElMessage.error(error?.message || '异常订单处理失败')
  } finally {
    busyOrderId.value = null
    resumeRealtimePoll()
    void loadOrders({ background: true })
  }
}

watch(
  () => startMode.value,
  (mode) => {
    startForm.source_type = mode === 'manual_demo' ? 'manual_demo' : 'qr_code'
  },
)

onMounted(async () => {
  await loadOrders({ background: true })
  await loadStartOptions({ background: true })
  scheduleRealtimePoll()
  document.addEventListener('visibilitychange', onRealtimeVisibility)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onRealtimeVisibility)
  if (realtimePollTimer) {
    window.clearInterval(realtimePollTimer)
    realtimePollTimer = null
  }
})

onActivated(() => {
  if (shouldRefreshRequestCache(listCacheKey.value, CACHE_TTL)) {
    void loadOrders({ background: true })
  }
  scheduleRealtimePoll()
  if (shouldRefreshRequestCache(startCacheKey.value, CACHE_TTL)) {
    loadStartOptions({ background: true })
  }
})
</script>

<template>
  <div class="page-shell realtime-page">
    <PageSectionHeader
      eyebrow="订单中心"
      title="实时订单"
      description="查看当前充电中的订单，并支持演示发起、结束和异常处理。"
      chip="实时监控"
    >
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button type="primary" :icon="Plus" @click="openStartDialog('manual_demo')">演示创建订单</el-button>
        <el-button type="primary" plain :icon="Tickets" @click="openStartDialog('qr_code')">扫码充电</el-button>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadOrders()">刷新列表</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--realtime">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">订单列表</h3>
          <p class="panel-heading__desc">共 {{ total }} 条记录。</p>
        </div>
      </div>
      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="8" />

      <el-table v-else-if="orders.length" :data="orders" v-loading="loading" stripe>
        <el-table-column prop="order_no" label="订单编号" min-width="190" />
        <el-table-column label="用户" min-width="150">
          <template #default="{ row }">
            <div class="cell-stack">
              <strong>{{ row.user_nickname }}</strong>
              <span>{{ row.user_phone }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="source_type_text" label="订单来源" width="120" align="center" />
        <el-table-column prop="start_time" label="开始时间" width="170" />
        <el-table-column prop="station_name" label="电站" min-width="170" />
        <el-table-column prop="charger_name" label="电桩" min-width="160" />
        <el-table-column label="电量(kWh)" width="110" align="right">
          <template #default="{ row }">{{ Number(row.charge_amount || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="总费用" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/operator/orders/detail/${row.id}`)">查看详情</el-button>
            <el-button link type="success" :loading="busyOrderId === row.id" @click="handleFinish(row)">结束订单</el-button>
            <el-button link type="danger" :loading="busyOrderId === row.id" @click="handleMarkAbnormal(row)">标记异常</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无实时订单" description="当前没有处于充电中的订单。" />
    </section>

    <el-dialog v-model="startDialogVisible" width="620px" :title="sourceTypeLabel">
      <el-form label-width="96px" v-loading="startOptionsLoading">
        <el-form-item label="用户">
          <el-select v-model="startForm.user_id" style="width: 100%">
            <el-option v-for="item in startUsers" :key="item.id" :label="`${item.nickname} / ${item.phone}`" :value="item.id" />
            <template #empty>
              <div class="empty-select-tip">暂无可用演示用户，请先执行初始化脚本</div>
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="电站">
          <el-select v-model="startForm.station_id" style="width: 100%" @change="handleStartStationChange">
            <el-option v-for="item in manualStations" :key="item.id" :label="`${item.station_name} / ${item.status_text}`" :value="item.id" />
            <template #empty>
              <div class="empty-select-tip">暂无已审核通过的电站，请先完成电站审核</div>
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="电桩">
          <el-select v-model="startForm.charger_id" style="width: 100%">
            <el-option
              v-for="item in startChargers"
              :key="item.id"
              :label="`${item.sn_code} / ${item.charger_name} / ${item.station_name} / ${item.status_text}`"
              :value="item.id"
            />
            <template #empty>
              <div class="empty-select-tip">暂无可用空闲电桩，请先在电桩管理中新增或恢复电桩状态</div>
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="订单来源">
          <el-tag type="primary">{{ startMode === 'manual_demo' ? '演示发起' : '扫码充电' }}</el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="startLoading" @click="submitStartOrder">确认发起</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid--realtime {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.cell-stack {
  display: grid;
  gap: 4px;
}

.cell-stack span {
  color: var(--color-text-2);
}

.empty-select-tip {
  padding: 12px;
  color: var(--color-text-2);
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 1280px) {
  .stats-grid--realtime {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--realtime {
    grid-template-columns: 1fr;
  }
}
</style>
