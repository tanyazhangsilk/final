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
  data: {
    type: Array,
    default: () => [],
  },
  xField: {
    type: String,
    default: 'date',
  },
  yField: {
    type: String,
    required: true,
  },
  valueFormatter: {
    type: Function,
    default: (value) => value,
  },
  color: {
    type: String,
    default: '#2f74ff',
  },
  areaColor: {
    type: String,
    default: 'rgba(47, 116, 255, 0.16)',
  },
  smooth: {
    type: Boolean,
    default: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const chartRef = ref(null)
let chartInstance = null

const hasData = computed(() => props.data.length > 0)

const renderChart = () => {
  if (!chartRef.value || !hasData.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  chartInstance.setOption({
    animationDuration: 500,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderWidth: 0,
      padding: [10, 12],
      textStyle: {
        color: '#fff',
      },
      formatter: (params) => {
        const point = params?.[0]
        if (!point) return ''
        return `${point.axisValue}<br/>${props.title}：${props.valueFormatter(point.data)}`
      },
    },
    grid: {
      left: 18,
      right: 18,
      top: 28,
      bottom: 12,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.35)',
        },
      },
      axisLabel: {
        color: '#7b8794',
      },
      data: props.data.map((item) => item[props.xField]),
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.16)',
        },
      },
      axisLabel: {
        color: '#94a3b8',
      },
    },
    series: [
      {
        type: 'line',
        smooth: props.smooth,
        symbol: 'circle',
        symbolSize: 8,
        data: props.data.map((item) => item[props.yField]),
        lineStyle: {
          width: 3,
          color: props.color,
        },
        itemStyle: {
          color: props.color,
          borderColor: '#ffffff',
          borderWidth: 2,
        },
        areaStyle: {
          color: props.areaColor,
        },
      },
    ],
  })
}

const resizeChart = () => {
  chartInstance?.resize()
}

watch(
  () => props.data,
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
  <article class="page-panel surface-card chart-panel trend-panel" v-loading="loading">
    <div class="panel-heading">
      <div>
        <h3 class="panel-heading__title">{{ title }}</h3>
        <p v-if="subtitle" class="panel-heading__desc">{{ subtitle }}</p>
      </div>
    </div>

    <div v-if="hasData" ref="chartRef" class="chart-panel__canvas"></div>
    <EmptyStateBlock
      v-else-if="!loading"
      title="暂无图表数据"
      description="当前时间范围内没有可展示的统计数据，后续接入接口后可直接替换为真实返回值。"
    />
  </article>
</template>

<style scoped>
.chart-panel {
  min-height: 340px;
}

.chart-panel__canvas {
  width: 100%;
  height: 260px;
  animation: chartReveal 460ms ease both;
}

.trend-panel {
  position: relative;
  overflow: hidden;
}

.trend-panel::after {
  content: '';
  position: absolute;
  inset: auto 16px 0;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(79, 70, 229, 0.6), rgba(54, 209, 220, 0.6));
}

@keyframes chartReveal {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
