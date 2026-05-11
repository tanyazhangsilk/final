<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <div class="empty-block">
    <el-empty :description="description">
      <template #image>
        <div class="empty-block__icon">EC</div>
      </template>
    </el-empty>
    <h4 class="empty-block__title">{{ title }}</h4>
  </div>
</template>

<style scoped>
.empty-block {
  padding: 12px 0;
  text-align: center;
}

.empty-block__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  margin: 0 auto;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(47, 116, 255, 0.9), rgba(73, 187, 174, 0.86));
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.empty-block__title {
  margin: -4px 0 0;
  color: var(--color-text);
}
</style>
