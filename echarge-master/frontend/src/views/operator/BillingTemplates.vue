<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Edit, Location, Plus, RefreshRight } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import { bindStationTemplate, createBillingTemplate, fetchOperatorPricingTemplates, fetchOperatorStationOptions, updateBillingTemplate } from '../../api/operator'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const rows = ref([])
const stationRows = ref([])
const cacheLabel = ref('')

const dialogVisible = ref(false)
const stationDialogVisible = ref(false)
const editingId = ref(null)
const applyingTemplate = ref(null)
const selectedStations = ref([])

const form = reactive({
  name: '',
  peak_price: 1.88,
  flat_price: 1.32,
  valley_price: 0.68,
  service_price: 0.8,
  scope: 'station',
  status: 'active',
  description: '',
})

const cacheKey = buildRequestCacheKey('/operator/billing/templates', { scope: 'billing-templates' })
const stationOptions = computed(() => stationRows.value.filter((item) => Number(item.status) === 0))

const stats = computed(() => [
  { label: '模板总数', value: rows.value.length, suffix: ' 个', tone: 'primary', icon: Document, trend: '计费模板沉淀', trendLabel: '支持站点复用' },
  { label: '启用模板', value: rows.value.filter((item) => item.status === 'active').length, suffix: ' 个', tone: 'success', icon: RefreshRight, trend: '当前可投产', trendLabel: '可直接下发到站点' },
  { label: '指定站点模板', value: rows.value.filter((item) => item.scope === 'station').length, suffix: ' 个', tone: 'warning', icon: Location, trend: '按站点差异化计费', trendLabel: '适配不同场景' },
  { label: '平均服务费', value: rows.value.length ? (rows.value.reduce((sum, item) => sum + Number(item.service_price || 0), 0) / rows.value.length).toFixed(2) : '0.00', prefix: '¥', tone: 'info', icon: Edit, trend: '当前模板均值', trendLabel: '便于对比价格策略' },
])

const resetForm = () => {
  editingId.value = null
  Object.assign(form, {
    name: '',
    peak_price: 1.88,
    flat_price: 1.32,
    valley_price: 0.68,
    service_price: 0.8,
    scope: 'station',
    status: 'active',
    description: '',
  })
}

const applyRows = (items = [], fromCache = false) => {
  rows.value = Array.isArray(items) ? items : []
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '缓存结果' : '最近刷新'} ${formatCacheUpdatedAt(Date.now())}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyRows(cached.value, true)
    cacheLabel.value = `缓存结果 ${formatCacheUpdatedAt(cached.updatedAt)}`
  }

  loading.value = !cached || !background
  try {
    const res = await fetchOperatorPricingTemplates()
    const items = Array.isArray(res?.data?.data) ? res.data.data : []
    applyRows(items)
    setRequestCache(cacheKey, items)
    cacheLabel.value = `最近刷新 ${formatCacheUpdatedAt(Date.now())}`
  } catch (error) {
    if (!rows.value.length) {
      applyRows([])
      cacheLabel.value = '当前内容可用'
    }
  } finally {
    loading.value = false
  }
}

const loadStationOptions = async () => {
  try {
    const { data } = await fetchOperatorStationOptions()
    if (data?.code !== 200) {
      throw new Error(data?.message || '电站选项加载失败')
    }
    stationRows.value = Array.isArray(data?.data) ? data.data : []
  } catch (error) {
    stationRows.value = []
    ElMessage.error(error?.message || '电站选项加载失败')
  }
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  Object.assign(form, row)
  dialogVisible.value = true
}

const save = async () => {
  if (!form.name.trim()) {
    ElMessage.warning('请填写模板名称')
    return
  }

  const payload = {
    name: form.name.trim(),
    peak_price: Number(form.peak_price) || 1.68,
    flat_price: Number(form.flat_price) || 1.18,
    valley_price: Number(form.valley_price) || 0.68,
    service_price: Number(form.service_price) || 0.72,
    scope: form.scope || 'all',
    status: form.status || 'active',
  }

  try {
    let res
    if (editingId.value) {
      res = await updateBillingTemplate(editingId.value, payload)
    } else {
      res = await createBillingTemplate(payload)
    }

    const rd = res?.data
    if (rd?.code !== 200) {
      throw new Error(rd?.message || '保存失败')
    }

    ElMessage.success(rd?.message || '模板保存成功')
    dialogVisible.value = false
    await loadData()
    setRequestCache(cacheKey, rows.value)
  } catch (error) {
    ElMessage.error(error?.message || '模板保存失败')
  }
}

const openStationDialog = (row) => {
  applyingTemplate.value = row
  selectedStations.value = []
  stationDialogVisible.value = true
}

const handleSelectedStations = (rows) => {
  selectedStations.value = rows
}

const submitStationApply = async () => {
  if (!applyingTemplate.value || !selectedStations.value.length) {
    ElMessage.warning('请至少选择一个电站')
    return
  }
  try {
    for (const station of selectedStations.value) {
      const { data } = await bindStationTemplate(station.id, applyingTemplate.value.id)
      if (data?.code !== 200) {
        throw new Error(data?.message || '模板应用失败')
      }
    }
    stationDialogVisible.value = false
    await loadStationOptions()
    ElMessage.success(`已将模板应用到 ${selectedStations.value.length} 个电站`)
  } catch (error) {
    ElMessage.error(error?.message || '模板应用失败')
  }
}

onMounted(async () => {
  await loadData()
  await loadStationOptions()
})
onActivated(() => {
  loadData({ background: true })
  loadStationOptions()
})
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="计费管理" title="计费模板管理" description="维护可复用的计费模板，并支持下发到指定电站。" chip="模板中心">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建模板</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--billing">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card table-shell">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">模板列表</h3>
          <p class="panel-heading__desc">统一维护峰平谷电价与服务费结构。</p>
        </div>
      </div>

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="8" />

      <el-table v-else-if="rows.length" :data="rows" v-loading="loading" stripe>
        <el-table-column prop="name" label="模板名称" min-width="180" />
        <el-table-column prop="peak_price" label="峰段" width="100" align="center" />
        <el-table-column prop="flat_price" label="平段" width="100" align="center" />
        <el-table-column prop="valley_price" label="谷段" width="100" align="center" />
        <el-table-column prop="service_price" label="服务费" width="100" align="center" />
        <el-table-column prop="scope" label="适用范围" width="120" align="center">
          <template #default="{ row }">{{ row.scope === 'station' ? '指定站点' : '全站通用' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用中' : '草稿' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="openEdit(row)">编辑</el-button>
            <el-button size="small" plain @click="openStationDialog(row)">应用站点</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无计费模板" description="可先新建模板并应用到指定电站。" />
    </section>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑模板' : '新建模板'" width="560px">
      <div class="form-grid">
        <el-form-item label="模板名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="适用范围">
          <el-select v-model="form.scope">
            <el-option label="全站通用" value="all" />
            <el-option label="指定站点" value="station" />
          </el-select>
        </el-form-item>
        <el-form-item label="峰段电价">
          <el-input-number v-model="form.peak_price" :step="0.01" style="width: 100%" />
        </el-form-item>
        <el-form-item label="平段电价">
          <el-input-number v-model="form.flat_price" :step="0.01" style="width: 100%" />
        </el-form-item>
        <el-form-item label="谷段电价">
          <el-input-number v-model="form.valley_price" :step="0.01" style="width: 100%" />
        </el-form-item>
        <el-form-item label="服务费">
          <el-input-number v-model="form.service_price" :step="0.01" style="width: 100%" />
        </el-form-item>
        <el-form-item label="模板说明" class="form-grid__full">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="简要说明模板适用业务场景" />
        </el-form-item>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="stationDialogVisible" title="应用到指定电站" width="640px">
      <div class="dialog-tip">
        当前模板：<strong>{{ applyingTemplate?.name || '-' }}</strong>
      </div>
      <el-table :data="stationOptions" border height="320" @selection-change="handleSelectedStations">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="station_name" label="电站名称" min-width="220" />
        <el-table-column prop="status_text" label="状态" width="120" align="center" />
        <el-table-column prop="price_template_name" label="当前模板" min-width="160" />
      </el-table>
      <template #footer>
        <el-button @click="stationDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitStationApply">确认应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid--billing {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.form-grid__full {
  grid-column: 1 / -1;
}

.dialog-tip {
  margin-bottom: 12px;
  color: var(--color-text-2);
}

@media (max-width: 1280px) {
  .stats-grid--billing {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--billing,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
