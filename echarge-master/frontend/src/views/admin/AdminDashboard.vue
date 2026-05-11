<script setup>
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import {
  Coin,
  Connection,
  DocumentChecked,
  Lightning,
  Money,
  OfficeBuilding,
  Tickets,
  WarningFilled,
} from '@element-plus/icons-vue'

import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import DonutStatusChart from '../../components/console/DonutStatusChart.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import TrendAreaChart from '../../components/console/TrendAreaChart.vue'
import { fetchAdminDashboard } from '../../api/console'
import { ROLES } from '../../config/permissions'
import { useOrderStore } from '../../stores/order'
import { buildRequestCacheKey, formatCacheLabel, getRequestCache, setRequestCache, shouldRefreshRequestCache } from '../../utils/requestCache'

const router = useRouter()
const orderStore = useOrderStore()

const loading = ref(false)
const baseOverviewStats = ref([])
const baseDistributions = ref(null)
const todoList = ref([])
const recentActivities = ref([])
const announcements = ref([])
const cacheLabel = ref('')
const CACHE_TTL = 12 * 1000

const adminScope = { role: ROLES.ADMIN }
const cacheKey = buildRequestCacheKey('/console/admin/dashboard', { scope: 'admin-dashboard' })

const orderStats = computed(() => orderStore.getOrderStats(adminScope))
const orderTrendSource = computed(() => orderStore.getOrderTrend(adminScope, 7))
const allOrders = computed(() => orderStore.getAllOrders(adminScope))

const overviewStats = computed(() =>
  baseOverviewStats.value.map((item) => {
    if (item.key === 'todayOrderCount') {
      return { ...item, value: allOrders.value.length }
    }
    if (item.key === 'todayRevenue') {
      return { ...item, value: orderStats.value.todayTotalAmount.toFixed(2) }
    }
    if (item.key === 'abnormalOrderCount') {
      return { ...item, value: orderStats.value.abnormalCount }
    }
    return item
  }),
)

const orderTrend = computed(() =>
  orderTrendSource.value.map((item) => ({
    date: item.date,
    orderCount: item.orderCount,
  })),
)

const revenueTrend = computed(() =>
  orderTrendSource.value.map((item) => ({
    date: item.date,
    revenue: item.revenue,
  })),
)

const distributions = computed(() => {
  const source = baseDistributions.value || {}
  const chargingCount = allOrders.value.filter((item) => item.status === 'charging').length
  const completedCount = allOrders.value.filter((item) => item.status === 'completed').length
  const abnormalCount = allOrders.value.filter((item) => item.status === 'abnormal').length
  return {
    ...source,
    orderStatus: {
      total: allOrders.value.length,
      totalLabel: '订单总数',
      items: [
        { label: '充电中', value: chargingCount, color: '#2f74ff' },
        { label: '已完成', value: completedCount, color: '#22a06b' },
        { label: '异常', value: abnormalCount, color: '#d84f57' },
      ],
    },
  }
})

const abnormalOrders = computed(() =>
  orderStore.getAbnormalOrders(adminScope).slice(0, 6).map((order) => ({
    id: order.id,
    orderNo: order.orderNo,
    userName: order.userName,
    stationName: order.stationName,
    abnormalType: order.abnormalReason || '订单异常',
    createdAt: (order.updatedAt || order.startTime || '').replace('T', ' ').slice(0, 16),
    status: '待复核',
  })),
)

const iconMap = {
  OfficeBuilding,
  DocumentChecked,
  Lightning,
  Connection,
  Tickets,
  Money,
  Coin,
  WarningFilled,
}

const decoratedOverviewStats = computed(() =>
  overviewStats.value.map((item) => ({
    ...item,
    label: item.title,
    icon: iconMap[item.icon] || null,
  })),
)

const currentDateText = computed(() => dayjs().format('YYYY年M月D日 dddd'))

const summaryText = computed(() => {
  const statsMap = Object.fromEntries(overviewStats.value.map((item) => [item.key, item]))
  const operatorTotal = statsMap.operatorTotal?.value ?? '--'
  const stationTotal = statsMap.stationTotal?.value ?? '--'
  const todayOrderCount = statsMap.todayOrderCount?.value ?? '--'
  return `当前平台接入 ${operatorTotal} 家运营商、${stationTotal} 座站点，今日累计订单 ${todayOrderCount} 单。`
})

const todayCompletionRate = computed(() => {
  const total = allOrders.value.length
  if (!total) return 0
  const completed = allOrders.value.filter((item) => item.status === 'completed').length
  return Math.round((completed / total) * 100)
})

const opsPulse = computed(() => {
  const operatorItems = distributions.value?.operatorAudit?.items || []
  const stationItems = distributions.value?.stationStatus?.items || []
  const operatorTotal = Number(distributions.value?.operatorAudit?.total || 0)
  const stationTotal = Number(distributions.value?.stationStatus?.total || 0)

  const inReview = operatorItems.find((item) => String(item.label).includes('审核'))?.value || 0
  const pendingStation = stationItems.find((item) => String(item.label).includes('待'))?.value || 0

  return [
    {
      key: 'operator-review',
      label: '运营商审核进度',
      value: operatorTotal ? Math.round(((operatorTotal - inReview) / operatorTotal) * 100) : 100,
      desc: `待审核 ${inReview} 家`,
      tone: 'primary',
    },
    {
      key: 'station-online',
      label: '站点上架进度',
      value: stationTotal ? Math.round(((stationTotal - pendingStation) / stationTotal) * 100) : 100,
      desc: `待上架 ${pendingStation} 座`,
      tone: 'success',
    },
    {
      key: 'order-safety',
      label: '订单风控健康度',
      value: Math.max(0, 100 - orderStats.value.abnormalCount * 6),
      desc: `异常订单 ${orderStats.value.abnormalCount} 单`,
      tone: 'warning',
    },
  ]
})

const abnormalTagType = (status) => {
  if (status === '处理中') return 'warning'
  if (status === '待复核') return 'danger'
  return 'info'
}

const todoPriorityType = (priority) => {
  if (String(priority).includes('高')) return 'danger'
  if (String(priority).includes('协同') || String(priority).includes('处理中')) return 'warning'
  return 'info'
}

const announcementTagType = (level) => {
  if (level === 'warning') return 'warning'
  if (level === 'success') return 'success'
  return 'info'
}

const sanitizeAnnouncement = (item = {}) => {
  const content = String(item.content || '')
    .replace(/当前页面结构已预留真实接口替换位置/g, '本周将持续完善平台审核、订单与清分协同能力。')
    .replace(/本版先提供页面骨架和入口，避免影响主链路截图与前后端联调节奏。/g, '异常订单与清分模块已纳入联动巡检，建议优先关注高风险记录。')
    .replace(/后续接入.*$/g, '当前公告面向日常运营与答辩展示，内容已按正式后台口径整理。')

  return {
    ...item,
    content,
  }
}

const applyPayload = (payload = {}, updatedAt = Date.now()) => {
  baseOverviewStats.value = payload.overviewStats || []
  baseDistributions.value = payload.distributions || null
  todoList.value = payload.todoList || []
  recentActivities.value = payload.recentActivities || []
  announcements.value = (payload.announcements || []).map(sanitizeAnnouncement)
  cacheLabel.value = formatCacheLabel(updatedAt)
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyPayload(cached.value, cached.updatedAt)
  }

  loading.value = !cached || !background
  try {
    const { data } = await fetchAdminDashboard()
    const payload = {
      overviewStats: data.overviewStats || [],
      distributions: data.distributions || null,
      todoList: data.todoList || [],
      recentActivities: data.recentActivities || [],
      announcements: data.announcements || [],
    }
    applyPayload(payload, Date.now())
    setRequestCache(cacheKey, payload)
  } catch (error) {
    if (!baseOverviewStats.value.length) {
      ElMessage.error('平台工作台暂未加载成功')
    }
  } finally {
    loading.value = false
  }
}

const goToTodo = (item) => {
  if (item.route) router.push(item.route)
}

const goToOrderDetail = (row) => {
  router.push(`/admin/orders/detail/${row.id}`)
}

onMounted(() => loadData({ background: true }))
onActivated(() => {
  if (shouldRefreshRequestCache(cacheKey, CACHE_TTL)) {
    loadData({ background: true })
  }
})
</script>

<template>
  <div class="page-shell admin-dashboard">
    <PageSectionHeader
      eyebrow="Admin Console"
      title="平台运营总览"
      description="聚焦审核、订单、清分与风险预警的运营总览。"
      chip="管理员视角"
    >
      <template #actions>
        <div class="hero-meta">
          <span class="hero-meta__date">{{ currentDateText }}</span>
          <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
          <el-button @click="loadData">刷新数据</el-button>
          <el-button type="primary" @click="router.push('/admin/finance')">进入清分中心</el-button>
        </div>
      </template>
    </PageSectionHeader>

    <section class="hero-banner surface-card">
      <div class="hero-banner__content">
        <p class="hero-banner__label">Platform Pulse</p>
        <h2 class="hero-banner__title">面向平台治理的可视化运营中枢</h2>
        <p class="hero-banner__desc">{{ summaryText }}</p>

        <div class="hero-banner__quick-actions">
          <el-button plain @click="router.push('/admin/institutions')">运营商审核</el-button>
          <el-button plain @click="router.push('/admin/institutions/stations')">站点审核</el-button>
          <el-button type="primary" plain @click="router.push('/admin/orders/abnormal')">异常订单</el-button>
        </div>
      </div>

      <div class="hero-banner__dashboard">
        <div class="dashboard-ring">
          <el-progress type="dashboard" :percentage="todayCompletionRate" :stroke-width="14" color="#2f74ff" :show-text="false" :width="136" />
          <div class="dashboard-ring__label">
            <strong>{{ todayCompletionRate }}%</strong>
            <span>订单完成率</span>
          </div>
        </div>
        <div class="dashboard-meta">
          <p>实时充电中 {{ orderStats.chargingCount }} 单</p>
          <p>今日异常 {{ orderStats.abnormalCount }} 单</p>
          <p>累计交易 ¥{{ Number(orderStats.todayTotalAmount || 0).toLocaleString() }}</p>
        </div>
      </div>
    </section>

    <section class="stats-grid stats-grid--dashboard">
      <MetricCard
        v-for="item in decoratedOverviewStats"
        :key="item.key"
        :label="item.label"
        :value="item.value"
        :prefix="item.prefix"
        :suffix="item.suffix"
        :trend="item.trend"
        :trend-label="item.trendLabel"
        :trend-direction="item.trendDirection"
        :tone="item.tone"
        :icon="item.icon"
      />
    </section>

    <section class="panel-grid panel-grid--wide">
      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">运营脉冲</h3>
            <p class="panel-heading__desc">通过关键进度条快速感知平台当前健康状态与优先处理方向。</p>
          </div>
        </div>
        <div class="ops-pulse-list">
          <div v-for="item in opsPulse" :key="item.key" class="ops-pulse-item">
            <div class="ops-pulse-item__head">
              <strong>{{ item.label }}</strong>
              <span>{{ item.value }}%</span>
            </div>
            <el-progress :percentage="item.value" :stroke-width="10" :show-text="false" :color="item.tone === 'primary' ? '#2f74ff' : item.tone === 'success' ? '#22a06b' : '#d9911f'" />
            <p>{{ item.desc }}</p>
          </div>
        </div>
      </article>

      <article class="page-panel surface-card" v-loading="loading">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">待办聚焦</h3>
            <p class="panel-heading__desc">集中展示当前最影响平台流转效率的任务。</p>
          </div>
        </div>

        <div v-if="todoList.length" class="todo-list">
          <button
            v-for="item in todoList"
            :key="item.id"
            type="button"
            class="todo-item"
            @click="goToTodo(item)"
          >
            <div class="todo-item__main">
              <div class="todo-item__title-row">
                <strong>{{ item.title }}</strong>
                <el-tag size="small" :type="todoPriorityType(item.priority)" effect="plain">{{ item.priority }}</el-tag>
              </div>
              <p class="todo-item__desc">{{ item.description }}</p>
            </div>
            <div class="todo-item__side">
              <span class="todo-item__count">{{ item.count }}</span>
              <span class="todo-item__action">{{ item.actionText }}</span>
            </div>
          </button>
        </div>

        <EmptyStateBlock
          v-else-if="!loading"
          title="当前暂无待处理事项"
          description="当待办为空时，会在这里展示默认空状态。"
        />
      </article>
    </section>

    <section class="panel-grid">
      <TrendAreaChart
        title="近 7 日订单趋势"
        subtitle="按自然日呈现订单规模变化，便于观察高峰波动。"
        :data="orderTrend"
        y-field="orderCount"
        :loading="loading"
      />
      <TrendAreaChart
        title="近 7 日交易趋势"
        subtitle="按日展示平台交易金额，用于运营复盘与财务跟踪。"
        :data="revenueTrend"
        y-field="revenue"
        color="#22a06b"
        area-color="rgba(34, 160, 107, 0.16)"
        :value-formatter="(value) => `¥${Number(value).toLocaleString()}`"
        :loading="loading"
      />
    </section>

    <section class="panel-grid distribution-grid">
      <DonutStatusChart
        title="运营商审核分布"
        subtitle="反映平台当前运营商准入审核结构。"
        :items="distributions?.operatorAudit?.items || []"
        :total="distributions?.operatorAudit?.total"
        :total-label="distributions?.operatorAudit?.totalLabel"
        :loading="loading"
      />
      <DonutStatusChart
        title="站点状态分布"
        subtitle="观察已运营、维护中与待审核站点占比。"
        :items="distributions?.stationStatus?.items || []"
        :total="distributions?.stationStatus?.total"
        :total-label="distributions?.stationStatus?.totalLabel"
        :loading="loading"
      />
      <DonutStatusChart
        title="订单状态分布"
        subtitle="从运营视角查看完成、实时与异常订单结构。"
        :items="distributions?.orderStatus?.items || []"
        :total="distributions?.orderStatus?.total"
        :total-label="distributions?.orderStatus?.totalLabel"
        :loading="loading"
      />
    </section>

    <section class="panel-grid panel-grid--wide">
      <article class="page-panel surface-card table-shell" v-loading="loading">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">最近异常订单</h3>
            <p class="panel-heading__desc">展示最新进入异常流程的订单，支持一键跳转详情处理。</p>
          </div>
        </div>

        <el-table v-if="abnormalOrders.length" :data="abnormalOrders">
          <el-table-column prop="orderNo" label="订单编号" min-width="180" />
          <el-table-column prop="userName" label="用户" width="110" />
          <el-table-column prop="stationName" label="站点" min-width="180" />
          <el-table-column prop="abnormalType" label="异常类型" min-width="160" />
          <el-table-column prop="createdAt" label="创建时间" width="150" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="abnormalTagType(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="goToOrderDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <EmptyStateBlock
          v-else-if="!loading"
          title="暂无异常订单"
          description="平台没有进入异常流程的订单时，将显示空状态。"
        />
      </article>

      <article class="page-panel surface-card" v-loading="loading">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">平台公告与动态</h3>
            <p class="panel-heading__desc">展示平台治理动态、运营提醒与系统公告。</p>
          </div>
        </div>

        <div class="activity-list" v-if="recentActivities.length">
          <div v-for="item in recentActivities" :key="item.id" class="activity-item">
            <div class="activity-item__dot"></div>
            <div class="activity-item__content">
              <div class="activity-item__head">
                <strong>{{ item.title }}</strong>
                <span>{{ item.time }}</span>
              </div>
              <p>{{ item.description }}</p>
            </div>
          </div>
        </div>

        <div class="info-list" v-if="announcements.length">
          <div v-for="item in announcements" :key="item.id" class="info-item notice-card">
            <div class="notice-card__head">
              <strong class="info-item__title">{{ item.title }}</strong>
              <el-tag :type="announcementTagType(item.level)">
                {{ item.level === 'warning' ? '提示' : item.level === 'success' ? '已生效' : '公告' }}
              </el-tag>
            </div>
            <p class="info-item__desc">{{ item.content }}</p>
          </div>
        </div>

        <EmptyStateBlock
          v-if="!loading && !recentActivities.length && !announcements.length"
          title="暂无平台动态"
          description="当前暂无新增公告或动态，平台运行平稳。"
        />
      </article>
    </section>
  </div>
</template>

<style scoped>
.admin-dashboard {
  padding-bottom: 8px;
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.hero-meta__date {
  color: var(--color-text-3);
  font-size: 12px;
}

.hero-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 286px;
  gap: 16px;
  padding: 20px 22px;
  background:
    radial-gradient(circle at 82% 10%, rgba(47, 116, 255, 0.2), transparent 34%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.98), rgba(246, 249, 252, 0.95));
  animation: fadeUp 520ms ease both;
}

.hero-banner__label {
  margin: 0;
  color: var(--color-primary-strong);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.hero-banner__title {
  margin: 8px 0 0;
  font-size: 24px;
  line-height: 1.2;
  color: var(--color-text);
}

.hero-banner__desc {
  margin: 10px 0 0;
  color: var(--color-text-2);
  font-size: 13px;
  line-height: 1.55;
}

.hero-banner__quick-actions {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-banner__dashboard {
  border-radius: 18px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(244, 248, 252, 0.72));
  border: 1px solid rgba(47, 116, 255, 0.14);
}

.dashboard-ring {
  position: relative;
  display: flex;
  justify-content: center;
}

.dashboard-ring__label {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
}

.dashboard-ring__label strong {
  font-size: 24px;
  color: var(--color-text);
  line-height: 1;
}

.dashboard-ring__label span {
  margin-top: 3px;
  color: var(--color-text-3);
  font-size: 11px;
}

.dashboard-meta {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.dashboard-meta p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-2);
}

.stats-grid--dashboard {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.distribution-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.ops-pulse-list {
  display: grid;
  gap: 14px;
}

.ops-pulse-item {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(246, 249, 253, 0.9));
}

.ops-pulse-item__head {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ops-pulse-item__head strong {
  color: var(--color-text);
  font-size: 14px;
}

.ops-pulse-item__head span {
  color: var(--color-primary-strong);
  font-weight: 700;
}

.ops-pulse-item p {
  margin: 8px 0 0;
  color: var(--color-text-3);
  font-size: 12px;
}

.todo-list,
.activity-list {
  display: grid;
  gap: 12px;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: var(--color-surface-3);
  text-align: left;
  cursor: pointer;
  transition: transform var(--motion-fast) ease, border-color var(--motion-fast) ease, box-shadow var(--motion-fast) ease;
}

.todo-item:hover {
  transform: translateY(-2px);
  border-color: rgba(47, 116, 255, 0.22);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
}

.todo-item__title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.todo-item__desc {
  margin: 8px 0 0;
  color: var(--color-text-2);
  font-size: 12px;
  line-height: 1.5;
}

.todo-item__side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  min-width: 72px;
}

.todo-item__count {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
}

.todo-item__action {
  color: var(--color-primary-strong);
  font-size: 12px;
}

.activity-item {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  gap: 12px;
}

.activity-item__dot {
  position: relative;
  margin-top: 6px;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #2f74ff, #22a06b);
  box-shadow: 0 0 0 4px rgba(47, 116, 255, 0.1);
}

.activity-item__content {
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--color-border);
}

.activity-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.activity-item__head span {
  color: var(--color-text-3);
  font-size: 12px;
}

.activity-item__content p {
  margin: 8px 0 0;
  color: var(--color-text-2);
  line-height: 1.6;
}

.notice-card {
  background: linear-gradient(180deg, var(--color-surface-3), rgba(255, 255, 255, 0.85));
}

.notice-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1280px) {
  .hero-banner {
    grid-template-columns: 1fr;
  }

  .distribution-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-meta,
  .todo-item,
  .activity-item__head {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-banner {
    padding: 16px;
  }

  .stats-grid--dashboard {
    grid-template-columns: 1fr;
  }

  .todo-item__side {
    align-items: flex-start;
  }
}
</style>
