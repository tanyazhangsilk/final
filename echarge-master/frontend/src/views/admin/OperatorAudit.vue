<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Calendar, CircleCheck, CloseBold, OfficeBuilding } from '@element-plus/icons-vue'

import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import OperatorAuditDetailDrawer from '../../components/admin/OperatorAuditDetailDrawer.vue'
import OperatorAuditDialog from '../../components/admin/OperatorAuditDialog.vue'
import { fetchOperatorAuditApplications, processOperatorAuditApplication } from '../../api/admin'
import {
  createAuditSummary,
  formatOperatorAuditStatus,
  getAuditStatusTagType,
  type OperatorAuditRecord,
  type OperatorAuditStatus,
} from '../../utils/operatorAudit'

type ReviewStatus = Extract<OperatorAuditStatus, 'approved' | 'rejected'>

const loading = ref(false)
const drawerVisible = ref(false)
const dialogVisible = ref(false)
const records = ref<OperatorAuditRecord[]>([])
const currentRecord = ref<OperatorAuditRecord | null>(null)
const reviewTarget = ref<OperatorAuditRecord | null>(null)

const filters = reactive({
  keyword: '',
  contactName: '',
  status: '' as '' | OperatorAuditStatus,
  submittedRange: [] as string[],
})

const tableStats = computed(() => {
  const total = records.value.length
  const pending = records.value.filter((item) => item.status === 'pending').length
  const approved = records.value.filter((item) => item.status === 'approved').length
  const rejected = records.value.filter((item) => item.status === 'rejected').length

  return [
    { label: '申请总数', value: total, hint: '当前平台运营商入驻申请总量', tone: 'primary', icon: OfficeBuilding },
    { label: '待审核数量', value: pending, hint: '等待管理员处理', tone: 'warning', icon: Calendar },
    { label: '已通过数量', value: approved, hint: '已进入后续接入与配置阶段', tone: 'success', icon: CircleCheck },
    { label: '已驳回数量', value: rejected, hint: '需补充材料后重新提交', tone: 'danger', icon: CloseBold },
  ]
})

const statusDistribution = computed(() =>
  [
    { key: 'pending', label: '待审核', value: records.value.filter((item) => item.status === 'pending').length, tone: 'warning' },
    { key: 'approved', label: '已通过', value: records.value.filter((item) => item.status === 'approved').length, tone: 'success' },
    { key: 'rejected', label: '已驳回', value: records.value.filter((item) => item.status === 'rejected').length, tone: 'danger' },
  ].filter((item) => item.value > 0),
)

const pendingFocusList = computed(() =>
  records.value
    .filter((item) => item.status === 'pending')
    .slice(0, 4)
    .map((item) => ({
      id: item.id,
      operatorName: item.operatorName,
      meta: `${item.region} · ${item.stationCount} 座站 / ${item.chargerCount} 个枪口`,
      submittedAt: item.submittedAt,
      attachmentSummary: createAuditSummary(item.attachments),
    })),
)

const filteredRecords = computed(() => {
  const [rangeStart, rangeEnd] = filters.submittedRange

  return records.value.filter((item) => {
    const keyword = filters.keyword.trim().toLowerCase()
    const contactName = filters.contactName.trim().toLowerCase()
    const submittedAtDate = new Date(item.submittedAt).getTime()
    const startTime = rangeStart ? new Date(rangeStart).getTime() : null
    const endTime = rangeEnd ? new Date(rangeEnd).getTime() + 24 * 60 * 60 * 1000 - 1 : null

    const matchKeyword =
      !keyword ||
      [item.applicationNo, item.operatorName, item.companyName, item.creditCode, item.region].some((field) =>
        String(field).toLowerCase().includes(keyword),
      )

    const matchContact =
      !contactName ||
      [item.contactName, item.phone, item.email].some((field) =>
        String(field).toLowerCase().includes(contactName),
      )

    const matchStatus = !filters.status || item.status === filters.status
    const matchDate = (!startTime || submittedAtDate >= startTime) && (!endTime || submittedAtDate <= endTime)

    return matchKeyword && matchContact && matchStatus && matchDate
  })
})

const latestUpdatedAt = computed(() => {
  if (!records.value.length) return '--'
  return records.value
    .map((item) => item.reviewedAt || item.submittedAt)
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0]
})

const pipelineProgress = computed(() => {
  const total = records.value.length || 1
  const pending = records.value.filter((item) => item.status === 'pending').length
  const approved = records.value.filter((item) => item.status === 'approved').length
  return {
    intake: 100,
    review: Math.round(((total - pending) / total) * 100),
    pass: Math.round((approved / total) * 100),
  }
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await fetchOperatorAuditApplications()
    const payload = res?.data
    if (payload?.code !== 200) {
      throw new Error(payload?.message || '运营商审核列表加载失败')
    }
    records.value = payload?.data?.records || []
  } catch (error) {
    console.error(error)
    ElMessage.error(error instanceof Error ? error.message : '运营商审核页面加载失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.keyword = ''
  filters.contactName = ''
  filters.status = ''
  filters.submittedRange = []
}

const handleSearch = () => {
  ElMessage.success(`已按条件筛选，共匹配 ${filteredRecords.value.length} 条申请记录`)
}

const openDetail = (record: OperatorAuditRecord) => {
  currentRecord.value = record
  drawerVisible.value = true
}

const openReviewDialog = (record: OperatorAuditRecord) => {
  reviewTarget.value = record
  dialogVisible.value = true
}

const syncCurrentRecord = (targetId: string) => {
  if (currentRecord.value?.id === targetId) {
    currentRecord.value = records.value.find((item) => item.id === targetId) || null
  }
}

const handleReviewSubmit = async (payload: { status: ReviewStatus; comment: string }) => {
  const target = reviewTarget.value
  if (!target) return

  const record = records.value.find((item) => item.id === target.id)
  if (!record) return

  const applicationId = Number(record.id)
  if (!Number.isFinite(applicationId)) {
    ElMessage.error('无效的申请 ID')
    return
  }

  try {
    const res = await processOperatorAuditApplication(applicationId, {
      action: payload.status === 'approved' ? 'approve' : 'reject',
      remark: payload.comment || '',
    })
    const body = res?.data
    if (body?.code !== 200) {
      throw new Error(body?.message || '审核提交失败')
    }
    dialogVisible.value = false
    ElMessage.success(`${record.operatorName} 已${payload.status === 'approved' ? '审核通过' : '驳回'}，已写入数据库`)
    await loadData()
    syncCurrentRecord(record.id)
  } catch (error) {
    console.error(error)
    ElMessage.error(error instanceof Error ? error.message : '审核提交失败')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page-shell operator-audit-page">
    <PageSectionHeader
      eyebrow="Operator Admission Review"
      title="运营商入驻审核"
      description="用于审核申请入驻平台的充电运营商资质信息与材料完整性。"
      chip="管理员核心业务页"
    >
      <template #actions>
        <span class="header-meta">最近处理时间：{{ latestUpdatedAt }}</span>
        <el-button @click="resetFilters">重置筛选</el-button>
        <el-button type="primary" @click="loadData">刷新数据</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid">
      <MetricCard
        v-for="item in tableStats"
        :key="item.label"
        :label="item.label"
        :value="item.value"
        :hint="item.hint"
        :tone="item.tone"
        :icon="item.icon"
      />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选与检索</h3>
          <p class="panel-heading__desc">支持按运营商、联系人、审核状态和提交时间范围进行筛选。</p>
        </div>
      </div>

      <div class="filter-panel">
        <div class="filter-grid operator-audit-filter-grid">
          <el-input v-model="filters.keyword" clearable placeholder="运营商名称 / 企业全称 / 申请编号" />
          <el-input v-model="filters.contactName" clearable placeholder="联系人 / 电话 / 邮箱" />
          <el-select v-model="filters.status" clearable placeholder="申请状态">
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
          <el-date-picker
            v-model="filters.submittedRange"
            type="daterange"
            range-separator="至"
            start-placeholder="提交开始日期"
            end-placeholder="提交结束日期"
            value-format="YYYY-MM-DD"
            unlink-panels
          />
        </div>

        <div class="toolbar-row toolbar-row--actions">
          <div class="toolbar-summary">
            <span>当前匹配记录</span>
            <strong>{{ filteredRecords.length }}</strong>
            <span>条</span>
          </div>
          <div class="toolbar-group">
            <el-button @click="resetFilters">重置</el-button>
            <el-button type="primary" @click="handleSearch">查询</el-button>
          </div>
        </div>
      </div>
    </section>

    <section class="audit-content-grid">
      <article class="page-panel surface-card table-shell">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">申请列表</h3>
            <p class="panel-heading__desc">集中展示运营商申请基础信息、审核状态与最近处理记录。</p>
          </div>
        </div>

        <el-table v-loading="loading" :data="filteredRecords" height="100%">
          <el-table-column prop="applicationNo" label="申请编号" min-width="176" />
          <el-table-column prop="operatorName" label="运营商名称" min-width="220" show-overflow-tooltip />
          <el-table-column prop="contactName" label="联系人" width="100" />
          <el-table-column prop="phone" label="联系电话" width="138" />
          <el-table-column prop="region" label="所在地区" min-width="138" />
          <el-table-column prop="submittedAt" label="申请时间" width="168" />
          <el-table-column label="审核状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="getAuditStatusTagType(row.status)" effect="light" round>
                {{ formatOperatorAuditStatus(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="lastProcessedBy" label="最近处理人" width="150" show-overflow-tooltip />
          <el-table-column prop="lastProcessedAt" label="最近处理时间" width="168" />
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
                <el-button link :type="row.status === 'pending' ? 'success' : 'info'" @click="openReviewDialog(row)">
                  {{ row.status === 'pending' ? '审核' : '重新审核' }}
                </el-button>
                <el-dropdown trigger="click">
                  <el-button link type="info">更多</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="openDetail(row)">查看资质材料</el-dropdown-item>
                      <el-dropdown-item @click="openReviewDialog(row)">填写审核意见</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <EmptyStateBlock
          v-if="!loading && filteredRecords.length === 0"
          title="暂无匹配的运营商申请"
          description="可尝试调整筛选条件，或等待新的入驻申请数据接入。"
        />
      </article>

      <article class="page-panel surface-card audit-aside">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">审核流程状态</h3>
            <p class="panel-heading__desc">展示准入流程进度和当前优先待审队列。</p>
          </div>
        </div>

        <div class="pipeline-grid">
          <div class="pipeline-item">
            <div class="pipeline-item__head">
              <span>资料接收完成率</span>
              <strong>{{ pipelineProgress.intake }}%</strong>
            </div>
            <el-progress :percentage="pipelineProgress.intake" :show-text="false" :stroke-width="10" />
          </div>
          <div class="pipeline-item">
            <div class="pipeline-item__head">
              <span>审核流转完成率</span>
              <strong>{{ pipelineProgress.review }}%</strong>
            </div>
            <el-progress :percentage="pipelineProgress.review" :show-text="false" :stroke-width="10" color="#2f74ff" />
          </div>
          <div class="pipeline-item">
            <div class="pipeline-item__head">
              <span>通过转化率</span>
              <strong>{{ pipelineProgress.pass }}%</strong>
            </div>
            <el-progress :percentage="pipelineProgress.pass" :show-text="false" :stroke-width="10" color="#22a06b" />
          </div>
        </div>

        <div class="audit-distribution">
          <div v-for="item in statusDistribution" :key="item.key" class="distribution-item" :class="`distribution-item--${item.tone}`">
            <div class="distribution-item__label">{{ item.label }}</div>
            <div class="distribution-item__value">{{ item.value }}</div>
          </div>
        </div>

        <div class="focus-list">
          <div class="focus-list__head">
            <strong>优先待审</strong>
            <span>{{ pendingFocusList.length }} 条</span>
          </div>

          <div v-if="pendingFocusList.length" class="focus-list__body">
            <button
              v-for="item in pendingFocusList"
              :key="item.id"
              type="button"
              class="focus-item"
              @click="openDetail(records.find((record) => record.id === item.id)!)"
            >
              <div>
                <strong>{{ item.operatorName }}</strong>
                <p>{{ item.meta }}</p>
              </div>
              <div class="focus-item__meta">
                <span>{{ item.submittedAt }}</span>
                <span>{{ item.attachmentSummary }}</span>
              </div>
            </button>
          </div>

          <EmptyStateBlock
            v-else
            title="当前无待审核申请"
            description="当前审核队列已清空，可继续关注新提交记录。"
          />
        </div>
      </article>
    </section>

    <OperatorAuditDetailDrawer v-model="drawerVisible" :record="currentRecord" @review="openReviewDialog" />

    <OperatorAuditDialog v-model="dialogVisible" :record="reviewTarget" @submit="handleReviewSubmit" />
  </div>
</template>

<style scoped>
.operator-audit-page {
  padding-bottom: 12px;
}

.header-meta {
  color: var(--color-text-3);
  font-size: 13px;
}

.operator-audit-top {
  align-items: start;
}

.audit-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
  align-items: start;
}

.audit-aside {
  position: sticky;
  top: 0;
}

.operator-audit-filter-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.toolbar-row--actions {
  margin-top: 16px;
  margin-bottom: 0;
}

.toolbar-summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-2);
}

.toolbar-summary strong {
  color: var(--color-text);
  font-size: 24px;
  line-height: 1;
}

.pipeline-grid {
  display: grid;
  gap: 10px;
}

.pipeline-item {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(243, 246, 251, 0.9));
}

.pipeline-item__head {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.pipeline-item__head span {
  color: var(--color-text-2);
  font-size: 13px;
}

.pipeline-item__head strong {
  color: var(--color-primary-strong);
}

.audit-distribution {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.distribution-item {
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(243, 246, 251, 0.92));
}

.distribution-item__label {
  color: var(--color-text-3);
  font-size: 13px;
}

.distribution-item__value {
  margin-top: 8px;
  color: var(--color-text);
  font-size: 30px;
  font-weight: 700;
}

.distribution-item--warning {
  border-color: rgba(230, 162, 60, 0.22);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6), 0 10px 18px rgba(230, 162, 60, 0.08);
}

.distribution-item--success {
  border-color: rgba(103, 194, 58, 0.2);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6), 0 10px 18px rgba(103, 194, 58, 0.08);
}

.distribution-item--danger {
  border-color: rgba(245, 108, 108, 0.2);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6), 0 10px 18px rgba(245, 108, 108, 0.08);
}

.focus-list {
  margin-top: 18px;
}

.focus-list__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--color-text-2);
  font-size: 13px;
}

.focus-list__body {
  display: grid;
  gap: 10px;
}

.focus-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-3);
  cursor: pointer;
  text-align: left;
  transition: transform var(--motion-fast) ease, border-color var(--motion-fast) ease, box-shadow var(--motion-fast) ease;
}

.focus-item:hover {
  transform: translateY(-2px);
  border-color: rgba(47, 116, 255, 0.2);
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.08);
}

.focus-item strong {
  color: var(--color-text);
}

.focus-item p {
  margin: 8px 0 0;
  color: var(--color-text-2);
  line-height: 1.6;
}

.focus-item__meta {
  display: grid;
  gap: 8px;
  min-width: 128px;
  color: var(--color-text-3);
  font-size: 12px;
  text-align: right;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

@media (max-width: 1280px) {
  .audit-content-grid {
    grid-template-columns: 1fr;
  }

  .operator-audit-filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .audit-distribution {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .operator-audit-filter-grid {
    grid-template-columns: 1fr;
  }

  .focus-item,
  .focus-item__meta {
    text-align: left;
  }

  .focus-item {
    flex-direction: column;
  }
}
</style>
