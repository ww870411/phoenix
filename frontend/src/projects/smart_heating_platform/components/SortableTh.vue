<template>
  <th
    :class="['sortable-th', { 'is-sorted': isActive }]"
    scope="col"
    :aria-sort="ariaSort"
    title="点击排序（降序 / 升序 / 恢复默认）"
    @click="onToggle"
  >
    <span class="sth-inner">
      <span>{{ label }}</span>
      <span class="sth-icon" aria-hidden="true">{{ icon }}</span>
    </span>
  </th>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  sortKey: {
    type: String,
    required: true,
  },
  sortState: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['sort'])

const isActive = computed(() => props.sortState?.key === props.sortKey && Boolean(props.sortState?.dir))

const ariaSort = computed(() => {
  if (!isActive.value) return 'none'
  return props.sortState.dir === 'asc' ? 'ascending' : 'descending'
})

const icon = computed(() => {
  if (!isActive.value) return '⇅'
  return props.sortState.dir === 'asc' ? '▲' : '▼'
})

function onToggle() {
  emit('sort', props.sortKey)
}
</script>

<style scoped>
.sortable-th {
  cursor: pointer;
  user-select: none;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.sortable-th:hover {
  background: #eff6ff !important;
  color: #1d4ed8 !important;
}

.sortable-th.is-sorted {
  background: #eff6ff !important;
  color: #1e40af !important;
}

.sth-inner {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.sth-icon {
  font-size: 10px;
  line-height: 1;
  opacity: 0.45;
  flex-shrink: 0;
}

.sortable-th:hover .sth-icon,
.sortable-th.is-sorted .sth-icon {
  opacity: 1;
  color: #1d4ed8;
}
</style>
