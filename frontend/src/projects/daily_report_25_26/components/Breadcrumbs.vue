<template>
  <nav class="breadcrumbs">
    <ol>
      <li v-for="(it, idx) in normalized" :key="idx">
        <span v-if="!it.to || idx === lastIndex" class="crumb current">{{ it.label }}</span>
        <router-link v-else class="crumb" :to="it.to">{{ it.label }}</router-link>
      </li>
    </ol>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const route = useRoute()
const normalized = computed(() => {
  if (Array.isArray(props.items) && props.items.length) return props.items
  // 回退：基于路由路径提供一个最小面包屑
  const segs = route.path.split('/').filter(Boolean)
  const acc = []
  let cur = ''
  for (const s of segs) {
    cur += `/${s}`
    acc.push({ label: s, to: cur })
  }
  return acc
})

const lastIndex = computed(() => Math.max(0, normalized.value.length - 1))
</script>

<style scoped>
.breadcrumbs { margin: 8px 0 12px; color: var(--neutral-600); }
ol { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; padding: 0; margin: 0; }
.crumb { color: var(--primary-700); text-decoration: none; }
.crumb.current { color: var(--neutral-600); font-weight: 600; cursor: default; }
li::after { content: '/'; margin: 0 6px; color: var(--neutral-400); }
li:last-child::after { content: ''; margin: 0; }
</style>

