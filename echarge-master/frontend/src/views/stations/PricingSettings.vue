<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Edit, Location, Plus, RefreshRight } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import {
  bindStationTemplate,
  createBillingTemplate,
  fetchOperatorPricingTemplates,
  fetchOperatorStationOptions,
  updateBillingTemplate,
} from '../../api/operator'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const pageReady = ref(false)
const cacheLabel = ref('')
const templates = ref([])
const stationRows = ref([])
const activeTemplateId = ref(null)
const dialogVisible = ref(false)
const editFormVisible = ref(false)
const editingTemplateId = ref(null)
const selectedStations = ref([])

const form = reactive({
  name: '',
  peak_price: 1.88,
  flat_price: 1.32,
  valley_price: 0.68,
  service_price: 0.8,
  scope: 'all',
  status: 'active',
  description: '',
})

const cacheKey = buildRequestCacheKey('/operator/pricing/templates', { scope: 'pricing-settings' })
const stationOptions = computed(() => stationRows.value.filter((item) => Number(item.status) === 0))
const activeTemplate = computed(() => templates.value.find((item) => String(item.id) === String(activeTemplateId.value)) || null)

const stats = computed(() => [
  { label: '模板总数', value: templates.value.length, suffix: ' 个', tone: 'primary', icon: Document },
  { label: '启用模板', value: templates.value.filter((item) => item.status === 'active').length, suffix: ' 个', tone: 'success', icon: RefreshRight },
  { label: '全站模板', value: templates.value.filter((item) => item.scope === 'all' || item.scope === '全站').length, suffix: ' 个', tone: 'warning', icon: Location },
  { label: '平均服务费', value: templates.value.length ? (templates.value.reduce((sum, item) => sum + Number(item.service_price || 0), 0) / templates.value.length).toFixed(2) : '0.00', prefix: '¥', tone: 'info', icon: Edit },
])

const applyTemplates = (items = [], fromCache = false) => {
  templates.value = Array.isArray(items) ? items : []
  if (!activeTemplateId.value && templates.value.length) {
    activeTemplateId.value = templates.value[0].id
  }
  pageReady.value = true
  cacheLabel.value = `${fromCache ? '缓存结果' : '最近刷新'} ${formatCacheUpdatedAt(Date.now())}`
}

const resetForm = () => {
  editingTemplateId.value = null
  Object.assign(form, {
    name: '',
    peak_price: 1.88,
    flat_price: 1.32,
    valley_price: 0.68,
    service_price: 0.8,
    scope: 'all',
    status: 'active',
    description: '',
  })
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyTemplates(cached.value, true)
    cacheLabel.value = `缓存结果 ${formatCacheUpdatedAt(cached.updatedAt)}`
  }

  loading.value = !cached || !background
  try {
    const res = await fetchOperatorPricingTemplates()
    const items = Array.isArray(res?.data?.data) ? res.data.data : []
    applyTemplates(items)
    setRequestCache(cacheKey, items)
    cacheLabel.value = `最近刷新 ${formatCacheUpdatedAt(Date.now())}`
  } catch (error) {
    if (!templates.value.length) {
      applyTemplates([])
      cacheLabel.value = '暂无可用模板'
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

const selectTemplate = (template) => {
  activeTemplateId.value = template.id
}

const openCreate = () => {
  resetForm()
  editFormVisible.value = true
}

const openEdit = () => {
  if (!activeTemplate.value) {
    ElMessage.warning('请先选择一个模板')
    return
  }
  editingTemplateId.value = activeTemplate.value.id
  Object.assign(form, {
    name: activeTemplate.value.name,
    peak_price: Number(activeTemplate.value.peak_price) || 1.88,
    flat_price: Number(activeTemplate.value.flat_price) || 1.32,
    valley_price: Number(activeTemplate.value.valley_price) || 0.68,
    service_price: Number(activeTemplate.value.service_price) || 0.8,
    scope: activeTemplate.value.scope === '全站通用' || activeTemplate.value.scope === '全站' || activeTemplate.value.scope === 'all' ? 'all' : 'station',
    status: activeTemplate.value.status || 'active',
    description: '',
  })
  editFormVisible.value = true
}

const saveTemplate = async () => {
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
    if (editingTemplateId.value) {
      res = await updateBillingTemplate(editingTemplateId.value, payload)
    } else {
      res = await createBillingTemplate(payload)
    }

    const rd = res?.data
    if (rd?.code !== 200) {
      throw new Error(rd?.message || '保存失败')
    }

    ElMessage.success(rd?.message || '模板保存成功')
    editFormVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error(error?.message || '模板保存失败')
  }
}

const openStationDialog = () => {
  if (!activeTemplate.value) {
    ElMessage.warning('请先选择模板')
    return
  }
  selectedStations.value = []
  dialogVisible.value = true
}

const handleSelectedStations = (rows) => {
  selectedStations.value = rows
}

const submitStationApply = async () => {
  if (!activeTemplate.value || !selectedStations.value.length) {
    ElMessage.warning('请至少选择一个电站')
    return
  }
  try {
    for (const station of selectedStations.value) {
      const { data } = await bindStationTemplate(station.id, activeTemplate.value.id)
      if (data?.code !== 200) {
        throw new Error(data?.message || '模板应用失败')
      }
    }
    dialogVisible.value = false
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
    <PageSectionHeader eyebrow="计费管理" title="电价设置" description="维护峰平谷电价与服务费模板，并支持下发到指定电站。" chip="电价策略">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="Plus" type="primary" @click="openCreate">新建模板</el-button>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--pricing">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">模板选择</h3>
          <p class="panel-heading__desc">选择模板后可编辑价格并下发到站点。</p>
        </div>
      </div>

      <TableSkeletonBlock v-if="loading && !pageReady" :rows="3" :columns="4" />

      <template v-else>
        <div v-if="templates.length" class="template-grid">
          <button
            v-for="item in templates"
            :key="item.id"
            type="button"
            class="template-card"
            :class="{ 'template-card--active': String(activeTemplateId) === String(item.id) }"
            @click="selectTemplate(item)"
          >
            <div class="template-card__head">
              <strong>{{ item.name }}</strong>
              <el-tag :type="item.status === 'active' ? 'success' : 'info'" size="small">{{ item.status === 'active' ? '启用中' : '草稿' }}</el-tag>
            </div>
            <div class="template-card__meta">
              <span>{{ item.scope === 'station' ? '指定站点' : '全站通用' }}</span>
              <span>{{ item.updated_at }}</span>
            </div>
          </button>
        </div>

        <EmptyStateBlock v-else title="暂无电价模板" description="点击上方「新建模板」按钮创建第一个计费模板。" />
      </template>
    </section>

    <section class="page-panel surface-card" v-if="activeTemplate">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">价格明细（{{ activeTemplate.name }}）</h3>
          <p class="panel-heading__desc">峰平谷电价与服务费标准，单位：元/kWh。</p>
        </div>
        <div class="toolbar-actions">
          <el-button plain :icon="Location" @click="openStationDialog">应用到指定电站</el-button>
          <el-button type="primary" plain :icon="Edit" @click="openEdit">编辑模板</el-button>
        </div>
      </div>

      <el-table :data="[activeTemplate]" border>
        <el-table-column prop="peak_price" label="峰段电价" width="180" align="center" />
        <el-table-column prop="flat_price" label="平段电价" width="180" align="center" />
        <el-table-column prop="valley_price" label="谷段电价" width="180" align="center" />
        <el-table-column prop="service_price" label="服务费" width="180" align="center" />
        <el-table-column label="合计均价" width="180" align="center">
          <template #default="{ row }">{{ (Number(row.peak_price || 0) + Number(row.service_price || 0)).toFixed(2) }}</template>
        </el-table-column>
      </el-table>

      <div class="detail-info">
        <div class="info-item">
          <span class="info-item__label">适用范围</span>
          <span>{{ activeTemplate.scope === 'station' ? '指定站点' : '全站通用' }}</span>
        </div>
        <div class="info-item">
          <span class="info-item__label">状态</span>
          <el-tag :type="activeTemplate.status === 'active' ? 'success' : 'info'" size="small">{{ activeTemplate.status === 'active' ? '启用中' : '草稿' }}</el-tag>
        </div>
        <div class="info-item">
          <span class="info-item__label">更新时间</span>
          <span>{{ activeTemplate.updated_at }}</span>
        </div>
      </div>
    </section>

    <el-dialog v-model="editFormVisible" :title="editingTemplateId ? '编辑模板' : '新建模板'" width="560px">
      <div class="form-grid">
        <el-form-item label="模板名称">
          <el-input v-model="form.name" placeholder="例：城市快充标准模板" />
        </el-form-item>
        <el-form-item label="适用范围">
          <el-select v-model="form.scope">
            <el-option label="全站通用" value="all" />
            <el-option label="指定站点" value="station" />
          </el-select>
        </el-form-item>
        <el-form-item label="峰段电价（元）">
          <el-input-number v-model="form.peak_price" :step="0.01" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="平段电价（元）">
          <el-input-number v-model="form.flat_price" :step="0.01" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="谷段电价（元）">
          <el-input-number v-model="form.valley_price" :step="0.01" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="服务费（元）">
          <el-input-number v-model="form.service_price" :step="0.01" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态" class="form-grid__full">
          <el-select v-model="form.status">
            <el-option label="启用" value="active" />
            <el-option label="草稿" value="draft" />
          </el-select>
        </el-form-item>
      </div>
      <template #footer>
        <el-button @click="editFormVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" title="应用到指定电站" width="640px">
      <div class="dialog-tip">
        当前模板：<strong>{{ activeTemplate?.name || '-' }}</strong>
      </div>
      <el-table :data="stationOptions" border height="320" @selection-change="handleSelectedStations">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="station_name" label="电站名称" min-width="220" />
        <el-table-column prop="status_text" label="状态" width="120" align="center" />
        <el-table-column prop="price_template_name" label="当前模板" min-width="160" />
      </el-table>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitStationApply">确认应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid--pricing {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.template-card {
  text-align: left;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  padding: 16px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.template-card--active {
  border-color: rgba(37, 99, 235, 0.32);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.12);
}

.template-card__head,
.template-card__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-info {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 12px;
  border: 1px solid #ebeef5;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item__label {
  color: var(--color-text-2);
  font-size: 13px;
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
  .stats-grid--pricing,
  .template-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--pricing,
  .template-grid {
    grid-template-columns: 1fr;
  }
}
</style>
