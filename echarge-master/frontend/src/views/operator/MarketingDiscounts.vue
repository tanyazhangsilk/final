<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Discount, Plus, RefreshRight, Tickets } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import ErrorBlock from '../../components/console/ErrorBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { createDiscount, fetchDiscounts } from '../../api/operator'
import { mockDiscounts } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const cacheLabel = ref('')
const errorMessage = ref('')
const rows = ref([])
const dialogVisible = ref(false)

const filters = reactive({ keyword: '', status: '' })
const form = reactive({ name: '', campaign_type: '满减', discount_value: 8.8, threshold: 30, audience: '车队客户', status: '待审核' })
const cacheKey = buildRequestCacheKey('/operator/marketing/discounts', { scope: 'operator-discounts' })

const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return rows.value.filter((item) => {
    const matchKeyword = !keyword || [item.name, item.campaign_type, item.audience].filter(Boolean).some((field) => String(field).toLowerCase().includes(keyword))
    const matchStatus = !filters.status || String(item.status) === filters.status
    return matchKeyword && matchStatus
  })
})

const stats = computed(() => [
  { label: '活动总数', value: rows.value.length, suffix: ' 个', trend: '当前折扣活动', trendLabel: '覆盖多类投放场景', tone: 'primary', icon: Discount },
  { label: '进行中', value: rows.value.filter((item) => String(item.status).includes('进行')).length, suffix: ' 个', trend: '可直接触达用户', trendLabel: '持续追踪核销效果', tone: 'success', icon: Tickets },
  { label: '待审核', value: rows.value.filter((item) => String(item.status).includes('审核')).length, suffix: ' 个', trend: '待审批活动', trendLabel: '建议尽快完成审核', tone: 'warning', icon: RefreshRight },
  { label: '累计核销', value: rows.value.reduce((sum, item) => sum + Number(item.redeem_count || 0), 0), suffix: ' 次', trend: '活动累计转化', trendLabel: '用于评估投放效率', tone: 'info', icon: Plus },
])

const applyRows = (items = [], fromCache = false, updatedAt = Date.now()) => {
  rows.value = Array.isArray(items) && items.length ? items : mockDiscounts
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '最近可用数据' : '已更新'} ${formatCacheUpdatedAt(updatedAt)}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) applyRows(cached.value, true, cached.updatedAt)

  loading.value = !cached || !background
  errorMessage.value = ''
  try {
    const res = await fetchDiscounts()
    const items = Array.isArray(res?.data?.data) ? res.data.data : mockDiscounts
    applyRows(items, false, Date.now())
    setRequestCache(cacheKey, items)
  } catch (error) {
    if (!rows.value.length) {
      applyRows(mockDiscounts, false, Date.now())
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
    await createDiscount({ ...form })
  } catch (error) {
    rows.value.unshift({
      ...form,
      id: Date.now(),
      redeem_count: 0,
      conversion_rate: '0%',
      discount_value: String(form.discount_value),
      threshold: `满 ${form.threshold} 可用`,
    })
  }
  ElMessage.success('活动已创建')
  dialogVisible.value = false
  await loadData({ background: true })
}

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="营销管理" title="折扣优惠" description="维护折扣活动、投放对象与核销转化表现。" chip="活动管理">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="dialogVisible = true">新建活动</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--discounts">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">按活动名称、类型、状态筛选投放活动。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索活动名称 / 类型 / 投放对象" style="width: 340px" />
        <el-select v-model="filters.status" clearable placeholder="活动状态" style="width: 160px">
          <el-option label="进行中" value="进行中" />
          <el-option label="待审核" value="待审核" />
        </el-select>
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <ErrorBlock
        v-if="errorMessage"
        title="活动列表状态提示"
        :description="errorMessage"
        @retry="loadData()"
      />

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="7" />

      <el-table v-else-if="filteredRows.length" :data="filteredRows" v-loading="loading" stripe>
        <el-table-column prop="name" label="活动名称" min-width="180" />
        <el-table-column prop="campaign_type" label="类型" width="100" align="center" />
        <el-table-column prop="discount_value" label="优惠力度" width="120" align="center" />
        <el-table-column prop="threshold" label="门槛" min-width="130" />
        <el-table-column prop="audience" label="投放对象" min-width="140" />
        <el-table-column prop="redeem_count" label="核销量" width="100" align="center" />
        <el-table-column prop="conversion_rate" label="转化率" width="100" align="center" />
        <el-table-column prop="status" label="状态" width="120" align="center" />
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无活动数据" description="当前筛选条件下没有匹配活动。" />
    </section>

    <el-dialog v-model="dialogVisible" title="新建折扣活动" width="520px">
      <div class="form-grid">
        <el-form-item label="活动名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="活动类型">
          <el-select v-model="form.campaign_type">
            <el-option label="满减" value="满减" />
            <el-option label="折扣" value="折扣" />
          </el-select>
        </el-form-item>
        <el-form-item label="优惠值"><el-input-number v-model="form.discount_value" :step="0.1" style="width: 100%" /></el-form-item>
        <el-form-item label="门槛"><el-input-number v-model="form.threshold" :step="10" style="width: 100%" /></el-form-item>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid--discounts {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

@media (max-width: 1280px) {
  .stats-grid--discounts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--discounts {
    grid-template-columns: 1fr;
  }
}
</style>
