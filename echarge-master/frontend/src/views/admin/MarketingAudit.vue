<script setup>
import { computed, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Promotion, RefreshRight, WarningFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import { fetchMarketingAudits, processMarketingAudit } from '../../api/admin'
import { mockMarketingAudits } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const rows = ref([])
const cacheLabel = ref('')

const filters = reactive({
  keyword: '',
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
})

const cacheKey = buildRequestCacheKey('/admin/marketing/audits', { scope: 'marketing-audits' })

const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return rows.value.filter((item) => {
    const matchKeyword =
      !keyword ||
      [item.name, item.operator_name, item.audience, item.campaign_type]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(keyword))
    const matchStatus = !filters.status || item.audit_status === filters.status
    return matchKeyword && matchStatus
  })
})

const pagedRows = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return filteredRows.value.slice(start, start + pagination.pageSize)
})

const stats = computed(() => [
  { label: '活动总数', value: rows.value.length, suffix: ' 个', tone: 'primary', icon: Promotion, trend: '待审与已审活动', trendLabel: '覆盖营销投放流程' },
  { label: '待审核', value: rows.value.filter((item) => item.audit_status === 'pending').length, suffix: ' 个', tone: 'warning', icon: WarningFilled, trend: '待处理池', trendLabel: '优先处理临近上线活动' },
  { label: '已通过', value: rows.value.filter((item) => item.audit_status === 'approved').length, suffix: ' 个', tone: 'success', icon: CircleCheck, trend: '已获准投放', trendLabel: '后续可跟踪核销效果' },
  { label: '审批预算', value: rows.value.length ? rows.value.map((item) => Number(String(item.budget || '0').replace(/[^\d.]/g, ''))).reduce((sum, item) => sum + item, 0).toFixed(0) : '0', prefix: '¥', tone: 'info', icon: RefreshRight, trend: '已申报预算', trendLabel: '便于管理员评估资源投入' },
])

const applyRows = (items = [], fromCache = false) => {
  rows.value = Array.isArray(items) && items.length ? items : mockMarketingAudits
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '缓存结果' : '最近刷新'} ${formatCacheUpdatedAt(Date.now())}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyRows(cached.value, true)
    cacheLabel.value = `缓存结果 ${formatCacheUpdatedAt(cached.updatedAt)}`
  }

  loading.value = !cached || !background
  try {
    const res = await fetchMarketingAudits()
    const items = Array.isArray(res?.data?.data) ? res.data.data : mockMarketingAudits
    applyRows(items)
    setRequestCache(cacheKey, items)
    cacheLabel.value = `最近刷新 ${formatCacheUpdatedAt(Date.now())}`
  } catch (error) {
    if (!rows.value.length) {
      applyRows(mockMarketingAudits)
      cacheLabel.value = '当前内容可用'
    }
  } finally {
    loading.value = false
  }
}

const handleAudit = async (row, action) => {
  const result = await ElMessageBox.prompt('请填写审核意见，可为空。', action === 'approve' ? '通过活动' : '驳回活动', {
    inputPlaceholder: '审核意见',
  }).catch(() => ({ value: null }))
  if (result.value === null) return

  try {
    await processMarketingAudit(row.id, { action, remark: result.value || '' })
  } catch (error) {
    row.audit_status = action === 'approve' ? 'approved' : 'rejected'
    row.remark = result.value || (action === 'approve' ? '审核通过' : '已驳回')
  }
  ElMessage.success('营销审核结果已更新')
  await loadData({ background: true })
}

watch(
  () => [filters.keyword, filters.status],
  () => {
    pagination.page = 1
  },
)

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="系统配置" title="营销审核" description="审核营销活动规则、投放范围、预算与上线状态。" chip="活动审批">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--marketing">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">按活动名称、发起方、投放对象与审核状态进行筛选。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索活动名称 / 发起方 / 投放对象" style="width: 340px" />
        <el-select v-model="filters.status" clearable placeholder="审核状态" style="width: 160px">
          <el-option label="待审核" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">活动列表</h3>
          <p class="panel-heading__desc">共 {{ filteredRows.length }} 条记录。</p>
        </div>
      </div>

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="7" />

      <el-table v-else-if="pagedRows.length" :data="pagedRows" v-loading="loading" stripe>
        <el-table-column prop="name" label="活动名称" min-width="200" />
        <el-table-column prop="operator_name" label="发起方" min-width="150" />
        <el-table-column prop="campaign_type" label="类型" width="110" align="center" />
        <el-table-column prop="discount_value" label="优惠力度" width="120" align="center" />
        <el-table-column prop="audience" label="投放对象" min-width="140" />
        <el-table-column prop="budget" label="预算" width="120" align="center" />
        <el-table-column prop="submitted_at" label="提交时间" width="170" />
        <el-table-column label="审核状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.audit_status === 'approved' ? 'success' : row.audit_status === 'rejected' ? 'danger' : 'warning'">
              {{ row.audit_status === 'approved' ? '已通过' : row.audit_status === 'rejected' ? '已驳回' : '待审核' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="审核意见" min-width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleAudit(row, 'approve')">通过</el-button>
            <el-button size="small" plain type="danger" @click="handleAudit(row, 'reject')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无营销审核数据" description="当前筛选条件下没有匹配记录。" />

      <div class="pager">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="[10, 20, 40]"
          :total="filteredRows.length"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="(page) => { pagination.page = page }"
          @size-change="(size) => { pagination.page = 1; pagination.pageSize = size }"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.stats-grid--marketing {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1280px) {
  .stats-grid--marketing {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--marketing {
    grid-template-columns: 1fr;
  }
}
</style>
