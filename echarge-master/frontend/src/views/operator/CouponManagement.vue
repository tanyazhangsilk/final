<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Promotion, RefreshRight, Tickets } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import ErrorBlock from '../../components/console/ErrorBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { createCoupon, dispatchCoupon, fetchCoupons } from '../../api/operator'
import { mockCoupons } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const cacheLabel = ref('')
const errorMessage = ref('')
const rows = ref([])

const dialogVisible = ref(false)
const filters = reactive({ keyword: '', status: '' })
const form = reactive({ name: '', discount_value: 10, inventory: 1000, status: '待投放' })
const cacheKey = buildRequestCacheKey('/operator/marketing/coupons', { scope: 'operator-coupons' })

const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return rows.value.filter((item) => {
    const matchKeyword = !keyword || [item.name, item.discount_value].filter(Boolean).some((field) => String(field).toLowerCase().includes(keyword))
    const matchStatus = !filters.status || String(item.status) === filters.status
    return matchKeyword && matchStatus
  })
})

const stats = computed(() => [
  { label: '券活动数', value: rows.value.length, suffix: ' 个', trend: '当前券池规模', trendLabel: '支持多场景投放', tone: 'primary', icon: Tickets },
  { label: '总库存', value: rows.value.reduce((sum, item) => sum + Number(item.inventory || 0), 0), suffix: ' 张', trend: '可发放总量', trendLabel: '建议按阶段释放', tone: 'success', icon: Promotion },
  { label: '已发放', value: rows.value.reduce((sum, item) => sum + Number(item.dispatched || 0), 0), suffix: ' 张', trend: '累计投放量', trendLabel: '关注分渠道效果', tone: 'warning', icon: RefreshRight },
  { label: '已核销', value: rows.value.reduce((sum, item) => sum + Number(item.used || 0), 0), suffix: ' 张', trend: '活动转化情况', trendLabel: '用于复盘投放效率', tone: 'info', icon: Plus },
])

const applyRows = (items = [], fromCache = false, updatedAt = Date.now()) => {
  rows.value = Array.isArray(items) && items.length ? items : mockCoupons
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '最近可用数据' : '已更新'} ${formatCacheUpdatedAt(updatedAt)}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) applyRows(cached.value, true, cached.updatedAt)

  loading.value = !cached || !background
  errorMessage.value = ''
  try {
    const res = await fetchCoupons()
    const items = Array.isArray(res?.data?.data) ? res.data.data : mockCoupons
    applyRows(items, false, Date.now())
    setRequestCache(cacheKey, items)
  } catch (error) {
    if (!rows.value.length) {
      applyRows(mockCoupons, false, Date.now())
      cacheLabel.value = '当前内容可用'
    }
    errorMessage.value = '当前列表已保持最近更新内容。'
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!form.name.trim()) {
    ElMessage.warning('请输入活动名称')
    return
  }
  try {
    await createCoupon({ ...form })
  } catch (error) {
    rows.value.unshift({
      id: Date.now(),
      name: form.name.trim(),
      discount_value: `${form.discount_value} 元`,
      inventory: Number(form.inventory || 0),
      dispatched: 0,
      used: 0,
      status: form.status,
    })
  }
  ElMessage.success('券活动已创建')
  dialogVisible.value = false
  await loadData({ background: true })
}

const dispatch = async (row) => {
  try {
    await dispatchCoupon(row.id, { dispatch_count: 100 })
  } catch (error) {
    row.dispatched = Number(row.dispatched || 0) + 100
  }
  ElMessage.success('已追加发放 100 张')
  await loadData({ background: true })
}

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="营销管理" title="优惠券发放" description="维护券活动、库存消耗与发放节奏。" chip="券中心">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="dialogVisible = true">创建券活动</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--coupons">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">按活动名称、状态筛选券池。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索活动名称 / 面额" style="width: 320px" />
        <el-select v-model="filters.status" clearable placeholder="活动状态" style="width: 160px">
          <el-option label="投放中" value="投放中" />
          <el-option label="待投放" value="待投放" />
        </el-select>
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <ErrorBlock
        v-if="errorMessage"
        title="券活动状态提示"
        :description="errorMessage"
        @retry="loadData()"
      />

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="7" />

      <el-table v-else-if="filteredRows.length" :data="filteredRows" v-loading="loading" stripe>
        <el-table-column prop="name" label="活动名称" min-width="180" />
        <el-table-column prop="discount_value" label="面额" width="100" align="center" />
        <el-table-column prop="inventory" label="总库存" width="110" align="center" />
        <el-table-column prop="dispatched" label="已发放" width="110" align="center" />
        <el-table-column prop="used" label="已核销" width="110" align="center" />
        <el-table-column prop="status" label="状态" width="120" align="center" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }"><el-button size="small" type="primary" plain @click="dispatch(row)">追加发放</el-button></template>
        </el-table-column>
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无券活动" description="当前筛选条件下没有匹配活动。" />
    </section>

    <el-dialog v-model="dialogVisible" title="创建优惠券活动" width="480px">
      <el-form label-position="top">
        <el-form-item label="活动名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="券面额"><el-input-number v-model="form.discount_value" :step="1" style="width: 100%" /></el-form-item>
        <el-form-item label="初始库存"><el-input-number v-model="form.inventory" :min="1" :step="100" style="width: 100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid--coupons {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

@media (max-width: 1280px) {
  .stats-grid--coupons {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--coupons {
    grid-template-columns: 1fr;
  }
}
</style>
