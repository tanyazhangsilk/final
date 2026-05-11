<script setup>
import { computed, onActivated, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import { fetchSystemParams, updateSystemParams } from '../../api/admin'
import { mockSystemParams } from '../../mock/backoffice'
import { readLocalState, writeLocalState } from '../../utils/localState'
import { buildRequestCacheKey, formatCacheLabel, getRequestCache, setRequestCache, shouldRefreshRequestCache } from '../../utils/requestCache'

const STORAGE_KEY = 'echarge-admin-system-params'
const CACHE_TTL = 60 * 1000

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const cacheLabel = ref('')

const form = reactive(readLocalState(STORAGE_KEY, mockSystemParams))

const tabs = [
  { key: 'basic', label: '基础参数', path: '/admin/settings/params/basic' },
  { key: 'billing', label: '计费参数', path: '/admin/settings/params/billing' },
  { key: 'settlement', label: '清分参数', path: '/admin/settings/params/settlement' },
  { key: 'notification', label: '通知参数', path: '/admin/settings/params/notification' },
]

const activeTab = computed(() => {
  const current = route.meta?.settingsSection
  return tabs.find((item) => item.key === current)?.key || 'basic'
})

const tabMeta = computed(() => tabs.find((item) => item.key === activeTab.value) || tabs[0])
const cacheKey = computed(() => buildRequestCacheKey('/admin/settings/params', { section: activeTab.value }))

const stats = computed(() => [
  {
    label: '自动审核开关',
    value: form.operator_auto_approve ? '已开启' : '未开启',
    tone: form.operator_auto_approve ? 'success' : 'warning',
  },
  {
    label: '平台清分比例',
    value: Number(form.settlement_platform_rate || 0),
    suffix: '%',
    tone: 'primary',
  },
  {
    label: '异常工单时限',
    value: Number(form.abnormal_order_sla_minutes || 0),
    suffix: ' 分钟',
    tone: 'danger',
  },
  {
    label: '客服热线',
    value: form.support_phone || '-',
    tone: 'info',
  },
])

const applyForm = (payload = {}, updatedAt = Date.now()) => {
  Object.assign(form, mockSystemParams, payload || {})
  writeLocalState(STORAGE_KEY, form)
  cacheLabel.value = formatCacheLabel(updatedAt)
}

const loadData = async ({ background = false, force = false } = {}) => {
  const cached = getRequestCache(cacheKey.value, { ttl: CACHE_TTL, allowStale: true })
  if (cached && !force) {
    applyForm(cached.value, cached.updatedAt)
  }

  loading.value = force || !cached || !background
  try {
    const res = await fetchSystemParams()
    const payload = res?.data?.data || mockSystemParams
    applyForm(payload, Date.now())
    setRequestCache(cacheKey.value, { ...form })
  } catch (error) {
    if (!cacheLabel.value) {
      applyForm(readLocalState(STORAGE_KEY, mockSystemParams), Date.now())
    }
  } finally {
    loading.value = false
  }
}

const save = async () => {
  loading.value = true
  try {
    await updateSystemParams({ ...form })
    ElMessage.success('系统参数已保存')
  } catch (error) {
    writeLocalState(STORAGE_KEY, form)
    ElMessage.success('后端暂未返回成功，已先保存当前系统参数')
  } finally {
    setRequestCache(cacheKey.value, { ...form })
    cacheLabel.value = formatCacheLabel(Date.now())
    loading.value = false
  }
}

const switchTab = (path) => {
  if (route.path !== path) {
    router.push(path)
  }
}

onMounted(() => loadData({ background: true }))
onActivated(() => {
  if (shouldRefreshRequestCache(cacheKey.value, CACHE_TTL)) {
    loadData({ background: true })
  }
})
</script>

<template>
  <div class="page-shell system-params-page">
    <PageSectionHeader eyebrow="系统配置" title="系统参数配置" description="维护平台基础审核、计费、清分与通知参数。" :chip="tabMeta.label">
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData({ force: true })">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--params">
      <MetricCard
        v-for="item in stats"
        :key="item.label"
        :label="item.label"
        :value="item.value"
        :suffix="item.suffix"
        :tone="item.tone"
      />
    </section>

    <section class="page-panel surface-card tab-shell">
      <div class="tab-row">
        <button
          v-for="item in tabs"
          :key="item.key"
          type="button"
          class="tab-pill"
          :class="{ 'tab-pill--active': activeTab === item.key }"
          @click="switchTab(item.path)"
        >
          {{ item.label }}
        </button>
      </div>
    </section>

    <section v-if="activeTab === 'basic'" class="page-panel surface-card">
      <div class="form-grid">
        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">准入流程</h3>
              <p class="panel-heading__desc">控制运营商入驻与站点发布流程。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="运营商自动通过">
              <el-switch v-model="form.operator_auto_approve" />
            </el-form-item>
            <el-form-item label="电站审核通过后自动公开">
              <el-switch v-model="form.station_auto_publish" />
            </el-form-item>
            <el-form-item label="公开站点需要复审">
              <el-switch v-model="form.station_public_requires_review" />
            </el-form-item>
          </el-form>
        </div>

        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">客服信息</h3>
              <p class="panel-heading__desc">配置平台对外服务邮箱与热线。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="服务邮箱">
              <el-input v-model="form.support_email" />
            </el-form-item>
            <el-form-item label="服务热线">
              <el-input v-model="form.support_phone" />
            </el-form-item>
          </el-form>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'billing'" class="page-panel surface-card">
      <div class="form-grid">
        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">票据与退款</h3>
              <p class="panel-heading__desc">控制发票自动审核阈值与退款限制。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="发票自动审核阈值（元）">
              <el-input-number v-model="form.invoice_auto_approve_limit" :min="0" :step="50" style="width: 100%" />
            </el-form-item>
            <el-form-item label="用户每日退款上限（次）">
              <el-input-number v-model="form.user_refund_limit_per_day" :min="1" :step="1" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>

        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">异常处理</h3>
              <p class="panel-heading__desc">控制异常订单处理时限。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="异常订单处理时限（分钟）">
              <el-input-number v-model="form.abnormal_order_sla_minutes" :min="5" :step="5" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'settlement'" class="page-panel surface-card">
      <div class="form-grid">
        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">平台清分</h3>
              <p class="panel-heading__desc">配置平台分成比例与起结金额门槛。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="平台清分比例（%）">
              <el-input-number v-model="form.settlement_platform_rate" :min="1" :max="100" style="width: 100%" />
            </el-form-item>
            <el-form-item label="最低结算金额（元）">
              <el-input-number v-model="form.settlement_minimum_amount" :min="0" :step="50" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>

        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">结算周期</h3>
              <p class="panel-heading__desc">控制自动清分的周期配置。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="T+N 天结算">
              <el-input-number v-model="form.settlement_cycle_days" :min="1" :max="31" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>
      </div>
    </section>

    <section v-else class="page-panel surface-card">
      <div class="form-grid">
        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">通知渠道</h3>
              <p class="panel-heading__desc">维护邮件、短信和发票通知开关。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="启用邮件通知">
              <el-switch v-model="form.notification_email_enabled" />
            </el-form-item>
            <el-form-item label="启用短信通知">
              <el-switch v-model="form.notification_sms_enabled" />
            </el-form-item>
            <el-form-item label="启用发票通知">
              <el-switch v-model="form.invoice_notice_enabled" />
            </el-form-item>
          </el-form>
        </div>

        <div class="soft-card section-card">
          <div class="panel-heading">
            <div>
              <h3 class="panel-heading__title">异常通知对象</h3>
              <p class="panel-heading__desc">维护异常订单通知岗位范围。</p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="通知岗位">
              <el-input v-model="form.abnormal_order_notify_roles" placeholder="例如：平台运营、财务审核、客服值班" />
            </el-form-item>
          </el-form>
        </div>
      </div>
    </section>

    <section class="page-panel surface-card footer-shell">
      <div class="footer-actions">
        <el-button type="primary" :loading="loading" @click="save">保存参数</el-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.stats-grid--params {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.tab-shell {
  padding: 16px;
}

.tab-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tab-pill {
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.82);
  color: var(--text-primary, #0f172a);
  border-radius: 999px;
  padding: 10px 18px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-pill--active {
  border-color: rgba(59, 130, 246, 0.24);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.16), rgba(14, 165, 233, 0.08));
  color: #1d4ed8;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.section-card {
  padding: 16px;
}

.footer-shell {
  padding: 16px;
}

@media (max-width: 1280px) {
  .stats-grid--params,
  .form-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid--params,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
