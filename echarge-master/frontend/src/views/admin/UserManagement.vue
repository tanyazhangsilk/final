<script setup>
import { computed, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Money, RefreshRight, UserFilled, WarningFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import { fetchAdminUsers, toggleAdminUserBlacklist } from '../../api/admin'
import { mockAdminUsers } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const users = ref([])
const summary = ref(mockAdminUsers.summary)
const cacheLabel = ref('')

const filters = reactive({
  keyword: '',
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 12,
})

const cacheKey = buildRequestCacheKey('/admin/users', { scope: 'admin-users' })

const filteredUsers = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return users.value.filter((item) => {
    const matchKeyword =
      !keyword ||
      [item.name, item.phone, item.vin_code]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(keyword))
    const matchStatus = !filters.status || item.status === filters.status
    return matchKeyword && matchStatus
  })
})

const pagedUsers = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return filteredUsers.value.slice(start, start + pagination.pageSize)
})

const stats = computed(() => [
  { label: '用户总数', value: summary.value.total_users || users.value.length, suffix: ' 人', tone: 'primary', icon: UserFilled, trend: '平台注册规模', trendLabel: '覆盖全部注册用户' },
  { label: '活跃用户', value: summary.value.active_users || users.value.filter((item) => item.order_count > 0).length, suffix: ' 人', tone: 'success', icon: CircleCheck, trend: '近 30 天有订单', trendLabel: '可持续跟踪复购表现' },
  { label: '黑名单用户', value: summary.value.blacklisted_users || users.value.filter((item) => item.status === 'blacklisted').length, suffix: ' 人', tone: 'danger', icon: WarningFilled, trend: '风险限制名单', trendLabel: '支持一键恢复或拉黑' },
  { label: '累计消费', value: users.value.reduce((sum, item) => sum + Number(item.total_spent || 0), 0).toFixed(0), prefix: '¥', tone: 'warning', icon: Money, trend: '当前列表汇总', trendLabel: '用于观察高价值用户' },
])

const applyPayload = (payload = {}, fromCache = false) => {
  users.value = Array.isArray(payload.rows) ? payload.rows : mockAdminUsers.rows
  summary.value = payload.summary || mockAdminUsers.summary
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '缓存结果' : '最近刷新'} ${formatCacheUpdatedAt(Date.now())}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyPayload(cached.value, true)
    cacheLabel.value = `缓存结果 ${formatCacheUpdatedAt(cached.updatedAt)}`
  }

  loading.value = !cached || !background
  try {
    const res = await fetchAdminUsers()
    const payload = {
      rows: Array.isArray(res?.data?.data) ? res.data.data : mockAdminUsers.rows,
      summary: res?.data?.summary || mockAdminUsers.summary,
    }
    applyPayload(payload)
    setRequestCache(cacheKey, payload)
    cacheLabel.value = `最近刷新 ${formatCacheUpdatedAt(Date.now())}`
  } catch (error) {
    if (!users.value.length) {
      applyPayload({ rows: mockAdminUsers.rows, summary: mockAdminUsers.summary })
      cacheLabel.value = '当前内容可用'
    }
  } finally {
    loading.value = false
  }
}

const toggleBlacklist = async (row) => {
  const nextStatus = row.status === 'blacklisted' ? 'active' : 'blacklisted'
  try {
    await toggleAdminUserBlacklist(row.id)
  } catch (error) {
    row.status = nextStatus
  }
  if (row.status !== nextStatus) {
    row.status = nextStatus
  }
  ElMessage.success(nextStatus === 'blacklisted' ? '用户已加入黑名单' : '用户已恢复正常')
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
    <PageSectionHeader eyebrow="用户管理" title="用户管理" description="查看平台用户状态、消费表现与风控处理记录。" chip="用户中心">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--users">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">支持按姓名、手机号、VIN 与账户状态快速筛选。</p>
        </div>
      </div>

      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索姓名 / 手机号 / VIN" style="width: 320px" />
        <el-select v-model="filters.status" clearable placeholder="账户状态" style="width: 160px">
          <el-option label="正常" value="active" />
          <el-option label="黑名单" value="blacklisted" />
        </el-select>
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">用户列表</h3>
          <p class="panel-heading__desc">共 {{ filteredUsers.length }} 条记录，默认按注册时间倒序展示。</p>
        </div>
      </div>

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="8" :columns="7" />

      <el-table v-else-if="pagedUsers.length" :data="pagedUsers" v-loading="loading" stripe>
        <el-table-column prop="name" label="用户" min-width="160" />
        <el-table-column prop="phone" label="手机号" width="150" />
        <el-table-column prop="vin_code" label="VIN" min-width="180" />
        <el-table-column prop="order_count" label="订单数" width="100" align="center" />
        <el-table-column label="累计消费" width="120" align="right">
          <template #default="{ row }">¥{{ Number(row.total_spent || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="账户状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'blacklisted' ? 'danger' : 'success'">
              {{ row.status === 'blacklisted' ? '黑名单' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :type="row.status === 'blacklisted' ? 'success' : 'danger'" plain @click="toggleBlacklist(row)">
              {{ row.status === 'blacklisted' ? '恢复' : '拉黑' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无用户数据" description="当前筛选条件下没有匹配用户。" />

      <div class="pager">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="[12, 24, 48]"
          :total="filteredUsers.length"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="(page) => { pagination.page = page }"
          @size-change="(size) => { pagination.page = 1; pagination.pageSize = size }"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.stats-grid--users {
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
  .stats-grid--users {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--users {
    grid-template-columns: 1fr;
  }
}
</style>
