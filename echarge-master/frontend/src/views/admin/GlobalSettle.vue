<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CircleCheck,
  Clock,
  DataAnalysis,
  Money,
  RefreshRight,
  View,
  WarningFilled,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import { fetchDemoFlowHealth } from '../../api/demo'
import http, { httpMutation } from '../../api/http'
import { mockSettlementRows } from '../../mock/backoffice'

const loading = ref(false)
const executing = ref(false)
const settleDate = ref('')
const batchRows = ref([])
const operatorRowsByDate = ref({})
const lastExecution = ref(null)
const logItems = ref([])

const detailVisible = ref(false)
const detailDate = ref('')
const detailRows = ref([])

const stats = reactive({
  pendingOrderCount: 0,
  pendingAmount: 0,
  settledAmount: 0,
  platformFee: 0,
})

const fallbackOperatorBlueprints = [
  { operator_id: 1, operator_name: '深能星充', base_order_count: 186, base_total_amount: 26890.34, platform_rate: 10, status_code: 1, can_payout: true, hold_reason: '' },
  { operator_id: 2, operator_name: '湾区智联', base_order_count: 142, base_total_amount: 20360.52, platform_rate: 10, status_code: 0, can_payout: true, hold_reason: '' },
  { operator_id: 3, operator_name: '城运快充', base_order_count: 118, base_total_amount: 16842.18, platform_rate: 10, status_code: 2, can_payout: false, hold_reason: '结算账户待补充开户证明' },
]

const formatMoney = (value) => {
  const num = Number(value || 0)
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getDateText = (offset = 0) => {
  const target = new Date()
  target.setDate(target.getDate() - offset)
  return target.toISOString().slice(0, 10)
}

const appendLog = (message, type = 'info') => {
  const now = new Date()
  const time = now.toTimeString().slice(0, 8)
  logItems.value.unshift({ time, message, type })
  if (logItems.value.length > 80) {
    logItems.value = logItems.value.slice(0, 80)
  }
}

const normalizeOperatorRow = (row) => {
  if (!row) return null
  let statusCode = row.status_code
  if (typeof row.status === 'number') statusCode = row.status
  if (typeof row.status === 'string') {
    if (row.status === 'pending') statusCode = 0
    if (row.status === 'hold') statusCode = 2
    if (row.status === 'skipped') statusCode = -1
  }
  return {
    id: row.id ?? null,
    settle_date: row.settle_date,
    operator_id: row.operator_id ?? null,
    operator_name: row.operator_name || `运营商 #${row.operator_id ?? '--'}`,
    order_count: Number(row.order_count || 0),
    total_amount: Number(row.total_amount || 0),
    platform_fee: Number(row.platform_fee || 0),
    settle_amount: Number(row.settle_amount || 0),
    platform_rate: row.platform_rate == null ? null : Number(row.platform_rate),
    status_code: statusCode,
    can_payout: row.can_payout,
    hold_reason: row.hold_reason || '',
  }
}

const groupOperatorRowsByDate = (rows = []) =>
  rows.reduce((result, item) => {
    const normalized = normalizeOperatorRow(item)
    if (!normalized) return result
    if (!result[normalized.settle_date]) result[normalized.settle_date] = []
    result[normalized.settle_date].push(normalized)
    return result
  }, {})

const buildBatchRows = (groupedRows = {}) =>
  Object.entries(groupedRows)
    .map(([settleDate, rows]) => {
      const readyCount = rows.filter((item) => item.can_payout === true).length
      const holdCount = rows.filter((item) => item.can_payout === false).length
      const status = holdCount ? 2 : rows.every((item) => item.status_code === 1) ? 1 : 0
      return {
        settle_date: settleDate,
        order_count: rows.reduce((sum, item) => sum + Number(item.order_count || 0), 0),
        total_amount: Number(rows.reduce((sum, item) => sum + Number(item.total_amount || 0), 0).toFixed(2)),
        platform_fee: Number(rows.reduce((sum, item) => sum + Number(item.platform_fee || 0), 0).toFixed(2)),
        settle_amount: Number(rows.reduce((sum, item) => sum + Number(item.settle_amount || 0), 0).toFixed(2)),
        operator_count: rows.length,
        ready_count: readyCount,
        hold_count: holdCount,
        status,
        status_text: status === 1 ? '已完成' : status === 2 ? '已挂起' : '处理中',
      }
    })
    .sort((left, right) => String(right.settle_date).localeCompare(String(left.settle_date)))

const applySettlementSnapshot = (operatorRows = []) => {
  const grouped = groupOperatorRowsByDate(operatorRows)
  operatorRowsByDate.value = grouped
  batchRows.value = buildBatchRows(grouped)

  const pendingRows = operatorRows.filter((item) => item.status_code !== 1)
  stats.pendingAmount = Number(pendingRows.reduce((sum, item) => sum + Number(item.settle_amount || 0), 0).toFixed(2))
  stats.settledAmount = Number(
    operatorRows.filter((item) => item.status_code === 1).reduce((sum, item) => sum + Number(item.settle_amount || 0), 0).toFixed(2),
  )
  stats.platformFee = Number(operatorRows.reduce((sum, item) => sum + Number(item.platform_fee || 0), 0).toFixed(2))
}

const buildFallbackOperatorRows = () => {
  const importedRows = (Array.isArray(mockSettlementRows) ? mockSettlementRows : []).map((row) => normalizeOperatorRow({ ...row, status_code: row.status_code ?? row.status }))
  const generatedRows = [1, 2, 3].flatMap((offset) => {
    const targetSettleDate = getDateText(offset)
    return fallbackOperatorBlueprints.map((blueprint, index) => {
      const totalAmount = Number((blueprint.base_total_amount - offset * 620 + index * 360).toFixed(2))
      const platformFee = Number((totalAmount * (Number(blueprint.platform_rate || 10) / 100)).toFixed(2))
      return normalizeOperatorRow({
        id: `${targetSettleDate}-${blueprint.operator_id}`,
        settle_date: targetSettleDate,
        operator_id: blueprint.operator_id,
        operator_name: blueprint.operator_name,
        order_count: Math.max(42, blueprint.base_order_count - offset * 11 + index * 4),
        total_amount: totalAmount,
        platform_fee: platformFee,
        settle_amount: Number((totalAmount - platformFee).toFixed(2)),
        platform_rate: blueprint.platform_rate,
        status_code: blueprint.status_code,
        can_payout: blueprint.can_payout,
        hold_reason: blueprint.hold_reason,
      })
    })
  })
  const mergedMap = new Map()
  ;[...importedRows, ...generatedRows].forEach((row) => {
    if (!row) return
    mergedMap.set(`${row.settle_date}-${row.operator_id}`, row)
  })
  return Array.from(mergedMap.values()).sort((left, right) => {
    if (left.settle_date === right.settle_date) return String(left.operator_name).localeCompare(String(right.operator_name))
    return String(right.settle_date).localeCompare(String(left.settle_date))
  })
}

const applyFallbackData = () => {
  const fallbackRows = buildFallbackOperatorRows()
  applySettlementSnapshot(fallbackRows)
  stats.pendingOrderCount = fallbackRows.reduce((sum, item) => sum + Number(item.order_count || 0), 0)
  appendLog('清分中心已切换为演示批次数据', 'warning')
}

const batchStatusType = (row) => {
  if (row.status === 1) return 'success'
  if (row.status === 2) return 'danger'
  return 'warning'
}

const batchStatusText = (row) => row.status_text || (row.status === 1 ? '已完成' : row.status === 2 ? '已挂起' : '处理中')
const operatorPayoutType = (row) => (row.status_code === 1 ? 'success' : row.status_code === 2 ? 'danger' : row.status_code === -1 ? 'info' : 'warning')
const operatorPayoutText = (row) => (row.status_code === 1 ? '已打款' : row.status_code === 2 ? '挂起待补资料' : row.status_code === -1 ? '已存在批次' : '待打款')
const operatorQualificationType = (row) => (row.can_payout === true ? 'success' : row.can_payout === false ? 'warning' : 'info')
const operatorQualificationText = (row) => (row.can_payout === true ? '资格通过' : row.can_payout === false ? '待补资料' : '未判定')

const executionRows = computed(() => {
  const list = lastExecution.value?.data?.operator_results || []
  return list.map((item) => normalizeOperatorRow(item)).filter(Boolean)
})

const overviewCards = computed(() => [
  {
    label: '待清分订单数',
    value: stats.pendingOrderCount,
    suffix: ' 单',
    trend: 'T+1 目标批次',
    trendLabel: '仅统计已支付且未清分订单',
    tone: 'warning',
    icon: Clock,
  },
  {
    label: '待清分金额',
    value: formatMoney(stats.pendingAmount),
    prefix: '¥',
    trend: '待执行资金池',
    trendLabel: '计划在下一批次清分完成',
    tone: 'primary',
    icon: WarningFilled,
  },
  {
    label: '已清分金额',
    value: formatMoney(stats.settledAmount),
    prefix: '¥',
    trend: '累计已确认',
    trendLabel: '仅统计已结算订单',
    tone: 'success',
    icon: CircleCheck,
  },
  {
    label: '平台累计抽成',
    value: formatMoney(stats.platformFee),
    prefix: '¥',
    trend: '平台服务费汇总',
    trendLabel: '按运营商清分记录聚合',
    tone: 'info',
    icon: Money,
  },
])

const historySummary = computed(() => ({
  totalBatch: batchRows.value.length,
  totalOperator: batchRows.value.reduce((sum, row) => sum + Number(row.operator_count || 0), 0),
  holdTotal: batchRows.value.reduce((sum, row) => sum + Number(row.hold_count || 0), 0),
}))

const executionProgress = computed(() => {
  const rows = executionRows.value
  if (!rows.length) return { qualified: 0, payoutReady: 0 }
  const qualifiedCount = rows.filter((item) => item.can_payout === true).length
  const payoutReadyCount = rows.filter((item) => item.status_code === 0 || item.status_code === 1).length
  return {
    qualified: Math.round((qualifiedCount / rows.length) * 100),
    payoutReady: Math.round((payoutReadyCount / rows.length) * 100),
  }
})

const fetchAllData = async () => {
  loading.value = true
  try {
    const settlementResp = await http.get('/admin/finance/settlements')
    if (settlementResp?.data?.code !== 200) {
      throw new Error(settlementResp?.data?.message || '清分数据加载失败')
    }
    const operatorRows = Array.isArray(settlementResp?.data?.operator_records)
      ? settlementResp.data.operator_records.map((item) => normalizeOperatorRow(item)).filter(Boolean)
      : []
    if (operatorRows.length) {
      applySettlementSnapshot(operatorRows)
      try {
        const healthResp = await fetchDemoFlowHealth()
        if (healthResp?.data?.code === 200) {
          const health = healthResp?.data?.data || {}
          stats.pendingOrderCount = Number(health.unsettled_order_count || 0)
        }
      } catch {
        stats.pendingOrderCount = 0
      }
    } else {
      applyFallbackData()
    }
  } catch (error) {
    applyFallbackData()
    ElMessage.warning(error?.message || '清分接口不可用，已展示演示批次')
  } finally {
    loading.value = false
  }
}

const openDetail = (row) => {
  detailDate.value = row.settle_date
  detailRows.value = operatorRowsByDate.value[row.settle_date] || []
  detailVisible.value = true
}

const executeSettlement = async () => {
  if (!settleDate.value) {
    ElMessage.warning('请选择清分日期')
    return
  }

  await ElMessageBox.confirm(
    `确认对 ${settleDate.value} 执行平台清分？系统将按运营商分组生成批次并更新订单结算状态。`,
    '清分执行确认',
    { type: 'warning', confirmButtonText: '确认执行', cancelButtonText: '取消' },
  )

  executing.value = true
  appendLog(`开始执行 ${settleDate.value} 清分任务`)
  appendLog('正在拉取目标日期订单并进行运营商分组')

  try {
    const resp = await httpMutation.post('/admin/finance/settle', { date: settleDate.value })
    const payload = resp?.data || {}
    if (payload.code !== 200) {
      appendLog(`执行失败：${payload.message || '未知错误'}`, 'error')
      ElMessage.error(payload.message || '清分执行失败')
      return
    }

    lastExecution.value = {
      message: payload.message,
      processed: payload?.data?.processed_order_count || 0,
      operator_count: payload?.data?.processed_operator_count || 0,
      skipped_operator_count: payload?.data?.skipped_operator_count || 0,
      data: payload.data || {},
    }
    appendLog(payload.message || '清分执行完成', 'success')
    appendLog(`本次处理订单 ${lastExecution.value.processed || 0} 笔，覆盖运营商 ${lastExecution.value.operator_count || 0} 个`, 'success')
    if (lastExecution.value.skipped_operator_count) {
      appendLog(`已跳过 ${lastExecution.value.skipped_operator_count} 个已存在批次的运营商`, 'warning')
    }

    ElMessage.success(payload.message || '清分执行成功')
    await fetchAllData()
  } catch (error) {
    appendLog(`执行失败：${error?.message || '清分执行失败'}`, 'error')
    ElMessage.error(error?.message || '清分执行失败')
  } finally {
    executing.value = false
  }
}

onMounted(() => {
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  settleDate.value = yesterday.toISOString().slice(0, 10)
  appendLog('平台清分中心已就绪，等待执行指令')
  fetchAllData()
})
</script>

<template>
  <div class="page-shell global-settle-page">
    <PageSectionHeader
      eyebrow="Settlement Center"
      title="平台清分中心"
      description="支持按日执行 T+1 清分、按运营商分组核算，并区分资格状态与打款状态。"
      chip="管理员财务视角"
    >
      <template #actions>
        <el-button :icon="DataAnalysis" :loading="loading" @click="fetchAllData">刷新数据</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--settle">
      <MetricCard v-for="item in overviewCards" :key="item.label" v-bind="item" />
    </section>

    <section class="panel-grid panel-grid--wide">
      <article class="page-panel surface-card" v-loading="loading">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">手动清分执行台</h3>
            <p class="panel-heading__desc">按清分归属日执行批次，系统将自动分运营商生成清分结果。</p>
          </div>
        </div>

        <div class="execute-toolbar">
          <div class="execute-toolbar__left">
            <span class="label">清分日期</span>
            <el-date-picker
              v-model="settleDate"
              type="date"
              value-format="YYYY-MM-DD"
              format="YYYY-MM-DD"
              :clearable="false"
              style="width: 180px"
            />
            <el-button type="primary" :icon="RefreshRight" :loading="executing" @click="executeSettlement">
              执行清分
            </el-button>
          </div>
          <div class="execute-toolbar__summary">
            <span>历史批次 {{ historySummary.totalBatch }}</span>
            <span>覆盖运营商 {{ historySummary.totalOperator }}</span>
            <span>挂起记录 {{ historySummary.holdTotal }}</span>
          </div>
        </div>

        <div class="result-wrap" v-if="lastExecution">
          <div class="result-head">
            <strong>最近一次执行结果</strong>
            <span>{{ lastExecution.message }}</span>
          </div>
          <div class="result-grid">
            <div class="result-item">
              <span>处理订单</span>
              <strong>{{ lastExecution.processed || 0 }}</strong>
            </div>
            <div class="result-item">
              <span>覆盖运营商</span>
              <strong>{{ lastExecution.operator_count || 0 }}</strong>
            </div>
            <div class="result-item">
              <span>跳过批次</span>
              <strong>{{ lastExecution.skipped_operator_count || 0 }}</strong>
            </div>
          </div>

          <div class="progress-grid" v-if="executionRows.length">
            <div class="progress-card">
              <div class="progress-card__head">
                <strong>运营商资格通过率</strong>
                <span>{{ executionProgress.qualified }}%</span>
              </div>
              <el-progress :percentage="executionProgress.qualified" :show-text="false" :stroke-width="10" />
            </div>
            <div class="progress-card">
              <div class="progress-card__head">
                <strong>可打款状态占比</strong>
                <span>{{ executionProgress.payoutReady }}%</span>
              </div>
              <el-progress :percentage="executionProgress.payoutReady" :show-text="false" :stroke-width="10" color="#22a06b" />
            </div>
          </div>

          <el-table :data="executionRows" stripe size="small" class="execution-table">
            <el-table-column prop="operator_name" label="运营商" min-width="130" />
            <el-table-column prop="order_count" label="订单数" width="90" align="center" />
            <el-table-column prop="total_amount" label="订单总额" width="120" align="right">
              <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
            </el-table-column>
            <el-table-column label="资格状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="operatorQualificationType(row)" effect="dark" size="small">{{ operatorQualificationText(row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="打款状态" width="130" align="center">
              <template #default="{ row }">
                <el-tag :type="operatorPayoutType(row)" size="small">{{ operatorPayoutText(row) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </article>

      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">执行日志</h3>
            <p class="panel-heading__desc">按时间倒序记录清分链路状态，便于回溯异常原因。</p>
          </div>
        </div>

        <div class="log-panel">
          <div v-for="(log, idx) in logItems" :key="idx" class="log-item">
            <span class="log-time">[{{ log.time }}]</span>
            <span :class="['log-text', `log-text--${log.type}`]">{{ log.message }}</span>
          </div>
        </div>
      </article>
    </section>

    <section class="page-panel surface-card table-shell" v-loading="loading">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">历史清分批次</h3>
          <p class="panel-heading__desc">支持查看批次状态、资格通过情况与各运营商清分明细。</p>
        </div>
      </div>

      <el-table v-if="batchRows.length" :data="batchRows" stripe border>
        <el-table-column prop="settle_date" label="清分归属日期" min-width="130" />
        <el-table-column prop="order_count" label="订单数" width="90" align="center" />
        <el-table-column prop="operator_count" label="运营商数" width="95" align="center" />
        <el-table-column prop="ready_count" label="资格通过" width="95" align="center" />
        <el-table-column prop="hold_count" label="待补资料" width="95" align="center" />
        <el-table-column prop="total_amount" label="订单总额" min-width="140" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column prop="platform_fee" label="平台抽成" min-width="130" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.platform_fee) }}</template>
        </el-table-column>
        <el-table-column prop="settle_amount" label="应下发金额" min-width="130" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.settle_amount) }}</template>
        </el-table-column>
        <el-table-column label="批次状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="batchStatusType(row)" effect="dark">{{ batchStatusText(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" :icon="View" @click="openDetail(row)">运营商明细</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无历史批次" description="执行首批清分后，这里会展示按日批次记录。" />
    </section>

    <el-drawer v-model="detailVisible" size="58%" :title="`运营商清分明细 · ${detailDate || '-'}`" destroy-on-close>
      <el-alert
        type="info"
        :closable="false"
        class="mb-4"
        title="明细展示运营商资格状态、批次状态与打款状态，便于财务复核。"
      />

      <el-table :data="detailRows" stripe border>
        <el-table-column prop="operator_name" label="运营商" min-width="140" />
        <el-table-column prop="order_count" label="订单数" width="90" align="center" />
        <el-table-column prop="total_amount" label="订单总额" width="130" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column prop="platform_fee" label="平台抽成" width="120" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.platform_fee) }}</template>
        </el-table-column>
        <el-table-column prop="settle_amount" label="应结算金额" width="130" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.settle_amount) }}</template>
        </el-table-column>
        <el-table-column label="运营商资格状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="operatorQualificationType(row)" effect="dark" size="small">{{ operatorQualificationText(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="打款状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="operatorPayoutType(row)" size="small">{{ operatorPayoutText(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资格备注" min-width="180">
          <template #default="{ row }">
            <span v-if="row.hold_reason" class="text-warning">{{ row.hold_reason }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<style scoped>
.global-settle-page {
  padding-bottom: 10px;
}

.stats-grid--settle {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.execute-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.execute-toolbar__left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.label {
  color: var(--color-text-3);
  font-size: 13px;
}

.execute-toolbar__summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-2);
}

.result-wrap {
  margin-top: 12px;
  border-radius: 16px;
  border: 1px solid rgba(47, 116, 255, 0.16);
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.84), rgba(245, 250, 255, 0.9));
  padding: 16px;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.result-head strong {
  color: var(--color-text);
}

.result-head span {
  color: var(--color-primary-strong);
  font-size: 13px;
}

.result-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.result-item {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.8);
}

.result-item span {
  color: var(--color-text-3);
  font-size: 12px;
}

.result-item strong {
  display: block;
  margin-top: 8px;
  color: var(--color-text);
  font-size: 24px;
}

.progress-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.progress-card {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.8);
}

.progress-card__head {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.progress-card__head strong {
  color: var(--color-text);
  font-size: 13px;
}

.progress-card__head span {
  color: var(--color-primary-strong);
  font-weight: 600;
}

.execution-table {
  margin-top: 14px;
}

.log-panel {
  height: 460px;
  overflow: auto;
  border-radius: 14px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(12, 24, 48, 0.97), rgba(7, 19, 41, 0.95));
  border: 1px solid rgba(64, 158, 255, 0.28);
}

.log-item {
  font-family: var(--font-family-mono);
  font-size: 12px;
  line-height: 1.8;
  color: #dbeafe;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.25);
  padding: 2px 0;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #93c5fd;
  margin-right: 8px;
}

.log-text--success {
  color: #34d399;
}

.log-text--warning {
  color: #fbbf24;
}

.log-text--error {
  color: #f87171;
}

.text-warning {
  color: #e6a23c;
}

.text-muted {
  color: #909399;
}

.mb-4 {
  margin-bottom: 16px;
}

@media (max-width: 1280px) {
  .stats-grid--settle {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .result-grid,
  .progress-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid--settle {
    grid-template-columns: 1fr;
  }

  .execute-toolbar {
    align-items: flex-start;
  }
}
</style>
