<script setup>
import { computed, onActivated, onMounted, ref } from 'vue'
import { Document, Money, Reading, RefreshRight, Tickets, Wallet } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import http from '../../api/http'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const rows = ref([])
const cacheLabel = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const cacheKey = buildRequestCacheKey('/finance/settlements', { scope: 'settlement-page' })
const formatMoney = (value) => Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return rows.value.slice(start, start + pageSize.value)
})

const summary = computed(() => ({
  totalAmount: rows.value.reduce((sum, row) => sum + Number(row.total_amount || 0), 0),
  platformFee: rows.value.reduce((sum, row) => sum + Number(row.platform_fee || 0), 0),
  settleAmount: rows.value.reduce((sum, row) => sum + Number(row.settle_amount || 0), 0),
  paidAmount: rows.value.filter((row) => Number(row.status) === 1).reduce((sum, row) => sum + Number(row.settle_amount || 0), 0),
  pendingAmount: rows.value.filter((row) => Number(row.status) !== 1).reduce((sum, row) => sum + Number(row.settle_amount || 0), 0),
}))

const statCards = computed(() => [
  {
    label: '订单总额',
    value: formatMoney(summary.value.totalAmount),
    prefix: '¥',
    trend: '当前清分记录覆盖的订单金额',
    trendLabel: '按清分日期汇总',
    tone: 'primary',
    icon: Wallet,
  },
  {
    label: '平台服务费',
    value: formatMoney(summary.value.platformFee),
    prefix: '¥',
    trend: '平台抽成汇总',
    trendLabel: '用于毕业设计演示',
    tone: 'warning',
    icon: Tickets,
  },
  {
    label: '应结算金额',
    value: formatMoney(summary.value.settleAmount),
    prefix: '¥',
    trend: '运营商理论应收',
    trendLabel: '扣除平台服务费后',
    tone: 'success',
    icon: Money,
  },
  {
    label: '已结算金额',
    value: formatMoney(summary.value.paidAmount),
    prefix: '¥',
    trend: '状态为已清分的金额',
    trendLabel: '可用于收益对账',
    tone: 'info',
    icon: Document,
  },
  {
    label: '待处理金额',
    value: formatMoney(summary.value.pendingAmount),
    prefix: '¥',
    trend: '未完成打款或被挂起',
    trendLabel: '便于演示补资料场景',
    tone: 'danger',
    icon: Reading,
  },
])

const payoutStatusType = (status) => (Number(status) === 1 ? 'success' : Number(status) === 2 ? 'danger' : 'warning')
const qualificationType = (row) => (row.can_payout === true ? 'success' : row.can_payout === false ? 'warning' : 'info')

const fetchRows = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    rows.value = cached.value
    tableReady.value = true
    cacheLabel.value = `缓存结果 ${formatCacheUpdatedAt(cached.updatedAt)}`
  }

  loading.value = !cached || !background
  try {
    const resp = await http.get('/finance/settlements')
    const payload = resp?.data || {}
    if (payload.code !== 200) {
      throw new Error(payload.message || '收益对账数据加载失败')
    }
    const list = Array.isArray(payload.data) ? payload.data : []
    rows.value = list
    setRequestCache(cacheKey, list)
    cacheLabel.value = `最近刷新 ${formatCacheUpdatedAt(Date.now())}`
    tableReady.value = true
  } catch (error) {
    if (!rows.value.length) {
      rows.value = []
      cacheLabel.value = '暂无可用对账数据'
      tableReady.value = true
      ElMessage.error(error?.message || '收益对账数据加载失败')
    }
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await fetchRows()
  ElMessage.success('收益对账数据已刷新')
}

const handlePageChange = (page) => {
  currentPage.value = page
}

const handleSizeChange = (size) => {
  currentPage.value = 1
  pageSize.value = size
}

onMounted(fetchRows)
onActivated(() => fetchRows({ background: true }))
</script>

<template>
  <div class="page-shell settlement-page">
    <PageSectionHeader
      eyebrow="财务管理"
      title="运营商收益对账"
      description="展示当前运营商清分记录，用于核对订单金额、平台服务费和结算状态。"
      chip="收益对账"
    >
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" @click="refreshData">刷新对账数据</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--settlement">
      <MetricCard v-for="item in statCards" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">清分记录</h3>
          <p class="panel-heading__desc">按清分日期展示订单规模、平台服务费与结算状态。</p>
        </div>
      </div>

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="8" />

      <el-table v-else-if="pagedRows.length" :data="pagedRows" v-loading="loading" stripe>
        <el-table-column prop="settle_date" label="清分日期" width="120" />
        <el-table-column prop="operator_name" label="运营商" min-width="160" />
        <el-table-column prop="order_count" label="订单数" width="100" align="center" />
        <el-table-column label="订单总额" width="140" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="平台服务费" width="140" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.platform_fee) }}</template>
        </el-table-column>
        <el-table-column label="应结算金额" width="140" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.settle_amount) }}</template>
        </el-table-column>
        <el-table-column label="结算资格" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="qualificationType(row)">
              {{ row.can_payout === true ? '资格通过' : row.can_payout === false ? '待补资料' : '待判定' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="payoutStatusType(row.status)">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hold_reason" label="备注" min-width="180" />
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无对账数据" description="当前没有可展示的清分记录。" />

      <div class="pager">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :page-sizes="[10, 20, 40]"
          :total="rows.length"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.stats-grid--settlement {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1280px) {
  .stats-grid--settlement {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--settlement {
    grid-template-columns: 1fr;
  }
}
</style>
