<script setup>
defineProps({
  title: {
    type: String,
    default: '数据加载未完成',
  },
  description: {
    type: String,
    default: '当前页面已优先展示可用内容，可稍后重试获取最新结果。',
  },
  compact: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['retry'])
</script>

<template>
  <div class="error-block soft-card" :class="{ 'error-block--compact': compact }">
    <div class="error-block__icon">!</div>
    <div class="error-block__content">
      <strong>{{ title }}</strong>
      <p>{{ description }}</p>
    </div>
    <div class="error-block__actions">
      <slot>
        <el-button type="primary" plain @click="$emit('retry')">重新加载</el-button>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.error-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  margin-bottom: 16px;
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(255, 244, 229, 0.92), rgba(255, 251, 235, 0.98)),
    #fff;
  border-color: rgba(217, 145, 31, 0.22);
}

.error-block--compact {
  padding: 14px 16px;
}

.error-block__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: rgba(217, 145, 31, 0.12);
  color: #b86b00;
  font-weight: 800;
  font-size: 18px;
  flex: none;
}

.error-block__content {
  flex: 1;
  min-width: 0;
}

.error-block__content strong {
  display: block;
  color: var(--color-text);
}

.error-block__content p {
  margin: 6px 0 0;
  color: var(--color-text-2);
  line-height: 1.6;
}

.error-block__actions {
  flex: none;
}

@media (max-width: 768px) {
  .error-block {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
