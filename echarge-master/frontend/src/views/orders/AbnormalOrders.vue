<script setup>
import { computed, onActivated, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, Money, RefreshRight, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { fetchAdminAbnormalOrders } from '../../api/admin'
import { mockOrders } from '../../mock/orders'
import { buildAdminAbnormalDemoPayload } from '../../utils/adminDemoFallback'
import { fetchOperatorAbnormalOrders } from '../../api/operator'
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
const orders = ref([])
const total = ref(0)
const cacheLabel = ref('')

const pagination = reactive({ page: 1, pageSize: 10 })
const filters = reactive({ keyword: '', reason: '', dateRange: [] })
const summary = reactive({ total_count: 0, total_amount: 0, reason_count: 0, abnormal_count: 0 })

let searchTimer = null

const isAdmin = computed(() => route.meta?.role === ROLES.ADMIN)
const queryParams = computed(() => ({
  page: pagination.page,
  page_size: pagination.pageSize,
  keyword: filters.keyword.trim() || undefined,
  abnormal_reason: filters.reason.trim() || undefined,
  start_date: filters.dateRange?.[0] || undefined,
  end_date: filters.dateRange?.[1] || undefined,
}))
const listCacheKey = computed(() => buildRequestCacheKey(isAdmin.value ? '/admin/orders/abnormal' : '/operator/orders/abnormal', queryParams.value))
const formatMoney = (value) => `￥${Number(value || 0).toFixed(2)}`

const ABNORMAL_SUMMARY_DEFAULTS = {
  total_count: 0,
  total_charge_amount: 0,
  total_amount: 0,
  total_ele_fee: 0,
  total_service_fee: 0,
  charging_count: 0,
  completed_count: 0,
  abnormal_count: 0,
  station_count: 0,
  reason_count: 0,
}

const stats = computed(() => [
  {
    label: '异常订单',
    value: summary.total_count,
    suffix: ' 单',
    trend: '当前筛选结果',
    trendLabel: '支持按原因追踪',
    tone: 'danger',
    icon: WarningFilled,
  },
  {
    label: '异常金额',
    value: Number(summary.total_amount || 0).toFixed(2),
    prefix: '￥',
    trend: '异常订单涉及金额',
    trendLabel: '便于财务与客服跟进',
    tone: 'warning',
    icon: Money,
  },
  {
    label: '异常类型',
    value: summary.reason_count,
    suffix: ' 类',
    trend: '去重后的原因统计',
    trendLabel: '用于识别高频问题',
    tone: 'info',
    icon: Bell,
  },
  {
    label: '归档异常',
    value: summary.abnormal_count,
    suffix: ' 单',
    trend: '已归档异常订单',
    trendLabel: '用于安排复核优先级',
    tone: 'primary',
    icon: RefreshRight,
  },
])

const applyPayload = (payload = {}, updatedAt = Date.now()) => {
  orders.value = Array.isArray(payload.items) ? payload.items : []
  total.value = Number(payload.total || orders.value.length)
  pagination.page = Number(payload.page || pagination.page)
  pagination.pageSize = Number(payload.page_size || pagination.pageSize)
  Object.assign(summary, { ...ABNORMAL_SUMMARY_DEFAULTS, ...(payload.summary || {}) })
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
    const response = isAdmin.value ? await fetchAdminAbnormalOrders(queryParams.value) : await fetchOperatorAbnormalOrders(queryParams.value)
    if (epoch !== getOperatorOrderDataEpoch()) return
    if (response?.data?.code !== 200) {
      throw new Error(response?.data?.message || '异常订单加载失败')
    }
    let payload = response.data?.data || {}
    if (isAdmin.value && (!Array.isArray(payload.items) || !payload.items.length)) {
      payload = buildAdminAbnormalDemoPayload(mockOrders, pagination.pageSize)
      ElMessage.info('暂无平台异常订单，已展示演示数据（演示行不可跳转详情）')
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
          summary: { ...ABNORMAL_SUMMARY_DEFAULTS },
        },
        Date.now(),
      )
      ElMessage.error(error?.message || '异常订单加载失败')
    }
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.keyword = ''
  filters.reason = ''
  filters.dateRange = []
}

watch(
  () => [filters.keyword, filters.reason, JSON.stringify(filters.dateRange)],
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
    ElMessage.info('当前为演示数据，正式异常订单入库后可查看详情')
    return
  }
  router.push(isAdmin.value ? `/admin/orders/detail/${row.id}` : `/operator/orders/detail/${row.id}`)
}
</script>

<template>
  <div class="page-shell abnormal-page">
    <PageSectionHeader eyebrow="订单中心" :title="isAdmin ? '异常订单管理' : '异常订单'" description="查询异常订单、异常原因与相关费用，便于及时跟进处理。" :chip="isAdmin ? '平台订单' : '订单中心'">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadOrders()">刷新列表</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--abnormal">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">支持按订单、用户、异常原因与时间范围查询。</p>
        </div>
        <div class="toolbar-actions">
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>

      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="订单号 / 用户 / VIN / 来源" style="width: 320px" />
        <el-input v-model="filters.reason" clearable placeholder="异常原因关键词" style="width: 240px" />
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
      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="8" />

      <el-table v-else-if="orders.length" :data="orders" v-loading="loading" stripe>
        <el-table-column prop="order_no" label="订单编号" min-width="190" />
        <el-table-column label="用户" min-width="160">
          <template #default="{ row }">
            <div class="user-cell">
              <strong>{{ row.user_nickname }}</strong>
              <span>{{ row.user_phone }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="source_type_text" label="订单来源" width="120" align="center" />
        <el-table-column prop="vin" label="VIN" min-width="170" />
        <el-table-column prop="start_time" label="开始时间" width="170" />
        <el-table-column prop="end_time" label="结束时间" width="170" />
        <el-table-column prop="station_name" label="电站" min-width="170" />
        <el-table-column prop="charger_name" label="电桩" min-width="160" />
        <el-table-column label="异常原因" min-width="260">
          <template #default="{ row }"><div class="reason-pill">{{ row.abnormal_reason || '未记录异常原因' }}</div></template>
        </el-table-column>
        <el-table-column label="总费用" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goOrderDetail(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无异常订单" description="当前筛选条件下没有异常订单记录。" />

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
.stats-grid--abnormal { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.toolbar-actions, .filter-row { display: flex; flex-wrap: wrap; gap: 12px; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
.user-cell { display: grid; gap: 4px; }
.user-cell span { color: var(--color-text-2); }
.reason-pill { padding: 10px 12px; border-radius: 14px; background: linear-gradient(135deg, rgba(245, 108, 108, 0.18), rgba(255, 182, 93, 0.22)); color: #b42318; font-weight: 600; line-height: 1.5; }
@media (max-width: 1280px) { .stats-grid--abnormal { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 768px) { .stats-grid--abnormal { grid-template-columns: 1fr; } }
</style>
