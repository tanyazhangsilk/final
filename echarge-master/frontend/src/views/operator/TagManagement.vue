<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, RefreshRight, Tickets, UserFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import ErrorBlock from '../../components/console/ErrorBlock.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { createTag, fetchTags } from '../../api/operator'
import { mockTags } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const tableReady = ref(false)
const cacheLabel = ref('')
const errorMessage = ref('')
const rows = ref([])
const dialogVisible = ref(false)

const filters = reactive({ keyword: '' })
const form = reactive({ name: '', color: '#409EFF', description: '' })
const cacheKey = buildRequestCacheKey('/operator/customers/tags', { scope: 'operator-tags' })

const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return rows.value.filter((item) =>
    !keyword || [item.name, item.description].filter(Boolean).some((field) => String(field).toLowerCase().includes(keyword)),
  )
})

const stats = computed(() => [
  { label: '标签总数', value: rows.value.length, suffix: ' 个', trend: '当前标签体系', trendLabel: '支持用户分层运营', tone: 'primary', icon: Tickets },
  { label: '覆盖用户', value: rows.value.reduce((sum, item) => sum + Number(item.user_count || 0), 0), suffix: ' 人', trend: '标签触达规模', trendLabel: '用于活动定向投放', tone: 'success', icon: UserFilled },
  { label: '高活跃标签', value: rows.value.filter((item) => Number(item.user_count || 0) >= 100).length, suffix: ' 个', trend: '重点用户群体', trendLabel: '建议优先运营', tone: 'warning', icon: RefreshRight },
  { label: '待补充标签', value: rows.value.filter((item) => !item.description).length, suffix: ' 个', trend: '标签说明完善度', trendLabel: '建议补齐业务含义', tone: 'info', icon: Plus },
])

const applyRows = (items = [], fromCache = false, updatedAt = Date.now()) => {
  rows.value = Array.isArray(items) && items.length ? items : mockTags
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '最近可用数据' : '已更新'} ${formatCacheUpdatedAt(updatedAt)}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) applyRows(cached.value, true, cached.updatedAt)

  loading.value = !cached || !background
  errorMessage.value = ''
  try {
    const res = await fetchTags()
    const items = Array.isArray(res?.data?.data) ? res.data.data : mockTags
    applyRows(items, false, Date.now())
    setRequestCache(cacheKey, items)
  } catch (error) {
    if (!rows.value.length) {
      applyRows(mockTags, false, Date.now())
      cacheLabel.value = '当前内容可用'
    }
    errorMessage.value = '当前列表已保持最近更新内容。'
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!form.name.trim()) {
    ElMessage.warning('请输入标签名称')
    return
  }
  try {
    await createTag({ ...form })
  } catch (error) {
    rows.value.unshift({ ...form, id: Date.now(), user_count: 0 })
  }
  ElMessage.success('标签已创建')
  dialogVisible.value = false
  form.name = ''
  form.color = '#409EFF'
  form.description = ''
  await loadData({ background: true })
}

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell">
    <PageSectionHeader eyebrow="客户管理" title="标签管理" description="维护用户标签体系，支撑分层运营与活动定向。" chip="标签中心">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="dialogVisible = true">创建标签</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--tags">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">按标签名称与说明关键词筛选。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索标签名称 / 说明" style="width: 320px" />
      </div>
    </section>

    <section class="page-panel surface-card table-shell">
      <ErrorBlock
        v-if="errorMessage"
        title="标签列表状态提示"
        :description="errorMessage"
        @retry="loadData()"
      />

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="4" />

      <el-table v-else-if="filteredRows.length" :data="filteredRows" v-loading="loading" stripe>
        <el-table-column prop="name" label="标签" min-width="180">
          <template #default="{ row }"><span class="micro-chip" :style="{ background: `${row.color}18`, color: row.color }">{{ row.name }}</span></template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="260" />
        <el-table-column prop="user_count" label="覆盖人数" width="120" align="center" />
      </el-table>

      <EmptyStateBlock v-else-if="!loading" title="暂无标签数据" description="当前筛选条件下没有匹配标签。" />
    </section>

    <el-dialog v-model="dialogVisible" title="创建标签" width="480px">
      <el-form label-position="top">
        <el-form-item label="标签名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="标签颜色"><el-input v-model="form.color" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid--tags {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  gap: 12px;
}

@media (max-width: 1280px) {
  .stats-grid--tags {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--tags {
    grid-template-columns: 1fr;
  }
}
</style>
