<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { Connection, RefreshRight, UserFilled, Van } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import ErrorBlock from '../../components/console/ErrorBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { fetchCustomerOverview } from '../../api/operator'
import { mockCustomerOverview } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const errorMessage = ref('')
const cacheLabel = ref('')
const members = ref([])
const summary = reactive({ fleet_count: 0, whitelist_count: 0, member_count: 0 })
const filters = reactive({ keyword: '', whitelistOnly: false })

const cacheKey = buildRequestCacheKey('/operator/customers/overview', { scope: 'customer-overview' })

const filteredMembers = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return members.value.filter((item) => {
    const matchKeyword =
      !keyword ||
      [item.name, item.phone, item.fleet_name, item.status]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(keyword))
    const matchWhitelist = !filters.whitelistOnly || Boolean(item.is_whitelist)
    return matchKeyword && matchWhitelist
  })
})

const stats = computed(() => [
  { label: '车队数量', value: summary.fleet_count, suffix: ' 个', trend: '已建车队组织', trendLabel: '支持运营分层管理', tone: 'primary', icon: Van },
  { label: '白名单车队', value: summary.whitelist_count, suffix: ' 个', trend: '专属接入策略', trendLabel: '可配置定向权益', tone: 'success', icon: Connection },
  { label: '成员数量', value: summary.member_count, suffix: ' 人', trend: '已纳入客户池', trendLabel: '覆盖可运营用户', tone: 'warning', icon: UserFilled },
  { label: '重点成员', value: members.value.length, suffix: ' 人', trend: '当前主力客户', trendLabel: '支持标签与活动联动', tone: 'info', icon: RefreshRight },
])

const applyPayload = (payload = {}, fromCache = false, updatedAt = Date.now()) => {
  members.value = payload.members || mockCustomerOverview.members
  Object.assign(summary, payload.summary || mockCustomerOverview.summary)
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '最近可用数据' : '已更新'} ${formatCacheUpdatedAt(updatedAt)}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) applyPayload(cached.value, true, cached.updatedAt)

  loading.value = !cached || !background
  errorMessage.value = ''
  try {
    const res = await fetchCustomerOverview()
    const payload = {
      members: res?.data?.data?.members || mockCustomerOverview.members,
      summary: res?.data?.data?.summary || mockCustomerOverview.summary,
    }
    applyPayload(payload, false, Date.now())
    setRequestCache(cacheKey, payload)
  } catch (error) {
    if (!members.value.length) {
      applyPayload(mockCustomerOverview, false, Date.now())
      cacheLabel.value = '当前内容可用'
    }
    errorMessage.value = '当前列表已保持最近更新内容。'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="客户管理" title="车队与白名单" description="统一查看车队成员、白名单策略与客户状态。" chip="客户总览">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--customers">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">支持按车队、成员和白名单状态快速筛选。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索成员 / 手机号 / 所属车队" style="width: 320px" />
        <el-switch v-model="filters.whitelistOnly" active-text="仅白名单" inactive-text="全部成员" />
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">成员列表</h3>
          <p class="panel-heading__desc">共 {{ filteredMembers.length }} 条记录。</p>
        </div>
      </div>

      <ErrorBlock
        v-if="errorMessage"
        title="成员列表状态提示"
        :description="errorMessage"
        @retry="loadData()"
      />

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="5" />

      <el-table v-else-if="filteredMembers.length" :data="filteredMembers" v-loading="loading" stripe>
        <el-table-column prop="name" label="成员" min-width="170" />
        <el-table-column prop="phone" label="联系方式" width="160" />
        <el-table-column prop="fleet_name" label="所属车队" min-width="180" />
        <el-table-column label="白名单" width="110" align="center">
          <template #default="{ row }"><el-tag :type="row.is_whitelist ? 'success' : 'info'">{{ row.is_whitelist ? '是' : '否' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" min-width="140" />
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无成员记录" description="当前筛选条件下没有匹配成员。" />
    </section>
  </div>
</template>

<style scoped>
.stats-grid--customers {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

@media (max-width: 1280px) {
  .stats-grid--customers {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--customers {
    grid-template-columns: 1fr;
  }
}
</style>
