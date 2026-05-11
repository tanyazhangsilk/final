<script setup>
import { computed, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Lightning, Plus, RefreshRight, Tickets, WarningFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import {
  batchCreateStationChargers,
  createStationCharger,
  fetchOperatorStationOptions,
  fetchStationChargers,
  updateStationCharger,
} from '../../api/operator'
import {
  buildRequestCacheKey,
  clearOperatorOrderStartOptionsCaches,
  clearOperatorStationsOptionsCache,
  clearStationChargersCachesForStation,
  formatCacheLabel,
  getRequestCache,
  setRequestCache,
  shouldRefreshRequestCache,
} from '../../utils/requestCache'

const route = useRoute()
const CACHE_TTL = 60 * 1000

const stationLoading = ref(false)
const loading = ref(false)
const submitLoading = ref(false)
const batchSubmitting = ref(false)
const tableReady = ref(false)
const cacheLabel = ref('')
const initialized = ref(false)
/** 行级状态更新中，防止重复点击 */
const rowStatusSaving = ref(null)

const stations = ref([])
const chargers = ref([])
const selectedStationId = ref(null)

const addDialogVisible = ref(false)
const batchDialogVisible = ref(false)

const addForm = reactive({
  sn_code: '',
  charger_name: '',
  type: 'DC',
  power_kw: 120,
  status: 0,
})

const batchForm = reactive({
  count: 6,
  type: 'DC',
  power_kw: 120,
})

const statusOptions = [
  { label: '空闲', value: 0 },
  { label: '充电中', value: 1 },
  { label: '故障', value: 2 },
  { label: '停用', value: 3 },
]

const selectedStation = computed(() => stations.value.find((item) => String(item.id) === String(selectedStationId.value)) || null)
const stationCacheKey = computed(() => buildRequestCacheKey('/operator/stations/options', { scope: 'pile-management' }))
const chargerCacheKey = computed(() => buildRequestCacheKey(`/operator/stations/${selectedStationId.value}/chargers`, { station_id: selectedStationId.value }))

const chargerStats = computed(() => [
  {
    label: '电桩总数',
    value: chargers.value.length,
    suffix: ' 台',
    trend: '当前站点全部设备',
    trendLabel: '支持新增、批量生成和状态切换',
    tone: 'primary',
    icon: Lightning,
  },
  {
    label: '空闲可用',
    value: chargers.value.filter((item) => Number(item.status) === 0).length,
    suffix: ' 台',
    trend: '可立即发起充电',
    trendLabel: '用于演示扫码和手动启动',
    tone: 'success',
    icon: CircleCheck,
  },
  {
    label: '充电中',
    value: chargers.value.filter((item) => Number(item.status) === 1).length,
    suffix: ' 台',
    trend: '当前被订单占用',
    trendLabel: '与实时订单联动展示',
    tone: 'warning',
    icon: Tickets,
  },
  {
    label: '故障 / 停用',
    value: chargers.value.filter((item) => [2, 3].includes(Number(item.status))).length,
    suffix: ' 台',
    trend: '需跟进处理',
    trendLabel: '支持快速切换演示状态',
    tone: 'danger',
    icon: WarningFilled,
  },
])

const statusTagType = (status) => (Number(status) === 1 ? 'warning' : Number(status) === 2 ? 'danger' : Number(status) === 3 ? 'info' : 'success')

const STATUS_TEXT = { 0: '空闲', 1: '充电中', 2: '故障', 3: '停用' }

const updateCacheLabel = (timestamp = Date.now()) => {
  cacheLabel.value = formatCacheLabel(timestamp)
}

const resetAddForm = () => {
  Object.assign(addForm, {
    sn_code: '',
    charger_name: '',
    type: 'DC',
    power_kw: 120,
    status: 0,
  })
}

const applyChargers = (remoteRows = [], updatedAt = Date.now()) => {
  chargers.value = remoteRows
  tableReady.value = true
  updateCacheLabel(updatedAt)
}

/** 只把可 JSON 化的纯对象写入 requestCache，勿传 Axios response / Vue 行代理 */
const plainChargerRowsForCache = (rows) =>
  (Array.isArray(rows) ? rows : []).map((item) => (item && typeof item === 'object' ? { ...item } : item))

const plainStationOptionsForCache = (rows) =>
  (Array.isArray(rows) ? rows : []).map((item) => (item && typeof item === 'object' ? { ...item } : item))

const loadStations = async ({ background = false } = {}) => {
  const cached = getRequestCache(stationCacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    stations.value = Array.isArray(cached.value) ? cached.value : []
    if (!selectedStationId.value && stations.value.length) {
      selectedStationId.value = String(route.query.stationId || stations.value.find((item) => Number(item.status) === 0)?.id || stations.value[0].id)
    }
    updateCacheLabel(cached.updatedAt)
  }

  stationLoading.value = !cached || !background
  try {
    const { data } = await fetchOperatorStationOptions()
    if (data?.code !== 200) {
      throw new Error(data?.message || '电站列表加载失败')
    }
    const items = Array.isArray(data?.data) && data.data.length ? data.data : []
    stations.value = items
    if (String(route.query.stationId || '') && items.some((item) => String(item.id) === String(route.query.stationId))) {
      selectedStationId.value = String(route.query.stationId)
    } else if (!selectedStationId.value && items.length) {
      selectedStationId.value = String(items.find((item) => Number(item.status) === 0)?.id || items[0].id)
    }
    setRequestCache(stationCacheKey.value, plainStationOptionsForCache(items))
    updateCacheLabel(Date.now())
  } catch (error) {
    if (!stations.value.length) {
      stations.value = []
      selectedStationId.value = ''
      ElMessage.error(error?.message || '电站列表加载失败')
      updateCacheLabel(Date.now())
    }
  } finally {
    stationLoading.value = false
  }
}

const loadChargers = async ({ background = false } = {}) => {
  if (!selectedStationId.value) {
    chargers.value = []
    tableReady.value = true
    return
  }

  const cached = getRequestCache(chargerCacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyChargers(cached.value, cached.updatedAt)
  }

  loading.value = !cached || !background
  try {
    const { data } = await fetchStationChargers(selectedStationId.value)
    if (data?.code !== 200) {
      throw new Error(data?.message || '电桩列表加载失败')
    }
    const remoteRows = Array.isArray(data?.data) ? data.data : []
    applyChargers(remoteRows, Date.now())
    setRequestCache(chargerCacheKey.value, plainChargerRowsForCache(remoteRows))
  } catch (error) {
    if (Array.isArray(cached?.value) && cached.value.length) {
      applyChargers(cached.value, Date.now())
    } else if (!chargers.value.length) {
      applyChargers([], Date.now())
    }
    ElMessage.error(error?.message || '电桩列表加载失败')
  } finally {
    loading.value = false
  }
}

const rebuildDemoChargers = async () => {
  if (!selectedStation.value) {
    ElMessage.warning('请先选择电站')
    return
  }
  try {
    const { data } = await batchCreateStationChargers(selectedStation.value.id, {
      count: Math.max(1, Number(selectedStation.value.planned_charger_count || 4)),
      type: 'DC',
      power_kw: 120,
    })
    if (data?.code !== 200) {
      throw new Error(data?.message || '演示电桩生成失败')
    }
    clearOperatorStationsOptionsCache()
    clearStationChargersCachesForStation(selectedStation.value.id)
    clearOperatorOrderStartOptionsCaches()
    await loadChargers({ background: true })
    ElMessage.success(data?.message || '演示电桩已写入数据库')
  } catch (error) {
    ElMessage.error(error?.message || '演示电桩生成失败')
  }
}

const openAddDialog = () => {
  if (!selectedStation.value) {
    ElMessage.warning('请先选择电站')
    return
  }
  resetAddForm()
  addDialogVisible.value = true
}

const submitAddCharger = async () => {
  if (!selectedStation.value) {
    ElMessage.warning('请先选择电站')
    return
  }
  if (!addForm.sn_code.trim() || !addForm.charger_name.trim()) {
    ElMessage.warning('请填写电桩编号和名称')
    return
  }

  submitLoading.value = true
  try {
    const { data } = await createStationCharger(selectedStation.value.id, {
      sn_code: addForm.sn_code.trim(),
      charger_name: addForm.charger_name.trim(),
      type: addForm.type,
      power_kw: Number(addForm.power_kw),
      status: Number(addForm.status),
    })
    if (data?.code !== 200) {
      throw new Error(data?.message || '电桩新增失败')
    }
    const row = data?.data
    if (row && selectedStationId.value) {
      chargers.value = [row, ...chargers.value.filter((c) => String(c.id) !== String(row.id))]
      setRequestCache(chargerCacheKey.value, plainChargerRowsForCache(chargers.value))
    }
    clearStationChargersCachesForStation(selectedStation.value.id)
    clearOperatorOrderStartOptionsCaches()
    ElMessage.success(data?.message || '电桩新增成功')
  } catch (error) {
    ElMessage.error(error?.message || '电桩新增失败')
  } finally {
    submitLoading.value = false
    addDialogVisible.value = false
    void loadChargers({ background: true })
  }
}

const openBatchDialog = () => {
  if (!selectedStation.value) {
    ElMessage.warning('请先选择电站')
    return
  }
  Object.assign(batchForm, { count: 6, type: 'DC', power_kw: 120 })
  batchDialogVisible.value = true
}

const submitBatchCreate = async () => {
  if (!selectedStation.value) {
    ElMessage.warning('请先选择电站')
    return
  }

  batchSubmitting.value = true
  try {
    const { data } = await batchCreateStationChargers(selectedStation.value.id, {
      count: Number(batchForm.count),
      type: batchForm.type,
      power_kw: Number(batchForm.power_kw),
    })
    if (data?.code !== 200) {
      throw new Error(data?.message || '批量生成失败')
    }
    const created = Array.isArray(data?.data) ? data.data : []
    if (created.length && selectedStationId.value) {
      const idSet = new Set(created.map((r) => String(r.id)))
      chargers.value = [...created, ...chargers.value.filter((c) => !idSet.has(String(c.id)))]
      setRequestCache(chargerCacheKey.value, plainChargerRowsForCache(chargers.value))
    }
    clearStationChargersCachesForStation(selectedStation.value.id)
    clearOperatorOrderStartOptionsCaches()
    ElMessage.success(data?.message || '批量生成成功')
  } catch (error) {
    ElMessage.error(error?.message || '批量生成失败')
  } finally {
    batchSubmitting.value = false
    batchDialogVisible.value = false
    void loadChargers({ background: true })
  }
}

const updateChargerStatus = async (row, status) => {
  const stationId = Number(row?.station_id ?? selectedStationId.value)
  const chargerId = Number(row?.id)
  if (!Number.isFinite(stationId) || stationId <= 0 || !Number.isFinite(chargerId) || chargerId <= 0) {
    ElMessage.error('无效的电桩或电站信息，请刷新页面后重试')
    return
  }
  if (rowStatusSaving.value === chargerId) return

  const prevStatus = Number(row.status)
  const prevText = row.status_text
  const prevUpdated = row.updated_at
  rowStatusSaving.value = chargerId
  row.status = Number(status)
  row.status_text = STATUS_TEXT[Number(status)] || prevText
  try {
    const { data } = await updateStationCharger(stationId, chargerId, { status })
    if (data?.code !== 200) {
      throw new Error(data?.message || '电桩状态更新失败')
    }
    if (data?.data && typeof data.data === 'object') {
      const d = data.data
      row.status = Number(d.status ?? status)
      row.status_text = d.status_text || STATUS_TEXT[row.status] || prevText
      row.updated_at = d.updated_at || row.updated_at
    }
    clearStationChargersCachesForStation(stationId)
    clearOperatorOrderStartOptionsCaches()
    ElMessage.success(data?.message || '电桩状态已更新')
  } catch (error) {
    row.status = prevStatus
    row.status_text = prevText
    row.updated_at = prevUpdated
    const msg = error?.response?.data?.message || error?.message || '电桩状态更新失败'
    ElMessage.error(msg)
  } finally {
    rowStatusSaving.value = null
    await loadChargers({ background: true })
  }
}

watch(
  selectedStationId,
  async (value, oldValue) => {
    if (!initialized.value || !value || value === oldValue) return
    await loadChargers({ background: true })
  },
)

onMounted(async () => {
  await loadStations({ background: true })
  if (selectedStationId.value) {
    await loadChargers({ background: true })
  }
  initialized.value = true
})

onActivated(() => {
  if (shouldRefreshRequestCache(stationCacheKey.value, CACHE_TTL)) {
    loadStations({ background: true })
  }
  if (selectedStationId.value && shouldRefreshRequestCache(chargerCacheKey.value, CACHE_TTL)) {
    loadChargers({ background: true })
  }
})

// ===== QR 码 =====
import QRCode from 'qrcode'
const qrDialogVisible = ref(false)
const qrChargerSN = ref('')
const qrImageUrl = ref('')

function showChargerQR(row) {
  qrChargerSN.value = row.sn_code || ''
  qrImageUrl.value = ''
  qrDialogVisible.value = true
  if (qrChargerSN.value) {
    QRCode.toDataURL(qrChargerSN.value, { width: 260, margin: 2, color: { dark: '#000000', light: '#FFFFFF' } })
      .then((url) => { qrImageUrl.value = url })
      .catch(() => { qrImageUrl.value = '' })
  }
}
</script>

<template>
  <div class="page-shell charger-page">
    <PageSectionHeader
      eyebrow="资产管理"
      title="电桩管理"
      description="维护单桩新增、批量生成、设备状态与所属电站。"
      chip="设备配置"
    >
      <template #actions>
        <el-select v-model="selectedStationId" placeholder="请选择电站" filterable :loading="stationLoading" style="width: 300px">
          <el-option
            v-for="item in stations"
            :key="item.id"
            :label="`${item.station_name} / ${item.status_text}`"
            :value="String(item.id)"
          />
        </el-select>
        <el-button type="primary" :icon="Plus" @click="openAddDialog">新增电桩</el-button>
        <el-button type="primary" plain :icon="Tickets" @click="openBatchDialog">批量生成电桩</el-button>
        <el-button plain @click="rebuildDemoChargers">重建演示电桩</el-button>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadChargers()">刷新</el-button>
      </template>
    </PageSectionHeader>

    <div v-if="selectedStation" class="station-banner surface-card">
      <div>
        <strong>{{ selectedStation.station_name }}</strong>
        <p>{{ selectedStation.full_address || '当前电站地址待补充' }}</p>
      </div>
      <div class="station-banner__meta">
        <el-tag :type="Number(selectedStation.status) === 0 ? 'success' : 'warning'">{{ selectedStation.status_text }}</el-tag>
        <el-tag :type="selectedStation.visibility === 'public' ? 'success' : 'info'">{{ selectedStation.visibility_text }}</el-tag>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
      </div>
    </div>

    <section class="stats-grid stats-grid--chargers">
      <MetricCard v-for="item in chargerStats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card table-shell">
      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="8" />

      <el-table v-else-if="chargers.length" :data="chargers" v-loading="loading" stripe>
        <el-table-column prop="sn_code" label="设备编号" min-width="180" />
        <el-table-column prop="charger_name" label="设备名称" min-width="160" />
        <el-table-column prop="type" label="类型" width="100" align="center" />
        <el-table-column label="功率(kW)" width="110" align="right">
          <template #default="{ row }">{{ Number(row.power_kw || 0).toFixed(0) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="二维码" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showChargerQR(row)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最近更新" width="180" />
        <el-table-column label="快捷操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" :loading="rowStatusSaving != null && Number(rowStatusSaving) === Number(row.id)" :disabled="rowStatusSaving != null" @click="updateChargerStatus(row, 0)">设为空闲</el-button>
            <el-button link type="warning" :loading="rowStatusSaving != null && Number(rowStatusSaving) === Number(row.id)" :disabled="rowStatusSaving != null" @click="updateChargerStatus(row, 1)">设为充电中</el-button>
            <el-button link type="danger" :loading="rowStatusSaving != null && Number(rowStatusSaving) === Number(row.id)" :disabled="rowStatusSaving != null" @click="updateChargerStatus(row, 2)">标记故障</el-button>
            <el-button link type="info" :loading="rowStatusSaving != null && Number(rowStatusSaving) === Number(row.id)" :disabled="rowStatusSaving != null" @click="updateChargerStatus(row, 3)">停用</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock
        v-else-if="!loading"
        title="暂无电桩数据"
        description="当前站点暂未读取到电桩记录，可直接生成演示电桩继续演示。"
      />
    </section>

    <el-dialog v-model="addDialogVisible" title="新增电桩" width="560px">
      <el-form label-width="96px">
        <el-form-item label="设备编号"><el-input v-model="addForm.sn_code" /></el-form-item>
        <el-form-item label="设备名称"><el-input v-model="addForm.charger_name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="addForm.type" style="width: 100%">
            <el-option label="直流 DC" value="DC" />
            <el-option label="交流 AC" value="AC" />
          </el-select>
        </el-form-item>
        <el-form-item label="功率(kW)"><el-input-number v-model="addForm.power_kw" :min="7" :max="360" style="width: 100%" /></el-form-item>
        <el-form-item label="初始状态">
          <el-select v-model="addForm.status" style="width: 100%">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitAddCharger">确认新增</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="批量生成演示电桩" width="520px">
      <el-form label-width="110px">
        <el-form-item label="生成数量">
          <el-input-number v-model="batchForm.count" :min="1" :max="50" style="width: 100%" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="batchForm.type" style="width: 100%">
            <el-option label="直流 DC" value="DC" />
            <el-option label="交流 AC" value="AC" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认功率(kW)">
          <el-input-number v-model="batchForm.power_kw" :min="7" :max="360" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchSubmitting" @click="submitBatchCreate">开始生成</el-button>
      </template>
    </el-dialog>

    <!-- QR 码弹窗 -->
    <el-dialog v-model="qrDialogVisible" title="充电桩二维码" width="400px" :close-on-click-modal="false" align-center>
      <div v-if="qrChargerSN" style="text-align:center;padding:20px 0">
        <div style="font-size:14px;color:#666;margin-bottom:12px">设备编号：{{ qrChargerSN }}</div>
        <img v-if="qrImageUrl" :src="qrImageUrl" style="width:260px;height:260px;border-radius:8px;border:1px solid #eee" />
        <div v-else style="width:260px;height:260px;margin:0 auto;display:flex;align-items:center;justify-content:center;border:1px solid #eee;border-radius:8px;color:#999;font-size:14px">
          正在生成二维码...
        </div>
        <div style="margin-top:16px;font-size:13px;color:#999">可扫描此二维码开始充电</div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.station-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.station-banner strong {
  display: block;
  font-size: 18px;
  margin-bottom: 6px;
}

.station-banner p {
  margin: 0;
  color: var(--color-text-2);
}

.station-banner__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stats-grid--chargers {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

@media (max-width: 1280px) {
  .stats-grid--chargers {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .station-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .stats-grid--chargers {
    grid-template-columns: 1fr;
  }
}
</style>
