<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { IconArrowUpRight, IconBolt, IconCurrencyYuan, IconPlugConnected, IconUsers, IconExternalLink } from '@tabler/icons-vue'

import { fetchOverviewSummary, fetchRealtimeOrders } from '../api/overview'

const SUMMARY_STORAGE_KEY = 'echarge-dashboard-summary-v1'
const ORDERS_STORAGE_KEY = 'echarge-dashboard-orders-v1'

let overviewPollTimer = null

const POLL_MS = 20000

const scheduleOverviewPoll = () => {
  if (overviewPollTimer) {
    window.clearInterval(overviewPollTimer)
    overviewPollTimer = null
  }
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    return
  }
  overviewPollTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') {
      void loadData(true)
    }
  }, POLL_MS)
}

const onVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    void loadData(true)
    scheduleOverviewPoll()
  } else if (overviewPollTimer) {
    window.clearInterval(overviewPollTimer)
    overviewPollTimer = null
  }
}

const loading = ref(false)
/** 已有可信数据（本会话接口成功，或 sessionStorage 恢复），避免把初始 0 当成真实指标 */
const summaryDataReady = ref(false)

const defaultSummary = () => ({
  today_orders: 0,
  today_orders_change: 0,
  today_revenue: 0,
  today_revenue_change: 0,
  online_piles: 0,
  total_piles: 0,
  pile_availability: 0,
  active_users: 0,
  new_users_month: 0,
})

const summary = ref(defaultSummary())

const realtimeOrders = ref([])

const ordersChartRef = ref(null)
const revenueChartRef = ref(null)
let ordersChart
let revenueChart
const chartsHidden = ref(true)
let echartsApiPromise

const getEcharts = async () => {
  if (echartsApiPromise) return echartsApiPromise
  echartsApiPromise = (async () => {
    const echarts = await import('echarts/core')
    const charts = await import('echarts/charts')
    const components = await import('echarts/components')
    const renderers = await import('echarts/renderers')
    echarts.use([
      components.GridComponent,
      components.TooltipComponent,
      charts.LineChart,
      charts.BarChart,
      renderers.CanvasRenderer,
    ])
    return echarts
  })()
  return echartsApiPromise
}

const animated = ref({
  today_orders: 0,
  today_revenue: 0,
  online_piles: 0,
  active_users: 0,
})

const chartSkeleton = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600" viewBox="0 0 1200 600">
    <rect width="1200" height="600" fill="rgba(0,0,0,0)"/>
  </svg>`,
)}`

const formatMoney = (v) => {
  const num = Number(v || 0)
  return num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

const animateNumber = (key, to, duration = 800) => {
  const from = Number(animated.value[key] || 0)
  const target = Number(to || 0)
  const start = performance.now()
  const tick = (t) => {
    const p = Math.min(1, (t - start) / duration)
    const eased = 1 - Math.pow(1 - p, 3)
    animated.value[key] = from + (target - from) * eased
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

const syncAnimatedFromSummary = () => {
  animated.value.today_orders = Number(summary.value.today_orders || 0)
  animated.value.today_revenue = Number(summary.value.today_revenue || 0)
  animated.value.online_piles = Number(summary.value.online_piles || 0)
  animated.value.active_users = Number(summary.value.active_users || 0)
}

const hydrateOverviewFromSession = () => {
  try {
    const rawS = sessionStorage.getItem(SUMMARY_STORAGE_KEY)
    if (rawS) {
      const parsed = JSON.parse(rawS)
      if (parsed && typeof parsed === 'object') {
        summary.value = { ...defaultSummary(), ...parsed }
        summaryDataReady.value = true
        syncAnimatedFromSummary()
      }
    }
    const rawO = sessionStorage.getItem(ORDERS_STORAGE_KEY)
    if (rawO) {
      const parsed = JSON.parse(rawO)
      if (Array.isArray(parsed)) {
        realtimeOrders.value = parsed
      }
    }
  } catch {
    /* ignore corrupt session */
  }
}

const persistOverviewToSession = () => {
  try {
    sessionStorage.setItem(SUMMARY_STORAGE_KEY, JSON.stringify(summary.value))
    sessionStorage.setItem(ORDERS_STORAGE_KEY, JSON.stringify(realtimeOrders.value))
  } catch {
    /* quota or private mode */
  }
}

const loadData = async (silent = false) => {
  if (!silent) {
    loading.value = true
  }
  try {
    const [summaryRes, ordersRes] = await Promise.all([
      fetchOverviewSummary(),
      fetchRealtimeOrders(),
    ])

    summary.value = { ...defaultSummary(), ...(summaryRes.data || {}) }
    realtimeOrders.value = Array.isArray(ordersRes.data) ? ordersRes.data : []
    summaryDataReady.value = true
    persistOverviewToSession()
  } catch (error) {
    console.error(error)
    if (!silent) {
      ElMessage.error('加载概览数据失败，请稍后重试')
    }
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

const baseGrid = { left: 24, right: 16, top: 18, bottom: 16, containLabel: true }

const getChartThemeTokens = () => {
  const root = getComputedStyle(document.documentElement)
  const text2 = root.getPropertyValue('--color-text-2').trim() || 'rgba(17,24,39,0.72)'
  const text3 = root.getPropertyValue('--color-text-3').trim() || 'rgba(17,24,39,0.54)'
  const gridLine = root.getPropertyValue('--color-border').trim() || 'rgba(17,24,39,0.08)'
  return { text2, text3, gridLine }
}

const initOrdersChart = async () => {
  if (!ordersChartRef.value) return
  const echarts = await getEcharts()
  if (!ordersChart) ordersChart = echarts.init(ordersChartRef.value)
  const xDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const ordersData = [120, 132, 101, 134, 90, 230, 210]
  const { text2, text3, gridLine } = getChartThemeTokens()
  ordersChart.setOption({
    aria: { enabled: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17,24,39,0.92)',
      borderWidth: 0,
      textStyle: { color: '#fff' },
      extraCssText: 'border-radius: 12px; padding: 10px 12px;',
    },
    grid: baseGrid,
    xAxis: {
      type: 'category',
      data: xDays,
      boundaryGap: false,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: gridLine } },
      axisLabel: { color: text3 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: text3 },
      splitLine: { lineStyle: { color: gridLine } },
    },
    series: [
      {
        name: '订单量',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: ordersData,
        lineStyle: { color: '#409EFF', width: 2 },
        itemStyle: { color: '#409EFF' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.35)' },
            { offset: 1, color: 'rgba(64,158,255,0.06)' },
          ]),
        },
      },
    ],
    textStyle: { color: text2 },
  })
  setTimeout(() => {
    chartsHidden.value = false
  }, 0)
}

const initRevenueChart = async () => {
  if (!revenueChartRef.value) return
  const echarts = await getEcharts()
  if (!revenueChart) revenueChart = echarts.init(revenueChartRef.value)
  const xDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const revenueData = [12580, 13620, 11850, 14200, 13150, 15020, 16230]
  const { text2, text3, gridLine } = getChartThemeTokens()
  revenueChart.setOption({
    aria: { enabled: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17,24,39,0.92)',
      borderWidth: 0,
      textStyle: { color: '#fff' },
      extraCssText: 'border-radius: 12px; padding: 10px 12px;',
      valueFormatter: (v) => `¥ ${formatMoney(v)}`,
    },
    grid: baseGrid,
    xAxis: {
      type: 'category',
      data: xDays,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: gridLine } },
      axisLabel: { color: text3 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: text3 },
      splitLine: { lineStyle: { color: gridLine } },
    },
    series: [
      {
        name: '收益(元)',
        type: 'bar',
        data: revenueData,
        itemStyle: { color: '#67C23A', borderRadius: [10, 10, 6, 6] },
        barMaxWidth: 28,
      },
    ],
    textStyle: { color: text2 },
  })
  setTimeout(() => {
    chartsHidden.value = false
  }, 0)
}

const handleResize = () => {
  ordersChart && ordersChart.resize()
  revenueChart && revenueChart.resize()
}

watch(
  () => summary.value,
  (v) => {
    if (!summaryDataReady.value) return
    animateNumber('today_orders', v.today_orders, 800)
    animateNumber('today_revenue', v.today_revenue, 800)
    animateNumber('online_piles', v.online_piles, 800)
    animateNumber('active_users', v.active_users, 800)
  },
  { deep: true },
)

const handleThemeChange = () => {
  chartsHidden.value = true
  setTimeout(() => {
    initOrdersChart()
    initRevenueChart()
    handleResize()
    chartsHidden.value = false
  }, 300)
}

onMounted(() => {
  hydrateOverviewFromSession()
  void loadData()
  scheduleOverviewPoll()
  window.addEventListener('resize', handleResize)
  window.addEventListener('themechange', handleThemeChange)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  if (overviewPollTimer) {
    window.clearInterval(overviewPollTimer)
    overviewPollTimer = null
  }
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('themechange', handleThemeChange)
  ordersChart && ordersChart.dispose()
  revenueChart && revenueChart.dispose()
})
</script>

<template>
  <div class="dash">
    <section class="dash-grid dash-grid--cards">
      <div class="metric surface-card fade-up" role="group" aria-label="今日订单指标卡片">
        <div class="metric__icon metric__icon--primary" aria-hidden="true">
          <IconBolt :size="20" />
        </div>
        <div class="metric__meta">
          <div class="metric__label">今日订单</div>
          <div class="metric__value">{{ summaryDataReady ? Math.round(animated.today_orders).toLocaleString() : loading ? '加载中…' : '—' }}</div>
          <div class="metric__sub" aria-label="订单变化率">
            <IconArrowUpRight :size="16" />
            <span>{{ summaryDataReady ? `${summary.today_orders_change}%` : '—' }}</span>
            <span class="metric__subText">较昨日</span>
          </div>
        </div>
      </div>

      <div class="metric surface-card fade-up" role="group" aria-label="今日收益指标卡片">
        <div class="metric__icon metric__icon--success" aria-hidden="true">
          <IconCurrencyYuan :size="20" />
        </div>
        <div class="metric__meta">
          <div class="metric__label">今日收益</div>
          <div class="metric__value">{{ summaryDataReady ? `¥${formatMoney(animated.today_revenue)}` : loading ? '加载中…' : '—' }}</div>
          <div class="metric__sub" aria-label="收益变化率">
            <IconArrowUpRight :size="16" />
            <span>{{ summaryDataReady ? `${summary.today_revenue_change}%` : '—' }}</span>
            <span class="metric__subText">较昨日</span>
          </div>
        </div>
      </div>

      <div class="metric surface-card fade-up" role="group" aria-label="在线电桩指标卡片">
        <div class="metric__icon metric__icon--info" aria-hidden="true">
          <IconPlugConnected :size="20" />
        </div>
        <div class="metric__meta">
          <div class="metric__label">在线电桩</div>
          <div class="metric__value">
            {{ summaryDataReady ? `${Math.round(animated.online_piles)}/${summary.total_piles}` : loading ? '加载中…' : '—' }}
          </div>
          <div class="metric__sub" aria-label="可用率">
            <span class="metric__subText">可用率</span>
            <span>{{ summaryDataReady ? `${summary.pile_availability}%` : '—' }}</span>
          </div>
        </div>
      </div>

      <div class="metric surface-card fade-up" role="group" aria-label="活跃用户指标卡片">
        <div class="metric__icon metric__icon--warning" aria-hidden="true">
          <IconUsers :size="20" />
        </div>
        <div class="metric__meta">
          <div class="metric__label">活跃用户</div>
          <div class="metric__value">{{ summaryDataReady ? Math.round(animated.active_users).toLocaleString() : loading ? '加载中…' : '—' }}</div>
          <div class="metric__sub" aria-label="本月新增用户数">
            <span class="metric__subText">本月新增</span>
            <span>{{ summaryDataReady ? summary.new_users_month : '—' }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="dash-grid dash-grid--charts">
      <div class="panel surface-card fade-up">
        <div class="panel__head">
          <div class="panel__titleWrap">
            <h3 class="panel__title">订单趋势</h3>
            <p class="panel__sub">近 7 天订单量（Mock）</p>
          </div>
        </div>
        <div class="sr-only" role="note">订单趋势图，展示近 7 天订单量变化。</div>
        <div class="chartWrap">
          <img v-lazy="chartSkeleton" class="lazySentinel" alt="" aria-hidden="true" @load="initOrdersChart" />
          <div ref="ordersChartRef" class="chart chart-fade" :class="{ 'is-hidden': chartsHidden }"></div>
        </div>
      </div>

      <div class="panel surface-card fade-up">
        <div class="panel__head">
          <div class="panel__titleWrap">
            <h3 class="panel__title">收益趋势</h3>
            <p class="panel__sub">近 7 天收益（Mock）</p>
          </div>
        </div>
        <div class="sr-only" role="note">收益趋势图，展示近 7 天收益金额变化。</div>
        <div class="chartWrap">
          <img v-lazy="chartSkeleton" class="lazySentinel" alt="" aria-hidden="true" @load="initRevenueChart" />
          <div ref="revenueChartRef" class="chart chart-fade" :class="{ 'is-hidden': chartsHidden }"></div>
        </div>
      </div>
    </section>

    <section class="panel surface-card fade-up">
      <div class="panel__head panel__head--row">
        <div class="panel__titleWrap">
          <h3 class="panel__title">实时充电订单</h3>
          <p class="panel__sub">当前正在进行的充电订单</p>
        </div>
        <el-button link type="primary" aria-label="查看实时充电订单列表">
          查看更多
          <IconExternalLink :size="16" style="margin-left: 6px;" />
        </el-button>
      </div>

      <el-table
        :data="realtimeOrders"
        v-loading="loading"
        size="small"
        :max-height="320"
        style="width: 100%"
        aria-label="实时充电订单表格"
      >
        <el-table-column prop="user_name" label="用户" width="140" />
        <el-table-column prop="station_name" label="充电站" min-width="220" show-overflow-tooltip />
        <el-table-column prop="charged_kwh" label="已充电量 (kWh)" width="140" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag type="success" v-if="row.status === 'charging'">充电中</el-tag>
            <el-tag type="info" v-else>—</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: var(--grid-gap);
}

.dash-grid {
  display: grid;
  gap: var(--grid-gap);
}

.dash-grid--cards {
  grid-template-columns: repeat(12, minmax(0, 1fr));
}

.dash-grid--charts {
  grid-template-columns: repeat(12, minmax(0, 1fr));
}

.metric,
.panel {
  padding: 16px;
}

.metric {
  display: flex;
  gap: 14px;
  align-items: center;
  min-height: 92px;
}

.metric__icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
}

.metric__icon--primary {
  background: rgba(64, 158, 255, 0.10);
  color: var(--color-primary);
}

.metric__icon--success {
  background: rgba(103, 194, 58, 0.10);
  color: var(--color-success);
}

.metric__icon--warning {
  background: rgba(230, 162, 60, 0.12);
  color: var(--color-warning);
}

.metric__icon--info {
  background: rgba(144, 147, 153, 0.10);
  color: var(--color-info);
}

.metric__label {
  font-size: var(--font-size-2);
  color: var(--color-text-3);
  letter-spacing: 0.2px;
}

.metric__value {
  margin-top: 2px;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--color-text);
}

.metric__sub {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-1);
  color: var(--color-text-2);
}

.metric__subText {
  color: var(--color-text-3);
}

.panel__head {
  margin-bottom: 10px;
}

.panel__head--row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel__title {
  margin: 0;
  font-size: var(--font-size-3);
  font-weight: 700;
  color: var(--color-text);
}

.panel__sub {
  margin: 4px 0 0 0;
  font-size: var(--font-size-1);
  color: var(--color-text-3);
}

.chartWrap {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
}

.chart {
  height: 280px;
  width: 100%;
}

.lazySentinel {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  pointer-events: none;
}

.dash-grid--cards > .metric {
  grid-column: span 3;
}

.dash-grid--charts > .panel {
  grid-column: span 6;
}

@media (max-width: 1366px) {
  .dash-grid--cards > .metric {
    grid-column: span 6;
  }
  .dash-grid--charts > .panel {
    grid-column: span 12;
  }
}

@media (max-width: 768px) {
  .dash-grid--cards > .metric {
    grid-column: span 12;
  }
}
</style>

