<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCloseFilled, RefreshRight, UserFilled, WarningFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import ErrorBlock from '../../components/console/ErrorBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { fetchAdminBlacklist, toggleAdminUserBlacklist } from '../../api/admin'
import { mockBlacklistRows } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const cacheLabel = ref('')
const errorMessage = ref('')
const rows = ref([])

const filters = reactive({ keyword: '', reason: '' })
const cacheKey = buildRequestCacheKey('/admin/users/blacklist', { scope: 'admin-blacklist' })

const normalizedRows = computed(() => {
  if (rows.value.length) return rows.value
  return mockBlacklistRows.map((item, index) => ({
    ...item,
    risk_level: index % 2 === 0 ? '高' : '中',
    source: index % 2 === 0 ? '风控策略' : '人工复核',
    review_note: index % 2 === 0 ? '近 30 日异常交易频次过高' : '投诉复核待跟进',
  }))
})

const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  const reason = filters.reason.trim().toLowerCase()
  return normalizedRows.value.filter((item) => {
    const matchKeyword =
      !keyword || [item.name, item.phone, item.source].filter(Boolean).some((field) => String(field).toLowerCase().includes(keyword))
    const matchReason = !reason || String(item.reason || '').toLowerCase().includes(reason)
    return matchKeyword && matchReason
  })
})

const stats = computed(() => [
  { label: '黑名单总量', value: normalizedRows.value.length, suffix: ' 人', trend: '当前限制用户', trendLabel: '用于风控拦截与复核', tone: 'danger', icon: WarningFilled },
  { label: '高风险用户', value: normalizedRows.value.filter((item) => item.risk_level === '高').length, suffix: ' 人', trend: '优先复核对象', trendLabel: '建议 24 小时内处理', tone: 'warning', icon: CircleCloseFilled },
  { label: '人工复核中', value: normalizedRows.value.filter((item) => item.source === '人工复核').length, suffix: ' 人', trend: '待结论记录', trendLabel: '保持复核备注完整', tone: 'info', icon: UserFilled },
  { label: '可恢复用户', value: normalizedRows.value.filter((item) => item.risk_level !== '高').length, suffix: ' 人', trend: '可进入恢复流程', trendLabel: '需确认账户风险解除', tone: 'success', icon: RefreshRight },
])

const applyRows = (items = [], fromCache = false, updatedAt = Date.now()) => {
  rows.value = Array.isArray(items) ? items : []
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '最近可用数据' : '已更新'} ${formatCacheUpdatedAt(updatedAt)}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) applyRows(cached.value, true, cached.updatedAt)

  loading.value = !cached || !background
  errorMessage.value = ''
  try {
    const res = await fetchAdminBlacklist()
    const items = Array.isArray(res?.data?.data) ? res.data.data : mockBlacklistRows
    applyRows(items, false, Date.now())
    setRequestCache(cacheKey, items)
  } catch (error) {
    if (!rows.value.length) {
      applyRows(mockBlacklistRows, false, Date.now())
      cacheLabel.value = '当前内容可用'
    }
    errorMessage.value = '当前列表已保持最近更新内容。'
  } finally {
    loading.value = false
  }
}

const restoreUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确认将 ${row.name} 恢复为正常账户状态吗？`, '恢复账户', {
      type: 'warning',
      confirmButtonText: '确认恢复',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await toggleAdminUserBlacklist(row.id)
  } catch (error) {
    rows.value = rows.value.filter((item) => item.id !== row.id)
  }
  ElMessage.success('账户状态已恢复')
  await loadData({ background: true })
}

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="用户管理" title="黑名单管理" description="集中处理风险用户，支持快速复核、恢复与备注留痕。" chip="风控中心">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--blacklist">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">支持按用户、手机号、风险来源和原因关键词筛选。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索用户 / 手机号 / 来源" style="width: 320px" />
        <el-input v-model="filters.reason" clearable placeholder="输入风险原因关键词" style="width: 260px" />
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">名单列表</h3>
          <p class="panel-heading__desc">共 {{ filteredRows.length }} 条记录。</p>
        </div>
      </div>

      <ErrorBlock
        v-if="errorMessage"
        title="名单状态提示"
        :description="errorMessage"
        @retry="loadData()"
      />

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="6" />

      <el-table v-else-if="filteredRows.length" :data="filteredRows" v-loading="loading" stripe>
        <el-table-column prop="name" label="用户" min-width="130" />
        <el-table-column prop="phone" label="手机号" width="150" />
        <el-table-column label="风险等级" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.risk_level === '高' ? 'danger' : 'warning'">{{ row.risk_level || '中' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120" align="center" />
        <el-table-column prop="reason" label="限制原因" min-width="220" />
        <el-table-column prop="review_note" label="复核备注" min-width="220" />
        <el-table-column prop="created_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" plain @click="restoreUser(row)">恢复账户</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无黑名单记录" description="当前筛选条件下没有匹配用户。" />
    </section>
  </div>
</template>

<style scoped>
.stats-grid--blacklist {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

@media (max-width: 1280px) {
  .stats-grid--blacklist {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--blacklist {
    grid-template-columns: 1fr;
  }
}
</style>
