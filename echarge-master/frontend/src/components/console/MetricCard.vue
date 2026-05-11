<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    required: true,
  },
  prefix: {
    type: String,
    default: '',
  },
  suffix: {
    type: String,
    default: '',
  },
  hint: {
    type: String,
    default: '',
  },
  trend: {
    type: String,
    default: '',
  },
  tone: {
    type: String,
    default: 'primary',
  },
  icon: {
    type: [Object, Function],
    default: null,
  },
  trendDirection: {
    type: String,
    default: 'flat',
  },
  trendLabel: {
    type: String,
    default: '',
  },
})

const displayValue = computed(() => `${props.prefix}${props.value}${props.suffix}`)
const trendClass = computed(() => `stat-surface__badge--${props.trendDirection}`)
</script>

<template>
  <article class="stat-surface surface-card metric-card" :class="`stat-surface--${tone}`">
    <div class="metric-card__glow"></div>
    <div class="stat-surface__header">
      <div>
        <p class="stat-surface__label">{{ label }}</p>
        <h3 class="stat-surface__value">{{ displayValue }}</h3>
      </div>
      <div v-if="icon" class="stat-surface__icon">
        <component :is="icon" />
      </div>
    </div>
    <div class="stat-surface__footer">
      <span v-if="trend" class="stat-surface__badge" :class="trendClass">{{ trend }}</span>
      <span class="stat-surface__meta">{{ trendLabel || hint }}</span>
    </div>
    <div class="metric-card__progress">
      <span class="metric-card__progress-inner"></span>
    </div>
  </article>
</template>

<style scoped>
.metric-card {
  animation: metricReveal 420ms ease both;
}

.metric-card__glow {
  position: absolute;
  width: 180px;
  height: 180px;
  border-radius: 999px;
  right: -70px;
  top: -80px;
  background: radial-gradient(circle, rgba(64, 158, 255, 0.18), transparent 70%);
  pointer-events: none;
  transition: transform 260ms ease;
}

.metric-card:hover .metric-card__glow {
  transform: scale(1.08);
}

.stat-surface {
  position: relative;
  overflow: hidden;
}

.stat-surface__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.stat-surface__footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.stat-surface__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--color-primary-strong);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.stat-surface__icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.stat-surface__badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.stat-surface__badge--up {
  background: rgba(34, 160, 107, 0.12);
  color: #16885a;
}

.stat-surface__badge--down {
  background: rgba(216, 79, 87, 0.12);
  color: #c23b43;
}

.stat-surface__badge--flat {
  background: rgba(75, 95, 122, 0.12);
  color: #4b5f7a;
}

.metric-card__progress {
  margin-top: 12px;
  height: 3px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.2);
  overflow: hidden;
}

.metric-card__progress-inner {
  display: block;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, rgba(79, 70, 229, 0.8), rgba(54, 209, 220, 0.86));
  transform-origin: left;
  animation: metricProgress 820ms ease both;
}

.stat-surface::after {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 3px;
  opacity: 0.9;
}

.stat-surface--primary::after {
  background: linear-gradient(90deg, #2f74ff, #62a2ff);
}

.stat-surface--success::after {
  background: linear-gradient(90deg, #22a06b, #62c98d);
}

.stat-surface--warning::after {
  background: linear-gradient(90deg, #d9911f, #f3bf57);
}

.stat-surface--danger::after {
  background: linear-gradient(90deg, #d84f57, #f78a8f);
}

.stat-surface--info::after {
  background: linear-gradient(90deg, #4b5f7a, #7d90ab);
}

:root[data-theme='dark'] .stat-surface__icon {
  background: rgba(15, 23, 42, 0.7);
}

:root[data-theme='dark'] .stat-surface__badge--up {
  color: #7ce2ac;
}

:root[data-theme='dark'] .stat-surface__badge--down {
  color: #ff9ca2;
}

:root[data-theme='dark'] .stat-surface__badge--flat {
  color: #b2bfd4;
}

@keyframes metricReveal {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes metricProgress {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}
</style>
