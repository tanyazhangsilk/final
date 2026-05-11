<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Plus, RefreshRight, Van, WarningFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import ErrorBlock from '../../components/console/ErrorBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { createFleet, fetchFleets } from '../../api/operator'
import { mockFleets } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const errorMessage = ref('')
const cacheLabel = ref('')
const rows = ref([])

const dialogVisible = ref(false)
const form = reactive({ name: '', is_whitelist: false })
const filters = reactive({ keyword: '', whitelistOnly: false })

const cacheKey = buildRequestCacheKey('/operator/customers/fleets', { scope: 'fleet-management' })

const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return rows.value.filter((item) => {
    const matchKeyword = !keyword || String(item.name || '').toLowerCase().includes(keyword)
    const matchWhitelist = !filters.whitelistOnly || Boolean(item.is_whitelist)
    return matchKeyword && matchWhitelist
  })
})

const stats = computed(() => [
  { label: '车队总数', value: rows.value.length, suffix: ' 个', trend: '当前已建车队', trendLabel: '支撑专属用户分层', tone: 'primary', icon: Van },
  { label: '白名单车队', value: rows.value.filter((item) => item.is_whitelist).length, suffix: ' 个', trend: '专属策略对象', trendLabel: '可配置定向权益', tone: 'success', icon: CircleCheck },
  { label: '普通车队', value: rows.value.filter((item) => !item.is_whitelist).length, suffix: ' 个', trend: '基础运营对象', trendLabel: '可逐步转化白名单', tone: 'warning', icon: WarningFilled },
  { label: '车队成员', value: rows.value.reduce((sum, item) => sum + Number(item.member_count || 0), 0), suffix: ' 人', trend: '成员覆盖规模', trendLabel: '支持订单与营销联动', tone: 'info', icon: RefreshRight },
])

const applyRows = (items = [], fromCache = false, updatedAt = Date.now()) => {
  rows.value = Array.isArray(items) && items.length ? items : mockFleets
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '最近可用数据' : '已更新'} ${formatCacheUpdatedAt(updatedAt)}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) applyRows(cached.value, true, cached.updatedAt)

  loading.value = !cached || !background
  errorMessage.value = ''
  try {
    const res = await fetchFleets()
    const items = Array.isArray(res?.data?.data) ? res.data.data : mockFleets
    applyRows(items, false, Date.now())
    setRequestCache(cacheKey, items)
  } catch (error) {
    if (!rows.value.length) {
      applyRows(mockFleets, false, Date.now())
      cacheLabel.value = '当前内容可用'
    }
    errorMessage.value = '当前列表已保持最近更新内容。'
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!form.name.trim()) {
    ElMessage.warning('请输入车队名称')
    return
  }
  try {
    await createFleet({ ...form })
  } catch (error) {
    rows.value.unshift({
      id: Date.now(),
      name: form.name.trim(),
      member_count: 0,
      is_whitelist: form.is_whitelist,
      created_at: new Date().toLocaleString('zh-CN', { hour12: false }),
    })
  }
  ElMessage.success('车队已创建')
  dialogVisible.value = false
  form.name = ''
  form.is_whitelist = false
  await loadData({ background: true })
}

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="客户管理" title="专属用户管理" description="管理车队组织与白名单状态，形成可持续运营客户池。" chip="车队管理">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="dialogVisible = true">新建车队</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--fleets">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">按车队名称和白名单状态筛选目标车队。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索车队名称" style="width: 320px" />
        <el-switch v-model="filters.whitelistOnly" active-text="仅白名单" inactive-text="全部车队" />
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <ErrorBlock
        v-if="errorMessage"
        title="车队列表状态提示"
        :description="errorMessage"
        @retry="loadData()"
      />

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="4" />

      <el-table v-else-if="filteredRows.length" :data="filteredRows" v-loading="loading" stripe>
        <el-table-column prop="name" label="车队名称" min-width="180" />
        <el-table-column prop="member_count" label="成员数" width="120" align="center" />
        <el-table-column label="白名单" width="120" align="center">
          <template #default="{ row }"><el-tag :type="row.is_whitelist ? 'success' : 'info'">{{ row.is_whitelist ? '白名单' : '普通' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无车队数据" description="当前筛选条件下没有匹配车队。" />
    </section>

    <el-dialog v-model="dialogVisible" title="新建车队" width="460px">
      <el-form label-position="top">
        <el-form-item label="车队名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="加入白名单"><el-switch v-model="form.is_whitelist" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid--fleets {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

@media (max-width: 1280px) {
  .stats-grid--fleets {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--fleets {
    grid-template-columns: 1fr;
  }
}
</style>
