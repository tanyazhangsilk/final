<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, Document, Money, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import { fetchAdminOrderDetail } from '../../api/admin'
import { fetchOperatorOrderDetail } from '../../api/operator'
import { ROLES } from '../../config/permissions'
import { getDemoOrderDetail } from '../../utils/demoOrderAdapter'
import { buildRequestCacheKey, formatCacheLabel, getRequestCache, setRequestCache } from '../../utils/requestCache'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const order = ref(null)
const loadError = ref('')
const cacheLabel = ref('')

const CACHE_TTL = 45 * 1000

const isAdmin = computed(() => route.meta?.role === ROLES.ADMIN)
const cacheKey = computed(() =>
  buildRequestCacheKey(isAdmin.value ? `/admin/orders/${route.params.id}` : `/operator/orders/${route.params.id}`, {
    scope: 'order-detail',
    orderId: route.params.id,
  }),
)

const formatMoney = (value) => `￥${Number(value || 0).toFixed(2)}`
const feeDetail = computed(() => order.value?.fee_detail || {})
const statusFlow = computed(() => order.value?.status_flow || [])

const summaryCards = computed(() => {
  if (!order.value) return []
  const o = order.value
  return [
    {
      label: '订单状态',
      value: o.status_text || '-',
      trend: '当前订单处理状态',
      trendLabel: '与状态流转同步更新',
      tone: o.abnormal_reason ? 'danger' : o.end_time ? 'success' : 'warning',
      icon: Document,
    },
    {
      label: '订单来源',
      value: o.source_type_text || o.source_type || '-',
      trend: '业务入口来源',
      trendLabel: o.source_type || '业务入口',
      tone: 'primary',
      icon: Clock,
    },
    {
      label: '总费用',
      value: Number(o.total_amount || 0).toFixed(2),
      prefix: '￥',
      trend: '电费与服务费合计',
      trendLabel: '以结算明细为准',
      tone: 'warning',
      icon: Money,
    },
    {
      label: '异常标记',
      value: o.abnormal_reason ? '已标记' : '正常',
      trend: o.abnormal_reason || '当前无异常记录',
      trendLabel: '异常订单会同步展示原因',
      tone: o.abnormal_reason ? 'danger' : 'info',
      icon: WarningFilled,
    },
  ]
})

const applyOrder = (payload, updatedAt = Date.now()) => {
  order.value = payload || null
  cacheLabel.value = formatCacheLabel(updatedAt)
}

const parseDetailResponse = (response) => {
  const body = response?.data
  if (!body || typeof body !== 'object') {
    return { ok: false, payload: null, message: '接口返回异常' }
  }
  if (Number(body.code) !== 200) {
    return { ok: false, payload: null, message: body.message || '订单详情加载失败' }
  }
  const payload = body.data
  if (!payload || typeof payload !== 'object') {
    return { ok: false, payload: null, message: '订单数据为空' }
  }
  return { ok: true, payload, message: '' }
}

const loadOrder = async ({ background = false } = {}) => {
  loadError.value = ''
  const cached = getRequestCache(cacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached?.value) {
    applyOrder(cached.value, cached.updatedAt)
  }

  loading.value = !cached || !background
  try {
    const response = isAdmin.value ? await fetchAdminOrderDetail(route.params.id) : await fetchOperatorOrderDetail(route.params.id)
    const { ok, payload, message } = parseDetailResponse(response)
    if (ok && payload) {
      applyOrder(payload, Date.now())
      setRequestCache(cacheKey.value, payload)
      return
    }
    const fallback = order.value || getDemoOrderDetail(route.params.id)
    if (fallback) {
      applyOrder(fallback, Date.now())
      if (!cached?.value) {
        setRequestCache(cacheKey.value, fallback)
      }
      if (!cached?.value && message) {
        ElMessage.warning(`${message}，已展示本地演示数据`)
      }
    } else {
      applyOrder(null, Date.now())
      loadError.value = message || '订单详情加载失败'
      ElMessage.error(loadError.value)
    }
  } catch (error) {
    const fallback = order.value || getDemoOrderDetail(route.params.id)
    if (fallback) {
      applyOrder(fallback, Date.now())
      if (!cached?.value) {
        setRequestCache(cacheKey.value, fallback)
      }
    } else {
      applyOrder(null, Date.now())
      loadError.value = error?.response?.data?.message || error?.message || '订单详情加载失败'
      ElMessage.error(loadError.value)
    }
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push(isAdmin.value ? '/admin/orders' : '/operator/orders/history')
}

onMounted(() => loadOrder({ background: true }))

watch(
  () => route.params.id,
  () => {
    order.value = null
    loadError.value = ''
    void loadOrder({ background: true })
  },
)
</script>

<template>
  <div class="page-shell detail-page">
    <PageSectionHeader
      eyebrow="订单中心"
      title="订单详情"
      description="查看订单来源、费用明细、站点信息与状态流转记录。"
      :chip="isAdmin ? '平台订单' : '订单中心'"
    >
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button v-if="loadError" type="primary" plain @click="loadOrder()">重新加载</el-button>
        <el-button @click="goBack">返回列表</el-button>
      </template>
    </PageSectionHeader>

    <template v-if="order">
      <section class="stats-grid stats-grid--detail">
        <MetricCard v-for="item in summaryCards" :key="item.label" v-bind="item" />
      </section>

      <section class="detail-grid">
        <article class="page-panel surface-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">订单信息</h3>
              <p class="panel-heading__desc">{{ order.order_no }}</p>
            </div>
          </div>

          <div class="amount-banner">
            <div class="amount-banner__item">
              <span>电费</span>
              <strong>{{ formatMoney(order.electricity_fee) }}</strong>
            </div>
            <div class="amount-banner__item">
              <span>服务费</span>
              <strong>{{ formatMoney(order.service_fee) }}</strong>
            </div>
            <div class="amount-banner__item amount-banner__item--highlight">
              <span>总费用</span>
              <strong>{{ formatMoney(order.total_amount) }}</strong>
            </div>
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="订单编号">{{ order.order_no }}</el-descriptions-item>
            <el-descriptions-item label="订单状态">{{ order.status_text }}</el-descriptions-item>
            <el-descriptions-item label="订单来源">{{ order.source_type_text }}</el-descriptions-item>
            <el-descriptions-item label="来源编码">{{ order.source_type }}</el-descriptions-item>
            <el-descriptions-item label="用户账号">{{ order.user_phone }}</el-descriptions-item>
            <el-descriptions-item label="用户昵称">{{ order.user_nickname }}</el-descriptions-item>
            <el-descriptions-item label="VIN">{{ order.vin || '-' }}</el-descriptions-item>
            <el-descriptions-item label="运营商">{{ order.operator_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ order.start_time || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ order.end_time || '-' }}</el-descriptions-item>
            <el-descriptions-item label="充电时长">{{ order.charge_duration_text || '-' }}</el-descriptions-item>
            <el-descriptions-item label="充电电量">{{ Number(order.charge_amount || 0).toFixed(2) }} kWh</el-descriptions-item>
            <el-descriptions-item label="支付状态">{{ order.pay_status_text }}</el-descriptions-item>
            <el-descriptions-item label="电站名称">{{ order.station_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="站点地址" :span="2">{{ order.station_address || '-' }}</el-descriptions-item>
            <el-descriptions-item label="经纬度" :span="2">
              <template v-if="order.station_longitude != null && order.station_latitude != null">
                {{ Number(order.station_longitude).toFixed(5) }}, {{ Number(order.station_latitude).toFixed(5) }}
              </template>
              <template v-else>-</template>
            </el-descriptions-item>
            <el-descriptions-item label="电站状态">{{ order.station_status_text || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电价模板">{{ order.price_template_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电桩编号">{{ order.charger_sn || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电桩名称">{{ order.charger_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电桩类型">{{ order.charger_type || '-' }}</el-descriptions-item>
            <el-descriptions-item label="桩功率(kW)">{{ order.charger_power_kw != null ? Number(order.charger_power_kw).toFixed(0) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="清分状态">{{ order.settlement_status_text || '-' }}</el-descriptions-item>
            <el-descriptions-item label="异常原因" :span="2">{{ order.abnormal_reason || '无' }}</el-descriptions-item>
          </el-descriptions>

          <div class="fee-card">
            <h4>费用明细</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="充电电量">{{ Number(feeDetail.charge_amount || 0).toFixed(2) }} kWh</el-descriptions-item>
              <el-descriptions-item label="电费">{{ formatMoney(feeDetail.electricity_fee) }}</el-descriptions-item>
              <el-descriptions-item label="服务费">{{ formatMoney(feeDetail.service_fee) }}</el-descriptions-item>
              <el-descriptions-item label="总费用">{{ formatMoney(feeDetail.total_amount) }}</el-descriptions-item>
              <el-descriptions-item label="电价">{{ formatMoney(feeDetail.flat_price) }}</el-descriptions-item>
              <el-descriptions-item label="服务费单价">{{ formatMoney(feeDetail.service_price) }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </article>

        <article class="page-panel surface-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">状态流转</h3>
              <p class="panel-heading__desc">按时间顺序展示创建、开始充电、完成或异常节点。</p>
            </div>
          </div>

          <el-empty v-if="!statusFlow.length" description="暂无流转记录" />
          <el-timeline v-else>
            <el-timeline-item v-for="item in statusFlow" :key="`${item.key}-${item.time}`" :timestamp="item.time" placement="top">
              <div class="timeline-card">
                <strong>{{ item.title }}</strong>
                <p>{{ item.desc }}</p>
              </div>
            </el-timeline-item>
          </el-timeline>
        </article>
      </section>
    </template>

    <section v-else-if="loading" class="page-panel surface-card">
      <el-skeleton :rows="8" animated />
    </section>

    <section v-else class="page-panel surface-card">
      <EmptyStateBlock :title="loadError || '未找到订单'" :description="loadError ? '请检查网络与登录身份，或返回列表重试。' : '当前订单不存在或无权限查看。'" />
    </section>
  </div>
</template>

<style scoped>
.stats-grid--detail { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.detail-grid { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr); gap: 20px; }
.amount-banner { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }
.amount-banner__item { padding: 18px; border-radius: 18px; background: #f7fafc; border: 1px solid rgba(15, 23, 42, 0.06); }
.amount-banner__item span { display: block; margin-bottom: 10px; color: var(--color-text-2); }
.amount-banner__item strong { font-size: 24px; }
.amount-banner__item--highlight { background: linear-gradient(135deg, rgba(47, 116, 255, 0.12), rgba(73, 187, 174, 0.14)); }
.fee-card { margin-top: 18px; }
.timeline-card { padding: 12px 14px; border-radius: 14px; background: #f8fafc; border: 1px solid rgba(15, 23, 42, 0.06); }
.timeline-card p { margin: 8px 0 0; color: var(--color-text-2); line-height: 1.6; }
@media (max-width: 1280px) { .stats-grid--detail { grid-template-columns: repeat(2, minmax(0, 1fr)); } .detail-grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .stats-grid--detail, .amount-banner { grid-template-columns: 1fr; } }
</style>
