<script setup>
import { computed, onActivated, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Bell, TrendCharts, Lightning } from '@element-plus/icons-vue'

import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import { ROLES, getStoredOperatorId } from '../../config/permissions'
import { fetchOperatorDashboard } from '../../api/console'
import { fetchOperatorOrderStats, fetchOperatorRealtimeOrders } from '../../api/operator'
import { useOrderStore } from '../../stores/order'
import { buildRequestCacheKey, formatCacheLabel, getRequestCache, setRequestCache, shouldRefreshRequestCache } from '../../utils/requestCache'

const orderStore = useOrderStore()
const apiOrderStats = ref(null)
const apiRealtimeRows = ref([])
/** 接口已成功返回过实时列表后，即使为空也不再使用本地 mock */
const realtimeListFromApi = ref(false)
const ORDER_SNAPSHOT_POLL_MS = 8000
const loading = ref(false)
const profile = ref(null)
const stationHealth = ref([])
const alarms = ref([])
const cacheLabel = ref('')
const CACHE_TTL = 12 * 1000
const scope = {
  role: ROLES.OPERATOR,
  operatorId: getStoredOperatorId(),
}
const cacheKey = buildRequestCacheKey('/console/operator/dashboard', { scope: 'operator-dashboard' })

const orderStats = computed(() => {
  const s = apiOrderStats.value
  if (s) {
    return {
      chargingCount: Number(s.charging_count || 0),
      todayCompletedCount: Number(s.today_completed_count || 0),
      todayTotalChargeAmount: Number(s.today_charge_amount || 0).toFixed(2),
      todayTotalAmount: Number(s.today_total_amount || 0).toFixed(2),
      abnormalCount: Number(s.abnormal_count || 0),
    }
  }
  return orderStore.getOrderStats(scope)
})
const cards = computed(() => [
  {
    label: '实时充电订单',
    value: orderStats.value.chargingCount,
    suffix: ' 单',
    trend: '实时订单监控',
    trendLabel: '来自本机构充电中订单',
    tone: 'primary',
    icon: Monitor,
  },
  {
    label: '今日完成订单',
    value: orderStats.value.todayCompletedCount,
    suffix: ' 单',
    trend: '历史订单累计',
    trendLabel: '用于复盘日内运营效率',
    tone: 'success',
    icon: TrendCharts,
  },
  {
    label: '今日充电量',
    value: orderStats.value.todayTotalChargeAmount,
    suffix: ' kWh',
    trend: '已完成订单累计',
    trendLabel: '反映站点负载活跃度',
    tone: 'warning',
    icon: Lightning,
  },
  {
    label: '异常订单数量',
    value: orderStats.value.abnormalCount,
    suffix: ' 单',
    trend: '风控预警联动',
    trendLabel: '建议优先处理高风险异常',
    tone: 'danger',
    icon: Bell,
  },
])

const orderTrend = computed(() => orderStore.getOrderTrend(scope, 7))
const realtimeOrders = computed(() => {
  if (realtimeListFromApi.value) {
    return apiRealtimeRows.value.map((row) => ({
      id: row.id,
      orderNo: row.order_no,
      vehiclePlate: row.vin || row.user_nickname || '-',
      stationName: row.station_name,
      connectorName: row.charger_name,
      chargedKwh: Number(row.charge_amount || 0).toFixed(2),
      amount: Number(row.total_amount || 0).toFixed(2),
      status: Number(row.status) === 0 ? 'charging' : 'other',
    }))
  }
  return orderStore.getRealtimeOrders(scope).map((order) => ({
    id: order.id,
    orderNo: order.orderNo,
    vehiclePlate: order.vin || '-',
    stationName: order.stationName,
    connectorName: order.chargerName,
    chargedKwh: Number(order.chargeAmount).toFixed(2),
    amount: Number(order.totalAmount).toFixed(2),
    status: order.status,
  }))
})

const maxOrderCount = computed(() => Math.max(1, ...orderTrend.value.map((item) => item.orderCount)))

const onlineRate = computed(() => Number(profile.value?.onlineRate || 0))
const healthyStationCount = computed(() => {
  const item = stationHealth.value.find((i) => String(i.status).includes('正常'))
  return Number(item?.count || 0)
})

const applyPayload = (payload = {}, updatedAt = Date.now()) => {
  profile.value = payload.profile || null
  stationHealth.value = payload.stationHealth || []
  alarms.value = payload.alarms || []
  cacheLabel.value = formatCacheLabel(updatedAt)
}

/** 订单变更事件在短时间内可能多次触发，合并为一次快照请求 */
let ordersMutatedDebounceTimer = null

/**
 * 驾驶舱订单快照为只读聚合，不参与 operatorOrderDataEpoch 门禁。
 * Epoch 用于订单列表页防「清空缓存后旧请求写回」；若此处也比对 epoch，
 * 在结束/创建订单 bump 后易把在途快照整段丢弃，出现工作台与订单模块数据此消彼长。
 */
const loadOrderSnapshot = async () => {
  try {
    const [statsRes, rtRes] = await Promise.all([
      fetchOperatorOrderStats(),
      fetchOperatorRealtimeOrders({ page: 1, page_size: 15 }),
    ])
    const st = statsRes?.data
    if (st?.code === 200 && st.data) {
      apiOrderStats.value = st.data
    }
    const rt = rtRes?.data
    if (rt?.code === 200 && rt.data) {
      realtimeListFromApi.value = true
      apiRealtimeRows.value = Array.isArray(rt.data.items) ? rt.data.items : []
    }
  } catch {
    /* 驾驶舱 mock 仍可展示 */
  }
}

const onOperatorOrdersMutated = () => {
  if (ordersMutatedDebounceTimer != null) {
    clearTimeout(ordersMutatedDebounceTimer)
  }
  ordersMutatedDebounceTimer = window.setTimeout(() => {
    ordersMutatedDebounceTimer = null
    void loadOrderSnapshot()
  }, 280)
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyPayload(cached.value, cached.updatedAt)
  }

  loading.value = !cached || !background
  try {
    const { data } = await fetchOperatorDashboard()
    const payload = {
      profile: data.profile || null,
      stationHealth: data.stationHealth || [],
      alarms: data.alarms || [],
    }
    applyPayload(payload, Date.now())
    setRequestCache(cacheKey, payload)
    void loadOrderSnapshot()
  } catch (error) {
    if (!profile.value) {
      ElMessage.error('运营商工作台暂未加载成功')
    }
  } finally {
    loading.value = false
  }
}

let orderSnapshotTimer = null
onMounted(() => {
  void loadData({ background: true })
  void loadOrderSnapshot()
  if (typeof window !== 'undefined') {
    window.addEventListener('echarge:operator-orders-mutated', onOperatorOrdersMutated)
  }
  orderSnapshotTimer = window.setInterval(() => {
    void loadOrderSnapshot()
  }, ORDER_SNAPSHOT_POLL_MS)
})
onActivated(() => {
  void loadOrderSnapshot()
  if (shouldRefreshRequestCache(cacheKey, CACHE_TTL)) {
    loadData({ background: true })
  }
})
onUnmounted(() => {
  if (ordersMutatedDebounceTimer != null) {
    clearTimeout(ordersMutatedDebounceTimer)
    ordersMutatedDebounceTimer = null
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('echarge:operator-orders-mutated', onOperatorOrdersMutated)
  }
  if (orderSnapshotTimer != null) {
    clearInterval(orderSnapshotTimer)
    orderSnapshotTimer = null
  }
})
</script>

<template>
  <div class="page-shell operator-dashboard-page">
    <PageSectionHeader
      eyebrow="Operator Console"
      title="运营中心驾驶舱"
      description="面向运营商日常经营的订单、营收与站点健康总览。"
      chip="运营商视角"
    >
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button @click="loadData">刷新概览</el-button>
        <el-button type="primary">发起巡检</el-button>
      </template>
    </PageSectionHeader>

    <section v-if="profile" class="operator-hero surface-card">
      <div class="operator-hero__left">
        <p class="operator-hero__eyebrow">Operator Profile</p>
        <h2>{{ profile.operatorName }}</h2>
        <p>{{ profile.region }} · {{ profile.stationCount }} 座站点 · {{ profile.connectorCount }} 个枪口</p>

        <div class="operator-hero__chips">
          <span>健康站点 {{ healthyStationCount }} 座</span>
          <span>今日完成订单 {{ orderStats.todayCompletedCount }} 单</span>
          <span>实时充电 {{ orderStats.chargingCount }} 单</span>
        </div>
      </div>

      <div class="operator-hero__right">
        <div class="ring-wrap">
          <el-progress type="dashboard" :percentage="Math.round(onlineRate)" :stroke-width="14" color="#22a06b" :show-text="false" :width="132" />
          <div class="ring-wrap__label">
            <strong>{{ onlineRate.toFixed(1) }}%</strong>
            <span>设备在线率</span>
          </div>
        </div>
      </div>
    </section>

    <section class="stats-grid">
      <MetricCard
        v-for="item in cards"
        :key="item.label"
        :label="item.label"
        :value="item.value"
        :suffix="item.suffix"
        :trend="item.trend"
        :trend-label="item.trendLabel"
        :tone="item.tone"
        :icon="item.icon"
      />
    </section>

    <section class="split-layout">
      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">近 7 日订单趋势</h3>
            <p class="panel-heading__desc">按自然日展示订单量与收入变化，便于观察运营波峰。</p>
          </div>
        </div>

        <div class="order-trend">
          <div v-for="item in orderTrend" :key="item.date" class="order-trend__row">
            <span class="order-trend__date">{{ item.date }}</span>
            <div class="order-trend__track">
              <div class="order-trend__fill" :style="{ width: `${(item.orderCount / maxOrderCount) * 100}%` }"></div>
            </div>
            <strong>{{ item.orderCount }}</strong>
            <span class="order-trend__revenue">¥{{ item.revenue.toLocaleString() }}</span>
          </div>
        </div>
      </article>

      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">站点健康概况</h3>
            <p class="panel-heading__desc">用状态卡片和进度条快速识别站点运营风险。</p>
          </div>
        </div>

        <div class="info-list" v-if="stationHealth.length">
          <div v-for="item in stationHealth" :key="item.status" class="list-card health-card">
            <strong class="list-card__title">{{ item.status }}</strong>
            <p class="list-card__meta">{{ item.count }} 座站点</p>
            <el-progress :percentage="Math.min(100, Math.round((item.count / Math.max(1, profile?.stationCount || 1)) * 100))" :show-text="false" :stroke-width="8" />
          </div>
        </div>

        <EmptyStateBlock v-else title="暂无站点健康数据" description="后续接入健康监测接口后，这里会展示实时健康分布。" />
      </article>
    </section>

    <section class="panel-grid">
      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">设备告警</h3>
            <p class="panel-heading__desc">用于定位高优先级设备问题，方便运维班组快速处理。</p>
          </div>
        </div>
        <div class="alarm-list" v-if="alarms.length">
          <div v-for="item in alarms" :key="item.id" class="list-card alarm-card">
            <div class="alarm-head">
              <strong class="list-card__title">{{ item.stationName }}</strong>
              <el-tag :type="item.level === 'high' ? 'danger' : item.level === 'medium' ? 'warning' : 'info'">
                {{ item.level === 'high' ? '高告警' : item.level === 'medium' ? '中告警' : '低告警' }}
              </el-tag>
            </div>
            <p class="list-card__meta">{{ item.equipmentCode }} · {{ item.issue }}</p>
            <p class="list-card__meta">{{ item.detectedAt }} · {{ item.suggestion }}</p>
          </div>
        </div>

        <EmptyStateBlock v-else title="暂无设备告警" description="当前设备运行平稳，无需额外处置。" />
      </article>

      <article class="page-panel surface-card table-shell">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">实时充电订单</h3>
            <p class="panel-heading__desc">展示当前正在充电的订单，便于站点实时巡检与客服响应。</p>
          </div>
        </div>
        <el-table v-loading="loading" :data="realtimeOrders" size="small" v-if="realtimeOrders.length">
          <el-table-column prop="orderNo" label="订单号" min-width="180" />
          <el-table-column prop="vehiclePlate" label="车牌/VIN" width="120" />
          <el-table-column prop="stationName" label="站点" min-width="170" />
          <el-table-column prop="connectorName" label="设备" min-width="150" />
          <el-table-column label="电量(kWh)" width="130">
            <template #default="{ row }">
              <div class="mini-progress">
                <span>{{ row.chargedKwh }}</span>
                <el-progress :percentage="Math.min(100, Number(row.chargedKwh) * 2.4)" :show-text="false" :stroke-width="8" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="金额" width="110" align="right">
            <template #default="{ row }">¥{{ row.amount }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'charging' ? 'success' : 'warning'">
                {{ row.status === 'charging' ? '充电中' : '待结算' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <EmptyStateBlock
          v-else-if="!loading"
          title="当前暂无实时订单"
          description="当前时段暂无进行中的充电订单。"
        />
      </article>
    </section>
  </div>
</template>

<style scoped>
.operator-dashboard-page {
  padding-bottom: 8px;
}

.operator-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 232px;
  gap: 16px;
  padding: 18px 22px;
  background:
    radial-gradient(circle at 88% 8%, rgba(34, 160, 107, 0.2), transparent 32%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.98), rgba(244, 249, 246, 0.94));
}

.operator-hero__eyebrow {
  margin: 0;
  color: #22a06b;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 700;
}

.operator-hero h2 {
  margin: 8px 0 0;
  color: var(--color-text);
  font-size: 24px;
}

.operator-hero p {
  margin: 8px 0 0;
  color: var(--color-text-2);
  font-size: 13px;
}

.operator-hero__chips {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.operator-hero__chips span {
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(34, 160, 107, 0.1);
  border: 1px solid rgba(34, 160, 107, 0.24);
  color: #16885a;
  font-size: 11px;
}

.operator-hero__right {
  display: grid;
  place-items: center;
}

.ring-wrap {
  position: relative;
}

.ring-wrap__label {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
}

.ring-wrap__label strong {
  font-size: 22px;
  color: var(--color-text);
  line-height: 1;
}

.ring-wrap__label span {
  margin-top: 3px;
  color: var(--color-text-3);
  font-size: 11px;
}

.order-trend {
  display: grid;
  gap: 10px;
}

.order-trend__row {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) 60px 110px;
  gap: 12px;
  align-items: center;
}

.order-trend__date,
.order-trend__revenue {
  color: var(--color-text-3);
  font-size: 12px;
}

.order-trend__track {
  height: 12px;
  border-radius: 999px;
  background: var(--color-surface-3);
  overflow: hidden;
}

.order-trend__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2f74ff, #6aa7ff);
  animation: growBar 700ms ease both;
}

.health-card {
  text-align: center;
}

.alarm-list {
  display: grid;
  gap: 10px;
}

.alarm-card {
  border: 1px solid rgba(47, 116, 255, 0.14);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 251, 255, 0.9));
}

.alarm-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mini-progress {
  display: grid;
  gap: 6px;
}

.mini-progress span {
  font-size: 12px;
  color: var(--color-text-2);
}

@keyframes growBar {
  from {
    transform: scaleX(0.6);
    opacity: 0.5;
  }
  to {
    transform: scaleX(1);
    opacity: 1;
  }
}

@media (max-width: 980px) {
  .operator-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .order-trend__row {
    grid-template-columns: 1fr;
  }
}
</style>
