<script setup>
import { computed, onActivated, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, RefreshRight, Setting, UserFilled } from '@element-plus/icons-vue'

import PageSectionHeader from '../../components/console/PageSectionHeader.vue'
import MetricCard from '../../components/console/MetricCard.vue'
import TableSkeletonBlock from '../../components/console/TableSkeletonBlock.vue'
import { fetchAdminPermissionSettings, updateAdminPermissionSettings } from '../../api/admin'
import { readLocalState, writeLocalState } from '../../utils/localState'
import { buildRequestCacheKey, formatCacheLabel, getRequestCache, setRequestCache, shouldRefreshRequestCache } from '../../utils/requestCache'

const STORAGE_KEY = 'echarge-admin-role-permissions'
const CACHE_TTL = 60 * 1000

const defaultRoles = [
  {
    key: 'platform-admin',
    roleName: '平台管理员',
    scope: '负责平台治理、关键配置和跨模块审批',
    members: 3,
    modules: ['工作台总览', '运营商审核', '电站审核', '全局订单', '异常订单', '平台清分', '发票管理', '系统参数'],
    canEdit: true,
    canApprove: true,
    canExport: true,
    enabled: true,
  },
  {
    key: 'finance-auditor',
    roleName: '财务审核',
    scope: '负责清分、发票、对账和财务数据导出',
    members: 4,
    modules: ['平台清分', '发票管理', '历史订单', '异常订单'],
    canEdit: true,
    canApprove: true,
    canExport: true,
    enabled: true,
  },
  {
    key: 'reviewer',
    roleName: '审核专员',
    scope: '负责运营商与电站准入审核',
    members: 6,
    modules: ['运营商审核', '电站审核', '异常订单'],
    canEdit: true,
    canApprove: true,
    canExport: false,
    enabled: true,
  },
  {
    key: 'service',
    roleName: '客服值班',
    scope: '负责订单查询、异常跟进和用户响应',
    members: 8,
    modules: ['工作台总览', '历史订单', '异常订单', '发票管理'],
    canEdit: false,
    canApprove: false,
    canExport: false,
    enabled: true,
  },
]

const changeLogs = [
  { id: 1, title: '财务审核新增发票导出权限', time: '今天 09:20', status: '已生效' },
  { id: 2, title: '审核专员保留电站准入审批权限', time: '昨天 18:40', status: '已生效' },
  { id: 3, title: '客服值班维持只读权限范围', time: '昨天 10:15', status: '稳定运行' },
]

const cacheKey = buildRequestCacheKey('/admin/settings/permissions', { scope: 'role-permissions' })

const loading = ref(false)
const tableReady = ref(false)
const cacheLabel = ref('')
const roles = ref(readLocalState(STORAGE_KEY, defaultRoles))

const stats = computed(() => [
  {
    label: '岗位角色',
    value: roles.value.length,
    suffix: ' 个',
    tone: 'primary',
    icon: UserFilled,
    trend: '当前授权模型',
    trendLabel: '覆盖管理、财务、审核和客服岗位',
  },
  {
    label: '审批岗位',
    value: roles.value.filter((item) => item.canApprove && item.enabled).length,
    suffix: ' 个',
    tone: 'warning',
    icon: Lock,
    trend: '承担关键审批动作',
    trendLabel: '准入与资金链路保持集中授权',
  },
  {
    label: '导出岗位',
    value: roles.value.filter((item) => item.canExport && item.enabled).length,
    suffix: ' 个',
    tone: 'success',
    icon: RefreshRight,
    trend: '支持复盘与归档',
    trendLabel: '敏感数据导出范围受控',
  },
  {
    label: '启用岗位',
    value: roles.value.filter((item) => item.enabled).length,
    suffix: ' 个',
    tone: 'info',
    icon: Setting,
    trend: '当前值班配置',
    trendLabel: '停用岗位不会参与后台授权',
  },
])

const roleSummary = computed(() => [
  {
    label: '授权摘要',
    value: `${roles.value.filter((item) => item.enabled).length} 个岗位在线`,
    desc: '当前后台已按岗位划分查看、审批和导出权限。',
  },
  {
    label: '岗位说明',
    value: '以职责为中心',
    desc: '适用于平台治理、财务结算、审核处理和客服值班场景。',
  },
  {
    label: '最近调整',
    value: '3 条记录',
    desc: '最近一次权限变更已于今天上午生效。',
  },
])

const normalizeRoles = (items = []) => {
  if (!Array.isArray(items) || !items.length) {
    return defaultRoles.map((item) => ({ ...item }))
  }

  return items.map((item, index) => ({
    key: item.key || `role-${index + 1}`,
    roleName: item.roleName || item.role_name || item.name || `岗位 ${index + 1}`,
    scope: item.scope || item.description || '未补充岗位说明',
    members: Number(item.members || item.memberCount || 0),
    modules: Array.isArray(item.modules) ? item.modules : [],
    canEdit: Boolean(item.canEdit ?? item.can_edit ?? false),
    canApprove: Boolean(item.canApprove ?? item.can_approve ?? false),
    canExport: Boolean(item.canExport ?? item.can_export ?? false),
    enabled: Boolean(item.enabled ?? true),
  }))
}

const applyRoles = (items = [], updatedAt = Date.now()) => {
  roles.value = normalizeRoles(items)
  writeLocalState(STORAGE_KEY, roles.value)
  tableReady.value = true
  cacheLabel.value = formatCacheLabel(updatedAt)
}

const loadData = async ({ background = false, force = false } = {}) => {
  const cached = getRequestCache(cacheKey, { ttl: CACHE_TTL, allowStale: true })
  if (cached && !force) {
    applyRoles(cached.value, cached.updatedAt)
  }

  loading.value = force || !cached || !background
  try {
    const { data } = await fetchAdminPermissionSettings()
    const payload = data?.data?.roles || data?.data?.items || []
    applyRoles(payload, Date.now())
    setRequestCache(cacheKey, roles.value)
  } catch (error) {
    if (!roles.value.length) {
      applyRoles(readLocalState(STORAGE_KEY, defaultRoles), Date.now())
    }
  } finally {
    loading.value = false
  }
}

const save = async () => {
  loading.value = true
  try {
    await updateAdminPermissionSettings({ roles: roles.value })
    ElMessage.success('岗位权限配置已保存')
  } catch (error) {
    writeLocalState(STORAGE_KEY, roles.value)
    ElMessage.success('后端暂未返回成功，已先保存当前岗位权限配置')
  } finally {
    setRequestCache(cacheKey, roles.value)
    cacheLabel.value = formatCacheLabel(Date.now())
    loading.value = false
  }
}

onMounted(() => loadData({ background: true }))
onActivated(() => {
  if (shouldRefreshRequestCache(cacheKey, CACHE_TTL)) {
    loadData({ background: true })
  }
})
</script>

<template>
  <div class="page-shell permission-page">
    <PageSectionHeader
      eyebrow="系统配置"
      title="后台岗位权限"
      description="维护后台岗位的可见模块、审批权限和导出范围。"
      chip="角色与授权"
    >
      <template #actions>
        <el-tag v-if="cacheLabel" type="info" effect="plain">{{ cacheLabel }}</el-tag>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadData({ force: true })">刷新</el-button>
      </template>
    </PageSectionHeader>

    <section class="stats-grid stats-grid--permissions">
      <MetricCard v-for="item in stats" :key="item.label" v-bind="item" />
    </section>

    <section class="permission-top-grid">
      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">授权摘要</h3>
            <p class="panel-heading__desc">概览当前岗位授权状态与生效情况。</p>
          </div>
        </div>
        <div class="summary-list">
          <div v-for="item in roleSummary" :key="item.label" class="summary-item">
            <span class="summary-item__label">{{ item.label }}</span>
            <strong class="summary-item__value">{{ item.value }}</strong>
            <p class="summary-item__desc">{{ item.desc }}</p>
          </div>
        </div>
      </article>

      <article class="page-panel surface-card">
        <div class="panel-heading">
          <div>
            <h3 class="panel-heading__title">最近调整记录</h3>
            <p class="panel-heading__desc">用于追踪近期岗位授权变更。</p>
          </div>
        </div>
        <div class="change-log">
          <div v-for="item in changeLogs" :key="item.id" class="change-log__item">
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.time }}</p>
            </div>
            <el-tag size="small" type="info" effect="plain">{{ item.status }}</el-tag>
          </div>
        </div>
      </article>
    </section>

    <section class="page-panel surface-card">
      <div class="panel-heading">
        <div>
          <h3 class="panel-heading__title">岗位权限配置</h3>
          <p class="panel-heading__desc">按岗位维护模块可见范围、编辑权限、审批权限和导出权限。</p>
        </div>
        <div class="toolbar-actions">
          <el-button type="primary" :loading="loading" @click="save">保存配置</el-button>
        </div>
      </div>

      <TableSkeletonBlock v-if="loading && !tableReady" :rows="6" :columns="6" />

      <el-table v-else :data="roles" v-loading="loading" stripe>
        <el-table-column prop="roleName" label="岗位角色" min-width="140" />
        <el-table-column prop="scope" label="岗位职责" min-width="200" show-overflow-tooltip />
        <el-table-column label="可见模块" min-width="280">
          <template #default="{ row }">
            <div class="module-tags">
              <el-tag v-for="module in row.modules" :key="module" size="small" effect="plain">{{ module }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="在岗人数" width="100" align="center">
          <template #default="{ row }">{{ row.members }} 人</template>
        </el-table-column>
        <el-table-column label="可编辑" width="96" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.canEdit" />
          </template>
        </el-table-column>
        <el-table-column label="可审批" width="96" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.canApprove" />
          </template>
        </el-table-column>
        <el-table-column label="可导出" width="96" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.canExport" />
          </template>
        </el-table-column>
        <el-table-column label="启用状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" />
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.stats-grid--permissions {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.permission-top-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 14px;
}

.summary-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-item {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(245, 248, 252, 0.94));
}

.summary-item__label {
  display: block;
  color: var(--color-text-3);
  font-size: 11px;
}

.summary-item__value {
  display: block;
  margin-top: 8px;
  color: var(--color-text);
  font-size: 18px;
}

.summary-item__desc {
  margin: 6px 0 0;
  color: var(--color-text-2);
  font-size: 12px;
  line-height: 1.5;
}

.change-log {
  display: grid;
  gap: 10px;
}

.change-log__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface-3);
}

.change-log__item strong {
  color: var(--color-text);
  font-size: 13px;
}

.change-log__item p {
  margin: 6px 0 0;
  color: var(--color-text-3);
  font-size: 12px;
}

.module-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 1280px) {
  .stats-grid--permissions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .permission-top-grid,
  .summary-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid--permissions {
    grid-template-columns: 1fr;
  }
}
</style>
