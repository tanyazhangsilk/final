<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { IconArrowRight, IconTool } from '@tabler/icons-vue'

const route = useRoute()
const router = useRouter()

const title = computed(() => route.meta.title || '页面待开发')
const description = computed(
  () =>
    route.meta.placeholderDescription ||
    '当前页面已经预留到正式导航结构中，后续可以直接在这个位置继续接真实功能。',
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
  <div class="placeholder">
    <section class="placeholder__card surface-card">
      <div class="placeholder__icon">
        <IconTool :size="28" />
      </div>
      <p class="placeholder__eyebrow">业务筹备中</p>
      <h1 class="placeholder__title">{{ title }}</h1>
      <p class="placeholder__description">{{ description }}</p>

      <div class="placeholder__actions">
        <el-button type="primary" @click="goBack">
          返回上一页
          <IconArrowRight :size="16" style="margin-left: 6px;" />
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.placeholder {
  min-height: calc(100vh - 156px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder__card {
  width: min(720px, 100%);
  padding: 32px;
  text-align: center;
}

.placeholder__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.12), rgba(54, 207, 201, 0.2));
  color: #409eff;
}

.placeholder__eyebrow {
  margin: 18px 0 8px;
  color: var(--color-text-3);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.placeholder__title {
  margin: 0;
  font-size: 28px;
  color: var(--color-text);
}

.placeholder__description {
  margin: 12px auto 0;
  max-width: 560px;
  line-height: 1.7;
  color: var(--color-text-2);
}

.placeholder__actions {
  margin-top: 24px;
}

@media (max-width: 768px) {
  .placeholder__card {
    padding: 24px 18px;
  }

  .placeholder__title {
    font-size: 24px;
  }
}
</style>
