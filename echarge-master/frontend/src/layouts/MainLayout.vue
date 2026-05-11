<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Bell, Menu as MenuIcon, Search, SwitchButton } from '@element-plus/icons-vue'
import { IconMoonStars, IconSun } from '@tabler/icons-vue'

import {
  ROLE_LABELS,
  ROLES,
  buildMenuByRole,
  getStoredRole,
  resolveRoleDefaultRoute,
  setStoredRole,
} from '../config/permissions'

const route = useRoute()
const router = useRouter()

const collapsed = ref(false)
const drawerVisible = ref(false)
const windowWidth = ref(window.innerWidth)
const theme = ref(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')

const keepAliveNames = [
  'AdminOrders',
  'AdminOrderAbnormal',
  'AdminFinanceInvoices',
  'OperatorStations',
  'OperatorStationsChargers',
  'OperatorOrdersHistory',
  'OperatorOrdersAbnormal',
  'AdminInstitutionStations',
  'OperatorFinanceInvoices',
]

const currentRole = computed(() => route.meta?.role || getStoredRole())
const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta?.title || '运营后台')
const pageSection = computed(() => route.meta?.section || ROLE_LABELS[currentRole.value] || '业务概览')
const pageDescription = computed(() => route.meta?.description || '查看当前业务模块信息')
const roleLabel = computed(() => ROLE_LABELS[currentRole.value] || '充电运营商')
const visibleMenuGroups = computed(() => buildMenuByRole(currentRole.value))
const isMobile = computed(() => windowWidth.value < 960)
const breadcrumbs = computed(() => {
  const items = [ROLE_LABELS[currentRole.value], pageSection.value].filter(Boolean)
  if (pageTitle.value && pageTitle.value !== pageSection.value) items.push(pageTitle.value)
  return items
})

const handleResize = () => {
  windowWidth.value = window.innerWidth
  if (isMobile.value) collapsed.value = false
}

const handleMenuSelect = (path) => {
  router.push(path)
  if (isMobile.value) drawerVisible.value = false
}

const toggleTheme = () => {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('theme', theme.value)
  window.dispatchEvent(new Event('themechange'))
}

const switchRole = (role) => {
  setStoredRole(role)
  router.push(resolveRoleDefaultRoute(role))
  if (isMobile.value) drawerVisible.value = false
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  handleResize()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <el-container class="layout-root">
    <el-aside v-if="!isMobile" :width="collapsed ? '76px' : '236px'" class="layout-aside">
      <div class="brand">
        <div class="brand__mark">EC</div>
        <div v-show="!collapsed" class="brand__text">
          <strong>E-Charge 联合平台</strong>
          <span>{{ roleLabel }}控制台</span>
        </div>
      </div>

      <div class="menu-scroll">
        <section v-for="group in visibleMenuGroups" :key="group.label" class="menu-group">
          <p v-show="!collapsed" class="menu-group__label">{{ group.label }}</p>
          <el-menu
            :default-active="activeMenu"
            class="menu"
            :collapse="collapsed"
            :collapse-transition="false"
            background-color="transparent"
            text-color="var(--color-sidebar-text)"
            active-text-color="#ffffff"
            @select="handleMenuSelect"
          >
            <el-menu-item v-for="item in group.items" :key="item.index" :index="item.index">
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
          </el-menu>
        </section>
      </div>
    </el-aside>

    <el-drawer v-model="drawerVisible" direction="ltr" :size="272" :with-header="false">
      <div class="brand brand--mobile">
        <div class="brand__mark">EC</div>
        <div class="brand__text">
          <strong>E-Charge 联合平台</strong>
          <span>{{ roleLabel }}控制台</span>
        </div>
      </div>

      <div class="menu-scroll">
        <section v-for="group in visibleMenuGroups" :key="group.label" class="menu-group">
          <p class="menu-group__label">{{ group.label }}</p>
          <el-menu
            :default-active="activeMenu"
            class="menu"
            background-color="transparent"
            text-color="var(--color-sidebar-text)"
            active-text-color="#ffffff"
            @select="handleMenuSelect"
          >
            <el-menu-item v-for="item in group.items" :key="item.index" :index="item.index">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </el-menu>
        </section>
      </div>
    </el-drawer>

    <el-container class="main-shell">
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="header-action" @click="isMobile ? (drawerVisible = true) : (collapsed = !collapsed)">
            <MenuIcon />
          </el-icon>

          <div class="page-meta">
            <div class="page-breadcrumb">
              <span v-for="(item, index) in breadcrumbs" :key="`${item}-${index}`" class="page-breadcrumb__item">
                <el-icon v-if="index > 0" class="page-breadcrumb__arrow"><ArrowRight /></el-icon>
                <span>{{ item }}</span>
              </span>
            </div>
            <h2 class="page-meta__title">{{ pageTitle }}</h2>
            <p class="page-meta__sub">{{ pageDescription }}</p>
          </div>
        </div>

        <div class="header-right">
          <el-input v-if="!isMobile" placeholder="搜索订单、电站、运营商或设备编号" :prefix-icon="Search" class="search-input" />
          <el-button v-else circle :icon="Search" />

          <el-button circle class="toolbar-btn" @click="toggleTheme">
            <IconSun v-if="theme === 'dark'" :size="18" />
            <IconMoonStars v-else :size="18" />
          </el-button>

          <el-popover placement="bottom-end" :width="320" trigger="click">
            <template #reference>
              <el-button circle class="toolbar-btn">
                <el-badge :value="2">
                  <el-icon><Bell /></el-icon>
                </el-badge>
              </el-button>
            </template>
            <div class="notify-panel">
              <div class="notify-panel__item">
                <strong>系统通知</strong>
                <p>核心业务页已启用状态保留与轻量刷新，切换返回时优先展示最近结果。</p>
              </div>
              <div class="notify-panel__item">
                <strong>待办提醒</strong>
                <p>电站申请、审核、电桩配置与订单处理链路已整理为稳定演示状态。</p>
              </div>
            </div>
          </el-popover>

          <el-dropdown @command="switchRole">
            <div class="role-switcher">
              <span class="role-switcher__label">当前角色</span>
              <el-icon class="role-switcher__icon"><SwitchButton /></el-icon>
              <el-tag :type="currentRole === ROLES.ADMIN ? 'danger' : 'success'">{{ roleLabel }}</el-tag>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :command="ROLES.ADMIN">切换到平台管理员</el-dropdown-item>
                <el-dropdown-item :command="ROLES.OPERATOR">切换到充电运营商</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <div class="layout-main__inner">
          <router-view v-slot="{ Component, route: currentRoute }">
            <keep-alive :include="keepAliveNames">
              <component v-if="currentRoute.meta?.keepAlive" :is="Component" :key="currentRoute.name || currentRoute.path" />
            </keep-alive>

            <component v-if="!currentRoute.meta?.keepAlive" :is="Component" :key="currentRoute.fullPath" />
          </router-view>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-root {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.layout-aside {
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background:
    radial-gradient(circle at top left, rgba(64, 158, 255, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(7, 19, 42, 0.98), rgba(10, 26, 55, 0.98));
  transition: width 0.24s ease;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #36cfc9, #409eff);
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #fff;
}

.brand__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand__text strong {
  font-size: 14px;
  color: #fff;
}

.brand__text span {
  margin-top: 3px;
  color: var(--color-sidebar-text-soft);
  font-size: 11px;
}

.brand--mobile {
  margin: -18px -16px 0;
  background:
    radial-gradient(circle at top left, rgba(64, 158, 255, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(7, 19, 42, 0.98), rgba(10, 26, 55, 0.98));
}

.menu-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 14px 8px 16px;
}

.menu-group + .menu-group {
  margin-top: 12px;
}

.menu-group__label {
  margin: 0 0 6px;
  padding: 0 12px;
  color: var(--color-sidebar-text-soft);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.menu {
  border-right: none;
}

.menu :deep(.el-menu-item) {
  margin-bottom: 5px;
  min-height: 42px;
  border-radius: 12px;
  color: var(--color-sidebar-text) !important;
}

.menu :deep(.el-menu-item:hover) {
  background: var(--color-sidebar-hover) !important;
}

.menu :deep(.el-menu-item.is-active) {
  background: var(--color-sidebar-active) !important;
  box-shadow: 0 10px 24px rgba(64, 158, 255, 0.24);
}

.main-shell {
  min-width: 0;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 68px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(14px);
  position: relative;
  box-shadow: 0 4px 18px rgba(17, 24, 39, 0.08);
}

.layout-header::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(79, 70, 229, 0.55), rgba(54, 209, 220, 0.55));
  opacity: 0.8;
}

:root[data-theme='dark'] .layout-header {
  background: rgba(15, 23, 42, 0.82);
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  min-width: 0;
}

.header-action {
  font-size: 18px;
  cursor: pointer;
  color: var(--color-text-2);
}

.page-meta {
  min-width: 0;
}

.page-breadcrumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  margin-bottom: 4px;
  color: var(--color-text-3);
  font-size: 11px;
}

.page-breadcrumb__item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.page-breadcrumb__arrow {
  font-size: 11px;
}

.page-meta__title {
  margin: 0;
  font-size: 18px;
  color: var(--color-text);
}

.page-meta__sub {
  margin: 3px 0 0;
  color: var(--color-text-3);
  font-size: 11px;
}

.search-input {
  width: 248px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--color-border);
}

.toolbar-btn {
  color: var(--color-text-2);
}

.notify-panel {
  display: grid;
  gap: 12px;
}

.notify-panel__item {
  padding: 12px;
  border-radius: 12px;
  background: var(--color-surface-2);
}

.notify-panel__item p {
  margin: 6px 0 0;
  color: var(--color-text-3);
  line-height: 1.55;
  font-size: 12px;
}

.role-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 7px 10px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}

.role-switcher__label {
  color: var(--color-text-3);
  font-size: 11px;
}

.role-switcher__icon {
  color: var(--color-text-2);
}

.layout-main {
  padding: 16px;
  overflow-y: auto;
  background:
    radial-gradient(800px 400px at 100% -10%, rgba(64, 158, 255, 0.08), transparent 55%),
    radial-gradient(900px 460px at -10% 100%, rgba(16, 185, 129, 0.06), transparent 55%);
}

.layout-main__inner {
  max-width: min(1560px, 100%);
  margin: 0 auto;
  animation: pageReveal 320ms ease-out both;
}

.menu-scroll::-webkit-scrollbar {
  width: 8px;
}

.menu-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.menu-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
}

@media (max-width: 960px) {
  .layout-header {
    height: 64px;
    padding: 0 14px;
  }

  .layout-main {
    padding: 12px;
  }

  .page-meta__title {
    font-size: 17px;
  }

  .page-meta__sub,
  .page-breadcrumb {
    display: none;
  }
}
</style>
