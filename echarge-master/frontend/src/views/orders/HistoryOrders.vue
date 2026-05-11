<script setup>
import { computed, onActivated, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataAnalysis, Money, RefreshRight, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { fetchAdminOrders, fetchAdminStationOptions } from '../../api/admin'
import { mockOrders } from '../../mock/orders'
import { buildAdminHistoryDemoPayload } from '../../utils/adminDemoFallback'
import { fetchOperatorHistoryOrders, fetchOperatorStationOptions } from '../../api/operator'
import { ROLES } from '../../config/permissions'
import {
  buildRequestCacheKey,
  formatCacheLabel,
  getOperatorOrderDataEpoch,
  getRequestCache,
  setRequestCache,
  shouldRefreshRequestCache,
} from '../../utils/requestCache'

const route = useRoute()
const router = useRouter()
const CACHE_TTL = 45 * 1000

const loading = ref(false)
const tableReady = ref(false)
const stationLoading = ref(false)
const orders = ref([])
const total = ref(0)
const stationOptions = ref([])
const stationOptionsLoaded = ref(false)
const cacheLabel = ref('')

const pagination = reactive({ page: 1, pageSize: 10 })
const filters = reactive({ keyword: '', status: '', stationId: '', dateRange: [] })
const summary = reactive({ total_count: 0, total_charge_amount: 0, total_amount: 0, total_service_fee: 0 })

let searchTimer = null

const isAdmin = computed(() => route.meta?.role === ROLES.ADMIN)
const pageTitle = computed(() => (isAdmin.value ? '订单管理' : '历史订单'))
const pageChip = computed(() => (isAdmin.value ? '平台订单' : '订单中心'))
const queryParams = computed(() => ({
  page: pagination.page,
  page_size: pagination.pageSize,
  keyword: filters.keyword.trim() || undefined,
  station_id: filters.stationId || undefined,
  start_date: filters.dateRange?.[0] || undefined,
  end_date: filters.dateRange?.[1] || undefined,
  status: isAdmin.value ? (filters.status === '' ? undefined : Number(filters.status)) : 1,
}))
const listCacheKey = computed(() => buildRequestCacheKey(isAdmin.value ? '/admin/orders' : '/operator/orders/history', queryParams.value))

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '充电中', value: 0 },
  { label: '已完成', value: 1 },
  { label: '异常结束', value: 2 },
]

const formatMoney = (value) => `￥${Number(value || 0).toFixed(2)}`

const HISTORY_SUMMARY_DEFAULTS = {
  total_count: 0,
  total_charge_amount: 0,
  total_amount: 0,
  total_service_fee: 0,
  total_ele_fee: 0,
  charging_count: 0,
  completed_count: 0,
  abnormal_count: 0,
  station_count: 0,
  reason_count: 0,
}

const stats = computed(() => [
  {
    label: '历史订单',
    value: summary.total_count,
    suffix: ' 单',
    trend: '当前筛选结果',
    trendLabel: '含归档完成订单',
    tone: 'primary',
    icon: Tickets,
  },
  {
    label: '累计电量',
    value: Number(summary.total_charge_amount || 0).toFixed(2),
    suffix: ' kWh',
    trend: '已结束订单累计充电量',
    trendLabel: '用于统计运营规模',
    tone: 'success',
    icon: DataAnalysis,
  },
  {
    label: '累计营收',
    value: Number(summary.total_amount || 0).toFixed(2),
    prefix: '￥',
    trend: '订单总费用汇总',
    trendLabel: '包含电费与服务费',
    tone: 'warning',
    icon: Money,
  },
  {
    label: '累计服务费',
    value: Number(summary.total_service_fee || 0).toFixed(2),
    prefix: '￥',
    trend: '服务费累计汇总',
    trendLabel: '便于财务核对',
    tone: 'info',
    icon: RefreshRight,
  },
])

const applyPayload = (payload = {}, updatedAt = Date.now()) => {
  orders.value = Array.isArray(payload.items) ? payload.items : []
  total.value = Number(payload.total || orders.value.length)
  pagination.page = Number(payload.page || pagination.page)
  pagination.pageSize = Number(payload.page_size || pagination.pageSize)
  Object.assign(summary, { ...HISTORY_SUMMARY_DEFAULTS, ...(payload.summary || {}) })
  tableReady.value = true
  cacheLabel.value = formatCacheLabel(updatedAt)
}

const loadOrders = async ({ background = false } = {}) => {
  const epoch = getOperatorOrderDataEpoch()
  const cached = getRequestCache(listCacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    if (epoch !== getOperatorOrderDataEpoch()) return
    applyPayload(cached.value, cached.updatedAt)
  }

  loading.value = !cached || !background
  try {
    const response = isAdmin.value ? await fetchAdminOrders(queryParams.value) : await fetchOperatorHistoryOrders(queryParams.value)
    if (epoch !== getOperatorOrderDataEpoch()) return
    if (response?.data?.code !== 200) {
      throw new Error(response?.data?.message || '订单列表加载失败')
    }
    let payload = response.data?.data || {}
    if (isAdmin.value && (!Array.isArray(payload.items) || !payload.items.length)) {
      payload = buildAdminHistoryDemoPayload(mockOrders, pagination.pageSize)
      ElMessage.info('暂无平台历史订单，已展示演示数据（演示行不可跳转详情）')
    }
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
          summary: { ...HISTORY_SUMMARY_DEFAULTS },
        },
        Date.now(),
      )
      ElMessage.error(error?.message || '订单列表加载失败')
    }
  } finally {
    loading.value = false
  }
}

const loadStationOptions = async () => {
  if (stationOptionsLoaded.value || stationLoading.value) return
  stationLoading.value = true
  try {
    const { data } = isAdmin.value ? await fetchAdminStationOptions() : await fetchOperatorStationOptions()
    if (data?.code !== 200) {
      throw new Error(data?.message || '电站选项加载失败')
    }
    stationOptions.value = (data?.data || []).map((item) => ({ label: item.station_name, value: item.id }))
    stationOptionsLoaded.value = true
  } catch (error) {
    stationOptions.value = []
    stationOptionsLoaded.value = true
    ElMessage.error(error?.message || '电站选项加载失败')
  } finally {
    stationLoading.value = false
  }
}

const resetFilters = () => {
  filters.keyword = ''
  filters.status = ''
  filters.stationId = ''
  filters.dateRange = []
}

watch(
  () => [filters.keyword, filters.status, filters.stationId, JSON.stringify(filters.dateRange)],
  () => {
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      pagination.page = 1
      loadOrders()
    }, 260)
  },
)

onMounted(() => loadOrders({ background: true }))
onActivated(() => {
  if (!isAdmin.value) {
    if (shouldRefreshRequestCache(listCacheKey.value, CACHE_TTL)) {
      void loadOrders({ background: true })
    }
    return
  }
  if (shouldRefreshRequestCache(listCacheKey.value, CACHE_TTL)) {
    loadOrders({ background: true })
  }
})
onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

const goOrderDetail = (row) => {
  if (row.is_demo) {
    ElMessage.info('当前为演示数据，正式订单入库后可查看详情')
    return
  }
  router.push(isAdmin.value ? `/admin/orders/detail/${row.id}` : `/operator/orders/detail/${row.id}`)
}
</script>

<template>
  <div class="page-shell history-page">
    <PageSectionHeader eyebrow="订单中心" :title="pageTitle" description="查询已完成订单的时间、来源、费用和结算信息。" :chip="pageChip">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadOrders()">刷新列表</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--history">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">优先加载订单列表，电站选项在交互时按需获取。</p>
        </div>
        <div class="toolbar-actions">
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>

      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="订单号 / 用户 / VIN / 来源" style="width: 320px" />
        <el-select v-if="isAdmin" v-model="filters.status" clearable placeholder="选择状态" style="width: 160px">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="filters.stationId"
          clearable
          filterable
          :loading="stationLoading"
          placeholder="选择电站"
          style="width: 220px"
          @visible-change="(visible) => visible && loadStationOptions()"
          @focus="loadStationOptions"
        >
          <el-option v-for="item in stationOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        />
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">订单列表</h3>
          <p class="panel-heading__desc">共 {{ total }} 条记录。</p>
        </div>
      </div>
      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="9" />

      <el-table v-else-if="orders.length" :data="orders" v-loading="loading" stripe>
        <el-table-column prop="order_no" label="订单编号" min-width="190" />
        <el-table-column label="用户" min-width="160">
          <template #default="{ row }">
            <div class="time-range">
              <strong>{{ row.user_nickname }}</strong>
              <span>{{ row.user_phone }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="source_type_text" label="订单来源" width="120" align="center" />
        <el-table-column label="起止时间" min-width="260">
          <template #default="{ row }">
            <div class="time-range">
              <span>{{ row.start_time }}</span>
              <span>{{ row.end_time || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="电量(kWh)" width="110" align="right">
          <template #default="{ row }">{{ Number(row.charge_amount || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="电费" width="100" align="right">
          <template #default="{ row }">{{ formatMoney(row.electricity_fee) }}</template>
        </el-table-column>
        <el-table-column label="服务费" width="100" align="right">
          <template #default="{ row }">{{ formatMoney(row.service_fee) }}</template>
        </el-table-column>
        <el-table-column label="总费用" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column prop="station_name" label="电站" min-width="160" />
        <el-table-column prop="charger_name" label="电桩" min-width="160" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goOrderDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无历史订单" description="当前筛选条件下没有历史订单记录。" />

      <div class="pager">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="(page) => { pagination.page = page; loadOrders() }"
          @size-change="(size) => { pagination.page = 1; pagination.pageSize = size; loadOrders() }"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.stats-grid--history { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.toolbar-actions, .filter-row { display: flex; flex-wrap: wrap; gap: 12px; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
.time-range { display: grid; gap: 4px; }
.time-range span:last-child { color: var(--color-text-2); }
@media (max-width: 1280px) { .stats-grid--history { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 768px) { .stats-grid--history { grid-template-columns: 1fr; } }
</style>
