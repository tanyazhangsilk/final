<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goSettings = () => {
  router.push('/admin/settings')
}
</script>

<template>
  <div class="page-shell">
    <el-result
      icon="info"
      title="系统设置"
      sub-title="请在系统设置中维护平台参数与规则配置。"
    >
      <template #extra>
        <el-button type="primary" @click="goSettings">进入系统设置</el-button>
      </template>
    </el-result>
  </div>
</template>
