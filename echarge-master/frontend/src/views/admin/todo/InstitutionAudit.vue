<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { IconArrowRight, IconTool } from '@tabler/icons-vue'

const route = useRoute()
const router = useRouter()

const title = computed(() => route.meta.title || '运营商入驻审核')
const description = computed(
  () =>
    route.meta.placeholderDescription ||
    '此页面待开发，将承接运营商准入、资质复核与审核流转。',
)

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }

  ElMessage.info('当前没有可返回的历史记录')
}
</script>

<template>
  <div class="placeholder-content">
    <div class="placeholder-icon">
      <IconTool :size="28" />
    </div>
    <p class="placeholder-eyebrow">业务筹备中</p>
    <h1 class="placeholder-title">{{ title }}</h1>
    <p class="placeholder-description">{{ description }}</p>

    <div class="placeholder-actions">
      <el-button type="primary" @click="goBack">
        返回上一页
        <IconArrowRight :size="16" style="margin-left: 6px;" />
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px;
  background-color: var(--el-bg-color-overlay);
  border-radius: 12px;
  box-shadow: var(--el-box-shadow-light);
  width: min(720px, 100%);
  margin: 40px auto;
}

.placeholder-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.12), rgba(54, 207, 201, 0.2));
  color: #409eff;
}

.placeholder-eyebrow {
  margin: 18px 0 8px;
  color: var(--color-text-3);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.placeholder-title {
  margin: 0;
  font-size: 28px;
  color: var(--color-text);
}

.placeholder-description {
  margin: 12px auto 0;
  max-width: 560px;
  line-height: 1.7;
  color: var(--color-text-2);
}

.placeholder-actions {
  margin-top: 24px;
}

@media (max-width: 768px) {
  .placeholder-content {
    padding: 24px 18px;
  }

  .placeholder-title {
    font-size: 24px;
  }
}
</style>
