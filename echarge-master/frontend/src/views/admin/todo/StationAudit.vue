<script setup>
import { computed, onActivated, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, CircleCheck, OfficeBuilding, WarningFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../../components/console/PageSectionHeader.vue'
import MetricCard from '../../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../../components/console/EmptyStateBlock.vue'
import TableSkeletonBlock from '../../../components/console/TableSkeletonBlock.vue'
import { fetchStationAudits, processStationAudit } from '../../../api/admin'
import { stationAuditMock } from '../../../mock/console'
import { buildStationAuditDemoItems, buildStationAuditDemoSummary } from '../../../utils/adminDemoFallback'
import {
  buildRequestCacheKey,
  clearOperatorMainStationsCache,
  clearOperatorStationsOptionsCache,
  clearRequestCache,
  formatCacheLabel,
  getRequestCache,
  setRequestCache,
} from '../../../utils/requestCache'

const CACHE_TTL = 45 * 1000

const loading = ref(false)
const tableReady = ref(false)
const drawerVisible = ref(false)
const currentStation = ref(null)
const auditSubmitting = ref(false)
const stations = ref([])
const total = ref(0)
const cacheLabel = ref('')

const filters = reactive({ keyword: '', status: '' })
const pagination = reactive({ page: 1, pageSize: 10 })
const auditForm = reactive({ remark: '' })
const summary = reactive({ total_count: 0, pending_count: 0, approved_count: 0, rejected_count: 0 })

let searchTimer = null

const statusFilterParam = () => {
  const s = filters.status
  if (s === '' || s === null || s === undefined) return undefined
  const n = Number(s)
  return Number.isFinite(n) ? n : undefined
}

const queryParams = computed(() => ({
  page: pagination.page,
  page_size: pagination.pageSize,
  keyword: filters.keyword.trim() || undefined,
  status: statusFilterParam(),
}))

const listCacheKey = computed(() =>
  buildRequestCacheKey('/admin/audit/stations', queryParams.value, { scope: 'station-audit' }),
)

const stats = computed(() => [
  {
    label: '申请总数',
    value: summary.total_count,
    suffix: ' 座',
    trend: '统一进入审核队列',
    trendLabel: '保持审核节奏稳定',
    tone: 'primary',
    icon: OfficeBuilding,
  },
  {
    label: '待审核',
    value: summary.pending_count,
    suffix: ' 座',
    trend: '待处理申请',
    trendLabel: '优先处理可投运电站',
    tone: 'warning',
    icon: Bell,
  },
  {
    label: '已通过',
    value: summary.approved_count,
    suffix: ' 座',
    trend: '已进入运营配置',
    trendLabel: '可继续配置电桩与模板',
    tone: 'success',
    icon: CircleCheck,
  },
  {
    label: '已驳回',
    value: summary.rejected_count,
    suffix: ' 座',
    trend: '待补充材料',
    trendLabel: '保持原因记录清晰',
    tone: 'danger',
    icon: WarningFilled,
  },
])

const statusTagType = (status) => (Number(status) === 0 ? 'success' : Number(status) === 3 ? 'warning' : Number(status) === 4 ? 'danger' : 'info')

const normalizePayload = (raw) => {
  if (Array.isArray(raw)) {
    return {
      items: raw,
      total: raw.length,
      page: 1,
      page_size: raw.length || pagination.pageSize,
      summary: {
        total_count: raw.length,
        pending_count: raw.filter((r) => Number(r.status) === 3).length,
        approved_count: raw.filter((r) => Number(r.status) === 0).length,
        rejected_count: raw.filter((r) => Number(r.status) === 4).length,
      },
    }
  }
  if (Array.isArray(raw?.items)) {
    return {
      items: raw.items,
      total: raw.total,
      page: raw.page || pagination.page,
      page_size: raw.page_size || pagination.pageSize,
      summary: raw.summary || {},
    }
  }
  return {
    items: [],
    total: 0,
    page: pagination.page,
    page_size: pagination.pageSize,
    summary: {
      total_count: 0,
      pending_count: 0,
      approved_count: 0,
      rejected_count: 0,
    },
  }
}

const applyPayload = (payload = {}, fromCache = false, updatedAt = Date.now()) => {
  stations.value = Array.isArray(payload.items) ? payload.items : []
  total.value = Number(payload.total || stations.value.length)
  pagination.page = Number(payload.page || pagination.page)
  pagination.pageSize = Number(payload.page_size || pagination.pageSize)
  Object.assign(summary, {
    total_count: 0,
    pending_count: 0,
    approved_count: 0,
    rejected_count: 0,
    ...(payload.summary || {}),
  })
  tableReady.value = true
  cacheLabel.value = formatCacheLabel(updatedAt)
}

const loadStations = async ({ background = false, force = false } = {}) => {
  const cached = getRequestCache(listCacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached && !force) {
    applyPayload(cached.value, true, cached.updatedAt)
  }

  loading.value = !cached || !background || force
  try {
    const { data } = await fetchStationAudits(queryParams.value)
    if (data?.code !== 200) {
      throw new Error(data?.message || '审核列表加载失败')
    }
    let payload = normalizePayload(data?.data)
    if (!payload.items.length && Array.isArray(stationAuditMock?.records) && stationAuditMock.records.length) {
      const demoItems = buildStationAuditDemoItems(stationAuditMock.records)
      payload = normalizePayload({
        items: demoItems,
        total: demoItems.length,
        page: 1,
        page_size: demoItems.length || pagination.pageSize,
        summary: buildStationAuditDemoSummary(demoItems),
      })
      ElMessage.info('暂无真实电站审核数据，已展示演示列表（演示行不可提交审核）')
    }
    applyPayload(payload, false, Date.now())
    setRequestCache(listCacheKey.value, payload)
  } catch (error) {
    if (!stations.value.length) {
      if (Array.isArray(stationAuditMock?.records) && stationAuditMock.records.length) {
        const demoItems = buildStationAuditDemoItems(stationAuditMock.records)
        applyPayload(
          normalizePayload({
            items: demoItems,
            total: demoItems.length,
            page: 1,
            page_size: demoItems.length || pagination.pageSize,
            summary: buildStationAuditDemoSummary(demoItems),
          }),
          false,
          Date.now(),
        )
        ElMessage.warning(`${error?.message || '审核列表加载失败'}，已展示演示数据`)
      } else {
        applyPayload(normalizePayload(null), false, Date.now())
        ElMessage.error(error?.message || '审核列表加载失败')
      }
    }
  } finally {
    loading.value = false
  }
}

const openDrawer = (row) => {
  currentStation.value = row
  auditForm.remark = row.audit_remark || ''
  drawerVisible.value = true
}

const handleAudit = async (action) => {
  if (!currentStation.value) return
  if (currentStation.value.is_demo) {
    ElMessage.info('当前为演示数据，请在运营商侧提交真实建站申请后再审核')
    return
  }
  if (action === 'reject' && !auditForm.remark.trim()) {
    ElMessage.warning('驳回时请填写原因')
    return
  }

  auditSubmitting.value = true
  try {
    const { data } = await processStationAudit(currentStation.value.id, {
      action,
      remark: auditForm.remark.trim(),
    })
    if (data?.code !== 200) {
      throw new Error(data?.message || '审核处理失败')
    }
    clearOperatorMainStationsCache()
    clearOperatorStationsOptionsCache()
    clearRequestCache('/admin/audit/stations')
    ElMessage.success(data?.message || '审核处理成功')
  } catch (error) {
    ElMessage.error(error?.message || '审核处理失败')
  } finally {
    auditSubmitting.value = false
    await loadStations({ background: true, force: true })
    currentStation.value = stations.value.find((item) => String(item.id) === String(currentStation.value?.id)) || currentStation.value
    if (currentStation.value && Number(currentStation.value.status) !== 3) {
      drawerVisible.value = false
    }
  }
}

watch(
  () => [filters.keyword, filters.status],
  () => {
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      pagination.page = 1
      loadStations()
    }, 260)
  },
)

onMounted(() => loadStations({ background: true }))
onActivated(() => {
  /** 每次进入审核页拉最新队列（运营商可能刚提交申请） */
  void loadStations({ background: true, force: true })
})
onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <div class="page-shell station-audit-page">
    <PageSectionHeader eyebrow="审核中心" title="电站审核" description="按申请节奏查看电站资料、核验信息并完成审核处理。" chip="站点审核">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :loading="loading" @click="loadStations({ force: true })">刷新列表</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--audit">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">支持按电站、运营主体、联系人与审核状态查询。</p>
        </div>
      </div>

      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索电站 / 运营商 / 联系人 / 地址" style="width: 340px" />
        <el-select v-model="filters.status" clearable placeholder="审核状态" style="width: 160px">
          <el-option label="已审核通过" :value="0" />
          <el-option label="待审核" :value="3" />
          <el-option label="已驳回" :value="4" />
        </el-select>
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">审核列表</h3>
          <p class="panel-heading__desc">共 {{ total }} 条申请，按分页节奏加载与处理。</p>
        </div>
      </div>
      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="7" />

      <el-table v-else-if="stations.length" :data="stations" v-loading="loading" stripe>
        <el-table-column label="电站名称" min-width="220">
          <template #default="{ row }">
            <div class="cell-stack">
              <strong>{{ row.station_name }}</strong>
              <span>{{ row.operator_name || '当前运营商' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="联系人" min-width="160">
          <template #default="{ row }">
            <div class="cell-stack">
              <strong>{{ row.contact_name || '-' }}</strong>
              <span>{{ row.contact_phone || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="full_address" label="地址" min-width="240" />
        <el-table-column label="规划规模" width="160" align="center">
          <template #default="{ row }">{{ row.planned_charger_count }} 枪 / {{ row.total_power_kw }} kW</template>
        </el-table-column>
        <el-table-column label="审核状态" width="120" align="center">
          <template #default="{ row }"><el-tag :type="statusTagType(row.status)">{{ row.status_text }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDrawer(row)">查看详情</el-button>
            <el-button v-if="Number(row.status) === 3" link type="success" @click="openDrawer(row)">审核处理</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无电站审核记录" description="当前筛选条件下没有匹配的电站申请。" />

      <div class="pager">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="(page) => { pagination.page = page; loadStations() }"
          @size-change="(size) => { pagination.page = 1; pagination.pageSize = size; loadStations() }"
        />
      </div>
    </section>

    <el-drawer v-model="drawerVisible" size="900px" :title="currentStation?.station_name || '电站详情'">
      <template v-if="currentStation">
        <div class="station-card">
          <div>
            <strong>{{ currentStation.station_name }}</strong>
            <p>{{ currentStation.operator_name || '当前运营商' }}</p>
          </div>
          <div class="station-card__meta">
            <el-tag :type="statusTagType(currentStation.status)">{{ currentStation.status_text }}</el-tag>
            <el-tag type="info">{{ currentStation.visibility_text || '待确认开放策略' }}</el-tag>
          </div>
        </div>

        <div class="detail-grid">
          <el-descriptions :column="2" border class="detail-card">
            <el-descriptions-item label="详细地址" :span="2">{{ currentStation.full_address }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ currentStation.contact_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="联系电话">{{ currentStation.contact_phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="经纬度">{{ currentStation.longitude }}, {{ currentStation.latitude }}</el-descriptions-item>
            <el-descriptions-item label="营业时间">{{ currentStation.operation_hours || '-' }}</el-descriptions-item>
            <el-descriptions-item label="规划规模">{{ currentStation.planned_charger_count }} 枪 / {{ currentStation.total_power_kw }} kW</el-descriptions-item>
            <el-descriptions-item label="停车位">{{ currentStation.parking_slot_count || '-' }}</el-descriptions-item>
            <el-descriptions-item label="服务半径">{{ currentStation.service_radius_km ? `${currentStation.service_radius_km} km` : '-' }}</el-descriptions-item>
            <el-descriptions-item label="场地方">{{ currentStation.site_owner || '-' }}</el-descriptions-item>
            <el-descriptions-item label="建设阶段">{{ currentStation.construction_phase || '-' }}</el-descriptions-item>
            <el-descriptions-item label="供电说明" :span="2">{{ currentStation.grid_capacity_remark || '-' }}</el-descriptions-item>
            <el-descriptions-item label="停车收费说明" :span="2">{{ currentStation.parking_fee_desc || '-' }}</el-descriptions-item>
            <el-descriptions-item label="适配车辆" :span="2">{{ (currentStation.support_vehicle_types || []).join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="配套设施" :span="2">{{ (currentStation.facility_tags || []).join('、') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="安全联系人">{{ currentStation.safety_contact_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="安全联系电话">{{ currentStation.safety_contact_phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="资质补充说明" :span="2">{{ currentStation.qualification_remark || '-' }}</el-descriptions-item>
            <el-descriptions-item label="站点说明" :span="2">{{ currentStation.station_remark || '-' }}</el-descriptions-item>
            <el-descriptions-item label="审核备注" :span="2">{{ currentStation.audit_remark || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="info-list">
            <div class="info-item">
              <p class="info-item__title">封面信息</p>
              <p class="info-item__desc">{{ currentStation.cover_image || '已登记站点封面说明，可在正式材料中补充。' }}</p>
            </div>
            <div class="info-item">
              <p class="info-item__title">现场图片</p>
              <p class="info-item__desc">{{ currentStation.site_photos?.length ? currentStation.site_photos.join('；') : '已预留现场图片资料位。' }}</p>
            </div>
          </div>
        </div>

        <div class="audit-box" v-if="Number(currentStation.status) === 3">
          <h4>审核意见</h4>
          <el-input v-model="auditForm.remark" type="textarea" :rows="4" placeholder="通过时可补充说明，驳回时请填写明确原因" />
          <div class="drawer-actions">
            <el-button type="danger" plain :loading="auditSubmitting" @click="handleAudit('reject')">驳回申请</el-button>
            <el-button type="primary" :loading="auditSubmitting" @click="handleAudit('approve')">审核通过</el-button>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.stats-grid--audit {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.cell-stack {
  display: grid;
  gap: 4px;
}

.cell-stack span,
.station-card p {
  color: var(--color-text-2);
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.station-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  margin-bottom: 18px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(47, 116, 255, 0.08), rgba(73, 187, 174, 0.12));
}

.station-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(240px, 0.8fr);
  gap: 16px;
}

.detail-card,
.audit-box {
  margin-bottom: 16px;
}

.audit-box h4 {
  margin: 0 0 12px;
  font-size: 16px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 1280px) {
  .stats-grid--audit {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid--audit {
    grid-template-columns: 1fr;
  }

  .station-card {
    flex-direction: column;
  }
}
</style>


