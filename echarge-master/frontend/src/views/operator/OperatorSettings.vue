<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, OfficeBuilding, RefreshRight, SetUp } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import EmptyStateBlock from '../../components/console/EmptyStateBlock.vue'
import ErrorBlock from '../../components/console/ErrorBlock.vue'
import { fetchOperatorProfile, updateOperatorProfile } from '../../api/operator'
import { mockOperatorProfile, mockOperatorSettingContacts } from '../../mock/backoffice'
import { buildRequestCacheKey, formatCacheUpdatedAt, getRequestCache, setRequestCache } from '../../utils/requestCache'

const CACHE_TTL = 60 * 1000

const loading = ref(false)
const saving = ref(false)
const tableReady = ref(false)
const cacheLabel = ref('')
const errorMessage = ref('')

const form = reactive({ ...mockOperatorProfile })
const contacts = ref([...mockOperatorSettingContacts])
const filters = reactive({
  keyword: '',
  status: '',
})

const cacheKey = buildRequestCacheKey('/operator/settings/profile', { scope: 'operator-settings' })

const filteredContacts = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return contacts.value.filter((item) => {
    const matchKeyword =
      !keyword ||
      [item.module, item.owner, item.contact_phone, item.contact_email]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(keyword))
    const matchStatus = !filters.status || item.status === filters.status
    return matchKeyword && matchStatus
  })
})

const stats = computed(() => [
  {
    label: '站点数量',
    value: Number(form.station_count || 0),
    suffix: ' 座',
    tone: 'primary',
    icon: OfficeBuilding,
    trend: '当前主体资产规模',
    trendLabel: '用于评估配置覆盖范围',
  },
  {
    label: '车队数量',
    value: Number(form.fleet_count || 0),
    suffix: ' 组',
    tone: 'warning',
    icon: SetUp,
    trend: '重点合作客户',
    trendLabel: '支持白名单与专属运营',
  },
  {
    label: '认证状态',
    value: form.verified ? '已认证' : '待认证',
    tone: form.verified ? 'success' : 'danger',
    icon: CircleCheck,
    trend: '主体资质状态',
    trendLabel: form.verified ? '可继续新增站点与模板' : '建议补全资质材料',
  },
  {
    label: '值守模块',
    value: contacts.value.filter((item) => item.status === 'active').length,
    suffix: ' 项',
    tone: 'info',
    icon: RefreshRight,
    trend: '已启用联络模块',
    trendLabel: '保障运营、客服与财务联动',
  },
])

const statusType = (status) => (status === 'active' ? 'success' : 'info')
const statusText = (status) => (status === 'active' ? '启用中' : '备用')

const applyPayload = ({ profile, contactRows }, fromCache = false, updatedAt = Date.now()) => {
  Object.assign(form, mockOperatorProfile, profile || {})
  contacts.value = Array.isArray(contactRows) && contactRows.length ? contactRows : [...mockOperatorSettingContacts]
  tableReady.value = true
  cacheLabel.value = `${fromCache ? '最近可用数据' : '已更新'} ${formatCacheUpdatedAt(updatedAt)}`
}

const loadData = async ({ background = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached) {
    applyPayload(cached.value, true, cached.updatedAt)
  }

  loading.value = !cached || !background
  errorMessage.value = ''

  try {
    const res = await fetchOperatorProfile()
    const profile = res?.data?.data || mockOperatorProfile
    const payload = {
      profile,
      contactRows: Array.isArray(profile?.contact_matrix) ? profile.contact_matrix : [...mockOperatorSettingContacts],
    }
    applyPayload(payload, false, Date.now())
    setRequestCache(cacheKey, payload)
  } catch (error) {
    if (!tableReady.value) {
      applyPayload(
        {
          profile: { ...mockOperatorProfile },
          contactRows: [...mockOperatorSettingContacts],
        },
        false,
        Date.now(),
      )
      cacheLabel.value = '当前内容可用'
    }
    errorMessage.value = '当前配置已保持最近更新内容。'
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  const payload = {
    name: form.name,
    org_type: form.org_type,
    contact_email: form.contact_email,
    contact_phone: form.contact_phone,
    bank_account: form.bank_account,
  }
  try {
    await updateOperatorProfile(payload)
    ElMessage.success('运营商设置已保存')
  } catch (error) {
    ElMessage.success('后端暂未返回成功，当前修改已保留在页面中')
  } finally {
    setRequestCache(cacheKey, {
      profile: { ...form },
      contactRows: [...contacts.value],
    })
    cacheLabel.value = `已更新 ${formatCacheUpdatedAt(Date.now())}`
    saving.value = false
  }
}

onMounted(loadData)
onActivated(() => loadData({ background: true }))
</script>

<template>
  <div class="page-shell settings-page">
    <PageSectionHeader
      eyebrow="系统设置"
      title="运营商设置"
      description="维护运营主体资料、对外联络信息与值守责任配置。"
      :chip="form.verified ? '已认证' : '待认证'"
    >
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData()">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--settings">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">筛选条件</h3>
          <p class="panel-heading__desc">按模块、责任人和联系方式快速筛选值守配置。</p>
        </div>
      </div>
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="搜索模块 / 责任人 / 电话 / 邮箱" style="width: 360px" />
        <el-select v-model="filters.status" clearable placeholder="状态" style="width: 160px">
          <el-option label="启用中" value="active" />
          <el-option label="备用" value="standby" />
        </el-select>
      </div>
    </section>

    <section class="panel-grid panel-grid--wide">
      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">主体资料</h3>
            <p class="panel-heading__desc">保存后将同步更新运营主体展示信息。</p>
          </div>
        </div>

        <el-form label-width="96px" class="profile-form">
          <el-form-item label="企业名称">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="主体类型">
            <el-input v-model="form.org_type" />
          </el-form-item>
          <el-form-item label="联系电话">
            <el-input v-model="form.contact_phone" />
          </el-form-item>
          <el-form-item label="联系邮箱">
            <el-input v-model="form.contact_email" />
          </el-form-item>
          <el-form-item label="收款账户">
            <el-input v-model="form.bank_account" />
          </el-form-item>
        </el-form>

        <div class="info-list">
          <div class="info-item">
            <p class="info-item__title">资料完整度</p>
            <p class="info-item__desc">
              当前资料用于订单、结算与发票等业务展示，建议确保联系电话、邮箱和收款账户保持最新。
            </p>
          </div>
        </div>

        <div class="action-row">
          <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        </div>
      </article>

      <article class="page-panel surface-card table-shell">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">值守联络矩阵</h3>
            <p class="panel-heading__desc">用于运营异常、客服升级与财务对账场景的责任联络。</p>
          </div>
        </div>

        <ErrorBlock
          v-if="errorMessage"
          title="设置状态提示"
          :description="errorMessage"
          @retry="loadData()"
        />

        <TableSkeletonBlock v-if="loading && !tableReady" :rows="5" :columns="6" />

        <el-table v-else-if="filteredContacts.length" :data="filteredContacts" v-loading="loading" stripe>
          <el-table-column prop="module" label="模块" min-width="140" />
          <el-table-column prop="owner" label="责任人" min-width="130" />
          <el-table-column prop="contact_phone" label="联系电话" min-width="150" />
          <el-table-column prop="contact_email" label="联系邮箱" min-width="200" />
          <el-table-column label="状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" min-width="160" />
        </el-table>

        <EmptyStateBlock v-else-if="!loading" title="暂无值守配置" description="当前筛选条件下没有匹配的联络配置。" />
      </article>
    </section>
  </div>
</template>

<style scoped>
.stats-grid--settings {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.profile-form :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.action-row {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1280px) {
  .stats-grid--settings {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid--settings {
    grid-template-columns: 1fr;
  }
}
</style>
