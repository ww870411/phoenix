<template>
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <template v-for="(item, idx) in items" :key="idx">
      <a
        v-if="item.to && idx < items.length - 1"
        href="#"
        @click.prevent="go(item.to)"
      >{{ item.label }}</a>
      <span v-else class="current">{{ item.label }}</span>
      <span v-if="idx < items.length - 1" class="separator">›</span>
    </template>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const items = computed(() => {
  const name = route.name
  const p = route.params || {}
  const q = route.query || {}
  const projectKey = p.projectKey
  const sheetKey = p.sheetKey
  const biz = q.biz_date

  // 基于路由名与参数构造面包屑
  // login 页不显示面包屑
  if (name === 'projects') {
    return [
      { label: '项目', to: null },
    ]
  }
  if (name === 'dashboard') {
    return [
      { label: '项目', to: '/projects' },
      { label: String(projectKey || ''), to: null },
    ]
  }
  if (name === 'data-entry') {
    const fillPath = `/projects/${encodeURIComponent(projectKey)}/sheets/${encodeURIComponent(sheetKey)}/fill${biz ? `?biz_date=${encodeURIComponent(biz)}` : ''}`
    return [
      { label: '项目', to: '/projects' },
      { label: String(projectKey || ''), to: `/projects/${encodeURIComponent(projectKey)}/dashboard` },
      { label: `填报：${String(sheetKey || '')}`, to: null },
    ]
  }
  // 其他兜底：不显示或仅显示当前
  return [ { label: '导航', to: null } ]
})

function go(path) {
  router.push(path)
}
</script>

<style scoped>
.breadcrumbs {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 14px;
  margin: 4px 0 12px 0;
}
.breadcrumbs a { color: var(--primary-700); text-decoration: none; }
.breadcrumbs a:hover { text-decoration: underline; }
.separator { color: #cbd5e1; user-select: none; }
.current { color: var(--text); font-weight: 700; }
</style>
