<script setup>
defineProps({
  rows: {
    type: Number,
    default: 6,
  },
  columns: {
    type: Number,
    default: 5,
  },
})
</script>

<template>
  <div class="table-skeleton">
    <div class="table-skeleton__toolbar">
      <el-skeleton-item variant="text" class="table-skeleton__title" />
      <div class="table-skeleton__filters">
        <el-skeleton-item variant="button" class="filter-pill" />
        <el-skeleton-item variant="button" class="filter-pill" />
        <el-skeleton-item variant="button" class="filter-pill" />
      </div>
    </div>

    <div class="table-skeleton__table">
      <div class="table-skeleton__row table-skeleton__row--head" :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }">
        <el-skeleton-item
          v-for="col in columns"
          :key="`head-${col}`"
          variant="text"
          class="table-skeleton__cell"
        />
      </div>

      <div
        v-for="row in rows"
        :key="`row-${row}`"
        class="table-skeleton__row"
        :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }"
      >
        <el-skeleton-item
          v-for="col in columns"
          :key="`cell-${row}-${col}`"
          variant="text"
          class="table-skeleton__cell"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.table-skeleton {
  display: grid;
  gap: 18px;
}

.table-skeleton__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.table-skeleton__title {
  width: 160px;
  height: 18px;
}

.table-skeleton__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-pill {
  width: 120px;
  height: 34px;
  border-radius: 999px;
}

.table-skeleton__table {
  border: 1px solid var(--color-border);
  border-radius: 18px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.92);
}

.table-skeleton__row {
  display: grid;
  gap: 14px;
  padding: 14px 18px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

.table-skeleton__row--head {
  background: rgba(47, 116, 255, 0.04);
  border-top: none;
}

.table-skeleton__cell {
  width: 100%;
  height: 14px;
}
</style>
