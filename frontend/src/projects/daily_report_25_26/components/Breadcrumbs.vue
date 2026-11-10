<template>
  <nav class="breadcrumbs" aria-label="面包屑导航">
    <ol>
      <li v-for="(it, idx) in normalized" :key="idx">
        <span v-if="idx > 0" class="separator" aria-hidden="true">/</span>
        <span v-if="!it.to || idx === lastIndex" class="crumb current" :aria-current="idx === lastIndex ? 'page' : undefined">{{ it.label }}</span>
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
.breadcrumbs { margin: 8px 0 12px; color: var(--muted, #64748b); font-size: 14px; line-height: 1.7; }
.breadcrumbs ol { display: flex; flex-wrap: wrap; gap: 4px 8px; list-style: none; padding: 0; margin: 0; }
.breadcrumbs li { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.separator { flex: none; color: var(--muted, #64748b); }
.crumb { min-width: 0; overflow-wrap: anywhere; color: var(--primary-700, #1e40af); text-decoration: none; }
a.crumb:hover { text-decoration: underline; text-underline-offset: 3px; }
.crumb.current { color: var(--muted, #64748b); font-weight: 600; cursor: default; }
</style>

