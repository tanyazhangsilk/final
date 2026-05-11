<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

import EmptyStateBlock from './EmptyStateBlock.vue'

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  items: {
    type: Array,
    default: () => [],
  },
  total: {
    type: [String, Number],
    default: '',
  },
  totalLabel: {
    type: String,
    default: '总量',
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const chartRef = ref(null)
let chartInstance = null

const palette = ['#2f74ff', '#22a06b', '#e19a2b', '#7c8ba1', '#d84f57']
const hasData = computed(() => props.items.length > 0)

const renderChart = () => {
  if (!chartRef.value || !hasData.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  chartInstance.setOption({
    animationDuration: 500,
    color: props.items.map((item, index) => item.color || palette[index % palette.length]),
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderWidth: 0,
      textStyle: {
        color: '#fff',
      },
      formatter: ({ name, value, percent }) => `${name}<br/>${value}（${percent}%）`,
    },
    series: [
      {
        type: 'pie',
        radius: ['56%', '76%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        label: {
          show: false,
        },
        labelLine: {
          show: false,
        },
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 3,
        },
        data: props.items.map((item) => ({
          value: item.value,
          name: item.label,
        })),
      },
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '42%',
        style: {
          text: `${props.total || ''}`,
          textAlign: 'center',
          fill: '#0f172a',
          fontSize: 24,
          fontWeight: 700,
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '56%',
        style: {
          text: props.totalLabel,
          textAlign: 'center',
          fill: '#7b8794',
          fontSize: 12,
        },
      },
    ],
  })
}

const resizeChart = () => {
  chartInstance?.resize()
}

watch(
  () => props.items,
  async () => {
    if (!hasData.value) return
    await nextTick()
    renderChart()
  },
  { deep: true },
)

watch(
  () => props.loading,
  async (value) => {
    if (!value) {
      await nextTick()
      renderChart()
    }
  },
)

onMounted(async () => {
  await nextTick()
  renderChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<template>
  <article class="page-panel surface-card distribution-panel donut-panel" v-loading="loading">
    <div class="panel-heading">
      <div>
        <h3 class="panel-heading__title">{{ title }}</h3>
        <p v-if="subtitle" class="panel-heading__desc">{{ subtitle }}</p>
      </div>
    </div>

    <template v-if="hasData">
      <div ref="chartRef" class="distribution-panel__chart"></div>
      <div class="distribution-panel__legend">
        <div v-for="(item, index) in items" :key="item.label" class="distribution-panel__legend-item">
          <span class="distribution-panel__dot" :style="{ background: item.color || palette[index % palette.length] }"></span>
          <span class="distribution-panel__name">{{ item.label }}</span>
          <strong class="distribution-panel__value">{{ item.value }}</strong>
        </div>
      </div>
    </template>

    <EmptyStateBlock
      v-else-if="!loading"
      title="暂无分布数据"
      description="当前没有状态分布可展示，后续可直接对接接口统计。"
    />
  </article>
</template>

<style scoped>
.distribution-panel {
  min-height: 360px;
}

.distribution-panel__chart {
  width: 100%;
  height: 220px;
  animation: donutReveal 460ms ease both;
}

.distribution-panel__legend {
  display: grid;
  gap: 10px;
}

.distribution-panel__legend-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--color-surface-3);
  transition: transform var(--motion-fast) ease, box-shadow var(--motion-fast) ease;
}

.distribution-panel__legend-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(17, 24, 39, 0.10);
}

.distribution-panel__dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.distribution-panel__name {
  color: var(--color-text-2);
  font-size: 13px;
}

.distribution-panel__value {
  color: var(--color-text);
}

.donut-panel {
  position: relative;
  overflow: hidden;
}

.donut-panel::after {
  content: '';
  position: absolute;
  right: -70px;
  top: -70px;
  width: 180px;
  height: 180px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(64, 158, 255, 0.18), transparent 70%);
  pointer-events: none;
}

@keyframes donutReveal {
  from {
    opacity: 0;
    transform: scale(0.97);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
